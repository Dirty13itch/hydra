"""
Hydra Research Queue

Ingestion pipeline for external research - URLs, documents, papers.
Fetches content, analyzes with LLM, extracts key insights, stores to knowledge base.

Endpoints:
- POST /research/queue - Submit URL/document for analysis
- GET /research/queue - List queued items
- GET /research/queue/{id} - Get specific item status/results
- POST /research/queue/{id}/process - Manually trigger processing
- GET /research/queue/results - Get all completed analyses
- DELETE /research/queue/{id} - Remove item from queue

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

RESEARCH_QUEUED = Counter(
    "hydra_research_queued_total",
    "Total research items queued",
    ["source_type", "priority"]
)

RESEARCH_PROCESSED = Counter(
    "hydra_research_processed_total",
    "Total research items processed",
    ["status"]
)

RESEARCH_LATENCY = Histogram(
    "hydra_research_processing_seconds",
    "Research processing latency",
    buckets=[5, 10, 30, 60, 120, 300, 600]
)

RESEARCH_QUEUE_SIZE = Gauge(
    "hydra_research_queue_size",
    "Current research queue size"
)

# =============================================================================
# Enums and Types
# =============================================================================

class ResearchPriority(str, Enum):
    CRITICAL = "critical"  # Process immediately
    HIGH = "high"          # Process within hour
    NORMAL = "normal"      # Process in batch
    LOW = "low"            # Process when idle


class ResearchStatus(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    URL = "url"
    DOCUMENT = "document"
    TEXT = "text"
    ARXIV = "arxiv"
    GITHUB = "github"


@dataclass
class ResearchItem:
    """A queued research item."""
    id: str
    source: str  # URL, file path, or raw text
    source_type: SourceType
    topic: Optional[str] = None
    priority: ResearchPriority = ResearchPriority.NORMAL
    status: ResearchStatus = ResearchStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Content
    raw_content: Optional[str] = None
    content_length: int = 0

    # Analysis results
    summary: Optional[str] = None
    key_insights: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    relevance_to_hydra: Optional[str] = None
    action_items: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Metadata
    title: Optional[str] = None
    author: Optional[str] = None
    publish_date: Optional[str] = None
    error: Optional[str] = None

    # Storage
    stored_to_knowledge: bool = False
    knowledge_id: Optional[str] = None


@dataclass
class ResearchQueueConfig:
    """Configuration for research queue."""
    # LLM settings
    llm_url: str = "http://192.168.1.203:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = "not-needed"

    # Processing settings
    max_content_length: int = 50000  # Max chars to analyze
    auto_process: bool = True
    process_interval: int = 60  # Seconds between batch processing

    # Storage
    data_dir: str = "/data/research"
    auto_store_to_knowledge: bool = True

    # Qdrant settings
    qdrant_url: str = "http://192.168.1.244:6333"
    qdrant_collection: str = "hydra_research"
    embedding_url: str = "http://192.168.1.203:11434/api/embeddings"
    embedding_model: str = "nomic-embed-text"


# =============================================================================
# Research Queue Implementation
# =============================================================================

class ResearchQueue:
    """
    Research ingestion and analysis queue.

    Accepts URLs, documents, and text for analysis by LLM.
    Extracts insights, tags, and action items.
    Stores results to knowledge base.
    """

    def __init__(self, config: Optional[ResearchQueueConfig] = None):
        self.config = config or ResearchQueueConfig()
        self.queue: Dict[str, ResearchItem] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False

        # Ensure data directory exists
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)

        # Load existing queue from disk
        self._load_queue()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    # =========================================================================
    # Queue Management
    # =========================================================================

    def add(
        self,
        source: str,
        source_type: SourceType = SourceType.URL,
        topic: Optional[str] = None,
        priority: ResearchPriority = ResearchPriority.NORMAL,
    ) -> ResearchItem:
        """Add item to research queue."""
        item_id = str(uuid.uuid4())[:8]

        item = ResearchItem(
            id=item_id,
            source=source,
            source_type=source_type,
            topic=topic,
            priority=priority,
        )

        self.queue[item_id] = item
        self._save_queue()

        RESEARCH_QUEUED.labels(
            source_type=source_type.value,
            priority=priority.value
        ).inc()
        RESEARCH_QUEUE_SIZE.set(len([i for i in self.queue.values() if i.status == ResearchStatus.QUEUED]))

        logger.info(f"Queued research item {item_id}: {source[:50]}...")
        return item

    def get(self, item_id: str) -> Optional[ResearchItem]:
        """Get item by ID."""
        return self.queue.get(item_id)

    def list_items(
        self,
        status: Optional[ResearchStatus] = None,
        limit: int = 50
    ) -> List[ResearchItem]:
        """List queue items, optionally filtered by status."""
        items = list(self.queue.values())

        if status:
            items = [i for i in items if i.status == status]

        # Sort by priority then created_at
        priority_order = {
            ResearchPriority.CRITICAL: 0,
            ResearchPriority.HIGH: 1,
            ResearchPriority.NORMAL: 2,
            ResearchPriority.LOW: 3,
        }
        items.sort(key=lambda x: (priority_order.get(x.priority, 2), x.created_at))

        return items[:limit]

    def remove(self, item_id: str) -> bool:
        """Remove item from queue."""
        if item_id in self.queue:
            del self.queue[item_id]
            self._save_queue()
            RESEARCH_QUEUE_SIZE.set(len([i for i in self.queue.values() if i.status == ResearchStatus.QUEUED]))
            return True
        return False

    # =========================================================================
    # Content Fetching
    # =========================================================================

    async def _fetch_url(self, url: str) -> tuple[str, Dict[str, Any]]:
        """Fetch content from URL."""
        metadata = {}

        try:
            # Handle different URL types
            if "arxiv.org" in url:
                return await self._fetch_arxiv(url)
            elif "github.com" in url:
                return await self._fetch_github(url)

            # Generic URL fetch
            response = await self.client.get(
                url,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; HydraResearchBot/1.0)"
                }
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            content = response.text

            # Try to extract title from HTML
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()

            # Strip HTML tags for analysis
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()

            return content, metadata

        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise

    async def _fetch_arxiv(self, url: str) -> tuple[str, Dict[str, Any]]:
        """Fetch arXiv paper abstract and metadata."""
        metadata = {}

        # Extract paper ID
        arxiv_id = re.search(r'(\d+\.\d+)', url)
        if not arxiv_id:
            raise ValueError(f"Could not extract arXiv ID from {url}")

        paper_id = arxiv_id.group(1)
        api_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"

        response = await self.client.get(api_url)
        content = response.text

        # Parse basic metadata from XML
        title_match = re.search(r'<title>([^<]+)</title>', content)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        summary_match = re.search(r'<summary>([^<]+)</summary>', content, re.DOTALL)
        if summary_match:
            abstract = summary_match.group(1).strip()
            metadata["abstract"] = abstract
            return abstract, metadata

        return content, metadata

    async def _fetch_github(self, url: str) -> tuple[str, Dict[str, Any]]:
        """Fetch GitHub README or file content."""
        metadata = {}

        # Convert to raw URL if needed
        if "github.com" in url and "/blob/" in url:
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        elif "github.com" in url and not "/raw/" in url:
            # Try to get README
            parts = url.rstrip("/").split("/")
            if len(parts) >= 5:
                owner, repo = parts[3], parts[4]
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
                metadata["title"] = f"{owner}/{repo} README"

        response = await self.client.get(url)
        return response.text, metadata

    # =========================================================================
    # LLM Analysis
    # =========================================================================

    async def _analyze_content(self, item: ResearchItem) -> Dict[str, Any]:
        """Analyze content with LLM."""

        content = item.raw_content or ""

        # Truncate if too long
        if len(content) > self.config.max_content_length:
            content = content[:self.config.max_content_length] + "\n\n[Content truncated...]"

        topic_context = f"Topic: {item.topic}\n\n" if item.topic else ""

        prompt = f"""Analyze this research content and extract key information for a home AI cluster called Hydra.

