"""
Morning Briefing Module for Hydra

Combines multiple data sources to provide a comprehensive daily briefing:
- Google Calendar events
- Gmail priority emails
- Weather information
- System health status
- Research updates

Author: Hydra Autonomous System
Phase: 14 - External Intelligence
Created: 2025-12-18
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(os.getenv("HYDRA_DATA_DIR", "/data"))
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "Austin,TX")
HYDRA_API_BASE = "http://localhost:8700"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BriefingSection:
    """A section of the morning briefing."""
    title: str
    icon: str
    items: List[Dict[str, Any]]
    summary: str
    priority: int  # 1-5, 1 being highest priority


@dataclass
class MorningBriefing:
    """Complete morning briefing."""
    generated_at: datetime
    greeting: str
    sections: List[BriefingSection]
    voice_summary: str  # Text-to-speech friendly summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "greeting": self.greeting,
            "sections": [
                {
                    "title": s.title,
                    "icon": s.icon,
                    "items": s.items,
                    "summary": s.summary,
                    "priority": s.priority,
                }
                for s in sorted(self.sections, key=lambda x: x.priority)
            ],
            "voice_summary": self.voice_summary,
        }


# =============================================================================
# Data Fetchers
# =============================================================================

async def fetch_calendar_data() -> Optional[BriefingSection]:
    """Fetch today's calendar events."""
    try:
        async with httpx.AsyncClient() as client:
            # Get events for today
            response = await client.get(
                f"{HYDRA_API_BASE}/google/events",
                params={"days": 1},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])

                if not events:
                    return BriefingSection(
                        title="Calendar",
                        icon="calendar",
                        items=[],
                        summary="No events scheduled for today.",
                        priority=3,
                    )

                items = []
                meetings = []
                for event in events[:10]:
                    start = event.get("start", "")
                    if "T" in start:
                        time_str = datetime.fromisoformat(start.replace("Z", "+00:00")).strftime("%I:%M %p")
                    else:
                        time_str = "All Day"

                    items.append({
                        "time": time_str,
                        "title": event.get("summary", "Untitled"),
                        "location": event.get("location"),
                        "is_meeting": event.get("is_meeting", False),
                    })

                    if event.get("is_meeting"):
                        meetings.append(event.get("summary", "meeting"))

                if meetings:
                    summary = f"{len(events)} events today, including {len(meetings)} meeting(s): {', '.join(meetings[:3])}"
                else:
                    summary = f"{len(events)} events scheduled for today."

                return BriefingSection(
                    title="Calendar",
                    icon="calendar",
                    items=items,
                    summary=summary,
                    priority=2,
                )
            elif response.status_code == 401:
                return BriefingSection(
                    title="Calendar",
                    icon="calendar",
                    items=[],
                    summary="Calendar not connected. Use /google/auth to authenticate.",
                    priority=5,
                )
    except Exception as e:
        logger.error(f"Failed to fetch calendar data: {e}")

    return None


