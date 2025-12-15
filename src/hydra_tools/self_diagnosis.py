"""
Self-Diagnosis System for Hydra Cluster.

Enables agents to analyze their own failures, identify patterns,
and suggest improvements for autonomous self-improvement.
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


class FailureCategory(Enum):
    """Categories of failures for diagnosis."""
    INFERENCE = "inference"           # Model/LLM failures
    NETWORK = "network"               # Connection, timeout issues
    RESOURCE = "resource"             # OOM, disk full, CPU overload
    CONFIGURATION = "configuration"   # Config errors, missing settings
    DEPENDENCY = "dependency"         # Service dependencies unavailable
    PERMISSION = "permission"         # Auth, access control failures
    DATA = "data"                     # Invalid input, parsing errors
    TIMEOUT = "timeout"               # Operation timeouts
    UNKNOWN = "unknown"               # Unclassified failures


class Severity(Enum):
    """Failure severity levels."""
    CRITICAL = "critical"    # System-wide impact
    HIGH = "high"            # Service-level impact
    MEDIUM = "medium"        # Degraded performance
    LOW = "low"              # Minor issues


@dataclass
class FailurePattern:
    """Represents a recurring failure pattern."""
    id: str
    category: str
    pattern_signature: str
    description: str
    occurrences: int = 0
    first_seen: str = ""
    last_seen: str = ""
    affected_services: list = field(default_factory=list)
    root_causes: list = field(default_factory=list)
    remediation_steps: list = field(default_factory=list)
    auto_remediation: Optional[str] = None  # Command/action to auto-fix
    resolved_count: int = 0
    mean_time_to_resolve: float = 0.0  # Minutes


@dataclass
class FailureEvent:
    """Individual failure occurrence."""
    id: str
    timestamp: str
    category: str
    severity: str
    service: str
    error_message: str
    stack_trace: Optional[str] = None
    context: dict = field(default_factory=dict)
    pattern_id: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic analysis."""
    generated_at: str
    time_range_hours: int
    total_failures: int
    failures_by_category: dict
    failures_by_severity: dict
    top_patterns: list
    recommendations: list
    health_score: float  # 0-100
    trend: str  # "improving", "stable", "degrading"


