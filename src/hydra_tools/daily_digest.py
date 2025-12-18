"""
Daily Digest Generator

Compiles a daily summary of Hydra cluster activity including:
- Overnight work results and task completions
- Cluster health summary
- Resource usage trends
- Pending task count and priorities
- Notable events and alerts

Can be triggered manually or scheduled via n8n/cron.

Endpoints:
    GET /digest/daily - Generate daily digest
    GET /digest/overnight - Summary of overnight activity
    GET /digest/trends - Resource and performance trends
    POST /digest/send - Generate and send digest (to Discord/email)
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digest", tags=["digest"])

# =============================================================================
# CONFIGURATION
# =============================================================================

HYDRA_API_URL = os.environ.get("HYDRA_API_URL", "http://localhost:8700")
HYDRA_API_KEY = os.environ.get("HYDRA_API_KEY", "hydra-dev-key")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://192.168.1.244:9090")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


# =============================================================================
# DATA MODELS
# =============================================================================

class DigestSection(BaseModel):
    title: str
    content: str
    status: str  # good, warning, critical
    metrics: Optional[Dict[str, Any]] = None


class DailyDigest(BaseModel):
    generated_at: str
    period_start: str
    period_end: str
    summary: str
    sections: List[DigestSection]
    overall_status: str
    action_items: List[str]


class TrendData(BaseModel):
    metric: str
    current: float
    previous: float
    change_percent: float
    trend: str  # up, down, stable


# =============================================================================
# DATA COLLECTORS
# =============================================================================

async def get_cluster_health() -> Dict[str, Any]:
    """Get cluster health status."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/health/cluster",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get cluster health: {e}")
    return {"status": "unknown", "error": "Could not fetch cluster health"}


async def get_queue_stats() -> Dict[str, Any]:
    """Get autonomous queue statistics."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/autonomous/queue/stats",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
    return {}


async def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/autonomous/scheduler/status",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
    return {}


async def get_recent_tasks(hours: int = 24) -> List[Dict[str, Any]]:
    """Get tasks completed in the last N hours."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/autonomous/queue",
                params={"status": "completed", "limit": 50},
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                all_tasks = response.json()
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                return [t for t in all_tasks if t.get("completed_at", "") >= cutoff]
    except Exception as e:
        logger.error(f"Failed to get recent tasks: {e}")
    return []


async def get_benchmark_results() -> Dict[str, Any]:
    """Get latest benchmark results."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/self-improvement/benchmarks/latest",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get benchmark results: {e}")
    return {}


async def get_resource_summary() -> Dict[str, Any]:
    """Get cluster resource summary."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/autonomous/resources/summary",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get resource summary: {e}")
    return {}


async def get_alerts_summary() -> Dict[str, Any]:
    """Get active alerts summary."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/alerts/active",
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
    return {"alerts": []}


async def get_prometheus_metric(query: str) -> Optional[float]:
    """Query a Prometheus metric."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    return float(results[0]["value"][1])
    except Exception as e:
        logger.warning(f"Prometheus query failed: {query} - {e}")
    return None


