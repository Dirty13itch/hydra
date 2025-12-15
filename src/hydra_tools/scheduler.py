"""
Hydra Crew Scheduler - Background task for autonomous crew scheduling.

Runs as a background task within the Hydra Tools API.
Triggers CrewAI crews on schedule without external dependencies.

Schedules:
- Monitoring: Daily at 6:00 AM CST
- Research: Monday at 2:00 AM CST
- Maintenance: Sunday at 3:00 AM CST
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Chicago")
CREWAI_URL = "http://192.168.1.244:8500"


class ScheduleFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    HOURLY = "hourly"


@dataclass
class CrewSchedule:
    """Configuration for a scheduled crew run."""
    crew_name: str
    frequency: ScheduleFrequency
    hour: int
    minute: int = 0
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    enabled: bool = True
    last_run: Optional[datetime] = None
    topic_rotation: Optional[List[str]] = None


@dataclass
class SchedulerState:
    """Current state of the scheduler."""
    running: bool = False
    schedules: Dict[str, CrewSchedule] = field(default_factory=dict)
    run_history: List[Dict[str, Any]] = field(default_factory=list)
    task: Optional[asyncio.Task] = None


# Default schedules
DEFAULT_SCHEDULES = {
    "monitoring": CrewSchedule(
        crew_name="monitoring",
        frequency=ScheduleFrequency.DAILY,
        hour=6,
        minute=0,
    ),
    "research": CrewSchedule(
        crew_name="research",
        frequency=ScheduleFrequency.WEEKLY,
        hour=2,
        minute=0,
        day_of_week=0,  # Monday
        topic_rotation=[
            "Latest developments in local LLM inference optimization 2024",
            "ExLlamaV2 tensor parallelism and performance tuning",
            "Home automation AI integration best practices",
            "Vector database optimization for RAG systems",
        ],
    ),
    "maintenance": CrewSchedule(
        crew_name="maintenance",
        frequency=ScheduleFrequency.WEEKLY,
        hour=3,
        minute=0,
        day_of_week=6,  # Sunday
    ),
}


class CrewScheduler:
    """Background scheduler for CrewAI crews."""

    def __init__(self, activity_callback=None):
        self.state = SchedulerState(schedules=DEFAULT_SCHEDULES.copy())
        self.activity_callback = activity_callback

    async def run_crew(self, schedule: CrewSchedule) -> Dict[str, Any]:
        """Execute a crew and return the result."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{CREWAI_URL}/run/{schedule.crew_name}"

            # Handle topic rotation for research crew
            payload = {}
            if schedule.topic_rotation:
                week_num = datetime.now(TIMEZONE).isocalendar()[1]
                topic = schedule.topic_rotation[week_num % len(schedule.topic_rotation)]
                payload["topic"] = topic
                logger.info(f"Research topic this week: {topic}")

            try:
                logger.info(f"Triggering {schedule.crew_name} crew...")
                response = await client.post(url, json=payload)
                result = response.json()
                logger.info(f"{schedule.crew_name} crew completed: {result.get('status', 'unknown')}")

                # Update last run
                schedule.last_run = datetime.now(TIMEZONE)

                # Log to history
                self.state.run_history.append({
                    "crew": schedule.crew_name,
                    "timestamp": schedule.last_run.isoformat(),
                    "status": result.get("status", "unknown"),
                    "topic": payload.get("topic"),
                })

                # Keep only last 100 runs
                if len(self.state.run_history) > 100:
                    self.state.run_history = self.state.run_history[-100:]

                return result

            except Exception as e:
                logger.error(f"Failed to run {schedule.crew_name} crew: {e}")
                return {"status": "error", "error": str(e)}

    def should_run_now(self, schedule: CrewSchedule) -> bool:
        """Check if a crew should run at the current time."""
        if not schedule.enabled:
            return False

        now = datetime.now(TIMEZONE)

        # Check if we're in the right minute
        if now.minute != schedule.minute:
            return False

        # Check if we're in the right hour
        if now.hour != schedule.hour:
            return False

        # For weekly schedules, check day
        if schedule.frequency == ScheduleFrequency.WEEKLY:
            if schedule.day_of_week is not None and now.weekday() != schedule.day_of_week:
                return False

        # Prevent double runs (must be at least 55 minutes since last run)
        if schedule.last_run:
            if (now - schedule.last_run.replace(tzinfo=TIMEZONE)) < timedelta(minutes=55):
                return False

        return True

    async def check_schedules(self):
        """Check all schedules and run crews that are due."""
        for name, schedule in self.state.schedules.items():
            if self.should_run_now(schedule):
                logger.info(f"Schedule triggered for {name}")
                result = await self.run_crew(schedule)

                # Log activity if callback provided
                if self.activity_callback:
                    try:
                        await self.activity_callback(
                            source="hydra-scheduler",
                            action=f"crew_run_{name}",
                            action_type="scheduled",
                            target=f"crewai-{name}",
                            result=result.get("status", "unknown"),
                            decision_reason=f"Scheduled {name} crew execution at {schedule.hour:02d}:{schedule.minute:02d}",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log activity: {e}")

    async def run_loop(self):
        """Main scheduler loop."""
        logger.info("Hydra Crew Scheduler starting...")
        logger.info(f"Timezone: {TIMEZONE}")

        for name, schedule in self.state.schedules.items():
            if schedule.frequency == ScheduleFrequency.DAILY:
                logger.info(f"  {name}: Daily at {schedule.hour:02d}:{schedule.minute:02d}")
            elif schedule.frequency == ScheduleFrequency.WEEKLY:
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_name = days[schedule.day_of_week] if schedule.day_of_week is not None else "?"
                logger.info(f"  {name}: {day_name} at {schedule.hour:02d}:{schedule.minute:02d}")

        self.state.running = True

        while self.state.running:
            try:
                await self.check_schedules()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            # Check every minute
            await asyncio.sleep(60)

    def start(self) -> asyncio.Task:
        """Start the scheduler as a background task."""
        if self.state.task and not self.state.task.done():
            logger.warning("Scheduler already running")
            return self.state.task

        self.state.task = asyncio.create_task(self.run_loop())
        return self.state.task

    def stop(self):
        """Stop the scheduler."""
        self.state.running = False
        if self.state.task:
            self.state.task.cancel()

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        now = datetime.now(TIMEZONE)

        schedules_info = {}
        for name, schedule in self.state.schedules.items():
            next_run = self._calculate_next_run(schedule, now)
            schedules_info[name] = {
                "enabled": schedule.enabled,
                "frequency": schedule.frequency.value,
                "schedule": f"{schedule.hour:02d}:{schedule.minute:02d}",
                "day_of_week": schedule.day_of_week,
                "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
                "next_run": next_run.isoformat() if next_run else None,
            }

        return {
            "running": self.state.running,
            "timezone": str(TIMEZONE),
            "current_time": now.isoformat(),
            "schedules": schedules_info,
            "recent_runs": self.state.run_history[-10:],
        }

    def _calculate_next_run(self, schedule: CrewSchedule, now: datetime) -> Optional[datetime]:
        """Calculate the next scheduled run time."""
        if not schedule.enabled:
            return None

        # Start with today at scheduled time
        next_run = now.replace(
            hour=schedule.hour,
            minute=schedule.minute,
            second=0,
            microsecond=0
        )

        if schedule.frequency == ScheduleFrequency.DAILY:
            if next_run <= now:
                next_run += timedelta(days=1)
        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            if schedule.day_of_week is not None:
                days_ahead = schedule.day_of_week - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and next_run <= now):
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)

        return next_run

    async def trigger_crew(self, crew_name: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger a crew run."""
        if crew_name not in self.state.schedules:
            return {"status": "error", "error": f"Unknown crew: {crew_name}"}

        schedule = self.state.schedules[crew_name]

        # Override topic if provided
        original_topic = schedule.topic_rotation
        if topic:
            schedule.topic_rotation = [topic]

        result = await self.run_crew(schedule)

        # Restore original topic
        schedule.topic_rotation = original_topic

        return result


# Global scheduler instance
_scheduler: Optional[CrewScheduler] = None


def get_scheduler() -> CrewScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CrewScheduler()
    return _scheduler


def create_scheduler_router():
    """Create FastAPI router for scheduler endpoints."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/scheduler", tags=["scheduler"])

    @router.get("/status")
    async def get_status():
        """Get scheduler status and upcoming runs."""
        return get_scheduler().get_status()

    @router.post("/trigger/{crew_name}")
    async def trigger_crew(crew_name: str, topic: str = None):
        """Manually trigger a crew run."""
        return await get_scheduler().trigger_crew(crew_name, topic)

    @router.post("/enable/{crew_name}")
    async def enable_schedule(crew_name: str):
        """Enable a crew schedule."""
        scheduler = get_scheduler()
        if crew_name in scheduler.state.schedules:
            scheduler.state.schedules[crew_name].enabled = True
            return {"status": "enabled", "crew": crew_name}
        return {"status": "error", "error": f"Unknown crew: {crew_name}"}

    @router.post("/disable/{crew_name}")
    async def disable_schedule(crew_name: str):
        """Disable a crew schedule."""
        scheduler = get_scheduler()
        if crew_name in scheduler.state.schedules:
            scheduler.state.schedules[crew_name].enabled = False
            return {"status": "disabled", "crew": crew_name}
        return {"status": "error", "error": f"Unknown crew: {crew_name}"}

    return router
