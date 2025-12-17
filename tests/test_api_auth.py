"""
Tests for API Authentication endpoints and middleware.

Note: These tests use a single client fixture that doesn't require authentication.
The authentication middleware reads environment variables at import time, making
it difficult to test auth-enabled scenarios with mocking. For full auth testing,
use integration tests against a running API with HYDRA_API_KEY configured.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client (auth disabled by default in test environment)."""
    from hydra_tools.api import app
    return TestClient(app)


class TestAuthStatusEndpoint:
    """Tests for /auth/status endpoint."""

    def test_auth_status_returns_200(self, client):
        """Auth status endpoint should return 200."""
        response = client.get("/auth/status")
        assert response.status_code == 200

    def test_auth_status_has_auth_enabled_field(self, client):
        """Auth status should have auth_enabled field."""
        response = client.get("/auth/status")
        data = response.json()
        assert "auth_enabled" in data

    def test_auth_status_has_message_field(self, client):
        """Auth status should have message field."""
        response = client.get("/auth/status")
        data = response.json()
        assert "message" in data


class TestGenerateKeyEndpoint:
    """Tests for /auth/generate-key endpoint."""

    def test_generate_key_returns_200(self, client):
        """Generate key endpoint should return 200."""
        response = client.post("/auth/generate-key")
        assert response.status_code == 200

    def test_generate_key_returns_api_key(self, client):
        """Generate key should return an api_key field."""
        response = client.post("/auth/generate-key")
        data = response.json()
        assert "api_key" in data
        assert isinstance(data["api_key"], str)

    def test_generate_key_returns_secure_key(self, client):
        """Generated key should be at least 32 characters."""
        response = client.post("/auth/generate-key")
        data = response.json()
        assert len(data["api_key"]) >= 32

    def test_generate_key_returns_unique_keys(self, client):
        """Each call should return a unique key."""
        response1 = client.post("/auth/generate-key")
        response2 = client.post("/auth/generate-key")

        key1 = response1.json()["api_key"]
        key2 = response2.json()["api_key"]

        assert key1 != key2

    def test_generate_key_has_instructions(self, client):
        """Generate key should return usage instructions."""
        response = client.post("/auth/generate-key")
        data = response.json()
        assert "instructions" in data
        assert isinstance(data["instructions"], list)


class TestExemptEndpoints:
    """Tests for endpoints that don't require authentication."""

    def test_health_endpoint_works(self, client):
        """Health endpoint should always work."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint_works(self, client):
        """Root endpoint should always work."""
        response = client.get("/")
        assert response.status_code == 200

    def test_docs_endpoint_works(self, client):
        """Docs endpoint should always work."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_works(self, client):
        """OpenAPI JSON should always work."""
        response = client.get("/openapi.json")
        assert response.status_code == 200


class TestHealthEndpointAuthInfo:
    """Tests for auth info in health endpoint."""

    def test_health_has_auth_enabled_field(self, client):
        """Health endpoint should have auth_enabled field."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data

    def test_health_auth_enabled_is_boolean(self, client):
        """Health auth_enabled should be a boolean."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["auth_enabled"], bool)
