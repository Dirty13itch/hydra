"""
Tests for Resource Optimization module.
"""

import pytest
from hydra_tools.resource_optimization import (
    ResourceOptimizer,
    ResourceType,
    OptimizationPriority,
    ResourceSnapshot,
    UtilizationPattern,
    OptimizationSuggestion,
    ModelLoadingSuggestion,
)


class TestResourceOptimizer:
    """Tests for ResourceOptimizer class."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        """Create a ResourceOptimizer with temp storage."""
        return ResourceOptimizer(
            data_dir=str(tmp_path / "optimization"),
            retention_hours=168,
        )

    def test_collect_snapshot_known_node(self, optimizer):
        """Collecting snapshot from known node should succeed."""
        snapshot = optimizer.collect_snapshot("hydra-ai")

        assert snapshot is not None
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.node == "hydra-ai"
        assert len(snapshot.gpu_memory_used_mb) == 2  # 5090 + 4090

    def test_collect_snapshot_unknown_node(self, optimizer):
        """Collecting snapshot from unknown node should return None."""
        snapshot = optimizer.collect_snapshot("unknown-node")
        assert snapshot is None

    def test_snapshot_persisted(self, optimizer):
        """Snapshots should be persisted."""
        optimizer.collect_snapshot("hydra-ai")

        # Create new optimizer with same path
        new_optimizer = ResourceOptimizer(
            data_dir=str(optimizer.data_dir),
        )

        assert len(new_optimizer.snapshots) >= 1

    def test_analyze_patterns_empty_data(self, optimizer):
        """Analyzing patterns with no data should return empty list."""
        patterns = optimizer.analyze_patterns("hydra-ai", hours=24)
        assert patterns == []

    def test_analyze_patterns_with_data(self, optimizer):
        """Analyzing patterns with data should return patterns."""
        # Collect several snapshots
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")

        patterns = optimizer.analyze_patterns("hydra-ai", hours=24)

        # Should have patterns for GPU memory, CPU, RAM
        assert len(patterns) > 0
        assert all(isinstance(p, UtilizationPattern) for p in patterns)

    def test_pattern_has_required_fields(self, optimizer):
        """Patterns should have all required fields."""
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")

        patterns = optimizer.analyze_patterns("hydra-ai", hours=24)

        if patterns:
            pattern = patterns[0]
            assert pattern.resource is not None
            assert pattern.node == "hydra-ai"
            assert pattern.avg_utilization >= 0
            assert pattern.peak_utilization >= pattern.avg_utilization
            assert pattern.pattern_type in ["consistent", "bursty", "idle", "overloaded"]

    def test_generate_suggestions(self, optimizer):
        """Should generate optimization suggestions."""
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")
            optimizer.collect_snapshot("hydra-compute")

        suggestions = optimizer.generate_suggestions()

        assert isinstance(suggestions, list)
        assert all(isinstance(s, OptimizationSuggestion) for s in suggestions)

    def test_suggestion_has_priority(self, optimizer):
        """Suggestions should have priority levels."""
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")

        suggestions = optimizer.generate_suggestions()

        for suggestion in suggestions:
            assert suggestion.priority in [
                OptimizationPriority.CRITICAL.value,
                OptimizationPriority.HIGH.value,
                OptimizationPriority.MEDIUM.value,
                OptimizationPriority.LOW.value,
            ]

    def test_model_placement_suggestions(self, optimizer):
        """Should provide model placement suggestions."""
        placements = optimizer.suggest_model_placement()

        assert len(placements) > 0
        assert all(isinstance(p, ModelLoadingSuggestion) for p in placements)

        for placement in placements:
            assert placement.model_name
            assert placement.suggested_location
            assert placement.reason

    def test_power_recommendations(self, optimizer):
        """Should provide power recommendations."""
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")

        recommendations = optimizer.get_power_recommendations()

        assert isinstance(recommendations, list)

    def test_export_report(self, optimizer):
        """Should export comprehensive report."""
        for _ in range(5):
            optimizer.collect_snapshot("hydra-ai")

        report = optimizer.export_report()

        assert "generated_at" in report
        assert "summary" in report
        assert "suggestions" in report
        assert "model_placement" in report
        assert "cluster_health" in report

    def test_cluster_health_calculation(self, optimizer):
        """Should calculate cluster health."""
        health = optimizer._calculate_cluster_health()

        assert "score" in health
        assert "status" in health
        assert health["score"] >= 0
        assert health["score"] <= 100
        assert health["status"] in ["healthy", "degraded", "critical"]


class TestNodeConfiguration:
    """Tests for node configuration handling."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return ResourceOptimizer(data_dir=str(tmp_path / "optimization"))

    def test_hydra_ai_configuration(self, optimizer):
        """hydra-ai should have correct configuration."""
        config = optimizer.NODES["hydra-ai"]

        assert config["ip"] == "192.168.1.250"
        assert len(config["gpus"]) == 2
        assert config["gpus"][0]["name"] == "RTX 5090"
        assert config["gpus"][0]["vram_mb"] == 32768
        assert config["gpus"][1]["name"] == "RTX 4090"
        assert config["role"] == "primary-inference"

    def test_hydra_compute_configuration(self, optimizer):
        """hydra-compute should have correct configuration."""
        config = optimizer.NODES["hydra-compute"]

        assert config["ip"] == "192.168.1.203"
        assert len(config["gpus"]) == 2
        assert config["gpus"][0]["name"] == "RTX 5070 Ti"
        assert config["role"] == "secondary-inference"

    def test_hydra_storage_configuration(self, optimizer):
        """hydra-storage should have correct configuration."""
        config = optimizer.NODES["hydra-storage"]

        assert config["ip"] == "192.168.1.244"
        assert len(config["gpus"]) == 1
        assert config["gpus"][0]["name"] == "Arc A380"
        assert config["role"] == "storage-docker"


