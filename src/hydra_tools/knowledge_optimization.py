"""
Knowledge Optimization Tools for Hydra Cluster.

Manages knowledge lifecycle including:
- Pruning outdated archival memory
- Consolidating redundant knowledge
- Measuring knowledge quality and coverage
- Optimizing retrieval performance
"""

import json
import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
from collections import defaultdict
import difflib


class KnowledgeSource(Enum):
    """Sources of knowledge in the system."""
    LETTA_ARCHIVAL = "letta_archival"
    QDRANT_VECTOR = "qdrant_vector"
    KNOWLEDGE_FILES = "knowledge_files"
    SESSION_MEMORY = "session_memory"
    LEARNINGS_MD = "learnings_md"


class KnowledgeCategory(Enum):
    """Categories of knowledge."""
    INFRASTRUCTURE = "infrastructure"
    CONFIGURATION = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    PROCEDURES = "procedures"
    HISTORY = "history"
    USER_PREFERENCES = "user_preferences"
    RESEARCH = "research"
    TEMPORARY = "temporary"


@dataclass
class KnowledgeEntry:
    """Individual knowledge entry for analysis."""
    id: str
    source: str
    category: str
    content: str
    content_hash: str
    created_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0
    relevance_score: float = 1.0
    is_stale: bool = False
    is_redundant: bool = False
    related_entries: list = field(default_factory=list)


@dataclass
class ConsolidationSuggestion:
    """Suggestion for consolidating related knowledge."""
    entries: list[str]  # Entry IDs to consolidate
    similarity_score: float
    reason: str
    merged_content: Optional[str] = None
    space_savings_bytes: int = 0


@dataclass
class PruningSuggestion:
    """Suggestion for pruning stale knowledge."""
    entry_id: str
    source: str
    reason: str
    last_accessed: Optional[str]
    age_days: int
    confidence: float  # 0-1, higher = more confident it should be pruned


@dataclass
class KnowledgeMetrics:
    """Metrics about knowledge store health."""
    total_entries: int
    entries_by_source: dict
    entries_by_category: dict
    stale_entries: int
    redundant_entries: int
    avg_relevance_score: float
    total_size_mb: float
    recommendations: list[str]


