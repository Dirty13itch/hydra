"""
Human Feedback Integration Loop

Analyzes accumulated human feedback to:
- Identify quality issues and patterns
- Trigger improvement proposals
- Adjust model selection and routing
- Generate actionable recommendations

Integrates with:
- Human feedback collection system
- Self-improvement system
- Preference learning
- Model routing

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

FEEDBACK_ANALYZED = Counter(
    "hydra_feedback_analyzed_total",
    "Total feedback items analyzed"
)

IMPROVEMENT_PROPOSALS = Counter(
    "hydra_feedback_improvement_proposals_total",
    "Improvement proposals from feedback",
    ["category"]
)

FEEDBACK_QUALITY_SCORE = Gauge(
    "hydra_feedback_quality_score",
    "Current quality score from feedback",
    ["category"]
)


# =============================================================================
# Feedback Pattern Types
# =============================================================================

class IssueCategory(Enum):
    """Categories of issues detected from feedback."""
    MODEL_QUALITY = "model_quality"
    PROMPT_EFFECTIVENESS = "prompt_effectiveness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    PERFORMANCE = "performance"
    STYLE = "style"
    SAFETY = "safety"


class FeedbackTrend(Enum):
    """Trend direction for feedback metrics."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FeedbackPattern:
    """A detected pattern in feedback."""
    pattern_id: str
    category: IssueCategory
    description: str
    affected_items: List[str]
    frequency: int
    severity: float  # 0-1
    first_seen: datetime
    last_seen: datetime
    suggested_actions: List[str] = field(default_factory=list)


@dataclass
class QualityMetrics:
    """Quality metrics from feedback."""
    overall_score: float
    asset_score: float
    generation_score: float
    by_model: Dict[str, float]
    by_category: Dict[str, float]
    trends: Dict[str, FeedbackTrend]
    sample_size: int


@dataclass
class ImprovementRecommendation:
    """A recommendation for improvement."""
    rec_id: str
    category: IssueCategory
    priority: int  # 1-5
    title: str
    description: str
    rationale: str
    affected_models: List[str]
    suggested_actions: List[str]
    expected_impact: str
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Feedback Integration Loop
# =============================================================================

