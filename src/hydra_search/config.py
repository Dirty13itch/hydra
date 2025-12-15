"""
Hydra Search Configuration

Central configuration for hybrid search service.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MeilisearchConfig:
    """Meilisearch connection configuration."""

    url: str = "http://192.168.1.244:7700"
    api_key: Optional[str] = None
    timeout: int = 30

    def __post_init__(self):
        self.url = os.getenv("MEILISEARCH_URL", self.url)
        self.api_key = os.getenv("MEILISEARCH_KEY", self.api_key)


@dataclass
class QdrantConfig:
    """Qdrant connection configuration."""

    url: str = "http://192.168.1.244:6333"
    api_key: Optional[str] = None
    timeout: int = 30
    prefer_grpc: bool = False

    def __post_init__(self):
        self.url = os.getenv("QDRANT_URL", self.url)
        self.api_key = os.getenv("QDRANT_API_KEY", self.api_key)


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""

    provider: str = "ollama"  # ollama, openai, sentence-transformers
    model: str = "nomic-embed-text"
    dimensions: int = 768
    ollama_url: str = "http://192.168.1.203:11434"
    batch_size: int = 32

    def __post_init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", self.ollama_url)
        self.model = os.getenv("EMBEDDING_MODEL", self.model)


@dataclass
class SearchConfig:
    """Main search service configuration."""

    # Sub-configurations
    meilisearch: MeilisearchConfig = field(default_factory=MeilisearchConfig)
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # Hybrid search parameters
    default_limit: int = 10
    semantic_weight: float = 0.6  # 0-1, higher = more semantic
    keyword_weight: float = 0.4  # 0-1, higher = more keyword
    min_score: float = 0.3
    rerank: bool = True

    # Collection/Index naming
    default_collection: str = "hydra_docs"
    default_index: str = "hydra_docs"

    # Chunking parameters for indexing
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Searchable attributes for Meilisearch
    searchable_attributes: List[str] = field(
        default_factory=lambda: ["content", "title", "source", "tags"]
    )

    # Filterable attributes for Meilisearch
    filterable_attributes: List[str] = field(
        default_factory=lambda: ["source", "type", "tags", "date"]
    )

    def __post_init__(self):
        # Ensure weights sum to 1.0
        total = self.semantic_weight + self.keyword_weight
        if abs(total - 1.0) > 0.01:
            self.semantic_weight = self.semantic_weight / total
            self.keyword_weight = self.keyword_weight / total


def get_default_config() -> SearchConfig:
    """Get default search configuration."""
    return SearchConfig()


def get_config_from_env() -> SearchConfig:
    """Create configuration from environment variables."""
    config = SearchConfig()

    # Override from environment
    if os.getenv("SEARCH_SEMANTIC_WEIGHT"):
        config.semantic_weight = float(os.getenv("SEARCH_SEMANTIC_WEIGHT"))
    if os.getenv("SEARCH_KEYWORD_WEIGHT"):
        config.keyword_weight = float(os.getenv("SEARCH_KEYWORD_WEIGHT"))
    if os.getenv("SEARCH_MIN_SCORE"):
        config.min_score = float(os.getenv("SEARCH_MIN_SCORE"))
    if os.getenv("SEARCH_DEFAULT_LIMIT"):
        config.default_limit = int(os.getenv("SEARCH_DEFAULT_LIMIT"))

    return config
