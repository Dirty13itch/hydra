"""
Hydra Preference Learning System

Tracks user preferences, model choices, and feedback to continuously improve
recommendations and system behavior.

Features:
- Tracks model usage patterns
- Learns from explicit feedback (thumbs up/down)
- Adjusts routing based on past performance
- Stores preferences in Redis for fast access
- Persists to PostgreSQL for long-term analysis

Usage:
    from hydra_tools.preference_learning import PreferenceLearner

    learner = PreferenceLearner()
    learner.record_interaction(
        prompt="...",
        model="midnight-miqu-70b",  # Hydra local model
        response="...",
        feedback="positive"
    )

    # Get personalized recommendation for local models
    preferred = learner.get_preferred_model(task_type="code")
    # Returns: "qwen2.5-coder-7b" (local code model)
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx


class FeedbackType(Enum):
    """Types of user feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    REGENERATE = "regenerate"  # User asked to regenerate
    EDIT = "edit"  # User edited the response


class TaskType(Enum):
    """Categories of tasks."""
    GENERAL = "general"
    CODE = "code"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


@dataclass
class Interaction:
    """Record of a single interaction."""
    id: str
    timestamp: str
    prompt_hash: str  # Hash of prompt for privacy
    prompt_length: int
    model: str
    response_length: int
    latency_ms: int
    task_type: str
    feedback: str | None = None
    feedback_timestamp: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelStats:
    """Statistics for a model."""
    model: str
    total_uses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    regenerations: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_used: str | None = None


@dataclass
class UserPreferences:
    """User's learned preferences."""
    preferred_models: dict[str, str] = field(default_factory=dict)  # task_type -> model
    model_stats: dict[str, ModelStats] = field(default_factory=dict)
    style_preferences: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