class KnowledgeOptimizer:
    """
    Knowledge optimization engine for the Hydra cluster.

    Analyzes, consolidates, and prunes knowledge across all stores.
    """

    # Staleness thresholds by category
    STALENESS_THRESHOLDS = {
        KnowledgeCategory.INFRASTRUCTURE: 30,      # 30 days
        KnowledgeCategory.CONFIGURATION: 14,       # 14 days (configs change often)
        KnowledgeCategory.TROUBLESHOOTING: 60,     # 60 days
        KnowledgeCategory.PROCEDURES: 90,          # 90 days
        KnowledgeCategory.HISTORY: 365,            # 1 year
        KnowledgeCategory.USER_PREFERENCES: 180,   # 6 months
        KnowledgeCategory.RESEARCH: 30,            # 30 days (research gets outdated)
        KnowledgeCategory.TEMPORARY: 7,            # 7 days
    }

    # Keywords for category detection
    CATEGORY_KEYWORDS = {
        KnowledgeCategory.INFRASTRUCTURE: [
            "node", "gpu", "nvidia", "docker", "container", "port", "ip",
            "network", "storage", "nfs", "mount", "memory", "cpu", "disk",
        ],
        KnowledgeCategory.CONFIGURATION: [
            "config", "setting", "parameter", "yaml", "json", "env",
            "environment", "variable", "option", "flag",
        ],
        KnowledgeCategory.TROUBLESHOOTING: [
            "error", "fix", "issue", "problem", "debug", "fail", "crash",
            "restart", "recover", "rollback", "workaround",
        ],
        KnowledgeCategory.PROCEDURES: [
            "how to", "step", "procedure", "process", "workflow",
            "deploy", "install", "setup", "configure",
        ],
        KnowledgeCategory.USER_PREFERENCES: [
            "prefer", "like", "want", "style", "format", "approach",
            "shaun", "user", "personal",
        ],
        KnowledgeCategory.RESEARCH: [
            "research", "found", "discovered", "new", "latest",
            "update", "version", "release", "announcement",
        ],
    }

    def __init__(
        self,
        data_dir: str = "/mnt/user/appdata/hydra-stack/data/knowledge",
        similarity_threshold: float = 0.85,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.entries_file = self.data_dir / "knowledge_entries.json"
        self.metrics_file = self.data_dir / "knowledge_metrics.json"

        self.similarity_threshold = similarity_threshold
        self.entries: dict[str, KnowledgeEntry] = {}

        self._load_data()

    def _load_data(self):
        """Load persisted knowledge entries."""
        if self.entries_file.exists():
            try:
                with open(self.entries_file) as f:
                    data = json.load(f)
                    self.entries = {
                        k: KnowledgeEntry(**v) for k, v in data.items()
                    }
            except (json.JSONDecodeError, TypeError):
                self.entries = {}

    def _save_data(self):
        """Persist knowledge entries."""
        with open(self.entries_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self.entries.items()}, f, indent=2)

    def _compute_hash(self, content: str) -> str:
        """Compute content hash for deduplication."""
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _detect_category(self, content: str) -> KnowledgeCategory:
        """Detect knowledge category from content."""
        content_lower = content.lower()
        scores = defaultdict(int)

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[category] += 1

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return KnowledgeCategory.HISTORY

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts."""
        # Normalize texts
        norm1 = re.sub(r'\s+', ' ', text1.lower().strip())
        norm2 = re.sub(r'\s+', ' ', text2.lower().strip())

        # Use SequenceMatcher for similarity
        return difflib.SequenceMatcher(None, norm1, norm2).ratio()

    def add_entry(
        self,
        content: str,
        source: KnowledgeSource,
        category: Optional[KnowledgeCategory] = None,
        entry_id: Optional[str] = None,
    ) -> KnowledgeEntry:
        """Add a knowledge entry for tracking."""
        now = datetime.utcnow()
        content_hash = self._compute_hash(content)

        # Check for duplicates
        for existing in self.entries.values():
            if existing.content_hash == content_hash:
                # Update access info
                existing.last_accessed = now.isoformat() + "Z"
                existing.access_count += 1
                self._save_data()
                return existing

        if category is None:
            category = self._detect_category(content)

        if entry_id is None:
            entry_id = f"ke-{now.strftime('%Y%m%d%H%M%S')}-{len(self.entries) % 10000:04d}"

        entry = KnowledgeEntry(
            id=entry_id,
            source=source.value,
            category=category.value,
            content=content,
            content_hash=content_hash,
            created_at=now.isoformat() + "Z",
            last_accessed=now.isoformat() + "Z",
            access_count=1,
        )

        self.entries[entry_id] = entry
        self._save_data()
        return entry

    def record_access(self, entry_id: str) -> bool:
        """Record that an entry was accessed."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        entry.last_accessed = datetime.utcnow().isoformat() + "Z"
        entry.access_count += 1
        self._save_data()
        return True

    def find_stale_entries(self) -> list[PruningSuggestion]:
        """Find entries that may be stale and should be pruned."""
        suggestions = []
        now = datetime.utcnow()

        for entry in self.entries.values():
            # Get threshold for this category
            try:
                category = KnowledgeCategory(entry.category)
                threshold_days = self.STALENESS_THRESHOLDS.get(category, 90)
            except ValueError:
                threshold_days = 90

            # Check last access time
            if entry.last_accessed:
                last_access = datetime.fromisoformat(entry.last_accessed.rstrip("Z"))
                age_days = (now - last_access).days

                if age_days > threshold_days:
                    # Calculate confidence based on how much over threshold
                    over_threshold = age_days - threshold_days
                    confidence = min(1.0, 0.5 + (over_threshold / threshold_days) * 0.5)

                    suggestions.append(PruningSuggestion(
                        entry_id=entry.id,
                        source=entry.source,
                        reason=f"Not accessed in {age_days} days (threshold: {threshold_days})",
                        last_accessed=entry.last_accessed,
                        age_days=age_days,
                        confidence=confidence,
                    ))
                    entry.is_stale = True
            else:
                # No access record, check creation time
                created = datetime.fromisoformat(entry.created_at.rstrip("Z"))
                age_days = (now - created).days

                if age_days > threshold_days * 2:
                    suggestions.append(PruningSuggestion(
                        entry_id=entry.id,
                        source=entry.source,
                        reason=f"Created {age_days} days ago, never accessed",
                        last_accessed=None,
                        age_days=age_days,
                        confidence=0.9,
                    ))
                    entry.is_stale = True

        self._save_data()
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)

    def find_redundant_entries(self) -> list[ConsolidationSuggestion]:
        """Find entries that are redundant and could be consolidated."""
        suggestions = []
        entries_list = list(self.entries.values())

        # Compare all pairs (expensive, but knowledge stores are small)
        for i, entry1 in enumerate(entries_list):
            related = []

            for entry2 in entries_list[i + 1:]:
                similarity = self._compute_similarity(entry1.content, entry2.content)

                if similarity >= self.similarity_threshold:
                    related.append((entry2.id, similarity))
                    entry1.is_redundant = True
                    entry2.is_redundant = True

            if related:
                # Find all related entries
                all_related = [entry1.id] + [r[0] for r in related]
                avg_similarity = sum(r[1] for r in related) / len(related)

                # Estimate space savings (assuming dedup)
                total_size = sum(
                    len(self.entries[eid].content.encode())
                    for eid in all_related
                )
                merged_size = len(entry1.content.encode())  # Keep longest
                savings = total_size - merged_size

                suggestions.append(ConsolidationSuggestion(
                    entries=all_related,
                    similarity_score=avg_similarity,
                    reason=f"{len(all_related)} entries with {avg_similarity:.0%} similarity",
                    merged_content=entry1.content,  # Use first as base
                    space_savings_bytes=max(0, savings),
                ))

        self._save_data()
        return sorted(suggestions, key=lambda x: x.similarity_score, reverse=True)

    def prune_entries(
        self,
        entry_ids: list[str],
        archive: bool = True,
    ) -> dict:
        """
        Prune specified entries.

        Args:
            entry_ids: List of entry IDs to prune
            archive: Whether to archive before deleting

        Returns:
            Summary of pruning operation
        """
        pruned = []
        archived = []

        if archive:
            archive_file = self.data_dir / f"archive_{datetime.utcnow().strftime('%Y%m%d')}.json"
            archive_data = []

            if archive_file.exists():
                with open(archive_file) as f:
                    archive_data = json.load(f)

        for entry_id in entry_ids:
            if entry_id in self.entries:
                entry = self.entries[entry_id]

                if archive:
                    archive_data.append(asdict(entry))
                    archived.append(entry_id)

                del self.entries[entry_id]
                pruned.append(entry_id)

        if archive and archive_data:
            with open(archive_file, "w") as f:
                json.dump(archive_data, f, indent=2)

        self._save_data()

        return {
            "pruned": len(pruned),
            "archived": len(archived) if archive else 0,
            "entry_ids": pruned,
        }

    def consolidate_entries(
        self,
        entry_ids: list[str],
        keep_id: Optional[str] = None,
    ) -> Optional[KnowledgeEntry]:
        """
        Consolidate multiple entries into one.

        Args:
            entry_ids: Entry IDs to consolidate
            keep_id: ID of entry to keep (others merged into it)

        Returns:
            The consolidated entry, or None if failed
        """
        if len(entry_ids) < 2:
            return None

        entries = [self.entries[eid] for eid in entry_ids if eid in self.entries]

        if len(entries) < 2:
            return None

        # Determine which entry to keep
        if keep_id and keep_id in entry_ids:
            keeper = self.entries[keep_id]
        else:
            # Keep the one with most accesses
            keeper = max(entries, key=lambda e: e.access_count)

        # Merge content (combine unique parts)
        all_content = [e.content for e in entries]
        # For now, just keep the longest content
        merged_content = max(all_content, key=len)

        # Update keeper
        keeper.content = merged_content
        keeper.content_hash = self._compute_hash(merged_content)
        keeper.access_count = sum(e.access_count for e in entries)
        keeper.is_redundant = False
        keeper.related_entries = [e.id for e in entries if e.id != keeper.id]

        # Remove other entries
        for entry in entries:
            if entry.id != keeper.id:
                del self.entries[entry.id]

        self._save_data()
        return keeper

    def compute_metrics(self) -> KnowledgeMetrics:
        """Compute comprehensive knowledge metrics."""
        if not self.entries:
            return KnowledgeMetrics(
                total_entries=0,
                entries_by_source={},
                entries_by_category={},
                stale_entries=0,
                redundant_entries=0,
                avg_relevance_score=0,
                total_size_mb=0,
                recommendations=["No knowledge entries to analyze"],
            )

        # Count by source and category
        by_source = defaultdict(int)
        by_category = defaultdict(int)
        total_size = 0
        relevance_scores = []

        for entry in self.entries.values():
            by_source[entry.source] += 1
            by_category[entry.category] += 1
            total_size += len(entry.content.encode())
            relevance_scores.append(entry.relevance_score)

        # Find stale and redundant
        stale = self.find_stale_entries()
        redundant = self.find_redundant_entries()

        # Generate recommendations
        recommendations = []

        if len(stale) > 5:
            recommendations.append(
                f"Consider pruning {len(stale)} stale entries to improve retrieval quality"
            )

        if len(redundant) > 3:
            total_savings = sum(r.space_savings_bytes for r in redundant)
            recommendations.append(
                f"Consolidate {len(redundant)} redundant entry groups to save {total_savings / 1024:.1f}KB"
            )

        if by_category.get("temporary", 0) > 10:
            recommendations.append(
                f"Review {by_category['temporary']} temporary entries for cleanup"
            )

        if not recommendations:
            recommendations.append("Knowledge store is well-optimized")

        return KnowledgeMetrics(
            total_entries=len(self.entries),
            entries_by_source=dict(by_source),
            entries_by_category=dict(by_category),
            stale_entries=len(stale),
            redundant_entries=sum(len(r.entries) for r in redundant),
            avg_relevance_score=sum(relevance_scores) / len(relevance_scores),
            total_size_mb=total_size / (1024 * 1024),
            recommendations=recommendations,
        )

    def optimize(
        self,
        prune_stale: bool = True,
        consolidate_redundant: bool = True,
        min_confidence: float = 0.8,
    ) -> dict:
        """
        Run full optimization pass.

        Args:
            prune_stale: Whether to prune stale entries
            consolidate_redundant: Whether to consolidate redundant entries
            min_confidence: Minimum confidence for automatic pruning

        Returns:
            Summary of optimization actions taken
        """
        results = {
            "stale_pruned": 0,
            "redundant_consolidated": 0,
            "space_saved_bytes": 0,
            "actions": [],
        }

        if prune_stale:
            stale = self.find_stale_entries()
            to_prune = [s.entry_id for s in stale if s.confidence >= min_confidence]

            if to_prune:
                prune_result = self.prune_entries(to_prune)
                results["stale_pruned"] = prune_result["pruned"]
                results["actions"].append(
                    f"Pruned {prune_result['pruned']} stale entries"
                )

        if consolidate_redundant:
            redundant = self.find_redundant_entries()

            for suggestion in redundant:
                if suggestion.similarity_score >= 0.9:  # Only very similar
                    consolidated = self.consolidate_entries(suggestion.entries)
                    if consolidated:
                        results["redundant_consolidated"] += len(suggestion.entries) - 1
                        results["space_saved_bytes"] += suggestion.space_savings_bytes
                        results["actions"].append(
                            f"Consolidated {len(suggestion.entries)} entries"
                        )

        if not results["actions"]:
            results["actions"].append("No optimization actions needed")

        return results

    def export_health_report(self) -> str:
        """Export knowledge health report as markdown."""
        metrics = self.compute_metrics()
        stale = self.find_stale_entries()[:10]
        redundant = self.find_redundant_entries()[:5]

        lines = [
            "# Knowledge Store Health Report",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            "",
            "## Summary",
            "",
            f"- **Total Entries:** {metrics.total_entries}",
            f"- **Total Size:** {metrics.total_size_mb:.2f} MB",
            f"- **Average Relevance:** {metrics.avg_relevance_score:.2f}",
            f"- **Stale Entries:** {metrics.stale_entries}",
            f"- **Redundant Entries:** {metrics.redundant_entries}",
            "",
            "## By Source",
            "",
        ]

        for source, count in sorted(metrics.entries_by_source.items()):
            lines.append(f"- {source}: {count}")

        lines.extend(["", "## By Category", ""])

        for category, count in sorted(metrics.entries_by_category.items()):
            lines.append(f"- {category}: {count}")

        if stale:
            lines.extend(["", "## Stale Entries (Top 10)", ""])
            for s in stale:
                lines.append(
                    f"- `{s.entry_id}`: {s.reason} (confidence: {s.confidence:.0%})"
                )

        if redundant:
            lines.extend(["", "## Redundant Groups (Top 5)", ""])
            for r in redundant:
                lines.append(
                    f"- {len(r.entries)} entries, {r.similarity_score:.0%} similar, "
                    f"save {r.space_savings_bytes} bytes"
                )

        lines.extend(["", "## Recommendations", ""])

        for rec in metrics.recommendations:
            lines.append(f"- {rec}")

        lines.extend([
            "",
            "---",
            "*Generated by Hydra Knowledge Optimizer*",
        ])

        return "\n".join(lines)


