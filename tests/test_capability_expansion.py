"""
Tests for Capability Expansion module.
"""

import pytest
from hydra_tools.capability_expansion import (
    CapabilityTracker,
    CapabilityGap,
    GapPriority,
    GapStatus,
)


class TestCapabilityTracker:
    """Tests for CapabilityTracker class."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a CapabilityTracker with temp storage."""
        return CapabilityTracker(
            data_dir=str(tmp_path / "capabilities"),
        )

    def test_record_gap_creates_entry(self, tracker):
        """Recording a gap should create an entry."""
        gap = tracker.record_gap(
            title="Support for multi-GPU tensor parallelism",
            description="Need to split large models across multiple GPUs",
            context="User tried to load 70B model on single GPU",
        )

        assert isinstance(gap, CapabilityGap)
        assert gap.title == "Support for multi-GPU tensor parallelism"
        assert gap.occurrences == 1

    def test_record_gap_increments_occurrences(self, tracker):
        """Recording same gap again should increment occurrences."""
        gap1 = tracker.record_gap(
            title="Feature X",
            description="Description of feature X",
        )

        gap2 = tracker.record_gap(
            title="Feature X",
            description="Updated description",
        )

        assert gap1.id == gap2.id
        assert gap2.occurrences == 2

    def test_record_feature_request(self, tracker):
        """Recording a feature request should create gap."""
        gap = tracker.record_feature_request(
            title="Add voice control",
            description="Control cluster with voice commands",
            requested_by="shaun",
        )

        assert gap is not None
        assert gap.title == "Add voice control"
        assert gap.source == "feature_request"

    def test_update_gap_status(self, tracker):
        """Should be able to update gap status."""
        gap = tracker.record_gap(
            title="Test gap",
            description="Test description",
        )

        success = tracker.update_gap(
            gap_id=gap.id,
            status=GapStatus.IN_PROGRESS,
        )

        assert success
        assert tracker.gaps[gap.id].status == GapStatus.IN_PROGRESS.value

    def test_update_gap_priority(self, tracker):
        """Should be able to update gap priority."""
        gap = tracker.record_gap(
            title="Test gap",
            description="Test description",
        )

        success = tracker.update_gap(
            gap_id=gap.id,
            priority=GapPriority.HIGH,
        )

        assert success
        assert tracker.gaps[gap.id].priority == GapPriority.HIGH.value

    def test_update_nonexistent_gap(self, tracker):
        """Updating non-existent gap should return False."""
        success = tracker.update_gap(
            gap_id="nonexistent-id",
            status=GapStatus.COMPLETED,
        )

        assert not success


class TestPrioritization:
    """Tests for gap prioritization."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

    def test_get_prioritized_backlog(self, tracker):
        """Should return gaps sorted by priority score."""
        # Add gaps with different occurrences
        gap1 = tracker.record_gap("Gap 1", "Desc 1")
        gap2 = tracker.record_gap("Gap 2", "Desc 2")

        # Make gap2 more frequent
        for _ in range(5):
            tracker.record_gap("Gap 2", "Desc 2")

        backlog = tracker.get_prioritized_backlog()

        # Gap 2 should be first due to more occurrences
        assert backlog[0].id == gap2.id

    def test_backlog_filters_completed(self, tracker):
        """Completed gaps should not appear in backlog."""
        gap = tracker.record_gap("Completed gap", "Description")
        tracker.update_gap(gap.id, status=GapStatus.COMPLETED)

        backlog = tracker.get_prioritized_backlog()

        assert all(g.id != gap.id for g in backlog)

    def test_priority_score_calculation(self, tracker):
        """Priority score should consider occurrences and priority level."""
        low_gap = tracker.record_gap("Low priority", "Desc")
        tracker.update_gap(low_gap.id, priority=GapPriority.LOW)

        high_gap = tracker.record_gap("High priority", "Desc")
        tracker.update_gap(high_gap.id, priority=GapPriority.HIGH)

        backlog = tracker.get_prioritized_backlog()

        # High priority should come first
        high_idx = next(i for i, g in enumerate(backlog) if g.id == high_gap.id)
        low_idx = next(i for i, g in enumerate(backlog) if g.id == low_gap.id)

        assert high_idx < low_idx


class TestGapCategory:
    """Tests for gap category detection."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

    def test_detect_inference_category(self, tracker):
        """Should detect inference-related gaps."""
        gap = tracker.record_gap(
            title="Faster model loading",
            description="Models take too long to load into GPU memory",
            context="Loading 70B model",
        )

        assert gap.category == "inference"

    def test_detect_monitoring_category(self, tracker):
        """Should detect monitoring-related gaps."""
        gap = tracker.record_gap(
            title="Better GPU metrics",
            description="Need more detailed Prometheus metrics for GPUs",
        )

        assert gap.category == "monitoring"

    def test_detect_automation_category(self, tracker):
        """Should detect automation-related gaps."""
        gap = tracker.record_gap(
            title="Auto-scaling containers",
            description="Automatically scale based on workflow triggers",
        )

        assert gap.category == "automation"