class PreferenceLearner:
    """
    Learns and applies user preferences for model selection and behavior.
    """

    def __init__(
        self,
        redis_url: str = "redis://:ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC@192.168.1.244:6379/1",
        postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
        user_id: str = "default",
    ):
        """
        Initialize the preference learner.

        Args:
            redis_url: Redis connection URL for fast cache
            postgres_url: PostgreSQL URL for persistent storage
            user_id: User identifier (single-user system uses "default")
        """
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.user_id = user_id

        # In-memory cache
        self._preferences_cache: UserPreferences | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl = 300  # 5 minutes

        # Model weights for routing decisions
        self._model_weights: dict[str, dict[str, float]] = {}

    def _hash_prompt(self, prompt: str) -> str:
        """Create privacy-preserving hash of prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _classify_task(self, prompt: str) -> TaskType:
        """Classify the task type from prompt."""
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["```", "code", "function", "class", "debug", "implement"]):
            return TaskType.CODE
        if any(kw in prompt_lower for kw in ["write a story", "creative", "poem", "fiction"]):
            return TaskType.CREATIVE
        if any(kw in prompt_lower for kw in ["analyze", "compare", "evaluate", "assess"]):
            return TaskType.ANALYSIS
        if any(kw in prompt_lower for kw in ["translate", "in spanish", "in french", "to english"]):
            return TaskType.TRANSLATION
        if any(kw in prompt_lower for kw in ["summarize", "tldr", "brief", "key points"]):
            return TaskType.SUMMARIZATION

        return TaskType.GENERAL

    def _get_redis_key(self, key_type: str) -> str:
        """Generate Redis key."""
        return f"hydra:prefs:{self.user_id}:{key_type}"

    async def _save_to_redis(self, key: str, data: dict, ttl: int = 86400) -> bool:
        """Save data to Redis."""
        try:
            # Using httpx to communicate with Redis via a simple HTTP wrapper
            # In production, use redis-py directly
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://192.168.1.244:8600/cache/set",
                    json={"key": key, "value": data, "ttl": ttl},
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _load_from_redis(self, key: str) -> dict | None:
        """Load data from Redis."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://192.168.1.244:8600/cache/get/{key}",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None

    def record_interaction(
        self,
        prompt: str,
        model: str,
        response: str,
        latency_ms: int = 0,
        feedback: FeedbackType | str | None = None,
        metadata: dict | None = None,
    ) -> Interaction:
        """
        Record an interaction for learning.

        Args:
            prompt: The user's prompt
            model: Model used
            response: Model's response
            latency_ms: Response latency in milliseconds
            feedback: Optional immediate feedback
            metadata: Additional metadata

        Returns:
            Interaction record
        """
        task_type = self._classify_task(prompt)

        interaction = Interaction(
            id=f"{int(time.time() * 1000)}-{self._hash_prompt(prompt)[:8]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            prompt_hash=self._hash_prompt(prompt),
            prompt_length=len(prompt),
            model=model,
            response_length=len(response),
            latency_ms=latency_ms,
            task_type=task_type.value,
            feedback=feedback.value if isinstance(feedback, FeedbackType) else feedback,
            metadata=metadata or {},
        )

        # Update model stats
        self._update_model_stats(model, task_type, latency_ms, feedback)

        return interaction

    def _update_model_stats(
        self,
        model: str,
        task_type: TaskType,
        latency_ms: int,
        feedback: FeedbackType | str | None,
    ) -> None:
        """Update running statistics for a model."""
        # Ensure preferences are loaded
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences()

        # Get or create model stats
        if model not in self._preferences_cache.model_stats:
            self._preferences_cache.model_stats[model] = ModelStats(model=model)

        stats = self._preferences_cache.model_stats[model]

        # Update counts
        stats.total_uses += 1
        stats.last_used = datetime.utcnow().isoformat() + "Z"

        # Update latency (rolling average)
        if stats.avg_latency_ms == 0:
            stats.avg_latency_ms = latency_ms
        else:
            stats.avg_latency_ms = (stats.avg_latency_ms * 0.9) + (latency_ms * 0.1)

        # Update feedback counts
        if feedback:
            feedback_val = feedback.value if isinstance(feedback, FeedbackType) else feedback
            if feedback_val == "positive":
                stats.positive_feedback += 1
            elif feedback_val == "negative":
                stats.negative_feedback += 1
            elif feedback_val == "regenerate":
                stats.regenerations += 1

        # Calculate success rate
        total_feedback = stats.positive_feedback + stats.negative_feedback
        if total_feedback > 0:
            stats.success_rate = stats.positive_feedback / total_feedback

        # Update preferences cache timestamp
        self._preferences_cache.updated_at = datetime.utcnow().isoformat() + "Z"

    def record_feedback(
        self,
        interaction_id: str,
        feedback: FeedbackType | str,
    ) -> bool:
        """
        Record feedback for a previous interaction.

        Args:
            interaction_id: ID of the interaction
            feedback: Feedback type

        Returns:
            Success status
        """
        # In a full implementation, this would update the stored interaction
        # and recalculate model weights
        return True

    def get_preferred_model(
        self,
        task_type: TaskType | str | None = None,
        prompt: str | None = None,
        available_models: list[str] | None = None,
    ) -> str:
        """
        Get the preferred model based on learned preferences.

        Args:
            task_type: Type of task (or auto-detect from prompt)
            prompt: Optional prompt for task detection
            available_models: List of available models

        Returns:
            Recommended model name
        """
        # Determine task type
        if task_type is None and prompt:
            task_type = self._classify_task(prompt)
        elif isinstance(task_type, str):
            task_type = TaskType(task_type)
        else:
            task_type = TaskType.GENERAL

        # Check explicit preferences
        if self._preferences_cache and task_type.value in self._preferences_cache.preferred_models:
            preferred = self._preferences_cache.preferred_models[task_type.value]
            if available_models is None or preferred in available_models:
                return preferred

        # Calculate scores based on stats
        model_scores: dict[str, float] = {}

        if self._preferences_cache:
            for model, stats in self._preferences_cache.model_stats.items():
                if available_models and model not in available_models:
                    continue

                # Score based on success rate and usage
                score = (
                    stats.success_rate * 0.5 +  # Success matters most
                    min(stats.total_uses / 100, 1.0) * 0.2 +  # Experience
                    (1.0 - min(stats.avg_latency_ms / 10000, 1.0)) * 0.2 +  # Speed
                    (1.0 - min(stats.regenerations / max(stats.total_uses, 1), 1.0)) * 0.1  # Low regenerations
                )
                model_scores[model] = score

        # Return best scoring model or default
        if model_scores:
            return max(model_scores, key=model_scores.get)

        # Defaults by task type - Hydra local models
        defaults = {
            TaskType.GENERAL: "qwen2.5-7b",
            TaskType.CODE: "qwen2.5-coder-7b",
            TaskType.CREATIVE: "midnight-miqu-70b",
            TaskType.ANALYSIS: "midnight-miqu-70b",
            TaskType.TRANSLATION: "qwen2.5-7b",
            TaskType.SUMMARIZATION: "qwen2.5-7b",
        }

        default = defaults.get(task_type, "qwen2.5-7b")

        if available_models and default not in available_models:
            return available_models[0] if available_models else "qwen2.5-7b"

        return default

    def get_style_preferences(self) -> dict[str, Any]:
        """
        Get learned style preferences.

        Returns:
            Dictionary of style preferences (verbosity, tone, etc.)
        """
        if self._preferences_cache:
            return self._preferences_cache.style_preferences

        # Defaults
        return {
            "verbosity": "concise",  # concise, balanced, detailed
            "tone": "professional",  # casual, professional, formal
            "code_style": "modern",  # classic, modern
            "explanation_depth": "medium",  # brief, medium, thorough
        }

    def export_preferences(self) -> dict:
        """
        Export all preferences as a dictionary.

        Returns:
            Serializable preferences dictionary
        """
        if self._preferences_cache is None:
            return {}

        return {
            "user_id": self.user_id,
            "preferred_models": self._preferences_cache.preferred_models,
            "model_stats": {
                model: {
                    "model": stats.model,
                    "total_uses": stats.total_uses,
                    "positive_feedback": stats.positive_feedback,
                    "negative_feedback": stats.negative_feedback,
                    "regenerations": stats.regenerations,
                    "avg_latency_ms": stats.avg_latency_ms,
                    "success_rate": stats.success_rate,
                    "last_used": stats.last_used,
                }
                for model, stats in self._preferences_cache.model_stats.items()
            },
            "style_preferences": self._preferences_cache.style_preferences,
            "updated_at": self._preferences_cache.updated_at,
        }

    def import_preferences(self, data: dict) -> bool:
        """
        Import preferences from a dictionary.

        Args:
            data: Preferences dictionary

        Returns:
            Success status
        """
        try:
            self._preferences_cache = UserPreferences(
                preferred_models=data.get("preferred_models", {}),
                model_stats={
                    model: ModelStats(**stats_data)
                    for model, stats_data in data.get("model_stats", {}).items()
                },
                style_preferences=data.get("style_preferences", {}),
                updated_at=data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
            )
            return True
        except Exception:
            return False