# FastAPI integration
def create_knowledge_router():
    """Create FastAPI router for knowledge optimization endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/knowledge", tags=["knowledge"])
    optimizer = KnowledgeOptimizer()

    class EntryInput(BaseModel):
        content: str
        source: str
        category: Optional[str] = None

    class PruneInput(BaseModel):
        entry_ids: list[str]
        archive: bool = True

    class ConsolidateInput(BaseModel):
        entry_ids: list[str]
        keep_id: Optional[str] = None

    @router.post("/entry")
    async def add_entry(entry: EntryInput):
        """Add a knowledge entry for tracking."""
        try:
            source = KnowledgeSource(entry.source)
        except ValueError:
            source = KnowledgeSource.SESSION_MEMORY

        category = None
        if entry.category:
            try:
                category = KnowledgeCategory(entry.category)
            except ValueError:
                pass

        result = optimizer.add_entry(
            content=entry.content,
            source=source,
            category=category,
        )
        return {"entry_id": result.id, "category": result.category}

    @router.get("/metrics")
    async def get_metrics():
        """Get knowledge store metrics."""
        metrics = optimizer.compute_metrics()
        return asdict(metrics)

    @router.get("/stale")
    async def find_stale():
        """Find stale entries."""
        stale = optimizer.find_stale_entries()
        return {"stale": [asdict(s) for s in stale]}

    @router.get("/redundant")
    async def find_redundant():
        """Find redundant entries."""
        redundant = optimizer.find_redundant_entries()
        return {"redundant": [asdict(r) for r in redundant]}

    @router.post("/prune")
    async def prune_entries(prune: PruneInput):
        """Prune specified entries."""
        result = optimizer.prune_entries(
            entry_ids=prune.entry_ids,
            archive=prune.archive,
        )
        return result

    @router.post("/consolidate")
    async def consolidate_entries(consolidate: ConsolidateInput):
        """Consolidate redundant entries."""
        result = optimizer.consolidate_entries(
            entry_ids=consolidate.entry_ids,
            keep_id=consolidate.keep_id,
        )
        if result:
            return {"status": "consolidated", "entry": asdict(result)}
        raise HTTPException(status_code=400, detail="Consolidation failed")

    @router.post("/optimize")
    async def run_optimization(
        prune_stale: bool = True,
        consolidate_redundant: bool = True,
        min_confidence: float = 0.8,
    ):
        """Run full optimization pass."""
        result = optimizer.optimize(
            prune_stale=prune_stale,
            consolidate_redundant=consolidate_redundant,
            min_confidence=min_confidence,
        )
        return result

    @router.get("/report")
    async def get_health_report():
        """Get knowledge health report."""
        return {"markdown": optimizer.export_health_report()}

    @router.get("/health")
    async def knowledge_health():
        """Quick health check."""
        metrics = optimizer.compute_metrics()
        health_score = 100

        if metrics.stale_entries > 10:
            health_score -= 20
        if metrics.redundant_entries > 20:
            health_score -= 15
        if metrics.avg_relevance_score < 0.5:
            health_score -= 15

        return {
            "status": "healthy" if health_score >= 70 else "needs_attention",
            "health_score": max(0, health_score),
            "total_entries": metrics.total_entries,
            "stale": metrics.stale_entries,
            "redundant": metrics.redundant_entries,
        }

    return router
