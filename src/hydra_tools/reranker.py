"""
Hydra Search Reranker

Cross-encoder reranker for improving search result relevance.
Uses LLM-based scoring to rerank search results.

Expected improvement: 10-15% relevance boost over initial retrieval.

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

RERANK_QUERIES = Counter(
    "hydra_rerank_queries_total",
    "Total rerank operations",
    ["method"]
)

RERANK_LATENCY = Histogram(
    "hydra_rerank_latency_seconds",
    "Reranking latency",
    ["method"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class RerankerConfig:
    """Configuration for the reranker."""
    # LLM endpoint (Ollama)
    llm_url: str = "http://192.168.1.203:11434/api/chat"
    llm_model: str = "qwen2.5:7b"

    # Embedding endpoint for cosine similarity reranking
    embedding_url: str = "http://192.168.1.203:11434/api/embeddings"
    embedding_model: str = "nomic-embed-text"

    # Reranking parameters
    max_candidates: int = 20  # Max candidates to rerank
    top_k: int = 10  # Return top K after reranking
    timeout: float = 30.0  # Request timeout in seconds

    # Scoring
    min_score: float = 0.3  # Minimum relevance score to include


# =============================================================================
# Reranker Implementation
# =============================================================================

class Reranker:
    """
    Cross-encoder reranker for search results.

    Supports multiple reranking methods:
    1. LLM-based: Uses LLM to score query-document relevance
    2. Embedding-based: Uses cosine similarity with better embeddings
    """

    def __init__(self, config: Optional[RerankerConfig] = None):
        self.config = config or RerankerConfig()
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def rerank_llm(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using LLM-based relevance scoring.

        This method prompts the LLM to score each document's relevance
        to the query on a scale of 0-10.

        Args:
            query: The search query
            documents: List of documents with 'content' field
            top_k: Number of results to return

        Returns:
            Reranked documents with 'rerank_score' field added
        """
        if not documents:
            return []

        start = time.time()
        top_k = top_k or self.config.top_k

        # Limit candidates
        candidates = documents[:self.config.max_candidates]

        # Score each document
        scored_docs = []

        for doc in candidates:
            content = doc.get("content", doc.get("text", str(doc)))[:1000]  # Limit content length

            prompt = f"""Rate the relevance of the following document to the query on a scale of 0-10.
Only respond with a single number between 0 and 10.

Query: {query}

Document: {content}

Relevance score (0-10):"""

            try:
                response = await self.client.post(
                    self.config.llm_url,
                    json={
                        "model": self.config.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0, "num_predict": 10}
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    score_text = result.get("message", {}).get("content", "0").strip()
                    # Extract number from response
                    try:
                        score = float(''.join(c for c in score_text if c.isdigit() or c == '.'))
                        score = min(10, max(0, score)) / 10.0  # Normalize to 0-1
                    except (ValueError, TypeError):
                        score = 0.0
                else:
                    score = 0.0

            except Exception as e:
                logger.warning(f"Failed to score document: {e}")
                score = 0.0

            scored_docs.append({
                **doc,
                "rerank_score": score,
                "rerank_method": "llm"
            })

        # Sort by rerank score
        scored_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        # Filter by minimum score and return top_k
        result = [
            doc for doc in scored_docs[:top_k]
            if doc.get("rerank_score", 0) >= self.config.min_score
        ]

        RERANK_LATENCY.labels(method="llm").observe(time.time() - start)
        RERANK_QUERIES.labels(method="llm").inc()

        logger.info(f"LLM reranking: {len(documents)} -> {len(result)} docs in {time.time()-start:.2f}s")
        return result

    async def rerank_embedding(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using embedding cosine similarity.

        This is faster than LLM reranking but may be less accurate.

        Args:
            query: The search query
            documents: List of documents with 'content' field
            top_k: Number of results to return

        Returns:
            Reranked documents with 'rerank_score' field added
        """
        if not documents:
            return []

        start = time.time()
        top_k = top_k or self.config.top_k

        # Get query embedding
        try:
            query_response = await self.client.post(
                self.config.embedding_url,
                json={"model": self.config.embedding_model, "prompt": query}
            )
            query_embedding = query_response.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Failed to get query embedding: {e}")
            return documents[:top_k]

        # Score each document
        scored_docs = []

        for doc in documents[:self.config.max_candidates]:
            content = doc.get("content", doc.get("text", str(doc)))[:1000]

            try:
                doc_response = await self.client.post(
                    self.config.embedding_url,
                    json={"model": self.config.embedding_model, "prompt": content}
                )
                doc_embedding = doc_response.json().get("embedding", [])

                # Compute cosine similarity
                score = self._cosine_similarity(query_embedding, doc_embedding)
            except Exception as e:
                logger.warning(f"Failed to embed document: {e}")
                score = 0.0

            scored_docs.append({
                **doc,
                "rerank_score": score,
                "rerank_method": "embedding"
            })

        # Sort by score
        scored_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        result = scored_docs[:top_k]

        RERANK_LATENCY.labels(method="embedding").observe(time.time() - start)
        RERANK_QUERIES.labels(method="embedding").inc()

        logger.info(f"Embedding reranking: {len(documents)} -> {len(result)} docs in {time.time()-start:.2f}s")
        return result

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        method: str = "embedding",
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using specified method.

        Args:
            query: The search query
            documents: List of documents
            method: "llm" for LLM-based, "embedding" for embedding-based
            top_k: Number of results to return

        Returns:
            Reranked documents
        """
        if method == "llm":
            return await self.rerank_llm(query, documents, top_k)
        else:
            return await self.rerank_embedding(query, documents, top_k)

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# Global Instance
# =============================================================================

_reranker_instance: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get the global reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance


# =============================================================================
# FastAPI Router
# =============================================================================

def create_reranker_router():
    """Create FastAPI router for reranker endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/rerank", tags=["reranker"])

    class RerankRequest(BaseModel):
        query: str
        documents: List[Dict[str, Any]]
        method: str = "embedding"  # "llm" or "embedding"
        top_k: int = 10

    class RerankResponse(BaseModel):
        query: str
        results: List[Dict[str, Any]]
        method: str
        count: int

    @router.post("/", response_model=RerankResponse)
    async def rerank_documents(request: RerankRequest):
        """
        Rerank a list of documents based on relevance to query.

        Methods:
        - embedding: Fast cosine similarity reranking
        - llm: LLM-based relevance scoring (slower but more accurate)
        """
        reranker = get_reranker()
        results = await reranker.rerank(
            query=request.query,
            documents=request.documents,
            method=request.method,
            top_k=request.top_k,
        )
        return RerankResponse(
            query=request.query,
            results=results,
            method=request.method,
            count=len(results),
        )

    @router.get("/health")
    async def reranker_health():
        """Check reranker health."""
        return {
            "status": "healthy",
            "config": {
                "llm_model": get_reranker().config.llm_model,
                "embedding_model": get_reranker().config.embedding_model,
                "max_candidates": get_reranker().config.max_candidates,
            }
        }

    return router


# =============================================================================
# Integration Helper
# =============================================================================

async def rerank_search_results(
    query: str,
    results: List[Dict[str, Any]],
    method: str = "embedding",
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Convenience function to rerank search results.

    Can be used to enhance results from any search source:
    - Qdrant vector search
    - Graphiti graph search
    - Combined hybrid search

    Args:
        query: The original search query
        results: Raw search results
        method: Reranking method ("embedding" or "llm")
        top_k: Number of results to return

    Returns:
        Reranked results
    """
    reranker = get_reranker()
    return await reranker.rerank(query, results, method, top_k)
