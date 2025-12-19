"""
Google Calendar Integration for Hydra

OAuth2 authentication and calendar synchronization for:
- 7-day event lookahead
- Meeting-aware inference blocking
- Schedule-aware operations
- Morning briefing context

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
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://192.168.1.244:8700/google/callback")
TOKEN_FILE = Path(os.getenv("HYDRA_DATA_DIR", "/data")) / "google_tokens.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GoogleCalendarEvent:
    """A Google Calendar event."""
    id: str
    summary: str
    description: Optional[str]
    location: Optional[str]
    start: datetime
    end: datetime
    all_day: bool
    attendees: List[str]
    organizer: str
    status: str  # confirmed, tentative, cancelled
    html_link: str

    def is_meeting(self) -> bool:
        """Check if this is a meeting (has attendees)."""
        return len(self.attendees) > 0

    def is_active_now(self) -> bool:
        """Check if this event is currently active."""
        now = datetime.now()
        return self.start <= now <= self.end

    def minutes_until_start(self) -> int:
        """Get minutes until this event starts."""
        now = datetime.now()
        if now >= self.start:
            return 0
        return int((self.start - now).total_seconds() / 60)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "all_day": self.all_day,
            "attendees": self.attendees,
            "organizer": self.organizer,
            "status": self.status,
            "html_link": self.html_link,
            "is_meeting": self.is_meeting(),
            "is_active_now": self.is_active_now(),
            "minutes_until_start": self.minutes_until_start(),
        }


# =============================================================================
# Google Calendar Client
# =============================================================================

class GoogleCalendarClient:
    """Client for Google Calendar API with OAuth2."""

    def __init__(self):
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uri = GOOGLE_REDIRECT_URI
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from file."""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                    self._access_token = data.get("access_token")
                    self._refresh_token = data.get("refresh_token")
                    if data.get("expiry"):
                        self._token_expiry = datetime.fromisoformat(data["expiry"])
                    logger.info("Loaded Google tokens from file")
            except Exception as e:
                logger.warning(f"Failed to load Google tokens: {e}")

    def _save_tokens(self):
        """Save tokens to file."""
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                    "expiry": self._token_expiry.isoformat() if self._token_expiry else None,
                }, f)
            logger.info("Saved Google tokens to file")
        except Exception as e:
            logger.error(f"Failed to save Google tokens: {e}")

    @property
    def is_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        return bool(self._access_token)

    @property
    def needs_refresh(self) -> bool:
        """Check if tokens need refresh."""
        if not self._token_expiry:
            return False
        return datetime.now() >= self._token_expiry - timedelta(minutes=5)

    def get_auth_url(self, state: str = "hydra") -> str:
        """Get OAuth2 authorization URL."""
        if not self.is_configured:
            raise ValueError("Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            data = response.json()
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token", self._refresh_token)

            expires_in = data.get("expires_in", 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

            self._save_tokens()
            logger.info("Google OAuth tokens obtained successfully")

            return {"status": "authenticated", "expires_in": expires_in}

    async def refresh_access_token(self) -> bool:
        """Refresh the access token."""
        if not self._refresh_token:
            logger.warning("No refresh token available")
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                return False

            data = response.json()
            self._access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

            self._save_tokens()
            logger.info("Google access token refreshed")
            return True

    async def _ensure_valid_token(self):
        """Ensure we have a valid access token."""
        if not self.is_authenticated:
            raise ValueError("Not authenticated. Please complete OAuth flow.")

        if self.needs_refresh:
            if not await self.refresh_access_token():
                raise ValueError("Failed to refresh token. Please re-authenticate.")

    async def get_events(
        self,
        days_ahead: int = 7,
        calendar_id: str = "primary",
    ) -> List[GoogleCalendarEvent]:
        """Get calendar events for the next N days."""
        await self._ensure_valid_token()

        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 100,
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to get events: {response.text}")
                raise ValueError(f"Failed to get events: {response.status_code}")

            data = response.json()
            events = []

            for item in data.get("items", []):
                try:
                    # Parse start/end times
                    start_data = item.get("start", {})
                    end_data = item.get("end", {})

                    all_day = "date" in start_data

                    if all_day:
                        start = datetime.fromisoformat(start_data["date"])
                        end = datetime.fromisoformat(end_data["date"])
                    else:
                        start_str = start_data.get("dateTime", "")
                        end_str = end_data.get("dateTime", "")
                        # Handle timezone-aware strings
                        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        # Convert to local time (naive)
                        start = start.replace(tzinfo=None)
                        end = end.replace(tzinfo=None)

                    # Extract attendees
                    attendees = [
                        a.get("email", "")
                        for a in item.get("attendees", [])
                        if not a.get("self", False)
                    ]

                    event = GoogleCalendarEvent(
                        id=item.get("id", ""),
                        summary=item.get("summary", "No Title"),
                        description=item.get("description"),
                        location=item.get("location"),
                        start=start,
                        end=end,
                        all_day=all_day,
                        attendees=attendees,
                        organizer=item.get("organizer", {}).get("email", ""),
                        status=item.get("status", "confirmed"),
                        html_link=item.get("htmlLink", ""),
                    )
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event: {e}")
                    continue

            return events

    async def get_today_events(self) -> List[GoogleCalendarEvent]:
        """Get events for today."""
        events = await self.get_events(days_ahead=1)
        today = datetime.now().date()
        return [e for e in events if e.start.date() == today]

    async def get_upcoming_meetings(self, hours: int = 2) -> List[GoogleCalendarEvent]:
        """Get meetings in the next N hours."""
        events = await self.get_events(days_ahead=1)
        cutoff = datetime.now() + timedelta(hours=hours)
        return [
            e for e in events
            if e.is_meeting() and e.start <= cutoff and e.end >= datetime.now()
        ]

    async def is_in_meeting(self) -> Dict[str, Any]:
        """Check if currently in a meeting."""
        try:
            events = await self.get_today_events()
            for event in events:
                if event.is_meeting() and event.is_active_now():
                    return {
                        "in_meeting": True,
                        "meeting": event.to_dict(),
                        "minutes_remaining": int((event.end - datetime.now()).total_seconds() / 60),
                    }
            return {"in_meeting": False, "meeting": None}
        except Exception as e:
            return {"in_meeting": False, "error": str(e)}

    def disconnect(self):
        """Clear tokens and disconnect."""
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        logger.info("Google Calendar disconnected")

    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "configured": self.is_configured,
            "authenticated": self.is_authenticated,
            "needs_refresh": self.needs_refresh,
            "token_expiry": self._token_expiry.isoformat() if self._token_expiry else None,
        }


# =============================================================================
# Global Instance
# =============================================================================

_google_client: Optional[GoogleCalendarClient] = None


def get_google_client() -> GoogleCalendarClient:
    """Get or create Google Calendar client."""
    global _google_client
    if _google_client is None:
        _google_client = GoogleCalendarClient()
    return _google_client


# =============================================================================
# FastAPI Router
# =============================================================================

def create_google_calendar_router() -> APIRouter:
    """Create FastAPI router for Google Calendar endpoints."""
    router = APIRouter(prefix="/google", tags=["google-calendar"])

    @router.get("/status")
    async def get_status():
        """Get Google Calendar integration status."""
        client = get_google_client()
        return client.get_status()

    @router.get("/auth")
    async def start_auth():
        """Start OAuth2 authentication flow."""
        client = get_google_client()
        if not client.is_configured:
            return {
                "error": "Google OAuth not configured",
                "instructions": "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables",
            }

        auth_url = client.get_auth_url()
        return {
            "auth_url": auth_url,
            "instructions": "Visit the URL to authorize Hydra to access your Google Calendar",
        }

    @router.get("/callback")
    async def oauth_callback(code: str = None, error: str = None, state: str = None):
        """Handle OAuth2 callback."""
        if error:
            return HTMLResponse(f"""
                <html><body>
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
                <p><a href="http://192.168.1.244:3210">Return to Command Center</a></p>
                </body></html>
            """)

        if not code:
            raise HTTPException(status_code=400, detail="No authorization code provided")

        client = get_google_client()
        try:
            result = await client.exchange_code(code)
            return HTMLResponse(f"""
                <html><body>
                <h1>Authorization Successful!</h1>
                <p>Hydra can now access your Google Calendar.</p>
                <p>Token expires in {result.get('expires_in', 3600)} seconds.</p>
                <p><a href="http://192.168.1.244:3210">Return to Command Center</a></p>
                </body></html>
            """)
        except Exception as e:
            return HTMLResponse(f"""
                <html><body>
                <h1>Authorization Failed</h1>
                <p>Error: {str(e)}</p>
                <p><a href="http://192.168.1.244:3210">Return to Command Center</a></p>
                </body></html>
            """)

    @router.post("/disconnect")
    async def disconnect():
        """Disconnect Google Calendar integration."""
        client = get_google_client()
        client.disconnect()
        return {"status": "disconnected"}

    @router.get("/events")
    async def get_events(days: int = 7):
        """Get calendar events for the next N days."""
        client = get_google_client()
        if not client.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        try:
            events = await client.get_events(days_ahead=days)
            return {
                "events": [e.to_dict() for e in events],
                "count": len(events),
                "days_ahead": days,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/events/today")
    async def get_today():
        """Get today's events."""
        client = get_google_client()
        if not client.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            events = await client.get_today_events()
            return {
                "events": [e.to_dict() for e in events],
                "count": len(events),
                "date": datetime.now().date().isoformat(),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/events/upcoming")
    async def get_upcoming(hours: int = 2):
        """Get upcoming meetings in the next N hours."""
        client = get_google_client()
        if not client.is_authenticated:
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            events = await client.get_upcoming_meetings(hours=hours)
            return {
                "events": [e.to_dict() for e in events],
                "count": len(events),
                "hours_ahead": hours,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/meeting-status")
    async def check_meeting_status():
        """Check if currently in a meeting."""
        client = get_google_client()
        if not client.is_authenticated:
            return {"in_meeting": False, "authenticated": False}

        return await client.is_in_meeting()

    @router.get("/should-block-inference")
    async def should_block_inference():
        """Check if inference should be blocked due to meeting."""
        client = get_google_client()
        if not client.is_authenticated:
            return {"should_block": False, "reason": "Not authenticated"}

        meeting_status = await client.is_in_meeting()
        if meeting_status.get("in_meeting"):
            return {
                "should_block": True,
                "reason": f"In meeting: {meeting_status['meeting']['summary']}",
                "minutes_remaining": meeting_status.get("minutes_remaining", 0),
            }

        # Check for upcoming meetings in next 5 minutes
        try:
            upcoming = await client.get_upcoming_meetings(hours=1)
            for event in upcoming:
                if event.minutes_until_start() <= 5:
                    return {
                        "should_block": True,
                        "reason": f"Meeting starting soon: {event.summary}",
                        "minutes_until": event.minutes_until_start(),
                    }
        except Exception:
            pass

        return {"should_block": False, "reason": "No active or upcoming meetings"}

    return router


if __name__ == "__main__":
    import asyncio

    async def test():
        client = GoogleCalendarClient()
        print("Status:", client.get_status())

        if client.is_authenticated:
            events = await client.get_events(days_ahead=7)
            print(f"\nFound {len(events)} events:")
            for e in events[:5]:
                print(f"  - {e.summary} ({e.start})")

    asyncio.run(test())