async def fetch_email_data() -> Optional[BriefingSection]:
    """Fetch email summary."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HYDRA_API_BASE}/gmail/morning-briefing-data",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()

                if not data.get("authenticated"):
                    return BriefingSection(
                        title="Email",
                        icon="mail",
                        items=[],
                        summary="Gmail not connected. Use /google/auth to authenticate.",
                        priority=5,
                    )

                unread = data.get("unread_total", 0)
                priority = data.get("unread_priority", 0)
                important = data.get("unread_important", 0)

                items = []
                for email in data.get("priority_emails", [])[:5]:
                    items.append({
                        "from": email.get("from"),
                        "subject": email.get("subject"),
                        "snippet": email.get("snippet", "")[:100],
                        "priority": True,
                    })

                for email in data.get("recent_important", [])[:3]:
                    if not any(e.get("subject") == email.get("subject") for e in items):
                        items.append({
                            "from": email.get("from"),
                            "subject": email.get("subject"),
                            "snippet": email.get("snippet", "")[:100],
                            "priority": False,
                        })

                if priority > 0:
                    summary = f"{unread} unread emails, {priority} from priority contacts require attention."
                    section_priority = 1
                elif important > 0:
                    summary = f"{unread} unread emails, {important} marked important."
                    section_priority = 2
                else:
                    summary = f"{unread} unread emails." if unread > 0 else "Inbox is clear."
                    section_priority = 3

                return BriefingSection(
                    title="Email",
                    icon="mail",
                    items=items,
                    summary=summary,
                    priority=section_priority,
                )
    except Exception as e:
        logger.error(f"Failed to fetch email data: {e}")

    return None


async def fetch_weather_data() -> Optional[BriefingSection]:
    """Fetch current weather."""
    if not WEATHER_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": WEATHER_LOCATION,
                    "appid": WEATHER_API_KEY,
                    "units": "imperial",
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                temp = round(data["main"]["temp"])
                feels_like = round(data["main"]["feels_like"])
                condition = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]

                items = [
                    {"label": "Temperature", "value": f"{temp}F (feels like {feels_like}F)"},
                    {"label": "Conditions", "value": condition.title()},
                    {"label": "Humidity", "value": f"{humidity}%"},
                ]

                summary = f"Currently {temp}F and {condition} in {WEATHER_LOCATION}."

                return BriefingSection(
                    title="Weather",
                    icon="cloud-sun",
                    items=items,
                    summary=summary,
                    priority=4,
                )
    except Exception as e:
        logger.error(f"Failed to fetch weather: {e}")

    return None


async def fetch_system_health() -> BriefingSection:
    """Fetch Hydra system health status."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HYDRA_API_BASE}/health/cluster",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()

                items = []
                issues = []

                # Parse the summary
                summary_data = data.get("summary", {})
                healthy_count = summary_data.get("healthy", 0)
                unhealthy_count = summary_data.get("unhealthy", 0)
                degraded_count = summary_data.get("degraded", 0)
                total_count = summary_data.get("total", 0)
                critical_down = summary_data.get("critical_down", [])

                # Parse services
                services = data.get("services", [])
                for svc in services[:8]:  # Top 8 services
                    items.append({
                        "service": svc.get("service"),
                        "node": svc.get("node"),
                        "status": svc.get("status"),
                        "category": svc.get("category"),
                    })
                    if svc.get("status") != "healthy":
                        issues.append(f"{svc.get('service')} on {svc.get('node')}")

                if critical_down:
                    issues.insert(0, f"CRITICAL: {', '.join(critical_down)}")

                if issues:
                    summary = f"System issues: {'; '.join(issues[:3])}"
                    priority = 1
                elif unhealthy_count > 0 or degraded_count > 0:
                    summary = f"{healthy_count}/{total_count} services healthy, {unhealthy_count + degraded_count} need attention."
                    priority = 2
                else:
                    summary = f"All {total_count} services operational."
                    priority = 4

                return BriefingSection(
                    title="System Health",
                    icon="server",
                    items=items,
                    summary=summary,
                    priority=priority,
                )
    except Exception as e:
        logger.error(f"Failed to fetch system health: {e}")

    return BriefingSection(
        title="System Health",
        icon="server",
        items=[],
        summary="Unable to fetch system status.",
        priority=4,
    )


async def fetch_research_updates() -> Optional[BriefingSection]:
    """Fetch recent autonomous research updates."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HYDRA_API_BASE}/autonomous-research/reports",
                params={"limit": 5},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                reports = data.get("reports", [])

                if not reports:
                    return None

                # Only include reports from the last 24 hours
                recent = []
                cutoff = datetime.utcnow() - timedelta(hours=24)
                for r in reports:
                    try:
                        created = datetime.fromisoformat(r.get("created_at", "").replace("Z", "+00:00"))
                        if created.replace(tzinfo=None) > cutoff:
                            recent.append(r)
                    except Exception:
                        pass

                if not recent:
                    return None

                items = [
                    {
                        "topic": r.get("topic"),
                        "key_insights": r.get("key_insights", [])[:2],
                    }
                    for r in recent[:3]
                ]

                summary = f"{len(recent)} research report(s) completed in the last 24 hours."

                return BriefingSection(
                    title="Research Updates",
                    icon="book-open",
                    items=items,
                    summary=summary,
                    priority=3,
                )
    except Exception as e:
        logger.error(f"Failed to fetch research updates: {e}")

    return None


async def fetch_news_updates() -> Optional[BriefingSection]:
    """Fetch news from Miniflux RSS feeds."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HYDRA_API_BASE}/news/morning-briefing-data",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()

                if not data.get("configured"):
                    return None

                unread = data.get("unread_total", 0)
                topic_alerts = data.get("topic_alerts", [])
                headlines = data.get("top_headlines", [])

                items = []

                # Add topic alerts first (high priority)
                for alert in topic_alerts[:3]:
                    items.append({
                        "type": "topic_alert",
                        "topic": alert.get("topic"),
                        "count": alert.get("count"),
                        "headlines": alert.get("headlines", [])[:2],
                    })

                # Add top headlines
                for headline in headlines[:5]:
                    items.append({
                        "type": "headline",
                        "title": headline.get("title"),
                        "source": headline.get("source"),
                        "age_hours": headline.get("age_hours"),
                    })

                if topic_alerts:
                    summary = f"{unread} unread articles. {len(topic_alerts)} monitored topic(s) have new updates."
                    priority = 2
                elif unread > 0:
                    summary = f"{unread} unread articles from {data.get('feeds_count', 0)} feeds."
                    priority = 3
                else:
                    summary = "No new articles."
                    priority = 5

                return BriefingSection(
                    title="News",
                    icon="newspaper",
                    items=items,
                    summary=summary,
                    priority=priority,
                )
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")

    return None


