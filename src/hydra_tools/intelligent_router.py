"""
Intelligent Task-Aware Model Router

Automatically selects the best available model based on:
- Task type classification (coding, creative, analysis, etc.)
- Model capabilities and specializations
- Service availability (circuit breaker status)
- Cost considerations (local vs cloud)
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Classification of task types."""
    CODING = "coding"
    CREATIVE = "creative"           # Stories, roleplay, NSFW
    ANALYSIS = "analysis"           # Reasoning, math, logic
    CONVERSATION = "conversation"   # General chat
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    QUICK_QUERY = "quick_query"     # Simple questions


@dataclass
class ModelCapability:
    """Describes a model's capabilities and characteristics."""
    name: str                       # LiteLLM model name
    provider: str                   # tabbyapi, ollama, anthropic, openai
    size_class: str                 # "70b", "32b", "7b", "cloud"
    vram_gb: float                  # VRAM required (0 for cloud)
    strengths: List[TaskType]       # What this model excels at
    supports_nsfw: bool = False     # Uncensored model
    cost_per_1k_tokens: float = 0   # 0 for local models
    avg_latency_ms: int = 0         # Typical response latency
    context_length: int = 8192


# Model capability registry
MODEL_REGISTRY: Dict[str, ModelCapability] = {
    # Primary - TabbyAPI (hydra-ai)
    "tabby": ModelCapability(
        name="tabby",
        provider="tabbyapi",
        size_class="70b",
        vram_gb=50,
        strengths=[TaskType.CREATIVE, TaskType.CODING, TaskType.ANALYSIS, TaskType.CONVERSATION],
        supports_nsfw=True,
        context_length=16384,
        avg_latency_ms=2000,
    ),
    "midnight-miqu-70b": ModelCapability(
        name="midnight-miqu-70b",
        provider="tabbyapi",
        size_class="70b",
        vram_gb=50,
        strengths=[TaskType.CREATIVE, TaskType.CODING, TaskType.ANALYSIS],
        supports_nsfw=True,
        context_length=16384,
        avg_latency_ms=2000,
    ),

    # Local Fallback - Ollama (hydra-compute)
    "qwen-coder-32b": ModelCapability(
        name="qwen-coder-32b",
        provider="ollama",
        size_class="32b",
        vram_gb=18,
        strengths=[TaskType.CODING, TaskType.ANALYSIS],
        supports_nsfw=False,
        context_length=32768,
        avg_latency_ms=3500,
    ),
    "dolphin-70b": ModelCapability(
        name="dolphin-70b",
        provider="ollama",
        size_class="70b",
        vram_gb=43,  # Spills to RAM
        strengths=[TaskType.CREATIVE, TaskType.CONVERSATION],
        supports_nsfw=True,
        context_length=8192,
        avg_latency_ms=30000,  # Slow due to CPU offload
    ),
    "codellama-13b": ModelCapability(
        name="codellama-13b",
        provider="ollama",
        size_class="13b",
        vram_gb=8,
        strengths=[TaskType.CODING],
        supports_nsfw=False,
        context_length=16384,
        avg_latency_ms=1500,
    ),
    "qwen2.5-7b": ModelCapability(
        name="qwen2.5-7b",
        provider="ollama",
        size_class="7b",
        vram_gb=5,
        strengths=[TaskType.QUICK_QUERY, TaskType.CONVERSATION],
        supports_nsfw=False,
        context_length=32768,
        avg_latency_ms=800,
    ),
    "deepseek-r1-8b": ModelCapability(
        name="deepseek-r1-8b",
        provider="ollama",
        size_class="8b",
        vram_gb=5,
        strengths=[TaskType.ANALYSIS, TaskType.CODING],
        supports_nsfw=False,
        context_length=32768,
        avg_latency_ms=1000,
    ),

    # Cloud Fallbacks
    "claude": ModelCapability(
        name="claude",
        provider="anthropic",
        size_class="cloud",
        vram_gb=0,
        strengths=[TaskType.CODING, TaskType.ANALYSIS, TaskType.CREATIVE],
        supports_nsfw=False,
        cost_per_1k_tokens=0.015,  # ~$15/M tokens
        context_length=200000,
        avg_latency_ms=1500,
    ),
    "gpt-4": ModelCapability(
        name="openai-gpt4o",
        provider="openai",
        size_class="cloud",
        vram_gb=0,
        strengths=[TaskType.CODING, TaskType.ANALYSIS],
        supports_nsfw=False,
        cost_per_1k_tokens=0.01,
        context_length=128000,
        avg_latency_ms=2000,
    ),
}


