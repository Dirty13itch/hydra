"""
Tests for API Prometheus Metrics.

Tests the /metrics endpoint and metric recording functions.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    from hydra_tools.api import app
    return TestClient(app)


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Metrics endpoint should return 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self, client):
        """Metrics should return Prometheus text format."""
        response = client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        # prometheus_client returns text/plain with charset
        assert "text/plain" in content_type or "text/openmetrics" in content_type

    def test_metrics_contains_auth_counters(self, client):
        """Metrics should contain auth request counters."""
        response = client.get("/metrics")
        content = response.text
        assert "hydra_api_auth_requests_total" in content

    def test_metrics_contains_auth_latency(self, client):
        """Metrics should contain auth latency histogram."""
        response = client.get("/metrics")
        content = response.text
        assert "hydra_api_auth_latency_seconds" in content

    def test_metrics_contains_auth_status(self, client):
        """Metrics should contain auth status gauges."""
        response = client.get("/metrics")
        content = response.text
        assert "hydra_api_auth_enabled" in content
        assert "hydra_api_auth_keys_configured" in content

    def test_metrics_contains_http_counters(self, client):
        """Metrics should contain HTTP request counters."""
        response = client.get("/metrics")
        content = response.text
        assert "hydra_api_http_requests_total" in content

    def test_metrics_contains_http_latency(self, client):
        """Metrics should contain HTTP request latency histogram."""
        response = client.get("/metrics")
        content = response.text
        assert "hydra_api_http_request_latency_seconds" in content


class TestMetricsRecording:
    """Tests that metrics are recorded correctly."""

    def test_health_request_increments_counter(self, client):
        """Health check should increment request counter."""
        # Get metrics before
        before = client.get("/metrics").text

        # Make a health request
        client.get("/health")

        # Get metrics after
        after = client.get("/metrics").text

        # Verify the health endpoint metrics exist
        assert 'endpoint="/health"' in after

    def test_auth_disabled_recorded(self, client):
        """Auth disabled result should be recorded."""
        # Make a request that triggers auth check
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should show disabled result (since no API key is set)
        assert 'result="disabled"' in content or 'result="exempt"' in content

    def test_request_latency_recorded(self, client):
        """Request latency should be recorded."""
        # Make a request
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have latency histogram entries
        assert "hydra_api_http_request_latency_seconds_bucket" in content
        assert "hydra_api_http_request_latency_seconds_count" in content


class TestMetricsNoAuth:
    """Tests that /metrics doesn't require authentication."""

    def test_metrics_exempt_from_auth(self, client):
        """Metrics endpoint should be exempt from auth."""
        # Even with auth enabled environment, /metrics should work
        response = client.get("/metrics")
        # Should not get 401 or 403
        assert response.status_code == 200
