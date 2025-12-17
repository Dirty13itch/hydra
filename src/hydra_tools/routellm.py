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
