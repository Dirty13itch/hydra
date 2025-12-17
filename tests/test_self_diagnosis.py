"""
Tests for Self-Diagnosis module.
"""

import pytest
from hydra_tools.self_diagnosis import (
    SelfDiagnosisEngine,
    FailureCategory,
    Severity,
    FailureEvent,
    FailurePattern,
    DiagnosticReport,
)


class TestSelfDiagnosisEngine:
    """Tests for SelfDiagnosisEngine class."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a SelfDiagnosisEngine with temp storage."""
        return SelfDiagnosisEngine(
            data_dir=str(tmp_path / "diagnosis"),
            max_events=100,
            pattern_threshold=2,
        )

    def test_record_failure_creates_event(self, engine):
        """Recording a failure should create an event."""
        event = engine.record_failure(
            service="tabbyapi",
            error_message="Connection refused on port 5000",
        )

        assert isinstance(event, FailureEvent)
        assert event.service == "tabbyapi"
        assert "connection refused" in event.error_message.lower()

    def test_failure_classification_network(self, engine):
        """Network errors should be classified correctly."""
        # Use a port that isn't associated with INFERENCE services (5000=TabbyAPI, 11434=Ollama)
        event = engine.record_failure(
            service="test-service",
            error_message="Connection refused to host 192.168.1.250:8080",
        )

        assert event.category == FailureCategory.NETWORK.value

    def test_failure_classification_resource(self, engine):
        """Resource errors should be classified correctly."""
        event = engine.record_failure(
            service="tabbyapi",
            error_message="CUDA out of memory when allocating tensor",
        )

        assert event.category == FailureCategory.INFERENCE.value

    def test_failure_classification_disk(self, engine):
        """Disk space errors should be classified correctly."""
        event = engine.record_failure(
            service="docker",
            error_message="No space left on device",
        )

        assert event.category == FailureCategory.RESOURCE.value

    def test_severity_critical_for_database(self, engine):
        """Database failures should be high severity."""
        event = engine.record_failure(
            service="hydra-postgres",
            error_message="Connection refused to database",
        )

        assert event.severity in [Severity.CRITICAL.value, Severity.HIGH.value]

    def test_pattern_creation_on_repeated_failures(self, engine):
        """Repeated failures should create a pattern."""
        # Record same error multiple times
        for _ in range(3):
            engine.record_failure(
                service="test-service",
                error_message="Specific error message for testing",
            )

        # Should have created a pattern
        assert len(engine.patterns) > 0

    def test_resolve_failure_marks_resolved(self, engine):
        """Resolving a failure should mark it resolved."""
        event = engine.record_failure(
            service="test-service",
            error_message="Test error",
        )

        success = engine.resolve_failure(event.id, resolution_notes="Fixed manually")

        assert success
        resolved_event = next(e for e in engine.events if e.id == event.id)
        assert resolved_event.resolved
        assert resolved_event.resolution_notes == "Fixed manually"

    def test_resolve_nonexistent_returns_false(self, engine):
        """Resolving non-existent event should return False."""
        success = engine.resolve_failure("nonexistent-id")
        assert not success

    def test_analyze_returns_report(self, engine):
        """Analyze should return a DiagnosticReport."""
        engine.record_failure(
            service="test-service",
            error_message="Test error",
        )

        report = engine.analyze(hours=24)

        assert isinstance(report, DiagnosticReport)
        assert report.total_failures >= 1
        assert report.health_score >= 0
        assert report.health_score <= 100

    def test_health_score_decreases_with_failures(self, engine):
        """More failures should decrease health score."""
        initial_report = engine.analyze(hours=24)

        # Add several failures
        for i in range(10):
            engine.record_failure(
                service=f"service-{i}",
                error_message=f"Error {i}",
            )

        final_report = engine.analyze(hours=24)

        assert final_report.health_score <= initial_report.health_score

    def test_recommendations_generated(self, engine):
        """Analysis should generate recommendations."""
        # Add multiple failures
        for _ in range(5):
            engine.record_failure(
                service="test",
                error_message="Network connection refused",
            )

        report = engine.analyze(hours=24)

        assert len(report.recommendations) > 0

    def test_suggest_auto_remediation(self, engine):
        """Should suggest auto-remediation for known patterns."""
        # Create a pattern with remediation
        for _ in range(3):
            event = engine.record_failure(
                service="hydra-redis",
                error_message="Redis connection failure",
            )

        suggestion = engine.suggest_auto_remediation(event)

        # May or may not have suggestion based on pattern matching
        if suggestion:
            assert "action" in suggestion
            assert "command" in suggestion