class FeedbackIntegrationLoop:
    """
    Analyzes human feedback to drive system improvements.

    Features:
    - Pattern detection in feedback
    - Quality metric tracking
    - Improvement proposal generation
    - Integration with self-improvement system
    """

    def __init__(
        self,
        db_path: str = "/data/human_feedback.db",
        analysis_interval_hours: int = 6,
    ):
        self.db_path = Path(db_path)
        self.analysis_interval = timedelta(hours=analysis_interval_hours)

        self.patterns: Dict[str, FeedbackPattern] = {}
        self.recommendations: List[ImprovementRecommendation] = []
        self.last_analysis: Optional[datetime] = None
        self.quality_history: List[Tuple[datetime, float]] = []

        # Thresholds for triggering improvements
        self.thresholds = {
            "min_feedback_for_analysis": 10,
            "quality_decline_trigger": 0.1,  # 10% decline
            "issue_frequency_trigger": 3,    # Same issue 3+ times
            "severity_trigger": 0.7,         # Severity above 70%
        }

        logger.info("Feedback integration loop initialized")

    def _get_db(self):
        """Get database connection."""
        if not self.db_path.exists():
            logger.warning(f"Feedback database not found at {self.db_path}")
            return None
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Feedback Analysis
    # =========================================================================

    async def analyze_feedback(
        self,
        lookback_days: int = 7,
    ) -> Dict[str, Any]:
        """Analyze recent feedback for patterns and quality metrics."""
        conn = self._get_db()
        if not conn:
            return {"error": "Database not available"}

        try:
            cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()

            # Fetch asset feedback
            asset_rows = conn.execute("""
                SELECT * FROM asset_feedback
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (cutoff,)).fetchall()

            # Fetch generation feedback
            gen_rows = conn.execute("""
                SELECT * FROM generation_feedback
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (cutoff,)).fetchall()

            # Fetch comparisons
            comp_rows = conn.execute("""
                SELECT * FROM comparison_feedback
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (cutoff,)).fetchall()

            conn.close()

            # Calculate quality metrics
            metrics = self._calculate_quality_metrics(asset_rows, gen_rows, comp_rows)

            # Detect patterns
            patterns = self._detect_patterns(asset_rows, gen_rows, comp_rows)

            # Generate recommendations
            recommendations = self._generate_recommendations(metrics, patterns)

            # Update state
            self.last_analysis = datetime.utcnow()
            self.patterns = {p.pattern_id: p for p in patterns}
            self.recommendations = recommendations
            self.quality_history.append((self.last_analysis, metrics.overall_score))

            # Update metrics
            FEEDBACK_ANALYZED.inc(len(asset_rows) + len(gen_rows) + len(comp_rows))
            FEEDBACK_QUALITY_SCORE.labels(category="overall").set(metrics.overall_score)
            FEEDBACK_QUALITY_SCORE.labels(category="assets").set(metrics.asset_score)
            FEEDBACK_QUALITY_SCORE.labels(category="generations").set(metrics.generation_score)

            return {
                "analyzed_at": self.last_analysis.isoformat(),
                "feedback_count": {
                    "assets": len(asset_rows),
                    "generations": len(gen_rows),
                    "comparisons": len(comp_rows),
                },
                "quality_metrics": {
                    "overall": round(metrics.overall_score, 2),
                    "assets": round(metrics.asset_score, 2),
                    "generations": round(metrics.generation_score, 2),
                    "by_model": {k: round(v, 2) for k, v in metrics.by_model.items()},
                    "trends": {k: v.value for k, v in metrics.trends.items()},
                },
                "patterns_detected": len(patterns),
                "recommendations": len(recommendations),
            }

        except Exception as e:
            logger.error(f"Feedback analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_quality_metrics(
        self,
        asset_rows: List,
        gen_rows: List,
        comp_rows: List,
    ) -> QualityMetrics:
        """Calculate quality metrics from feedback."""
        rating_values = {
            "excellent": 5, "good": 4, "acceptable": 3, "poor": 2, "rejected": 1
        }

        # Asset scores
        asset_scores = [rating_values.get(r["rating"], 3) for r in asset_rows]
        asset_avg = sum(asset_scores) / len(asset_scores) if asset_scores else 3.0

        # Generation scores
        gen_scores = [rating_values.get(r["rating"], 3) for r in gen_rows]
        gen_avg = sum(gen_scores) / len(gen_scores) if gen_scores else 3.0

        # By model
        model_scores: Dict[str, List[int]] = {}
        for row in asset_rows:
            model = row["model_used"] or "unknown"
            if model not in model_scores:
                model_scores[model] = []
            model_scores[model].append(rating_values.get(row["rating"], 3))

        for row in gen_rows:
            model = row["model_used"] or "unknown"
            if model not in model_scores:
                model_scores[model] = []
            model_scores[model].append(rating_values.get(row["rating"], 3))

        by_model = {
            model: sum(scores) / len(scores)
            for model, scores in model_scores.items() if scores
        }

        # By category
        by_category: Dict[str, List[int]] = {}
        for row in asset_rows:
            cat = row["asset_type"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(rating_values.get(row["rating"], 3))

        for row in gen_rows:
            cat = row["generation_type"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(rating_values.get(row["rating"], 3))

        by_cat_avg = {
            cat: sum(scores) / len(scores)
            for cat, scores in by_category.items() if scores
        }

        # Calculate trends (compare to previous analysis if available)
        trends = self._calculate_trends(asset_avg, gen_avg)

        # Overall score (weighted average)
        total = len(asset_scores) + len(gen_scores)
        overall = (
            (asset_avg * len(asset_scores) + gen_avg * len(gen_scores)) / total
            if total > 0 else 3.0
        )

        return QualityMetrics(
            overall_score=overall,
            asset_score=asset_avg,
            generation_score=gen_avg,
            by_model=by_model,
            by_category=by_cat_avg,
            trends=trends,
            sample_size=total,
        )

    def _calculate_trends(
        self,
        current_asset: float,
        current_gen: float,
    ) -> Dict[str, FeedbackTrend]:
        """Calculate quality trends."""
        trends = {}

        # Check historical data
        if len(self.quality_history) >= 2:
            prev_overall = self.quality_history[-2][1]
            curr_overall = (current_asset + current_gen) / 2

            diff = curr_overall - prev_overall
            if diff > 0.1:
                trends["overall"] = FeedbackTrend.IMPROVING
            elif diff < -0.1:
                trends["overall"] = FeedbackTrend.DECLINING
            else:
                trends["overall"] = FeedbackTrend.STABLE
        else:
            trends["overall"] = FeedbackTrend.STABLE

        return trends

    def _detect_patterns(
        self,
        asset_rows: List,
        gen_rows: List,
        comp_rows: List,
    ) -> List[FeedbackPattern]:
        """Detect patterns in feedback."""
        patterns = []

        # Issue frequency analysis
        issue_counts: Dict[str, List[str]] = {}

        for row in asset_rows:
            issues = json.loads(row["issues"]) if row["issues"] else []
            for issue in issues:
                if issue not in issue_counts:
                    issue_counts[issue] = []
                issue_counts[issue].append(row["asset_id"])

        for row in gen_rows:
            issues = json.loads(row["issues"]) if row["issues"] else []
            for issue in issues:
                if issue not in issue_counts:
                    issue_counts[issue] = []
                issue_counts[issue].append(row["generation_id"])

        # Create patterns for frequent issues
        for issue, items in issue_counts.items():
            if len(items) >= self.thresholds["issue_frequency_trigger"]:
                patterns.append(FeedbackPattern(
                    pattern_id=f"issue-{hash(issue) % 10000}",
                    category=self._categorize_issue(issue),
                    description=f"Recurring issue: {issue}",
                    affected_items=items[:10],  # Limit for storage
                    frequency=len(items),
                    severity=min(len(items) / 10, 1.0),
                    first_seen=datetime.utcnow() - timedelta(days=7),
                    last_seen=datetime.utcnow(),
                    suggested_actions=self._suggest_actions_for_issue(issue),
                ))

        # Model quality pattern
        model_ratings: Dict[str, List[int]] = {}
        rating_values = {"excellent": 5, "good": 4, "acceptable": 3, "poor": 2, "rejected": 1}

        for row in asset_rows:
            model = row["model_used"] or "unknown"
            if model not in model_ratings:
                model_ratings[model] = []
            model_ratings[model].append(rating_values.get(row["rating"], 3))

        for model, ratings in model_ratings.items():
            avg = sum(ratings) / len(ratings) if ratings else 3.0
            if avg < 2.5 and len(ratings) >= 5:
                patterns.append(FeedbackPattern(
                    pattern_id=f"model-quality-{hash(model) % 10000}",
                    category=IssueCategory.MODEL_QUALITY,
                    description=f"Low quality ratings for model: {model}",
                    affected_items=[],
                    frequency=len(ratings),
                    severity=1 - (avg / 5),
                    first_seen=datetime.utcnow() - timedelta(days=7),
                    last_seen=datetime.utcnow(),
                    suggested_actions=[
                        f"Review {model} configuration",
                        f"Consider alternative models",
                        f"Adjust routing to reduce {model} usage for this task type",
                    ],
                ))

        # Rejection pattern
        rejected_count = sum(
            1 for row in asset_rows if row["rating"] == "rejected"
        ) + sum(
            1 for row in gen_rows if row["rating"] == "rejected"
        )

        if rejected_count >= 5:
            patterns.append(FeedbackPattern(
                pattern_id="high-rejection-rate",
                category=IssueCategory.MODEL_QUALITY,
                description=f"High rejection rate: {rejected_count} items rejected",
                affected_items=[],
                frequency=rejected_count,
                severity=min(rejected_count / 20, 1.0),
                first_seen=datetime.utcnow() - timedelta(days=7),
                last_seen=datetime.utcnow(),
                suggested_actions=[
                    "Review rejected items for common issues",
                    "Adjust quality thresholds",
                    "Improve prompt engineering",
                ],
            ))

        return patterns

    def _categorize_issue(self, issue: str) -> IssueCategory:
        """Categorize an issue string."""
        issue_lower = issue.lower()

        if any(w in issue_lower for w in ["hand", "finger", "face", "anatomy"]):
            return IssueCategory.ACCURACY
        elif any(w in issue_lower for w in ["style", "art", "color"]):
            return IssueCategory.STYLE
        elif any(w in issue_lower for w in ["consistency", "different", "changed"]):
            return IssueCategory.CONSISTENCY
        elif any(w in issue_lower for w in ["slow", "timeout", "error"]):
            return IssueCategory.PERFORMANCE
        elif any(w in issue_lower for w in ["hallucination", "wrong", "incorrect"]):
            return IssueCategory.ACCURACY
        elif any(w in issue_lower for w in ["inappropriate", "unsafe"]):
            return IssueCategory.SAFETY
        else:
            return IssueCategory.MODEL_QUALITY

    def _suggest_actions_for_issue(self, issue: str) -> List[str]:
        """Suggest actions for an issue."""
        issue_lower = issue.lower()

        if "hand" in issue_lower or "finger" in issue_lower:
            return [
                "Add hand-focused negative prompts",
                "Enable ADetailer for hand correction",
                "Use inpainting for hand fixes",
            ]
        elif "hallucination" in issue_lower:
            return [
                "Reduce temperature for generations",
                "Improve context grounding",
                "Add fact-checking step",
            ]
        elif "consistency" in issue_lower:
            return [
                "Review character sheet prompts",
                "Increase prompt specificity",
                "Use LoRA for character consistency",
            ]
        else:
            return [
                "Review and adjust prompts",
                "Consider alternative models",
                "Gather more specific feedback",
            ]

    def _generate_recommendations(
        self,
        metrics: QualityMetrics,
        patterns: List[FeedbackPattern],
    ) -> List[ImprovementRecommendation]:
        """Generate improvement recommendations."""
        recommendations = []

        # Quality decline recommendation
        if metrics.trends.get("overall") == FeedbackTrend.DECLINING:
            recommendations.append(ImprovementRecommendation(
                rec_id="rec-quality-decline",
                category=IssueCategory.MODEL_QUALITY,
                priority=1,
                title="Address Quality Decline",
                description="Overall quality metrics are declining based on recent feedback",
                rationale=f"Quality score has decreased. Current: {metrics.overall_score:.2f}",
                affected_models=list(metrics.by_model.keys()),
                suggested_actions=[
                    "Review recent changes to prompts or models",
                    "Analyze patterns in low-rated outputs",
                    "Consider rolling back recent configuration changes",
                ],
                expected_impact="Restore quality to previous levels",
            ))

        # Low-performing model recommendations
        for model, score in metrics.by_model.items():
            if score < 2.5:
                recommendations.append(ImprovementRecommendation(
                    rec_id=f"rec-model-{hash(model) % 10000}",
                    category=IssueCategory.MODEL_QUALITY,
                    priority=2,
                    title=f"Review Model Performance: {model}",
                    description=f"Model {model} has low feedback scores",
                    rationale=f"Average rating: {score:.2f}/5",
                    affected_models=[model],
                    suggested_actions=[
                        f"Reduce routing weight for {model}",
                        "Review prompt compatibility",
                        "Consider deprecating for this use case",
                    ],
                    expected_impact="Improved output quality by routing away from underperforming model",
                ))

        # Pattern-based recommendations
        for pattern in patterns:
            if pattern.severity >= self.thresholds["severity_trigger"]:
                recommendations.append(ImprovementRecommendation(
                    rec_id=f"rec-pattern-{pattern.pattern_id}",
                    category=pattern.category,
                    priority=int(pattern.severity * 5),
                    title=f"Address: {pattern.description}",
                    description=f"Detected pattern affecting {pattern.frequency} items",
                    rationale=f"Severity: {pattern.severity:.0%}, Frequency: {pattern.frequency}",
                    affected_models=[],
                    suggested_actions=pattern.suggested_actions,
                    expected_impact="Reduce occurrence of this issue",
                ))

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority, reverse=True)

        # Update metrics
        for rec in recommendations:
            IMPROVEMENT_PROPOSALS.labels(category=rec.category.value).inc()

        return recommendations

    # =========================================================================
    # Integration Points
    # =========================================================================

    async def get_routing_adjustments(self) -> Dict[str, Any]:
        """Get recommended routing adjustments based on feedback."""
        if not self.recommendations:
            await self.analyze_feedback()

        adjustments = {
            "models_to_reduce": [],
            "models_to_increase": [],
            "task_specific": {},
        }

        conn = self._get_db()
        if not conn:
            return adjustments

        try:
            # Find models with consistently good ratings
            good_models = conn.execute("""
                SELECT model_used, AVG(
                    CASE rating
                        WHEN 'excellent' THEN 5
                        WHEN 'good' THEN 4
                        WHEN 'acceptable' THEN 3
                        WHEN 'poor' THEN 2
                        WHEN 'rejected' THEN 1
                    END
                ) as avg_rating, COUNT(*) as count
                FROM (
                    SELECT model_used, rating FROM asset_feedback WHERE model_used IS NOT NULL
                    UNION ALL
                    SELECT model_used, rating FROM generation_feedback WHERE model_used IS NOT NULL
                )
                GROUP BY model_used
                HAVING count >= 5
                ORDER BY avg_rating DESC
            """).fetchall()

            conn.close()

            for row in good_models:
                if row["avg_rating"] >= 4.0:
                    adjustments["models_to_increase"].append({
                        "model": row["model_used"],
                        "avg_rating": round(row["avg_rating"], 2),
                        "sample_size": row["count"],
                    })
                elif row["avg_rating"] < 2.5:
                    adjustments["models_to_reduce"].append({
                        "model": row["model_used"],
                        "avg_rating": round(row["avg_rating"], 2),
                        "sample_size": row["count"],
                    })

        except Exception as e:
            logger.error(f"Failed to calculate routing adjustments: {e}")

        return adjustments

    async def trigger_improvement_proposal(
        self,
        recommendation: ImprovementRecommendation,
    ) -> Dict[str, Any]:
        """Trigger a self-improvement proposal based on recommendation."""
        try:
            # Integration with self-improvement system
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8700/self-improvement/propose",
                    json={
                        "title": recommendation.title,
                        "description": recommendation.description,
                        "rationale": recommendation.rationale,
                        "proposed_changes": recommendation.suggested_actions,
                        "expected_impact": recommendation.expected_impact,
                        "source": "feedback_integration_loop",
                    },
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Failed to create proposal: {response.status_code}"}

        except Exception as e:
            logger.error(f"Failed to trigger improvement proposal: {e}")
            return {"error": str(e)}

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get current recommendations."""
        return [
            {
                "rec_id": r.rec_id,
                "category": r.category.value,
                "priority": r.priority,
                "title": r.title,
                "description": r.description,
                "rationale": r.rationale,
                "suggested_actions": r.suggested_actions,
                "expected_impact": r.expected_impact,
                "created_at": r.created_at.isoformat(),
            }
            for r in self.recommendations
        ]

    def get_patterns(self) -> List[Dict[str, Any]]:
        """Get detected patterns."""
        return [
            {
                "pattern_id": p.pattern_id,
                "category": p.category.value,
                "description": p.description,
                "frequency": p.frequency,
                "severity": round(p.severity, 2),
                "suggested_actions": p.suggested_actions,
            }
            for p in self.patterns.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get integration loop status."""
        return {
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None,
            "patterns_detected": len(self.patterns),
            "active_recommendations": len(self.recommendations),
            "quality_history_size": len(self.quality_history),
            "thresholds": self.thresholds,
        }


# =============================================================================
# Global Instance
# =============================================================================

_feedback_loop: Optional[FeedbackIntegrationLoop] = None


def get_feedback_loop() -> FeedbackIntegrationLoop:
    """Get or create the feedback integration loop."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackIntegrationLoop()
    return _feedback_loop


# =============================================================================
# FastAPI Router
# =============================================================================

def create_feedback_loop_router():
    """Create FastAPI router for feedback integration loop endpoints."""
    from fastapi import APIRouter, HTTPException, BackgroundTasks

    router = APIRouter(prefix="/feedback-loop", tags=["feedback-integration"])

    @router.get("/status")
    async def loop_status():
        """Get feedback integration loop status."""
        loop = get_feedback_loop()
        return loop.get_status()

    @router.post("/analyze")
    async def analyze_feedback(lookback_days: int = 7):
        """Trigger feedback analysis."""
        loop = get_feedback_loop()
        results = await loop.analyze_feedback(lookback_days=lookback_days)
        return results

    @router.get("/patterns")
    async def get_patterns():
        """Get detected feedback patterns."""
        loop = get_feedback_loop()
        return {"patterns": loop.get_patterns()}

    @router.get("/recommendations")
    async def get_recommendations():
        """Get current improvement recommendations."""
        loop = get_feedback_loop()
        return {"recommendations": loop.get_recommendations()}

    @router.get("/routing-adjustments")
    async def get_routing_adjustments():
        """Get recommended routing adjustments based on feedback."""
        loop = get_feedback_loop()
        adjustments = await loop.get_routing_adjustments()
        return adjustments

    @router.post("/recommendations/{rec_id}/apply")
    async def apply_recommendation(rec_id: str, background_tasks: BackgroundTasks):
        """Apply a recommendation by triggering an improvement proposal."""
        loop = get_feedback_loop()

        rec = next((r for r in loop.recommendations if r.rec_id == rec_id), None)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        result = await loop.trigger_improvement_proposal(rec)
        return result

    return router
