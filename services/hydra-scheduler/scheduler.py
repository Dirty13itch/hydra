#!/usr/bin/env python3
"""
Hydra Crew Scheduler - Autonomous scheduling for CrewAI crews

Schedules:
- Monitoring: Daily at 6:00 AM CST
- Research: Monday at 2:00 AM CST
- Maintenance: Sunday at 3:00 AM CST
"""

import asyncio
import httpx
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hydra-scheduler')

# Configuration
CREWAI_URL = "http://192.168.1.244:8500"
ACTIVITY_URL = "http://192.168.1.244:8700/activity"
TIMEZONE = ZoneInfo("America/Chicago")

# Schedule definitions (hour, minute, day_of_week for weekly tasks)
SCHEDULES = {
    "monitoring": {"hour": 6, "minute": 0, "frequency": "daily"},
    "research": {"hour": 2, "minute": 0, "frequency": "weekly", "day": 0},  # Monday
    "maintenance": {"hour": 3, "minute": 0, "frequency": "weekly", "day": 6},  # Sunday
}


async def run_crew(crew_name: str, topic: Optional[str] = None) -> dict:
    """Execute a crew and return the result."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        url = f"{CREWAI_URL}/run/{crew_name}"
        payload = {"topic": topic} if topic else {}

        try:
            logger.info(f"Triggering {crew_name} crew...")
            response = await client.post(url, json=payload)
            result = response.json()
            logger.info(f"{crew_name} crew completed: {result.get('status', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to run {crew_name} crew: {e}")
            return {"status": "error", "error": str(e)}


async def log_activity(crew_name: str, result: dict):
    """Log crew execution to the activity API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            activity = {
                "source": "hydra-scheduler",
                "action": f"crew_run_{crew_name}",
                "action_type": "scheduled",
                "target": f"crewai-{crew_name}",
                "result": result.get("status", "unknown"),
                "decision_reason": f"Scheduled {crew_name} crew execution",
                "requires_approval": False
            }
            await client.post(ACTIVITY_URL, json=activity)
            logger.info(f"Logged activity for {crew_name}")
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")


def should_run_now(schedule: dict) -> bool:
    """Check if a crew should run at the current time."""
    now = datetime.now(TIMEZONE)

    if schedule["frequency"] == "daily":
        return now.hour == schedule["hour"] and now.minute == schedule["minute"]
    elif schedule["frequency"] == "weekly":
        return (now.weekday() == schedule["day"] and
                now.hour == schedule["hour"] and
                now.minute == schedule["minute"])
    return False


async def check_and_run_schedules():
    """Check all schedules and run crews that are due."""
    for crew_name, schedule in SCHEDULES.items():
        if should_run_now(schedule):
            logger.info(f"Schedule triggered for {crew_name}")

            # Research crew gets a rotating topic
            topic = None
            if crew_name == "research":
                topics = [
                    "Latest developments in local LLM inference optimization",
                    "ExLlamaV2 and ExLlamaV3 updates and best practices",
                    "Home automation AI integration patterns",
                    "Vector database optimization techniques",
                ]
                topic = topics[datetime.now().isocalendar()[1] % len(topics)]

            result = await run_crew(crew_name, topic)
            await log_activity(crew_name, result)


async def main():
    """Main scheduler loop."""
    logger.info("Hydra Scheduler starting...")
    logger.info(f"Timezone: {TIMEZONE}")
    logger.info("Schedules:")
    for crew, sched in SCHEDULES.items():
        if sched["frequency"] == "daily":
            logger.info(f"  {crew}: Daily at {sched['hour']:02d}:{sched['minute']:02d}")
        else:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            logger.info(f"  {crew}: {days[sched['day']]} at {sched['hour']:02d}:{sched['minute']:02d}")

    while True:
        try:
            await check_and_run_schedules()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Check every minute
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