{topic_context}Content:
{content}

Provide your analysis in the following JSON format:
{{
    "title": "Title of the content",
    "summary": "2-3 paragraph summary of the main points",
    "key_insights": ["insight 1", "insight 2", "insight 3", ...],
    "entities": ["technology/framework/concept mentioned", ...],
    "relevance_to_hydra": "How this relates to building autonomous AI systems, inference optimization, agent orchestration, or self-improvement",
    "action_items": ["specific action Hydra could take based on this", ...],
    "tags": ["tag1", "tag2", ...],
    "author": "Author if identifiable",
    "publish_date": "Publication date if identifiable"
}}

Focus on practical insights for AI infrastructure, agent frameworks, LLM optimization, and autonomous systems."""

        try:
            response = await self.client.post(
                f"{self.config.llm_url}/chat/completions",
                json={
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {self.config.llm_api_key}"},
            )

            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.status_code}")

            data = response.json()
            result_text = data["choices"][0]["message"]["content"]

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"summary": result_text, "key_insights": [], "tags": []}

        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return {"summary": result_text, "key_insights": [], "tags": []}
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise

    # =========================================================================
    # Processing Pipeline
    # =========================================================================

    async def process_item(self, item_id: str) -> ResearchItem:
        """Process a single research item."""
        item = self.queue.get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        start_time = time.time()
        item.started_at = datetime.utcnow().isoformat() + "Z"
        item.status = ResearchStatus.FETCHING
        self._save_queue()

        try:
            # Fetch content
            if item.source_type == SourceType.URL:
                content, metadata = await self._fetch_url(item.source)
                item.raw_content = content
                item.content_length = len(content)
                item.title = metadata.get("title", item.title)
            elif item.source_type == SourceType.TEXT:
                item.raw_content = item.source
                item.content_length = len(item.source)
            elif item.source_type == SourceType.ARXIV:
                content, metadata = await self._fetch_arxiv(item.source)
                item.raw_content = content
                item.content_length = len(content)
                item.title = metadata.get("title", item.title)
            elif item.source_type == SourceType.GITHUB:
                content, metadata = await self._fetch_github(item.source)
                item.raw_content = content
                item.content_length = len(content)
                item.title = metadata.get("title", item.title)

            # Analyze with LLM
            item.status = ResearchStatus.ANALYZING
            self._save_queue()

            analysis = await self._analyze_content(item)

            # Apply analysis results
            item.title = analysis.get("title", item.title)
            item.summary = analysis.get("summary")
            item.key_insights = analysis.get("key_insights", [])
            item.entities = analysis.get("entities", [])
            item.relevance_to_hydra = analysis.get("relevance_to_hydra")
            item.action_items = analysis.get("action_items", [])
            item.tags = analysis.get("tags", [])
            item.author = analysis.get("author")
            item.publish_date = analysis.get("publish_date")

            # Store to knowledge base if enabled
            if self.config.auto_store_to_knowledge:
                await self._store_to_knowledge(item)

            item.status = ResearchStatus.COMPLETED
            item.completed_at = datetime.utcnow().isoformat() + "Z"

            RESEARCH_PROCESSED.labels(status="success").inc()
            RESEARCH_LATENCY.observe(time.time() - start_time)

            logger.info(f"Processed research item {item_id}: {item.title}")

        except Exception as e:
            item.status = ResearchStatus.FAILED
            item.error = str(e)
            item.completed_at = datetime.utcnow().isoformat() + "Z"
            RESEARCH_PROCESSED.labels(status="failed").inc()
            logger.error(f"Failed to process item {item_id}: {e}")

        self._save_queue()
        RESEARCH_QUEUE_SIZE.set(len([i for i in self.queue.values() if i.status == ResearchStatus.QUEUED]))

        return item

    async def _store_to_knowledge(self, item: ResearchItem):
        """Store processed research to Qdrant knowledge base."""
        try:
            # Generate embedding
            embed_response = await self.client.post(
                self.config.embedding_url,
                json={
                    "model": self.config.embedding_model,
                    "prompt": f"{item.title or ''}\n{item.summary or ''}"
                }
            )

            if embed_response.status_code != 200:
                logger.warning(f"Failed to generate embedding: {embed_response.status_code}")
                return

            embedding = embed_response.json().get("embedding", [])

            if not embedding:
                logger.warning("Empty embedding returned")
                return

            # Store to Qdrant
            point_id = str(uuid.uuid4())

            qdrant_response = await self.client.put(
                f"{self.config.qdrant_url}/collections/{self.config.qdrant_collection}/points",
                json={
                    "points": [{
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "research_id": item.id,
                            "title": item.title,
                            "summary": item.summary,
                            "source": item.source,
                            "source_type": item.source_type.value,
                            "key_insights": item.key_insights,
                            "entities": item.entities,
                            "relevance_to_hydra": item.relevance_to_hydra,
                            "action_items": item.action_items,
                            "tags": item.tags,
                            "created_at": item.created_at,
                            "processed_at": item.completed_at,
                        }
                    }]
                }
            )

            if qdrant_response.status_code in (200, 201):
                item.stored_to_knowledge = True
                item.knowledge_id = point_id
                logger.info(f"Stored research {item.id} to knowledge base as {point_id}")
            else:
                logger.warning(f"Failed to store to Qdrant: {qdrant_response.status_code}")

        except Exception as e:
            logger.error(f"Failed to store to knowledge base: {e}")

    async def process_queue(self):
        """Process all queued items by priority."""
        queued = self.list_items(status=ResearchStatus.QUEUED)

        for item in queued:
            try:
                await self.process_item(item.id)
            except Exception as e:
                logger.error(f"Error processing {item.id}: {e}")

    # =========================================================================
    # Background Processing
    # =========================================================================

    async def start_background_processing(self):
        """Start background processing loop."""
        if self._running:
            return

        self._running = True

        async def process_loop():
            while self._running:
                try:
                    # Process critical items immediately
                    critical = [
                        i for i in self.queue.values()
                        if i.status == ResearchStatus.QUEUED
                        and i.priority == ResearchPriority.CRITICAL
                    ]
                    for item in critical:
                        await self.process_item(item.id)

                    # Process high priority items
                    high = [
                        i for i in self.queue.values()
                        if i.status == ResearchStatus.QUEUED
                        and i.priority == ResearchPriority.HIGH
                    ]
                    for item in high:
                        await self.process_item(item.id)

                except Exception as e:
                    logger.error(f"Background processing error: {e}")

                await asyncio.sleep(self.config.process_interval)

        self._processing_task = asyncio.create_task(process_loop())
        logger.info("Research queue background processing started")

    async def stop_background_processing(self):
        """Stop background processing."""
        self._running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_queue(self):
        """Save queue to disk."""
        data = {
            item_id: asdict(item)
            for item_id, item in self.queue.items()
        }

        queue_file = Path(self.config.data_dir) / "queue.json"
        with open(queue_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_queue(self):
        """Load queue from disk."""
        queue_file = Path(self.config.data_dir) / "queue.json"

        if not queue_file.exists():
            return

        try:
            with open(queue_file, "r") as f:
                data = json.load(f)

            for item_id, item_data in data.items():
                # Convert enums
                item_data["source_type"] = SourceType(item_data.get("source_type", "url"))
                item_data["priority"] = ResearchPriority(item_data.get("priority", "normal"))
                item_data["status"] = ResearchStatus(item_data.get("status", "queued"))

                self.queue[item_id] = ResearchItem(**item_data)

            logger.info(f"Loaded {len(self.queue)} items from research queue")
            RESEARCH_QUEUE_SIZE.set(len([i for i in self.queue.values() if i.status == ResearchStatus.QUEUED]))

        except Exception as e:
            logger.error(f"Failed to load queue: {e}")

    async def close(self):
        """Close resources."""
        await self.stop_background_processing()
        if self._client:
            await self._client.aclose()


# =============================================================================
# Global Instance
# =============================================================================

_queue_instance: Optional[ResearchQueue] = None


def get_research_queue() -> ResearchQueue:
    """Get the global ResearchQueue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = ResearchQueue()
    return _queue_instance