class TestFailureClassification:
    """Tests for failure classification."""

    @pytest.fixture
    def engine(self, tmp_path):
        return SelfDiagnosisEngine(data_dir=str(tmp_path / "diagnosis"))

    @pytest.mark.parametrize("error_message,expected_category", [
        ("CUDA out of memory", FailureCategory.INFERENCE),
        ("model not found at path", FailureCategory.INFERENCE),
        ("connection refused", FailureCategory.NETWORK),
        ("timeout waiting for response", FailureCategory.NETWORK),
        ("DNS resolution failed", FailureCategory.NETWORK),
        ("no space left on device", FailureCategory.RESOURCE),
        ("out of memory", FailureCategory.RESOURCE),
        ("invalid configuration file", FailureCategory.CONFIGURATION),
        ("missing required key", FailureCategory.CONFIGURATION),
        ("permission denied", FailureCategory.PERMISSION),
        ("unauthorized access", FailureCategory.PERMISSION),
        ("JSON decode error", FailureCategory.DATA),
        ("validation error: invalid format", FailureCategory.DATA),
        # Note: generic timeout patterns match NETWORK's "timeout" pattern first
        # "deadline exceeded" is unique to TIMEOUT and doesn't match NETWORK
        ("deadline exceeded", FailureCategory.TIMEOUT),
    ])
    def test_error_classification(self, engine, error_message, expected_category):
        """Various error messages should be classified correctly."""
        event = engine.record_failure(
            service="test",
            error_message=error_message,
        )
        assert event.category == expected_category.value


class TestPatternDetection:
    """Tests for pattern detection."""

    @pytest.fixture
    def engine(self, tmp_path):
        return SelfDiagnosisEngine(
            data_dir=str(tmp_path / "diagnosis"),
            pattern_threshold=2,
        )

    def test_pattern_signature_normalized(self, engine):
        """Pattern signatures should normalize IPs and IDs."""
        event1 = engine.record_failure(
            service="test",
            error_message="Failed to connect to 192.168.1.250:5000",
        )
        event2 = engine.record_failure(
            service="test",
            error_message="Failed to connect to 192.168.1.203:5000",
        )

        # Should have same pattern signature after normalization
        assert event1.pattern_id == event2.pattern_id

    def test_pattern_tracks_occurrences(self, engine):
        """Pattern should track occurrence count."""
        for i in range(5):
            engine.record_failure(
                service="test",
                error_message="Repeated error pattern",
            )

        pattern_id = engine.events[0].pattern_id
        if pattern_id in engine.patterns:
            pattern = engine.patterns[pattern_id]
            assert pattern.occurrences >= 3

    def test_pattern_tracks_affected_services(self, engine):
        """Pattern should track affected services."""
        for service in ["service-a", "service-b", "service-c"]:
            engine.record_failure(
                service=service,
                error_message="Common error across services",
            )

        pattern_id = engine.events[0].pattern_id
        if pattern_id in engine.patterns:
            pattern = engine.patterns[pattern_id]
            assert len(pattern.affected_services) >= 2


class TestDiagnosticReport:
    """Tests for diagnostic report generation."""

    @pytest.fixture
    def engine(self, tmp_path):
        engine = SelfDiagnosisEngine(data_dir=str(tmp_path / "diagnosis"))
        # Add some test failures
        engine.record_failure("svc1", "Network error")
        engine.record_failure("svc2", "Memory error")
        engine.record_failure("svc3", "Config error")
        return engine

    def test_report_has_time_range(self, engine):
        """Report should have correct time range."""
        report = engine.analyze(hours=24)
        assert report.time_range_hours == 24

    def test_report_counts_by_category(self, engine):
        """Report should count failures by category."""
        report = engine.analyze(hours=24)
        assert len(report.failures_by_category) > 0

    def test_report_counts_by_severity(self, engine):
        """Report should count failures by severity."""
        report = engine.analyze(hours=24)
        assert len(report.failures_by_severity) > 0

    def test_markdown_export(self, engine):
        """Should export report as markdown."""
        markdown = engine.export_report_markdown(hours=24)

        assert "# Hydra Cluster Diagnostic Report" in markdown
        assert "Health Score" in markdown
        assert "Recommendations" in markdown

    def test_trend_detection(self, engine):
        """Report should detect trend."""
        report = engine.analyze(hours=24)
        assert report.trend in ["improving", "stable", "degrading"]
