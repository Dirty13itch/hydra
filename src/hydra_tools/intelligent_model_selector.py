"""
Intelligent Model Selector - Proactive Model Management

This module adds intelligence to Hydra's model selection:
1. Task Classification - Detect what type of task is being requested
2. Model Quality Rankings - Know which models are best for each task type
3. Auto-Loading - Automatically load the optimal model for a task
4. VRAM Awareness - Consider hardware constraints when selecting

The goal: Hydra should aggressively pursue the BEST model for every task,
not settle for whatever happens to be loaded.
"""

import re
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# TASK CLASSIFICATION
# =============================================================================

class TaskType(str, Enum):
    """Types of tasks Hydra can perform."""
    CODING = "coding"           # Writing, editing, debugging code
    CREATIVE = "creative"       # Creative writing, roleplay, storytelling
    REASONING = "reasoning"     # Math, logic, analysis, planning
    GENERAL = "general"         # General chat, Q&A, summarization
    UNCENSORED = "uncensored"   # Tasks requiring uncensored output
    AGENTIC = "agentic"         # Tool use, multi-step tasks


# Task detection patterns - ordered by priority
TASK_PATTERNS = {
    TaskType.CODING: [
        r'\b(code|coding|program|function|class|method|bug|debug|fix|refactor)\b',
        r'\b(python|javascript|typescript|rust|go|java|c\+\+|sql|html|css)\b',
        r'\b(api|endpoint|database|query|implement|develop|build)\b',
        r'\b(git|commit|merge|branch|repository|test|unittest)\b',
        r'```',  # Code blocks
        r'\.(py|js|ts|rs|go|java|cpp|sql|sh|yaml|json|md)$',  # File extensions
        r'\bdef\s+\w+\s*\(',  # Python function definition
        r'\bclass\s+\w+',  # Class definition
        r'\bimport\s+\w+',  # Import statements
        r'\bfrom\s+\w+\s+import',  # Python from import
        r'\bconst\s+\w+\s*=',  # JS/TS const
        r'\blet\s+\w+\s*=',  # JS/TS let
        r'\bfunction\s+\w+\s*\(',  # Function keyword
        r'=>',  # Arrow functions
        r'\breturn\s+',  # Return statements
        r'\bfor\s+\w+\s+in\b',  # Python for loops
        r'\bwhile\s+.*:',  # While loops
        r'\bif\s+.*:',  # If statements (Python)
        r'\bif\s*\(.*\)\s*\{',  # If statements (C-style)
    ],
    TaskType.REASONING: [
        r'\b(calculate|compute|solve|prove|analyze|reason|think|plan)\b',
        r'\b(math|equation|formula|algorithm|logic|probability|statistics)\b',
        r'\b(why|how|explain|understand|evaluate|compare|assess)\b',
        r'\b(step.by.step|chain.of.thought|reasoning|deduce)\b',
        r'\d+\s*[\+\-\*\/\^]\s*\d+',  # Math expressions
    ],
    TaskType.CREATIVE: [
        r'\b(story|write|creative|fiction|character|scene|dialogue)\b',
        r'\b(roleplay|rp|fantasy|adventure|romance|drama)\b',
        r'\b(poem|poetry|lyrics|narrative|describe|imagine)\b',
        r'\b(queen|empire|kingdom|princess|throne)\b',  # Empire of Broken Queens context
    ],
    TaskType.UNCENSORED: [
        r'\b(nsfw|adult|explicit|uncensored|mature)\b',
        r'\b(violent|dark|gore|horror)\b',
    ],
    TaskType.AGENTIC: [
        r'\b(execute|run|deploy|automate|schedule|workflow)\b',
        r'\b(agent|autonomous|automated|pipeline)\b',
        r'\b(docker|container|ssh|server|cluster)\b',
    ],
}


