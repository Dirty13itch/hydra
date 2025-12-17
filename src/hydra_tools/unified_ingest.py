"""
Hydra Unified Ingest Pipeline

Single endpoint for ingesting any content into Hydra's knowledge base:
- Files (images, PDFs, documents, code)
- URLs (web pages, GitHub, arXiv)
- Clipboard images (base64)
- Raw text

Routes to appropriate processing pipeline:
- Images → Vision API → Analysis → Knowledge
- PDFs → Text extraction → LLM analysis → Knowledge
- URLs → Research Queue → Fetch → Analysis → Knowledge
- Code → Syntax analysis → LLM → Knowledge
- Text → Direct LLM analysis → Knowledge

Endpoints:
- POST /ingest - Upload files, URLs, or text
- POST /ingest/clipboard - Paste from clipboard (base64 image)
- POST /ingest/url - Quick URL submission
- GET /ingest/{id} - Get ingestion status/results
- GET /ingest/stream/{id} - SSE progress stream

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import mimetypes
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

INGEST_TOTAL = Counter(
    "hydra_ingest_total",
    "Total ingestion requests",
    ["content_type", "source"]
)

INGEST_PROCESSED = Counter(
    "hydra_ingest_processed_total",
    "Total items processed",
    ["status", "content_type"]
)

INGEST_LATENCY = Histogram(
    "hydra_ingest_processing_seconds",
    "Ingestion processing latency",
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

INGEST_ACTIVE = Gauge(
    "hydra_ingest_active",
    "Currently processing ingestions"
)

# =============================================================================
# Enums and Types
# =============================================================================

class ContentType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    DOCUMENT = "document"  # docx, txt, md
    CODE = "code"
    URL = "url"
    TEXT = "text"
    UNKNOWN = "unknown"


class IngestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestSource(str, Enum):
    UPLOAD = "upload"
    CLIPBOARD = "clipboard"
    URL = "url"
    TEXT = "text"
    API = "api"


@dataclass
class IngestItem:
    """An item being ingested."""
    id: str
    source: IngestSource
    content_type: ContentType
    status: IngestStatus = IngestStatus.PENDING

    # Input
    filename: Optional[str] = None
    url: Optional[str] = None
    raw_size: int = 0

    # Progress
    progress: int = 0  # 0-100
    current_step: str = "queued"

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Extracted content
    extracted_text: Optional[str] = None
    extracted_length: int = 0

    # Analysis results
    title: Optional[str] = None
    summary: Optional[str] = None
    key_insights: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    relevance_to_hydra: Optional[str] = None
    action_items: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Vision-specific (for images)
    image_description: Optional[str] = None
    ocr_text: Optional[str] = None

    # Storage
    stored_to_qdrant: bool = False
    qdrant_id: Optional[str] = None
    file_path: Optional[str] = None

    # Error handling
    error: Optional[str] = None


@dataclass
class IngestConfig:
    """Configuration for ingest pipeline."""
    # LLM settings
    llm_url: str = "http://192.168.1.203:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = "not-needed"

    # Vision settings
    vision_url: str = "http://192.168.1.244:8700"
    vision_model: str = "llava:7b"

    # Embedding settings
    embedding_url: str = "http://192.168.1.203:11434/api/embeddings"
    embedding_model: str = "nomic-embed-text"

    # Qdrant settings
    qdrant_url: str = "http://192.168.1.244:6333"
    qdrant_collection: str = "hydra_ingest"

    # Storage
    storage_dir: str = "/data/ingest"
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Processing
    max_text_length: int = 50000
    image_max_size: int = 4096  # Max dimension


# =============================================================================
# Content Type Detection
# =============================================================================

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
PDF_EXTENSIONS = {'.pdf'}
DOC_EXTENSIONS = {'.txt', '.md', '.rst', '.doc', '.docx', '.rtf'}
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.c', '.cpp',
    '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh',
    '.bash', '.zsh', '.yaml', '.yml', '.json', '.xml', '.html', '.css', '.sql',
    '.nix', '.toml', '.ini', '.cfg'
}

IMAGE_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'}
PDF_MIMETYPES = {'application/pdf'}


def detect_content_type(
    filename: Optional[str] = None,
    mimetype: Optional[str] = None,
    content: Optional[bytes] = None
) -> ContentType:
    """Detect content type from filename, mimetype, or content."""

    # Check by extension first
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return ContentType.IMAGE
        if ext in PDF_EXTENSIONS:
            return ContentType.PDF
        if ext in DOC_EXTENSIONS:
            return ContentType.DOCUMENT
        if ext in CODE_EXTENSIONS:
            return ContentType.CODE

    # Check by mimetype
    if mimetype:
        if mimetype in IMAGE_MIMETYPES or mimetype.startswith('image/'):
            return ContentType.IMAGE
        if mimetype in PDF_MIMETYPES:
            return ContentType.PDF
        if mimetype.startswith('text/'):
            return ContentType.DOCUMENT

    # Check by content magic bytes
    if content and len(content) >= 8:
        # PNG
        if content[:8] == b'\x89PNG\r\n\x1a\n':
            return ContentType.IMAGE
        # JPEG
        if content[:2] == b'\xff\xd8':
            return ContentType.IMAGE
        # PDF
        if content[:4] == b'%PDF':
            return ContentType.PDF
        # GIF
        if content[:6] in (b'GIF87a', b'GIF89a'):
            return ContentType.IMAGE

    return ContentType.UNKNOWN


def is_url(text: str) -> bool:
    """Check if text is a URL."""
    return text.startswith(('http://', 'https://', 'ftp://'))


# =============================================================================
# Unified Ingest Pipeline
# =============================================================================

class UnifiedIngestPipeline:
    """
    Unified ingestion pipeline for all content types.

    Handles files, URLs, clipboard, and text input.
    Routes to appropriate processing pipeline.
    Stores results in knowledge base.
    """

    def __init__(self, config: Optional[IngestConfig] = None):
        self.config = config or IngestConfig()
        self.items: Dict[str, IngestItem] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._progress_subscribers: Dict[str, List[asyncio.Queue]] = {}

        # Ensure storage directory exists
        Path(self.config.storage_dir).mkdir(parents=True, exist_ok=True)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def _update_progress(self, item: IngestItem, progress: int, step: str):
        """Update item progress and notify subscribers."""
        item.progress = progress
        item.current_step = step

        # Notify SSE subscribers
        if item.id in self._progress_subscribers:
            event = {
                "id": item.id,
                "progress": progress,
                "step": step,
                "status": item.status.value,
            }
            for queue in self._progress_subscribers[item.id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def subscribe_progress(self, item_id: str) -> asyncio.Queue:
        """Subscribe to progress updates for an item."""
        if item_id not in self._progress_subscribers:
            self._progress_subscribers[item_id] = []

        queue = asyncio.Queue(maxsize=100)
        self._progress_subscribers[item_id].append(queue)
        return queue

    def unsubscribe_progress(self, item_id: str, queue: asyncio.Queue):
        """Unsubscribe from progress updates."""
        if item_id in self._progress_subscribers:
            try:
                self._progress_subscribers[item_id].remove(queue)
            except ValueError:
                pass

    # =========================================================================
    # Main Ingestion Methods
    # =========================================================================

    async def ingest_file(
        self,
        content: bytes,
        filename: str,
        mimetype: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> IngestItem:
        """Ingest a file upload."""
        item_id = str(uuid.uuid4())[:8]
        content_type = detect_content_type(filename, mimetype, content)

        item = IngestItem(
            id=item_id,
            source=IngestSource.UPLOAD,
            content_type=content_type,
            filename=filename,
            raw_size=len(content),
        )

        self.items[item_id] = item
        INGEST_TOTAL.labels(content_type=content_type.value, source="upload").inc()

        # Save file to storage
        file_path = Path(self.config.storage_dir) / f"{item_id}_{filename}"
        with open(file_path, 'wb') as f:
            f.write(content)
        item.file_path = str(file_path)

        # Process in background
        asyncio.create_task(self._process_item(item, content, topic))

        return item

    async def ingest_clipboard(
        self,
        image_base64: str,
        topic: Optional[str] = None,
    ) -> IngestItem:
        """Ingest a clipboard paste (base64 image)."""
        item_id = str(uuid.uuid4())[:8]

        # Decode base64
        try:
            # Handle data URL format
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            content = base64.b64decode(image_base64)
        except Exception as e:
            raise ValueError(f"Invalid base64 image: {e}")

        content_type = detect_content_type(content=content)
        if content_type != ContentType.IMAGE:
            content_type = ContentType.IMAGE  # Assume image for clipboard

        item = IngestItem(
            id=item_id,
            source=IngestSource.CLIPBOARD,
            content_type=content_type,
            filename=f"clipboard_{item_id}.png",
            raw_size=len(content),
        )

        self.items[item_id] = item
        INGEST_TOTAL.labels(content_type=content_type.value, source="clipboard").inc()

        # Save to storage
        file_path = Path(self.config.storage_dir) / f"{item_id}_clipboard.png"
        with open(file_path, 'wb') as f:
            f.write(content)
        item.file_path = str(file_path)

        # Process in background
        asyncio.create_task(self._process_item(item, content, topic))

        return item

    async def ingest_url(
        self,
        url: str,
        topic: Optional[str] = None,
    ) -> IngestItem:
        """Ingest a URL."""
        item_id = str(uuid.uuid4())[:8]

        item = IngestItem(
            id=item_id,
            source=IngestSource.URL,
            content_type=ContentType.URL,
            url=url,
        )

        self.items[item_id] = item
        INGEST_TOTAL.labels(content_type="url", source="url").inc()

        # Process in background
        asyncio.create_task(self._process_url(item, topic))

        return item

    async def ingest_text(
        self,
        text: str,
        title: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> IngestItem:
        """Ingest raw text."""
        item_id = str(uuid.uuid4())[:8]

        item = IngestItem(
            id=item_id,
            source=IngestSource.TEXT,
            content_type=ContentType.TEXT,
            raw_size=len(text),
            extracted_text=text,
            extracted_length=len(text),
            title=title,
        )

        self.items[item_id] = item
        INGEST_TOTAL.labels(content_type="text", source="text").inc()

        # Process in background
        asyncio.create_task(self._process_text(item, topic))

        return item

    # =========================================================================
    # Processing Pipelines
    # =========================================================================

    async def _process_item(
        self,
        item: IngestItem,
        content: bytes,
        topic: Optional[str] = None
    ):
        """Process uploaded file based on content type."""
        start_time = time.time()
        item.started_at = datetime.utcnow().isoformat() + "Z"
        item.status = IngestStatus.PROCESSING
        INGEST_ACTIVE.inc()

        try:
            self._update_progress(item, 10, "detecting content type")

            if item.content_type == ContentType.IMAGE:
                await self._process_image(item, content, topic)
            elif item.content_type == ContentType.PDF:
                await self._process_pdf(item, content, topic)
            elif item.content_type in (ContentType.DOCUMENT, ContentType.CODE):
                await self._process_document(item, content, topic)
            else:
                # Try as text
                try:
                    text = content.decode('utf-8')
                    item.extracted_text = text
                    item.extracted_length = len(text)
                    await self._analyze_and_store(item, topic)
                except UnicodeDecodeError:
                    item.status = IngestStatus.FAILED
                    item.error = "Unknown content type and not valid text"

            if item.status != IngestStatus.FAILED:
                item.status = IngestStatus.COMPLETED
                INGEST_PROCESSED.labels(status="success", content_type=item.content_type.value).inc()

        except Exception as e:
            logger.error(f"Failed to process item {item.id}: {e}")
            item.status = IngestStatus.FAILED
            item.error = str(e)
            INGEST_PROCESSED.labels(status="failed", content_type=item.content_type.value).inc()

        finally:
            item.completed_at = datetime.utcnow().isoformat() + "Z"
            INGEST_ACTIVE.dec()
            INGEST_LATENCY.observe(time.time() - start_time)
            self._update_progress(item, 100, "completed" if item.status == IngestStatus.COMPLETED else "failed")

    async def _process_image(
        self,
        item: IngestItem,
        content: bytes,
        topic: Optional[str] = None
    ):
        """Process image through Vision API."""
        self._update_progress(item, 20, "encoding image")
        item.status = IngestStatus.EXTRACTING

        # Encode to base64
        image_b64 = base64.b64encode(content).decode()

        self._update_progress(item, 30, "analyzing with vision model")
        item.status = IngestStatus.ANALYZING

        # Call Vision API for description
        try:
            response = await self.client.post(
                f"{self.config.vision_url}/vision/describe",
                json={
                    "image_base64": image_b64,
                    "detail_level": "detailed",
                },
                timeout=120.0
            )

            if response.status_code == 200:
                data = response.json()
                item.image_description = data.get("description", "")
                self._update_progress(item, 50, "description generated")
        except Exception as e:
            logger.warning(f"Vision describe failed: {e}")

        # OCR if it looks like it has text
        self._update_progress(item, 60, "extracting text (OCR)")
        try:
            response = await self.client.post(
                f"{self.config.vision_url}/vision/ocr",
                json={"image_base64": image_b64},
                timeout=120.0
            )

            if response.status_code == 200:
                data = response.json()
                item.ocr_text = data.get("description", "")
                if item.ocr_text:
                    item.extracted_text = item.ocr_text
                    item.extracted_length = len(item.ocr_text)
        except Exception as e:
            logger.warning(f"Vision OCR failed: {e}")

        # Build combined text for analysis
        combined = []
        if item.image_description:
            combined.append(f"Image Description: {item.image_description}")
        if item.ocr_text:
            combined.append(f"Extracted Text: {item.ocr_text}")

        if combined:
            item.extracted_text = "\n\n".join(combined)
            item.extracted_length = len(item.extracted_text)

        self._update_progress(item, 70, "generating insights")
        await self._analyze_and_store(item, topic)

    async def _process_pdf(
        self,
        item: IngestItem,
        content: bytes,
        topic: Optional[str] = None
    ):
        """Process PDF - extract text and analyze."""
        self._update_progress(item, 20, "extracting text from PDF")
        item.status = IngestStatus.EXTRACTING

        extracted_text = ""

        # Try PyMuPDF first
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=content, filetype="pdf")
            pages_text = []

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()
            extracted_text = "\n\n".join(pages_text)

        except ImportError:
            logger.warning("PyMuPDF not available, trying pdfplumber")

            # Fallback to pdfplumber
            try:
                import pdfplumber

                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    pages_text = []
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        if text.strip():
                            pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

                    extracted_text = "\n\n".join(pages_text)

            except ImportError:
                logger.warning("pdfplumber not available, trying pypdf")

                # Fallback to pypdf
                try:
                    from pypdf import PdfReader

                    reader = PdfReader(io.BytesIO(content))
                    pages_text = []

                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        if text.strip():
                            pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

                    extracted_text = "\n\n".join(pages_text)

                except ImportError:
                    logger.error("No PDF library available")
                    item.error = "No PDF extraction library available"
                    item.status = IngestStatus.FAILED
                    return

        if not extracted_text.strip():
            # PDF might be image-based, try OCR via Vision
            self._update_progress(item, 40, "PDF appears to be image-based, trying OCR")
            # For now, mark as limited extraction
            item.extracted_text = "(PDF appears to be image-based. Text extraction limited.)"
            item.extracted_length = 0
        else:
            item.extracted_text = extracted_text[:self.config.max_text_length]
            item.extracted_length = len(extracted_text)

        self._update_progress(item, 60, "analyzing content")
        await self._analyze_and_store(item, topic)

    async def _process_document(
        self,
        item: IngestItem,
        content: bytes,
        topic: Optional[str] = None
    ):
        """Process text document or code file."""
        self._update_progress(item, 20, "reading document")
        item.status = IngestStatus.EXTRACTING

        # Try to decode as text
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except:
                item.status = IngestStatus.FAILED
                item.error = "Could not decode document as text"
                return

        item.extracted_text = text[:self.config.max_text_length]
        item.extracted_length = len(text)

        self._update_progress(item, 50, "analyzing content")
        await self._analyze_and_store(item, topic)

    async def _process_url(
        self,
        item: IngestItem,
        topic: Optional[str] = None
    ):
        """Process URL by delegating to research queue."""
        start_time = time.time()
        item.started_at = datetime.utcnow().isoformat() + "Z"
        item.status = IngestStatus.PROCESSING
        INGEST_ACTIVE.inc()

        try:
            self._update_progress(item, 10, "submitting to research queue")

            # Determine source type
            url = item.url
            source_type = "url"
            if "github.com" in url:
                source_type = "github"
            elif "arxiv.org" in url:
                source_type = "arxiv"

            # Submit to research queue
            response = await self.client.post(
                f"{self.config.vision_url}/research/queue",
                json={
                    "source": url,
                    "source_type": source_type,
                    "topic": topic,
                    "priority": "high",
                    "process_immediately": True,
                }
            )

            if response.status_code != 200:
                raise Exception(f"Research queue error: {response.status_code}")

            queue_item = response.json()
            queue_id = queue_item.get("id")

            self._update_progress(item, 30, "waiting for research queue processing")

            # Poll for completion
            max_attempts = 60  # 5 minutes max
            for attempt in range(max_attempts):
                await asyncio.sleep(5)

                status_response = await self.client.get(
                    f"{self.config.vision_url}/research/queue/{queue_id}"
                )

                if status_response.status_code != 200:
                    continue

                status_data = status_response.json()
                status = status_data.get("status")

                progress = min(30 + (attempt * 60 // max_attempts), 90)
                self._update_progress(item, progress, f"research queue: {status}")

                if status == "completed":
                    # Copy results
                    item.title = status_data.get("title")
                    item.summary = status_data.get("summary")
                    item.key_insights = status_data.get("key_insights", [])
                    item.relevance_to_hydra = status_data.get("relevance_to_hydra")
                    item.action_items = status_data.get("action_items", [])
                    item.tags = status_data.get("tags", [])
                    item.status = IngestStatus.COMPLETED
                    break
                elif status == "failed":
                    item.error = status_data.get("error", "Research queue processing failed")
                    item.status = IngestStatus.FAILED
                    break
            else:
                item.error = "Research queue processing timed out"
                item.status = IngestStatus.FAILED

            if item.status == IngestStatus.COMPLETED:
                INGEST_PROCESSED.labels(status="success", content_type="url").inc()
            else:
                INGEST_PROCESSED.labels(status="failed", content_type="url").inc()

        except Exception as e:
            logger.error(f"Failed to process URL {item.id}: {e}")
            item.status = IngestStatus.FAILED
            item.error = str(e)
            INGEST_PROCESSED.labels(status="failed", content_type="url").inc()

        finally:
            item.completed_at = datetime.utcnow().isoformat() + "Z"
            INGEST_ACTIVE.dec()
            INGEST_LATENCY.observe(time.time() - start_time)
            self._update_progress(item, 100, "completed" if item.status == IngestStatus.COMPLETED else "failed")

    async def _process_text(
        self,
        item: IngestItem,
        topic: Optional[str] = None
    ):
        """Process raw text input."""
        start_time = time.time()
        item.started_at = datetime.utcnow().isoformat() + "Z"
        item.status = IngestStatus.ANALYZING
        INGEST_ACTIVE.inc()

        try:
            self._update_progress(item, 30, "analyzing text")
            await self._analyze_and_store(item, topic)
            item.status = IngestStatus.COMPLETED
            INGEST_PROCESSED.labels(status="success", content_type="text").inc()

        except Exception as e:
            logger.error(f"Failed to process text {item.id}: {e}")
            item.status = IngestStatus.FAILED
            item.error = str(e)
            INGEST_PROCESSED.labels(status="failed", content_type="text").inc()

        finally:
            item.completed_at = datetime.utcnow().isoformat() + "Z"
            INGEST_ACTIVE.dec()
            INGEST_LATENCY.observe(time.time() - start_time)
            self._update_progress(item, 100, "completed" if item.status == IngestStatus.COMPLETED else "failed")

    # =========================================================================
    # Analysis and Storage
    # =========================================================================

    async def _analyze_and_store(
        self,
        item: IngestItem,
        topic: Optional[str] = None
    ):
        """Analyze extracted content with LLM and store to Qdrant."""
        item.status = IngestStatus.ANALYZING

        content = item.extracted_text or item.image_description or ""
        if not content:
            return

        # Truncate if needed
        if len(content) > self.config.max_text_length:
            content = content[:self.config.max_text_length] + "\n\n[Content truncated...]"

        topic_context = f"Topic: {topic}\n\n" if topic else ""
        filename_context = f"Filename: {item.filename}\n\n" if item.filename else ""

        prompt = f"""Analyze this content and extract key information for a home AI cluster called Hydra.

