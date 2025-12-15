"""
Pytest configuration and fixtures for Hydra cluster tests
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_env():
    """Fixture to set up mock environment variables."""
    original_env = os.environ.copy()

    os.environ.update({
        "LITELLM_URL": "http://test-litellm:4000",
        "QDRANT_URL": "http://test-qdrant:6333",
        "MEILISEARCH_URL": "http://test-meili:7700",
        "OLLAMA_URL": "http://test-ollama:11434",
        "TABBY_URL": "http://test-tabby:5000",
    })

    yield os.environ

    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_httpx_client():
    """Fixture for mocked httpx client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_async_httpx_client():
    """Fixture for mocked async httpx client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_health_response():
    """Sample health check response data."""
    return {
        "summary": {
            "status": "healthy",
            "healthy": 15,
            "unhealthy": 0,
            "degraded": 1,
            "unknown": 0,
            "total": 16,
            "critical_down": [],
            "timestamp": "2025-12-13T10:00:00Z",
        },
        "services": [
            {
                "service": "TabbyAPI",
                "status": "healthy",
                "latency_ms": 12.5,
                "node": "hydra-ai",
                "category": "inference",
                "critical": True,
            }
        ],
        "nodes": {
            "hydra-ai": {"healthy": 2, "unhealthy": 0, "total": 2},
        },
        "categories": {
            "inference": {"healthy": 4, "unhealthy": 0, "total": 4},
        },
    }


@pytest.fixture
def sample_qdrant_response():
    """Sample Qdrant search response."""
    return {
        "result": [
            {
                "id": "doc_1",
                "score": 0.95,
                "payload": {
                    "content": "Sample document content",
                    "source": "docs/test.md",
                    "category": "test",
                },
            },
            {
                "id": "doc_2",
                "score": 0.82,
                "payload": {
                    "content": "Another document",
                    "source": "docs/other.md",
                    "category": "test",
                },
            },
        ],
        "status": "ok",
        "time": 0.015,
    }


@pytest.fixture
def sample_ollama_models():
    """Sample Ollama model list."""
    return {
        "models": [
            {
                "name": "llama3.1:8b",
                "size": 4661224528,
                "modified_at": "2025-12-10T10:00:00Z",
            },
            {
                "name": "qwen2.5:7b",
                "size": 4354631680,
                "modified_at": "2025-12-09T08:00:00Z",
            },
        ]
    }


@pytest.fixture
def sample_gpu_output():
    """Sample nvidia-smi output."""
    return """0, NVIDIA GeForce RTX 5090, 28000 MiB, 32768 MiB, 320.50 W, 65
1, NVIDIA GeForce RTX 4090, 18000 MiB, 24576 MiB, 280.00 W, 62"""


# Markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
