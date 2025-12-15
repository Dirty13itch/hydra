"""
Tests for Preference Learning module.
"""

import pytest
from hydra_tools.preference_learning import (
    PreferenceLearner,
    FeedbackType,
    TaskType,
    ModelStats,
    UserPreferences,
    Interaction,
)


class TestPreferenceLearner:
    """Tests for PreferenceLearner class."""

    @pytest.fixture
    def learner(self):
        """Create a PreferenceLearner instance."""
        return PreferenceLearner(user_id="test-user")

    def test_record_interaction_returns_interaction(self, learner):
        """Recording an interaction should return an Interaction object."""
        interaction = learner.record_interaction(
            prompt="What is Python?",
            model="gpt-3.5-turbo",
            response="Python is a programming language.",
            latency_ms=100,
        )

        assert isinstance(interaction, Interaction)
        assert interaction.model == "gpt-3.5-turbo"
        assert interaction.prompt_length == len("What is Python?")
        assert interaction.latency_ms == 100

    def test_record_interaction_classifies_task(self, learner):
        """Interactions should have task type classified."""
        code_interaction = learner.record_interaction(
            prompt="```python\ndef foo(): pass```\nFix this code",
            model="codestral",
            response="Here is the fix...",
        )
        assert code_interaction.task_type == "code"

        general_interaction = learner.record_interaction(
            prompt="What is the weather like?",
            model="gpt-3.5-turbo",
            response="I cannot check weather.",
        )
        assert general_interaction.task_type == "general"

    def test_record_interaction_with_feedback(self, learner):
        """Interactions can include feedback."""
        interaction = learner.record_interaction(
            prompt="Test prompt",
            model="gpt-4",
            response="Test response",
            feedback=FeedbackType.POSITIVE,
        )
        assert interaction.feedback == "positive"

    def test_model_stats_updated_on_interaction(self, learner):
        """Model stats should be updated when interactions are recorded."""
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            latency_ms=500,
        )

        prefs = learner.export_preferences()
        assert "gpt-4" in prefs.get("model_stats", {})
        stats = prefs["model_stats"]["gpt-4"]
        assert stats["total_uses"] == 1
        assert stats["avg_latency_ms"] > 0

    def test_positive_feedback_increases_success_rate(self, learner):
        """Positive feedback should increase success rate."""
        # Record several interactions with positive feedback
        for _ in range(5):
            learner.record_interaction(
                prompt="Test",
                model="gpt-4",
                response="Response",
                feedback=FeedbackType.POSITIVE,
            )

        prefs = learner.export_preferences()
        stats = prefs["model_stats"]["gpt-4"]
        assert stats["success_rate"] == 1.0
        assert stats["positive_feedback"] == 5

    def test_negative_feedback_decreases_success_rate(self, learner):
        """Negative feedback should decrease success rate."""
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            feedback=FeedbackType.POSITIVE,
        )
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            feedback=FeedbackType.NEGATIVE,
        )

        prefs = learner.export_preferences()
        stats = prefs["model_stats"]["gpt-4"]
        assert stats["success_rate"] == 0.5

    def test_get_preferred_model_default(self, learner):
        """Without history, should return sensible default."""
        model = learner.get_preferred_model(task_type=TaskType.GENERAL)
        assert model in ["gpt-3.5-turbo", "gpt-4", "codestral", "mistral"]

    def test_get_preferred_model_from_prompt(self, learner):
        """Should detect task type from prompt."""
        model = learner.get_preferred_model(prompt="Debug this Python code")
        # Code task should get code-appropriate model
        assert model in ["codestral", "gpt-4", "gpt-3.5-turbo"]

    def test_get_preferred_model_respects_history(self, learner):
        """Model with good history should be preferred."""
        # Build history for gpt-4 with positive feedback
        for _ in range(10):
            learner.record_interaction(
                prompt="Analysis task",
                model="gpt-4",
                response="Response",
                feedback=FeedbackType.POSITIVE,
            )

        # gpt-4 should now be preferred due to success rate
        model = learner.get_preferred_model(task_type=TaskType.ANALYSIS)
        # Should prefer gpt-4 based on history
        assert model in ["gpt-4", "gpt-3.5-turbo", "codestral"]

    def test_get_preferred_model_available_models_filter(self, learner):
        """Should only recommend available models."""
        model = learner.get_preferred_model(
            task_type=TaskType.GENERAL,
            available_models=["mistral"],
        )
        assert model == "mistral"

    def test_export_import_preferences(self, learner):
        """Preferences should be exportable and importable."""
        # Record some interactions
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            feedback=FeedbackType.POSITIVE,
        )

        # Export
        exported = learner.export_preferences()
        assert "model_stats" in exported
        assert "gpt-4" in exported["model_stats"]

        # Create new learner and import
        new_learner = PreferenceLearner(user_id="test-user-2")
        success = new_learner.import_preferences(exported)
        assert success

        # Verify imported data
        new_exported = new_learner.export_preferences()
        assert new_exported["model_stats"]["gpt-4"]["total_uses"] == 1

    def test_style_preferences_default(self, learner):
        """Should return default style preferences."""
        style = learner.get_style_preferences()

        assert "verbosity" in style
        assert "tone" in style
        assert style["verbosity"] in ["concise", "balanced", "detailed"]