def classify_task(prompt: str, files: List[str] = None) -> TaskType:
    """
    Classify a task based on prompt content and file types.

    Returns the most specific task type that matches.
    """
    prompt_lower = prompt.lower()
    files = files or []

    # Check file extensions for coding tasks
    code_extensions = {'.py', '.js', '.ts', '.rs', '.go', '.java', '.cpp', '.c', '.h',
                       '.sql', '.sh', '.yaml', '.yml', '.json', '.toml', '.md'}
    if any(f.lower().endswith(tuple(code_extensions)) for f in files):
        return TaskType.CODING

    # Score each task type
    scores = {task_type: 0 for task_type in TaskType}

    for task_type, patterns in TASK_PATTERNS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, prompt_lower, re.IGNORECASE))
            scores[task_type] += matches

    # Get highest scoring type
    best_type = max(scores, key=scores.get)

    # Default to general if no strong signal
    if scores[best_type] == 0:
        return TaskType.GENERAL

    return best_type


# =============================================================================
# MODEL QUALITY RANKINGS
# =============================================================================

@dataclass
class ModelRanking:
    """Quality ranking for a model on a specific task type."""
    model_name: str
    backend: Literal["tabbyapi", "ollama"]
    quality_score: float  # 0-100
    speed_score: float    # 0-100 (higher = faster)
    vram_gb: float        # Required VRAM
    notes: str = ""


# Best models for each task type, ordered by quality
MODEL_RANKINGS: Dict[TaskType, List[ModelRanking]] = {
    TaskType.CODING: [
        ModelRanking("Devstral-Small-2505-exl2-4.25bpw", "tabbyapi", 95, 80, 14,
                    "Mistral's dedicated coding model, agentic capabilities"),
        ModelRanking("DeepSeek-R1-Distill-Llama-70B-exl2-4.25bpw", "tabbyapi", 90, 50, 35,
                    "Strong reasoning helps with complex code"),
        ModelRanking("qwen2.5-coder:32b", "ollama", 88, 70, 20,
                    "Excellent coder, fast on Ollama"),
        ModelRanking("Llama-3.1-70B-Instruct-exl2-4.5bpw", "tabbyapi", 85, 55, 40,
                    "General purpose but solid at coding"),
        ModelRanking("qwen2.5-coder:7b", "ollama", 70, 95, 5,
                    "Fast fallback for simple tasks"),
    ],
    TaskType.CREATIVE: [
        ModelRanking("Midnight-Miqu-70B-v1.5-exl2-2.5bpw", "tabbyapi", 98, 60, 25,
                    "Best 70B creative that fits in 56GB VRAM with cache"),
        ModelRanking("L3.3-70B-Euryale-v2.3-exl2-3.5bpw", "tabbyapi", 96, 50, 45,
                    "Top quality but requires 50GB+ VRAM"),
        ModelRanking("Lumimaid-v0.2-70B-exl2-4.0bpw", "tabbyapi", 94, 50, 50,
                    "Excellent for roleplay, requires 55GB+ VRAM"),
        ModelRanking("MN-12B-Celeste-V1.9-exl2-6bpw", "tabbyapi", 85, 85, 10,
                    "Fast creative model for shorter tasks"),
        ModelRanking("dolphin-llama3:70b", "ollama", 88, 45, 40,
                    "Uncensored creative via Ollama"),
    ],
    TaskType.REASONING: [
        ModelRanking("DeepSeek-R1-Distill-Llama-70B-exl2-4.25bpw", "tabbyapi", 98, 45, 35,
                    "Best reasoning model, chain-of-thought"),
        ModelRanking("Llama-3.1-70B-Instruct-exl2-4.5bpw", "tabbyapi", 90, 55, 40,
                    "Strong general reasoning"),
        ModelRanking("Hermes-3-Llama-3.1-70B-exl2-4.65bpw", "tabbyapi", 88, 50, 42,
                    "Agentic reasoning"),
        ModelRanking("Llama-3.3-70B-abliterated-GGUF", "tabbyapi", 85, 55, 35,
                    "Good reasoning, uncensored"),
    ],
    TaskType.GENERAL: [
        ModelRanking("Llama-3.1-70B-Instruct-exl2-4.5bpw", "tabbyapi", 92, 55, 40,
                    "Best all-around model"),
        ModelRanking("Llama-3.3-70B-abliterated-GGUF", "tabbyapi", 90, 55, 35,
                    "Great general purpose, no guardrails"),
        ModelRanking("Hermes-3-Llama-3.1-70B-exl2-4.65bpw", "tabbyapi", 88, 50, 42,
                    "Versatile with tool use"),
        ModelRanking("dolphin-llama3:70b", "ollama", 85, 45, 40,
                    "Solid general via Ollama"),
        ModelRanking("qwen2.5:7b", "ollama", 70, 95, 5,
                    "Fast fallback"),
    ],
    TaskType.UNCENSORED: [
        ModelRanking("Midnight-Miqu-70B-v1.5-exl2-2.5bpw", "tabbyapi", 95, 60, 25,
                    "Uncensored, creative"),
        ModelRanking("Llama-3.3-70B-abliterated-GGUF", "tabbyapi", 93, 55, 35,
                    "Abliterated = no refusals"),
        ModelRanking("dolphin-llama3:70b", "ollama", 90, 45, 40,
                    "Dolphin = uncensored"),
        ModelRanking("L3.3-70B-Euryale-v2.3-exl2-3.5bpw", "tabbyapi", 88, 50, 35,
                    "Creative uncensored"),
    ],
    TaskType.AGENTIC: [
        ModelRanking("Devstral-Small-2505-exl2-4.25bpw", "tabbyapi", 95, 80, 14,
                    "Built for agentic tasks"),
        ModelRanking("Hermes-3-Llama-3.1-70B-exl2-4.65bpw", "tabbyapi", 92, 50, 42,
                    "Strong tool use"),
        ModelRanking("DeepSeek-R1-Distill-Llama-70B-exl2-4.25bpw", "tabbyapi", 88, 45, 35,
                    "Good reasoning for planning"),
        ModelRanking("qwen2.5-coder:32b", "ollama", 85, 70, 20,
                    "Good for automated coding tasks"),
    ],
}


