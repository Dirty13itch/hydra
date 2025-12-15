"""
Tests for hydra_tools.config module
"""

import os
import pytest
from unittest.mock import patch


class TestClusterConfig:
    """Tests for ClusterConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        from hydra_tools.config import ClusterConfig

        config = ClusterConfig()

        assert config.litellm_url == "http://192.168.1.244:4000"
        assert config.qdrant_url == "http://192.168.1.244:6333"
        assert config.ollama_url == "http://192.168.1.203:11434"
        assert config.tabby_url == "http://192.168.1.250:5000"

    def test_env_override(self):
        """Test environment variable overrides."""
        from hydra_tools.config import ClusterConfig

        with patch.dict(os.environ, {
            "LITELLM_URL": "http://custom:4000",
            "QDRANT_URL": "http://custom:6333",
        }):
            config = ClusterConfig()

            assert config.litellm_url == "http://custom:4000"
            assert config.qdrant_url == "http://custom:6333"
            # Non-overridden should keep defaults
            assert config.ollama_url == "http://192.168.1.203:11434"


class TestNodeConfig:
    """Tests for node configuration."""

    def test_nodes_defined(self):
        """Test all nodes are defined."""
        from hydra_tools.config import NODES

        assert "hydra-ai" in NODES
        assert "hydra-compute" in NODES
        assert "hydra-storage" in NODES

    def test_node_properties(self):
        """Test node properties are correct."""
        from hydra_tools.config import NODES

        hydra_ai = NODES["hydra-ai"]
        assert hydra_ai["ip"] == "192.168.1.250"
        assert hydra_ai["user"] == "typhon"
        assert "role" in hydra_ai

    def test_get_node_ip(self):
        """Test getting node IP address."""
        from hydra_tools.config import get_node_ip

        assert get_node_ip("hydra-ai") == "192.168.1.250"
        assert get_node_ip("hydra-storage") == "192.168.1.244"
        # Unknown node returns input
        assert get_node_ip("192.168.1.100") == "192.168.1.100"


class TestServiceConfig:
    """Tests for service configuration."""

    def test_services_defined(self):
        """Test all key services are defined."""
        from hydra_tools.config import SERVICES

        required_services = [
            "tabbyapi",
            "ollama",
            "litellm",
            "qdrant",
            "postgres",
            "redis",
        ]

        for service in required_services:
            assert service in SERVICES, f"Service {service} not defined"

    def test_service_properties(self):
        """Test service properties are present."""
        from hydra_tools.config import SERVICES

        for name, svc in SERVICES.items():
            assert "port" in svc, f"Service {name} missing port"
            assert "node" in svc, f"Service {name} missing node"
            assert isinstance(svc["port"], int), f"Service {name} port not int"

    def test_get_service_url(self):
        """Test getting service URL."""
        from hydra_tools.config import get_service_url

        url = get_service_url("tabbyapi")
        assert url == "http://192.168.1.250:5000"

        url = get_service_url("qdrant")
        assert url == "http://192.168.1.244:6333"

        # Unknown service returns None
        assert get_service_url("nonexistent") is None