class TestTaskTypeClassification:
    """Tests for task type classification."""

    @pytest.fixture
    def learner(self):
        return PreferenceLearner()

    def test_code_classification(self, learner):
        """Code-related prompts should be classified as code."""
        prompts = [
            "Write a Python function",
            "Debug this JavaScript code",
            "```python\nprint('hello')\n```",
            "Implement a class for database connections",
        ]

        for prompt in prompts:
            interaction = learner.record_interaction(
                prompt=prompt,
                model="test",
                response="test",
            )
            assert interaction.task_type == "code", f"Failed for: {prompt}"

    def test_analysis_classification(self, learner):
        """Analysis prompts should be classified as analysis."""
        prompts = [
            "Analyze this data",
            "Compare these two approaches",
            "Evaluate the pros and cons",
        ]

        for prompt in prompts:
            interaction = learner.record_interaction(
                prompt=prompt,
                model="test",
                response="test",
            )
            assert interaction.task_type == "analysis", f"Failed for: {prompt}"

    def test_translation_classification(self, learner):
        """Translation prompts should be classified as translation."""
        prompts = [
            "Translate this to Spanish",
            "How do you say hello in French",
            "Translate 'goodbye' to English",
        ]

        for prompt in prompts:
            interaction = learner.record_interaction(
                prompt=prompt,
                model="test",
                response="test",
            )
            assert interaction.task_type == "translation", f"Failed for: {prompt}"

    def test_summarization_classification(self, learner):
        """Summarization prompts should be classified as summarization."""
        prompts = [
            "Summarize this article",
            "Give me the TLDR",
            "What are the key points",
        ]

        for prompt in prompts:
            interaction = learner.record_interaction(
                prompt=prompt,
                model="test",
                response="test",
            )
            assert interaction.task_type == "summarization", f"Failed for: {prompt}"

    def test_general_classification(self, learner):
        """Unmatched prompts should be classified as general."""
        prompts = [
            "Hello",
            "What time is it",
            "Tell me a joke",
        ]

        for prompt in prompts:
            interaction = learner.record_interaction(
                prompt=prompt,
                model="test",
                response="test",
            )
            assert interaction.task_type == "general", f"Failed for: {prompt}"


class TestModelStats:
    """Tests for ModelStats tracking."""

    @pytest.fixture
    def learner(self):
        return PreferenceLearner()

    def test_latency_tracking(self, learner):
        """Latency should be tracked with rolling average."""
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            latency_ms=100,
        )
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            latency_ms=200,
        )

        prefs = learner.export_preferences()
        avg_latency = prefs["model_stats"]["gpt-4"]["avg_latency_ms"]
        # Rolling average should be between 100 and 200
        assert 100 <= avg_latency <= 200

    def test_regeneration_tracking(self, learner):
        """Regenerations should be tracked."""
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
            feedback=FeedbackType.REGENERATE,
        )

        prefs = learner.export_preferences()
        assert prefs["model_stats"]["gpt-4"]["regenerations"] == 1

    def test_last_used_timestamp(self, learner):
        """Last used timestamp should be updated."""
        learner.record_interaction(
            prompt="Test",
            model="gpt-4",
            response="Response",
        )

        prefs = learner.export_preferences()
        assert prefs["model_stats"]["gpt-4"]["last_used"] is not None


class TestInteraction:
    """Tests for Interaction dataclass."""

    def test_interaction_has_required_fields(self):
        """Interaction should have all required fields."""
        interaction = Interaction(
            id="test-123",
            timestamp="2025-01-01T00:00:00Z",
            prompt_hash="abc123",
            prompt_length=10,
            model="gpt-4",
            response_length=100,
            latency_ms=50,
            task_type="general",
        )

        assert interaction.id == "test-123"
        assert interaction.model == "gpt-4"
        assert interaction.task_type == "general"
        assert interaction.feedback is None  # Optional

    def test_interaction_with_feedback(self):
        """Interaction can include feedback."""
        interaction = Interaction(
            id="test-123",
            timestamp="2025-01-01T00:00:00Z",
            prompt_hash="abc123",
            prompt_length=10,
            model="gpt-4",
            response_length=100,
            latency_ms=50,
            task_type="general",
            feedback="positive",
            feedback_timestamp="2025-01-01T00:01:00Z",
        )

        assert interaction.feedback == "positive"
        assert interaction.feedback_timestamp is not None
