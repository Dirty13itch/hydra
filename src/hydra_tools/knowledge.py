"""
Knowledge Tools for Hydra Agents

Provides semantic search and embedding capabilities using Qdrant and Meilisearch.
"""

import requests
from typing import List, Dict, Any, Optional
from langchain.tools import tool

from .config import get_config


@tool
def query_knowledge(
    query: str,
    collection: str = "hydra_docs",
    limit: int = 5,
    score_threshold: float = 0.7,
) -> str:
    """
    Semantic search in Qdrant vector database.

    Args:
        query: The search query (will be embedded automatically)
        collection: Qdrant collection name (default: hydra_docs)
        limit: Maximum number of results (default: 5)
        score_threshold: Minimum similarity score (default: 0.7)

    Returns:
        Formatted search results with content and metadata
    """
    config = get_config()

    try:
        # First, generate embedding for the query
        embedding = _generate_embedding_internal(query, config)
        if not embedding:
            return "Failed to generate query embedding"

        # Search Qdrant
        response = requests.post(
            f"{config.qdrant_url}/collections/{collection}/points/search",
            json={
                "vector": embedding,
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])
        if not results:
            return f"No relevant documents found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            payload = r.get("payload", {})
            content = payload.get("content", payload.get("text", "No content"))[:500]
            source = payload.get("source", payload.get("file", "Unknown"))
            formatted.append(
                f"{i}. [{score:.2f}] **{source}**\n   {content}"
            )

        return "\n\n".join(formatted)

    except requests.exceptions.RequestException as e:
        return f"Knowledge search failed: {str(e)}"


@tool
def generate_embedding(text: str, model: str = "nomic-embed-text") -> List[float]:
    """
    Generate text embeddings using Ollama.

    Args:
        text: The text to embed
        model: Embedding model name (default: nomic-embed-text)

    Returns:
        List of embedding floats
    """
    config = get_config()
    embedding = _generate_embedding_internal(text, config, model)
    return embedding if embedding else []


def _generate_embedding_internal(
    text: str, config, model: str = "nomic-embed-text"
) -> Optional[List[float]]:
    """Internal embedding generation helper."""
    try:
        response = requests.post(
            f"{config.ollama_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except requests.exceptions.RequestException:
        return None


@tool
def hybrid_search(
    query: str,
    collection: str = "hydra_docs",
    index: str = "hydra_docs",
    limit: int = 5,
    semantic_weight: float = 0.7,
) -> str:
    """
    Hybrid search combining Qdrant (semantic) and Meilisearch (keyword).

    Args:
        query: The search query
        collection: Qdrant collection name
        index: Meilisearch index name
        limit: Maximum results per source
        semantic_weight: Weight for semantic results (0-1, default: 0.7)

    Returns:
        Combined and re-ranked search results
    """
    config = get_config()

    try:
        # Semantic search via Qdrant
        semantic_results = _semantic_search(query, collection, limit, config)

        # Keyword search via Meilisearch
        keyword_results = _keyword_search(query, index, limit, config)

        # Combine and re-rank
        combined = _combine_results(
            semantic_results, keyword_results, semantic_weight
        )

        if not combined:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(combined[:limit], 1):
            score = r.get("combined_score", 0)
            content = r.get("content", "")[:400]
            source = r.get("source", "Unknown")
            search_type = r.get("type", "unknown")
            formatted.append(
                f"{i}. [{score:.2f}] ({search_type}) **{source}**\n   {content}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Hybrid search failed: {str(e)}"


def _semantic_search(
    query: str, collection: str, limit: int, config
) -> List[Dict[str, Any]]:
    """Perform semantic search via Qdrant."""
    try:
        embedding = _generate_embedding_internal(query, config)
        if not embedding:
            return []

        response = requests.post(
            f"{config.qdrant_url}/collections/{collection}/points/search",
            json={
                "vector": embedding,
                "limit": limit,
                "with_payload": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("result", []):
            payload = r.get("payload", {})
            results.append({
                "content": payload.get("content", payload.get("text", "")),
                "source": payload.get("source", payload.get("file", "Unknown")),
                "score": r.get("score", 0),
                "type": "semantic",
            })
        return results
    except requests.exceptions.RequestException:
        return []


def _keyword_search(
    query: str, index: str, limit: int, config
) -> List[Dict[str, Any]]:
    """Perform keyword search via Meilisearch."""
    try:
        headers = {}
        if config.meilisearch_key:
            headers["Authorization"] = f"Bearer {config.meilisearch_key}"

        response = requests.post(
            f"{config.meilisearch_url}/indexes/{index}/search",
            json={"q": query, "limit": limit},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        hits = data.get("hits", [])
        max_score = len(hits)  # Meilisearch returns ranked results

        for i, hit in enumerate(hits):
            # Convert rank to normalized score (1.0 to 0.5)
            normalized_score = 1.0 - (i / (max_score * 2)) if max_score > 0 else 0.5
            results.append({
                "content": hit.get("content", hit.get("text", "")),
                "source": hit.get("source", hit.get("title", "Unknown")),
                "score": normalized_score,
                "type": "keyword",
            })
        return results
    except requests.exceptions.RequestException:
        return []


def _combine_results(
    semantic: List[Dict], keyword: List[Dict], semantic_weight: float
) -> List[Dict[str, Any]]:
    """Combine and re-rank results from both search types."""
    keyword_weight = 1.0 - semantic_weight

    # Create lookup by source for deduplication
    combined = {}

    for r in semantic:
        source = r["source"]
        combined[source] = {
            **r,
            "combined_score": r["score"] * semantic_weight,
        }

    for r in keyword:
        source = r["source"]
        if source in combined:
            # Boost score if found in both
            combined[source]["combined_score"] += r["score"] * keyword_weight
            combined[source]["type"] = "hybrid"
        else:
            combined[source] = {
                **r,
                "combined_score": r["score"] * keyword_weight,
            }

    # Sort by combined score
    sorted_results = sorted(
        combined.values(), key=lambda x: x["combined_score"], reverse=True
    )
    return sorted_results


def store_document(
    content: str,
    source: str,
    collection: str = "hydra_docs",
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Store a document in Qdrant with auto-generated embedding.

    Args:
        content: Document content to store
        source: Source identifier (filename, URL, etc.)
        collection: Target collection name
        metadata: Additional metadata to store

    Returns:
        Dict with status and point ID
    """
    config = get_config()

    try:
        # Generate embedding
        embedding = _generate_embedding_internal(content, config)
        if not embedding:
            return {"success": False, "error": "Failed to generate embedding"}

        # Create point ID from source hash
        import hashlib
        point_id = int(hashlib.md5(source.encode()).hexdigest()[:16], 16)

        # Prepare payload
        payload = {
            "content": content,
            "source": source,
            **(metadata or {}),
        }

        # Upsert to Qdrant
        response = requests.put(
            f"{config.qdrant_url}/collections/{collection}/points",
            json={
                "points": [
                    {
                        "id": point_id,
                        "vector": embedding,
                        "payload": payload,
                    }
                ]
            },
            timeout=30,
        )
        response.raise_for_status()

        return {"success": True, "point_id": point_id, "source": source}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
