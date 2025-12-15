"""
Health Check Definitions

Defines health checks for all cluster services.
"""

import asyncio
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx


class CheckStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CheckResult:
    """Result of a health check."""
    service: str
    status: CheckStatus
    latency_ms: float
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ServiceCheck:
    """Service health check definition."""
    name: str
    url: str
    node: str
    category: str = "service"
    timeout: float = 5.0
    critical: bool = True
    expected_status: int = 200
    custom_check: Optional[Callable] = None


# Service definitions
SERVICES: List[ServiceCheck] = [
    # Inference
    ServiceCheck("TabbyAPI", "http://192.168.1.250:5000/health", "hydra-ai", "inference", critical=True),
    ServiceCheck("Ollama", "http://192.168.1.203:11434/api/tags", "hydra-compute", "inference", critical=True),
    ServiceCheck("LiteLLM", "http://192.168.1.244:4000/health", "hydra-storage", "inference", critical=True),
    ServiceCheck("ComfyUI", "http://192.168.1.203:8188/system_stats", "hydra-compute", "inference", critical=False),

    # Databases
    ServiceCheck("PostgreSQL", "tcp://192.168.1.244:5432", "hydra-storage", "database", critical=True),
    ServiceCheck("Qdrant", "http://192.168.1.244:6333/health", "hydra-storage", "database", critical=True),
    ServiceCheck("Redis", "tcp://192.168.1.244:6379", "hydra-storage", "database", critical=True),
    ServiceCheck("Meilisearch", "http://192.168.1.244:7700/health", "hydra-storage", "database", critical=False),

    # Observability
    ServiceCheck("Prometheus", "http://192.168.1.244:9090/-/healthy", "hydra-storage", "observability"),
    ServiceCheck("Grafana", "http://192.168.1.244:3003/api/health", "hydra-storage", "observability"),
    ServiceCheck("Loki", "http://192.168.1.244:3100/ready", "hydra-storage", "observability"),

    # Automation
    ServiceCheck("n8n", "http://192.168.1.244:5678/healthz", "hydra-storage", "automation"),
    ServiceCheck("SearXNG", "http://192.168.1.244:8888/healthz", "hydra-storage", "automation"),
    ServiceCheck("Firecrawl", "http://192.168.1.244:3005/health", "hydra-storage", "automation", critical=False),

    # Web UIs
    ServiceCheck("Open WebUI", "http://192.168.1.250:3000", "hydra-ai", "ui", critical=False),
    ServiceCheck("Perplexica", "http://192.168.1.244:3030", "hydra-storage", "ui", critical=False),
    ServiceCheck("SillyTavern", "http://192.168.1.244:8000", "hydra-storage", "ui", critical=False),

    # Media
    ServiceCheck("Sonarr", "http://192.168.1.244:8989/ping", "hydra-storage", "media", critical=False),
    ServiceCheck("Radarr", "http://192.168.1.244:7878/ping", "hydra-storage", "media", critical=False),
    ServiceCheck("Prowlarr", "http://192.168.1.244:9696/ping", "hydra-storage", "media", critical=False),
]


async def check_http(service: ServiceCheck, client: httpx.AsyncClient) -> CheckResult:
    """Perform HTTP health check."""
    start = time.time()

    try:
        response = await client.get(
            service.url,
            timeout=service.timeout,
            follow_redirects=True,
        )
        latency = (time.time() - start) * 1000

        if response.status_code < 400:
            return CheckResult(
                service=service.name,
                status=CheckStatus.HEALTHY,
                latency_ms=latency,
                details={"status_code": response.status_code},
            )
        else:
            return CheckResult(
                service=service.name,
                status=CheckStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"HTTP {response.status_code}",
                details={"status_code": response.status_code},
            )

    except httpx.TimeoutException:
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=service.timeout * 1000,
            message="Timeout",
        )
    except httpx.ConnectError:
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=0,
            message="Connection refused",
        )
    except Exception as e:
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=0,
            message=str(e),
        )


async def check_tcp(service: ServiceCheck) -> CheckResult:
    """Perform TCP port check."""
    start = time.time()

    # Parse tcp://host:port
    url = service.url.replace("tcp://", "")
    host, port = url.split(":")
    port = int(port)

    try:
        # Async socket check
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: socket.create_connection((host, port), timeout=service.timeout)
            ),
            timeout=service.timeout,
        )
        latency = (time.time() - start) * 1000

        return CheckResult(
            service=service.name,
            status=CheckStatus.HEALTHY,
            latency_ms=latency,
            details={"host": host, "port": port},
        )

    except (socket.timeout, asyncio.TimeoutError):
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=service.timeout * 1000,
            message="Connection timeout",
        )
    except ConnectionRefusedError:
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=0,
            message="Connection refused",
        )
    except Exception as e:
        return CheckResult(
            service=service.name,
            status=CheckStatus.UNHEALTHY,
            latency_ms=0,
            message=str(e),
        )


async def check_service(service: ServiceCheck, client: httpx.AsyncClient) -> CheckResult:
    """Check a service based on its URL type."""
    if service.url.startswith("tcp://"):
        return await check_tcp(service)
    else:
        return await check_http(service, client)


async def check_all_services(
    services: Optional[List[ServiceCheck]] = None,
) -> List[CheckResult]:
    """Check all services in parallel."""
    services = services or SERVICES

    async with httpx.AsyncClient() as client:
        tasks = [check_service(svc, client) for svc in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CheckResult(
                    service=services[i].name,
                    status=CheckStatus.UNKNOWN,
                    latency_ms=0,
                    message=str(result),
                ))
            else:
                final_results.append(result)

        return final_results


def get_services_by_category(category: str) -> List[ServiceCheck]:
    """Get services filtered by category."""
    return [s for s in SERVICES if s.category == category]


def get_services_by_node(node: str) -> List[ServiceCheck]:
    """Get services filtered by node."""
    return [s for s in SERVICES if s.node == node]