# =============================================================================
# INTELLIGENT MODEL SELECTOR
# =============================================================================

# Service URLs
TABBYAPI_URL = "http://192.168.1.250:5000"
OLLAMA_URL = "http://192.168.1.203:11434"


class IntelligentModelSelector:
    """
    Intelligent model selection and management.

    This class proactively ensures the best model is loaded for each task.
    """

    def __init__(self):
        self._current_tabby_model: Optional[str] = None
        self._current_ollama_models: List[str] = []
        self._loading_lock = asyncio.Lock()

    async def get_current_models(self) -> Dict[str, Any]:
        """Get currently loaded models across all backends."""
        result = {"tabbyapi": None, "ollama": []}

        async with httpx.AsyncClient(timeout=10) as client:
            # Check TabbyAPI
            try:
                resp = await client.get(f"{TABBYAPI_URL}/v1/model")
                if resp.status_code == 200:
                    data = resp.json()
                    result["tabbyapi"] = data.get("id")
                    self._current_tabby_model = result["tabbyapi"]
            except Exception as e:
                logger.warning(f"TabbyAPI check failed: {e}")

            # Check Ollama
            try:
                resp = await client.get(f"{OLLAMA_URL}/api/ps")
                if resp.status_code == 200:
                    data = resp.json()
                    result["ollama"] = [m.get("name") for m in data.get("models", [])]
                    self._current_ollama_models = result["ollama"]
            except Exception as e:
                logger.warning(f"Ollama check failed: {e}")

        return result

    async def select_best_model(
        self,
        task_type: TaskType,
        prefer_speed: bool = False,
        max_vram: float = 56  # Default to hydra-ai capacity
    ) -> Optional[ModelRanking]:
        """
        Select the best model for a task type.

        Args:
            task_type: The type of task
            prefer_speed: Prioritize speed over quality
            max_vram: Maximum VRAM available

        Returns:
            The best ModelRanking that fits constraints, or None
        """
        rankings = MODEL_RANKINGS.get(task_type, MODEL_RANKINGS[TaskType.GENERAL])

        for ranking in rankings:
            # Check VRAM constraint
            if ranking.vram_gb > max_vram:
                continue

            # If preferring speed, check speed score
            if prefer_speed and ranking.speed_score < 70:
                continue

            return ranking

        # Fallback to any available model
        return rankings[-1] if rankings else None

    async def ensure_optimal_model(
        self,
        prompt: str,
        files: List[str] = None,
        auto_load: bool = True,
        prefer_speed: bool = False,
        quality_threshold: int = 75,  # Use loaded model if quality >= this
        force_best: bool = False  # Override and always load best model
    ) -> Dict[str, Any]:
        """
        Intelligently ensure a good model is available for the task.

        SMART ROUTING STRATEGY:
        1. Check what's already loaded across all nodes
        2. If loaded model quality >= threshold for task type, USE IT
        3. Only switch if quality gap is significant or force_best=True
        4. Route to the node with best already-loaded model

        This minimizes model switching while maintaining quality.
        """
        # Classify the task
        task_type = classify_task(prompt, files)

        # Get current models across cluster
        current = await self.get_current_models()
        current_tabby = current.get("tabbyapi")
        current_ollama = current.get("ollama", [])

        # Evaluate quality of currently loaded models for this task type
        loaded_quality = self._evaluate_loaded_model_quality(current_tabby, task_type)
        ollama_quality = max(
            [self._evaluate_loaded_model_quality(m, task_type) for m in current_ollama],
            default=0
        )

        # Select theoretical best model
        best = await self.select_best_model(task_type, prefer_speed)

        # SMART DECISION: Use loaded model if good enough
        if not force_best:
            # TabbyAPI model is good enough
            if loaded_quality >= quality_threshold:
                return {
                    "task_type": task_type,
                    "recommended_model": best,
                    "current_model": current_tabby,
                    "action_taken": "using_loaded",
                    "ready": True,
                    "quality_delta": (best.quality_score if best else 100) - loaded_quality,
                    "reason": f"Loaded model quality {loaded_quality} >= threshold {quality_threshold}"
                }

            # Ollama model is good enough
            if ollama_quality >= quality_threshold:
                best_ollama = max(current_ollama, key=lambda m: self._evaluate_loaded_model_quality(m, task_type))
                return {
                    "task_type": task_type,
                    "recommended_model": best,
                    "current_model": best_ollama,
                    "action_taken": "routing_to_ollama",
                    "ready": True,
                    "quality_delta": (best.quality_score if best else 100) - ollama_quality,
                    "reason": f"Ollama model quality {ollama_quality} >= threshold {quality_threshold}"
                }

        # Current models aren't good enough - check if we should switch
        if not best:
            return {
                "task_type": task_type,
                "recommended_model": None,
                "current_model": current,
                "action_taken": "no_suitable_model",
                "ready": False
            }

        # Check if best model is already loaded
        is_loaded = (best.backend == "tabbyapi" and current_tabby == best.model_name) or \
                   (best.backend == "ollama" and best.model_name in current_ollama)

        if is_loaded:
            return {
                "task_type": task_type,
                "recommended_model": best,
                "current_model": current_tabby if best.backend == "tabbyapi" else best.model_name,
                "action_taken": "already_loaded",
                "ready": True
            }

        # Model needs to be loaded
        if not auto_load:
            return {
                "task_type": task_type,
                "recommended_model": best,
                "current_model": current_tabby,
                "action_taken": "would_load",
                "ready": loaded_quality >= 50,  # Can still use loaded model at reduced quality
                "quality_delta": best.quality_score - loaded_quality,
                "reason": f"Best model {best.model_name} not loaded. Current quality: {loaded_quality}"
            }

        # Auto-load only if quality improvement is significant (>20 points)
        # Skip this check if force_best=True - always load optimal model
        quality_improvement = best.quality_score - max(loaded_quality, ollama_quality)
        if not force_best and quality_improvement < 20 and max(loaded_quality, ollama_quality) >= 50:
            return {
                "task_type": task_type,
                "recommended_model": best,
                "current_model": current_tabby,
                "action_taken": "using_loaded_acceptable",
                "ready": True,
                "quality_delta": quality_improvement,
                "reason": f"Quality improvement ({quality_improvement}) not worth model switch time"
            }

        # Quality improvement is significant - load the better model
        async with self._loading_lock:
            success = await self._load_model(best)

            return {
                "task_type": task_type,
                "recommended_model": best,
                "current_model": best.model_name if success else current_tabby,
                "action_taken": "loaded" if success else "load_failed",
                "ready": success or loaded_quality >= 50,
                "quality_delta": quality_improvement
            }

    def _evaluate_loaded_model_quality(self, model_name: str, task_type: TaskType) -> int:
        """
        Evaluate how good a loaded model is for a specific task type.

        Returns quality score 0-100.
        """
        if not model_name:
            return 0

        # Check if this model is ranked for this task type
        rankings = MODEL_RANKINGS.get(task_type, [])
        for ranking in rankings:
            if ranking.model_name.lower() in model_name.lower() or model_name.lower() in ranking.model_name.lower():
                return int(ranking.quality_score)

        # Model not in rankings for this task - estimate based on model characteristics
        model_lower = model_name.lower()

        # Base quality by model type
        base_quality = 50

        # Adjust for model size (larger = generally better)
        if "70b" in model_lower:
            base_quality += 25
        elif "32b" in model_lower or "24b" in model_lower:
            base_quality += 15
        elif "12b" in model_lower or "13b" in model_lower:
            base_quality += 10
        elif "7b" in model_lower or "8b" in model_lower:
            base_quality += 5

        # Adjust for model specialization
        if task_type == TaskType.CODING:
            if "coder" in model_lower or "devstral" in model_lower:
                base_quality += 15
            elif "instruct" in model_lower:
                base_quality += 5

        elif task_type == TaskType.CREATIVE:
            if "euryale" in model_lower or "lumimaid" in model_lower or "miqu" in model_lower:
                base_quality += 20
            elif "dolphin" in model_lower or "celeste" in model_lower:
                base_quality += 15

        elif task_type == TaskType.REASONING:
            if "deepseek" in model_lower and "r1" in model_lower:
                base_quality += 20
            elif "instruct" in model_lower:
                base_quality += 10

        return min(base_quality, 100)

    async def _load_model_by_name(self, model_name: str, backend: str = "tabbyapi") -> bool:
        """Load a model by name on specified backend."""
        # Create a dummy ranking for the load
        ranking = ModelRanking(model_name, backend, 0, 0, 0)
        return await self._load_model(ranking)

    async def _load_model(self, ranking: ModelRanking) -> bool:
        """Load a model on the appropriate backend with optimized settings."""
        async with httpx.AsyncClient(timeout=600) as client:
            try:
                if ranking.backend == "tabbyapi":
                    # Unload current model first
                    await client.post(f"{TABBYAPI_URL}/v1/model/unload")
                    await asyncio.sleep(3)

                    # Determine optimal settings based on model size
                    load_params = {"model_name": ranking.model_name}

                    # 70B models need reduced cache to fit in 56GB
                    if "70b" in ranking.model_name.lower():
                        load_params["max_seq_len"] = 8192  # Reduced from 16K
                        load_params["cache_mode"] = "Q4"   # 4x less VRAM for cache
                        logger.info(f"Loading 70B model with optimized settings: 8K context, Q4 cache")

                    # Load new model
                    resp = await client.post(
                        f"{TABBYAPI_URL}/v1/model/load",
                        json=load_params
                    )

                    if resp.status_code == 200:
                        logger.info(f"Loaded {ranking.model_name} on TabbyAPI")
                        self._current_tabby_model = ranking.model_name
                        return True
                    else:
                        logger.error(f"Failed to load {ranking.model_name}: {resp.text}")
                        return False

                else:  # ollama
                    # Ollama loads on demand, just warm it up
                    resp = await client.post(
                        f"{OLLAMA_URL}/api/generate",
                        json={"model": ranking.model_name, "prompt": "test", "stream": False}
                    )

                    if resp.status_code == 200:
                        logger.info(f"Warmed up {ranking.model_name} on Ollama")
                        return True
                    else:
                        logger.error(f"Failed to load {ranking.model_name}: {resp.text}")
                        return False

            except Exception as e:
                logger.exception(f"Error loading model {ranking.model_name}: {e}")
                return False

    def get_task_recommendations(self) -> Dict[TaskType, List[str]]:
        """Get recommended models for each task type."""
        return {
            task_type: [r.model_name for r in rankings[:3]]
            for task_type, rankings in MODEL_RANKINGS.items()
        }