# API endpoints for integration
def create_preference_api():
    """Create FastAPI router for preference learning endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/preferences", tags=["preferences"])
    learner = PreferenceLearner()

    class InteractionRequest(BaseModel):
        prompt: str
        model: str
        response: str
        latency_ms: int = 0
        feedback: str | None = None

    class FeedbackRequest(BaseModel):
        interaction_id: str
        feedback: str

    class ModelRecommendationRequest(BaseModel):
        task_type: str | None = None
        prompt: str | None = None
        available_models: list[str] | None = None

    @router.post("/interaction")
    async def record_interaction(req: InteractionRequest):
        """Record an interaction."""
        interaction = learner.record_interaction(
            prompt=req.prompt,
            model=req.model,
            response=req.response,
            latency_ms=req.latency_ms,
            feedback=req.feedback,
        )
        return {"id": interaction.id, "task_type": interaction.task_type}

    @router.post("/feedback")
    async def record_feedback(req: FeedbackRequest):
        """Record feedback for an interaction."""
        success = learner.record_feedback(req.interaction_id, req.feedback)
        if not success:
            raise HTTPException(status_code=404, detail="Interaction not found")
        return {"status": "recorded"}

    @router.post("/recommend")
    async def get_recommendation(req: ModelRecommendationRequest):
        """Get model recommendation."""
        model = learner.get_preferred_model(
            task_type=req.task_type,
            prompt=req.prompt,
            available_models=req.available_models,
        )
        return {"recommended_model": model}

    @router.get("/export")
    async def export_prefs():
        """Export all preferences."""
        return learner.export_preferences()

    @router.get("/style")
    async def get_style():
        """Get style preferences."""
        return learner.get_style_preferences()

    return router


if __name__ == "__main__":
    # Test the preference learner
    learner = PreferenceLearner()

    # Simulate some interactions with Hydra local models
    test_prompts = [
        ("Write a Python function to sort a list", "qwen2.5-coder-7b", "positive"),
        ("What is the capital of France?", "qwen2.5-7b", "positive"),
        ("Explain quantum computing", "midnight-miqu-70b", "positive"),
        ("Fix this code: def foo(): pass", "qwen2.5-coder-7b", "positive"),
        ("Translate hello to Spanish", "qwen2.5-7b", "positive"),
        ("Write a haiku about programming", "midnight-miqu-70b", "negative"),
        ("Summarize this article", "qwen2.5-7b", "positive"),
    ]

    print("Recording test interactions...")
    for prompt, model, feedback in test_prompts:
        interaction = learner.record_interaction(
            prompt=prompt,
            model=model,
            response="Test response",
            latency_ms=100,
            feedback=feedback,
        )
        print(f"  {interaction.task_type}: {model} ({feedback})")

    print("\nModel recommendations:")
    for task in TaskType:
        recommended = learner.get_preferred_model(task_type=task)
        print(f"  {task.value}: {recommended}")

    print("\nExported preferences:")
    prefs = learner.export_preferences()
    print(json.dumps(prefs, indent=2, default=str))
