"""
Search API Router

Exposes hybrid search, document indexing, and web research capabilities
via REST endpoints.

Endpoints:
- /search/query - Hybrid search (Qdrant + Meilisearch)
- /search/semantic - Semantic-only search
- /search/keyword - Keyword-only search
- /ingest/document - Index a single document
- /ingest/url - Crawl and index a URL
- /ingest/batch - Batch index multiple documents
- /research/topic - Research a topic (search + crawl)
- /research/web - Web search via SearXNG
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from hydra_search.config import SearchConfig, get_config_from_env
from hydra_search.hybrid import HybridSearchClient
from hydra_search.indexer import DocumentIndexer, Document


# Request/Response Models
class SearchRequest(BaseModel):
    """Search query request."""
    query: str = Field(..., description="Search query text")
    collection: Optional[str] = Field(None, description="Qdrant collection name")
    index: Optional[str] = Field(None, description="Meilisearch index name")
    limit: int = Field(10, ge=1, le=100, description="Max results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter criteria")
    semantic_weight: Optional[float] = Field(None, ge=0, le=1)
    keyword_weight: Optional[float] = Field(None, ge=0, le=1)


class SearchResultItem(BaseModel):
    """Single search result."""
    id: str
    content: str
    score: float
    source: str
    source_type: str
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    results: List[SearchResultItem]
    total: int
    search_time_ms: float


class IngestDocumentRequest(BaseModel):
    """Document ingestion request."""
    content: str = Field(..., description="Document content")
    source: str = Field(..., description="Source identifier (URL, file path, etc.)")
    title: Optional[str] = Field(None, description="Document title")
    doc_type: Optional[str] = Field(None, description="Document type")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    collection: Optional[str] = Field(None, description="Target Qdrant collection")
    index: Optional[str] = Field(None, description="Target Meilisearch index")


class IngestURLRequest(BaseModel):
    """URL ingestion request."""
    url: str = Field(..., description="URL to crawl and index")
    collection: Optional[str] = Field(None, description="Target Qdrant collection")
    index: Optional[str] = Field(None, description="Target Meilisearch index")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")


class IngestResponse(BaseModel):
    """Ingestion response."""
    document_id: str
    chunks: int
    qdrant_success: bool
    meilisearch_success: bool
    message: str


class WebSearchRequest(BaseModel):
    """Web search request."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(10, ge=1, le=50)
    categories: Optional[List[str]] = Field(None, description="Search categories")
    engines: Optional[List[str]] = Field(None, description="Specific search engines")


class ResearchRequest(BaseModel):
    """Topic research request."""
    topic: str = Field(..., description="Topic to research")
    max_sources: int = Field(5, ge=1, le=20)
    include_content: bool = Field(True, description="Include full page content")
    index_results: bool = Field(False, description="Index results to knowledge base")
    collection: Optional[str] = Field(None, description="Target collection for indexing")


# Shared instances
_config: Optional[SearchConfig] = None
_search_client: Optional[HybridSearchClient] = None
_indexer: Optional[DocumentIndexer] = None


def get_config() -> SearchConfig:
    global _config
    if _config is None:
        _config = get_config_from_env()
    return _config


async def get_search_client() -> HybridSearchClient:
    global _search_client
    if _search_client is None:
        _search_client = HybridSearchClient(get_config())
    return _search_client


async def get_indexer() -> DocumentIndexer:
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer(get_config())
    return _indexer


