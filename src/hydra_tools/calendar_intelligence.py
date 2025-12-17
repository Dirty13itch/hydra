"""
Calendar Intelligence for Hydra

Schedule-aware operations that adjust system behavior based on:
- Time of day (working hours, night, weekend)
- Scheduled events (maintenance windows, inference peaks)
- User calendar integration (optional)

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TimeSlot(str, Enum):
    """Time-of-day slots."""
    NIGHT = "night"          # 00:00 - 06:00
    MORNING = "morning"      # 06:00 - 12:00
    AFTERNOON = "afternoon"  # 12:00 - 18:00
    EVENING = "evening"      # 18:00 - 24:00


class DayType(str, Enum):
    """Type of day."""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


@dataclass
class ScheduleConfig:
    """Configuration for a schedule slot."""
    inference_priority: str  # "high", "normal", "low"
    maintenance_allowed: bool
    heavy_tasks_allowed: bool
    power_mode: str  # "full", "balanced", "eco"


# Default schedule configurations
DEFAULT_SCHEDULE = {
    # Weekday configurations
    (DayType.WEEKDAY, TimeSlot.NIGHT): ScheduleConfig(
        inference_priority="low",
        maintenance_allowed=True,
        heavy_tasks_allowed=True,
        power_mode="eco",
    ),
    (DayType.WEEKDAY, TimeSlot.MORNING): ScheduleConfig(
        inference_priority="normal",
        maintenance_allowed=False,
        heavy_tasks_allowed=False,
        power_mode="balanced",
    ),
    (DayType.WEEKDAY, TimeSlot.AFTERNOON): ScheduleConfig(
        inference_priority="high",
        maintenance_allowed=False,
        heavy_tasks_allowed=False,
        power_mode="full",
    ),
    (DayType.WEEKDAY, TimeSlot.EVENING): ScheduleConfig(
        inference_priority="high",
        maintenance_allowed=False,
        heavy_tasks_allowed=False,
        power_mode="full",
    ),
    # Weekend configurations (more relaxed)
    (DayType.WEEKEND, TimeSlot.NIGHT): ScheduleConfig(
        inference_priority="low",
        maintenance_allowed=True,
        heavy_tasks_allowed=True,
        power_mode="eco",
    ),
    (DayType.WEEKEND, TimeSlot.MORNING): ScheduleConfig(
        inference_priority="normal",
        maintenance_allowed=True,
        heavy_tasks_allowed=True,
        power_mode="balanced",
    ),
    (DayType.WEEKEND, TimeSlot.AFTERNOON): ScheduleConfig(
        inference_priority="high",
        maintenance_allowed=False,
        heavy_tasks_allowed=True,
        power_mode="full",
    ),
    (DayType.WEEKEND, TimeSlot.EVENING): ScheduleConfig(
        inference_priority="high",
        maintenance_allowed=False,
        heavy_tasks_allowed=False,
        power_mode="full",
    ),
}


@dataclass
class ScheduledEvent:
    """A scheduled event."""
    id: str
    name: str
    event_type: str  # "maintenance", "high_load", "backup", "custom"
    start_time: datetime
    end_time: datetime
    config_override: Optional[ScheduleConfig] = None
    recurrence: Optional[str] = None  # "daily", "weekly", "monthly"


class CalendarManager:
    """Manages schedule-aware operations."""

    def __init__(self, timezone: str = "America/Chicago"):
        self.timezone = ZoneInfo(timezone)
        self._events: List[ScheduledEvent] = []
        self._init_default_events()

    def _init_default_events(self):
        """Initialize default scheduled events."""
        now = datetime.now(self.timezone)

        # Daily maintenance window (3-5 AM)
        self._events.append(ScheduledEvent(
            id="maintenance-daily",
            name="Daily Maintenance Window",
            event_type="maintenance",
            start_time=now.replace(hour=3, minute=0, second=0, microsecond=0),
            end_time=now.replace(hour=5, minute=0, second=0, microsecond=0),
            config_override=ScheduleConfig(
                inference_priority="low",
                maintenance_allowed=True,
                heavy_tasks_allowed=True,
                power_mode="eco",
            ),
            recurrence="daily",
        ))

        # Weekly backup window (Sunday 2-4 AM)
        sunday = now + timedelta(days=(6 - now.weekday()) % 7)
        self._events.append(ScheduledEvent(
            id="backup-weekly",
            name="Weekly Backup Window",
            event_type="backup",
            start_time=sunday.replace(hour=2, minute=0, second=0, microsecond=0),
            end_time=sunday.replace(hour=4, minute=0, second=0, microsecond=0),
            config_override=ScheduleConfig(
                inference_priority="low",
                maintenance_allowed=True,
                heavy_tasks_allowed=True,
                power_mode="eco",
            ),
            recurrence="weekly",
        ))

    def get_current_time_slot(self) -> TimeSlot:
        """Get the current time slot."""
        now = datetime.now(self.timezone)
        hour = now.hour

        if 0 <= hour < 6:
            return TimeSlot.NIGHT
        elif 6 <= hour < 12:
            return TimeSlot.MORNING
        elif 12 <= hour < 18:
            return TimeSlot.AFTERNOON
        else:
            return TimeSlot.EVENING

    def get_current_day_type(self) -> DayType:
        """Get the current day type."""
        now = datetime.now(self.timezone)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return DayType.WEEKEND
        return DayType.WEEKDAY

    def get_active_events(self) -> List[ScheduledEvent]:
        """Get currently active scheduled events."""
        now = datetime.now(self.timezone)
        active = []

        for event in self._events:
            # Handle recurrence
            if event.recurrence == "daily":
                # Check if current time is within event hours
                event_start = event.start_time.replace(
                    year=now.year, month=now.month, day=now.day
                )
                event_end = event.end_time.replace(
                    year=now.year, month=now.month, day=now.day
                )
                if event_start <= now <= event_end:
                    active.append(event)
            elif event.recurrence == "weekly":
                # Check if same day of week and within hours
                if now.weekday() == event.start_time.weekday():
                    event_start = event.start_time.replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    event_end = event.end_time.replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    if event_start <= now <= event_end:
                        active.append(event)
            else:
                # One-time event
                if event.start_time <= now <= event.end_time:
                    active.append(event)

        return active

    def get_current_config(self) -> ScheduleConfig:
        """Get the current schedule configuration."""
        # Check for active events with overrides
        active_events = self.get_active_events()
        for event in active_events:
            if event.config_override:
                return event.config_override

        # Fall back to default schedule
        day_type = self.get_current_day_type()
        time_slot = self.get_current_time_slot()
        return DEFAULT_SCHEDULE.get(
            (day_type, time_slot),
            DEFAULT_SCHEDULE[(DayType.WEEKDAY, TimeSlot.AFTERNOON)]
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current calendar status."""
        now = datetime.now(self.timezone)
        config = self.get_current_config()
        active_events = self.get_active_events()

        return {
            "current_time": now.isoformat(),
            "timezone": str(self.timezone),
            "time_slot": self.get_current_time_slot().value,
            "day_type": self.get_current_day_type().value,
            "config": {
                "inference_priority": config.inference_priority,
                "maintenance_allowed": config.maintenance_allowed,
                "heavy_tasks_allowed": config.heavy_tasks_allowed,
                "power_mode": config.power_mode,
            },
            "active_events": [
                {"id": e.id, "name": e.name, "type": e.event_type}
                for e in active_events
            ],
        }

    def add_event(
        self,
        name: str,
        event_type: str,
        start_time: datetime,
        end_time: datetime,
        recurrence: Optional[str] = None,
    ) -> ScheduledEvent:
        """Add a scheduled event."""
        import uuid
        event = ScheduledEvent(
            id=str(uuid.uuid4())[:8],
            name=name,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            recurrence=recurrence,
        )
        self._events.append(event)
        return event

    def remove_event(self, event_id: str) -> bool:
        """Remove a scheduled event."""
        for i, event in enumerate(self._events):
            if event.id == event_id:
                self._events.pop(i)
                return True
        return False

    def should_allow_task(self, task_type: str) -> Dict[str, Any]:
        """Check if a task type should be allowed now."""
        config = self.get_current_config()

        result = {
            "task_type": task_type,
            "allowed": True,
            "reason": "Default allow",
        }

        if task_type == "maintenance":
            result["allowed"] = config.maintenance_allowed
            result["reason"] = "Maintenance " + ("allowed" if result["allowed"] else "blocked")
        elif task_type == "heavy":
            result["allowed"] = config.heavy_tasks_allowed
            result["reason"] = "Heavy tasks " + ("allowed" if result["allowed"] else "blocked")
        elif task_type == "inference":
            result["allowed"] = True
            result["priority"] = config.inference_priority
            result["reason"] = f"Inference at {config.inference_priority} priority"

        return result


