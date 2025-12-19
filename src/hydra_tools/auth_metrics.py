"""
Prometheus Metrics for API Authentication

Tracks:
- Auth request counts (success/failure/disabled)
- Auth request latency
- API key usage patterns
"""

import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


# =============================================================================
# Authentication Metrics
# =============================================================================

# Request counters by result
AUTH_REQUESTS_TOTAL = Counter(
    "hydra_api_auth_requests_total",
    "Total authentication requests",
    ["result", "path_prefix"]
)

# Auth request latency histogram (excluding request processing time)
AUTH_LATENCY = Histogram(
    "hydra_api_auth_latency_seconds",
    "Authentication check latency in seconds",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1]
)

# Currently configured API keys count (not the actual keys)
AUTH_KEYS_CONFIGURED = Gauge(
    "hydra_api_auth_keys_configured",
    "Number of API keys currently configured"
)

# Auth enabled status (1 = enabled, 0 = disabled)
AUTH_ENABLED = Gauge(
    "hydra_api_auth_enabled",
    "Whether API key authentication is enabled (1) or disabled (0)"
)


# =============================================================================
# Request Metrics
# =============================================================================

# HTTP requests total by method and status
HTTP_REQUESTS_TOTAL = Counter(
    "hydra_api_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

# HTTP request latency by endpoint
HTTP_REQUEST_LATENCY = Histogram(
    "hydra_api_http_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Active requests gauge
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "hydra_api_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"]
)


# =============================================================================
# Inference Health Metrics (for Prometheus alerting)
# =============================================================================

# Service health gauges (1=healthy, 0=unhealthy)
INFERENCE_SERVICE_HEALTH = Gauge(
    "hydra_inference_service_health",
    "Inference service health (1=healthy, 0=unhealthy)",
    ["service", "node"]
)

# TabbyAPI specific metrics
TABBYAPI_MODEL_LOADED = Gauge(
    "hydra_tabbyapi_model_loaded",
    "Whether TabbyAPI has a model loaded (1=loaded, 0=no model)"
)

TABBYAPI_VRAM_USED_GB = Gauge(
    "hydra_tabbyapi_vram_used_gb",
    "VRAM used by TabbyAPI in GB",
    ["gpu"]
)

# Inference latency from health checks
INFERENCE_HEALTH_CHECK_LATENCY = Gauge(
    "hydra_inference_health_check_latency_ms",
    "Latency of health check in milliseconds",
    ["service"]
)

# Service restart counter (pushed when detected)
INFERENCE_SERVICE_RESTARTS = Counter(
    "hydra_inference_service_restarts_total",
    "Total service restarts detected",
    ["service"]
)

# Circuit breaker state (0=closed/healthy, 1=open/tripped)
INFERENCE_CIRCUIT_BREAKER = Gauge(
    "hydra_inference_circuit_breaker_open",
    "Circuit breaker state (0=closed, 1=open)",
    ["service"]
)


# =============================================================================
# Metric Recording Functions
# =============================================================================

def record_auth_result(result: str, path: str):
    """
    Record an authentication result.

    Args:
        result: One of 'success', 'missing_key', 'invalid_key', 'disabled', 'exempt'
        path: Request path (will be converted to prefix)
    """
    # Convert path to prefix for lower cardinality
    path_prefix = _get_path_prefix(path)
    AUTH_REQUESTS_TOTAL.labels(result=result, path_prefix=path_prefix).inc()


def record_auth_latency(duration_seconds: float):
    """Record authentication check latency."""
    AUTH_LATENCY.observe(duration_seconds)


def update_auth_status(enabled: bool, num_keys: int):
    """Update auth status gauges."""
    AUTH_ENABLED.set(1 if enabled else 0)
    AUTH_KEYS_CONFIGURED.set(num_keys)


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float):
    """
    Record an HTTP request.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: Response status code
        duration_seconds: Request duration
    """
    endpoint = _get_path_prefix(path)
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    HTTP_REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration_seconds)


def _get_path_prefix(path: str) -> str:
    """
    Convert a path to its prefix for metric labeling.

    Reduces cardinality by grouping paths like:
    - /diagnosis/analyze/123 -> /diagnosis
    - /characters/abc-123/portrait -> /characters
    """
    if not path or path == "/":
        return "/"

    # Remove leading slash and split
    parts = path.lstrip("/").split("/")
    if parts:
        return f"/{parts[0]}"
    return "/"


# =============================================================================
# Metrics Endpoint
# =============================================================================