{topic_context}{filename_context}Content:
{content}

Provide your analysis in the following JSON format (no comments, valid JSON only):
{{
    "title": "Title or name of the content",
    "summary": "2-3 paragraph summary of the main points",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "entities": ["technology/framework/concept mentioned"],
    "relevance_to_hydra": "How this relates to building autonomous AI systems, inference optimization, agent orchestration, or self-improvement",
    "action_items": ["specific action Hydra could take based on this"],
    "tags": ["tag1", "tag2"]
}}

Focus on practical insights for AI infrastructure, agent frameworks, LLM optimization, and autonomous systems."""

        try:
            response = await self.client.post(
                f"{self.config.llm_url}/chat/completions",
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {self.config.llm_api_key}"},
            )

            if response.status_code == 200:
                data = response.json()
                result_text = data["choices"][0]["message"]["content"]

                # Extract JSON
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group())

                        item.title = analysis.get("title", item.title)
                        item.summary = analysis.get("summary")
                        item.key_insights = analysis.get("key_insights", [])
                        item.entities = analysis.get("entities", [])
                        item.relevance_to_hydra = analysis.get("relevance_to_hydra")
                        item.action_items = analysis.get("action_items", [])
                        item.tags = analysis.get("tags", [])
                    except json.JSONDecodeError:
                        # Use raw text as summary
                        item.summary = result_text

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")

        # Store to Qdrant
        self._update_progress(item, 85, "storing to knowledge base")
        item.status = IngestStatus.STORING
        await self._store_to_qdrant(item)

    async def _store_to_qdrant(self, item: IngestItem):
        """Store processed item to Qdrant."""
        try:
            # Generate embedding
            embed_text = f"{item.title or ''}\n{item.summary or ''}\n{item.extracted_text or ''}"[:8000]

            response = await self.client.post(
                self.config.embedding_url,
                json={
                    "model": self.config.embedding_model,
                    "prompt": embed_text
                }
            )

            if response.status_code != 200:
                logger.warning(f"Embedding failed: {response.status_code}")
                return

            embedding = response.json().get("embedding", [])
            if not embedding:
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
                            "ingest_id": item.id,
                            "source": item.source.value,
                            "content_type": item.content_type.value,
                            "filename": item.filename,
                            "url": item.url,
                            "title": item.title,
                            "summary": item.summary,
                            "key_insights": item.key_insights,
                            "entities": item.entities,
                            "relevance_to_hydra": item.relevance_to_hydra,
                            "action_items": item.action_items,
                            "tags": item.tags,
                            "created_at": item.created_at,
                        }
                    }]
                }
            )

            if qdrant_response.status_code in (200, 201):
                item.stored_to_qdrant = True
                item.qdrant_id = point_id
                logger.info(f"Stored ingest {item.id} to Qdrant as {point_id}")

        except Exception as e:
            logger.error(f"Failed to store to Qdrant: {e}")

    # =========================================================================
    # Retrieval
    # =========================================================================

    def get(self, item_id: str) -> Optional[IngestItem]:
        """Get item by ID."""
        return self.items.get(item_id)

    def list_items(self, limit: int = 50) -> List[IngestItem]:
        """List recent items."""
        items = sorted(
            self.items.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return items[:limit]

    async def close(self):
        """Close resources."""
        if self._client:
            await self._client.aclose()


# =============================================================================
# Global Instance
# =============================================================================

_pipeline_instance: Optional[UnifiedIngestPipeline] = None


def get_ingest_pipeline() -> UnifiedIngestPipeline:
    """Get the global ingest pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = UnifiedIngestPipeline()
    return _pipeline_instance


