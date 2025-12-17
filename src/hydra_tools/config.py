"""
Hydra Tools Configuration

Central configuration for all Hydra cluster endpoints and credentials.
Override with environment variables for flexibility.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any


# Node definitions for the cluster
NODES: Dict[str, Dict[str, Any]] = {
    "hydra-ai": {
        "ip": "192.168.1.250",
        "user": "typhon",
        "role": "Primary inference (TabbyAPI)",
        "gpus": ["RTX 5090", "RTX 4090"],
    },
    "hydra-compute": {
        "ip": "192.168.1.203",
        "user": "typhon",
        "role": "Ollama, ComfyUI",
        "gpus": ["RTX 5070 Ti", "RTX 5070 Ti"],
    },
    "hydra-storage": {
        "ip": "192.168.1.244",
        "user": "root",
        "role": "Docker services, NFS",
        "gpus": [],
    },
}

# Service definitions
SERVICES: Dict[str, Dict[str, Any]] = {
    "tabbyapi": {"port": 5000, "node": "hydra-ai", "health": "/v1/model"},
    "ollama": {"port": 11434, "node": "hydra-compute", "health": "/"},
    "litellm": {"port": 4000, "node": "hydra-storage", "health": "/health/liveliness"},
    "qdrant": {"port": 6333, "node": "hydra-storage", "health": "/"},
    "postgres": {"port": 5432, "node": "hydra-storage", "health": None},
    "redis": {"port": 6379, "node": "hydra-storage", "health": None},
    "comfyui": {"port": 8188, "node": "hydra-compute", "health": "/"},
    "meilisearch": {"port": 7700, "node": "hydra-storage", "health": "/health"},
    "searxng": {"port": 8888, "node": "hydra-storage", "health": "/"},
    "grafana": {"port": 3003, "node": "hydra-storage", "health": "/api/health"},
    "prometheus": {"port": 9090, "node": "hydra-storage", "health": "/-/healthy"},
}


def get_node_ip(node_name: str) -> str:
    """Get IP address for a node name. Returns input if not found."""
    if node_name in NODES:
        return NODES[node_name]["ip"]
    return node_name


def get_service_url(service_name: str) -> Optional[str]:
    """Get URL for a service. Returns None if not found."""
    if service_name not in SERVICES:
        return None
    svc = SERVICES[service_name]
    node_ip = get_node_ip(svc["node"])
    return f"http://{node_ip}:{svc['port']}"


# Alias for backward compatibility
class ClusterConfig:
    """Configuration for cluster endpoints. Alias for HydraConfig."""

    def __init__(self):
        self.litellm_url = os.getenv("LITELLM_URL", "http://192.168.1.244:4000")
        self.qdrant_url = os.getenv("QDRANT_URL", "http://192.168.1.244:6333")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://192.168.1.203:11434")
        self.tabby_url = os.getenv("TABBY_URL", "http://192.168.1.250:5000")


@dataclass
class HydraConfig:
    """Configuration for Hydra cluster services."""

    # LiteLLM (API Gateway)
    litellm_url: str = "http://192.168.1.244:4000"
    litellm_api_key: str = ""

    # Ollama (Embeddings & Fast Inference)
    ollama_url: str = "http://192.168.1.203:11434"

    # TabbyAPI (Primary Inference)
    tabbyapi_url: str = "http://192.168.1.250:5000"

    # Qdrant (Vector Database)
    qdrant_url: str = "http://192.168.1.244:6333"

    # Meilisearch (Full-text Search)
    meilisearch_url: str = "http://192.168.1.244:7700"
    meilisearch_key: str = ""

    # SearXNG (Web Search)
    searxng_url: str = "http://192.168.1.244:8888"

    # Firecrawl (Web Scraping)
    firecrawl_url: str = "http://192.168.1.244:3005"

    # ComfyUI (Image Generation)
    comfyui_url: str = "http://192.168.1.203:8188"

    # Shared Storage
    shared_path: str = "/mnt/user/hydra_shared"

    # SSH Nodes
    nodes: dict = None

    def __post_init__(self):
        # Load from environment variables
        self.litellm_url = os.getenv("HYDRA_LITELLM_URL", self.litellm_url)
        self.litellm_api_key = os.getenv(
            "HYDRA_LITELLM_KEY", "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7"
        )
        self.ollama_url = os.getenv("HYDRA_OLLAMA_URL", self.ollama_url)
        self.tabbyapi_url = os.getenv("HYDRA_TABBYAPI_URL", self.tabbyapi_url)
        self.qdrant_url = os.getenv("HYDRA_QDRANT_URL", self.qdrant_url)
        self.meilisearch_url = os.getenv("HYDRA_MEILISEARCH_URL", self.meilisearch_url)
        self.meilisearch_key = os.getenv("HYDRA_MEILISEARCH_KEY", self.meilisearch_key)
        self.searxng_url = os.getenv("HYDRA_SEARXNG_URL", self.searxng_url)
        self.firecrawl_url = os.getenv("HYDRA_FIRECRAWL_URL", self.firecrawl_url)
        self.comfyui_url = os.getenv("HYDRA_COMFYUI_URL", self.comfyui_url)
        self.shared_path = os.getenv("HYDRA_SHARED_PATH", self.shared_path)

        # Node configuration
        self.nodes = {
            "hydra-compute": {
                "host": os.getenv("HYDRA_COMPUTE_HOST", "192.168.1.203"),
                "user": "typhon",
            },
            "hydra-ai": {
                "host": os.getenv("HYDRA_AI_HOST", "192.168.1.250"),
                "user": "typhon",
            },
            "hydra-storage": {
                "host": os.getenv("HYDRA_STORAGE_HOST", "192.168.1.244"),
                "user": "root",
            },
        }


# Global configuration instance
config = HydraConfig()


def get_config() -> HydraConfig:
    """Get the global configuration instance."""
    return config