# Singleton instance
_selector: Optional[IntelligentModelSelector] = None


def get_model_selector() -> IntelligentModelSelector:
    """Get the singleton model selector instance."""
    global _selector
    if _selector is None:
        _selector = IntelligentModelSelector()
    return _selector


# =============================================================================
# API INTEGRATION
# =============================================================================

from fastapi import APIRouter

router = APIRouter(prefix="/model-intelligence", tags=["model-intelligence"])


@router.get("/classify")
async def classify_task_endpoint(prompt: str):
    """Classify a task and get model recommendations."""
    task_type = classify_task(prompt)
    selector = get_model_selector()
    best = await selector.select_best_model(task_type)

    return {
        "task_type": task_type.value,
        "recommended_model": {
            "name": best.model_name,
            "backend": best.backend,
            "quality_score": best.quality_score,
            "notes": best.notes
        } if best else None,
        "all_rankings": [
            {
                "name": r.model_name,
                "backend": r.backend,
                "quality": r.quality_score,
                "speed": r.speed_score,
                "vram_gb": r.vram_gb
            }
            for r in MODEL_RANKINGS.get(task_type, [])
        ]
    }


@router.post("/ensure-optimal")
async def ensure_optimal_endpoint(
    prompt: str,
    files: List[str] = None,
    auto_load: bool = True,
    prefer_speed: bool = False,
    force_best: bool = True,
    quality_threshold: int = 85
):
    """
    Ensure the optimal model is loaded for a task.

    This endpoint will:
    1. Classify the task
    2. Check if the best model is loaded
    3. Load it if auto_load=True and it's not loaded

    Default behavior (force_best=True): Always load the optimal model for each task type.
    Set force_best=False to allow using already-loaded models if quality >= threshold.
    """
    selector = get_model_selector()
    result = await selector.ensure_optimal_model(
        prompt, files, auto_load, prefer_speed, quality_threshold, force_best
    )

    return {
        "task_type": result["task_type"].value,
        "recommended_model": {
            "name": result["recommended_model"].model_name,
            "backend": result["recommended_model"].backend,
            "quality_score": result["recommended_model"].quality_score,
        } if result["recommended_model"] else None,
        "current_model": result["current_model"],
        "action_taken": result["action_taken"],
        "ready": result["ready"]
    }