# Task classification patterns
TASK_PATTERNS = {
    TaskType.CODING: [
        r'\b(code|function|class|def |import |from |const |let |var |async |await)\b',
        r'\b(python|javascript|typescript|rust|go|java|c\+\+|sql)\b',
        r'\b(bug|error|fix|debug|refactor|implement|api|endpoint)\b',
        r'\b(git|docker|kubernetes|aws|deploy)\b',
        r'```',  # Code blocks
    ],
    TaskType.CREATIVE: [
        r'\b(story|write|creative|fiction|character|roleplay|scene)\b',
        r'\b(nsfw|adult|explicit|erotic|sensual)\b',
        r'\b(describe|imagine|fantasy|narrative)\b',
    ],
    TaskType.ANALYSIS: [
        r'\b(analyze|analysis|reason|logic|math|calculate|solve)\b',
        r'\b(explain|why|how does|compare|evaluate)\b',
        r'\b(pros and cons|trade-?offs|implications)\b',
    ],
    TaskType.SUMMARIZATION: [
        r'\b(summarize|summary|tldr|brief|overview|key points)\b',
        r'\b(condense|shorten|recap)\b',
    ],
    TaskType.TRANSLATION: [
        r'\b(translate|translation|convert to|in \w+ language)\b',
    ],
    TaskType.QUICK_QUERY: [
        r'^(what|who|when|where|how many|how much|is |are |can |does )',
        r'\?$',  # Questions
    ],
}


def classify_task(messages: List[dict]) -> Tuple[TaskType, float]:
    """
    Classify the task type from the conversation messages.

    Returns:
        Tuple of (TaskType, confidence score 0-1)
    """
    # Combine all message content
    text = " ".join(
        msg.get("content", "") for msg in messages
        if isinstance(msg.get("content"), str)
    ).lower()

    scores: Dict[TaskType, int] = {t: 0 for t in TaskType}

    for task_type, patterns in TASK_PATTERNS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            scores[task_type] += matches

    # Find highest scoring task type
    max_score = max(scores.values())
    if max_score == 0:
        return TaskType.CONVERSATION, 0.5  # Default

    best_type = max(scores, key=scores.get)
    confidence = min(1.0, max_score / 5)  # Normalize

    return best_type, confidence


def check_nsfw_required(messages: List[dict]) -> bool:
    """Check if the request likely needs an uncensored model."""
    text = " ".join(
        msg.get("content", "") for msg in messages
        if isinstance(msg.get("content"), str)
    ).lower()

    nsfw_patterns = [
        r'\b(nsfw|adult|explicit|erotic|sensual|sexual)\b',
        r'\b(nude|naked|intimate|passionate)\b',
    ]

    for pattern in nsfw_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


