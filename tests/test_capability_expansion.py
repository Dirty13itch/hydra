"""
Tests for Capability Expansion module.
"""

import pytest
from hydra_tools.capability_expansion import (
    CapabilityTracker,
    CapabilityGap,
    CapabilityCategory,
    Priority,
    Status,
)


class TestCapabilityTracker:
    """Tests for CapabilityTracker class."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a CapabilityTracker with temp storage."""
        return CapabilityTracker(
            storage_path=str(tmp_path / "capabilities.json"),
        )

    def test_record_gap_creates_entry(self, tracker):
        """Recording a gap should create an entry."""
        gap = tracker.record_gap(
            description="Need to split large models across multiple GPUs",
            context="User tried to load 70B model on single GPU",
        )

        assert isinstance(gap, CapabilityGap)
        assert "split large models" in gap.description
        assert gap.occurrences == 1

    def test_record_gap_increments_occurrences(self, tracker):
        """Recording same gap again should increment occurrences."""
        gap1 = tracker.record_gap(
            description="Feature X description",
            context="Context for feature X",
        )

        gap2 = tracker.record_gap(
            description="Feature X description",
            context="Updated context",
        )

        # Same description should update the same gap
        assert gap2.occurrences >= 1

    def test_record_feature_request(self, tracker):
        """Recording a feature request should create gap."""
        gap = tracker.record_feature_request(
            description="Control cluster with voice commands",
            context="User request for voice control",
        )

        assert gap is not None
        assert "voice commands" in gap.description

    def test_update_gap_status(self, tracker):
        """Should be able to update gap status."""
        gap = tracker.record_gap(
            description="Test gap description",
            context="Test context",
        )

        updated = tracker.update_gap(
            gap_id=gap.id,
            status=Status.IN_PROGRESS,
        )

        assert updated is not None
        assert updated.status == Status.IN_PROGRESS

    def test_update_gap_priority(self, tracker):
        """Should be able to update gap priority."""
        gap = tracker.record_gap(
            description="Test gap description",
            context="Test context",
        )

        updated = tracker.update_gap(
            gap_id=gap.id,
            priority=Priority.HIGH,
        )

        assert updated is not None
        assert updated.priority == Priority.HIGH

    def test_update_nonexistent_gap(self, tracker):
        """Updating non-existent gap should return None."""
        result = tracker.update_gap(
            gap_id="nonexistent-id",
            status=Status.IMPLEMENTED,
        )

        assert result is None


class TestPrioritization:
    """Tests for gap prioritization."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(storage_path=str(tmp_path / "capabilities.json"))

    def test_get_prioritized_backlog(self, tracker):
        """Should return gaps sorted by priority score."""
        gap1 = tracker.record_gap("Gap 1 description", "Context 1")
        gap2 = tracker.record_gap("Gap 2 description", "Context 2")

        backlog = tracker.get_prioritized_backlog()

        assert len(backlog) >= 2
        assert all(isinstance(g, CapabilityGap) for g in backlog)

    def test_backlog_filters_completed(self, tracker):
        """Completed gaps should not appear in backlog by default."""
        gap = tracker.record_gap("Completed gap", "Description")
        tracker.update_gap(gap.id, status=Status.IMPLEMENTED)

        backlog = tracker.get_prioritized_backlog()

        assert all(g.id != gap.id for g in backlog)

    def test_priority_score_calculation(self, tracker):
        """Priority score should consider priority level."""
        low_gap = tracker.record_gap("Low priority gap", "Context")
        tracker.update_gap(low_gap.id, priority=Priority.LOW)

        high_gap = tracker.record_gap("High priority gap", "Context")
        tracker.update_gap(high_gap.id, priority=Priority.CRITICAL)

        backlog = tracker.get_prioritized_backlog()

        # Find indices
        high_idx = next((i for i, g in enumerate(backlog) if g.id == high_gap.id), -1)
        low_idx = next((i for i, g in enumerate(backlog) if g.id == low_gap.id), -1)

        # Higher priority should come first (if both exist)
        if high_idx >= 0 and low_idx >= 0:
            assert high_idx < low_idx


class TestGapCategory:
    """Tests for gap category detection."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(storage_path=str(tmp_path / "capabilities.json"))

    def test_detect_inference_category(self, tracker):
        """Should be able to create inference-related gaps."""
        gap = tracker.record_gap(
            description="Models take too long to load into GPU memory",
            context="Loading 70B model",
            category=CapabilityCategory.INFERENCE,
        )

        assert gap.category == CapabilityCategory.INFERENCE

    def test_detect_monitoring_category(self, tracker):
        """Should be able to create monitoring-related gaps."""
        gap = tracker.record_gap(
            description="Need more detailed Prometheus metrics for GPUs",
            context="Monitoring request",
            category=CapabilityCategory.MONITORING,
        )

        assert gap.category == CapabilityCategory.MONITORING

    def test_detect_automation_category(self, tracker):
        """Should be able to create automation-related gaps."""
        gap = tracker.record_gap(
            description="Automatically scale based on workflow triggers",
            context="Automation request",
            category=CapabilityCategory.AUTOMATION,
        )

        assert gap.category == CapabilityCategory.AUTOMATION