@router.get("/recommendations")
async def get_recommendations():
    """Get model recommendations for all task types."""
    selector = get_model_selector()
    current = await selector.get_current_models()

    return {
        "current_models": current,
        "recommendations": {
            task_type.value: [
                {
                    "name": r.model_name,
                    "backend": r.backend,
                    "quality": r.quality_score,
                    "speed": r.speed_score,
                    "vram_gb": r.vram_gb,
                    "notes": r.notes,
                    "is_loaded": (
                        r.model_name == current.get("tabbyapi") if r.backend == "tabbyapi"
                        else r.model_name in current.get("ollama", [])
                    )
                }
                for r in rankings[:5]
            ]
            for task_type, rankings in MODEL_RANKINGS.items()
        }
    }


@router.get("/status")
async def get_intelligence_status():
    """Get the current model intelligence status."""
    selector = get_model_selector()
    current = await selector.get_current_models()

    # Determine what task the current model is best for
    current_tabby = current.get("tabbyapi")
    best_for = None

    if current_tabby:
        for task_type, rankings in MODEL_RANKINGS.items():
            for rank in rankings[:3]:  # Check top 3 for each type
                if rank.model_name == current_tabby:
                    best_for = task_type.value
                    break
            if best_for:
                break

    return {
        "current_models": current,
        "current_model_best_for": best_for,
        "task_types": [t.value for t in TaskType],
        "total_models_ranked": sum(len(r) for r in MODEL_RANKINGS.values()),
    }


def create_model_intelligence_router() -> APIRouter:
    """Create and return the model intelligence router."""
    return router