class TestMetrics:
    """Tests for capability metrics."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

    def test_get_metrics_empty(self, tracker):
        """Empty tracker should return valid metrics."""
        metrics = tracker.get_metrics()

        assert "total_gaps" in metrics
        assert metrics["total_gaps"] == 0

    def test_get_metrics_with_data(self, tracker):
        """Metrics should reflect stored data."""
        tracker.record_gap("Gap 1", "Desc")
        tracker.record_gap("Gap 2", "Desc")

        gap3 = tracker.record_gap("Gap 3", "Desc")
        tracker.update_gap(gap3.id, status=GapStatus.COMPLETED)

        metrics = tracker.get_metrics()

        assert metrics["total_gaps"] == 3
        assert metrics["open_gaps"] == 2
        assert metrics["completed_gaps"] == 1

    def test_metrics_by_category(self, tracker):
        """Metrics should include breakdown by category."""
        tracker.record_gap("Model issue", "Related to inference and models")
        tracker.record_gap("Dashboard issue", "Related to monitoring and metrics")

        metrics = tracker.get_metrics()

        assert "by_category" in metrics
        assert isinstance(metrics["by_category"], dict)


class TestExport:
    """Tests for export functionality."""

    @pytest.fixture
    def tracker(self, tmp_path):
        tracker = CapabilityTracker(data_dir=str(tmp_path / "capabilities"))
        tracker.record_gap("Gap 1", "Description 1")
        tracker.record_gap("Gap 2", "Description 2")
        return tracker

    def test_export_to_markdown(self, tracker):
        """Should export gaps as markdown."""
        markdown = tracker.export_to_markdown()

        assert "# Capability Backlog" in markdown
        assert "Gap 1" in markdown
        assert "Gap 2" in markdown

    def test_export_includes_priorities(self, tracker):
        """Export should include priority levels."""
        markdown = tracker.export_to_markdown()

        # Should mention priority somewhere
        assert "Priority" in markdown or "priority" in markdown

    def test_generate_roadmap_entry(self, tracker):
        """Should generate roadmap entries."""
        gap = tracker.record_gap(
            title="New feature",
            description="Description of feature",
        )

        entry = tracker.generate_roadmap_entry(gap.id)

        assert entry is not None
        assert "New feature" in entry["title"]
        assert "description" in entry


class TestPersistence:
    """Tests for data persistence."""

    def test_gaps_persisted(self, tmp_path):
        """Gaps should be persisted across instances."""
        tracker1 = CapabilityTracker(data_dir=str(tmp_path / "capabilities"))
        gap = tracker1.record_gap("Persistent gap", "Description")

        # Create new instance
        tracker2 = CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

        assert gap.id in tracker2.gaps
        assert tracker2.gaps[gap.id].title == "Persistent gap"

    def test_feature_requests_persisted(self, tmp_path):
        """Feature requests should be persisted."""
        tracker1 = CapabilityTracker(data_dir=str(tmp_path / "capabilities"))
        tracker1.record_feature_request(
            title="Requested feature",
            description="User wants this",
            requested_by="user",
        )

        tracker2 = CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

        assert len(tracker2.gaps) == 1


class TestGapStatus:
    """Tests for gap status management."""

    @pytest.fixture
    def tracker(self, tmp_path):
        return CapabilityTracker(data_dir=str(tmp_path / "capabilities"))

    def test_new_gap_is_open(self, tracker):
        """New gaps should have 'open' status."""
        gap = tracker.record_gap("New gap", "Description")
        assert gap.status == GapStatus.OPEN.value

    def test_status_transitions(self, tracker):
        """Gaps should be able to transition through statuses."""
        gap = tracker.record_gap("Test gap", "Description")

        tracker.update_gap(gap.id, status=GapStatus.IN_PROGRESS)
        assert tracker.gaps[gap.id].status == GapStatus.IN_PROGRESS.value

        tracker.update_gap(gap.id, status=GapStatus.COMPLETED)
        assert tracker.gaps[gap.id].status == GapStatus.COMPLETED.value

    def test_closed_status(self, tracker):
        """Gaps can be closed without completion."""
        gap = tracker.record_gap("Will close", "Description")

        tracker.update_gap(gap.id, status=GapStatus.CLOSED)
        assert tracker.gaps[gap.id].status == GapStatus.CLOSED.value
