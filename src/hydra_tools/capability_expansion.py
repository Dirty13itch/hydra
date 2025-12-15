"""
Hydra Capability Expansion System

Tracks new requirements encountered during sessions, documents them,
and prioritizes implementation in the roadmap.

Features:
- Captures capability gaps when tasks fail or are unsupported
- Tracks feature requests and enhancements
- Prioritizes based on frequency and impact
- Generates roadmap updates
- Integrates with Letta for persistent memory

Usage:
    from hydra_tools.capability_expansion import CapabilityTracker

    tracker = CapabilityTracker()
    tracker.record_gap(
        description="Need to support PDF parsing",
        context="User asked to analyze a PDF document",
        category="document_processing"
    )

    # Get prioritized backlog
    backlog = tracker.get_prioritized_backlog()
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CapabilityCategory(Enum):
    """Categories of capabilities."""
    INFERENCE = "inference"
    DOCUMENT_PROCESSING = "document_processing"
    DATA_ANALYSIS = "data_analysis"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    UI_UX = "ui_ux"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MONITORING = "monitoring"
    OTHER = "other"


class Priority(Enum):
    """Priority levels for capability gaps."""
    CRITICAL = 1  # Blocks core functionality
    HIGH = 2      # Significantly impacts user experience
    MEDIUM = 3    # Would be nice to have
    LOW = 4       # Minor enhancement


class Status(Enum):
    """Status of capability gaps."""
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    WONT_FIX = "wont_fix"


@dataclass
class CapabilityGap:
    """A single capability gap or feature request."""
    id: str
    description: str
    category: CapabilityCategory
    context: str  # When/how was this gap discovered
    priority: Priority = Priority.MEDIUM
    status: Status = Status.NEW
    occurrences: int = 1
    first_seen: str = ""
    last_seen: str = ""
    related_tasks: list[str] = field(default_factory=list)
    proposed_solution: str = ""
    implementation_notes: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.utcnow().isoformat() + "Z"
        if not self.last_seen:
            self.last_seen = self.first_seen


@dataclass
class CapabilityMetrics:
    """Metrics about capability tracking."""
    total_gaps: int = 0
    gaps_by_category: dict[str, int] = field(default_factory=dict)
    gaps_by_priority: dict[str, int] = field(default_factory=dict)
    gaps_by_status: dict[str, int] = field(default_factory=dict)
    most_requested: list[str] = field(default_factory=list)
    recently_added: list[str] = field(default_factory=list)


class CapabilityTracker:
    """
    Tracks capability gaps and feature requests.

    Stores data locally and can sync with Letta for persistence.
    """

    def __init__(
        self,
        storage_path: str | Path = "/mnt/user/appdata/hydra-stack/data/capabilities.json",
        auto_save: bool = True,
    ):
        """
        Initialize the capability tracker.

        Args:
            storage_path: Path to JSON storage file
            auto_save: Whether to auto-save after changes
        """
        self.storage_path = Path(storage_path)
        self.auto_save = auto_save
        self._gaps: dict[str, CapabilityGap] = {}
        self._load()

    def _generate_id(self, description: str) -> str:
        """Generate a unique ID from description."""
        hash_input = description.lower().strip()
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _load(self) -> None:
        """Load gaps from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for gap_data in data.get("gaps", []):
                    gap = CapabilityGap(
                        id=gap_data["id"],
                        description=gap_data["description"],
                        category=CapabilityCategory(gap_data["category"]),
                        context=gap_data["context"],
                        priority=Priority(gap_data.get("priority", 3)),
                        status=Status(gap_data.get("status", "new")),
                        occurrences=gap_data.get("occurrences", 1),
                        first_seen=gap_data.get("first_seen", ""),
                        last_seen=gap_data.get("last_seen", ""),
                        related_tasks=gap_data.get("related_tasks", []),
                        proposed_solution=gap_data.get("proposed_solution", ""),
                        implementation_notes=gap_data.get("implementation_notes", ""),
                        tags=gap_data.get("tags", []),
                    )
                    self._gaps[gap.id] = gap
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load capabilities: {e}")

    def _save(self) -> None:
        """Save gaps to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "gaps": [
                {
                    "id": gap.id,
                    "description": gap.description,
                    "category": gap.category.value,
                    "context": gap.context,
                    "priority": gap.priority.value,
                    "status": gap.status.value,
                    "occurrences": gap.occurrences,
                    "first_seen": gap.first_seen,
                    "last_seen": gap.last_seen,
                    "related_tasks": gap.related_tasks,
                    "proposed_solution": gap.proposed_solution,
                    "implementation_notes": gap.implementation_notes,
                    "tags": gap.tags,
                }
                for gap in self._gaps.values()
            ],
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    def record_gap(
        self,
        description: str,
        context: str,
        category: CapabilityCategory | str = CapabilityCategory.OTHER,
        priority: Priority | int = Priority.MEDIUM,
        related_task: str | None = None,
        tags: list[str] | None = None,
    ) -> CapabilityGap:
        """
        Record a capability gap.

        Args:
            description: What capability is missing
            context: When/how this was discovered
            category: Category of the capability
            priority: Priority level
            related_task: Optional task ID that triggered this
            tags: Optional tags for categorization

        Returns:
            The created or updated CapabilityGap
        """
        # Normalize inputs
        if isinstance(category, str):
            category = CapabilityCategory(category)
        if isinstance(priority, int):
            priority = Priority(priority)

        gap_id = self._generate_id(description)
        now = datetime.utcnow().isoformat() + "Z"

        if gap_id in self._gaps:
            # Update existing gap
            gap = self._gaps[gap_id]
            gap.occurrences += 1
            gap.last_seen = now
            if related_task and related_task not in gap.related_tasks:
                gap.related_tasks.append(related_task)
            if tags:
                gap.tags = list(set(gap.tags + tags))
            # Escalate priority if seen frequently
            if gap.occurrences >= 5 and gap.priority.value > Priority.HIGH.value:
                gap.priority = Priority.HIGH
        else:
            # Create new gap
            gap = CapabilityGap(
                id=gap_id,
                description=description,
                category=category,
                context=context,
                priority=priority,
                first_seen=now,
                last_seen=now,
                related_tasks=[related_task] if related_task else [],
                tags=tags or [],
            )
            self._gaps[gap_id] = gap

        if self.auto_save:
            self._save()

        return gap

    def record_feature_request(
        self,
        description: str,
        context: str,
        category: CapabilityCategory | str = CapabilityCategory.OTHER,
        proposed_solution: str = "",
    ) -> CapabilityGap:
        """
        Record a feature request (convenience method).

        Args:
            description: What feature is requested
            context: Why/when this was requested
            category: Category of the feature
            proposed_solution: Optional proposed implementation

        Returns:
            The created CapabilityGap
        """
        gap = self.record_gap(
            description=description,
            context=context,
            category=category,
            priority=Priority.MEDIUM,
            tags=["feature_request"],
        )
        if proposed_solution:
            gap.proposed_solution = proposed_solution
            if self.auto_save:
                self._save()
        return gap

    def update_gap(
        self,
        gap_id: str,
        status: Status | None = None,
        priority: Priority | None = None,
        proposed_solution: str | None = None,
        implementation_notes: str | None = None,
    ) -> CapabilityGap | None:
        """
        Update an existing capability gap.

        Args:
            gap_id: ID of the gap to update
            status: New status
            priority: New priority
            proposed_solution: Proposed solution
            implementation_notes: Implementation notes

        Returns:
            Updated gap or None if not found
        """
        if gap_id not in self._gaps:
            return None

        gap = self._gaps[gap_id]
        if status:
            gap.status = status
        if priority:
            gap.priority = priority
        if proposed_solution:
            gap.proposed_solution = proposed_solution
        if implementation_notes:
            gap.implementation_notes = implementation_notes

        if self.auto_save:
            self._save()

        return gap

    def get_gap(self, gap_id: str) -> CapabilityGap | None:
        """Get a specific capability gap."""
        return self._gaps.get(gap_id)

    def get_all_gaps(self) -> list[CapabilityGap]:
        """Get all capability gaps."""
        return list(self._gaps.values())

    def get_gaps_by_category(self, category: CapabilityCategory) -> list[CapabilityGap]:
        """Get gaps filtered by category."""
        return [g for g in self._gaps.values() if g.category == category]

    def get_gaps_by_status(self, status: Status) -> list[CapabilityGap]:
        """Get gaps filtered by status."""
        return [g for g in self._gaps.values() if g.status == status]

    def get_prioritized_backlog(
        self,
        include_implemented: bool = False,
    ) -> list[CapabilityGap]:
        """
        Get prioritized list of capability gaps.

        Sorted by: priority (asc), occurrences (desc), last_seen (desc)

        Args:
            include_implemented: Whether to include implemented gaps

        Returns:
            Sorted list of gaps
        """
        gaps = list(self._gaps.values())

        if not include_implemented:
            gaps = [g for g in gaps if g.status != Status.IMPLEMENTED]

        # Sort by priority, then occurrences, then recency
        gaps.sort(
            key=lambda g: (
                g.priority.value,
                -g.occurrences,
                g.last_seen,
            )
        )

        return gaps

    def get_metrics(self) -> CapabilityMetrics:
        """Get capability tracking metrics."""
        gaps = list(self._gaps.values())

        # Count by category
        by_category: dict[str, int] = {}
        for gap in gaps:
            cat = gap.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by priority
        by_priority: dict[str, int] = {}
        for gap in gaps:
            pri = gap.priority.name
            by_priority[pri] = by_priority.get(pri, 0) + 1

        # Count by status
        by_status: dict[str, int] = {}
        for gap in gaps:
            stat = gap.status.value
            by_status[stat] = by_status.get(stat, 0) + 1

        # Most requested (by occurrences)
        sorted_by_occurrences = sorted(gaps, key=lambda g: -g.occurrences)
        most_requested = [g.description[:50] for g in sorted_by_occurrences[:5]]

        # Recently added
        sorted_by_date = sorted(gaps, key=lambda g: g.first_seen, reverse=True)
        recently_added = [g.description[:50] for g in sorted_by_date[:5]]

        return CapabilityMetrics(
            total_gaps=len(gaps),
            gaps_by_category=by_category,
            gaps_by_priority=by_priority,
            gaps_by_status=by_status,
            most_requested=most_requested,
            recently_added=recently_added,
        )

    def generate_roadmap_entry(self, gap: CapabilityGap) -> str:
        """
        Generate a ROADMAP.md entry for a capability gap.

        Args:
            gap: The capability gap

        Returns:
            Markdown-formatted roadmap entry
        """
        priority_emoji = {
            Priority.CRITICAL: "🔴",
            Priority.HIGH: "🟠",
            Priority.MEDIUM: "🟡",
            Priority.LOW: "🟢",
        }

        entry = f"""### {priority_emoji.get(gap.priority, '⚪')} {gap.description}

