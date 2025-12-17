"""
Preference Collection Module for Hydra

Provides webhook endpoints for collecting LLM interaction data:
- LiteLLM SpendLogs database sync (primary method)
- LiteLLM callback endpoint for automatic data collection (backup)
- Manual feedback submission endpoint
- Batch preference analysis

This module bridges LiteLLM usage tracking to the preference learning system.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Database connection for reading LiteLLM SpendLogs
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra"
)

# Track last sync timestamp
_last_sync_timestamp: Optional[datetime] = None

from hydra_tools.preference_learning import (
    PreferenceLearner,
    FeedbackType,
    TaskType,
)


class LiteLLMCallback(BaseModel):
    """LiteLLM callback payload structure."""
    call_type: str  # "completion", "embedding", etc.
    model: str
    messages: Optional[list] = None
    input: Optional[str] = None
    response: Optional[dict] = None
    response_cost: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    user: Optional[str] = None
    metadata: Optional[dict] = None
    exception: Optional[str] = None
    status: str = "success"  # "success" or "failure"


class FeedbackSubmission(BaseModel):
    """User feedback submission."""
    interaction_id: str
    feedback: str  # "positive", "negative", "regenerate", "edit"
    comment: Optional[str] = None


class InteractionQuery(BaseModel):
    """Query for analyzing interactions."""
    model: Optional[str] = None
    task_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_interactions: int = 10


# Shared learner instance
_learner = PreferenceLearner(user_id="hydra-default")


def create_preference_collector_router() -> APIRouter:
    """Create the preference collector API router."""
    router = APIRouter(prefix="/preference-collector", tags=["preference-collector"])

    @router.post("/litellm/callback")
    async def litellm_callback(request: Request):
        """
        Webhook endpoint for LiteLLM callbacks.

        Configure LiteLLM with:
        ```yaml
        litellm_settings:
          success_callback: ["webhook"]
          failure_callback: ["webhook"]
          callbacks:
            webhook_url: "http://192.168.1.244:8700/preference-collector/litellm/callback"
        ```
        """
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Extract relevant data
        call_type = body.get("call_type", "unknown")
        model = body.get("model", "unknown")
        status = body.get("status", "success")

        # Skip non-completion calls
        if call_type not in ["completion", "acompletion"]:
            return {"status": "skipped", "reason": f"call_type={call_type}"}

        # Extract prompt from messages
        messages = body.get("messages", [])
        prompt = ""
        if messages:
            # Get user message
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    prompt = msg.get("content", "")
                    break

        # Extract response
        response = body.get("response", {})
        response_text = ""
        if response:
            choices = response.get("choices", [])
            if choices:
                response_text = choices[0].get("message", {}).get("content", "")

        # Calculate latency
        start_time = body.get("start_time", 0)
        end_time = body.get("end_time", 0)
        latency_ms = int((end_time - start_time) * 1000) if start_time and end_time else 0

        # Record the interaction
        try:
            interaction = _learner.record_interaction(
                prompt=prompt,
                model=model,
                response=response_text,
                latency_ms=latency_ms,
                feedback=None if status == "success" else FeedbackType.NEGATIVE,
            )

            return {
                "status": "recorded",
                "interaction_id": interaction.id,
                "model": model,
                "latency_ms": latency_ms,
                "task_type": interaction.task_type,
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @router.post("/feedback")
    async def submit_feedback(feedback: FeedbackSubmission):
        """Submit feedback for a previous interaction."""
        try:
            feedback_type = FeedbackType(feedback.feedback)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback type: {feedback.feedback}"
            )

        # Update the interaction with feedback
        success = _learner.add_feedback(
            interaction_id=feedback.interaction_id,
            feedback=feedback_type,
        )

        if success:
            return {
                "status": "recorded",
                "interaction_id": feedback.interaction_id,
                "feedback": feedback.feedback
            }
        else:
            raise HTTPException(status_code=404, detail="Interaction not found")

    @router.get("/stats")
    async def get_collection_stats():
        """Get preference collection statistics."""
        prefs = _learner.export_preferences()

        return {
            "total_interactions": sum(
                s.get("total_uses", 0)
                for s in prefs.get("model_stats", {}).values()
            ),
            "models_tracked": len(prefs.get("model_stats", {})),
            "model_stats": prefs.get("model_stats", {}),
            "style_preferences": prefs.get("style_preferences", {}),
            "task_preferences": prefs.get("preferred_models", {}),
        }

    @router.get("/recommendations")
    async def get_recommendations():
        """Get model recommendations based on collected data."""
        recommendations = {}

        for task_type in TaskType:
            model = _learner.get_preferred_model(task_type=task_type)
            if model:
                recommendations[task_type.value] = model

        return {
            "task_recommendations": recommendations,
            "style_preferences": _learner.get_style_preferences(),
        }

    @router.post("/analyze")
    async def analyze_preferences(query: InteractionQuery):
        """Analyze collected preferences."""
        prefs = _learner.export_preferences()
        model_stats = prefs.get("model_stats", {})

        analysis = {
            "total_models": len(model_stats),
            "models": [],
        }

        for model, stats in model_stats.items():
            if query.model and model != query.model:
                continue

            total_uses = stats.get("total_uses", 0)
            if total_uses < query.min_interactions:
                continue

            positive = stats.get("positive_feedback", 0)
            negative = stats.get("negative_feedback", 0)
            total_feedback = positive + negative

            analysis["models"].append({
                "model": model,
                "total_uses": total_uses,
                "positive_feedback": positive,
                "negative_feedback": negative,
                "satisfaction_rate": positive / total_feedback if total_feedback > 0 else 0.5,
                "avg_latency_ms": stats.get("avg_latency_ms", 0),
                "last_used": stats.get("last_used"),
            })

        # Sort by satisfaction rate
        analysis["models"].sort(
            key=lambda x: (x["satisfaction_rate"], x["total_uses"]),
            reverse=True
        )

        return analysis

    @router.post("/simulate")
    async def simulate_interaction(
        prompt: str,
        model: str,
        latency_ms: int = 1000,
        feedback: Optional[str] = None
    ):
        """
        Simulate an interaction for testing.
        Useful for bootstrapping preference data.
        """
        try:
            feedback_type = FeedbackType(feedback) if feedback else None
        except ValueError:
            feedback_type = None

        interaction = _learner.record_interaction(
            prompt=prompt,
            model=model,
            response="[simulated response]",
            latency_ms=latency_ms,
            feedback=feedback_type,
        )

        return {
            "status": "simulated",
            "interaction_id": interaction.id,
            "task_type": interaction.task_type,
        }

    @router.post("/sync-from-litellm")
    async def sync_from_litellm(limit: int = 100, since_hours: int = 24):
        """
        Sync usage data from LiteLLM SpendLogs database.

        This is the primary method for collecting preference data.
        Reads from LiteLLM's PostgreSQL database directly.

        Args:
            limit: Max records to sync (default 100)
            since_hours: Only sync records from last N hours (default 24)
        """
        global _last_sync_timestamp
        import asyncpg

        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Database connection failed: {str(e)}"
            )

        try:
            # Query recent SpendLogs
            query = '''
                SELECT
                    request_id,
                    call_type,
                    model,
                    total_tokens,
                    prompt_tokens,
                    completion_tokens,
                    "startTime",
                    "endTime",
                    api_base,
                    metadata
                FROM "LiteLLM_SpendLogs"
                WHERE "startTime" > NOW() - INTERVAL '%s hours'
                  AND call_type IN ('completion', 'acompletion')
                ORDER BY "startTime" DESC
                LIMIT $1
            ''' % since_hours

            rows = await conn.fetch(query, limit)
            synced_count = 0
            skipped_count = 0

            for row in rows:
                request_id = row["request_id"]
                model = row["model"] or "unknown"
                start_time = row["startTime"]
                end_time = row["endTime"]

                # Calculate latency
                if start_time and end_time:
                    latency_ms = int((end_time - start_time).total_seconds() * 1000)
                else:
                    latency_ms = 0

                # Extract prompt from metadata if available
                metadata = row["metadata"] or {}
                prompt = "[from litellm sync]"

                # Record the interaction
                try:
                    _learner.record_interaction(
                        prompt=prompt,
                        model=model,
                        response=f"[tokens: {row['completion_tokens']}]",
                        latency_ms=latency_ms,
                        feedback=None,
                    )
                    synced_count += 1
                except Exception:
                    skipped_count += 1

            _last_sync_timestamp = datetime.utcnow()

            return {
                "status": "synced",
                "records_synced": synced_count,
                "records_skipped": skipped_count,
                "since_hours": since_hours,
                "timestamp": _last_sync_timestamp.isoformat(),
            }

        finally:
            await conn.close()

    @router.get("/litellm-stats")
    async def get_litellm_stats():
        """
        Get usage statistics directly from LiteLLM database.

        This provides raw usage data before preference processing.
        """
        import asyncpg

        try:
            conn = await asyncpg.connect(DATABASE_URL)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Database connection failed: {str(e)}"
            )

        try:
            # Get model usage summary
            query = '''
                SELECT
                    model,
                    COUNT(*) as request_count,
                    SUM(total_tokens) as total_tokens,
                    AVG(EXTRACT(EPOCH FROM ("endTime" - "startTime")) * 1000)::int as avg_latency_ms,
                    MAX("startTime") as last_used
                FROM "LiteLLM_SpendLogs"
                WHERE call_type IN ('completion', 'acompletion')
                GROUP BY model
                ORDER BY request_count DESC
            '''

            rows = await conn.fetch(query)

            models = []
            for row in rows:
                models.append({
                    "model": row["model"],
                    "request_count": row["request_count"],
                    "total_tokens": row["total_tokens"] or 0,
                    "avg_latency_ms": row["avg_latency_ms"] or 0,
                    "last_used": row["last_used"].isoformat() if row["last_used"] else None,
                })

            # Get total count
            total_query = 'SELECT COUNT(*) FROM "LiteLLM_SpendLogs"'
            total_count = await conn.fetchval(total_query)

            return {
                "total_requests": total_count,
                "models": models,
                "last_sync": _last_sync_timestamp.isoformat() if _last_sync_timestamp else None,
            }

        finally:
            await conn.close()

    return router


# For direct API import
def get_learner() -> PreferenceLearner:
    """Get the shared preference learner instance."""
    return _learner
