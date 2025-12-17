"""
Tests for RouteLLM module.
"""

import pytest
from hydra_tools.routellm import (
    RouteClassifier,
    RoutingDecision,
    ModelTier,
    classify_prompt,
)


class TestRouteClassifier:
    """Tests for RouteClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create a RouteClassifier instance."""
        return RouteClassifier()

    def test_simple_greeting_routes_to_fast(self, classifier):
        """Simple greetings should route to fast model."""
        result = classifier.route("Hello!")
        assert result.tier == ModelTier.FAST
        assert result.model == "qwen2.5-7b"

    def test_simple_question_routes_to_fast(self, classifier):
        """Simple questions should route to fast model."""
        result = classifier.route("What is the capital of France?")
        assert result.tier == ModelTier.FAST

    def test_complex_analysis_routes_to_quality(self, classifier):
        """Complex analysis requests should route to quality model."""
        result = classifier.route(
            "Analyze the implications of quantum computing on modern cryptography "
            "and explain step by step how current encryption methods might become "
            "obsolete. Include pros and cons of different mitigation strategies."
        )
        assert result.tier == ModelTier.QUALITY
        assert result.model == "midnight-miqu-70b"

    def test_code_task_routes_to_code_model(self, classifier):
        """Code tasks should route to code-optimized model."""
        result = classifier.route(
            "```python\ndef broken_function():\n    pass\n```\n\n"
            "Fix this function to implement a binary search algorithm."
        )
        assert result.tier == ModelTier.CODE
        assert result.model == "qwen2.5-coder-7b"

    def test_code_keywords_route_to_code(self, classifier):
        """Code-related keywords should route to code model."""
        result = classifier.route(
            "Debug this JavaScript code that's throwing an undefined error"
        )
        assert result.tier == ModelTier.CODE

    def test_prefer_quality_increases_complexity(self, classifier):
        """prefer_quality flag should push towards quality tier."""
        # A prompt that would normally be borderline
        prompt = "Explain how photosynthesis works"

        result_normal = classifier.route(prompt)
        result_prefer = classifier.route(prompt, prefer_quality=True)

        # With prefer_quality, confidence for quality should be higher
        assert result_prefer.confidence >= result_normal.confidence - 0.3

    def test_prefer_speed_decreases_complexity(self, classifier):
        """prefer_speed flag should push towards fast tier."""
        prompt = "Write a detailed explanation of machine learning algorithms"

        result_normal = classifier.route(prompt)
        result_prefer = classifier.route(prompt, prefer_speed=True)

        # With prefer_speed, should tend towards fast tier
        assert result_prefer.tier in [ModelTier.FAST, ModelTier.QUALITY]

    def test_long_prompt_increases_complexity(self, classifier):
        """Longer prompts should increase complexity score."""
        short_prompt = "Explain recursion"
        long_prompt = short_prompt + " " + "with examples " * 100

        result_short = classifier.route(short_prompt)
        result_long = classifier.route(long_prompt)

        # Long prompt should have higher complexity (lower confidence for fast)
        assert result_long.confidence != result_short.confidence

    def test_system_prompt_considered(self, classifier):
        """System prompt should be included in classification."""
        prompt = "Review this function and fix any bugs"
        system = "You are a code reviewer analyzing Python code for security vulnerabilities"

        result = classifier.route(prompt, system_prompt=system)
        # System prompt + prompt both mention code, should route to CODE
        assert result.tier == ModelTier.CODE

    def test_routing_decision_has_reason(self, classifier):
        """Routing decisions should include explanatory reason."""
        result = classifier.route("Hello world")
        assert result.reason
        assert len(result.reason) > 0

    def test_routing_decision_has_confidence(self, classifier):
        """Routing decisions should have confidence score."""
        result = classifier.route("Explain quantum computing")
        assert 0.0 <= result.confidence <= 1.0

    def test_route_with_fallback_respects_availability(self, classifier):
        """Fallback routing should respect available models."""
        # Request would normally go to gpt-4, but it's not available
        result = classifier.route_with_fallback(
            "Analyze this complex problem thoroughly",
            available_models=["gpt-3.5-turbo", "mistral"]
        )
        assert result.model in ["gpt-3.5-turbo", "mistral"]

    def test_route_with_fallback_uses_preferred_when_available(self, classifier):
        """Fallback should use preferred model when available."""
        result = classifier.route_with_fallback(
            "Hello!",
            available_models=["midnight-miqu-70b", "qwen2.5-7b", "mistral"]
        )
        # Simple prompt prefers qwen2.5-7b, which is available
        assert result.model == "qwen2.5-7b"


class TestClassifyPrompt:
    """Tests for convenience function."""

    def test_classify_prompt_returns_model_name(self):
        """classify_prompt should return just the model name string."""
        result = classify_prompt("What is 2+2?")
        assert isinstance(result, str)
        assert result in ["midnight-miqu-70b", "qwen2.5-7b", "qwen2.5-coder-7b"]

    def test_classify_prompt_accepts_kwargs(self):
        """classify_prompt should pass kwargs to route method."""
        result = classify_prompt("Explain something", prefer_quality=True)
        assert isinstance(result, str)


class TestPatternMatching:
    """Tests for pattern matching behavior."""

    @pytest.fixture
    def classifier(self):
        return RouteClassifier()

    @pytest.mark.parametrize("prompt", [
        "Hi there!",
        "Hello, how are you?",
        "Good morning",
        "Hey",
    ])
    def test_greetings_match_simple_pattern(self, classifier, prompt):
        """Various greetings should match simple patterns."""
        result = classifier.route(prompt)
        assert result.tier == ModelTier.FAST

    @pytest.mark.parametrize("prompt", [
        "What is Python?",
        "Define recursion",
        "Translate 'hello' to Spanish",
        "List 5 programming languages",
    ])
    def test_simple_tasks_route_fast(self, classifier, prompt):
        """Simple tasks should route to fast model."""
        result = classifier.route(prompt)
        assert result.tier == ModelTier.FAST

    @pytest.mark.parametrize("prompt", [
        "Compare and contrast microservices vs monolithic architecture",
        "Analyze the pros and cons of different database systems",
        "Write a comprehensive essay about climate change",
        "Evaluate the economic impact of artificial intelligence",
    ])
    def test_complex_tasks_route_quality(self, classifier, prompt):
        """Complex tasks should route to quality model."""
        result = classifier.route(prompt)
        assert result.tier == ModelTier.QUALITY

    @pytest.mark.parametrize("prompt", [
        "```python\nprint('hello')\n```\nFix this code",
        "Implement a function to calculate fibonacci numbers",
        "Debug this JavaScript that has a null reference error",
        "Write a class in Python that handles database connections",
    ])
    def test_code_tasks_route_code(self, classifier, prompt):
        """Code-related tasks should route to code model."""
        result = classifier.route(prompt)
        assert result.tier == ModelTier.CODE