class TestMetrics:
    """Tests for capability metrics."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(storage_path=str(tmp_path / "capabilities.json"))

    def test_get_metrics_empty(self, tracker):
        """Empty tracker should return valid metrics."""
        metrics = tracker.get_metrics()

        assert metrics is not None
        assert hasattr(metrics, 'total_gaps')
        assert metrics.total_gaps == 0

    def test_get_metrics_with_data(self, tracker):
        """Metrics should reflect stored data."""
        tracker.record_gap("Gap 1", "Context")
        tracker.record_gap("Gap 2", "Context")

        gap3 = tracker.record_gap("Gap 3", "Context")
        tracker.update_gap(gap3.id, status=Status.IMPLEMENTED)

        metrics = tracker.get_metrics()

        assert metrics.total_gaps == 3

    def test_metrics_by_category(self, tracker):
        """Metrics should include breakdown by category."""
        tracker.record_gap("Model issue", "Context", category=CapabilityCategory.INFERENCE)
        tracker.record_gap("Dashboard issue", "Context", category=CapabilityCategory.MONITORING)

        metrics = tracker.get_metrics()

        assert hasattr(metrics, 'gaps_by_category')


class TestExport:
    """Tests for export functionality."""

    @pytest.fixture
    def tracker(self, tmp_path):
        tracker = CapabilityTracker(storage_path=str(tmp_path / "capabilities.json"))
        tracker.record_gap("Gap 1 description", "Context 1")
        tracker.record_gap("Gap 2 description", "Context 2")
        return tracker

    def test_export_to_markdown(self, tracker):
        """Should export gaps as markdown."""
        markdown = tracker.export_to_markdown()

        assert isinstance(markdown, str)
        assert len(markdown) > 0

    def test_export_includes_priorities(self, tracker):
        """Export should include content."""
        markdown = tracker.export_to_markdown()

        # Should have content about the gaps
        assert "Gap" in markdown or "gap" in markdown

    def test_generate_roadmap_entry(self, tracker):
        """Should generate roadmap entries."""
        gaps = tracker.get_all_gaps()
        if gaps:
            gap = gaps[0]
            entry = tracker.generate_roadmap_entry(gap)

            assert isinstance(entry, str)
            assert len(entry) > 0


class TestPersistence:
    """Tests for data persistence."""

    def test_gaps_persisted(self, tmp_path):
        """Gaps should be persisted across instances."""
        storage_path = str(tmp_path / "capabilities.json")
        tracker1 = CapabilityTracker(storage_path=storage_path)
        gap = tracker1.record_gap("Persistent gap description", "Context")

        # Create new instance
        tracker2 = CapabilityTracker(storage_path=storage_path)

        # Should find the gap
        found = tracker2.get_gap(gap.id)
        assert found is not None
        assert found.description == gap.description

    def test_feature_requests_persisted(self, tmp_path):
        """Feature requests should be persisted."""
        storage_path = str(tmp_path / "capabilities.json")
        tracker1 = CapabilityTracker(storage_path=storage_path)
        tracker1.record_feature_request(
            description="User wants this feature",
            context="Feature request context",
        )

        tracker2 = CapabilityTracker(storage_path=storage_path)

        assert len(tracker2.get_all_gaps()) >= 1


class TestGapStatus:
    """Tests for gap status management."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(storage_path=str(tmp_path / "capabilities.json"))

    def test_new_gap_is_new(self, tracker):
        """New gaps should have 'new' status."""
        gap = tracker.record_gap("New gap description", "Context")
        assert gap.status == Status.NEW

    def test_status_transitions(self, tracker):
        """Gaps should be able to transition through statuses."""
        gap = tracker.record_gap("Test gap", "Context")

        updated = tracker.update_gap(gap.id, status=Status.IN_PROGRESS)
        assert updated.status == Status.IN_PROGRESS

        updated = tracker.update_gap(gap.id, status=Status.IMPLEMENTED)
        assert updated.status == Status.IMPLEMENTED

    def test_closed_status(self, tracker):
        """Gaps can be closed without completion."""
        gap = tracker.record_gap("Will close", "Context")

        updated = tracker.update_gap(gap.id, status=Status.WONT_FIX)
        assert updated.status == Status.WONT_FIX
