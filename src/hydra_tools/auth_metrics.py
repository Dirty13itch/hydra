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