class TestThresholds:
    """Tests for threshold configuration."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return ResourceOptimizer(data_dir=str(tmp_path / "optimization"))

    def test_gpu_memory_thresholds(self, optimizer):
        """GPU memory thresholds should be configured."""
        assert optimizer.THRESHOLDS["gpu_memory_high"] == 0.90
        assert optimizer.THRESHOLDS["gpu_memory_low"] == 0.30

    def test_temperature_thresholds(self, optimizer):
        """Temperature thresholds should be configured."""
        assert optimizer.THRESHOLDS["gpu_temp_warning"] == 80
        assert optimizer.THRESHOLDS["gpu_temp_critical"] == 90

    def test_cpu_ram_thresholds(self, optimizer):
        """CPU and RAM thresholds should be configured."""
        assert optimizer.THRESHOLDS["cpu_high"] == 0.85
        assert optimizer.THRESHOLDS["ram_high"] == 0.90


class TestPatternClassification:
    """Tests for utilization pattern classification."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return ResourceOptimizer(data_dir=str(tmp_path / "optimization"))

    def test_classify_overloaded(self, optimizer):
        """High utilization should be classified as overloaded."""
        pattern = optimizer._classify_pattern([95, 92, 98, 94, 96])
        assert pattern == "overloaded"

    def test_classify_idle(self, optimizer):
        """Low utilization should be classified as idle."""
        pattern = optimizer._classify_pattern([5, 8, 3, 10, 7])
        assert pattern == "idle"

    def test_classify_bursty(self, optimizer):
        """Variable utilization should be classified as bursty."""
        pattern = optimizer._classify_pattern([10, 80, 20, 90, 30])
        assert pattern == "bursty"

    def test_classify_consistent(self, optimizer):
        """Stable mid-range utilization should be classified as consistent."""
        pattern = optimizer._classify_pattern([50, 52, 48, 51, 49])
        assert pattern == "consistent"
