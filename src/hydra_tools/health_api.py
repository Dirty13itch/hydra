"""
Health API Router

Exposes cluster health aggregation via the Hydra Tools API.
Uses the hydra_health module for service checks.

Endpoints:
- /health/cluster - Full cluster health with all services
- /health/summary - Quick health summary
- /health/services - Per-service health (filterable)
- /health/nodes - Health by node
- /health/categories - Health by category
- /health/prometheus - Query Prometheus directly
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


# Configuration
PROMETHEUS_URL = "http://192.168.1.244:9090"
HEALTH_AGGREGATOR_URL = "http://192.168.1.244:8600"


class CheckStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealthInfo(BaseModel):
    """Individual service health."""
    service: str
    status: CheckStatus
    latency_ms: float
    message: Optional[str] = None
    node: str
    category: str
    critical: bool
    timestamp: datetime


class HealthSummaryInfo(BaseModel):
    """Health summary."""
    status: CheckStatus
    healthy: int
    unhealthy: int
    degraded: int
    unknown: int
    total: int
    critical_down: List[str]
    timestamp: datetime


class ClusterHealthInfo(BaseModel):
    """Complete cluster health."""
    summary: HealthSummaryInfo
    services: List[ServiceHealthInfo]
    nodes: Dict[str, Dict[str, int]]
    categories: Dict[str, Dict[str, int]]


class PrometheusQueryResult(BaseModel):
    """Prometheus query result."""
    query: str
    result_type: str
    results: List[Dict[str, Any]]
    timestamp: str


# Service definitions for direct checks
SERVICES = [
    # Inference
    {"name": "TabbyAPI", "url": "http://192.168.1.250:5000/health", "node": "hydra-ai", "category": "inference", "critical": True},
    {"name": "Ollama", "url": "http://192.168.1.203:11434/api/tags", "node": "hydra-compute", "category": "inference", "critical": True},
    {"name": "LiteLLM", "url": "http://192.168.1.244:4000/health/liveliness", "node": "hydra-storage", "category": "inference", "critical": True},
    {"name": "ComfyUI", "url": "http://192.168.1.203:8188/system_stats", "node": "hydra-compute", "category": "inference", "critical": False},
    # Databases
    {"name": "Qdrant", "url": "http://192.168.1.244:6333/healthz", "node": "hydra-storage", "category": "database", "critical": True},
    {"name": "Neo4j", "url": "http://192.168.1.244:7474/", "node": "hydra-storage", "category": "database", "critical": False},
    {"name": "Meilisearch", "url": "http://192.168.1.244:7700/health", "node": "hydra-storage", "category": "database", "critical": False},
    # Observability
    {"name": "Prometheus", "url": "http://192.168.1.244:9090/-/healthy", "node": "hydra-storage", "category": "observability", "critical": True},
    {"name": "Grafana", "url": "http://192.168.1.244:3003/api/health", "node": "hydra-storage", "category": "observability", "critical": False},
    {"name": "Loki", "url": "http://192.168.1.244:3100/ready", "node": "hydra-storage", "category": "observability", "critical": False},
    # Automation
    {"name": "n8n", "url": "http://192.168.1.244:5678/healthz", "node": "hydra-storage", "category": "automation", "critical": True},
    # Web UIs
    {"name": "Open WebUI", "url": "http://192.168.1.244:3001", "node": "hydra-storage", "category": "webui", "critical": False},
    {"name": "Command Center", "url": "http://192.168.1.244:3210/", "node": "hydra-storage", "category": "webui", "critical": False},
    # Agents
    {"name": "Letta", "url": "http://192.168.1.244:8283/v1/health/", "node": "hydra-storage", "category": "agents", "critical": False},
    {"name": "CrewAI", "url": "http://192.168.1.244:8500/", "node": "hydra-storage", "category": "agents", "critical": False},
]


async def check_service(service: dict, client: httpx.AsyncClient) -> ServiceHealthInfo:
    """Check a single service health."""
    import time
    start = time.time()

    try:
        resp = await client.get(service["url"], timeout=5.0)
        latency = (time.time() - start) * 1000

        if resp.status_code < 400:
            status = CheckStatus.HEALTHY
            message = None
        else:
            status = CheckStatus.UNHEALTHY
            message = f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        latency = 5000
        status = CheckStatus.UNHEALTHY
        message = "Timeout"
    except httpx.ConnectError:
        latency = 0
        status = CheckStatus.UNHEALTHY
        message = "Connection refused"
    except Exception as e:
        latency = 0
        status = CheckStatus.UNKNOWN
        message = str(e)

    return ServiceHealthInfo(
        service=service["name"],
        status=status,
        latency_ms=latency,
        message=message,
        node=service["node"],
        category=service["category"],
        critical=service["critical"],
        timestamp=datetime.utcnow(),
    )


def create_health_router() -> APIRouter:
    """Create and configure the health API router."""
    router = APIRouter(prefix="/health", tags=["cluster-health"])

    @router.get("/cluster", response_model=ClusterHealthInfo)
    async def get_cluster_health(
        refresh: bool = Query(False, description="Force refresh (bypass cache)"),
    ):
        """
        Get complete cluster health status.

        Checks all configured services and returns comprehensive health info.
        """
        async with httpx.AsyncClient() as client:
            # Check all services in parallel
            tasks = [check_service(svc, client) for svc in SERVICES]
            services = await asyncio.gather(*tasks)

        # Calculate summary
        healthy = sum(1 for s in services if s.status == CheckStatus.HEALTHY)
        unhealthy = sum(1 for s in services if s.status == CheckStatus.UNHEALTHY)
        degraded = sum(1 for s in services if s.status == CheckStatus.DEGRADED)
        unknown = sum(1 for s in services if s.status == CheckStatus.UNKNOWN)

        critical_down = [
            s.service for s in services
            if s.status == CheckStatus.UNHEALTHY and s.critical
        ]

        if critical_down:
            overall = CheckStatus.UNHEALTHY
        elif unhealthy > 0 or degraded > 0:
            overall = CheckStatus.DEGRADED
        elif unknown > 0:
            overall = CheckStatus.UNKNOWN
        else:
            overall = CheckStatus.HEALTHY

        # Group by node
        nodes: Dict[str, Dict[str, int]] = {}
        for svc in services:
            if svc.node not in nodes:
                nodes[svc.node] = {"healthy": 0, "unhealthy": 0, "total": 0}
            nodes[svc.node]["total"] += 1
            if svc.status == CheckStatus.HEALTHY:
                nodes[svc.node]["healthy"] += 1
            else:
                nodes[svc.node]["unhealthy"] += 1

        # Group by category
        categories: Dict[str, Dict[str, int]] = {}
        for svc in services:
            if svc.category not in categories:
                categories[svc.category] = {"healthy": 0, "unhealthy": 0, "total": 0}
            categories[svc.category]["total"] += 1
            if svc.status == CheckStatus.HEALTHY:
                categories[svc.category]["healthy"] += 1
            else:
                categories[svc.category]["unhealthy"] += 1

        return ClusterHealthInfo(
            summary=HealthSummaryInfo(
                status=overall,
                healthy=healthy,
                unhealthy=unhealthy,
                degraded=degraded,
                unknown=unknown,
                total=len(services),
                critical_down=critical_down,
                timestamp=datetime.utcnow(),
            ),
            services=services,
            nodes=nodes,
            categories=categories,
        )

    @router.get("/summary", response_model=HealthSummaryInfo)
    async def get_health_summary():
        """
        Get quick health summary.

        Returns just the summary without individual service details.
        """
        health = await get_cluster_health(refresh=False)
        return health.summary

    @router.get("/services", response_model=List[ServiceHealthInfo])
    async def get_services_health(
        category: Optional[str] = Query(None, description="Filter by category"),
        node: Optional[str] = Query(None, description="Filter by node"),
        status: Optional[CheckStatus] = Query(None, description="Filter by status"),
    ):
        """
        Get per-service health status.

        Supports filtering by category, node, or status.
        """
        health = await get_cluster_health(refresh=False)
        services = health.services

        if category:
            services = [s for s in services if s.category == category]
        if node:
            services = [s for s in services if s.node == node]
        if status:
            services = [s for s in services if s.status == status]

        return services

    @router.get("/service/{name}", response_model=ServiceHealthInfo)
    async def get_service_health(name: str):
        """
        Get health for a specific service.

        Returns health info for the named service.
        """
        health = await get_cluster_health(refresh=True)

        for svc in health.services:
            if svc.service.lower() == name.lower():
                return svc

        raise HTTPException(status_code=404, detail=f"Service not found: {name}")

    @router.get("/nodes")
    async def get_nodes_health():
        """
        Get health grouped by node.

        Returns health counts for each cluster node.
        """
        health = await get_cluster_health(refresh=False)
        return health.nodes

    @router.get("/categories")
    async def get_categories_health():
        """
        Get health grouped by category.

        Returns health counts for each service category.
        """
        health = await get_cluster_health(refresh=False)
        return health.categories

    @router.get("/prometheus", response_model=PrometheusQueryResult)
    async def query_prometheus(
        query: str = Query(..., description="PromQL query"),
        time: Optional[str] = Query(None, description="Evaluation time (RFC3339 or Unix)"),
    ):
        """
        Query Prometheus directly.

        Execute a PromQL instant query against Prometheus.
        """
        params = {"query": query}
        if time:
            params["time"] = time

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params=params
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") != "success":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Prometheus error: {data.get('error', 'Unknown error')}"
                    )

                result = data.get("data", {})
                return PrometheusQueryResult(
                    query=query,
                    result_type=result.get("resultType", "unknown"),
                    results=result.get("result", []),
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Prometheus error: {str(e)}")

    @router.get("/prometheus/range")
    async def query_prometheus_range(
        query: str = Query(..., description="PromQL query"),
        start: str = Query(..., description="Start time"),
        end: str = Query(..., description="End time"),
        step: str = Query("1m", description="Query step"),
    ):
        """
        Query Prometheus range.

        Execute a PromQL range query against Prometheus.
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/query_range",
                    params=params
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("status") != "success":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Prometheus error: {data.get('error', 'Unknown error')}"
                    )

                return data.get("data", {})
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Prometheus error: {str(e)}")

    @router.get("/gpu")
    async def get_gpu_health():
        """
        Get GPU health metrics from Prometheus.

        Returns GPU utilization, memory, and temperature across nodes.
        """
        queries = {
            "utilization": 'nvidia_smi_gpu_utilization_percentage',
            "memory_used": 'nvidia_smi_memory_used_bytes',
            "memory_total": 'nvidia_smi_memory_total_bytes',
            "temperature": 'nvidia_smi_temperature_celsius',
            "power": 'nvidia_smi_power_draw_watts',
        }

        results = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, query in queries.items():
                try:
                    resp = await client.get(
                        f"{PROMETHEUS_URL}/api/v1/query",
                        params={"query": query}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "success":
                            results[name] = data.get("data", {}).get("result", [])
                except Exception:
                    results[name] = []

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": results,
        }

    return router