class SelfDiagnosisEngine:
    """
    Self-diagnosis engine for failure analysis and improvement suggestions.

    Tracks failures, identifies patterns, and provides actionable recommendations.
    """

    # Pattern detection rules
    PATTERN_RULES = {
        FailureCategory.INFERENCE: [
            (r"CUDA out of memory", "GPU memory exhaustion"),
            (r"model.*not found", "Missing model files"),
            (r"timeout.*inference", "Inference timeout"),
            (r"connection refused.*5000", "TabbyAPI unavailable"),
            (r"connection refused.*11434", "Ollama unavailable"),
            (r"rate limit", "API rate limiting"),
        ],
        FailureCategory.NETWORK: [
            (r"connection refused", "Service connection failure"),
            (r"timeout|timed out", "Network timeout"),
            (r"DNS.*failed|resolve", "DNS resolution failure"),
            (r"connection reset", "Connection reset by peer"),
            (r"no route to host", "Network routing failure"),
        ],
        FailureCategory.RESOURCE: [
            (r"out of memory|OOM|oom-killer", "Memory exhaustion"),
            (r"no space left on device", "Disk space exhaustion"),
            (r"too many open files", "File descriptor exhaustion"),
            (r"resource temporarily unavailable", "Resource contention"),
        ],
        FailureCategory.CONFIGURATION: [
            (r"invalid.*config|configuration", "Invalid configuration"),
            (r"missing.*key|required", "Missing required configuration"),
            (r"yaml.*error|parse", "YAML parsing error"),
            (r"environment variable.*not set", "Missing environment variable"),
        ],
        FailureCategory.DEPENDENCY: [
            (r"service.*unavailable", "Dependent service down"),
            (r"database.*connection", "Database connection failure"),
            (r"redis.*connection", "Redis connection failure"),
            (r"container.*not running", "Container dependency failure"),
        ],
        FailureCategory.PERMISSION: [
            (r"permission denied", "File permission error"),
            (r"unauthorized|401", "Authentication failure"),
            (r"forbidden|403", "Authorization failure"),
            (r"access denied", "Access control failure"),
        ],
        FailureCategory.DATA: [
            (r"json.*decode|invalid json", "JSON parsing error"),
            (r"validation.*error|invalid", "Data validation failure"),
            (r"null|none.*not allowed", "Null value error"),
            (r"type.*error|expected", "Type mismatch"),
        ],
        FailureCategory.TIMEOUT: [
            (r"deadline exceeded", "Deadline timeout"),
            (r"operation timed out", "Operation timeout"),
            (r"read timeout", "Read timeout"),
            (r"connect timeout", "Connection timeout"),
        ],
    }

    # Remediation suggestions by category
    REMEDIATION_SUGGESTIONS = {
        FailureCategory.INFERENCE: {
            "GPU memory exhaustion": [
                "Reduce batch size or context length",
                "Unload unused models from GPU",
                "Consider smaller quantization (6bpw → 4bpw)",
                "Implement model rotation for large workloads",
            ],
            "Missing model files": [
                "Verify model path in TabbyAPI config",
                "Check NFS mount: df -h /mnt/models",
                "Re-download model from HuggingFace",
            ],
            "Inference timeout": [
                "Check GPU utilization: nvidia-smi",
                "Reduce max_tokens for long responses",
                "Consider routing to faster model",
            ],
        },
        FailureCategory.NETWORK: {
            "Service connection failure": [
                "Check service status: docker ps | grep <service>",
                "Verify port accessibility: nc -zv <ip> <port>",
                "Check firewall rules on target node",
            ],
            "DNS resolution failure": [
                "Verify AdGuard status at 192.168.1.244:3053",
                "Check /etc/resolv.conf on affected node",
                "Use IP address as fallback",
            ],
        },
        FailureCategory.RESOURCE: {
            "Memory exhaustion": [
                "Check memory usage: free -h",
                "Identify memory hogs: docker stats",
                "Restart memory-leaking containers",
                "Increase swap or add memory limits",
            ],
            "Disk space exhaustion": [
                "Check disk usage: df -h",
                "Clean Docker: docker system prune -af",
                "Clear old logs: journalctl --vacuum-size=100M",
                "Review /mnt/user/temp_migration for stale data",
            ],
        },
        FailureCategory.DEPENDENCY: {
            "Database connection failure": [
                "Check PostgreSQL: docker exec hydra-postgres pg_isready",
                "Verify connection string in service config",
                "Check database resource limits",
            ],
            "Container dependency failure": [
                "Restart dependent container: docker restart <name>",
                "Check docker-compose depends_on configuration",
                "Verify healthcheck status",
            ],
        },
    }

    def __init__(
        self,
        data_dir: str = "/mnt/user/appdata/hydra-stack/data/diagnosis",
        max_events: int = 10000,
        pattern_threshold: int = 3,  # Min occurrences to create pattern
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.events_file = self.data_dir / "failure_events.json"
        self.patterns_file = self.data_dir / "failure_patterns.json"
        self.reports_file = self.data_dir / "diagnostic_reports.json"

        self.max_events = max_events
        self.pattern_threshold = pattern_threshold

        self.events: list[FailureEvent] = []
        self.patterns: dict[str, FailurePattern] = {}

        self._load_data()

    def _load_data(self):
        """Load persisted events and patterns."""
        if self.events_file.exists():
            try:
                with open(self.events_file) as f:
                    data = json.load(f)
                    self.events = [FailureEvent(**e) for e in data]
            except (json.JSONDecodeError, TypeError):
                self.events = []

        if self.patterns_file.exists():
            try:
                with open(self.patterns_file) as f:
                    data = json.load(f)
                    self.patterns = {k: FailurePattern(**v) for k, v in data.items()}
            except (json.JSONDecodeError, TypeError):
                self.patterns = {}

    def _save_data(self):
        """Persist events and patterns."""
        # Trim events if exceeding max
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        with open(self.events_file, "w") as f:
            json.dump([asdict(e) for e in self.events], f, indent=2)

        with open(self.patterns_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self.patterns.items()}, f, indent=2)

    def _generate_pattern_signature(self, error_message: str) -> str:
        """Generate a normalized signature for pattern matching."""
        # Remove specific values like IPs, ports, IDs
        normalized = re.sub(r'\d+\.\d+\.\d+\.\d+', '<IP>', error_message)
        normalized = re.sub(r':\d+', ':<PORT>', normalized)
        normalized = re.sub(r'[a-f0-9]{8,}', '<ID>', normalized.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Create hash for signature
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _classify_failure(self, error_message: str) -> tuple[FailureCategory, str]:
        """Classify failure based on error message patterns."""
        error_lower = error_message.lower()

        for category, rules in self.PATTERN_RULES.items():
            for pattern, description in rules:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return category, description

        return FailureCategory.UNKNOWN, "Unclassified failure"

    def _determine_severity(
        self,
        category: FailureCategory,
        service: str,
        error_message: str,
    ) -> Severity:
        """Determine severity based on failure characteristics."""
        # Critical services get higher severity
        critical_services = ["hydra-postgres", "hydra-redis", "tabbyapi", "litellm"]

        if any(svc in service.lower() for svc in critical_services):
            if category in [FailureCategory.RESOURCE, FailureCategory.DEPENDENCY]:
                return Severity.CRITICAL
            return Severity.HIGH

        # Resource exhaustion is always high severity
        if category == FailureCategory.RESOURCE:
            return Severity.HIGH

        # Repeated failures (check patterns)
        pattern_sig = self._generate_pattern_signature(error_message)
        if pattern_sig in self.patterns:
            if self.patterns[pattern_sig].occurrences > 10:
                return Severity.HIGH

        # Default severity mapping
        severity_map = {
            FailureCategory.INFERENCE: Severity.MEDIUM,
            FailureCategory.NETWORK: Severity.MEDIUM,
            FailureCategory.CONFIGURATION: Severity.LOW,
            FailureCategory.PERMISSION: Severity.MEDIUM,
            FailureCategory.DATA: Severity.LOW,
            FailureCategory.TIMEOUT: Severity.MEDIUM,
            FailureCategory.UNKNOWN: Severity.LOW,
        }

        return severity_map.get(category, Severity.LOW)

    def record_failure(
        self,
        service: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> FailureEvent:
        """
        Record a failure event and update patterns.

        Args:
            service: Name of the affected service
            error_message: Error message or description
            stack_trace: Optional stack trace
            context: Optional additional context

        Returns:
            The created FailureEvent
        """
        now = datetime.utcnow()

        # Classify the failure
        category, description = self._classify_failure(error_message)
        severity = self._determine_severity(category, service, error_message)

        # Generate pattern signature
        pattern_sig = self._generate_pattern_signature(error_message)

        # Create event
        event = FailureEvent(
            id=f"fail-{now.strftime('%Y%m%d%H%M%S')}-{len(self.events) % 10000:04d}",
            timestamp=now.isoformat() + "Z",
            category=category.value,
            severity=severity.value,
            service=service,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
            pattern_id=pattern_sig,
        )

        self.events.append(event)

        # Update or create pattern
        if pattern_sig in self.patterns:
            pattern = self.patterns[pattern_sig]
            pattern.occurrences += 1
            pattern.last_seen = event.timestamp
            if service not in pattern.affected_services:
                pattern.affected_services.append(service)
        else:
            # Check if we should create a new pattern
            similar_events = [
                e for e in self.events[-100:]
                if e.pattern_id == pattern_sig
            ]

            if len(similar_events) >= self.pattern_threshold:
                # Get remediation suggestions
                remediation = []
                if category in self.REMEDIATION_SUGGESTIONS:
                    if description in self.REMEDIATION_SUGGESTIONS[category]:
                        remediation = self.REMEDIATION_SUGGESTIONS[category][description]

                self.patterns[pattern_sig] = FailurePattern(
                    id=pattern_sig,
                    category=category.value,
                    pattern_signature=pattern_sig,
                    description=description,
                    occurrences=len(similar_events),
                    first_seen=similar_events[0].timestamp,
                    last_seen=event.timestamp,
                    affected_services=[service],
                    root_causes=[description],
                    remediation_steps=remediation,
                )

        self._save_data()
        return event

    def resolve_failure(
        self,
        event_id: str,
        resolution_notes: Optional[str] = None,
    ) -> bool:
        """Mark a failure as resolved."""
        for event in self.events:
            if event.id == event_id:
                event.resolved = True
                event.resolution_time = datetime.utcnow().isoformat() + "Z"
                event.resolution_notes = resolution_notes

                # Update pattern resolution stats
                if event.pattern_id and event.pattern_id in self.patterns:
                    pattern = self.patterns[event.pattern_id]
                    pattern.resolved_count += 1

                    # Calculate mean time to resolve
                    event_time = datetime.fromisoformat(event.timestamp.rstrip("Z"))
                    resolve_time = datetime.fromisoformat(event.resolution_time.rstrip("Z"))
                    resolution_minutes = (resolve_time - event_time).total_seconds() / 60

                    # Rolling average
                    if pattern.mean_time_to_resolve == 0:
                        pattern.mean_time_to_resolve = resolution_minutes
                    else:
                        pattern.mean_time_to_resolve = (
                            pattern.mean_time_to_resolve * 0.8 + resolution_minutes * 0.2
                        )

                self._save_data()
                return True

        return False

    def analyze(
        self,
        hours: int = 24,
        include_resolved: bool = False,
    ) -> DiagnosticReport:
        """
        Analyze failures and generate diagnostic report.

        Args:
            hours: Time range to analyze
            include_resolved: Whether to include resolved failures

        Returns:
            DiagnosticReport with analysis
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)

        # Filter events
        relevant_events = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp.rstrip("Z")) >= cutoff
            and (include_resolved or not e.resolved)
        ]

        # Count by category and severity
        by_category = defaultdict(int)
        by_severity = defaultdict(int)

        for event in relevant_events:
            by_category[event.category] += 1
            by_severity[event.severity] += 1

        # Get top patterns
        pattern_counts = defaultdict(int)
        for event in relevant_events:
            if event.pattern_id:
                pattern_counts[event.pattern_id] += 1

        top_patterns = []
        for pattern_id, count in sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:
            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                top_patterns.append({
                    "id": pattern_id,
                    "description": pattern.description,
                    "count": count,
                    "category": pattern.category,
                    "remediation": pattern.remediation_steps[:2],
                })

        # Generate recommendations
        recommendations = self._generate_recommendations(
            relevant_events,
            dict(by_category),
            dict(by_severity),
        )

        # Calculate health score
        health_score = self._calculate_health_score(
            len(relevant_events),
            dict(by_severity),
            hours,
        )

        # Determine trend
        trend = self._determine_trend(hours)

        return DiagnosticReport(
            generated_at=now.isoformat() + "Z",
            time_range_hours=hours,
            total_failures=len(relevant_events),
            failures_by_category=dict(by_category),
            failures_by_severity=dict(by_severity),
            top_patterns=top_patterns,
            recommendations=recommendations,
            health_score=health_score,
            trend=trend,
        )

    def _generate_recommendations(
        self,
        events: list[FailureEvent],
        by_category: dict,
        by_severity: dict,
    ) -> list[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # High severity issues
        if by_severity.get("critical", 0) > 0:
            recommendations.append(
                f"URGENT: {by_severity['critical']} critical failures require immediate attention"
            )

        # Most common category
        if by_category:
            top_category = max(by_category.items(), key=lambda x: x[1])
            if top_category[1] >= 3:
                recommendations.append(
                    f"Focus on {top_category[0]} issues - {top_category[1]} occurrences"
                )

        # Resource recommendations
        if by_category.get("resource", 0) >= 2:
            recommendations.append(
                "Resource constraints detected - consider cleanup or scaling"
            )

        # Network recommendations
        if by_category.get("network", 0) >= 3:
            recommendations.append(
                "Network issues frequent - check connectivity and DNS"
            )

        # Inference recommendations
        if by_category.get("inference", 0) >= 2:
            recommendations.append(
                "Inference issues detected - verify GPU health and model loading"
            )

        # Pattern-based recommendations
        for event in events[:10]:
            if event.pattern_id and event.pattern_id in self.patterns:
                pattern = self.patterns[event.pattern_id]
                if pattern.remediation_steps and pattern.occurrences > 5:
                    rec = f"Recurring: {pattern.description} - Try: {pattern.remediation_steps[0]}"
                    if rec not in recommendations:
                        recommendations.append(rec)

        if not recommendations:
            recommendations.append("No critical issues detected - cluster operating normally")

        return recommendations[:6]  # Limit to 6 recommendations

    def _calculate_health_score(
        self,
        failure_count: int,
        by_severity: dict,
        hours: int,
    ) -> float:
        """Calculate health score from 0-100."""
        # Start at 100
        score = 100.0

        # Deduct for failures (weighted by severity)
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 0.5,
        }

        for severity, count in by_severity.items():
            weight = severity_weights.get(severity, 1)
            score -= count * weight

        # Adjust for time window (more tolerance for longer periods)
        if hours > 24:
            score *= 1 + (hours - 24) / 100

        return max(0, min(100, score))

    def _determine_trend(self, hours: int) -> str:
        """Determine failure trend over time."""
        now = datetime.utcnow()

        # Compare current period to previous period
        current_cutoff = now - timedelta(hours=hours)
        previous_cutoff = current_cutoff - timedelta(hours=hours)

        current_count = sum(
            1 for e in self.events
            if datetime.fromisoformat(e.timestamp.rstrip("Z")) >= current_cutoff
        )

        previous_count = sum(
            1 for e in self.events
            if previous_cutoff <= datetime.fromisoformat(e.timestamp.rstrip("Z")) < current_cutoff
        )

        if previous_count == 0:
            return "stable" if current_count < 5 else "degrading"

        ratio = current_count / previous_count

        if ratio < 0.7:
            return "improving"
        elif ratio > 1.3:
            return "degrading"
        else:
            return "stable"

    def get_pattern_details(self, pattern_id: str) -> Optional[FailurePattern]:
        """Get detailed information about a specific pattern."""
        return self.patterns.get(pattern_id)

    def suggest_auto_remediation(self, event: FailureEvent) -> Optional[dict]:
        """
        Suggest automatic remediation for a failure.

        Returns dict with:
            - action: Description of action
            - command: Shell command to execute
            - confidence: Confidence level (0-1)
            - requires_confirmation: Whether human approval needed
        """
        if not event.pattern_id or event.pattern_id not in self.patterns:
            return None

        pattern = self.patterns[event.pattern_id]

        # Auto-remediation mappings
        auto_remediations = {
            "Container dependency failure": {
                "action": f"Restart container: {event.service}",
                "command": f"docker restart {event.service}",
                "confidence": 0.8,
                "requires_confirmation": False,
            },
            "Disk space exhaustion": {
                "action": "Clean Docker system",
                "command": "docker system prune -f --volumes",
                "confidence": 0.6,
                "requires_confirmation": True,
            },
            "GPU memory exhaustion": {
                "action": "Restart inference service",
                "command": "sudo systemctl restart tabbyapi",
                "confidence": 0.5,
                "requires_confirmation": True,
            },
            "Redis connection failure": {
                "action": "Restart Redis container",
                "command": "docker restart hydra-redis",
                "confidence": 0.7,
                "requires_confirmation": False,
            },
            "Database connection failure": {
                "action": "Restart PostgreSQL container",
                "command": "docker restart hydra-postgres",
                "confidence": 0.6,
                "requires_confirmation": True,
            },
        }

        return auto_remediations.get(pattern.description)

    def export_report_markdown(self, hours: int = 24) -> str:
        """Export diagnostic report as markdown."""
        report = self.analyze(hours)

        lines = [
            "# Hydra Cluster Diagnostic Report",
            "",
            f"**Generated:** {report.generated_at}",
            f"**Time Range:** Last {report.time_range_hours} hours",
            f"**Health Score:** {report.health_score:.1f}/100",
            f"**Trend:** {report.trend.upper()}",
            "",
            "## Summary",
            "",
            f"- **Total Failures:** {report.total_failures}",
        ]

        if report.failures_by_severity:
            lines.append("- **By Severity:**")
            for sev, count in sorted(report.failures_by_severity.items()):
                lines.append(f"  - {sev}: {count}")

        if report.failures_by_category:
            lines.append("- **By Category:**")
            for cat, count in sorted(report.failures_by_category.items()):
                lines.append(f"  - {cat}: {count}")

        lines.extend(["", "## Top Failure Patterns", ""])

        if report.top_patterns:
            for i, pattern in enumerate(report.top_patterns, 1):
                lines.append(f"### {i}. {pattern['description']}")
                lines.append(f"- **Category:** {pattern['category']}")
                lines.append(f"- **Occurrences:** {pattern['count']}")
                if pattern.get('remediation'):
                    lines.append("- **Suggested Fix:**")
                    for rem in pattern['remediation']:
                        lines.append(f"  - {rem}")
                lines.append("")
        else:
            lines.append("*No recurring patterns detected.*")

        lines.extend(["", "## Recommendations", ""])

        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")

        lines.extend([
            "",
            "---",
            "*Generated by Hydra Self-Diagnosis Engine*",
        ])

        return "\n".join(lines)


# FastAPI integration
def create_diagnosis_router():
    """Create FastAPI router for diagnosis endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])
    engine = SelfDiagnosisEngine()

    class FailureInput(BaseModel):
        service: str
        error_message: str
        stack_trace: Optional[str] = None
        context: Optional[dict] = None

    class ResolutionInput(BaseModel):
        event_id: str
        notes: Optional[str] = None

    @router.post("/failure")
    async def record_failure(failure: FailureInput):
        """Record a new failure event."""
        event = engine.record_failure(
            service=failure.service,
            error_message=failure.error_message,
            stack_trace=failure.stack_trace,
            context=failure.context,
        )
        return {
            "event_id": event.id,
            "category": event.category,
            "severity": event.severity,
            "pattern_id": event.pattern_id,
        }

    @router.post("/resolve")
    async def resolve_failure(resolution: ResolutionInput):
        """Mark a failure as resolved."""
        success = engine.resolve_failure(
            event_id=resolution.event_id,
            resolution_notes=resolution.notes,
        )
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"status": "resolved", "event_id": resolution.event_id}

    @router.get("/report")
    async def get_report(hours: int = 24):
        """Get diagnostic report."""
        report = engine.analyze(hours=hours)
        return asdict(report)

    @router.get("/report/markdown")
    async def get_report_markdown(hours: int = 24):
        """Get diagnostic report as markdown."""
        return {"markdown": engine.export_report_markdown(hours)}

    @router.get("/patterns")
    async def list_patterns():
        """List all failure patterns."""
        return {
            "patterns": [
                {
                    "id": p.id,
                    "description": p.description,
                    "category": p.category,
                    "occurrences": p.occurrences,
                    "last_seen": p.last_seen,
                }
                for p in engine.patterns.values()
            ]
        }

    @router.get("/patterns/{pattern_id}")
    async def get_pattern(pattern_id: str):
        """Get pattern details."""
        pattern = engine.get_pattern_details(pattern_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        return asdict(pattern)

    @router.get("/remediation/{event_id}")
    async def suggest_remediation(event_id: str):
        """Get auto-remediation suggestion for an event."""
        event = next((e for e in engine.events if e.id == event_id), None)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        suggestion = engine.suggest_auto_remediation(event)
        return {"event_id": event_id, "remediation": suggestion}

    @router.get("/health")
    async def diagnosis_health():
        """Health check with current status."""
        report = engine.analyze(hours=1)
        return {
            "status": "healthy" if report.health_score >= 80 else "degraded",
            "health_score": report.health_score,
            "recent_failures": report.total_failures,
            "trend": report.trend,
        }

    return router
