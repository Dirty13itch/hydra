"""
Hybrid Search Client

Combines Meilisearch and Qdrant for optimal retrieval.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import httpx

from .config import SearchConfig
from .embeddings import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Unified search result from hybrid search."""

    id: str
    content: str
    score: float
    source: str
    source_type: str  # "semantic", "keyword", or "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Detailed scores
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    combined_score: Optional[float] = None


class HybridSearchClient:
    """
    Hybrid search client combining semantic and keyword search.

    Uses:
    - Qdrant for semantic/vector search (better for conceptual queries)
    - Meilisearch for keyword/BM25 search (better for exact matches)

    Results are combined using Reciprocal Rank Fusion (RRF) or weighted scoring.
    """

    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.embedding_client = EmbeddingClient(self.config.embedding)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def search(
        self,
        query: str,
        collection: Optional[str] = None,
        index: Optional[str] = None,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Perform hybrid search across both backends.

        Args:
            query: Search query text
            collection: Qdrant collection name (default from config)
            index: Meilisearch index name (default from config)
            limit: Maximum results to return
            filters: Optional filters (applied to both backends where possible)
            semantic_weight: Override semantic weight (0-1)
            keyword_weight: Override keyword weight (0-1)

        Returns:
            List of SearchResult objects, sorted by combined score
        """
        collection = collection or self.config.default_collection
        index = index or self.config.default_index
        limit = limit or self.config.default_limit

        sem_weight = semantic_weight or self.config.semantic_weight
        kw_weight = keyword_weight or self.config.keyword_weight

        # Normalize weights
        total = sem_weight + kw_weight
        sem_weight = sem_weight / total
        kw_weight = kw_weight / total

        # Run both searches in parallel
        semantic_task = self._semantic_search(query, collection, limit * 2, filters)
        keyword_task = self._keyword_search(query, index, limit * 2, filters)

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task, return_exceptions=True
        )

        # Handle errors gracefully
        if isinstance(semantic_results, Exception):
            logger.warning(f"Semantic search failed: {semantic_results}")
            semantic_results = []
        if isinstance(keyword_results, Exception):
            logger.warning(f"Keyword search failed: {keyword_results}")
            keyword_results = []

        # Combine results
        combined = self._combine_results(
            semantic_results,
            keyword_results,
            sem_weight,
            kw_weight,
        )

        # Sort by combined score and limit
        combined.sort(key=lambda x: x.combined_score or 0, reverse=True)

        return combined[:limit]

    async def semantic_search(
        self,
        query: str,
        collection: Optional[str] = None,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform semantic-only search via Qdrant."""
        collection = collection or self.config.default_collection
        limit = limit or self.config.default_limit
        return await self._semantic_search(query, collection, limit, filters)

    async def keyword_search(
        self,
        query: str,
        index: Optional[str] = None,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform keyword-only search via Meilisearch."""
        index = index or self.config.default_index
        limit = limit or self.config.default_limit
        return await self._keyword_search(query, index, limit, filters)

    async def _semantic_search(
        self,
        query: str,
        collection: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Execute semantic search via Qdrant."""
        client = await self._get_client()

        # Generate embedding for query
        embedding = await self.embedding_client.embed(query)

        # Build Qdrant search request
        search_params = {
            "vector": embedding,
            "limit": limit,
            "with_payload": True,
        }

        if filters:
            search_params["filter"] = self._build_qdrant_filter(filters)

        try:
            response = await client.post(
                f"{self.config.qdrant.url}/collections/{collection}/points/search",
                json=search_params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for point in data.get("result", []):
                payload = point.get("payload", {})
                results.append(
                    SearchResult(
                        id=str(point.get("id", "")),
                        content=payload.get("content", payload.get("text", "")),
                        score=point.get("score", 0),
                        source=payload.get("source", payload.get("file", "unknown")),
                        source_type="semantic",
                        metadata=payload,
                        semantic_score=point.get("score", 0),
                    )
                )

            return results

        except httpx.HTTPError as e:
            logger.error(f"Qdrant search error: {e}")
            raise

    async def _keyword_search(
        self,
        query: str,
        index: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Execute keyword search via Meilisearch."""
        client = await self._get_client()

        # Build Meilisearch search request
        search_params = {
            "q": query,
            "limit": limit,
            "attributesToRetrieve": ["*"],
            "showRankingScore": True,
        }

        if filters:
            search_params["filter"] = self._build_meilisearch_filter(filters)

        headers = {}
        if self.config.meilisearch.api_key:
            headers["Authorization"] = f"Bearer {self.config.meilisearch.api_key}"

        try:
            response = await client.post(
                f"{self.config.meilisearch.url}/indexes/{index}/search",
                json=search_params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            hits = data.get("hits", [])

            for i, hit in enumerate(hits):
                # Meilisearch returns ranked results; convert to score
                ranking_score = hit.get("_rankingScore", 1 - (i / max(len(hits), 1)))

                results.append(
                    SearchResult(
                        id=str(hit.get("id", hashlib.md5(str(hit).encode()).hexdigest()[:16])),
                        content=hit.get("content", hit.get("text", "")),
                        score=ranking_score,
                        source=hit.get("source", hit.get("title", "unknown")),
                        source_type="keyword",
                        metadata=hit,
                        keyword_score=ranking_score,
                    )
                )

            return results

        except httpx.HTTPError as e:
            logger.error(f"Meilisearch search error: {e}")
            raise

    def _combine_results(
        self,
        semantic: List[SearchResult],
        keyword: List[SearchResult],
        semantic_weight: float,
        keyword_weight: float,
    ) -> List[SearchResult]:
        """
        Combine results from both search backends.

        Uses weighted scoring with deduplication based on content similarity.
        """
        # Create lookup by content hash for deduplication
        combined: Dict[str, SearchResult] = {}

        def content_hash(text: str) -> str:
            """Generate hash for content deduplication."""
            normalized = " ".join(text.lower().split()[:100])
            return hashlib.md5(normalized.encode()).hexdigest()

        # Process semantic results
        for result in semantic:
            h = content_hash(result.content)
            if h not in combined:
                result.combined_score = result.score * semantic_weight
                combined[h] = result
            else:
                # Already seen from keyword search - boost score
                combined[h].semantic_score = result.score
                combined[h].combined_score = (
                    (combined[h].keyword_score or 0) * keyword_weight
                    + result.score * semantic_weight
                )
                combined[h].source_type = "hybrid"

        # Process keyword results
        for result in keyword:
            h = content_hash(result.content)
            if h not in combined:
                result.combined_score = result.score * keyword_weight
                combined[h] = result
            else:
                # Already seen from semantic search - boost score
                if combined[h].keyword_score is None:
                    combined[h].keyword_score = result.score
                    combined[h].combined_score = (
                        (combined[h].semantic_score or 0) * semantic_weight
                        + result.score * keyword_weight
                    )
                    combined[h].source_type = "hybrid"

        return list(combined.values())

    def _build_qdrant_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert generic filters to Qdrant filter format."""
        conditions = []

        for key, value in filters.items():
            if isinstance(value, list):
                # Multiple values = OR condition
                conditions.append({
                    "should": [
                        {"key": key, "match": {"value": v}} for v in value
                    ]
                })
            else:
                conditions.append({"key": key, "match": {"value": value}})

        if len(conditions) == 1:
            return {"must": conditions}

        return {"must": conditions}

    def _build_meilisearch_filter(self, filters: Dict[str, Any]) -> str:
        """Convert generic filters to Meilisearch filter string."""
        parts = []

        for key, value in filters.items():
            if isinstance(value, list):
                # Multiple values = OR condition
                or_parts = [f'{key} = "{v}"' for v in value]
                parts.append(f"({' OR '.join(or_parts)})")
            else:
                parts.append(f'{key} = "{value}"')

        return " AND ".join(parts)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Synchronous wrapper for non-async code
class HybridSearchClientSync:
    """Synchronous wrapper for HybridSearchClient."""

    def __init__(self, config: Optional[SearchConfig] = None):
        self._async_client = HybridSearchClient(config)

    def search(self, *args, **kwargs) -> List[SearchResult]:
        return asyncio.run(self._async_client.search(*args, **kwargs))

    def semantic_search(self, *args, **kwargs) -> List[SearchResult]:
        return asyncio.run(self._async_client.semantic_search(*args, **kwargs))

    def keyword_search(self, *args, **kwargs) -> List[SearchResult]:
        return asyncio.run(self._async_client.keyword_search(*args, **kwargs))

    def close(self):
        asyncio.run(self._async_client.close())
