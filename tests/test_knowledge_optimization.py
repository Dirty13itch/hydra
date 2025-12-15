"""
Tests for Knowledge Optimization module.
"""

import pytest
from hydra_tools.knowledge_optimization import (
    KnowledgeOptimizer,
    KnowledgeSource,
    KnowledgeCategory,
    KnowledgeEntry,
    ConsolidationSuggestion,
    PruningSuggestion,
    KnowledgeMetrics,
)


class TestKnowledgeOptimizer:
    """Tests for KnowledgeOptimizer class."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        """Create a KnowledgeOptimizer with temp storage."""
        return KnowledgeOptimizer(
            data_dir=str(tmp_path / "knowledge"),
            similarity_threshold=0.85,
        )

    def test_add_entry_creates_entry(self, optimizer):
        """Adding an entry should create it."""
        entry = optimizer.add_entry(
            content="Test knowledge content about infrastructure",
            source=KnowledgeSource.KNOWLEDGE_FILES,
        )

        assert isinstance(entry, KnowledgeEntry)
        assert entry.content == "Test knowledge content about infrastructure"
        assert entry.source == KnowledgeSource.KNOWLEDGE_FILES.value

    def test_add_entry_detects_category(self, optimizer):
        """Entry category should be detected from content."""
        entry = optimizer.add_entry(
            content="The GPU on hydra-ai is an RTX 5090 with 32GB VRAM",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        assert entry.category == KnowledgeCategory.INFRASTRUCTURE.value

    def test_add_entry_explicit_category(self, optimizer):
        """Explicit category should override detection."""
        entry = optimizer.add_entry(
            content="Some random content",
            source=KnowledgeSource.SESSION_MEMORY,
            category=KnowledgeCategory.PROCEDURES,
        )

        assert entry.category == KnowledgeCategory.PROCEDURES.value

    def test_duplicate_entry_updates_access(self, optimizer):
        """Adding duplicate entry should update access info."""
        entry1 = optimizer.add_entry(
            content="Unique test content",
            source=KnowledgeSource.KNOWLEDGE_FILES,
        )

        entry2 = optimizer.add_entry(
            content="Unique test content",  # Same content
            source=KnowledgeSource.KNOWLEDGE_FILES,
        )

        assert entry1.id == entry2.id
        assert entry2.access_count == 2

    def test_record_access(self, optimizer):
        """Recording access should update entry."""
        entry = optimizer.add_entry(
            content="Test content",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        initial_count = entry.access_count
        optimizer.record_access(entry.id)

        assert optimizer.entries[entry.id].access_count == initial_count + 1

    def test_record_access_nonexistent(self, optimizer):
        """Recording access for non-existent entry should return False."""
        result = optimizer.record_access("nonexistent-id")
        assert result is False


class TestCategoryDetection:
    """Tests for knowledge category detection."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    @pytest.mark.parametrize("content,expected_category", [
        ("The GPU has 32GB of VRAM and runs at 450W", KnowledgeCategory.INFRASTRUCTURE),
        ("Configure the yaml file with these settings", KnowledgeCategory.CONFIGURATION),
        ("To fix this error, restart the container", KnowledgeCategory.TROUBLESHOOTING),
        ("Step 1: Deploy the service using docker-compose", KnowledgeCategory.PROCEDURES),
        ("Shaun prefers concise responses", KnowledgeCategory.USER_PREFERENCES),
        ("Research shows the latest version has new features", KnowledgeCategory.RESEARCH),
    ])
    def test_category_detection(self, optimizer, content, expected_category):
        """Content should be categorized correctly."""
        detected = optimizer._detect_category(content)
        assert detected == expected_category