# =============================================================================
# Global Instance
# =============================================================================

_calendar_manager: Optional[CalendarManager] = None


def get_calendar_manager() -> CalendarManager:
    """Get or create calendar manager."""
    global _calendar_manager
    if _calendar_manager is None:
        tz = os.getenv("TZ", "America/Chicago")
        _calendar_manager = CalendarManager(timezone=tz)
    return _calendar_manager


# =============================================================================
# FastAPI Router
# =============================================================================

class AddEventRequest(BaseModel):
    name: str
    event_type: str
    start_time: str  # ISO format
    end_time: str
    recurrence: Optional[str] = None


def create_calendar_router() -> APIRouter:
    """Create FastAPI router for calendar endpoints."""
    router = APIRouter(prefix="/calendar", tags=["calendar"])

    @router.get("/status")
    async def get_status():
        """Get current calendar status."""
        manager = get_calendar_manager()
        return manager.get_status()

    @router.get("/config")
    async def get_config():
        """Get current schedule configuration."""
        manager = get_calendar_manager()
        config = manager.get_current_config()
        return {
            "inference_priority": config.inference_priority,
            "maintenance_allowed": config.maintenance_allowed,
            "heavy_tasks_allowed": config.heavy_tasks_allowed,
            "power_mode": config.power_mode,
        }

    @router.get("/events")
    async def list_events():
        """List all scheduled events."""
        manager = get_calendar_manager()
        return {
            "events": [
                {
                    "id": e.id,
                    "name": e.name,
                    "event_type": e.event_type,
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat(),
                    "recurrence": e.recurrence,
                }
                for e in manager._events
            ]
        }

    @router.post("/events")
    async def add_event(request: AddEventRequest):
        """Add a scheduled event."""
        manager = get_calendar_manager()
        try:
            event = manager.add_event(
                name=request.name,
                event_type=request.event_type,
                start_time=datetime.fromisoformat(request.start_time),
                end_time=datetime.fromisoformat(request.end_time),
                recurrence=request.recurrence,
            )
            return {"id": event.id, "status": "created"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/events/{event_id}")
    async def delete_event(event_id: str):
        """Delete a scheduled event."""
        manager = get_calendar_manager()
        if manager.remove_event(event_id):
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Event not found")

    @router.get("/check/{task_type}")
    async def check_task(task_type: str):
        """Check if a task type is allowed now."""
        manager = get_calendar_manager()
        return manager.should_allow_task(task_type)

    @router.get("/schedule")
    async def get_schedule():
        """Get the default schedule configuration."""
        return {
            key[0].value + "_" + key[1].value: {
                "inference_priority": config.inference_priority,
                "maintenance_allowed": config.maintenance_allowed,
                "heavy_tasks_allowed": config.heavy_tasks_allowed,
                "power_mode": config.power_mode,
            }
            for key, config in DEFAULT_SCHEDULE.items()
        }

    return router


if __name__ == "__main__":
    manager = CalendarManager()
    print("Status:", manager.get_status())
    print("\nMaintenance check:", manager.should_allow_task("maintenance"))