async def metrics_endpoint():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# Inference Health Updater with Circuit Breaker
# =============================================================================

import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

# Inference service endpoints
INFERENCE_SERVICES = {
    "tabbyapi": {"url": "http://192.168.1.250:5000/health", "node": "hydra-ai"},
    "ollama_gpu": {"url": "http://192.168.1.203:11434/api/tags", "node": "hydra-compute"},
    "ollama_cpu": {"url": "http://192.168.1.244:11434/api/tags", "node": "hydra-storage"},
    "litellm": {"url": "http://192.168.1.244:4000/health/liveliness", "node": "hydra-storage"},
}

# Track last known state for restart detection
_last_known_healthy = {}

# Circuit breaker instance (lazy loaded to avoid circular imports)
_circuit_breakers = None


def _get_circuit_breakers():
    """Get or create the circuit breakers instance."""
    global _circuit_breakers
    if _circuit_breakers is None:
        from hydra_tools.circuit_breaker import InferenceCircuitBreakers
        _circuit_breakers = InferenceCircuitBreakers()

        # Register callback to update Prometheus metrics
        def update_circuit_metric(service: str, is_open: int):
            INFERENCE_CIRCUIT_BREAKER.labels(service=service).set(is_open)

        _circuit_breakers.register_metrics_callback(update_circuit_metric)

    return _circuit_breakers


async def update_inference_metrics():
    """Update inference service health metrics with circuit breaker integration."""
    breakers = _get_circuit_breakers()

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, config in INFERENCE_SERVICES.items():
            breaker = breakers.get_or_create(service)

            # Skip health check if circuit is open (but still update metrics)
            if breaker.is_open:
                INFERENCE_SERVICE_HEALTH.labels(
                    service=service,
                    node=config["node"]
                ).set(0)
                INFERENCE_CIRCUIT_BREAKER.labels(service=service).set(1)
                continue

            try:
                start = time.time()
                resp = await client.get(config["url"])
                latency_ms = (time.time() - start) * 1000

                healthy = resp.status_code < 400
                INFERENCE_SERVICE_HEALTH.labels(
                    service=service,
                    node=config["node"]
                ).set(1 if healthy else 0)

                INFERENCE_HEALTH_CHECK_LATENCY.labels(service=service).set(latency_ms)
                INFERENCE_CIRCUIT_BREAKER.labels(service=service).set(0)

                # Update circuit breaker
                if healthy:
                    await breaker.record_success()
                else:
                    await breaker.record_failure()

                # Detect restarts (was unhealthy, now healthy)
                was_healthy = _last_known_healthy.get(service, True)
                if healthy and not was_healthy:
                    INFERENCE_SERVICE_RESTARTS.labels(service=service).inc()
                    logger.info(f"Detected restart of {service}")
                _last_known_healthy[service] = healthy

            except Exception as e:
                INFERENCE_SERVICE_HEALTH.labels(
                    service=service,
                    node=config["node"]
                ).set(0)
                INFERENCE_HEALTH_CHECK_LATENCY.labels(service=service).set(5000)
                _last_known_healthy[service] = False
                await breaker.record_failure()

                # Update circuit breaker metric based on current state
                INFERENCE_CIRCUIT_BREAKER.labels(service=service).set(
                    1 if breaker.is_open else 0
                )

        # Check TabbyAPI model status
        try:
            resp = await client.get("http://192.168.1.250:5000/v1/model")
            if resp.status_code == 200:
                data = resp.json()
                model_id = data.get("id")
                TABBYAPI_MODEL_LOADED.set(1 if model_id else 0)
            else:
                TABBYAPI_MODEL_LOADED.set(0)
        except Exception:
            TABBYAPI_MODEL_LOADED.set(0)


def get_circuit_breaker_status() -> dict:
    """Get current circuit breaker status for all services."""
    breakers = _get_circuit_breakers()
    return {
        service: {
            "state": stats.state.value,
            "failure_count": stats.failure_count,
            "total_failures": stats.total_failures,
            "total_successes": stats.total_successes,
        }
        for service, stats in breakers.get_all_stats().items()
    }


async def inference_metrics_background_task():
    """Background task that updates inference metrics every 30 seconds."""
    while True:
        try:
            await update_inference_metrics()
        except Exception as e:
            logger.error(f"Error updating inference metrics: {e}")
        await asyncio.sleep(30)


def start_inference_metrics_updater():
    """Start the background task for updating inference metrics."""
    asyncio.create_task(inference_metrics_background_task())
    logger.info("Started inference metrics background updater with circuit breakers")