# =============================================================================
# Briefing Generator
# =============================================================================

def get_greeting() -> str:
    """Generate time-appropriate greeting."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hello"


def generate_voice_summary(sections: List[BriefingSection]) -> str:
    """Generate a spoken summary of the briefing."""
    parts = [f"{get_greeting()}, Shaun. Here's your briefing."]

    # Sort by priority
    for section in sorted(sections, key=lambda x: x.priority)[:4]:
        parts.append(section.summary)

    return " ".join(parts)


async def generate_briefing() -> MorningBriefing:
    """Generate complete morning briefing."""
    # Fetch all data in parallel
    results = await asyncio.gather(
        fetch_calendar_data(),
        fetch_email_data(),
        fetch_weather_data(),
        fetch_system_health(),
        fetch_research_updates(),
        fetch_news_updates(),
        return_exceptions=True,
    )

    sections = []
    for result in results:
        if isinstance(result, BriefingSection):
            sections.append(result)
        elif isinstance(result, Exception):
            logger.error(f"Briefing section failed: {result}")

    return MorningBriefing(
        generated_at=datetime.utcnow(),
        greeting=get_greeting(),
        sections=sections,
        voice_summary=generate_voice_summary(sections),
    )


# =============================================================================
# FastAPI Router
# =============================================================================

def create_morning_briefing_router() -> APIRouter:
    """Create morning briefing API router."""
    router = APIRouter(prefix="/briefing", tags=["briefing"])

    @router.get("/")
    async def get_briefing():
        """
        Get complete morning briefing.

        Combines data from:
        - Google Calendar (today's events)
        - Gmail (priority emails)
        - Weather (current conditions)
        - System health (Hydra cluster status)
        - Research updates (recent discoveries)
        """
        briefing = await generate_briefing()
        return briefing.to_dict()

    @router.get("/voice")
    async def get_voice_briefing():
        """
        Get briefing formatted for voice synthesis.

        Returns a text string suitable for TTS.
        """
        briefing = await generate_briefing()
        return {
            "text": briefing.voice_summary,
            "greeting": briefing.greeting,
        }

    @router.post("/speak")
    async def speak_briefing():
        """
        Generate and speak the morning briefing via Kokoro TTS.
        """
        briefing = await generate_briefing()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{HYDRA_API_BASE}/voice/speak",
                    json={
                        "text": briefing.voice_summary,
                        "voice": "af_sky",
                    },
                    timeout=30,
                )
                if response.status_code == 200:
                    return {
                        "status": "spoken",
                        "text": briefing.voice_summary,
                    }
                else:
                    return {
                        "status": "failed",
                        "error": response.text,
                        "text": briefing.voice_summary,
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "text": briefing.voice_summary,
            }

    @router.get("/calendar")
    async def get_calendar_section():
        """Get just the calendar section of the briefing."""
        section = await fetch_calendar_data()
        if section:
            return {
                "title": section.title,
                "items": section.items,
                "summary": section.summary,
            }
        return {"error": "Unable to fetch calendar data"}

    @router.get("/email")
    async def get_email_section():
        """Get just the email section of the briefing."""
        section = await fetch_email_data()
        if section:
            return {
                "title": section.title,
                "items": section.items,
                "summary": section.summary,
            }
        return {"error": "Unable to fetch email data"}

    @router.get("/system")
    async def get_system_section():
        """Get just the system health section."""
        section = await fetch_system_health()
        return {
            "title": section.title,
            "items": section.items,
            "summary": section.summary,
        }

    @router.get("/news")
    async def get_news_section():
        """Get just the news section of the briefing."""
        section = await fetch_news_updates()
        if section:
            return {
                "title": section.title,
                "items": section.items,
                "summary": section.summary,
            }
        return {"error": "Unable to fetch news data or Miniflux not configured"}

    @router.post("/deliver")
    async def deliver_briefing(
        voice: bool = True,
        discord: bool = False,
        push: bool = False,
    ):
        """
        Generate and deliver the morning briefing via multiple channels.

        This is the "silver platter" endpoint - one call delivers everything.

        Channels:
        - voice: Speak via Kokoro TTS (default: true)
        - discord: Send to Discord webhook (requires DISCORD_WEBHOOK_URL)
        - push: Send push notification (future)
        """
        briefing = await generate_briefing()
        results = {"briefing": briefing.to_dict(), "delivery": {}}

        # Voice delivery
        if voice:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{HYDRA_API_BASE}/voice/speak",
                        json={"text": briefing.voice_summary, "voice": "af_sky"},
                        timeout=30,
                    )
                    results["delivery"]["voice"] = {
                        "status": "delivered" if response.status_code == 200 else "failed",
                    }
            except Exception as e:
                results["delivery"]["voice"] = {"status": "error", "error": str(e)}

        # Discord delivery
        if discord:
            discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
            if discord_url:
                try:
                    # Format for Discord
                    embed = {
                        "title": f"{briefing.greeting}, here's your briefing",
                        "description": briefing.voice_summary,
                        "color": 0x00D4AA,  # Hydra green
                        "fields": [
                            {"name": s.title, "value": s.summary, "inline": False}
                            for s in sorted(briefing.sections, key=lambda x: x.priority)[:5]
                        ],
                        "timestamp": briefing.generated_at.isoformat(),
                    }
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            discord_url,
                            json={"embeds": [embed]},
                            timeout=10,
                        )
                        results["delivery"]["discord"] = {
                            "status": "delivered" if response.status_code in (200, 204) else "failed",
                        }
                except Exception as e:
                    results["delivery"]["discord"] = {"status": "error", "error": str(e)}
            else:
                results["delivery"]["discord"] = {"status": "not_configured"}

        return results

    @router.get("/schedule")
    async def get_schedule():
        """
        Get the configured briefing schedule.

        The schedule is managed via the autonomous scheduler.
        """
        # Check if briefing is scheduled
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{HYDRA_API_BASE}/autonomous/tasks",
                    timeout=10,
                )
                if response.status_code == 200:
                    tasks = response.json().get("tasks", [])
                    briefing_task = next(
                        (t for t in tasks if "briefing" in t.get("name", "").lower()),
                        None,
                    )
                    if briefing_task:
                        return {
                            "scheduled": True,
                            "task": briefing_task,
                        }
        except Exception:
            pass

        return {
            "scheduled": False,
            "instructions": (
                "To schedule daily briefings, use the autonomous scheduler: "
                "POST /autonomous/schedule with a cron expression (e.g., '0 7 * * *' for 7am daily)"
            ),
        }

    @router.post("/test-delivery")
    async def test_delivery():
        """
        Test briefing delivery without actually fetching all data.
        Useful for testing voice and Discord delivery.
        """
        test_summary = (
            f"{get_greeting()}, this is a test briefing. "
            "All systems are operational. You have no urgent items."
        )

        results = {"test_summary": test_summary, "delivery": {}}

        # Test voice
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{HYDRA_API_BASE}/voice/speak",
                    json={"text": test_summary, "voice": "af_sky"},
                    timeout=30,
                )
                results["delivery"]["voice"] = {
                    "status": "delivered" if response.status_code == 200 else "failed",
                }
        except Exception as e:
            results["delivery"]["voice"] = {"status": "error", "error": str(e)}

        return results

    return router
