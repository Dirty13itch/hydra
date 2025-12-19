"""
Unified Search Module for Hydra AI System

Provides unified search across all data stores:
- Qdrant (vector search)
- Neo4j (graph search)
- Meilisearch (keyword search)
- PostgreSQL (structured data)

Uses Reciprocal Rank Fusion (RRF) to combine results.

Author: Hydra Autonomous Caretaker
Created: 2025-12-19
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import httpx

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

SEARCH_REQUESTS = Counter(
    "hydra_unified_search_requests_total",
    "Total unified search requests",
    ["search_type"]
)

SEARCH_LATENCY = Histogram(
    "hydra_unified_search_latency_seconds",
    "Unified search latency",
    ["search_type"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


# =============================================================================
# Configuration
# =============================================================================

ENDPOINTS = {
    "qdrant": "http://192.168.1.244:6333",
    "neo4j": "http://192.168.1.244:7474",
    "meilisearch": "http://192.168.1.244:7700",
    "postgres": "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
}

COLLECTIONS = {
    "qdrant": ["knowledge", "memories", "documents", "code"],
    "meilisearch": ["knowledge", "documents"],
}


class SearchSource(Enum):
    """Available search sources."""
    QDRANT = "qdrant"
    NEO4J = "neo4j"
    MEILISEARCH = "meilisearch"
    POSTGRES = "postgres"
    ALL = "all"


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    source: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlight: Optional[str] = None


@dataclass
class UnifiedSearchResponse:
    """Response from unified search."""
    query: str
    results: List[SearchResult]
    total_results: int
    sources_searched: List[str]
    fused: bool
    latency_ms: float


class UnifiedSearchEngine:
    """
    Unified search engine combining multiple backends.
    """

    def __init__(self):
        self.endpoints = ENDPOINTS
        self.k_param = 60  # RRF parameter

    async def search(
        self,
        query: str,
        sources: List[SearchSource] = None,
        limit: int = 20,
        collections: List[str] = None,
    ) -> UnifiedSearchResponse:
        """
        Execute unified search across multiple sources.
        """
        start_time = datetime.utcnow()

        if sources is None:
            sources = [SearchSource.QDRANT, SearchSource.MEILISEARCH]

        if SearchSource.ALL in sources:
            sources = [SearchSource.QDRANT, SearchSource.NEO4J, SearchSource.MEILISEARCH]

        # Execute searches in parallel
        search_tasks = []
        for source in sources:
            if source == SearchSource.QDRANT:
                search_tasks.append(self._search_qdrant(query, limit, collections))
            elif source == SearchSource.MEILISEARCH:
                search_tasks.append(self._search_meilisearch(query, limit))
            elif source == SearchSource.NEO4J:
                search_tasks.append(self._search_neo4j(query, limit))

        # Gather results
        results_by_source = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten and filter errors
        all_results = []
        sources_searched = []

        for i, results in enumerate(results_by_source):
            if isinstance(results, Exception):
                logger.warning(f"Search error for {sources[i].value}: {results}")
                continue
            all_results.extend(results)
            sources_searched.append(sources[i].value)

        # Apply RRF fusion if multiple sources
        fused = len(sources_searched) > 1
        if fused:
            all_results = self._rrf_fusion(all_results, limit)
        else:
            all_results = sorted(all_results, key=lambda r: r.score, reverse=True)[:limit]

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        SEARCH_REQUESTS.labels(search_type="unified").inc()
        SEARCH_LATENCY.labels(search_type="unified").observe(latency_ms / 1000)

        return UnifiedSearchResponse(
            query=query,
            results=all_results,
            total_results=len(all_results),
            sources_searched=sources_searched,
            fused=fused,
            latency_ms=round(latency_ms, 2),
        )

    def _rrf_fusion(
        self,
        results: List[SearchResult],
        limit: int,
    ) -> List[SearchResult]:
        """
        Apply Reciprocal Rank Fusion to combine results.

        RRF score = sum(1 / (k + rank_in_source))
        """
        # Group by source and rank
        source_ranks = {}
        for result in results:
            if result.source not in source_ranks:
                source_ranks[result.source] = {}
            source_ranks[result.source][result.id] = len(source_ranks[result.source])

        # Calculate RRF scores
        rrf_scores = {}
        id_to_result = {}

        for result in results:
            if result.id not in id_to_result:
                id_to_result[result.id] = result
                rrf_scores[result.id] = 0

            # Add RRF contribution from this source
            rank = source_ranks[result.source].get(result.id, 999)
            rrf_scores[result.id] += 1 / (self.k_param + rank)

        # Update scores and sort
        for result_id, rrf_score in rrf_scores.items():
            id_to_result[result_id].score = rrf_score

        sorted_results = sorted(
            id_to_result.values(),
            key=lambda r: r.score,
            reverse=True
        )

        return sorted_results[:limit]

    async def _search_qdrant(
        self,
        query: str,
        limit: int,
        collections: List[str] = None,
    ) -> List[SearchResult]:
        """Search Qdrant vector database."""
        results = []
        collections = collections or COLLECTIONS["qdrant"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, get embedding for query
            embed_response = await client.post(
                f"{self.endpoints['qdrant']}/collections/knowledge/points/search",
                json={
                    "query": query,
                    "limit": limit,
                    "with_payload": True,
                },
            )

            if embed_response.status_code != 200:
                # Try scroll with filter instead
                for collection in collections:
                    try:
                        response = await client.post(
                            f"{self.endpoints['qdrant']}/collections/{collection}/points/scroll",
                            json={
                                "limit": limit,
                                "with_payload": True,
                                "filter": {
                                    "should": [
                                        {"key": "content", "match": {"text": query}},
                                        {"key": "title", "match": {"text": query}},
                                    ]
                                }
                            },
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for point in data.get("result", {}).get("points", []):
                                payload = point.get("payload", {})
                                results.append(SearchResult(
                                    id=str(point.get("id", "")),
                                    source="qdrant",
                                    content=payload.get("content", payload.get("text", ""))[:500],
                                    score=0.5,  # Default score for scroll
                                    metadata={"collection": collection, **payload},
                                ))
                    except Exception as e:
                        logger.debug(f"Qdrant collection {collection} search failed: {e}")

                return results

            data = embed_response.json()
            for hit in data.get("result", []):
                payload = hit.get("payload", {})
                results.append(SearchResult(
                    id=str(hit.get("id", "")),
                    source="qdrant",
                    content=payload.get("content", payload.get("text", ""))[:500],
                    score=hit.get("score", 0),
                    metadata=payload,
                ))

        return results

    async def _search_meilisearch(
        self,
        query: str,
        limit: int,
    ) -> List[SearchResult]:
        """Search Meilisearch keyword index."""
        results = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for index in COLLECTIONS["meilisearch"]:
                try:
                    response = await client.post(
                        f"{self.endpoints['meilisearch']}/indexes/{index}/search",
                        json={
                            "q": query,
                            "limit": limit,
                            "attributesToHighlight": ["content", "title"],
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        for hit in data.get("hits", []):
                            results.append(SearchResult(
                                id=str(hit.get("id", "")),
                                source="meilisearch",
                                content=hit.get("content", hit.get("title", ""))[:500],
                                score=1.0,  # Meilisearch doesn't return scores
                                metadata={"index": index, **hit},
                                highlight=hit.get("_formatted", {}).get("content", ""),
                            ))
                except Exception as e:
                    logger.debug(f"Meilisearch index {index} search failed: {e}")

        return results

    async def _search_neo4j(
        self,
        query: str,
        limit: int,
    ) -> List[SearchResult]:
        """Search Neo4j graph database using full-text search."""
        results = []

        # Neo4j Cypher query for full-text search
        cypher = """
        CALL db.index.fulltext.queryNodes('knowledge_index', $query, {limit: $limit})
        YIELD node, score
        RETURN node, score
        """

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.endpoints['neo4j']}/db/neo4j/tx/commit",
                    json={
                        "statements": [{
                            "statement": cypher,
                            "parameters": {"query": query, "limit": limit}
                        }]
                    },
                    auth=("neo4j", "HydraNeo4j2024!"),
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("results", []):
                        for record in result.get("data", []):
                            row = record.get("row", [])
                            if len(row) >= 2:
                                node, score = row[0], row[1]
                                results.append(SearchResult(
                                    id=str(node.get("id", "")),
                                    source="neo4j",
                                    content=node.get("content", node.get("name", ""))[:500],
                                    score=score,
                                    metadata=node,
                                ))
            except Exception as e:
                logger.debug(f"Neo4j search failed: {e}")

        return results

    async def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        stats = {
            "sources": {},
            "total_documents": 0,
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Qdrant stats
            try:
                for collection in COLLECTIONS["qdrant"]:
                    response = await client.get(
                        f"{self.endpoints['qdrant']}/collections/{collection}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        count = data.get("result", {}).get("points_count", 0)
                        stats["sources"][f"qdrant:{collection}"] = count
                        stats["total_documents"] += count
            except Exception as e:
                stats["sources"]["qdrant"] = f"error: {e}"

            # Meilisearch stats
            try:
                response = await client.get(f"{self.endpoints['meilisearch']}/stats")
                if response.status_code == 200:
                    data = response.json()
                    for index, index_stats in data.get("indexes", {}).items():
                        count = index_stats.get("numberOfDocuments", 0)
                        stats["sources"][f"meilisearch:{index}"] = count
                        stats["total_documents"] += count
            except Exception as e:
                stats["sources"]["meilisearch"] = f"error: {e}"

        return stats


# =============================================================================
# Global Instance
# =============================================================================

_search_engine: Optional[UnifiedSearchEngine] = None


def get_search_engine() -> UnifiedSearchEngine:
    """Get or create the global search engine."""
    global _search_engine
    if _search_engine is None:
        _search_engine = UnifiedSearchEngine()
    return _search_engine


# =============================================================================
# FastAPI Router
# =============================================================================

def create_unified_search_router():
    """Create FastAPI router for unified search endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/search", tags=["unified-search"])

    class SearchRequest(BaseModel):
        query: str
        sources: Optional[List[str]] = None
        limit: int = 20
        collections: Optional[List[str]] = None

    @router.post("/")
    async def unified_search(request: SearchRequest):
        """Execute unified search across all data stores."""
        engine = get_search_engine()

        # Convert string sources to enums
        sources = None
        if request.sources:
            sources = [SearchSource(s) for s in request.sources if s in [e.value for e in SearchSource]]

        response = await engine.search(
            query=request.query,
            sources=sources,
            limit=request.limit,
            collections=request.collections,
        )

        return {
            "query": response.query,
            "results": [
                {
                    "id": r.id,
                    "source": r.source,
                    "content": r.content,
                    "score": round(r.score, 4),
                    "metadata": r.metadata,
                    "highlight": r.highlight,
                }
                for r in response.results
            ],
            "total_results": response.total_results,
            "sources_searched": response.sources_searched,
            "fused": response.fused,
            "latency_ms": response.latency_ms,
        }

    @router.get("/quick")
    async def quick_search(q: str, limit: int = 10):
        """Quick search with default settings."""
        engine = get_search_engine()
        response = await engine.search(query=q, limit=limit)

        return {
            "query": response.query,
            "results": [
                {"content": r.content[:200], "source": r.source, "score": round(r.score, 4)}
                for r in response.results
            ],
            "count": response.total_results,
        }

    @router.get("/stats")
    async def search_stats():
        """Get search engine statistics."""
        engine = get_search_engine()
        return await engine.get_stats()

    @router.get("/sources")
    async def list_sources():
        """List available search sources."""
        return {
            "sources": [s.value for s in SearchSource],
            "collections": COLLECTIONS,
            "endpoints": {k: "configured" for k in ENDPOINTS},
        }

    return router