**Category:** {gap.category.value}
**Priority:** {gap.priority.name}
**Occurrences:** {gap.occurrences}
**First seen:** {gap.first_seen[:10]}

**Context:** {gap.context}
"""
        if gap.proposed_solution:
            entry += f"\n**Proposed solution:** {gap.proposed_solution}\n"

        if gap.tags:
            entry += f"\n**Tags:** {', '.join(gap.tags)}\n"

        return entry

    def export_to_markdown(self, output_path: str | Path | None = None) -> str:
        """
        Export all gaps to markdown format.

        Args:
            output_path: Optional path to write the file

        Returns:
            Markdown content
        """
        backlog = self.get_prioritized_backlog()
        metrics = self.get_metrics()

        md = f"""# Hydra Capability Backlog

**Total gaps:** {metrics.total_gaps}
**Last updated:** {datetime.utcnow().isoformat()[:10]}

## Summary

| Category | Count |
|----------|-------|
"""
        for cat, count in sorted(metrics.gaps_by_category.items()):
            md += f"| {cat} | {count} |\n"

        md += "\n## Priority Distribution\n\n"
        for pri, count in sorted(metrics.gaps_by_priority.items()):
            md += f"- **{pri}:** {count}\n"

        md += "\n---\n\n## Backlog\n\n"

        # Group by priority
        current_priority = None
        for gap in backlog:
            if gap.priority != current_priority:
                current_priority = gap.priority
                md += f"\n### {current_priority.name} Priority\n\n"

            md += self.generate_roadmap_entry(gap)
            md += "\n---\n"

        if output_path:
            Path(output_path).write_text(md)

        return md


# FastAPI endpoints for integration
def create_capability_api():
    """Create FastAPI router for capability tracking."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/capabilities", tags=["capabilities"])
    tracker = CapabilityTracker()

    class GapRequest(BaseModel):
        description: str
        context: str
        category: str = "other"
        priority: int = 3
        tags: list[str] | None = None

    class UpdateRequest(BaseModel):
        status: str | None = None
        priority: int | None = None
        proposed_solution: str | None = None

    @router.post("/gap")
    async def record_gap(req: GapRequest):
        """Record a capability gap."""
        gap = tracker.record_gap(
            description=req.description,
            context=req.context,
            category=req.category,
            priority=req.priority,
            tags=req.tags,
        )
        return {"id": gap.id, "occurrences": gap.occurrences}

    @router.get("/backlog")
    async def get_backlog():
        """Get prioritized backlog."""
        gaps = tracker.get_prioritized_backlog()
        return {
            "count": len(gaps),
            "gaps": [
                {
                    "id": g.id,
                    "description": g.description,
                    "category": g.category.value,
                    "priority": g.priority.name,
                    "occurrences": g.occurrences,
                    "status": g.status.value,
                }
                for g in gaps
            ],
        }

    @router.get("/metrics")
    async def get_metrics():
        """Get capability metrics."""
        metrics = tracker.get_metrics()
        return {
            "total": metrics.total_gaps,
            "by_category": metrics.gaps_by_category,
            "by_priority": metrics.gaps_by_priority,
            "by_status": metrics.gaps_by_status,
            "most_requested": metrics.most_requested,
        }

    @router.patch("/gap/{gap_id}")
    async def update_gap(gap_id: str, req: UpdateRequest):
        """Update a capability gap."""
        status = Status(req.status) if req.status else None
        priority = Priority(req.priority) if req.priority else None

        gap = tracker.update_gap(
            gap_id=gap_id,
            status=status,
            priority=priority,
            proposed_solution=req.proposed_solution,
        )
        if not gap:
            raise HTTPException(status_code=404, detail="Gap not found")
        return {"id": gap.id, "status": gap.status.value}

    @router.get("/export")
    async def export_markdown():
        """Export backlog to markdown."""
        md = tracker.export_to_markdown()
        return {"markdown": md}

    return router