class TestStalenessDetection:
    """Tests for stale entry detection."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    def test_find_stale_entries_empty(self, optimizer):
        """Empty knowledge store should return no stale entries."""
        stale = optimizer.find_stale_entries()
        assert stale == []

    def test_recent_entry_not_stale(self, optimizer):
        """Recently accessed entry should not be stale."""
        optimizer.add_entry(
            content="Fresh content",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        stale = optimizer.find_stale_entries()
        assert len(stale) == 0

    def test_stale_entry_returns_suggestion(self, optimizer):
        """Stale entry should return pruning suggestion."""
        from datetime import datetime, timedelta

        entry = optimizer.add_entry(
            content="Old content",
            source=KnowledgeSource.SESSION_MEMORY,
            category=KnowledgeCategory.TEMPORARY,
        )

        # Manually make it stale
        old_date = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
        optimizer.entries[entry.id].last_accessed = old_date

        stale = optimizer.find_stale_entries()

        # Temporary category has 7 day threshold
        assert len(stale) >= 1
        assert any(s.entry_id == entry.id for s in stale)


class TestRedundancyDetection:
    """Tests for redundant entry detection."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(
            data_dir=str(tmp_path / "knowledge"),
            similarity_threshold=0.8,
        )

    def test_find_redundant_empty(self, optimizer):
        """Empty store should return no redundant entries."""
        redundant = optimizer.find_redundant_entries()
        assert redundant == []

    def test_similar_entries_detected(self, optimizer):
        """Very similar entries should be detected."""
        optimizer.add_entry(
            content="The GPU memory usage on hydra-ai is currently at 80%",
            source=KnowledgeSource.SESSION_MEMORY,
        )
        optimizer.add_entry(
            content="The GPU memory usage on hydra-ai is currently at 82%",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        redundant = optimizer.find_redundant_entries()

        assert len(redundant) >= 1
        assert all(isinstance(r, ConsolidationSuggestion) for r in redundant)

    def test_different_entries_not_redundant(self, optimizer):
        """Different entries should not be flagged."""
        optimizer.add_entry(
            content="Information about GPU performance",
            source=KnowledgeSource.SESSION_MEMORY,
        )
        optimizer.add_entry(
            content="Database connection settings for PostgreSQL",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        redundant = optimizer.find_redundant_entries()

        assert len(redundant) == 0


class TestPruning:
    """Tests for entry pruning."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    def test_prune_entries(self, optimizer):
        """Pruning should remove entries."""
        entry = optimizer.add_entry(
            content="To be deleted",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        result = optimizer.prune_entries([entry.id])

        assert result["pruned"] == 1
        assert entry.id not in optimizer.entries

    def test_prune_with_archive(self, optimizer):
        """Pruning with archive should save entries."""
        entry = optimizer.add_entry(
            content="To be archived",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        result = optimizer.prune_entries([entry.id], archive=True)

        assert result["archived"] == 1

    def test_prune_nonexistent(self, optimizer):
        """Pruning non-existent entry should not error."""
        result = optimizer.prune_entries(["nonexistent-id"])
        assert result["pruned"] == 0


class TestConsolidation:
    """Tests for entry consolidation."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    def test_consolidate_entries(self, optimizer):
        """Consolidating should merge entries."""
        entry1 = optimizer.add_entry(
            content="First version of content",
            source=KnowledgeSource.SESSION_MEMORY,
        )
        entry2 = optimizer.add_entry(
            content="Second version of the same content with more detail",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        result = optimizer.consolidate_entries([entry1.id, entry2.id])

        assert result is not None
        assert len(optimizer.entries) == 1

    def test_consolidate_keeps_access_count(self, optimizer):
        """Consolidated entry should have combined access count."""
        entry1 = optimizer.add_entry(
            content="Content A",
            source=KnowledgeSource.SESSION_MEMORY,
        )
        for _ in range(5):
            optimizer.record_access(entry1.id)

        entry2 = optimizer.add_entry(
            content="Content B",
            source=KnowledgeSource.SESSION_MEMORY,
        )
        for _ in range(3):
            optimizer.record_access(entry2.id)

        result = optimizer.consolidate_entries([entry1.id, entry2.id])

        assert result.access_count >= 8  # 6 + 4 (initial adds count)

    def test_consolidate_too_few_entries(self, optimizer):
        """Consolidating single entry should return None."""
        entry = optimizer.add_entry(
            content="Single entry",
            source=KnowledgeSource.SESSION_MEMORY,
        )

        result = optimizer.consolidate_entries([entry.id])

        assert result is None


class TestMetrics:
    """Tests for metrics computation."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    def test_compute_metrics_empty(self, optimizer):
        """Empty store should return valid metrics."""
        metrics = optimizer.compute_metrics()

        assert isinstance(metrics, KnowledgeMetrics)
        assert metrics.total_entries == 0

    def test_compute_metrics_with_data(self, optimizer):
        """Metrics should reflect stored data."""
        optimizer.add_entry("Content 1", KnowledgeSource.KNOWLEDGE_FILES)
        optimizer.add_entry("Content 2", KnowledgeSource.SESSION_MEMORY)
        optimizer.add_entry("Content 3", KnowledgeSource.LETTA_ARCHIVAL)

        metrics = optimizer.compute_metrics()

        assert metrics.total_entries == 3
        assert len(metrics.entries_by_source) >= 1
        assert metrics.total_size_mb > 0

    def test_metrics_has_recommendations(self, optimizer):
        """Metrics should include recommendations."""
        metrics = optimizer.compute_metrics()

        assert len(metrics.recommendations) > 0


class TestOptimization:
    """Tests for full optimization pass."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        return KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))

    def test_optimize_empty_store(self, optimizer):
        """Optimizing empty store should not error."""
        result = optimizer.optimize()

        assert "stale_pruned" in result
        assert "redundant_consolidated" in result
        assert "actions" in result

    def test_optimize_returns_actions(self, optimizer):
        """Optimization should return list of actions taken."""
        optimizer.add_entry("Content", KnowledgeSource.SESSION_MEMORY)

        result = optimizer.optimize()

        assert isinstance(result["actions"], list)


class TestHealthReport:
    """Tests for health report export."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        opt = KnowledgeOptimizer(data_dir=str(tmp_path / "knowledge"))
        opt.add_entry("Test content 1", KnowledgeSource.KNOWLEDGE_FILES)
        opt.add_entry("Test content 2", KnowledgeSource.SESSION_MEMORY)
        return opt

    def test_export_health_report(self, optimizer):
        """Should export health report as markdown."""
        markdown = optimizer.export_health_report()

        assert "# Knowledge Store Health Report" in markdown
        assert "Summary" in markdown
        assert "Recommendations" in markdown

    def test_report_includes_counts(self, optimizer):
        """Report should include entry counts."""
        markdown = optimizer.export_health_report()

        assert "Total Entries" in markdown
        assert "By Source" in markdown
