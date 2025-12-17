"""
Hydra Vision Integration

Multi-modal vision processing for image understanding, analysis, and OCR.
Supports local vision models (LLaVA via Ollama) and external providers.

Capabilities:
- Image description/captioning
- Visual question answering
- OCR text extraction
- Screenshot analysis
- Object detection descriptions
- Image comparison

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import base64
import io
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

VISION_REQUESTS = Counter(
    "hydra_vision_requests_total",
    "Total vision model requests",
    ["task_type", "model"]
)

VISION_LATENCY = Histogram(
    "hydra_vision_latency_seconds",
    "Vision processing latency",
    ["task_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

VISION_ERRORS = Counter(
    "hydra_vision_errors_total",
    "Vision processing errors",
    ["error_type"]
)

# =============================================================================
# Enums and Types
# =============================================================================

class VisionTask(Enum):
    """Types of vision tasks."""
    DESCRIBE = "describe"  # Generate image description
    QUESTION = "question"  # Answer question about image
    OCR = "ocr"  # Extract text from image
    ANALYZE = "analyze"  # Detailed analysis
    COMPARE = "compare"  # Compare multiple images


class VisionModel(Enum):
    """Supported vision models."""
    LLAVA_7B = "llava:7b"
    LLAVA_13B = "llava:13b"
    LLAVA_LLAMA3 = "llava-llama3:8b"
    BAKLLAVA = "bakllava:7b"


@dataclass
class VisionResult:
    """Result of a vision processing request."""
    task: VisionTask
    response: str
    model: str
    latency_ms: float
    image_size: Optional[Tuple[int, int]] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class VisionConfig:
    """Configuration for vision processing."""
    # Ollama endpoint
    ollama_url: str = "http://192.168.1.203:11434"

    # Default model
    default_model: str = "llava:7b"

    # Fallback models in order of preference
    fallback_models: List[str] = field(default_factory=lambda: [
        "llava:7b",
        "llava-llama3:8b",
        "bakllava:7b",
    ])

    # Processing settings
    max_image_size: int = 4096  # Max dimension in pixels
    jpeg_quality: int = 85  # JPEG compression quality
    timeout: float = 120.0  # Request timeout

    # Prompts for different tasks
    prompts: Dict[str, str] = field(default_factory=lambda: {
        "describe": "Describe this image in detail. Include objects, people, text, colors, and any notable features.",
        "ocr": "Extract and list all visible text from this image. Format the text as it appears.",
        "analyze": "Provide a comprehensive analysis of this image including: 1) Main subject, 2) Objects present, 3) Any text visible, 4) Colors and composition, 5) Context or setting, 6) Notable details.",
    })


# =============================================================================
# Vision Processor Implementation
# =============================================================================

class VisionProcessor:
    """
    Multi-modal vision processor.

    Handles image analysis using local vision models (LLaVA via Ollama).
    Supports various vision tasks including description, Q&A, and OCR.
    """

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._client = None
        self._available_models: Optional[List[str]] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout)
            )
        return self._client

    # =========================================================================
    # Model Management
    # =========================================================================

    async def get_available_models(self, refresh: bool = False) -> List[str]:
        """Get list of available vision models."""
        if self._available_models is not None and not refresh:
            return self._available_models

        try:
            response = await self.client.get(f"{self.config.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                all_models = [m["name"] for m in data.get("models", [])]
                # Filter to vision-capable models
                vision_keywords = ["llava", "bakllava", "vision", "vl"]
                self._available_models = [
                    m for m in all_models
                    if any(kw in m.lower() for kw in vision_keywords)
                ]
                return self._available_models
        except Exception as e:
            logger.warning(f"Failed to get available models: {e}")

        return []

    async def get_best_model(self) -> Optional[str]:
        """Get the best available vision model."""
        available = await self.get_available_models()

        # Try default model first
        if self.config.default_model in available:
            return self.config.default_model

        # Try fallbacks
        for model in self.config.fallback_models:
            if model in available:
                return model

        # Return first available
        return available[0] if available else None

    async def ensure_model_available(self, model: str) -> bool:
        """Ensure a model is available, pulling if needed."""
        available = await self.get_available_models(refresh=True)

        if model in available:
            return True

        # Try to pull the model
        logger.info(f"Pulling vision model: {model}")
        try:
            response = await self.client.post(
                f"{self.config.ollama_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=600.0,  # 10 min timeout for pulling
            )
            if response.status_code == 200:
                self._available_models = None  # Refresh cache
                return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")

        return False

    # =========================================================================
    # Image Processing
    # =========================================================================

    def _load_image(self, image_source: Union[str, bytes, Path]) -> Tuple[bytes, str]:
        """Load image from various sources and return as base64."""
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("PIL is required for image processing. Install with: pip install Pillow")

        # Load image bytes
        if isinstance(image_source, bytes):
            image_bytes = image_source
        elif isinstance(image_source, (str, Path)):
            path = Path(image_source)
            if path.exists():
                image_bytes = path.read_bytes()
            elif str(image_source).startswith(('http://', 'https://')):
                # URL - would need to fetch
                raise ValueError("URL images not yet supported. Provide local path or bytes.")
            elif str(image_source).startswith('data:image'):
                # Base64 data URL
                _, data = str(image_source).split(',', 1)
                image_bytes = base64.b64decode(data)
            else:
                raise ValueError(f"Image not found: {image_source}")
        else:
            raise ValueError(f"Unsupported image source type: {type(image_source)}")

        # Process with PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Get original size
        original_size = img.size

        # Resize if too large
        max_dim = self.config.max_image_size
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to RGB if needed (for JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.config.jpeg_quality)
        processed_bytes = buffer.getvalue()

        # Encode to base64
        b64_image = base64.b64encode(processed_bytes).decode('utf-8')

        return b64_image, f"{original_size[0]}x{original_size[1]}"

    # =========================================================================
    # Vision Tasks
    # =========================================================================

    async def describe(
        self,
        image: Union[str, bytes, Path],
        detail_level: str = "normal",
        model: Optional[str] = None,
    ) -> VisionResult:
        """Generate a description of an image."""
        prompt = self.config.prompts["describe"]
        if detail_level == "brief":
            prompt = "Briefly describe this image in 1-2 sentences."
        elif detail_level == "detailed":
            prompt = self.config.prompts["analyze"]

        return await self._process_vision(
            image=image,
            prompt=prompt,
            task=VisionTask.DESCRIBE,
            model=model,
        )

    async def question(
        self,
        image: Union[str, bytes, Path],
        question: str,
        model: Optional[str] = None,
    ) -> VisionResult:
        """Answer a question about an image."""
        return await self._process_vision(
            image=image,
            prompt=question,
            task=VisionTask.QUESTION,
            model=model,
        )

    async def ocr(
        self,
        image: Union[str, bytes, Path],
        model: Optional[str] = None,
    ) -> VisionResult:
        """Extract text from an image."""
        return await self._process_vision(
            image=image,
            prompt=self.config.prompts["ocr"],
            task=VisionTask.OCR,
            model=model,
        )

    async def analyze(
        self,
        image: Union[str, bytes, Path],
        focus: Optional[str] = None,
        model: Optional[str] = None,
    ) -> VisionResult:
        """Perform detailed analysis of an image."""
        prompt = self.config.prompts["analyze"]
        if focus:
            prompt = f"{prompt}\n\nPay special attention to: {focus}"

        return await self._process_vision(
            image=image,
            prompt=prompt,
            task=VisionTask.ANALYZE,
            model=model,
        )

    async def analyze_screenshot(
        self,
        image: Union[str, bytes, Path],
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> VisionResult:
        """Analyze a screenshot with UI-specific understanding."""
        prompt = """Analyze this screenshot. Identify:
