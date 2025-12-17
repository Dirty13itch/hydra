"""
Container Health Monitoring Module for Hydra

Provides external healthcheck capabilities for containers without built-in healthchecks.
Reports container health status to Prometheus metrics format.

This module adds "soft" healthchecks via HTTP probes for containers that
don't have Docker-level healthchecks defined.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List
import httpx
import docker
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NO_PROBE = "no_probe"


@dataclass
class ContainerHealthConfig:
    """Configuration for container healthcheck."""
    name: str
    probe_type: str  # "http", "tcp", "exec"
    probe_target: str  # URL, host:port, or command
    timeout_seconds: int = 5
    interval_seconds: int = 30
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3


@dataclass
class ContainerHealthResult:
    """Result of a container healthcheck."""
    name: str
    status: HealthStatus
    latency_ms: float
    last_check: str
    consecutive_failures: int
    message: str


# Prometheus metrics
container_health_status = Gauge(
    'hydra_container_health_status',
    'Container health status (1=healthy, 0=unhealthy, -1=unknown)',
    ['container']
)

container_health_latency = Gauge(
    'hydra_container_health_latency_ms',
    'Container healthcheck latency in milliseconds',
    ['container']
)

container_health_checks_total = Counter(
    'hydra_container_health_checks_total',
    'Total number of healthchecks performed',
    ['container', 'status']
)


# Host IP for containers on different Docker networks
HOST_IP = "192.168.1.244"

# Default healthcheck configurations for containers without Docker healthchecks
DEFAULT_HEALTHCHECKS = [
    # ===========================================
    # hydra-network (can use container hostnames)
    # ===========================================
    ContainerHealthConfig("hydra-n8n", "http", "http://hydra-n8n:5678/healthz"),
    ContainerHealthConfig("hydra-neo4j", "http", "http://hydra-neo4j:7474"),
    ContainerHealthConfig("hydra-litellm", "http", "http://hydra-litellm:4000/health/liveliness"),
    ContainerHealthConfig("hydra-grafana", "http", "http://hydra-grafana:3000/api/health"),
    ContainerHealthConfig("hydra-loki", "http", "http://hydra-loki:3100/ready"),
    ContainerHealthConfig("hydra-prometheus", "http", "http://hydra-prometheus:9090/-/healthy"),
    ContainerHealthConfig("hydra-miniflux", "http", "http://hydra-miniflux:8080/healthcheck"),
    ContainerHealthConfig("hydra-qdrant", "http", "http://hydra-qdrant:6333/readyz"),
    ContainerHealthConfig("hydra-alertmanager", "http", "http://hydra-alertmanager:9093/-/healthy"),
    ContainerHealthConfig("hydra-searxng", "http", "http://hydra-searxng:8080/healthz"),
    ContainerHealthConfig("hydra-letta", "http", "http://hydra-letta:8283/v1/health"),
    ContainerHealthConfig("hydra-docling", "http", "http://hydra-docling:5001/health"),
    ContainerHealthConfig("hydra-crewai", "http", "http://hydra-crewai:8500/"),
    ContainerHealthConfig("hydra-uptime-kuma", "http", f"http://{HOST_IP}:3001"),
    ContainerHealthConfig("hydra-meilisearch", "http", "http://hydra-meilisearch:7700/health"),
    ContainerHealthConfig("hydra-tools-api", "http", "http://hydra-tools-api:8700/health"),
    # hydra-command-center uses host IP (different network)
    ContainerHealthConfig("hydra-command-center", "http", f"http://{HOST_IP}:3210/"),

    # Firecrawl stack (port 3005 on host)
    ContainerHealthConfig("hydra-firecrawl-api", "http", f"http://{HOST_IP}:3005/"),

    # Control plane (various ports)
    ContainerHealthConfig("hydra-control-plane-ui", "http", f"http://{HOST_IP}:3200"),
    ContainerHealthConfig("hydra-control-plane-backend", "http", f"http://{HOST_IP}:3100/"),
    ContainerHealthConfig("hydra-task-hub", "http", "http://hydra-task-hub:8800"),

    # Open-webui (bridge network)
    ContainerHealthConfig("open-webui", "http", f"http://{HOST_IP}:3001/"),

    # ===========================================
    # Other networks (must use host IP)
    # ===========================================

    # Creative/App services (bridge network, use host IP)
    ContainerHealthConfig("homeassistant", "http", f"http://{HOST_IP}:8123/api/"),
    ContainerHealthConfig("sillytavern", "http", f"http://{HOST_IP}:8000"),
    ContainerHealthConfig("kokoro-tts", "http", f"http://{HOST_IP}:8880/health"),
    ContainerHealthConfig("perplexica", "http", f"http://{HOST_IP}:3030"),

    # Media services (download-stack_default network, use host IP)
    ContainerHealthConfig("sonarr", "http", f"http://{HOST_IP}:8989/ping"),
    ContainerHealthConfig("radarr", "http", f"http://{HOST_IP}:7878/ping"),
    ContainerHealthConfig("prowlarr", "http", f"http://{HOST_IP}:9696/ping"),
    ContainerHealthConfig("lidarr", "http", f"http://{HOST_IP}:8686/ping"),
    ContainerHealthConfig("readarr", "http", f"http://{HOST_IP}:8787/ping"),
    ContainerHealthConfig("bazarr", "http", f"http://{HOST_IP}:6767/api"),
    ContainerHealthConfig("sabnzbd", "http", f"http://{HOST_IP}:8085/api?mode=version"),
    ContainerHealthConfig("qbittorrent", "http", f"http://{HOST_IP}:8082"),

    # Infrastructure (various networks, use host IP)
    ContainerHealthConfig("adguard", "http", f"http://{HOST_IP}:3333"),
    ContainerHealthConfig("portainer", "http", f"http://{HOST_IP}:9000/api/status"),
    ContainerHealthConfig("node-exporter", "http", f"http://{HOST_IP}:9100/metrics"),
    ContainerHealthConfig("homepage", "http", f"http://{HOST_IP}:3000"),
    ContainerHealthConfig("Plex-Media-Server", "http", f"http://{HOST_IP}:32400/identity"),
    ContainerHealthConfig("stash", "http", f"http://{HOST_IP}:9999"),
    ContainerHealthConfig("whisparr", "http", f"http://{HOST_IP}:6969/ping"),
    # vaultwarden behind caddy proxy at port 8444 (HTTPS)
    # Skip health check for now as it requires HTTPS
]


class ContainerHealthMonitor:
    """Monitor container health via external probes."""

    def __init__(self, configs: list[ContainerHealthConfig] = None):
        self.configs = configs or DEFAULT_HEALTHCHECKS
        self._client = None
        self._results: dict[str, ContainerHealthResult] = {}
        self._failure_counts: dict[str, int] = {}

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_container(self, config: ContainerHealthConfig) -> ContainerHealthResult:
        """Perform healthcheck for a single container."""
        start = datetime.utcnow()

        try:
            if config.probe_type == "http":
                response = await self.client.get(
                    config.probe_target,
                    timeout=config.timeout_seconds
                )
                # Consider any HTTP response as healthy (service is running)
                # 2xx/3xx are success, 4xx means auth/path issue but service is up
                # Only 5xx indicates service problems
                if response.status_code < 500:
                    status = HealthStatus.HEALTHY
                    message = f"HTTP {response.status_code}"
                    self._failure_counts[config.name] = 0
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"HTTP {response.status_code}"
                    self._failure_counts[config.name] = self._failure_counts.get(config.name, 0) + 1
            else:
                status = HealthStatus.NO_PROBE
                message = f"Unsupported probe type: {config.probe_type}"

        except httpx.TimeoutException:
            status = HealthStatus.UNHEALTHY
            message = "Timeout"
            self._failure_counts[config.name] = self._failure_counts.get(config.name, 0) + 1
        except httpx.ConnectError:
            status = HealthStatus.UNHEALTHY
            message = "Connection refused"
            self._failure_counts[config.name] = self._failure_counts.get(config.name, 0) + 1
        except Exception as e:
            status = HealthStatus.UNKNOWN
            message = str(e)[:100]
            self._failure_counts[config.name] = self._failure_counts.get(config.name, 0) + 1

        end = datetime.utcnow()
        latency_ms = (end - start).total_seconds() * 1000

        result = ContainerHealthResult(
            name=config.name,
            status=status,
            latency_ms=latency_ms,
            last_check=end.isoformat() + "Z",
            consecutive_failures=self._failure_counts.get(config.name, 0),
            message=message,
        )

        # Update Prometheus metrics
        status_value = 1 if status == HealthStatus.HEALTHY else (0 if status == HealthStatus.UNHEALTHY else -1)
        container_health_status.labels(container=config.name).set(status_value)
        container_health_latency.labels(container=config.name).set(latency_ms)
        container_health_checks_total.labels(container=config.name, status=status.value).inc()

        self._results[config.name] = result
        return result

    async def check_all(self) -> list[ContainerHealthResult]:
        """Check health of all configured containers."""
        tasks = [self.check_container(config) for config in self.configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, ContainerHealthResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                print(f"Health check error: {r}")

        return valid_results

    def get_summary(self) -> dict:
        """Get summary of all healthcheck results."""
        results = list(self._results.values())
        healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        unhealthy = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for r in results if r.status in (HealthStatus.UNKNOWN, HealthStatus.NO_PROBE))

        return {
            "total": len(results),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "unknown": unknown,
            "health_rate": healthy / len(results) * 100 if results else 0,
        }


# Global monitor instance
_monitor = ContainerHealthMonitor()


def create_container_health_router() -> APIRouter:
    """Create the container health API router."""
    router = APIRouter(prefix="/container-health", tags=["container-health"])

    @router.get("/check-all")
    async def check_all_containers():
        """Run healthchecks on all configured containers."""
        results = await _monitor.check_all()
        summary = _monitor.get_summary()

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "containers": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "message": r.message,
                    "consecutive_failures": r.consecutive_failures,
                }
                for r in results
            ]
        }

    @router.get("/check/{container_name}")
    async def check_single_container(container_name: str):
        """Run healthcheck on a specific container."""
        for config in _monitor.configs:
            if config.name == container_name:
                result = await _monitor.check_container(config)
                return {
                    "name": result.name,
                    "status": result.status.value,
                    "latency_ms": result.latency_ms,
                    "message": result.message,
                    "last_check": result.last_check,
                    "consecutive_failures": result.consecutive_failures,
                }

        return {"error": f"Container {container_name} not configured for healthchecks"}

    @router.get("/status")
    async def get_health_status():
        """Get current cached health status (without running new checks)."""
        summary = _monitor.get_summary()
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "containers": {
                name: {
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "last_check": r.last_check,
                    "message": r.message,
                }
                for name, r in _monitor._results.items()
            }
        }

    @router.get("/unhealthy")
    async def get_unhealthy_containers():
        """Get list of unhealthy containers."""
        unhealthy = [
            {
                "name": r.name,
                "status": r.status.value,
                "message": r.message,
                "consecutive_failures": r.consecutive_failures,
                "last_check": r.last_check,
            }
            for r in _monitor._results.values()
            if r.status != HealthStatus.HEALTHY
        ]

        return {
            "count": len(unhealthy),
            "containers": unhealthy,
        }

    @router.get("/configs")
    async def get_healthcheck_configs():
        """Get list of configured healthchecks."""
        return {
            "total": len(_monitor.configs),
            "configs": [
                {
                    "name": c.name,
                    "probe_type": c.probe_type,
                    "probe_target": c.probe_target,
                    "timeout_seconds": c.timeout_seconds,
                }
                for c in _monitor.configs
            ]
        }

    @router.get("/metrics")
    async def get_prometheus_metrics():
        """Get Prometheus metrics for container health."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    # Container restart and remediation endpoints
    PROTECTED_CONTAINERS = {
        "hydra-postgres", "hydra-neo4j", "hydra-qdrant",
        "homeassistant", "adguard", "portainer"
    }

    class RestartRequest(BaseModel):
        container_name: str
        reason: str = "manual"
        force: bool = False

    class RemediationRequest(BaseModel):
        container_name: str
        action: str  # "restart", "stop", "start", "logs"
        reason: str = "auto-remediation"

    @router.post("/restart/{container_name}")
    async def restart_container(container_name: str, reason: str = "manual"):
        """Restart a container by name. Respects constitutional protections."""
        # Check constitutional protections
        if container_name in PROTECTED_CONTAINERS:
            raise HTTPException(
                status_code=403,
                detail=f"Container {container_name} is constitutionally protected. Manual approval required."
            )

        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.restart(timeout=30)

            return {
                "status": "success",
                "container": container_name,
                "action": "restart",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found")
        except docker.errors.APIError as e:
            raise HTTPException(status_code=500, detail=f"Docker API error: {str(e)}")

    @router.post("/remediate")
    async def remediate_container(request: RemediationRequest):
        """Execute a remediation action on a container."""
        # Check constitutional protections
        if request.container_name in PROTECTED_CONTAINERS and request.action in ["stop", "restart"]:
            raise HTTPException(
                status_code=403,
                detail=f"Container {request.container_name} is constitutionally protected."
            )

        try:
            client = docker.from_env()
            container = client.containers.get(request.container_name)

            result = {"container": request.container_name, "action": request.action}

            if request.action == "restart":
                container.restart(timeout=30)
                result["status"] = "restarted"
            elif request.action == "stop":
                container.stop(timeout=30)
                result["status"] = "stopped"
            elif request.action == "start":
                container.start()
                result["status"] = "started"
            elif request.action == "logs":
                logs = container.logs(tail=100).decode("utf-8")
                result["status"] = "fetched"
                result["logs"] = logs
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

            result["reason"] = request.reason
            result["timestamp"] = datetime.utcnow().isoformat() + "Z"
            return result

        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail=f"Container {request.container_name} not found")
        except docker.errors.APIError as e:
            raise HTTPException(status_code=500, detail=f"Docker API error: {str(e)}")

    @router.get("/remediation-history")
    async def get_remediation_history():
        """Get recent remediation actions (placeholder for audit log integration)."""
        return {
            "message": "Remediation history available via /audit endpoint",
            "endpoint": "/audit?category=remediation"
        }

    return router
