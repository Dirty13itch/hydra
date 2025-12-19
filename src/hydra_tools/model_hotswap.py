"""
Model Hot-Swap API - Dynamic Model Loading and Switching

Provides API endpoints for managing LLM models across the Hydra cluster:
- List available models (EXL2, Ollama)
- Get current loaded model status
- Load/unload models on TabbyAPI
- Switch models with automatic unload/load
- Get VRAM requirements and availability

Endpoints:
    GET /models/available - List all available model files
    GET /models/loaded - Get currently loaded models
    GET /models/status - Get detailed model status
    POST /models/load - Load a model
    POST /models/unload - Unload current model
    POST /models/switch - Atomically switch models
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])

# =============================================================================
# CONFIGURATION
# =============================================================================

# Model directories
EXL2_MODEL_DIR = Path(os.environ.get("EXL2_MODEL_DIR", "/mnt/models"))
OLLAMA_MODEL_DIR = Path(os.environ.get("OLLAMA_MODEL_DIR", "/mnt/user/appdata/ollama"))

# Model categories for discovery and routing
MODEL_CATEGORIES = {
    # NSFW/Uncensored creative models
    "euryale": ["creative", "nsfw", "roleplay", "writing"],
    "lumimaid": ["creative", "nsfw", "roleplay", "writing"],
    "celeste": ["creative", "nsfw", "roleplay", "writing"],
    "starcannon": ["creative", "nsfw", "roleplay", "writing"],
    "midnight-miqu": ["creative", "nsfw", "roleplay", "writing"],
    "abliterated": ["creative", "nsfw", "uncensored", "general"],
    "dolphin": ["creative", "nsfw", "general"],
    "fimbulvetr": ["creative", "nsfw", "horror", "writing"],
    "hermes": ["creative", "roleplay", "agentic", "general"],

    # Coding models
    "devstral": ["coding", "agentic", "software"],
    "deepseek-coder": ["coding", "software"],
    "qwen-coder": ["coding", "software"],
    "codestral": ["coding", "software"],

    # Reasoning models
    "deepseek-r1": ["reasoning", "thinking", "math", "logic"],
    "qwen3": ["reasoning", "general"],
    "nemotron": ["reasoning", "general"],

    # General purpose
    "llama-3": ["general", "instruction"],
    "llama-3.1": ["general", "instruction", "long-context"],
    "llama-3.2": ["general", "instruction"],
    "llama-3.3": ["general", "instruction"],
    "qwen2.5": ["general", "instruction"],
    "mistral": ["general", "instruction"],
}

# Service URLs
TABBYAPI_URL = os.environ.get("TABBYAPI_URL", "http://192.168.1.250:5000")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")
OLLAMA_CPU_URL = os.environ.get("OLLAMA_CPU_URL", "http://192.168.1.244:11434")


# =============================================================================
# DATA MODELS
# =============================================================================

class ModelInfo(BaseModel):
    name: str
    type: str  # exl2, ollama, gguf
    size_gb: Optional[float] = None
    path: Optional[str] = None
    quantization: Optional[str] = None
    context_length: Optional[int] = None
    vram_estimate_gb: Optional[float] = None
    categories: List[str] = Field(default_factory=list)
    is_nsfw: bool = False
    is_coding: bool = False
    is_reasoning: bool = False


class ChatRequest(BaseModel):
    model: str = Field(..., description="Model name or 'current' to use loaded model")
    messages: List[Dict[str, str]] = Field(..., description="Chat messages in OpenAI format")
    max_tokens: Optional[int] = Field(2048, description="Max tokens to generate")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    stream: bool = Field(False, description="Enable streaming response")


class ChatResponse(BaseModel):
    model: str
    response: str
    tokens_used: Optional[int] = None
    backend: str


def get_model_categories(model_name: str) -> List[str]:
    """Get categories for a model based on its name."""
    name_lower = model_name.lower()
    categories = []

    for keyword, cats in MODEL_CATEGORIES.items():
        if keyword in name_lower:
            categories.extend(cats)

    # Remove duplicates while preserving order
    seen = set()
    unique_categories = []
    for cat in categories:
        if cat not in seen:
            seen.add(cat)
            unique_categories.append(cat)

    return unique_categories if unique_categories else ["general"]


class LoadedModel(BaseModel):
    name: str
    type: str
    backend: str  # tabbyapi, ollama, ollama-cpu
    context_length: Optional[int] = None
    loaded_at: Optional[str] = None


class ModelLoadRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model to load")
    backend: str = Field("tabbyapi", description="Backend: tabbyapi, ollama, ollama-cpu")
    max_seq_len: Optional[int] = Field(None, description="Override max context length")
    gpu_split: Optional[List[float]] = Field(None, description="Manual GPU split (e.g., [32, 24])")


class ModelUnloadRequest(BaseModel):
    backend: str = Field("tabbyapi", description="Backend to unload from")


class ModelSwitchRequest(BaseModel):
    model_name: str = Field(..., description="Name of the model to switch to")
    backend: str = Field("tabbyapi", description="Backend: tabbyapi, ollama")
    unload_first: bool = Field(True, description="Unload current model before loading")


class ModelStatus(BaseModel):
    tabbyapi: Optional[Dict[str, Any]] = None
    ollama_gpu: Optional[Dict[str, Any]] = None
    ollama_cpu: Optional[Dict[str, Any]] = None
    available_exl2: int = 0
    available_ollama: int = 0


# =============================================================================
# MODEL DISCOVERY
# =============================================================================

async def scan_exl2_models() -> List[ModelInfo]:
    """Fetch EXL2 models from TabbyAPI (models are on hydra-ai, not local)."""
    models = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{TABBYAPI_URL}/v1/model/list")
            if response.status_code == 200:
                data = response.json()
                model_list = data.get("data", [])

                # Filter to only EXL2 models (exclude special entries like 'diffusion', 'whisper', 'ollama')
                skip_names = {"diffusion", "whisper", "ollama"}

                for model in model_list:
                    model_name = model.get("id", "")
                    if not model_name or model_name in skip_names:
                        continue

                    # Parse quantization from name (e.g., 4.0bpw, 3.5bpw)
                    quant = None
                    name_lower = model_name.lower()
                    for q in ["8.0bpw", "6.0bpw", "5.0bpw", "4.65bpw", "4.5bpw", "4.25bpw", "4.0bpw", "3.5bpw", "3.0bpw", "2.5bpw"]:
                        if q in name_lower:
                            quant = q
                            break

                    # Estimate size and VRAM based on quantization and model class
                    size_gb = 0.0
                    vram_estimate = 0.0

                    # Rough size estimates based on model name patterns
                    if "70b" in name_lower:
                        if quant:
                            bpw = float(quant.replace("bpw", ""))
                            size_gb = round(70 * bpw / 8, 1)  # 70B params * bpw / 8
                        else:
                            size_gb = 35.0
                    elif "12b" in name_lower:
                        size_gb = round(12 * (float(quant.replace("bpw", "")) if quant else 4.0) / 8, 1)
                    elif "8b" in name_lower:
                        size_gb = round(8 * (float(quant.replace("bpw", "")) if quant else 4.0) / 8, 1)
                    elif "1b" in name_lower:
                        size_gb = round(1 * (float(quant.replace("bpw", "")) if quant else 4.0) / 8, 1)

                    vram_estimate = round(size_gb * 1.2, 1)  # Add 20% for KV cache

                    # Get categories based on model name
                    categories = get_model_categories(model_name)

                    models.append(ModelInfo(
                        name=model_name,
                        type="exl2",
                        size_gb=size_gb,
                        path=f"/mnt/models/{model_name}",
                        quantization=quant,
                        vram_estimate_gb=vram_estimate,
                        categories=categories,
                        is_nsfw="nsfw" in categories or "creative" in categories,
                        is_coding="coding" in categories or "software" in categories,
                        is_reasoning="reasoning" in categories or "thinking" in categories,
                    ))
            else:
                logger.warning(f"TabbyAPI returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching models from TabbyAPI: {e}")

    return sorted(models, key=lambda m: m.name)


async def get_ollama_models(ollama_url: str) -> List[ModelInfo]:
    """Get models available in an Ollama instance."""
    models = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                for model in data.get("models", []):
                    size_gb = round(model.get("size", 0) / (1024**3), 2)
                    models.append(ModelInfo(
                        name=model.get("name", "unknown"),
                        type="ollama",
                        size_gb=size_gb,
                        quantization=model.get("details", {}).get("quantization_level"),
                    ))
    except Exception as e:
        logger.warning(f"Could not get Ollama models from {ollama_url}: {e}")

    return models


# =============================================================================
# MODEL STATUS
# =============================================================================

async def get_tabbyapi_status() -> Optional[Dict[str, Any]]:
    """Get current TabbyAPI model status."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{TABBYAPI_URL}/v1/model")
            if response.status_code == 200:
                data = response.json()
                # TabbyAPI returns 'id' for model name, not 'model_name'
                model_id = data.get("id")
                params = data.get("parameters", {})
                return {
                    "model_name": model_id,
                    "model_type": "exl2",
                    "max_seq_len": params.get("max_seq_len"),
                    "cache_size": params.get("cache_size"),
                    "cache_mode": params.get("cache_mode"),
                    "backend": "tabbyapi",
                    "status": "loaded" if model_id else "idle",
                }
    except Exception as e:
        logger.warning(f"TabbyAPI status check failed: {e}")
        return {"status": "unreachable", "error": str(e)}

    return {"status": "no_model_loaded"}