def create_search_router() -> APIRouter:
    """Create and configure the search API router."""
    router = APIRouter(prefix="/search", tags=["search"])

    @router.post("/query", response_model=SearchResponse)
    async def hybrid_search(request: SearchRequest):
        """
        Perform hybrid search combining semantic and keyword search.

        Uses Qdrant for semantic similarity and Meilisearch for BM25 keyword matching.
        Results are combined using weighted scoring.
        """
        import time
        start = time.time()

        client = await get_search_client()

        try:
            results = await client.search(
                query=request.query,
                collection=request.collection,
                index=request.index,
                limit=request.limit,
                filters=request.filters,
                semantic_weight=request.semantic_weight,
                keyword_weight=request.keyword_weight,
            )

            search_time = (time.time() - start) * 1000

            return SearchResponse(
                query=request.query,
                results=[
                    SearchResultItem(
                        id=r.id,
                        content=r.content,
                        score=r.combined_score or r.score,
                        source=r.source,
                        source_type=r.source_type,
                        semantic_score=r.semantic_score,
                        keyword_score=r.keyword_score,
                        metadata=r.metadata,
                    )
                    for r in results
                ],
                total=len(results),
                search_time_ms=search_time,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    @router.post("/semantic", response_model=SearchResponse)
    async def semantic_search(request: SearchRequest):
        """
        Perform semantic-only search using vector similarity.

        Uses Qdrant to find conceptually similar content.
        """
        import time
        start = time.time()

        client = await get_search_client()

        try:
            results = await client.semantic_search(
                query=request.query,
                collection=request.collection,
                limit=request.limit,
                filters=request.filters,
            )

            search_time = (time.time() - start) * 1000

            return SearchResponse(
                query=request.query,
                results=[
                    SearchResultItem(
                        id=r.id,
                        content=r.content,
                        score=r.score,
                        source=r.source,
                        source_type=r.source_type,
                        semantic_score=r.semantic_score,
                        metadata=r.metadata,
                    )
                    for r in results
                ],
                total=len(results),
                search_time_ms=search_time,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

    @router.post("/keyword", response_model=SearchResponse)
    async def keyword_search(request: SearchRequest):
        """
        Perform keyword-only search using BM25.

        Uses Meilisearch for exact keyword matching.
        """
        import time
        start = time.time()

        client = await get_search_client()

        try:
            results = await client.keyword_search(
                query=request.query,
                index=request.index,
                limit=request.limit,
                filters=request.filters,
            )

            search_time = (time.time() - start) * 1000

            return SearchResponse(
                query=request.query,
                results=[
                    SearchResultItem(
                        id=r.id,
                        content=r.content,
                        score=r.score,
                        source=r.source,
                        source_type=r.source_type,
                        keyword_score=r.keyword_score,
                        metadata=r.metadata,
                    )
                    for r in results
                ],
                total=len(results),
                search_time_ms=search_time,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Keyword search failed: {str(e)}")

    @router.get("/collections")
    async def list_collections():
        """List available search collections and indexes."""
        import httpx
        config = get_config()

        collections = []
        indexes = []

        async with httpx.AsyncClient(timeout=10) as client:
            # Get Qdrant collections
            try:
                resp = await client.get(f"{config.qdrant.url}/collections")
                if resp.status_code == 200:
                    data = resp.json()
                    collections = [c["name"] for c in data.get("result", {}).get("collections", [])]
            except Exception:
                pass

            # Get Meilisearch indexes
            try:
                headers = {}
                if config.meilisearch.api_key:
                    headers["Authorization"] = f"Bearer {config.meilisearch.api_key}"
                resp = await client.get(f"{config.meilisearch.url}/indexes", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    indexes = [idx["uid"] for idx in data.get("results", [])]
            except Exception:
                pass

        return {
            "qdrant_collections": collections,
            "meilisearch_indexes": indexes,
            "default_collection": config.default_collection,
            "default_index": config.default_index,
        }

    return router


def create_ingest_router() -> APIRouter:
    """Create and configure the ingestion API router."""
    router = APIRouter(prefix="/ingest", tags=["ingest"])

    @router.post("/document", response_model=IngestResponse)
    async def ingest_document(request: IngestDocumentRequest):
        """
        Index a single document to both Qdrant and Meilisearch.

        The document will be chunked, embedded, and indexed to both backends.
        """
        indexer = await get_indexer()

        doc = Document(
            content=request.content,
            source=request.source,
            title=request.title,
            doc_type=request.doc_type,
            tags=request.tags,
            metadata=request.metadata or {},
        )

        try:
            result = await indexer.index_document(
                document=doc,
                collection=request.collection,
                index=request.index,
            )

            return IngestResponse(
                document_id=result["document_id"],
                chunks=result["chunks"],
                qdrant_success=result["qdrant"]["success"],
                meilisearch_success=result["meilisearch"]["success"],
                message=f"Indexed {result['chunks']} chunks",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    @router.post("/url", response_model=IngestResponse)
    async def ingest_url(request: IngestURLRequest, background_tasks: BackgroundTasks):
        """
        Crawl a URL and index its content.

        Uses Firecrawl to extract content, then indexes to the knowledge base.
        """
        import httpx

        # Crawl the URL
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "http://192.168.1.244:3005/v1/scrape",
                    json={"url": request.url}
                )

                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Firecrawl error: {resp.text}")

                data = resp.json()
                content_data = data.get("data", {})

                markdown = content_data.get("markdown", content_data.get("content", ""))
                title = content_data.get("metadata", {}).get("title", request.url)

                if not markdown:
                    raise HTTPException(status_code=400, detail="No content extracted from URL")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to crawl URL: {str(e)}")

        # Index the content
        indexer = await get_indexer()

        doc = Document(
            content=markdown,
            source=request.url,
            title=title,
            doc_type="webpage",
            tags=request.tags,
            metadata={
                "crawled_at": datetime.utcnow().isoformat(),
                "original_url": request.url,
            },
        )

        try:
            result = await indexer.index_document(
                document=doc,
                collection=request.collection or "hydra_knowledge",
                index=request.index or "hydra_knowledge",
            )

            return IngestResponse(
                document_id=result["document_id"],
                chunks=result["chunks"],
                qdrant_success=result["qdrant"]["success"],
                meilisearch_success=result["meilisearch"]["success"],
                message=f"Indexed '{title}' ({result['chunks']} chunks)",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    @router.post("/batch")
    async def ingest_batch(
        documents: List[IngestDocumentRequest],
        collection: Optional[str] = None,
        index: Optional[str] = None,
    ):
        """
        Batch index multiple documents.

        More efficient than individual calls for large document sets.
        """
        indexer = await get_indexer()

        docs = [
            Document(
                content=d.content,
                source=d.source,
                title=d.title,
                doc_type=d.doc_type,
                tags=d.tags,
                metadata=d.metadata or {},
            )
            for d in documents
        ]

        try:
            result = await indexer.index_documents(
                documents=docs,
                collection=collection,
                index=index,
            )

            return {
                "total_documents": result["total_documents"],
                "successful": result["successful"],
                "failed": result["failed"],
                "total_chunks": result["total_chunks"],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch indexing failed: {str(e)}")

    @router.delete("/document/{document_id}")
    async def delete_document(
        document_id: str,
        collection: Optional[str] = None,
        index: Optional[str] = None,
    ):
        """Delete a document from both backends."""
        indexer = await get_indexer()

        try:
            result = await indexer.delete_document(
                document_id=document_id,
                collection=collection,
                index=index,
            )

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

    return router


def create_research_router() -> APIRouter:
    """Create and configure the web research API router."""
    router = APIRouter(prefix="/research", tags=["research"])

    @router.post("/web")
    async def web_search(request: WebSearchRequest):
        """
        Search the web using SearXNG metasearch engine.

        Aggregates results from multiple search engines.
        """
        import httpx

        params = {
            "q": request.query,
            "format": "json",
        }

        if request.categories:
            params["categories"] = ",".join(request.categories)
        if request.engines:
            params["engines"] = ",".join(request.engines)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "http://192.168.1.244:8888/search",
                    params=params
                )

                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="SearXNG error")

                data = resp.json()
                results = data.get("results", [])[:request.max_results]

                return {
                    "query": request.query,
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", ""),
                            "engine": r.get("engine", "unknown"),
                        }
                        for r in results
                    ],
                    "total": len(results),
                }
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Search failed: {str(e)}")

    @router.post("/topic")
    async def research_topic(request: ResearchRequest):
        """
        Research a topic by searching and crawling relevant sources.

        Combines SearXNG search with Firecrawl content extraction.
        Optionally indexes results to the knowledge base.
        """
        from hydra_tools.web_tools import WebResearchTool

        tool = WebResearchTool()

        try:
            result = await tool.research_topic(
                topic=request.topic,
                max_sources=request.max_sources,
                include_content=request.include_content,
            )

            # Optionally index results
            if request.index_results and result.get("sources"):
                indexer = await get_indexer()
                collection = request.collection or "hydra_knowledge"

                indexed = 0
                for source in result["sources"]:
                    if source.get("content"):
                        doc = Document(
                            content=source["content"],
                            source=source["url"],
                            title=source.get("title", ""),
                            doc_type="research",
                            tags=["research", request.topic.lower().replace(" ", "-")],
                            metadata={
                                "research_topic": request.topic,
                                "crawled_at": source.get("crawled_at"),
                            },
                        )
                        try:
                            await indexer.index_document(doc, collection=collection)
                            indexed += 1
                        except Exception:
                            pass

                result["indexed_sources"] = indexed

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

    @router.post("/crawl")
    async def crawl_url(url: str):
        """
        Crawl a single URL and return its content.

        Uses Firecrawl to extract clean markdown content.
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "http://192.168.1.244:3005/v1/scrape",
                    json={"url": url}
                )

                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Firecrawl error: {resp.text}")

                data = resp.json()
                content_data = data.get("data", {})

                return {
                    "url": url,
                    "title": content_data.get("metadata", {}).get("title", ""),
                    "markdown": content_data.get("markdown", ""),
                    "links": content_data.get("links", [])[:20],
                    "metadata": content_data.get("metadata", {}),
                }
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Crawl failed: {str(e)}")

    return router