# =============================================================================
# FastAPI Router
# =============================================================================

def create_ingest_router():
    """Create FastAPI router for unified ingest endpoints."""
    from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    from typing import Optional, List

    router = APIRouter(prefix="/ingest", tags=["ingest"])

    class IngestResponse(BaseModel):
        id: str
        source: str
        content_type: str
        status: str
        progress: int
        current_step: str
        filename: Optional[str] = None
        url: Optional[str] = None
        title: Optional[str] = None
        summary: Optional[str] = None
        key_insights: List[str] = []
        relevance_to_hydra: Optional[str] = None
        action_items: List[str] = []
        tags: List[str] = []
        error: Optional[str] = None

    class ClipboardRequest(BaseModel):
        image_base64: str
        topic: Optional[str] = None

    class UrlRequest(BaseModel):
        url: str
        topic: Optional[str] = None

    class TextRequest(BaseModel):
        text: str
        title: Optional[str] = None
        topic: Optional[str] = None

    def item_to_response(item: IngestItem) -> IngestResponse:
        return IngestResponse(
            id=item.id,
            source=item.source.value,
            content_type=item.content_type.value,
            status=item.status.value,
            progress=item.progress,
            current_step=item.current_step,
            filename=item.filename,
            url=item.url,
            title=item.title,
            summary=item.summary,
            key_insights=item.key_insights,
            relevance_to_hydra=item.relevance_to_hydra,
            action_items=item.action_items,
            tags=item.tags,
            error=item.error,
        )

    @router.post("", response_model=IngestResponse)
    async def ingest_file(
        file: UploadFile = File(...),
        topic: Optional[str] = Form(None),
    ):
        """
        Upload a file for ingestion.

        Supports:
        - Images (jpg, png, gif, webp) → Vision analysis + OCR
        - PDFs → Text extraction + analysis
        - Documents (txt, md, docx) → Text analysis
        - Code files → Syntax analysis

        Returns immediately with item ID. Poll /ingest/{id} for results.
        """
        pipeline = get_ingest_pipeline()

        content = await file.read()
        if len(content) > pipeline.config.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {pipeline.config.max_file_size // 1024 // 1024}MB"
            )

        item = await pipeline.ingest_file(
            content=content,
            filename=file.filename or "unknown",
            mimetype=file.content_type,
            topic=topic,
        )

        return item_to_response(item)

    @router.post("/clipboard", response_model=IngestResponse)
    async def ingest_clipboard(request: ClipboardRequest):
        """
        Ingest a clipboard paste (base64-encoded image).

        For Ctrl+V paste from Command Center UI.
        Accepts data URL format (data:image/png;base64,...) or raw base64.
        """
        pipeline = get_ingest_pipeline()

        item = await pipeline.ingest_clipboard(
            image_base64=request.image_base64,
            topic=request.topic,
        )

        return item_to_response(item)

    @router.post("/url", response_model=IngestResponse)
    async def ingest_url(request: UrlRequest):
        """
        Ingest a URL.

        Delegates to research queue for processing.
        Supports web pages, GitHub repos, arXiv papers.
        """
        pipeline = get_ingest_pipeline()

        if not request.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL")

        item = await pipeline.ingest_url(
            url=request.url,
            topic=request.topic,
        )

        return item_to_response(item)

    @router.post("/text", response_model=IngestResponse)
    async def ingest_text(request: TextRequest):
        """
        Ingest raw text content.

        For pasting text directly into Command Center.
        """
        pipeline = get_ingest_pipeline()

        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Empty text")

        item = await pipeline.ingest_text(
            text=request.text,
            title=request.title,
            topic=request.topic,
        )

        return item_to_response(item)

    @router.get("/{item_id}", response_model=IngestResponse)
    async def get_ingest_status(item_id: str):
        """Get status and results of an ingestion."""
        pipeline = get_ingest_pipeline()
        item = pipeline.get(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return item_to_response(item)

    @router.get("/{item_id}/stream")
    async def stream_progress(item_id: str):
        """
        SSE stream for real-time progress updates.

        Connect to this endpoint to receive progress events:
        - progress: 0-100
        - step: current processing step
        - status: pending/processing/completed/failed
        """
        pipeline = get_ingest_pipeline()
        item = pipeline.get(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        async def event_generator():
            queue = pipeline.subscribe_progress(item_id)

            try:
                # Send initial state
                yield f"data: {json.dumps({'id': item_id, 'progress': item.progress, 'step': item.current_step, 'status': item.status.value})}\n\n"

                # Stream updates
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"data: {json.dumps(event)}\n\n"

                        if event.get("status") in ("completed", "failed"):
                            break
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield f": keepalive\n\n"

                        # Check if item is done
                        current = pipeline.get(item_id)
                        if current and current.status in (IngestStatus.COMPLETED, IngestStatus.FAILED):
                            yield f"data: {json.dumps({'id': item_id, 'progress': current.progress, 'step': current.current_step, 'status': current.status.value})}\n\n"
                            break

            finally:
                pipeline.unsubscribe_progress(item_id, queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    @router.get("", response_model=List[IngestResponse])
    async def list_ingests(limit: int = 50):
        """List recent ingestions."""
        pipeline = get_ingest_pipeline()
        items = pipeline.list_items(limit=limit)
        return [item_to_response(i) for i in items]

    @router.get("/stats/summary")
    async def get_ingest_stats():
        """Get ingestion statistics."""
        pipeline = get_ingest_pipeline()
        items = list(pipeline.items.values())

        by_status = {}
        for status in IngestStatus:
            by_status[status.value] = len([i for i in items if i.status == status])

        by_type = {}
        for ct in ContentType:
            by_type[ct.value] = len([i for i in items if i.content_type == ct])

        by_source = {}
        for source in IngestSource:
            by_source[source.value] = len([i for i in items if i.source == source])

        return {
            "total": len(items),
            "by_status": by_status,
            "by_content_type": by_type,
            "by_source": by_source,
        }

    return router