# =============================================================================
# FastAPI Router
# =============================================================================

def create_research_queue_router():
    """Create FastAPI router for research queue endpoints."""
    from fastapi import APIRouter, HTTPException, BackgroundTasks
    from pydantic import BaseModel
    from typing import Optional, List

    router = APIRouter(prefix="/research", tags=["research-queue"])

    class QueueItemRequest(BaseModel):
        source: str  # URL, file path, or raw text
        source_type: str = "url"  # url, document, text, arxiv, github
        topic: Optional[str] = None
        priority: str = "normal"  # critical, high, normal, low
        process_immediately: bool = False

    class QueueItemResponse(BaseModel):
        id: str
        source: str
        source_type: str
        topic: Optional[str]
        priority: str
        status: str
        created_at: str
        title: Optional[str] = None
        summary: Optional[str] = None
        key_insights: List[str] = []
        relevance_to_hydra: Optional[str] = None
        action_items: List[str] = []
        tags: List[str] = []
        error: Optional[str] = None

    def item_to_response(item: ResearchItem) -> QueueItemResponse:
        return QueueItemResponse(
            id=item.id,
            source=item.source,
            source_type=item.source_type.value,
            topic=item.topic,
            priority=item.priority.value,
            status=item.status.value,
            created_at=item.created_at,
            title=item.title,
            summary=item.summary,
            key_insights=item.key_insights,
            relevance_to_hydra=item.relevance_to_hydra,
            action_items=item.action_items,
            tags=item.tags,
            error=item.error,
        )

    @router.post("/queue", response_model=QueueItemResponse)
    async def queue_research(
        request: QueueItemRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Queue a URL, document, or text for research analysis.

        Source types:
        - url: Web page URL
        - arxiv: arXiv paper URL
        - github: GitHub repository URL
        - text: Raw text content
        - document: File path (must be accessible to API)

        Priorities:
        - critical: Process immediately
        - high: Process within the hour
        - normal: Process in next batch
        - low: Process when idle
        """
        queue = get_research_queue()

        try:
            source_type = SourceType(request.source_type)
            priority = ResearchPriority(request.priority)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        item = queue.add(
            source=request.source,
            source_type=source_type,
            topic=request.topic,
            priority=priority,
        )

        # Process immediately if requested or critical priority
        if request.process_immediately or priority == ResearchPriority.CRITICAL:
            background_tasks.add_task(queue.process_item, item.id)

        return item_to_response(item)

    @router.get("/queue", response_model=List[QueueItemResponse])
    async def list_queue(
        status: Optional[str] = None,
        limit: int = 50
    ):
        """List queued research items."""
        queue = get_research_queue()

        status_filter = None
        if status:
            try:
                status_filter = ResearchStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        items = queue.list_items(status=status_filter, limit=limit)
        return [item_to_response(i) for i in items]

    @router.get("/queue/stats")
    async def get_queue_stats():
        """Get research queue statistics."""
        queue = get_research_queue()

        all_items = list(queue.queue.values())

        by_status = {}
        for status in ResearchStatus:
            by_status[status.value] = len([i for i in all_items if i.status == status])

        by_priority = {}
        for priority in ResearchPriority:
            by_priority[priority.value] = len([i for i in all_items if i.priority == priority])

        return {
            "total_items": len(all_items),
            "by_status": by_status,
            "by_priority": by_priority,
            "auto_process_enabled": queue.config.auto_process,
            "process_interval_seconds": queue.config.process_interval,
        }

    @router.get("/queue/results/completed", response_model=List[QueueItemResponse])
    async def get_completed_results(limit: int = 50):
        """Get all completed research analyses."""
        queue = get_research_queue()
        items = queue.list_items(status=ResearchStatus.COMPLETED, limit=limit)
        return [item_to_response(i) for i in items]

    @router.get("/queue/{item_id}", response_model=QueueItemResponse)
    async def get_queue_item(item_id: str):
        """Get a specific research item."""
        queue = get_research_queue()
        item = queue.get(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return item_to_response(item)

    @router.post("/queue/{item_id}/process", response_model=QueueItemResponse)
    async def process_item(item_id: str):
        """Manually trigger processing of a queued item."""
        queue = get_research_queue()
        item = queue.get(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        if item.status not in (ResearchStatus.QUEUED, ResearchStatus.FAILED):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot process item with status {item.status.value}"
            )

        # Reset status for retry
        item.status = ResearchStatus.QUEUED
        item.error = None

        result = await queue.process_item(item_id)
        return item_to_response(result)

    @router.delete("/queue/{item_id}")
    async def delete_item(item_id: str):
        """Delete a research item from the queue."""
        queue = get_research_queue()

        if queue.remove(item_id):
            return {"status": "deleted", "id": item_id}
        else:
            raise HTTPException(status_code=404, detail="Item not found")

    @router.post("/queue/process-all")
    async def process_all_queued(background_tasks: BackgroundTasks):
        """Trigger processing of all queued items."""
        queue = get_research_queue()
        queued = queue.list_items(status=ResearchStatus.QUEUED)

        for item in queued:
            background_tasks.add_task(queue.process_item, item.id)

        return {
            "status": "processing",
            "items_queued": len(queued),
        }

    return router