class IntelligentRouter:
    """
    Routes requests to the best available model based on task analysis.
    """

    def __init__(self):
        self._circuit_breakers = None
        self._available_models: Dict[str, bool] = {}

    def _get_circuit_breakers(self):
        """Lazy load circuit breakers."""
        if self._circuit_breakers is None:
            try:
                from hydra_tools.auth_metrics import _get_circuit_breakers
                self._circuit_breakers = _get_circuit_breakers()
            except ImportError:
                self._circuit_breakers = None
        return self._circuit_breakers

    def _is_service_available(self, provider: str) -> bool:
        """Check if a service is available via circuit breaker."""
        breakers = self._get_circuit_breakers()
        if breakers is None:
            return True  # Assume available if no circuit breaker

        # Map provider to circuit breaker service name
        provider_map = {
            "tabbyapi": "tabbyapi",
            "ollama": "ollama_gpu",
            "anthropic": "litellm",  # Cloud goes through LiteLLM
            "openai": "litellm",
        }

        service = provider_map.get(provider, provider)
        breaker = breakers.breakers.get(service)

        if breaker is None:
            return True

        return not breaker.is_open

    def get_best_model(
        self,
        messages: List[dict],
        preferred_model: Optional[str] = None,
        allow_cloud: bool = True,
        max_cost_per_1k: float = 0.05,
    ) -> Tuple[str, dict]:
        """
        Select the best available model for the given request.

        Args:
            messages: The conversation messages
            preferred_model: User's preferred model (will try this first)
            allow_cloud: Whether to allow cloud API fallback
            max_cost_per_1k: Maximum acceptable cost per 1k tokens

        Returns:
            Tuple of (model_name, routing_info)
        """
        task_type, confidence = classify_task(messages)
        needs_nsfw = check_nsfw_required(messages)

        routing_info = {
            "task_type": task_type.value,
            "task_confidence": confidence,
            "needs_nsfw": needs_nsfw,
            "preferred_model": preferred_model,
            "selected_model": None,
            "selection_reason": None,
            "fallback_chain": [],
        }

        # Build candidate list based on task type and requirements
        candidates: List[Tuple[str, ModelCapability, int]] = []

        for name, cap in MODEL_REGISTRY.items():
            score = 0

            # Check availability
            if not self._is_service_available(cap.provider):
                continue

            # Check NSFW requirement
            if needs_nsfw and not cap.supports_nsfw:
                continue

            # Check cost constraint
            if cap.cost_per_1k_tokens > max_cost_per_1k:
                if not allow_cloud:
                    continue

            # Score based on task match
            if task_type in cap.strengths:
                score += 100

            # Prefer larger local models
            size_scores = {"70b": 50, "32b": 40, "13b": 30, "8b": 20, "7b": 10, "cloud": 25}
            score += size_scores.get(cap.size_class, 0)

            # Penalize slow models
            if cap.avg_latency_ms > 10000:
                score -= 30

            # Prefer local over cloud (cost savings)
            if cap.cost_per_1k_tokens == 0:
                score += 20

            # Bonus for preferred model
            if name == preferred_model:
                score += 200

            candidates.append((name, cap, score))

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[2], reverse=True)

        routing_info["fallback_chain"] = [c[0] for c in candidates[:5]]

        if not candidates:
            # No available models - return error info
            routing_info["selection_reason"] = "No available models match requirements"
            return preferred_model or "qwen2.5-7b", routing_info

        # Select best candidate
        best_name, best_cap, best_score = candidates[0]

        routing_info["selected_model"] = best_name
        routing_info["selection_reason"] = (
            f"Best match for {task_type.value} task "
            f"(score: {best_score}, provider: {best_cap.provider})"
        )

        logger.info(
            f"Intelligent routing: {task_type.value} -> {best_name} "
            f"(confidence: {confidence:.2f}, nsfw: {needs_nsfw})"
        )

        return best_name, routing_info

    def get_fallback_chain(
        self,
        task_type: TaskType,
        needs_nsfw: bool = False,
        allow_cloud: bool = True,
    ) -> List[str]:
        """
        Get an ordered fallback chain for a task type.

        Returns list of model names in priority order.
        """
        chain = []

        for name, cap in MODEL_REGISTRY.items():
            if needs_nsfw and not cap.supports_nsfw:
                continue
            if not allow_cloud and cap.cost_per_1k_tokens > 0:
                continue
            if task_type in cap.strengths:
                chain.append((name, cap))

        # Sort: local large -> local small -> cloud
        def sort_key(item):
            name, cap = item
            # Lower is better
            cost_penalty = 1000 if cap.cost_per_1k_tokens > 0 else 0
            size_order = {"70b": 0, "32b": 1, "13b": 2, "8b": 3, "7b": 4, "cloud": 5}
            return cost_penalty + size_order.get(cap.size_class, 10)

        chain.sort(key=sort_key)
        return [name for name, _ in chain]


# Global router instance
intelligent_router = IntelligentRouter()


def get_intelligent_route(
    messages: List[dict],
    preferred_model: Optional[str] = None,
    allow_cloud: bool = True,
) -> Tuple[str, dict]:
    """
    Convenience function to get intelligent routing.

    Args:
        messages: Conversation messages
        preferred_model: User's preferred model
        allow_cloud: Allow cloud API fallback

    Returns:
        Tuple of (model_name, routing_info)
    """
    return intelligent_router.get_best_model(
        messages=messages,
        preferred_model=preferred_model,
        allow_cloud=allow_cloud,
    )