async def get_ollama_status(ollama_url: str, backend_name: str) -> Optional[Dict[str, Any]]:
    """Get current Ollama running model status."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/ps")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                if models:
                    return {
                        "models": [
                            {
                                "name": m.get("name"),
                                "size_gb": round(m.get("size", 0) / (1024**3), 2),
                                "vram_gb": round(m.get("size_vram", 0) / (1024**3), 2),
                            }
                            for m in models
                        ],
                        "backend": backend_name,
                        "status": "running",
                    }
                return {"status": "idle", "backend": backend_name}
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "backend": backend_name}

    return {"status": "idle", "backend": backend_name}


# =============================================================================
# MODEL LOADING OPERATIONS
# =============================================================================

async def load_tabbyapi_model(
    model_name: str,
    max_seq_len: Optional[int] = None,
    gpu_split: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Load a model in TabbyAPI."""
    payload = {"model_name": model_name}

    if max_seq_len:
        payload["max_seq_len"] = max_seq_len
    if gpu_split:
        payload["gpu_split"] = gpu_split

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Load the model
            response = await client.post(
                f"{TABBYAPI_URL}/v1/model/load",
                json=payload,
            )

            if response.status_code == 200:
                return {
                    "status": "loaded",
                    "model": model_name,
                    "backend": "tabbyapi",
                    "response": response.json(),
                }
            else:
                return {
                    "status": "failed",
                    "error": response.text,
                    "status_code": response.status_code,
                }
    except httpx.TimeoutException:
        return {"status": "timeout", "error": "Model loading timed out (10 min limit)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def unload_tabbyapi_model() -> Dict[str, Any]:
    """Unload the current model from TabbyAPI."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{TABBYAPI_URL}/v1/model/unload")

            if response.status_code == 200:
                return {"status": "unloaded", "backend": "tabbyapi"}
            else:
                return {"status": "failed", "error": response.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def load_ollama_model(model_name: str, ollama_url: str) -> Dict[str, Any]:
    """Load/pull a model in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # First try to run the model (will pull if needed)
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model_name, "prompt": "test", "stream": False},
            )

            if response.status_code == 200:
                return {
                    "status": "loaded",
                    "model": model_name,
                    "backend": "ollama",
                    "url": ollama_url,
                }
            else:
                return {"status": "failed", "error": response.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/available")
async def list_available_models():
    """List all available models across the cluster."""
    # Gather from all sources in parallel
    exl2_task = scan_exl2_models()
    ollama_gpu_task = get_ollama_models(OLLAMA_URL)
    ollama_cpu_task = get_ollama_models(OLLAMA_CPU_URL)

    exl2_models, ollama_gpu_models, ollama_cpu_models = await asyncio.gather(
        exl2_task, ollama_gpu_task, ollama_cpu_task
    )

    return {
        "exl2": [m.model_dump() for m in exl2_models],
        "ollama_gpu": [m.model_dump() for m in ollama_gpu_models],
        "ollama_cpu": [m.model_dump() for m in ollama_cpu_models],
        "summary": {
            "total_exl2": len(exl2_models),
            "total_ollama_gpu": len(ollama_gpu_models),
            "total_ollama_cpu": len(ollama_cpu_models),
        },
    }


@router.get("/loaded")
async def get_loaded_models():
    """Get currently loaded models across all backends."""
    tabby_status, ollama_gpu_status, ollama_cpu_status = await asyncio.gather(
        get_tabbyapi_status(),
        get_ollama_status(OLLAMA_URL, "ollama_gpu"),
        get_ollama_status(OLLAMA_CPU_URL, "ollama_cpu"),
    )

    return {
        "tabbyapi": tabby_status,
        "ollama_gpu": ollama_gpu_status,
        "ollama_cpu": ollama_cpu_status,
    }


@router.get("/status")
async def get_full_model_status():
    """Get comprehensive model status including VRAM usage."""
    loaded = await get_loaded_models()
    available = await list_available_models()

    return {
        "loaded": loaded,
        "available_counts": available["summary"],
        "backends": {
            "tabbyapi": {
                "url": TABBYAPI_URL,
                "node": "hydra-ai",
                "gpus": ["RTX 5090 (32GB)", "RTX 4090 (24GB)"],
            },
            "ollama_gpu": {
                "url": OLLAMA_URL,
                "node": "hydra-compute",
                "gpus": ["RTX 5070 Ti (16GB)", "RTX 5070 Ti (16GB)"],
            },
            "ollama_cpu": {
                "url": OLLAMA_CPU_URL,
                "node": "hydra-storage",
                "gpus": [],
            },
        },
    }


@router.post("/load")
async def load_model(request: ModelLoadRequest, background_tasks: BackgroundTasks):
    """Load a model on the specified backend."""
    if request.backend == "tabbyapi":
        result = await load_tabbyapi_model(
            model_name=request.model_name,
            max_seq_len=request.max_seq_len,
            gpu_split=request.gpu_split,
        )
    elif request.backend == "ollama":
        result = await load_ollama_model(request.model_name, OLLAMA_URL)
    elif request.backend == "ollama-cpu":
        result = await load_ollama_model(request.model_name, OLLAMA_CPU_URL)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {request.backend}")

    if result.get("status") in ("error", "failed"):
        raise HTTPException(status_code=500, detail=result.get("error", "Load failed"))

    return result


@router.post("/unload")
async def unload_model(request: ModelUnloadRequest):
    """Unload the current model from the specified backend."""
    if request.backend == "tabbyapi":
        result = await unload_tabbyapi_model()
    elif request.backend in ("ollama", "ollama-cpu"):
        # Ollama doesn't have an explicit unload - models time out automatically
        return {"status": "info", "message": "Ollama models auto-unload after inactivity"}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {request.backend}")

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Unload failed"))

    return result


@router.post("/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch to a different model (unload current, load new)."""
    results = {"unload": None, "load": None}

    # Unload first if requested
    if request.unload_first and request.backend == "tabbyapi":
        unload_result = await unload_tabbyapi_model()
        results["unload"] = unload_result

        if unload_result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Unload failed: {unload_result.get('error')}"
            )

        # Brief pause to let VRAM clear
        await asyncio.sleep(2)

    # Load new model
    load_request = ModelLoadRequest(
        model_name=request.model_name,
        backend=request.backend,
    )

    if request.backend == "tabbyapi":
        load_result = await load_tabbyapi_model(model_name=request.model_name)
    elif request.backend == "ollama":
        load_result = await load_ollama_model(request.model_name, OLLAMA_URL)
    elif request.backend == "ollama-cpu":
        load_result = await load_ollama_model(request.model_name, OLLAMA_CPU_URL)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {request.backend}")

    results["load"] = load_result

    if load_result.get("status") in ("error", "failed"):
        raise HTTPException(
            status_code=500,
            detail=f"Load failed: {load_result.get('error')}"
        )

    return {
        "status": "switched",
        "model": request.model_name,
        "backend": request.backend,
        "details": results,
    }


@router.get("/recommendations")
async def get_model_recommendations():
    """Get model recommendations based on current VRAM availability."""
    # Get VRAM status from Prometheus or direct query
    config = get_config()

    recommendations = {
        "hydra_ai_56gb": [
            {
                "name": "Llama-3.1-70B-Instruct-exl2-4.0bpw",
                "vram": "~52GB",
                "context": "24K",
                "quality": "High",
                "use_case": "General purpose, best quality",
            },
            {
                "name": "Llama-3.1-70B-Instruct-exl2-3.5bpw",
                "vram": "~45GB",
                "context": "32K",
                "quality": "Good",
                "use_case": "Long context tasks",
            },
            {
                "name": "Qwen2.5-72B-Instruct-exl2-3.5bpw",
                "vram": "~46GB",
                "context": "32K",
                "quality": "Good",
                "use_case": "Reasoning, coding",
            },
        ],
        "hydra_compute_32gb": [
            {
                "name": "llama3.1:8b",
                "vram": "~8GB",
                "context": "128K",
                "use_case": "Fast queries, embeddings",
            },
            {
                "name": "qwen2.5:14b",
                "vram": "~14GB",
                "context": "32K",
                "use_case": "Balanced speed/quality",
            },
        ],
        "hydra_storage_cpu": [
            {
                "name": "llama3.2:latest",
                "ram": "~4GB",
                "context": "8K",
                "use_case": "Fallback when GPUs busy",
            },
        ],
    }

    return recommendations


# =============================================================================
# CHAT ENDPOINT
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_model(request: ChatRequest):
    """
    Chat with a model via the unified interface.

    This endpoint provides a simple chat interface for the Command Center,
    automatically routing to the appropriate backend based on the model.
    """
    model_name = request.model
    backend = "tabbyapi"  # Default to TabbyAPI for EXL2 models

    # Determine backend from model name
    if model_name == "current":
        # Use currently loaded TabbyAPI model
        status = await get_tabbyapi_status()
        if status and status.get("status") == "loaded":
            model_name = status.get("model_name", "default")
        else:
            raise HTTPException(status_code=400, detail="No model currently loaded on TabbyAPI")
    elif "ollama" in model_name.lower() or model_name in ["qwen2.5-7b", "llama3.2", "qwen-coder"]:
        backend = "ollama"
    elif "cpu" in model_name.lower():
        backend = "ollama-cpu"

    # Build the request payload
    payload = {
        "model": model_name if backend != "tabbyapi" else "default",
        "messages": request.messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stream": request.stream,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            if backend == "tabbyapi":
                response = await client.post(
                    f"{TABBYAPI_URL}/v1/chat/completions",
                    json=payload,
                )
            elif backend == "ollama":
                # Convert to Ollama format
                ollama_payload = {
                    "model": model_name,
                    "messages": request.messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    }
                }
                response = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json=ollama_payload,
                )
            else:  # ollama-cpu
                ollama_payload = {
                    "model": model_name.replace("-cpu", ""),
                    "messages": request.messages,
                    "stream": False,
                }
                response = await client.post(
                    f"{OLLAMA_CPU_URL}/api/chat",
                    json=ollama_payload,
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Backend error: {response.text}"
                )

            data = response.json()

            # Parse response based on backend
            if backend == "tabbyapi":
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens")
            else:
                content = data.get("message", {}).get("content", "")
                tokens = data.get("eval_count")

            return ChatResponse(
                model=model_name,
                response=content,
                tokens_used=tokens,
                backend=backend,
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_model_registry():
    """
    Get a comprehensive model registry with categories for the Command Center.

    Returns models organized by category for easy selection.
    """
    available = await list_available_models()
    loaded = await get_loaded_models()

    # Organize models by category
    by_category = {
        "creative_nsfw": [],
        "coding": [],
        "reasoning": [],
        "general": [],
    }

    # Process EXL2 models
    for model in available.get("exl2", []):
        model_data = {
            "name": model["name"],
            "type": "exl2",
            "size_gb": model.get("size_gb"),
            "quantization": model.get("quantization"),
            "vram_gb": model.get("vram_estimate_gb"),
            "backend": "tabbyapi",
            "categories": model.get("categories", ["general"]),
            "is_nsfw": model.get("is_nsfw", False),
        }

        # Add to appropriate category
        if model.get("is_nsfw") or "creative" in model.get("categories", []):
            by_category["creative_nsfw"].append(model_data)
        elif model.get("is_coding") or "coding" in model.get("categories", []):
            by_category["coding"].append(model_data)
        elif model.get("is_reasoning") or "reasoning" in model.get("categories", []):
            by_category["reasoning"].append(model_data)
        else:
            by_category["general"].append(model_data)

    # Process Ollama models
    for model in available.get("ollama_gpu", []):
        model_data = {
            "name": model["name"],
            "type": "ollama",
            "size_gb": model.get("size_gb"),
            "backend": "ollama",
            "categories": get_model_categories(model["name"]),
        }
        by_category["general"].append(model_data)

    return {
        "by_category": by_category,
        "loaded": loaded,
        "backends": {
            "tabbyapi": {"url": TABBYAPI_URL, "node": "hydra-ai", "vram": "56GB"},
            "ollama": {"url": OLLAMA_URL, "node": "hydra-compute", "vram": "32GB"},
            "ollama_cpu": {"url": OLLAMA_CPU_URL, "node": "hydra-storage", "vram": "0GB"},
        },
        "quick_picks": {
            "nsfw_creative": "L3.3-70B-Euryale-v2.3-exl2-3.5bpw",
            "coding": "Devstral-Small-2505-exl2-4.25bpw",
            "reasoning": "DeepSeek-R1-Distill-Llama-70B-exl2-4.25bpw",
            "general": "Llama-3.1-70B-Instruct-exl2-3.5bpw",
            "fast": "qwen2.5-7b",
        },
    }


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_model_hotswap_router() -> APIRouter:
    """Create and return the model hot-swap router."""
    return router
