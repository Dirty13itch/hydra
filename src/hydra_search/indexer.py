"""
Document Indexer for Hybrid Search

Handles document chunking, embedding, and indexing to both
Meilisearch and Qdrant backends.
"""

import asyncio
import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx

from .config import SearchConfig
from .embeddings import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document to be indexed."""

    content: str
    source: str
    title: Optional[str] = None
    doc_type: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            # Generate deterministic ID from source
            self.id = hashlib.md5(self.source.encode()).hexdigest()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Chunk:
    """Document chunk for indexing."""

    content: str
    source: str
    chunk_index: int
    total_chunks: int
    title: Optional[str] = None
    doc_type: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    embedding: Optional[List[float]] = None


class DocumentIndexer:
    """
    Document indexer for hybrid search system.

    Handles:
    - Document chunking with overlap
    - Embedding generation
    - Parallel indexing to Meilisearch and Qdrant
    """

    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.embedding_client = EmbeddingClient(self.config.embedding)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def index_document(
        self,
        document: Document,
        collection: Optional[str] = None,
        index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Index a single document to both backends.

        Args:
            document: Document to index
            collection: Qdrant collection name
            index: Meilisearch index name

        Returns:
            Dict with indexing results
        """
        collection = collection or self.config.default_collection
        index = index or self.config.default_index

        # Chunk the document
        chunks = self._chunk_document(document)

        # Generate embeddings
        embeddings = await self.embedding_client.embed([c.content for c in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        # Index to both backends in parallel
        qdrant_task = self._index_to_qdrant(chunks, collection)
        meili_task = self._index_to_meilisearch(chunks, index)

        qdrant_result, meili_result = await asyncio.gather(
            qdrant_task, meili_task, return_exceptions=True
        )

        return {
            "document_id": document.id,
            "chunks": len(chunks),
            "qdrant": (
                {"success": True, "result": qdrant_result}
                if not isinstance(qdrant_result, Exception)
                else {"success": False, "error": str(qdrant_result)}
            ),
            "meilisearch": (
                {"success": True, "result": meili_result}
                if not isinstance(meili_result, Exception)
                else {"success": False, "error": str(meili_result)}
            ),
        }

    async def index_documents(
        self,
        documents: List[Document],
        collection: Optional[str] = None,
        index: Optional[str] = None,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Index multiple documents to both backends.

        Args:
            documents: List of documents to index
            collection: Qdrant collection name
            index: Meilisearch index name
            batch_size: Number of documents to process in parallel

        Returns:
            Dict with indexing summary
        """
        collection = collection or self.config.default_collection
        index = index or self.config.default_index

        results = []
        total_chunks = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.index_document(doc, collection, index) for doc in batch]
            )
            results.extend(batch_results)
            total_chunks += sum(r["chunks"] for r in batch_results)

        successes = sum(
            1 for r in results
            if r["qdrant"]["success"] and r["meilisearch"]["success"]
        )

        return {
            "total_documents": len(documents),
            "successful": successes,
            "failed": len(documents) - successes,
            "total_chunks": total_chunks,
            "results": results,
        }

    def _chunk_document(self, document: Document) -> List[Chunk]:
        """
        Split document into overlapping chunks.

        Uses sentence-aware chunking to avoid breaking mid-sentence.
        """
        text = document.content
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        # Split into sentences (rough approximation)
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence.split())

            if current_length + sentence_length > chunk_size and current_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk)
                chunk_id = f"{document.id}_{len(chunks)}"

                chunks.append(
                    Chunk(
                        id=chunk_id,
                        content=chunk_text,
                        source=document.source,
                        chunk_index=len(chunks),
                        total_chunks=0,  # Will be updated later
                        title=document.title,
                        doc_type=document.doc_type,
                        tags=document.tags,
                        metadata={
                            **(document.metadata or {}),
                            "parent_id": document.id,
                        },
                    )
                )

                # Keep overlap
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s.split()) <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s.split())
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_id = f"{document.id}_{len(chunks)}"

            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    source=document.source,
                    chunk_index=len(chunks),
                    total_chunks=0,
                    title=document.title,
                    doc_type=document.doc_type,
                    tags=document.tags,
                    metadata={
                        **(document.metadata or {}),
                        "parent_id": document.id,
                    },
                )
            )

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    async def _index_to_qdrant(
        self, chunks: List[Chunk], collection: str
    ) -> Dict[str, Any]:
        """Index chunks to Qdrant."""
        client = await self._get_client()

        # Ensure collection exists
        await self._ensure_qdrant_collection(collection)

        # Build points
        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue

            # Generate numeric ID from string ID
            point_id = int(hashlib.md5(chunk.id.encode()).hexdigest()[:16], 16)

            points.append({
                "id": point_id,
                "vector": chunk.embedding,
                "payload": {
                    "content": chunk.content,
                    "source": chunk.source,
                    "title": chunk.title,
                    "type": chunk.doc_type,
                    "tags": chunk.tags or [],
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "indexed_at": datetime.utcnow().isoformat(),
                    **(chunk.metadata or {}),
                },
            })

        # Upsert points
        response = await client.put(
            f"{self.config.qdrant.url}/collections/{collection}/points",
            json={"points": points},
        )
        response.raise_for_status()

        return {"indexed": len(points)}

    async def _index_to_meilisearch(
        self, chunks: List[Chunk], index: str
    ) -> Dict[str, Any]:
        """Index chunks to Meilisearch."""
        client = await self._get_client()

        # Ensure index exists
        await self._ensure_meilisearch_index(index)

        # Build documents
        documents = []
        for chunk in chunks:
            documents.append({
                "id": chunk.id,
                "content": chunk.content,
                "source": chunk.source,
                "title": chunk.title or "",
                "type": chunk.doc_type or "",
                "tags": chunk.tags or [],
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "indexed_at": datetime.utcnow().isoformat(),
                **(chunk.metadata or {}),
            })

        headers = {}
        if self.config.meilisearch.api_key:
            headers["Authorization"] = f"Bearer {self.config.meilisearch.api_key}"

        # Add documents
        response = await client.post(
            f"{self.config.meilisearch.url}/indexes/{index}/documents",
            json=documents,
            headers=headers,
        )
        response.raise_for_status()

        return {"indexed": len(documents), "task": response.json()}

    async def _ensure_qdrant_collection(self, collection: str):
        """Ensure Qdrant collection exists with correct schema."""
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.config.qdrant.url}/collections/{collection}"
            )
            if response.status_code == 200:
                return  # Collection exists
        except httpx.HTTPError:
            pass

        # Create collection
        dimensions = self.embedding_client.get_dimensions()

        await client.put(
            f"{self.config.qdrant.url}/collections/{collection}",
            json={
                "vectors": {
                    "size": dimensions,
                    "distance": "Cosine",
                },
                "optimizers_config": {
                    "memmap_threshold": 20000,
                },
            },
        )

        logger.info(f"Created Qdrant collection: {collection}")

    async def _ensure_meilisearch_index(self, index: str):
        """Ensure Meilisearch index exists with correct settings."""
        client = await self._get_client()

        headers = {}
        if self.config.meilisearch.api_key:
            headers["Authorization"] = f"Bearer {self.config.meilisearch.api_key}"

        try:
            response = await client.get(
                f"{self.config.meilisearch.url}/indexes/{index}",
                headers=headers,
            )
            if response.status_code == 200:
                return  # Index exists
        except httpx.HTTPError:
            pass

        # Create index
        await client.post(
            f"{self.config.meilisearch.url}/indexes",
            json={"uid": index, "primaryKey": "id"},
            headers=headers,
        )

        # Configure searchable attributes
        await client.put(
            f"{self.config.meilisearch.url}/indexes/{index}/settings/searchable-attributes",
            json=self.config.searchable_attributes,
            headers=headers,
        )

        # Configure filterable attributes
        await client.put(
            f"{self.config.meilisearch.url}/indexes/{index}/settings/filterable-attributes",
            json=self.config.filterable_attributes,
            headers=headers,
        )

        logger.info(f"Created Meilisearch index: {index}")

    async def delete_document(
        self,
        document_id: str,
        collection: Optional[str] = None,
        index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete a document from both backends.

        Args:
            document_id: Document ID to delete
            collection: Qdrant collection name
            index: Meilisearch index name

        Returns:
            Dict with deletion results
        """
        collection = collection or self.config.default_collection
        index = index or self.config.default_index

        client = await self._get_client()

        # Delete from Qdrant (by payload filter)
        qdrant_result = None
        try:
            response = await client.post(
                f"{self.config.qdrant.url}/collections/{collection}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "parent_id", "match": {"value": document_id}}
                        ]
                    }
                },
            )
            response.raise_for_status()
            qdrant_result = {"success": True}
        except httpx.HTTPError as e:
            qdrant_result = {"success": False, "error": str(e)}

        # Delete from Meilisearch (by filter)
        meili_result = None
        headers = {}
        if self.config.meilisearch.api_key:
            headers["Authorization"] = f"Bearer {self.config.meilisearch.api_key}"

        try:
            # First, find all chunk IDs for this document
            response = await client.post(
                f"{self.config.meilisearch.url}/indexes/{index}/search",
                json={
                    "q": "",
                    "filter": f'parent_id = "{document_id}"',
                    "limit": 1000,
                },
                headers=headers,
            )
            response.raise_for_status()
            hits = response.json().get("hits", [])
            ids = [h["id"] for h in hits]

            if ids:
                # Delete found documents
                delete_response = await client.post(
                    f"{self.config.meilisearch.url}/indexes/{index}/documents/delete-batch",
                    json=ids,
                    headers=headers,
                )
                delete_response.raise_for_status()

            meili_result = {"success": True, "deleted": len(ids)}
        except httpx.HTTPError as e:
            meili_result = {"success": False, "error": str(e)}

        return {
            "document_id": document_id,
            "qdrant": qdrant_result,
            "meilisearch": meili_result,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Synchronous wrapper
class DocumentIndexerSync:
    """Synchronous wrapper for DocumentIndexer."""

    def __init__(self, config: Optional[SearchConfig] = None):
        self._async_indexer = DocumentIndexer(config)

    def index_document(self, *args, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self._async_indexer.index_document(*args, **kwargs))

    def index_documents(self, *args, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self._async_indexer.index_documents(*args, **kwargs))

    def delete_document(self, *args, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self._async_indexer.delete_document(*args, **kwargs))

    def close(self):
        asyncio.run(self._async_indexer.close())