if __name__ == "__main__":
    # Demo usage
    tracker = CapabilityTracker(storage_path="./test_capabilities.json")

    # Record some gaps
    tracker.record_gap(
        description="Support for PDF document parsing",
        context="User tried to analyze a PDF file",
        category=CapabilityCategory.DOCUMENT_PROCESSING,
        priority=Priority.HIGH,
    )

    tracker.record_gap(
        description="Real-time streaming responses in UI",
        context="User wanted to see tokens appear as generated",
        category=CapabilityCategory.UI_UX,
        priority=Priority.MEDIUM,
        tags=["streaming", "ux"],
    )

    tracker.record_gap(
        description="Multi-GPU load balancing",
        context="5090 and 4090 could share inference load",
        category=CapabilityCategory.PERFORMANCE,
        priority=Priority.MEDIUM,
    )

    # Get metrics
    metrics = tracker.get_metrics()
    print(f"\nTotal gaps: {metrics.total_gaps}")
    print(f"By category: {metrics.gaps_by_category}")

    # Get prioritized backlog
    print("\nPrioritized Backlog:")
    for gap in tracker.get_prioritized_backlog():
        print(f"  [{gap.priority.name}] {gap.description}")

    # Export to markdown
    md = tracker.export_to_markdown()
    print("\n" + md[:500] + "...")
