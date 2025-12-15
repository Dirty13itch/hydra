"""
Health Aggregator API Server

FastAPI server providing unified health endpoints for the cluster.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .checks import (
    SERVICES,
    CheckResult,
    CheckStatus,
    ServiceCheck,
    check_all_services,
    check_service,
    get_services_by_category,
    get_services_by_node,
)

# API Models
class HealthSummary(BaseModel):
    """Overall cluster health summary."""
    status: CheckStatus
    healthy: int
    unhealthy: int
    degraded: int
    unknown: int
    total: int
    critical_down: List[str]
    timestamp: datetime


class ServiceHealth(BaseModel):
    """Individual service health."""
    service: str
    status: CheckStatus
    latency_ms: float
    message: Optional[str] = None
    node: str
    category: str
    critical: bool
    timestamp: datetime


class ClusterHealth(BaseModel):
    """Complete cluster health response."""
    summary: HealthSummary
    services: List[ServiceHealth]
    nodes: Dict[str, Dict[str, int]]
    categories: Dict[str, Dict[str, int]]


class HealthAggregator:
    """Manages cluster health checking with caching."""

    def __init__(self, cache_ttl: int = 30):
        self.cache_ttl = cache_ttl
        self._cache: Optional[ClusterHealth] = None
        self._cache_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def get_health(self, force_refresh: bool = False) -> ClusterHealth:
        """Get cluster health, using cache if available."""
        async with self._lock:
            now = datetime.utcnow()

            # Check cache validity
            if (
                not force_refresh
                and self._cache is not None
                and self._cache_time is not None
                and (now - self._cache_time).total_seconds() < self.cache_ttl
            ):
                return self._cache

            # Perform health checks
            results = await check_all_services()

            # Build service health list
            service_map = {s.name: s for s in SERVICES}
            services = []
            for result in results:
                svc_def = service_map.get(result.service)
                services.append(ServiceHealth(
                    service=result.service,
                    status=result.status,
                    latency_ms=result.latency_ms,
                    message=result.message,
                    node=svc_def.node if svc_def else "unknown",
                    category=svc_def.category if svc_def else "unknown",
                    critical=svc_def.critical if svc_def else False,
                    timestamp=result.timestamp,
                ))

            # Calculate counts
            healthy = sum(1 for r in results if r.status == CheckStatus.HEALTHY)
            unhealthy = sum(1 for r in results if r.status == CheckStatus.UNHEALTHY)
            degraded = sum(1 for r in results if r.status == CheckStatus.DEGRADED)
            unknown = sum(1 for r in results if r.status == CheckStatus.UNKNOWN)

            # Find critical services that are down
            critical_down = [
                r.service for r in results
                if r.status == CheckStatus.UNHEALTHY
                and service_map.get(r.service, ServiceCheck("", "", "", critical=False)).critical
            ]

            # Determine overall status
            if critical_down:
                overall_status = CheckStatus.UNHEALTHY
            elif unhealthy > 0 or degraded > 0:
                overall_status = CheckStatus.DEGRADED
            elif unknown > 0:
                overall_status = CheckStatus.UNKNOWN
            else:
                overall_status = CheckStatus.HEALTHY

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

            # Build response
            health = ClusterHealth(
                summary=HealthSummary(
                    status=overall_status,
                    healthy=healthy,
                    unhealthy=unhealthy,
                    degraded=degraded,
                    unknown=unknown,
                    total=len(results),
                    critical_down=critical_down,
                    timestamp=now,
                ),
                services=services,
                nodes=nodes,
                categories=categories,
            )

            # Update cache
            self._cache = health
            self._cache_time = now

            return health


# Create FastAPI app
app = FastAPI(
    title="Hydra Health Aggregator",
    description="Unified health monitoring API for Hydra cluster",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global aggregator
aggregator = HealthAggregator(cache_ttl=30)


@app.get("/")
async def root():
    """API root - redirect to health."""
    return {"message": "Hydra Health Aggregator", "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=ClusterHealth)
async def get_cluster_health(
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get complete cluster health status."""
    return await aggregator.get_health(force_refresh=refresh)


@app.get("/health/summary", response_model=HealthSummary)
async def get_health_summary(
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get health summary only."""
    health = await aggregator.get_health(force_refresh=refresh)
    return health.summary


@app.get("/health/services", response_model=List[ServiceHealth])
async def get_services_health(
    category: Optional[str] = Query(None, description="Filter by category"),
    node: Optional[str] = Query(None, description="Filter by node"),
    status: Optional[CheckStatus] = Query(None, description="Filter by status"),
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get individual service health."""
    health = await aggregator.get_health(force_refresh=refresh)
    services = health.services

    if category:
        services = [s for s in services if s.category == category]
    if node:
        services = [s for s in services if s.node == node]
    if status:
        services = [s for s in services if s.status == status]

    return services


@app.get("/health/service/{name}", response_model=ServiceHealth)
async def get_service_health(
    name: str,
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get health for a specific service."""
    health = await aggregator.get_health(force_refresh=refresh)

    for svc in health.services:
        if svc.service.lower() == name.lower():
            return svc

    raise HTTPException(status_code=404, detail=f"Service not found: {name}")


@app.get("/health/nodes", response_model=Dict[str, Dict[str, int]])
async def get_nodes_health(
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get health grouped by node."""
    health = await aggregator.get_health(force_refresh=refresh)
    return health.nodes


@app.get("/health/categories", response_model=Dict[str, Dict[str, int]])
async def get_categories_health(
    refresh: bool = Query(False, description="Force refresh cache"),
):
    """Get health grouped by category."""
    health = await aggregator.get_health(force_refresh=refresh)
    return health.categories


@app.get("/ready")
async def readiness():
    """Kubernetes-style readiness probe."""
    health = await aggregator.get_health()
    if health.summary.status == CheckStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="Cluster unhealthy")
    return {"status": "ready"}


@app.get("/live")
async def liveness():
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}


# Run with: uvicorn hydra_health.server:app --host 0.0.0.0 --port 8600
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
