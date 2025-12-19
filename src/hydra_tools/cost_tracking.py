"""
Cost Tracking Module for Hydra AI System

Tracks inference costs across all models and agents:
- Per-model token usage
- Per-agent task costs
- Local vs cloud breakdown
- Daily/weekly/monthly summaries
- Cost optimization suggestions

Author: Hydra Autonomous Caretaker
Created: 2025-12-19
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

TOKENS_TOTAL = Counter(
    "hydra_tokens_total",
    "Total tokens processed",
    ["model", "provider", "direction"]  # direction: input/output
)

COST_TOTAL = Counter(
    "hydra_cost_usd_total",
    "Total cost in USD",
    ["model", "provider"]
)

COST_DAILY = Gauge(
    "hydra_cost_usd_daily",
    "Cost in USD for today",
    ["provider"]
)


# =============================================================================
# Model Pricing (per 1M tokens)
# =============================================================================

MODEL_PRICING = {
    # Cloud APIs
    "claude-sonnet-4": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-opus-4": {"input": 15.00, "output": 75.00, "provider": "anthropic"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "grok-3": {"input": 3.00, "output": 15.00, "provider": "xai"},
    "grok-4": {"input": 5.00, "output": 20.00, "provider": "xai"},
    "perplexity-sonar": {"input": 1.00, "output": 1.00, "provider": "perplexity"},
    "perplexity-deep": {"input": 2.00, "output": 8.00, "provider": "perplexity"},
    "gemini-pro": {"input": 1.25, "output": 5.00, "provider": "google"},
    "gemini-flash": {"input": 0.075, "output": 0.30, "provider": "google"},

    # Local models (electricity cost estimate: ~$0.10/hour of GPU time)
    # Approximated as $0.002 per 1k output tokens for 70B models
    "tabby": {"input": 0.00, "output": 0.002, "provider": "local"},
    "midnight-miqu-70b": {"input": 0.00, "output": 0.002, "provider": "local"},
    "qwen-coder-32b": {"input": 0.00, "output": 0.001, "provider": "local"},
    "qwen2.5-7b": {"input": 0.00, "output": 0.0005, "provider": "local"},
    "dolphin-70b": {"input": 0.00, "output": 0.003, "provider": "local"},  # Slower due to CPU offload
    "deepseek-r1-8b": {"input": 0.00, "output": 0.0005, "provider": "local"},

    # Default for unknown models
    "default": {"input": 1.00, "output": 2.00, "provider": "unknown"},
}


@dataclass
class TokenUsage:
    """Record of token usage for a single request."""
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent: Optional[str] = None
    task_type: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class CostSummary:
    """Cost summary for a time period."""
    period: str  # "day", "week", "month"
    start_date: datetime
    end_date: datetime
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    by_model: Dict[str, float]
    by_provider: Dict[str, float]
    by_agent: Dict[str, float]
    request_count: int
    avg_cost_per_request: float


class CostTracker:
    """
    Tracks and analyzes inference costs across the Hydra system.
    """

    def __init__(self, db_path: str = "/mnt/user/appdata/hydra-dev/data/cost_tracking.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for cost tracking."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                agent TEXT,
                task_type TEXT,
                request_id TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON token_usage(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model ON token_usage(model)
        """)

        conn.commit()
        conn.close()

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for a request."""
        # Normalize model name
        model_lower = model.lower().replace("/", "-").replace("_", "-")

        # Find pricing
        pricing = MODEL_PRICING.get(model_lower, MODEL_PRICING["default"])

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> TokenUsage:
        """Record token usage for a request."""
        # Determine provider
        model_lower = model.lower().replace("/", "-").replace("_", "-")
        pricing = MODEL_PRICING.get(model_lower, MODEL_PRICING["default"])
        provider = pricing.get("provider", "unknown")

        # Calculate cost
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        usage = TokenUsage(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            agent=agent,
            task_type=task_type,
            request_id=request_id,
        )

        # Store in database
        self._store_usage(usage)

        # Update Prometheus metrics
        TOKENS_TOTAL.labels(model=model, provider=provider, direction="input").inc(input_tokens)
        TOKENS_TOTAL.labels(model=model, provider=provider, direction="output").inc(output_tokens)
        COST_TOTAL.labels(model=model, provider=provider).inc(cost)

        return usage

    def _store_usage(self, usage: TokenUsage):
        """Store usage record in database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO token_usage
            (timestamp, model, provider, input_tokens, output_tokens, cost_usd, agent, task_type, request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usage.timestamp.isoformat(),
            usage.model,
            usage.provider,
            usage.input_tokens,
            usage.output_tokens,
            usage.cost_usd,
            usage.agent,
            usage.task_type,
            usage.request_id,
        ))

        conn.commit()
        conn.close()

    def get_summary(
        self,
        period: str = "day",
        start_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Get cost summary for a time period."""
        now = datetime.utcnow()

        if period == "day":
            if start_date is None:
                start_date = datetime(now.year, now.month, now.day)
            end_date = start_date + timedelta(days=1)
        elif period == "week":
            if start_date is None:
                start_date = now - timedelta(days=now.weekday())
                start_date = datetime(start_date.year, start_date.month, start_date.day)
            end_date = start_date + timedelta(weeks=1)
        elif period == "month":
            if start_date is None:
                start_date = datetime(now.year, now.month, 1)
            # First day of next month
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1)
            else:
                end_date = datetime(now.year, now.month + 1, 1)
        else:
            raise ValueError(f"Invalid period: {period}")

        # Query database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(cost_usd) as total_cost,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                COUNT(*) as request_count
            FROM token_usage
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_date.isoformat(), end_date.isoformat()))

        row = cursor.fetchone()
        total_cost = row[0] or 0
        total_input = row[1] or 0
        total_output = row[2] or 0
        request_count = row[3] or 0

        # By model
        cursor.execute("""
            SELECT model, SUM(cost_usd) as cost
            FROM token_usage
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY model
            ORDER BY cost DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        by_model = {row[0]: row[1] for row in cursor.fetchall()}

        # By provider
        cursor.execute("""
            SELECT provider, SUM(cost_usd) as cost
            FROM token_usage
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY provider
            ORDER BY cost DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        by_provider = {row[0]: row[1] for row in cursor.fetchall()}

        # By agent
        cursor.execute("""
            SELECT agent, SUM(cost_usd) as cost
            FROM token_usage
            WHERE timestamp >= ? AND timestamp < ? AND agent IS NOT NULL
            GROUP BY agent
            ORDER BY cost DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        by_agent = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return CostSummary(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_cost_usd=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            by_model=by_model,
            by_provider=by_provider,
            by_agent=by_agent,
            request_count=request_count,
            avg_cost_per_request=total_cost / request_count if request_count > 0 else 0,
        )

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get cost optimization suggestions based on usage patterns."""
        suggestions = []

        # Get last 7 days summary
        week_summary = self.get_summary("week")

        # Check local vs cloud ratio
        local_cost = week_summary.by_provider.get("local", 0)
        cloud_cost = sum(
            cost for provider, cost in week_summary.by_provider.items()
            if provider != "local"
        )

        if cloud_cost > local_cost * 2:
            suggestions.append({
                "type": "use_more_local",
                "priority": "high",
                "message": f"Cloud spending (${cloud_cost:.2f}) is >2x local (${local_cost:.2f}). Consider routing more tasks to local models.",
                "potential_savings": f"${(cloud_cost * 0.5):.2f}/week",
            })

        # Check for expensive model overuse
        for model, cost in week_summary.by_model.items():
            if "opus" in model.lower() and cost > 10:
                suggestions.append({
                    "type": "downgrade_model",
                    "priority": "medium",
                    "message": f"High Opus usage (${cost:.2f}/week). Consider using Sonnet for simpler tasks.",
                    "potential_savings": f"${(cost * 0.7):.2f}/week",
                })

        # Check for inefficient agents
        for agent, cost in week_summary.by_agent.items():
            if cost > 5:
                suggestions.append({
                    "type": "optimize_agent",
                    "priority": "low",
                    "message": f"Agent '{agent}' spent ${cost:.2f} this week. Review for optimization opportunities.",
                })

        # Check overall spending trend
        if week_summary.total_cost_usd > 50:
            suggestions.append({
                "type": "budget_alert",
                "priority": "high",
                "message": f"Weekly spending (${week_summary.total_cost_usd:.2f}) exceeds $50. Review usage patterns.",
            })

        return suggestions

    def get_recent_usage(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent usage records."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, model, provider, input_tokens, output_tokens, cost_usd, agent, task_type
            FROM token_usage
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        results = [
            {
                "timestamp": row[0],
                "model": row[1],
                "provider": row[2],
                "input_tokens": row[3],
                "output_tokens": row[4],
                "cost_usd": row[5],
                "agent": row[6],
                "task_type": row[7],
            }
            for row in cursor.fetchall()
        ]

        conn.close()
        return results


# =============================================================================
# Global Instance
# =============================================================================

_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


# =============================================================================
# FastAPI Router
# =============================================================================

def create_cost_tracking_router():
    """Create FastAPI router for cost tracking endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/costs", tags=["cost-tracking"])

    class RecordUsageRequest(BaseModel):
        model: str
        input_tokens: int
        output_tokens: int
        agent: Optional[str] = None
        task_type: Optional[str] = None
        request_id: Optional[str] = None

    @router.get("/summary/{period}")
    async def get_cost_summary(period: str = "day"):
        """Get cost summary for a period (day/week/month)."""
        tracker = get_cost_tracker()
        summary = tracker.get_summary(period)

        return {
            "period": summary.period,
            "start_date": summary.start_date.isoformat(),
            "end_date": summary.end_date.isoformat(),
            "total_cost_usd": round(summary.total_cost_usd, 4),
            "total_tokens": summary.total_input_tokens + summary.total_output_tokens,
            "input_tokens": summary.total_input_tokens,
            "output_tokens": summary.total_output_tokens,
            "request_count": summary.request_count,
            "avg_cost_per_request": round(summary.avg_cost_per_request, 6),
            "by_model": summary.by_model,
            "by_provider": summary.by_provider,
            "by_agent": summary.by_agent,
        }

    @router.get("/recent")
    async def get_recent_usage(limit: int = 50):
        """Get recent usage records."""
        tracker = get_cost_tracker()
        return {"usage": tracker.get_recent_usage(limit)}

    @router.get("/suggestions")
    async def get_optimization_suggestions():
        """Get cost optimization suggestions."""
        tracker = get_cost_tracker()
        return {"suggestions": tracker.get_optimization_suggestions()}

    @router.post("/record")
    async def record_usage(request: RecordUsageRequest):
        """Record token usage for a request."""
        tracker = get_cost_tracker()
        usage = tracker.record_usage(
            model=request.model,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            agent=request.agent,
            task_type=request.task_type,
            request_id=request.request_id,
        )

        return {
            "cost_usd": usage.cost_usd,
            "model": usage.model,
            "provider": usage.provider,
            "recorded_at": usage.timestamp.isoformat(),
        }

    @router.get("/pricing")
    async def get_model_pricing():
        """Get pricing for all known models."""
        return {"pricing": MODEL_PRICING}

    @router.get("/dashboard")
    async def cost_dashboard():
        """Get dashboard data combining all cost metrics."""
        tracker = get_cost_tracker()

        day_summary = tracker.get_summary("day")
        week_summary = tracker.get_summary("week")
        month_summary = tracker.get_summary("month")
        suggestions = tracker.get_optimization_suggestions()

        return {
            "today": {
                "cost_usd": round(day_summary.total_cost_usd, 4),
                "requests": day_summary.request_count,
                "tokens": day_summary.total_input_tokens + day_summary.total_output_tokens,
            },
            "this_week": {
                "cost_usd": round(week_summary.total_cost_usd, 4),
                "requests": week_summary.request_count,
                "tokens": week_summary.total_input_tokens + week_summary.total_output_tokens,
            },
            "this_month": {
                "cost_usd": round(month_summary.total_cost_usd, 4),
                "requests": month_summary.request_count,
                "tokens": month_summary.total_input_tokens + month_summary.total_output_tokens,
            },
            "by_provider": week_summary.by_provider,
            "top_models": dict(list(week_summary.by_model.items())[:5]),
            "top_agents": dict(list(week_summary.by_agent.items())[:5]),
            "suggestions": suggestions[:3],
            "local_ratio": (
                week_summary.by_provider.get("local", 0) /
                max(sum(week_summary.by_provider.values()), 0.01)
            ),
        }

    return router
