"""
Hydra Hybrid Search Service

Combines Meilisearch (keyword/BM25) and Qdrant (semantic/vector) search
for superior retrieval quality in RAG applications.
"""

from .hybrid import HybridSearchClient, SearchResult
from .indexer import DocumentIndexer
from .config import SearchConfig

__all__ = [
    "HybridSearchClient",
    "SearchResult",
    "DocumentIndexer",
    "SearchConfig",
]

__version__ = "1.0.0"
