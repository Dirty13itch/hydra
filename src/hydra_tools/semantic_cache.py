"""
Hydra Semantic Cache - LLM Response Caching with Semantic Similarity

Caches LLM responses and retrieves them when semantically similar queries arrive.
Expected 30-50% reduction in redundant inference costs.

Features:
- Qdrant vector storage for query embeddings
- Configurable similarity threshold (default 0.95)
- TTL-based expiration
- Prometheus metrics for hit/miss tracking
- Support for different models and contexts

Architecture:
- Query → Embedding → Qdrant search
- If match above threshold → Return cached response
- If no match → Call LLM → Cache response → Return

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

CACHE_HITS = Counter(
    "hydra_semantic_cache_hits_total",
    "Total semantic cache hits",
    ["model", "cache_type"]
)

CACHE_MISSES = Counter(
    "hydra_semantic_cache_misses_total",
    "Total semantic cache misses",
    ["model", "reason"]
)

CACHE_LATENCY = Histogram(
    "hydra_semantic_cache_latency_seconds",
    "Semantic cache lookup latency",
    ["operation"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

CACHE_SIZE = Gauge(
    "hydra_semantic_cache_entries",
    "Number of entries in semantic cache"
)

CACHE_SAVINGS = Counter(
    "hydra_semantic_cache_tokens_saved_total",
    "Total tokens saved by cache hits",
    ["model"]
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CacheEntry:
    """A cached LLM response."""
    id: str
    query_hash: str
    query: str
    response: str
    model: str
    embedding: List[float]
    created_at: str
    expires_at: str
    hit_count: int = 0
    last_hit: Optional[str] = None
    tokens_saved: int = 0
    context_hash: Optional[str] = None  # For context-aware caching
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        return cls(**data)


class CacheConfig:
    """Configuration for semantic cache."""

    def __init__(
        self,
        qdrant_url: str = "http://192.168.1.244:6333",
        collection_name: str = "llm_cache",
        embedding_url: str = "http://192.168.1.203:11434/api/embeddings",
        embedding_model: str = "nomic-embed-text",
        similarity_threshold: float = 0.92,  # Lower threshold for nomic
        ttl_hours: int = 24,
        max_entries: int = 100000,
        embedding_dim: int = 768,  # nomic-embed-text dimension
        use_ollama: bool = True,  # Use Ollama API format
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_url = embedding_url
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self.max_entries = max_entries
        self.embedding_dim = embedding_dim
        self.use_ollama = use_ollama


# =============================================================================
# Semantic Cache Implementation
# =============================================================================

class SemanticCache:
    """
    Semantic cache for LLM responses.

    Uses Qdrant for vector storage and similarity search.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._initialized = False
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        """Initialize the cache (create collection if needed)."""
        if self._initialized:
            return True

        self._client = httpx.AsyncClient(timeout=30.0)

        try:
            # Check if collection exists
            resp = await self._client.get(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}"
            )

            if resp.status_code == 404:
                # Create collection
                await self._create_collection()
            elif resp.status_code != 200:
                logger.error(f"Failed to check collection: {resp.text}")
                return False

            self._initialized = True
            logger.info(f"Semantic cache initialized: {self.config.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize semantic cache: {e}")
            return False

    async def _create_collection(self):
        """Create the Qdrant collection."""
        resp = await self._client.put(
            f"{self.config.qdrant_url}/collections/{self.config.collection_name}",
            json={
                "vectors": {
                    "size": self.config.embedding_dim,
                    "distance": "Cosine"
                },
                "optimizers_config": {
                    "indexing_threshold": 20000
                },
                "on_disk_payload": True
            }
        )
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create collection: {resp.text}")
        logger.info(f"Created Qdrant collection: {self.config.collection_name}")

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Ollama or OpenAI-compatible API."""
        start = time.time()
        try:
            if self.config.use_ollama:
                # Ollama API format
                resp = await self._client.post(
                    self.config.embedding_url,
                    json={
                        "model": self.config.embedding_model,
                        "prompt": text[:8000]  # Truncate to avoid token limits
                    }
                )

                CACHE_LATENCY.labels(operation="embedding").observe(time.time() - start)

                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("embedding")
                else:
                    logger.warning(f"Ollama embedding error: {resp.status_code}")
                    return None
            else:
                # OpenAI-compatible API format
                resp = await self._client.post(
                    self.config.embedding_url,
                    json={
                        "model": self.config.embedding_model,
                        "input": text[:8000]
                    },
                    headers={"Authorization": "Bearer sk-hydra-master-key"}
                )

                CACHE_LATENCY.labels(operation="embedding").observe(time.time() - start)

                if resp.status_code == 200:
                    data = resp.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.warning(f"Embedding API error: {resp.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    async def lookup(
        self,
        query: str,
        model: str,
        context_hash: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Look up a cached response for a query.

        Args:
            query: The query to look up
            model: The model name (for filtering)
            context_hash: Optional hash of conversation context

        Returns:
            Tuple of (cached_response, similarity_score) or None
        """
        if not self._initialized:
            await self.initialize()

        start = time.time()

        try:
            # Get query embedding
            embedding = await self.get_embedding(query)
            if not embedding:
                CACHE_MISSES.labels(model=model, reason="embedding_failed").inc()
                return None

            # Build filter
            filter_conditions = [
                {"key": "model", "match": {"value": model}},
                {"key": "expires_at", "range": {"gt": datetime.utcnow().isoformat()}}
            ]

            if context_hash:
                filter_conditions.append(
                    {"key": "context_hash", "match": {"value": context_hash}}
                )

            # Search Qdrant
            resp = await self._client.post(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}/points/search",
                json={
                    "vector": embedding,
                    "limit": 1,
                    "with_payload": True,
                    "score_threshold": self.config.similarity_threshold,
                    "filter": {
                        "must": filter_conditions
                    }
                }
            )

            CACHE_LATENCY.labels(operation="lookup").observe(time.time() - start)

            if resp.status_code != 200:
                logger.warning(f"Qdrant search error: {resp.status_code}")
                CACHE_MISSES.labels(model=model, reason="search_failed").inc()
                return None

            results = resp.json().get("result", [])

            if not results:
                CACHE_MISSES.labels(model=model, reason="no_match").inc()
                return None

            # Found a match!
            best_match = results[0]
            score = best_match["score"]
            payload = best_match["payload"]

            if score >= self.config.similarity_threshold:
                # Update hit count
                await self._update_hit_count(best_match["id"], payload)

                CACHE_HITS.labels(model=model, cache_type="semantic").inc()
                CACHE_SAVINGS.labels(model=model).inc(payload.get("tokens_saved", 100))

                logger.info(f"Cache HIT for model={model}, score={score:.4f}")
                return (payload["response"], score)

            CACHE_MISSES.labels(model=model, reason="below_threshold").inc()
            return None

        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            CACHE_MISSES.labels(model=model, reason="error").inc()
            return None

    async def _update_hit_count(self, point_id: int, payload: Dict):
        """Update hit count and last_hit timestamp."""
        try:
            await self._client.post(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}/points/payload",
                json={
                    "points": [point_id],
                    "payload": {
                        "hit_count": payload.get("hit_count", 0) + 1,
                        "last_hit": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update hit count: {e}")

    async def store(
        self,
        query: str,
        response: str,
        model: str,
        tokens_used: int = 0,
        context_hash: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store a query-response pair in the cache.

        Args:
            query: The query text
            response: The LLM response
            model: The model name
            tokens_used: Number of tokens used (for savings tracking)
            context_hash: Optional hash of conversation context
            metadata: Optional additional metadata

        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()

        start = time.time()

        try:
            # Get embedding
            embedding = await self.get_embedding(query)
            if not embedding:
                return False

            # Generate IDs
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            point_id = int(hashlib.sha256(f"{query_hash}_{model}".encode()).hexdigest()[:8], 16)

            now = datetime.utcnow()
            expires = now + timedelta(hours=self.config.ttl_hours)

            # Create entry
            entry = CacheEntry(
                id=str(point_id),
                query_hash=query_hash,
                query=query[:1000],  # Truncate for storage
                response=response,
                model=model,
                embedding=embedding,
                created_at=now.isoformat(),
                expires_at=expires.isoformat(),
                tokens_saved=tokens_used,
                context_hash=context_hash,
                metadata=metadata or {}
            )

            # Upsert to Qdrant
            resp = await self._client.put(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}/points",
                json={
                    "points": [{
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "id": entry.id,
                            "query_hash": entry.query_hash,
                            "query": entry.query,
                            "response": entry.response,
                            "model": entry.model,
                            "created_at": entry.created_at,
                            "expires_at": entry.expires_at,
                            "hit_count": 0,
                            "tokens_saved": entry.tokens_saved,
                            "context_hash": entry.context_hash,
                            "metadata": entry.metadata
                        }
                    }]
                }
            )

            CACHE_LATENCY.labels(operation="store").observe(time.time() - start)

            if resp.status_code in [200, 201]:
                logger.debug(f"Cached response for model={model}")
                return True
            else:
                logger.warning(f"Failed to cache: {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            resp = await self._client.get(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}"
            )

            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", {})
                count = result.get("points_count", 0)
                CACHE_SIZE.set(count)

                return {
                    "entries": count,
                    "indexed_vectors": result.get("indexed_vectors_count", 0),
                    "collection": self.config.collection_name,
                    "similarity_threshold": self.config.similarity_threshold,
                    "ttl_hours": self.config.ttl_hours,
                    "status": result.get("status", "unknown")
                }

            return {"error": f"Failed to get stats: {resp.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    async def cleanup_expired(self) -> int:
        """Remove expired entries from the cache."""
        if not self._initialized:
            await self.initialize()

        try:
            # Delete entries where expires_at < now
            now = datetime.utcnow().isoformat()

            resp = await self._client.post(
                f"{self.config.qdrant_url}/collections/{self.config.collection_name}/points/delete",
                json={
                    "filter": {
                        "must": [{
                            "key": "expires_at",
                            "range": {"lt": now}
                        }]
                    }
                }
            )

            if resp.status_code == 200:
                result = resp.json().get("result", {})
                deleted = result.get("deleted", 0)
                logger.info(f"Cleaned up {deleted} expired cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()


# =============================================================================
# Global Instance and Helper Functions
# =============================================================================

_cache_instance: Optional[SemanticCache] = None


def get_cache() -> SemanticCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance


async def cached_completion(
    query: str,
    model: str,
    completion_func,
    context_hash: Optional[str] = None,
    bypass_cache: bool = False,
    **kwargs
) -> Tuple[str, bool]:
    """
    Wrapper for LLM completions with semantic caching.

    Args:
        query: The query/prompt
        model: Model name
        completion_func: Async function to call if cache miss
        context_hash: Optional context hash for context-aware caching
        bypass_cache: If True, skip cache lookup
        **kwargs: Additional args for completion_func

    Returns:
        Tuple of (response, was_cached)
    """
    cache = get_cache()

    # Try cache lookup first
    if not bypass_cache:
        result = await cache.lookup(query, model, context_hash)
        if result:
            return (result[0], True)

    # Cache miss - call the completion function
    response = await completion_func(query, model, **kwargs)

    # Store in cache for future use
    # Estimate tokens (rough: 4 chars per token)
    tokens_estimate = len(query) // 4 + len(response) // 4
    await cache.store(query, response, model, tokens_estimate, context_hash)

    return (response, False)


# =============================================================================
# FastAPI Router
# =============================================================================

def create_semantic_cache_router():
    """Create FastAPI router for semantic cache endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/cache", tags=["semantic-cache"])

    class CacheLookupRequest(BaseModel):
        query: str
        model: str
        context_hash: Optional[str] = None

    class CacheStoreRequest(BaseModel):
        query: str
        response: str
        model: str
        tokens_used: int = 0
        context_hash: Optional[str] = None

    @router.get("/status")
    async def cache_status():
        """Get semantic cache status and statistics."""
        cache = get_cache()
        return await cache.get_stats()

    @router.post("/lookup")
    async def cache_lookup(request: CacheLookupRequest):
        """
        Look up a query in the semantic cache.

        Returns cached response if found with similarity above threshold.
        """
        cache = get_cache()
        result = await cache.lookup(
            request.query,
            request.model,
            request.context_hash
        )

        if result:
            return {
                "cached": True,
                "response": result[0],
                "similarity": result[1]
            }

        return {"cached": False}

    @router.post("/store")
    async def cache_store(request: CacheStoreRequest):
        """Store a query-response pair in the cache."""
        cache = get_cache()
        success = await cache.store(
            request.query,
            request.response,
            request.model,
            request.tokens_used,
            request.context_hash
        )

        return {"stored": success}

    @router.post("/cleanup")
    async def cache_cleanup():
        """Remove expired entries from the cache."""
        cache = get_cache()
        deleted = await cache.cleanup_expired()
        return {"deleted": deleted}

    @router.get("/config")
    async def cache_config():
        """Get current cache configuration."""
        cache = get_cache()
        config = cache.config
        return {
            "collection": config.collection_name,
            "similarity_threshold": config.similarity_threshold,
            "ttl_hours": config.ttl_hours,
            "max_entries": config.max_entries,
            "embedding_model": config.embedding_model
        }

    @router.post("/initialize")
    async def cache_initialize():
        """Initialize the semantic cache (create collection if needed)."""
        cache = get_cache()
        success = await cache.initialize()
        return {"initialized": success}

    return router
