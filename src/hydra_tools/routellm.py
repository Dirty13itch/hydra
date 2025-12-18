"""
RouteLLM - Intelligent Model Routing for Hydra Cluster

Routes requests to optimal LOCAL model based on:
- Prompt complexity (simple → 7B, complex → 70B)
- Token count (short → 7B, long → 70B)
- Task type (code → code-optimized, general → default)
- Current load (fallback if model busy)

Local Model Tiers (via LiteLLM):
- FAST: qwen2.5-7b (Ollama on hydra-compute)
- QUALITY: midnight-miqu-70b (TabbyAPI on hydra-ai)
- CODE: qwen2.5-coder-7b (Ollama code model)

Usage:
    from hydra_tools.routellm import RouteClassifier

    classifier = RouteClassifier()
    model = classifier.route(prompt="Explain quantum computing in simple terms")
    # Returns: "qwen2.5-7b" or "midnight-miqu-70b" based on complexity
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelTier(Enum):
    """Model capability tiers."""
    FAST = "fast"      # 7B class - qwen2.5:7b, mistral
    QUALITY = "quality"  # 70B class - Llama 3.3 70B
    CODE = "code"      # Code-optimized - codestral


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    model: str
    tier: ModelTier
    confidence: float
    reason: str


class RouteClassifier:
    """
    Classifies prompts and routes to optimal model.

    Uses heuristics and patterns to determine complexity:
    - Simple: greetings, definitions, short answers
    - Complex: analysis, reasoning, long-form content
    - Code: programming tasks, debugging, code review
    """

    # Patterns indicating simple tasks (use 7B)
    SIMPLE_PATTERNS = [
        r"^(hi|hello|hey|good morning|good evening)",
        r"^what (is|are) ",
        r"^define ",
        r"^translate .{0,100}$",
        r"^summarize this (in )?(\d+ )?(sentence|word|bullet)",
        r"^list \d+ ",
        r"^(yes|no)\?",
        r"^(who|what|when|where) (is|was|are|were) ",
    ]

    # Patterns indicating complex tasks (use 70B)
    COMPLEX_PATTERNS = [
        r"(explain|analyze|compare|contrast|evaluate|assess|critique)",
        r"(step[- ]by[- ]step|detailed|comprehensive|thorough)",
        r"(why|how) (does|do|did|would|could|should|might)",
        r"(pros? and cons?|advantages? and disadvantages?)",
        r"(reasoning|logic|argument|evidence)",
        r"(essay|article|report|paper|document)",
        r"(research|study|investigation)",
        r"(complex|complicated|nuanced|subtle)",
    ]

    # Patterns indicating code tasks (use codestral)
    CODE_PATTERNS = [
        r"```[\w]*\n",  # Code blocks
        r"(def |class |function\s*\(|const |let |var )",
        r"(import \w+|from \w+ import|require\(['\"]|#include )",  # More specific import patterns
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|sql)\b.{0,30}(code|script|program|function|bug|error|fix|debug)",  # Language + code context
        r"(debug|fix|refactor|optimize|review) (this |the |my )?(code|function|class|script)",
        r"(implement|write|create|build) (a |an )?(function|class|method|api|script)",
        r"(error|exception|bug|issue) in (my |the |this )?(code|program|script)",
        r"(code|function|class|method|script) (that|which|to) ",  # Code entity references
    ]

    # Model mappings - Hydra local models via LiteLLM
    # These map to actual local inference:
    #   qwen2.5-7b → Ollama on hydra-compute (fast 7B)
    #   midnight-miqu-70b → TabbyAPI on hydra-ai (quality 70B)
    #   qwen2.5-coder-7b → Ollama code model on hydra-compute
    MODELS = {
        ModelTier.FAST: "qwen2.5-7b",
        ModelTier.QUALITY: "midnight-miqu-70b",
        ModelTier.CODE: "qwen2.5-coder-7b",
    }

    def __init__(
        self,
        complexity_threshold: float = 0.45,  # Lower threshold for more quality routing
        token_threshold: int = 300,  # Lower token threshold
    ):
        """
        Initialize the route classifier.

        Args:
            complexity_threshold: Score above which to use 70B (0.0-1.0)
            token_threshold: Token count above which to prefer 70B
        """
        self.complexity_threshold = complexity_threshold
        self.token_threshold = token_threshold

        # Compile patterns for efficiency
        self.simple_patterns = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        self.complex_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS]
        self.code_patterns = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4

    def _count_pattern_matches(self, text: str, patterns: list) -> int:
        """Count how many patterns match in text."""
        return sum(1 for p in patterns if p.search(text))

    def _calculate_complexity(self, prompt: str) -> float:
        """
        Calculate complexity score (0.0 to 1.0).

        Factors:
        - Pattern matches (simple vs complex)
        - Text length
        - Question depth
        - Technical terminology
        """
        simple_matches = self._count_pattern_matches(prompt, self.simple_patterns)
        complex_matches = self._count_pattern_matches(prompt, self.complex_patterns)

        # Base score from pattern matching
        if simple_matches + complex_matches == 0:
            pattern_score = 0.5  # Neutral
        else:
            pattern_score = complex_matches / (simple_matches + complex_matches)

        # Length factor (longer = more complex usually)
        tokens = self._estimate_tokens(prompt)
        length_score = min(tokens / 1000, 1.0)  # Cap at 1000 tokens

        # Question depth (nested questions = more complex)
        question_count = prompt.count("?")
        question_score = min(question_count * 0.2, 0.5)

        # Combine scores with weights
        complexity = (
            pattern_score * 0.5 +
            length_score * 0.3 +
            question_score * 0.2
        )

        return min(max(complexity, 0.0), 1.0)

    def _is_code_task(self, prompt: str) -> bool:
        """Determine if prompt is code-related."""
        code_matches = self._count_pattern_matches(prompt, self.code_patterns)
        # Lower threshold: 1+ matches is enough for code detection
        return code_matches >= 1 or "```" in prompt

    def route(
        self,
        prompt: str,
        system_prompt: str | None = None,
        prefer_quality: bool = False,
        prefer_speed: bool = False,
    ) -> RoutingDecision:
        """
        Route a prompt to the optimal model.

        Args:
            prompt: The user's prompt
            system_prompt: Optional system prompt for context
            prefer_quality: Force quality tier if uncertain
            prefer_speed: Force speed tier if uncertain

        Returns:
            RoutingDecision with model name and metadata
        """
        full_text = prompt
        if system_prompt:
            full_text = f"{system_prompt}\n\n{prompt}"

        # Check for code tasks first
        if self._is_code_task(full_text):
            return RoutingDecision(
                model=self.MODELS[ModelTier.CODE],
                tier=ModelTier.CODE,
                confidence=0.85,
                reason="Detected code-related task"
            )

        # Calculate complexity
        complexity = self._calculate_complexity(full_text)
        tokens = self._estimate_tokens(full_text)

        # Apply preferences
        if prefer_quality:
            complexity += 0.2
        elif prefer_speed:
            complexity -= 0.2

        # Token-based adjustment
        if tokens > self.token_threshold:
            complexity += 0.15

        # Make decision
        if complexity >= self.complexity_threshold:
            return RoutingDecision(
                model=self.MODELS[ModelTier.QUALITY],
                tier=ModelTier.QUALITY,
                confidence=complexity,
                reason=f"High complexity ({complexity:.2f}), {tokens} est. tokens"
            )
        else:
            return RoutingDecision(
                model=self.MODELS[ModelTier.FAST],
                tier=ModelTier.FAST,
                confidence=1.0 - complexity,
                reason=f"Low complexity ({complexity:.2f}), {tokens} est. tokens"
            )

    def route_with_fallback(
        self,
        prompt: str,
        available_models: list[str] | None = None,
        **kwargs,
    ) -> RoutingDecision:
        """
        Route with fallback if preferred model unavailable.

        Args:
            prompt: The user's prompt
            available_models: List of currently available model names
            **kwargs: Additional arguments for route()

        Returns:
            RoutingDecision with available model
        """
        decision = self.route(prompt, **kwargs)

        if available_models is None:
            return decision

        if decision.model in available_models:
            return decision

        # Fallback logic - Hydra local models
        fallback_order = {
            "midnight-miqu-70b": ["qwen2.5-7b", "llama-3.1-8b", "qwen2.5-coder-7b"],
            "qwen2.5-7b": ["llama-3.1-8b", "midnight-miqu-70b", "mistral-7b"],
            "qwen2.5-coder-7b": ["codellama-13b", "qwen2.5-7b", "midnight-miqu-70b"],
            # Legacy aliases for backwards compatibility
            "gpt-4": ["qwen2.5-7b", "llama-3.1-8b", "midnight-miqu-70b"],
            "gpt-3.5-turbo": ["qwen2.5-7b", "llama-3.1-8b", "mistral-7b"],
        }

        for fallback in fallback_order.get(decision.model, []):
            if fallback in available_models:
                is_fast = any(x in fallback for x in ["7b", "8b", "3b", "mistral"])
                return RoutingDecision(
                    model=fallback,
                    tier=ModelTier.FAST if is_fast else ModelTier.QUALITY,
                    confidence=decision.confidence * 0.8,
                    reason=f"Fallback from {decision.model}: {decision.reason}"
                )

        # Last resort - return first available
        if available_models:
            return RoutingDecision(
                model=available_models[0],
                tier=ModelTier.FAST,
                confidence=0.5,
                reason="Emergency fallback to first available model"
            )

        return decision


# Convenience function for simple usage
def classify_prompt(prompt: str, **kwargs) -> str:
    """
    Classify a prompt and return the recommended local model name.

    Args:
        prompt: The user's prompt
        **kwargs: Additional arguments for RouteClassifier.route()

    Returns:
        Local model name (e.g., "midnight-miqu-70b", "qwen2.5-7b", "qwen2.5-coder-7b")
    """
    classifier = RouteClassifier()
    decision = classifier.route(prompt, **kwargs)
    return decision.model


# =============================================================================
# Enhanced Routing Manager (3.2 Enhancement)
# =============================================================================

class TaskType(Enum):
    """Extended task type classification."""
    CHAT = "chat"           # Conversational
    CODE = "code"           # Programming
    REASONING = "reasoning" # Complex analysis
    RESEARCH = "research"   # Web research tasks
    CREATIVE = "creative"   # Creative writing
    SYSTEM = "system"       # System/admin tasks
    SIMPLE = "simple"       # Simple queries


@dataclass
class ModelCost:
    """Cost tracking for a model."""
    model: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: float


@dataclass
class QueueStatus:
    """Current queue status for a model."""
    model: str
    queue_depth: int
    estimated_wait_ms: float
    is_available: bool


class EnhancedRoutingManager:
    """
    Enhanced routing with queue awareness, cost tracking, and batch support.

    Improvements over basic RouteLLM:
    - More task types (research, creative, system)
    - Queue-depth aware routing
    - Cost tracking per model tier
    - Batch inference for background tasks
    - Adaptive routing based on load
    """

    # Extended task patterns
    RESEARCH_PATTERNS = [
        r"(research|investigate|find out|look up|search for)",
        r"(latest|current|recent) (news|updates|developments)",
        r"(what is happening|what's new) (in|with|about)",
    ]

    CREATIVE_PATTERNS = [
        r"(write|create|compose) (a |an )?(story|poem|essay|script|song)",
        r"(imagine|pretend|roleplay|act as)",
        r"(creative|artistic|fictional|fantasy)",
        r"(brainstorm|generate ideas|come up with)",
    ]

    SYSTEM_PATTERNS = [
        r"(docker|kubernetes|container|service|server)",
        r"(deploy|restart|configure|setup|install)",
        r"(monitor|check status|health|logs)",
        r"(database|cache|queue|storage)",
    ]

    # Cost per 1K tokens (estimated for local models based on power + time)
    MODEL_COSTS = {
        "qwen2.5-7b": ModelCost("qwen2.5-7b", 0.001, 0.002, 50),
        "qwen2.5-coder-7b": ModelCost("qwen2.5-coder-7b", 0.001, 0.002, 55),
        "midnight-miqu-70b": ModelCost("midnight-miqu-70b", 0.01, 0.02, 500),
        "codestral-22b": ModelCost("codestral-22b", 0.003, 0.006, 150),
        "qwen2.5-32b": ModelCost("qwen2.5-32b", 0.005, 0.01, 200),
    }

    # Routing matrix: TaskType -> QueueDepth -> Model
    ROUTING_MATRIX = {
        TaskType.SIMPLE: {"low": "qwen2.5-7b", "high": "qwen2.5-7b"},
        TaskType.CHAT: {"low": "qwen2.5-7b", "high": "qwen2.5-7b"},
        TaskType.CODE: {"low": "codestral-22b", "high": "qwen2.5-coder-7b"},
        TaskType.REASONING: {"low": "midnight-miqu-70b", "high": "qwen2.5-32b"},
        TaskType.RESEARCH: {"low": "qwen2.5-7b", "high": "qwen2.5-7b"},
        TaskType.CREATIVE: {"low": "midnight-miqu-70b", "high": "qwen2.5-32b"},
        TaskType.SYSTEM: {"low": "qwen2.5-7b", "high": "qwen2.5-7b"},
    }

    def __init__(self, high_queue_threshold: int = 5):
        self.base_classifier = RouteClassifier()
        self.high_queue_threshold = high_queue_threshold

        # Compile patterns
        self.research_patterns = [re.compile(p, re.IGNORECASE) for p in self.RESEARCH_PATTERNS]
        self.creative_patterns = [re.compile(p, re.IGNORECASE) for p in self.CREATIVE_PATTERNS]
        self.system_patterns = [re.compile(p, re.IGNORECASE) for p in self.SYSTEM_PATTERNS]

        # Cost tracking
        self.cost_history: list[dict] = []
        self.total_cost = 0.0

    def _classify_task_type(self, prompt: str) -> TaskType:
        """Classify prompt into extended task type."""
        # Check patterns
        research_matches = sum(1 for p in self.research_patterns if p.search(prompt))
        creative_matches = sum(1 for p in self.creative_patterns if p.search(prompt))
        system_matches = sum(1 for p in self.system_patterns if p.search(prompt))

        # Code check (reuse base classifier)
        if self.base_classifier._is_code_task(prompt):
            return TaskType.CODE

        # Pattern-based classification
        if research_matches >= 1:
            return TaskType.RESEARCH
        if creative_matches >= 1:
            return TaskType.CREATIVE
        if system_matches >= 1:
            return TaskType.SYSTEM

        # Complexity-based classification
        complexity = self.base_classifier._calculate_complexity(prompt)
        if complexity < 0.3:
            return TaskType.SIMPLE
        elif complexity > 0.6:
            return TaskType.REASONING

        return TaskType.CHAT

    def route_with_queue_awareness(
        self,
        prompt: str,
        queue_status: dict[str, int] | None = None,
    ) -> RoutingDecision:
        """
        Route with queue depth awareness.

        Args:
            prompt: User prompt
            queue_status: Dict of model -> queue depth

        Returns:
            RoutingDecision with optimal model for current load
        """
        task_type = self._classify_task_type(prompt)
        queue_status = queue_status or {}

        # Determine queue level (high if any preferred model is busy)
        preferred_model = self.ROUTING_MATRIX[task_type]["low"]
        queue_depth = queue_status.get(preferred_model, 0)
        queue_level = "high" if queue_depth >= self.high_queue_threshold else "low"

        # Get model from matrix
        selected_model = self.ROUTING_MATRIX[task_type][queue_level]

        return RoutingDecision(
            model=selected_model,
            tier=ModelTier.QUALITY if "70b" in selected_model or "32b" in selected_model else ModelTier.FAST,
            confidence=0.85,
            reason=f"Task: {task_type.value}, Queue: {queue_level}, Depth: {queue_depth}"
        )

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request."""
        cost_info = self.MODEL_COSTS.get(model)
        if not cost_info:
            return 0.0

        input_cost = (input_tokens / 1000) * cost_info.cost_per_1k_input
        output_cost = (output_tokens / 1000) * cost_info.cost_per_1k_output
        return input_cost + output_cost

    def record_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ):
        """Record cost for tracking."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        self.total_cost += cost

        self.cost_history.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat() if 'datetime' in dir() else None,
        })

        # Keep last 1000 records
        self.cost_history = self.cost_history[-1000:]

    def get_cost_summary(self) -> dict:
        """Get cost summary."""
        from collections import defaultdict

        by_model = defaultdict(lambda: {"requests": 0, "cost": 0, "tokens": 0})

        for record in self.cost_history:
            model = record["model"]
            by_model[model]["requests"] += 1
            by_model[model]["cost"] += record["cost"]
            by_model[model]["tokens"] += record["input_tokens"] + record["output_tokens"]

        return {
            "total_cost": round(self.total_cost, 4),
            "total_requests": len(self.cost_history),
            "by_model": dict(by_model),
        }

    def batch_route(
        self,
        prompts: list[str],
        priority: str = "background",
    ) -> list[RoutingDecision]:
        """
        Route multiple prompts for batch processing.

        For background tasks, always uses cheaper models.
        """
        results = []

        for prompt in prompts:
            task_type = self._classify_task_type(prompt)

            if priority == "background":
                # Always use fast tier for background
                model = "qwen2.5-7b"
                tier = ModelTier.FAST
            else:
                model = self.ROUTING_MATRIX[task_type]["low"]
                tier = ModelTier.QUALITY if "70b" in model or "32b" in model else ModelTier.FAST

            results.append(RoutingDecision(
                model=model,
                tier=tier,
                confidence=0.8,
                reason=f"Batch {priority}: {task_type.value}"
            ))

        return results


# Import datetime for cost tracking
from datetime import datetime


# =============================================================================
# FastAPI Router for Enhanced Routing
# =============================================================================

_enhanced_manager: EnhancedRoutingManager | None = None


def get_enhanced_manager() -> EnhancedRoutingManager:
    """Get or create enhanced routing manager."""
    global _enhanced_manager
    if _enhanced_manager is None:
        _enhanced_manager = EnhancedRoutingManager()
    return _enhanced_manager


def create_routing_router():
    """Create FastAPI router for enhanced routing."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/routing", tags=["routing"])

    class RouteRequest(BaseModel):
        prompt: str
        queue_status: dict[str, int] | None = None

    class BatchRouteRequest(BaseModel):
        prompts: list[str]
        priority: str = "background"

    class RecordCostRequest(BaseModel):
        model: str
        input_tokens: int
        output_tokens: int
        latency_ms: float

    @router.post("/route")
    async def route_prompt(request: RouteRequest):
        """Route a prompt to optimal model with queue awareness."""
        manager = get_enhanced_manager()
        decision = manager.route_with_queue_awareness(
            request.prompt,
            request.queue_status,
        )
        return {
            "model": decision.model,
            "tier": decision.tier.value,
            "confidence": decision.confidence,
            "reason": decision.reason,
        }

    @router.post("/route/batch")
    async def batch_route(request: BatchRouteRequest):
        """Route multiple prompts for batch processing."""
        manager = get_enhanced_manager()
        decisions = manager.batch_route(request.prompts, request.priority)
        return {
            "decisions": [
                {
                    "model": d.model,
                    "tier": d.tier.value,
                    "confidence": d.confidence,
                    "reason": d.reason,
                }
                for d in decisions
            ]
        }

    @router.get("/classify/{prompt}")
    async def classify_prompt_endpoint(prompt: str):
        """Classify a prompt's task type."""
        manager = get_enhanced_manager()
        task_type = manager._classify_task_type(prompt)
        return {
            "prompt": prompt[:100],
            "task_type": task_type.value,
        }

    @router.post("/cost/record")
    async def record_cost(request: RecordCostRequest):
        """Record cost for a completed request."""
        manager = get_enhanced_manager()
        manager.record_cost(
            request.model,
            request.input_tokens,
            request.output_tokens,
            request.latency_ms,
        )
        return {"status": "recorded"}

    @router.get("/cost/summary")
    async def get_cost_summary():
        """Get cost tracking summary."""
        manager = get_enhanced_manager()
        return manager.get_cost_summary()

    @router.get("/cost/estimate")
    async def estimate_cost(model: str, input_tokens: int, output_tokens: int):
        """Estimate cost for a request."""
        manager = get_enhanced_manager()
        cost = manager.estimate_cost(model, input_tokens, output_tokens)
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": round(cost, 6),
        }

    @router.get("/matrix")
    async def get_routing_matrix():
        """Get the routing matrix configuration."""
        manager = get_enhanced_manager()
        return {
            "matrix": {
                task_type.value: models
                for task_type, models in manager.ROUTING_MATRIX.items()
            },
            "high_queue_threshold": manager.high_queue_threshold,
        }

    @router.get("/models")
    async def get_model_costs():
        """Get model cost information."""
        manager = get_enhanced_manager()
        return {
            "models": {
                name: {
                    "cost_per_1k_input": cost.cost_per_1k_input,
                    "cost_per_1k_output": cost.cost_per_1k_output,
                    "avg_latency_ms": cost.avg_latency_ms,
                }
                for name, cost in manager.MODEL_COSTS.items()
            }
        }

    @router.get("/stats")
    async def get_routing_stats():
        """Get routing statistics."""
        manager = get_enhanced_manager()
        cost_summary = manager.get_cost_summary()
        return {
            "cost_summary": cost_summary,
            "task_types": [t.value for t in TaskType],
            "models_configured": len(manager.MODEL_COSTS),
        }

    return router


if __name__ == "__main__":
    # Test examples
    classifier = RouteClassifier()

    test_prompts = [
        "Hi there!",
        "What is the capital of France?",
        "Explain the implications of quantum entanglement on information theory and its potential applications in cryptography.",
        "```python\ndef foo():\n    pass\n```\n\nFix this function to calculate fibonacci",
        "Write a detailed analysis of the economic factors that led to the 2008 financial crisis.",
        "Translate 'hello' to Spanish",
        "Debug this JavaScript code that's throwing an error",
    ]

    print("RouteLLM Classification Tests\n" + "=" * 50)
    for prompt in test_prompts:
        decision = classifier.route(prompt)
        print(f"\nPrompt: {prompt[:60]}...")
        print(f"  Model: {decision.model}")
        print(f"  Tier: {decision.tier.value}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reason: {decision.reason}")