1. What application or website is shown
2. Key UI elements visible (buttons, menus, text fields)
3. Any text content visible
4. The current state or page being shown
5. Any errors, notifications, or important information"""

        if context:
            prompt = f"{prompt}\n\nContext: {context}"

        return await self._process_vision(
            image=image,
            prompt=prompt,
            task=VisionTask.ANALYZE,
            model=model,
        )

    # =========================================================================
    # Core Processing
    # =========================================================================

    async def _process_vision(
        self,
        image: Union[str, bytes, Path],
        prompt: str,
        task: VisionTask,
        model: Optional[str] = None,
    ) -> VisionResult:
        """Process a vision request."""
        start_time = time.time()

        # Get model
        if model is None:
            model = await self.get_best_model()
            if model is None:
                VISION_ERRORS.labels(error_type="no_model").inc()
                return VisionResult(
                    task=task,
                    response="No vision model available. Please install llava:7b or another vision model.",
                    model="none",
                    latency_ms=0,
                    confidence=0.0,
                )

        try:
            # Load and encode image
            b64_image, image_size = self._load_image(image)
            size_tuple = tuple(map(int, image_size.split('x')))

            # Call Ollama API
            response = await self.client.post(
                f"{self.config.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [b64_image],
                        }
                    ],
                    "stream": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                result_text = data.get("message", {}).get("content", "")

                latency_ms = (time.time() - start_time) * 1000

                VISION_REQUESTS.labels(task_type=task.value, model=model).inc()
                VISION_LATENCY.labels(task_type=task.value).observe(latency_ms / 1000)

                return VisionResult(
                    task=task,
                    response=result_text,
                    model=model,
                    latency_ms=latency_ms,
                    image_size=size_tuple,
                    confidence=1.0,
                    metadata={
                        "prompt_length": len(prompt),
                        "response_length": len(result_text),
                    }
                )
            else:
                VISION_ERRORS.labels(error_type="api_error").inc()
                return VisionResult(
                    task=task,
                    response=f"Vision API error: {response.status_code}",
                    model=model,
                    latency_ms=(time.time() - start_time) * 1000,
                    confidence=0.0,
                )

        except Exception as e:
            VISION_ERRORS.labels(error_type="processing_error").inc()
            logger.error(f"Vision processing error: {e}")
            return VisionResult(
                task=task,
                response=f"Vision processing error: {str(e)}",
                model=model or "unknown",
                latency_ms=(time.time() - start_time) * 1000,
                confidence=0.0,
            )

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# Global Instance
# =============================================================================

_vision_instance: Optional[VisionProcessor] = None


def get_vision_processor() -> VisionProcessor:
    """Get the global VisionProcessor instance."""
    global _vision_instance
    if _vision_instance is None:
        _vision_instance = VisionProcessor()
    return _vision_instance


# =============================================================================
# FastAPI Router
# =============================================================================

def create_vision_router():
    """Create FastAPI router for vision endpoints."""
    from fastapi import APIRouter, HTTPException, UploadFile, File, Form
    from pydantic import BaseModel

    router = APIRouter(prefix="/vision", tags=["vision"])

    class DescribeRequest(BaseModel):
        image_path: Optional[str] = None
        image_base64: Optional[str] = None
        detail_level: str = "normal"  # brief, normal, detailed
        model: Optional[str] = None

    class QuestionRequest(BaseModel):
        image_path: Optional[str] = None
        image_base64: Optional[str] = None
        question: str
        model: Optional[str] = None

    class AnalyzeRequest(BaseModel):
        image_path: Optional[str] = None
        image_base64: Optional[str] = None
        focus: Optional[str] = None
        model: Optional[str] = None

    class VisionResponse(BaseModel):
        task: str
        response: str
        model: str
        latency_ms: float
        image_size: Optional[List[int]] = None
        confidence: float

    def _get_image_source(request) -> Union[str, bytes]:
        """Extract image source from request."""
        if hasattr(request, 'image_path') and request.image_path:
            return request.image_path
        elif hasattr(request, 'image_base64') and request.image_base64:
            return base64.b64decode(request.image_base64)
        else:
            raise HTTPException(status_code=400, detail="Provide image_path or image_base64")

    @router.get("/health")
    async def vision_health():
        """Check vision service health and available models."""
        processor = get_vision_processor()
        models = await processor.get_available_models(refresh=True)
        best_model = await processor.get_best_model()

        return {
            "status": "healthy" if models else "no_models",
            "available_models": models,
            "default_model": processor.config.default_model,
            "best_available": best_model,
        }

    @router.get("/models")
    async def list_vision_models():
        """List available vision models."""
        processor = get_vision_processor()
        models = await processor.get_available_models(refresh=True)
        return {"models": models}

    @router.post("/pull/{model_name}")
    async def pull_vision_model(model_name: str):
        """Pull a vision model."""
        processor = get_vision_processor()
        success = await processor.ensure_model_available(model_name)
        return {
            "model": model_name,
            "available": success,
        }

    @router.post("/describe", response_model=VisionResponse)
    async def describe_image(request: DescribeRequest):
        """Generate a description of an image."""
        processor = get_vision_processor()
        image = _get_image_source(request)

        result = await processor.describe(
            image=image,
            detail_level=request.detail_level,
            model=request.model,
        )

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    @router.post("/question", response_model=VisionResponse)
    async def question_image(request: QuestionRequest):
        """Answer a question about an image."""
        processor = get_vision_processor()
        image = _get_image_source(request)

        result = await processor.question(
            image=image,
            question=request.question,
            model=request.model,
        )

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    @router.post("/ocr", response_model=VisionResponse)
    async def ocr_image(request: DescribeRequest):
        """Extract text from an image."""
        processor = get_vision_processor()
        image = _get_image_source(request)

        result = await processor.ocr(
            image=image,
            model=request.model,
        )

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    @router.post("/analyze", response_model=VisionResponse)
    async def analyze_image(request: AnalyzeRequest):
        """Perform detailed analysis of an image."""
        processor = get_vision_processor()
        image = _get_image_source(request)

        result = await processor.analyze(
            image=image,
            focus=request.focus,
            model=request.model,
        )

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    @router.post("/screenshot", response_model=VisionResponse)
    async def analyze_screenshot(request: AnalyzeRequest):
        """Analyze a screenshot with UI understanding."""
        processor = get_vision_processor()
        image = _get_image_source(request)

        result = await processor.analyze_screenshot(
            image=image,
            context=request.focus,
            model=request.model,
        )

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    @router.post("/upload")
    async def upload_and_analyze(
        file: UploadFile = File(...),
        task: str = Form("describe"),
        question: Optional[str] = Form(None),
        model: Optional[str] = Form(None),
    ):
        """Upload an image file and analyze it."""
        processor = get_vision_processor()

        # Read file
        image_bytes = await file.read()

        # Process based on task
        if task == "describe":
            result = await processor.describe(image_bytes, model=model)
        elif task == "question" and question:
            result = await processor.question(image_bytes, question=question, model=model)
        elif task == "ocr":
            result = await processor.ocr(image_bytes, model=model)
        elif task == "analyze":
            result = await processor.analyze(image_bytes, model=model)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown task: {task}")

        return VisionResponse(
            task=result.task.value,
            response=result.response,
            model=result.model,
            latency_ms=result.latency_ms,
            image_size=list(result.image_size) if result.image_size else None,
            confidence=result.confidence,
        )

    return router