async def get_feedback_summary() -> Dict[str, Any]:
    """Get human feedback summary."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HYDRA_API_URL}/feedback/stats",
                params={"days": 1},
                headers={"X-API-Key": HYDRA_API_KEY},
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get feedback summary: {e}")
    return {}


# =============================================================================
# DIGEST GENERATION
# =============================================================================

def determine_status(value: float, warning_threshold: float, critical_threshold: float, higher_is_better: bool = True) -> str:
    """Determine status based on thresholds."""
    if higher_is_better:
        if value >= warning_threshold:
            return "good"
        elif value >= critical_threshold:
            return "warning"
        return "critical"
    else:
        if value <= warning_threshold:
            return "good"
        elif value <= critical_threshold:
            return "warning"
        return "critical"


async def generate_digest(hours: int = 24) -> DailyDigest:
    """Generate a comprehensive daily digest."""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=hours)

    sections = []
    action_items = []
    overall_status = "good"

    # 1. Cluster Health Section
    health = await get_cluster_health()
    services = health.get("services", [])
    healthy_count = sum(1 for s in services if s.get("status") == "healthy")
    total_services = len(services) if services else 1
    health_pct = (healthy_count / total_services * 100) if total_services else 0

    health_status = determine_status(health_pct, 90, 70)
    if health_status != "good":
        overall_status = health_status
        unhealthy = [s["name"] for s in services if s.get("status") != "healthy"]
        action_items.append(f"Check unhealthy services: {', '.join(unhealthy[:5])}")

    sections.append(DigestSection(
        title="Cluster Health",
        content=f"{healthy_count}/{total_services} services healthy ({health_pct:.0f}%)",
        status=health_status,
        metrics={"healthy": healthy_count, "total": total_services, "percentage": health_pct},
    ))

    # 2. Autonomous Work Section
    queue_stats = await get_queue_stats()
    scheduler = await get_scheduler_status()
    recent_tasks = await get_recent_tasks(hours)

    completed = len(recent_tasks)
    pending = queue_stats.get("pending", 0)
    failed = queue_stats.get("failed_today", 0)
    scheduler_running = scheduler.get("running", False)

    work_content = f"Completed: {completed} tasks | Pending: {pending} | Failed: {failed}"
    if not scheduler_running:
        work_content += " | ⚠️ Scheduler STOPPED"
        action_items.append("Start the autonomous scheduler")

    work_status = "good"
    if failed > 0:
        work_status = "warning"
        action_items.append(f"Review {failed} failed tasks")
    if not scheduler_running:
        work_status = "warning" if work_status == "good" else work_status

    sections.append(DigestSection(
        title="Autonomous Work",
        content=work_content,
        status=work_status,
        metrics={
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "scheduler_running": scheduler_running,
        },
    ))

    # 3. Resource Usage Section
    resources = await get_resource_summary()
    gpu_util = float(resources.get("cluster_util", "0%").replace("%", ""))
    free_vram = resources.get("free_vram_gb", 0)
    available_gpus = resources.get("available_gpus", "0/0")

    resource_status = "good"
    if gpu_util > 80:
        resource_status = "warning"
        action_items.append("High GPU utilization - consider scaling or prioritizing tasks")

    sections.append(DigestSection(
        title="Resources",
        content=f"GPU Util: {gpu_util:.0f}% | Free VRAM: {free_vram:.1f}GB | Available: {available_gpus}",
        status=resource_status,
        metrics={
            "gpu_util_percent": gpu_util,
            "free_vram_gb": free_vram,
            "available_gpus": available_gpus,
        },
    ))

    # 4. Benchmark Score Section
    benchmark = await get_benchmark_results()
    if benchmark.get("overall_score"):
        score = benchmark.get("overall_score", 0)
        bench_status = determine_status(score, 90, 70)

        sections.append(DigestSection(
            title="System Score",
            content=f"Benchmark: {score:.1f}%",
            status=bench_status,
            metrics={"overall_score": score, "scores": benchmark.get("scores", {})},
        ))

    # 5. Alerts Section
    alerts = await get_alerts_summary()
    active_alerts = alerts.get("alerts", [])
    critical_alerts = [a for a in active_alerts if a.get("severity") == "critical"]
    warning_alerts = [a for a in active_alerts if a.get("severity") == "warning"]

    alert_status = "good"
    alert_content = "No active alerts"
    if critical_alerts:
        alert_status = "critical"
        overall_status = "critical"
        alert_content = f"🔴 {len(critical_alerts)} critical, {len(warning_alerts)} warning alerts"
        action_items.append(f"Address {len(critical_alerts)} critical alerts immediately")
    elif warning_alerts:
        alert_status = "warning"
        if overall_status == "good":
            overall_status = "warning"
        alert_content = f"🟡 {len(warning_alerts)} warning alerts"

    sections.append(DigestSection(
        title="Alerts",
        content=alert_content,
        status=alert_status,
        metrics={"critical": len(critical_alerts), "warning": len(warning_alerts)},
    ))

    # 6. Human Feedback Section (if any)
    feedback = await get_feedback_summary()
    if feedback.get("total_feedback", 0) > 0:
        total_fb = feedback.get("total_feedback", 0)
        avg_rating = feedback.get("avg_asset_rating", 0)
        regen_needed = feedback.get("needs_regeneration", 0)

        fb_status = "good"
        if avg_rating < 3:
            fb_status = "warning"
            action_items.append("Review low-rated assets for quality issues")
        if regen_needed > 0:
            action_items.append(f"{regen_needed} assets need regeneration")

        sections.append(DigestSection(
            title="Feedback",
            content=f"Collected: {total_fb} | Avg Rating: {avg_rating:.1f}/5 | Regen Queue: {regen_needed}",
            status=fb_status,
            metrics=feedback,
        ))

    # Generate summary
    summary_parts = []
    if overall_status == "good":
        summary_parts.append("All systems operating normally.")
    elif overall_status == "warning":
        summary_parts.append("Some items need attention.")
    else:
        summary_parts.append("Critical issues require immediate action.")

    if completed > 0:
        summary_parts.append(f"{completed} tasks completed in the last {hours}h.")
    if pending > 0:
        summary_parts.append(f"{pending} tasks pending.")

    return DailyDigest(
        generated_at=now.isoformat(),
        period_start=period_start.isoformat(),
        period_end=now.isoformat(),
        summary=" ".join(summary_parts),
        sections=sections,
        overall_status=overall_status,
        action_items=action_items,
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/daily", response_model=DailyDigest)
async def get_daily_digest():
    """Generate a comprehensive daily digest."""
    return await generate_digest(hours=24)


@router.get("/overnight")
async def get_overnight_summary():
    """Get summary of overnight activity (last 8 hours)."""
    return await generate_digest(hours=8)


@router.get("/weekly")
async def get_weekly_digest():
    """Get a weekly summary."""
    return await generate_digest(hours=168)


@router.get("/trends")
async def get_trends(days: int = Query(7, description="Days to analyze")):
    """Get resource and performance trends."""
    trends = []

    # GPU utilization trend (compare last 24h vs previous 24h)
    current_gpu = await get_prometheus_metric(
        'avg_over_time(DCGM_FI_DEV_GPU_UTIL[24h])'
    )
    previous_gpu = await get_prometheus_metric(
        'avg_over_time(DCGM_FI_DEV_GPU_UTIL[24h] offset 24h)'
    )

    if current_gpu is not None and previous_gpu is not None and previous_gpu > 0:
        change = ((current_gpu - previous_gpu) / previous_gpu) * 100
        trends.append(TrendData(
            metric="GPU Utilization",
            current=round(current_gpu, 1),
            previous=round(previous_gpu, 1),
            change_percent=round(change, 1),
            trend="up" if change > 5 else "down" if change < -5 else "stable",
        ))

    # Memory usage trend
    current_mem = await get_prometheus_metric(
        'avg_over_time(node_memory_MemAvailable_bytes{instance=~"192.168.1.244.*"}[24h])'
    )
    previous_mem = await get_prometheus_metric(
        'avg_over_time(node_memory_MemAvailable_bytes{instance=~"192.168.1.244.*"}[24h] offset 24h)'
    )

    if current_mem is not None and previous_mem is not None and previous_mem > 0:
        current_gb = current_mem / (1024**3)
        previous_gb = previous_mem / (1024**3)
        change = ((current_gb - previous_gb) / previous_gb) * 100
        trends.append(TrendData(
            metric="Available Memory (GB)",
            current=round(current_gb, 1),
            previous=round(previous_gb, 1),
            change_percent=round(change, 1),
            trend="up" if change > 5 else "down" if change < -5 else "stable",
        ))

    return {
        "period_days": days,
        "trends": [t.model_dump() for t in trends],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/send")
async def send_digest(
    background_tasks: BackgroundTasks,
    channel: str = Query("discord", description="Channel: discord, email, both"),
):
    """Generate and send digest to configured channels."""
    digest = await generate_digest(hours=24)

    async def send_to_discord():
        if not DISCORD_WEBHOOK_URL:
            logger.warning("Discord webhook URL not configured")
            return False

        # Format for Discord
        status_emoji = {
            "good": "🟢",
            "warning": "🟡",
            "critical": "🔴",
        }

        embed = {
            "title": f"{status_emoji.get(digest.overall_status, '⚪')} Hydra Daily Digest",
            "description": digest.summary,
            "color": {
                "good": 0x00FF00,
                "warning": 0xFFFF00,
                "critical": 0xFF0000,
            }.get(digest.overall_status, 0x808080),
            "fields": [],
            "timestamp": digest.generated_at,
            "footer": {"text": "Hydra Autonomous System"},
        }

        for section in digest.sections:
            embed["fields"].append({
                "name": f"{status_emoji.get(section.status, '⚪')} {section.title}",
                "value": section.content,
                "inline": True,
            })

        if digest.action_items:
            embed["fields"].append({
                "name": "📋 Action Items",
                "value": "\n".join(f"• {item}" for item in digest.action_items[:5]),
                "inline": False,
            })

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DISCORD_WEBHOOK_URL,
                    json={"embeds": [embed]},
                )
                return response.status_code == 204
        except Exception as e:
            logger.error(f"Failed to send Discord digest: {e}")
            return False

    if channel in ("discord", "both"):
        background_tasks.add_task(send_to_discord)

    return {
        "status": "sending",
        "channel": channel,
        "digest": digest.model_dump(),
    }


@router.get("/quick")
async def get_quick_summary():
    """Get a quick one-line status summary."""
    health = await get_cluster_health()
    queue = await get_queue_stats()
    scheduler = await get_scheduler_status()

    services = health.get("services", [])
    healthy = sum(1 for s in services if s.get("status") == "healthy")
    total = len(services)

    parts = [
        f"Health: {healthy}/{total}",
        f"Pending: {queue.get('pending', 0)}",
        f"Scheduler: {'✅' if scheduler.get('running') else '❌'}",
    ]

    return {
        "summary": " | ".join(parts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "good" if healthy == total and scheduler.get("running") else "warning",
    }


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_daily_digest_router() -> APIRouter:
    """Create and return the daily digest router."""
    return router
