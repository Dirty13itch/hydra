"""
Tests for hydra_health module
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        from hydra_health.checks import CheckStatus

        assert CheckStatus.HEALTHY.value == "healthy"
        assert CheckStatus.UNHEALTHY.value == "unhealthy"
        assert CheckStatus.DEGRADED.value == "degraded"
        assert CheckStatus.UNKNOWN.value == "unknown"


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_create_result(self):
        """Test creating a check result."""
        from hydra_health.checks import CheckResult, CheckStatus

        result = CheckResult(
            service="test-service",
            status=CheckStatus.HEALTHY,
            latency_ms=10.5,
        )

        assert result.service == "test-service"
        assert result.status == CheckStatus.HEALTHY
        assert result.latency_ms == 10.5
        assert result.message is None
        assert isinstance(result.timestamp, datetime)

    def test_result_with_message(self):
        """Test result with error message."""
        from hydra_health.checks import CheckResult, CheckStatus

        result = CheckResult(
            service="failing-service",
            status=CheckStatus.UNHEALTHY,
            latency_ms=0,
            message="Connection refused",
        )

        assert result.status == CheckStatus.UNHEALTHY
        assert result.message == "Connection refused"


class TestServiceCheck:
    """Tests for ServiceCheck dataclass."""

    def test_create_service_check(self):
        """Test creating a service check definition."""
        from hydra_health.checks import ServiceCheck

        check = ServiceCheck(
            name="TestService",
            url="http://localhost:8080/health",
            node="test-node",
            category="test",
        )

        assert check.name == "TestService"
        assert check.url == "http://localhost:8080/health"
        assert check.node == "test-node"
        assert check.timeout == 5.0  # default
        assert check.critical is True  # default

    def test_non_critical_service(self):
        """Test non-critical service."""
        from hydra_health.checks import ServiceCheck

        check = ServiceCheck(
            name="Optional",
            url="http://localhost/",
            node="test",
            critical=False,
        )

        assert check.critical is False


class TestServiceDefinitions:
    """Tests for service definitions."""

    def test_services_defined(self):
        """Test all expected services are defined."""
        from hydra_health.checks import SERVICES

        service_names = [s.name for s in SERVICES]

        # Key inference services
        assert "TabbyAPI" in service_names
        assert "Ollama" in service_names
        assert "LiteLLM" in service_names

        # Databases
        assert "PostgreSQL" in service_names
        assert "Qdrant" in service_names
        assert "Redis" in service_names

    def test_tcp_services(self):
        """Test TCP-based services have correct URL format."""
        from hydra_health.checks import SERVICES

        tcp_services = [s for s in SERVICES if s.url.startswith("tcp://")]

        for svc in tcp_services:
            # URL should be tcp://host:port
            assert ":" in svc.url.replace("tcp://", "")

    def test_http_services(self):
        """Test HTTP services have health endpoints."""
        from hydra_health.checks import SERVICES

        http_services = [s for s in SERVICES if s.url.startswith("http")]

        for svc in http_services:
            assert svc.url.startswith("http://") or svc.url.startswith("https://")


class TestHealthChecks:
    """Tests for health check functions."""

    @pytest.mark.asyncio
    async def test_check_http_success(self):
        """Test successful HTTP health check."""
        from hydra_health.checks import check_http, ServiceCheck, CheckStatus

        service = ServiceCheck(
            name="TestHTTP",
            url="http://localhost/health",
            node="test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await check_http(service, mock_client)

        assert result.status == CheckStatus.HEALTHY
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_check_http_failure(self):
        """Test failed HTTP health check."""
        from hydra_health.checks import check_http, ServiceCheck, CheckStatus
        import httpx

        service = ServiceCheck(
            name="TestHTTP",
            url="http://localhost/health",
            node="test",
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        result = await check_http(service, mock_client)

        assert result.status == CheckStatus.UNHEALTHY
        assert result.message == "Connection refused"

    @pytest.mark.asyncio
    async def test_check_http_timeout(self):
        """Test HTTP health check timeout."""
        from hydra_health.checks import check_http, ServiceCheck, CheckStatus
        import httpx

        service = ServiceCheck(
            name="TestHTTP",
            url="http://localhost/health",
            node="test",
            timeout=1.0,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        result = await check_http(service, mock_client)

        assert result.status == CheckStatus.UNHEALTHY
        assert result.message == "Timeout"
        assert result.latency_ms == 1000  # timeout in ms


class TestHealthAggregator:
    """Tests for HealthAggregator class."""

    def test_aggregator_creation(self):
        """Test creating health aggregator."""
        from hydra_health.server import HealthAggregator

        aggregator = HealthAggregator(cache_ttl=60)

        assert aggregator.cache_ttl == 60
        assert aggregator._cache is None

    @pytest.mark.asyncio
    async def test_aggregator_caching(self):
        """Test aggregator caches results."""
        from hydra_health.server import HealthAggregator

        aggregator = HealthAggregator(cache_ttl=60)

        # Mock check_all_services
        with patch("hydra_health.server.check_all_services") as mock_check:
            mock_check.return_value = []

            # First call
            result1 = await aggregator.get_health()

            # Second call should use cache
            result2 = await aggregator.get_health()

            # check_all_services should only be called once
            assert mock_check.call_count == 1
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_aggregator_force_refresh(self):
        """Test force refresh bypasses cache."""
        from hydra_health.server import HealthAggregator

        aggregator = HealthAggregator(cache_ttl=60)

        with patch("hydra_health.server.check_all_services") as mock_check:
            mock_check.return_value = []

            await aggregator.get_health()
            await aggregator.get_health(force_refresh=True)

            # Should be called twice with force_refresh
            assert mock_check.call_count == 2
