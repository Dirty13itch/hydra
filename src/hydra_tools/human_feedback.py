"""
Human Feedback Collection API

Collects human feedback on generated assets, model outputs, and system behavior.
This data feeds into the preference learning system to improve:
- Model selection for different task types
- Quality scoring calibration
- Asset generation parameters

Endpoints:
    POST /feedback/asset - Rate a generated asset (image, audio, etc.)
    POST /feedback/generation - Rate a text generation
    POST /feedback/comparison - A/B comparison between two outputs
    GET /feedback/stats - Feedback statistics and trends
    GET /feedback/pending - Assets awaiting feedback
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Database path
DB_PATH = Path(os.environ.get("HYDRA_DATA_DIR", "/data")) / "human_feedback.db"


# =============================================================================
# DATA MODELS
# =============================================================================

class FeedbackRating(str, Enum):
    """Rating scale for feedback."""
    EXCELLENT = "excellent"    # 5 stars - exceeds expectations
    GOOD = "good"              # 4 stars - meets expectations
    ACCEPTABLE = "acceptable"  # 3 stars - usable but needs improvement
    POOR = "poor"              # 2 stars - significant issues
    REJECTED = "rejected"      # 1 star - unusable, should regenerate


class AssetType(str, Enum):
    """Types of generated assets."""
    CHARACTER_PORTRAIT = "character_portrait"
    SCENE_BACKGROUND = "scene_background"
    EMOTION_VARIANT = "emotion_variant"
    VOICE_AUDIO = "voice_audio"
    VOICE_CLONE = "voice_clone"
    INPAINT_FIX = "inpaint_fix"
    OTHER = "other"


class GenerationType(str, Enum):
    """Types of text generations."""
    DIALOGUE = "dialogue"
    NARRATIVE = "narrative"
    RESEARCH = "research"
    CODE = "code"
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    ASSISTANT = "assistant"
    OTHER = "other"


class AssetFeedbackRequest(BaseModel):
    """Request to rate a generated asset."""
    asset_id: str = Field(..., description="Unique identifier for the asset")
    asset_type: AssetType = Field(..., description="Type of asset")
    rating: FeedbackRating = Field(..., description="Overall rating")
    character_name: Optional[str] = Field(None, description="Character name if applicable")
    prompt_used: Optional[str] = Field(None, description="Prompt used for generation")
    model_used: Optional[str] = Field(None, description="Model used (e.g., NoobAI-XL)")

    # Detailed ratings (optional)
    quality_score: Optional[int] = Field(None, ge=1, le=10, description="Visual quality 1-10")
    consistency_score: Optional[int] = Field(None, ge=1, le=10, description="Character consistency 1-10")
    style_score: Optional[int] = Field(None, ge=1, le=10, description="Style adherence 1-10")

    # Additional feedback
    issues: Optional[List[str]] = Field(None, description="List of issues (e.g., 'bad hands', 'off-model')")
    notes: Optional[str] = Field(None, description="Free-form notes")
    should_regenerate: bool = Field(False, description="Flag for regeneration queue")


class GenerationFeedbackRequest(BaseModel):
    """Request to rate a text generation."""
    generation_id: str = Field(..., description="Unique identifier for the generation")
    generation_type: GenerationType = Field(..., description="Type of generation")
    rating: FeedbackRating = Field(..., description="Overall rating")
    model_used: Optional[str] = Field(None, description="Model used for generation")
    prompt_used: Optional[str] = Field(None, description="Original prompt")

    # Detailed ratings
    accuracy_score: Optional[int] = Field(None, ge=1, le=10, description="Factual accuracy 1-10")
    coherence_score: Optional[int] = Field(None, ge=1, le=10, description="Coherence/flow 1-10")
    helpfulness_score: Optional[int] = Field(None, ge=1, le=10, description="Helpfulness 1-10")

    # Additional feedback
    issues: Optional[List[str]] = Field(None, description="Issues (e.g., 'hallucination', 'off-topic')")
    notes: Optional[str] = Field(None, description="Free-form notes")
    preferred_response: Optional[str] = Field(None, description="What you would have preferred")


class ComparisonFeedbackRequest(BaseModel):
    """A/B comparison between two outputs."""
    comparison_id: str = Field(..., description="Unique identifier for this comparison")
    item_a_id: str = Field(..., description="ID of first item")
    item_b_id: str = Field(..., description="ID of second item")
    preferred: str = Field(..., description="Which is preferred: 'a', 'b', or 'tie'")

    # Context
    comparison_type: str = Field(..., description="'asset' or 'generation'")
    model_a: Optional[str] = Field(None, description="Model used for A")
    model_b: Optional[str] = Field(None, description="Model used for B")

    # Reasoning
    reason: Optional[str] = Field(None, description="Why this choice was preferred")
    notes: Optional[str] = Field(None, description="Additional notes")


class FeedbackStats(BaseModel):
    """Feedback statistics."""
    total_feedback: int
    asset_feedback: int
    generation_feedback: int
    comparison_feedback: int
    avg_asset_rating: float
    avg_generation_rating: float
    top_issues: List[Dict[str, Any]]
    feedback_by_day: List[Dict[str, Any]]
    needs_regeneration: int


# =============================================================================
# DATABASE
# =============================================================================

def init_db():
    """Initialize the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    # Asset feedback table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS asset_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            rating TEXT NOT NULL,
            character_name TEXT,
            prompt_used TEXT,
            model_used TEXT,
            quality_score INTEGER,
            consistency_score INTEGER,
            style_score INTEGER,
            issues TEXT,
            notes TEXT,
            should_regenerate INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(asset_id)
        )
    """)

    # Generation feedback table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generation_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_id TEXT NOT NULL,
            generation_type TEXT NOT NULL,
            rating TEXT NOT NULL,
            model_used TEXT,
            prompt_used TEXT,
            accuracy_score INTEGER,
            coherence_score INTEGER,
            helpfulness_score INTEGER,
            issues TEXT,
            notes TEXT,
            preferred_response TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(generation_id)
        )
    """)

    # Comparison feedback table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparison_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comparison_id TEXT NOT NULL,
            item_a_id TEXT NOT NULL,
            item_b_id TEXT NOT NULL,
            preferred TEXT NOT NULL,
            comparison_type TEXT NOT NULL,
            model_a TEXT,
            model_b TEXT,
            reason TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(comparison_id)
        )
    """)

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_type ON asset_feedback(asset_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_rating ON asset_feedback(rating)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_type ON generation_feedback(generation_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gen_rating ON generation_feedback(rating)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_regenerate ON asset_feedback(should_regenerate)")

    conn.commit()
    conn.close()


init_db()


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# RATING CONVERSION
# =============================================================================

RATING_VALUES = {
    FeedbackRating.EXCELLENT: 5,
    FeedbackRating.GOOD: 4,
    FeedbackRating.ACCEPTABLE: 3,
    FeedbackRating.POOR: 2,
    FeedbackRating.REJECTED: 1,
}


def rating_to_value(rating: FeedbackRating) -> int:
    return RATING_VALUES.get(rating, 3)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/asset")
async def submit_asset_feedback(request: AssetFeedbackRequest):
    """Submit feedback for a generated asset."""
    conn = get_db()

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO asset_feedback
            (asset_id, asset_type, rating, character_name, prompt_used, model_used,
             quality_score, consistency_score, style_score, issues, notes,
             should_regenerate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.asset_id,
                request.asset_type.value,
                request.rating.value,
                request.character_name,
                request.prompt_used,
                request.model_used,
                request.quality_score,
                request.consistency_score,
                request.style_score,
                json.dumps(request.issues) if request.issues else None,
                request.notes,
                1 if request.should_regenerate else 0,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()

        return {
            "status": "recorded",
            "asset_id": request.asset_id,
            "rating": request.rating.value,
            "numeric_rating": rating_to_value(request.rating),
            "queued_for_regeneration": request.should_regenerate,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/generation")
async def submit_generation_feedback(request: GenerationFeedbackRequest):
    """Submit feedback for a text generation."""
    conn = get_db()

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO generation_feedback
            (generation_id, generation_type, rating, model_used, prompt_used,
             accuracy_score, coherence_score, helpfulness_score, issues, notes,
             preferred_response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.generation_id,
                request.generation_type.value,
                request.rating.value,
                request.model_used,
                request.prompt_used,
                request.accuracy_score,
                request.coherence_score,
                request.helpfulness_score,
                json.dumps(request.issues) if request.issues else None,
                request.notes,
                request.preferred_response,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()

        return {
            "status": "recorded",
            "generation_id": request.generation_id,
            "rating": request.rating.value,
            "numeric_rating": rating_to_value(request.rating),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/comparison")
async def submit_comparison_feedback(request: ComparisonFeedbackRequest):
    """Submit A/B comparison feedback."""
    conn = get_db()

    if request.preferred not in ("a", "b", "tie"):
        raise HTTPException(status_code=400, detail="preferred must be 'a', 'b', or 'tie'")

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO comparison_feedback
            (comparison_id, item_a_id, item_b_id, preferred, comparison_type,
             model_a, model_b, reason, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.comparison_id,
                request.item_a_id,
                request.item_b_id,
                request.preferred,
                request.comparison_type,
                request.model_a,
                request.model_b,
                request.reason,
                request.notes,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()

        return {
            "status": "recorded",
            "comparison_id": request.comparison_id,
            "preferred": request.preferred,
            "winner_id": request.item_a_id if request.preferred == "a" else
                        request.item_b_id if request.preferred == "b" else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/stats")
async def get_feedback_stats(days: int = Query(30, description="Days to include in stats")):
    """Get feedback statistics and trends."""
    conn = get_db()

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Total counts
        asset_count = conn.execute(
            "SELECT COUNT(*) FROM asset_feedback WHERE created_at >= ?", (cutoff,)
        ).fetchone()[0]

        gen_count = conn.execute(
            "SELECT COUNT(*) FROM generation_feedback WHERE created_at >= ?", (cutoff,)
        ).fetchone()[0]

        comp_count = conn.execute(
            "SELECT COUNT(*) FROM comparison_feedback WHERE created_at >= ?", (cutoff,)
        ).fetchone()[0]

        # Average ratings
        avg_asset = conn.execute(
            """
            SELECT AVG(
                CASE rating
                    WHEN 'excellent' THEN 5
                    WHEN 'good' THEN 4
                    WHEN 'acceptable' THEN 3
                    WHEN 'poor' THEN 2
                    WHEN 'rejected' THEN 1
                END
            ) FROM asset_feedback WHERE created_at >= ?
            """, (cutoff,)
        ).fetchone()[0] or 0

        avg_gen = conn.execute(
            """
            SELECT AVG(
                CASE rating
                    WHEN 'excellent' THEN 5
                    WHEN 'good' THEN 4
                    WHEN 'acceptable' THEN 3
                    WHEN 'poor' THEN 2
                    WHEN 'rejected' THEN 1
                END
            ) FROM generation_feedback WHERE created_at >= ?
            """, (cutoff,)
        ).fetchone()[0] or 0

        # Top issues
        issue_counts = {}
        for row in conn.execute(
            "SELECT issues FROM asset_feedback WHERE issues IS NOT NULL AND created_at >= ?",
            (cutoff,)
        ):
            issues = json.loads(row[0])
            for issue in issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        for row in conn.execute(
            "SELECT issues FROM generation_feedback WHERE issues IS NOT NULL AND created_at >= ?",
            (cutoff,)
        ):
            issues = json.loads(row[0])
            for issue in issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        top_issues = sorted(
            [{"issue": k, "count": v} for k, v in issue_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Feedback by day
        feedback_by_day = []
        for row in conn.execute(
            """
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM (
                SELECT created_at FROM asset_feedback WHERE created_at >= ?
                UNION ALL
                SELECT created_at FROM generation_feedback WHERE created_at >= ?
            )
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 14
            """, (cutoff, cutoff)
        ):
            feedback_by_day.append({"date": row[0], "count": row[1]})

        # Needs regeneration count
        regen_count = conn.execute(
            "SELECT COUNT(*) FROM asset_feedback WHERE should_regenerate = 1"
        ).fetchone()[0]

        return FeedbackStats(
            total_feedback=asset_count + gen_count + comp_count,
            asset_feedback=asset_count,
            generation_feedback=gen_count,
            comparison_feedback=comp_count,
            avg_asset_rating=round(avg_asset, 2),
            avg_generation_rating=round(avg_gen, 2),
            top_issues=top_issues,
            feedback_by_day=feedback_by_day,
            needs_regeneration=regen_count,
        )
    finally:
        conn.close()


@router.get("/pending")
async def get_pending_regeneration(
    limit: int = Query(50, description="Max items to return"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
):
    """Get assets flagged for regeneration."""
    conn = get_db()

    try:
        if asset_type:
            rows = conn.execute(
                """
                SELECT asset_id, asset_type, rating, character_name, issues, notes, created_at
                FROM asset_feedback
                WHERE should_regenerate = 1 AND asset_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (asset_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT asset_id, asset_type, rating, character_name, issues, notes, created_at
                FROM asset_feedback
                WHERE should_regenerate = 1
                ORDER BY created_at DESC
                LIMIT ?
                """, (limit,)
            ).fetchall()

        items = []
        for row in rows:
            items.append({
                "asset_id": row["asset_id"],
                "asset_type": row["asset_type"],
                "rating": row["rating"],
                "character_name": row["character_name"],
                "issues": json.loads(row["issues"]) if row["issues"] else [],
                "notes": row["notes"],
                "created_at": row["created_at"],
            })

        return {"pending_regeneration": items, "count": len(items)}
    finally:
        conn.close()


@router.post("/clear-regeneration/{asset_id}")
async def clear_regeneration_flag(asset_id: str):
    """Clear the regeneration flag for an asset (after regeneration)."""
    conn = get_db()

    try:
        result = conn.execute(
            "UPDATE asset_feedback SET should_regenerate = 0 WHERE asset_id = ?",
            (asset_id,)
        )
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset feedback not found")

        return {"status": "cleared", "asset_id": asset_id}
    finally:
        conn.close()


@router.get("/by-model")
async def get_feedback_by_model(days: int = Query(30)):
    """Get feedback statistics grouped by model."""
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        results = {"asset_models": [], "generation_models": []}

        # Asset feedback by model
        for row in conn.execute(
            """
            SELECT
                model_used,
                COUNT(*) as count,
                AVG(
                    CASE rating
                        WHEN 'excellent' THEN 5
                        WHEN 'good' THEN 4
                        WHEN 'acceptable' THEN 3
                        WHEN 'poor' THEN 2
                        WHEN 'rejected' THEN 1
                    END
                ) as avg_rating,
                SUM(CASE WHEN rating IN ('excellent', 'good') THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN rating IN ('poor', 'rejected') THEN 1 ELSE 0 END) as negative
            FROM asset_feedback
            WHERE model_used IS NOT NULL AND created_at >= ?
            GROUP BY model_used
            ORDER BY count DESC
            """, (cutoff,)
        ):
            results["asset_models"].append({
                "model": row["model_used"],
                "count": row["count"],
                "avg_rating": round(row["avg_rating"], 2),
                "positive": row["positive"],
                "negative": row["negative"],
                "satisfaction_rate": round(row["positive"] / row["count"] * 100, 1) if row["count"] > 0 else 0,
            })

        # Generation feedback by model
        for row in conn.execute(
            """
            SELECT
                model_used,
                COUNT(*) as count,
                AVG(
                    CASE rating
                        WHEN 'excellent' THEN 5
                        WHEN 'good' THEN 4
                        WHEN 'acceptable' THEN 3
                        WHEN 'poor' THEN 2
                        WHEN 'rejected' THEN 1
                    END
                ) as avg_rating,
                SUM(CASE WHEN rating IN ('excellent', 'good') THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN rating IN ('poor', 'rejected') THEN 1 ELSE 0 END) as negative
            FROM generation_feedback
            WHERE model_used IS NOT NULL AND created_at >= ?
            GROUP BY model_used
            ORDER BY count DESC
            """, (cutoff,)
        ):
            results["generation_models"].append({
                "model": row["model_used"],
                "count": row["count"],
                "avg_rating": round(row["avg_rating"], 2),
                "positive": row["positive"],
                "negative": row["negative"],
                "satisfaction_rate": round(row["positive"] / row["count"] * 100, 1) if row["count"] > 0 else 0,
            })

        # A/B comparison wins
        comparison_wins = {}
        for row in conn.execute(
            """
            SELECT model_a, model_b, preferred, COUNT(*) as count
            FROM comparison_feedback
            WHERE created_at >= ?
            GROUP BY model_a, model_b, preferred
            """, (cutoff,)
        ):
            if row["preferred"] == "a" and row["model_a"]:
                comparison_wins[row["model_a"]] = comparison_wins.get(row["model_a"], 0) + row["count"]
            elif row["preferred"] == "b" and row["model_b"]:
                comparison_wins[row["model_b"]] = comparison_wins.get(row["model_b"], 0) + row["count"]

        results["comparison_wins"] = sorted(
            [{"model": k, "wins": v} for k, v in comparison_wins.items()],
            key=lambda x: x["wins"],
            reverse=True
        )

        return results
    finally:
        conn.close()


@router.get("/export")
async def export_feedback(
    format: str = Query("json", description="Export format: json or csv"),
    days: int = Query(90, description="Days to export"),
):
    """Export all feedback data."""
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        data = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "days_included": days,
            "asset_feedback": [],
            "generation_feedback": [],
            "comparison_feedback": [],
        }

        # Asset feedback
        for row in conn.execute(
            "SELECT * FROM asset_feedback WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,)
        ):
            data["asset_feedback"].append(dict(row))

        # Generation feedback
        for row in conn.execute(
            "SELECT * FROM generation_feedback WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,)
        ):
            data["generation_feedback"].append(dict(row))

        # Comparison feedback
        for row in conn.execute(
            "SELECT * FROM comparison_feedback WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,)
        ):
            data["comparison_feedback"].append(dict(row))

        return data
    finally:
        conn.close()


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_human_feedback_router() -> APIRouter:
    """Create and return the human feedback router."""
    return router
