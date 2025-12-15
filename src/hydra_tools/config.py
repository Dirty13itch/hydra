"""
Hydra Tools Configuration

Central configuration for all Hydra cluster endpoints and credentials.
Override with environment variables for flexibility.
"""

import os
from dataclasses import dataclass
from typing import Optional


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
