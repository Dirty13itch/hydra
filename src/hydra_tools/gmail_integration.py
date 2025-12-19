"""
Gmail Integration for Hydra

OAuth2 authentication and email operations for:
- Inbox monitoring and priority detection
- Email summarization for morning briefings
- Important contact filtering
- Unread count tracking

Author: Hydra Autonomous System
Phase: 14 - External Intelligence
Created: 2025-12-18
"""

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
TOKEN_FILE = Path(os.getenv("HYDRA_DATA_DIR", "/data")) / "google_tokens.json"

# Gmail-specific scopes (added to calendar scopes)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]

# Priority contacts - emails from these addresses get special attention
PRIORITY_CONTACTS_FILE = Path(os.getenv("HYDRA_DATA_DIR", "/data")) / "priority_contacts.json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmailMessage:
    """A Gmail message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    recipients: List[str]
    snippet: str
    body_preview: str
    date: datetime
    labels: List[str]
    is_unread: bool
    is_important: bool
    has_attachments: bool

    def is_from_priority_contact(self, priority_emails: List[str]) -> bool:
        """Check if this email is from a priority contact."""
        sender_lower = self.sender_email.lower()
        return any(p.lower() in sender_lower for p in priority_emails)

    def age_hours(self) -> float:
        """Get age of email in hours."""
        return (datetime.utcnow() - self.date).total_seconds() / 3600

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "recipients": self.recipients,
            "snippet": self.snippet,
            "body_preview": self.body_preview[:500] if self.body_preview else "",
            "date": self.date.isoformat(),
            "labels": self.labels,
            "is_unread": self.is_unread,
            "is_important": self.is_important,
            "has_attachments": self.has_attachments,
            "age_hours": round(self.age_hours(), 1),
        }


@dataclass
class InboxSummary:
    """Summary of inbox state."""
    total_unread: int
    priority_unread: int
    important_unread: int
    recent_emails: List[EmailMessage]
    priority_emails: List[EmailMessage]
    label_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_unread": self.total_unread,
            "priority_unread": self.priority_unread,
            "important_unread": self.important_unread,
            "recent_emails": [e.to_dict() for e in self.recent_emails[:10]],
            "priority_emails": [e.to_dict() for e in self.priority_emails],
            "label_counts": self.label_counts,
        }


# =============================================================================
# Gmail Client
# =============================================================================

class GmailClient:
    """Client for Gmail API operations."""

    def __init__(self):
        self._priority_contacts: List[str] = []
        self._load_priority_contacts()

    def _load_priority_contacts(self):
        """Load priority contacts from file."""
        if PRIORITY_CONTACTS_FILE.exists():
            try:
                data = json.loads(PRIORITY_CONTACTS_FILE.read_text())
                self._priority_contacts = data.get("contacts", [])
                logger.info(f"Loaded {len(self._priority_contacts)} priority contacts")
            except Exception as e:
                logger.warning(f"Failed to load priority contacts: {e}")

    def _save_priority_contacts(self):
        """Save priority contacts to file."""
        try:
            PRIORITY_CONTACTS_FILE.write_text(json.dumps({
                "contacts": self._priority_contacts,
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save priority contacts: {e}")

    def add_priority_contact(self, email: str):
        """Add a priority contact."""
        if email.lower() not in [c.lower() for c in self._priority_contacts]:
            self._priority_contacts.append(email)
            self._save_priority_contacts()

    def remove_priority_contact(self, email: str):
        """Remove a priority contact."""
        self._priority_contacts = [c for c in self._priority_contacts if c.lower() != email.lower()]
        self._save_priority_contacts()

    def get_priority_contacts(self) -> List[str]:
        """Get list of priority contacts."""
        return self._priority_contacts.copy()

    def _get_tokens(self) -> Optional[Dict[str, Any]]:
        """Get stored OAuth tokens."""
        if TOKEN_FILE.exists():
            try:
                return json.loads(TOKEN_FILE.read_text())
            except Exception:
                return None
        return None

    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        tokens = self._get_tokens()
        if not tokens:
            return False

        # Check if token has gmail scope
        scopes = tokens.get("scope", "")
        return "gmail" in scopes.lower()

    async def _refresh_token_if_needed(self) -> Optional[str]:
        """Refresh access token if expired, return valid token."""
        tokens = self._get_tokens()
        if not tokens:
            return None

        expiry_str = tokens.get("token_expiry")
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                if datetime.utcnow().replace(tzinfo=expiry.tzinfo) >= expiry:
                    # Token expired, refresh it
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "https://oauth2.googleapis.com/token",
                            data={
                                "client_id": GOOGLE_CLIENT_ID,
                                "client_secret": GOOGLE_CLIENT_SECRET,
                                "refresh_token": tokens.get("refresh_token"),
                                "grant_type": "refresh_token",
                            },
                        )
                        if response.status_code == 200:
                            new_tokens = response.json()
                            tokens["access_token"] = new_tokens["access_token"]
                            tokens["token_expiry"] = (
                                datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 3600))
                            ).isoformat()
                            TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
                            logger.info("Refreshed Gmail access token")
                        else:
                            logger.error(f"Failed to refresh token: {response.text}")
                            return None
            except Exception as e:
                logger.error(f"Error checking token expiry: {e}")

        return tokens.get("access_token")

    async def get_unread_count(self) -> int:
        """Get total unread message count."""
        token = await self._refresh_token_if_needed()
        if not token:
            return 0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/labels/INBOX",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("messagesUnread", 0)
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")

        return 0

    async def list_messages(
        self,
        max_results: int = 20,
        query: str = "",
        label_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """List message IDs matching query."""
        token = await self._refresh_token_if_needed()
        if not token:
            return []

        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = ",".join(label_ids)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [m["id"] for m in data.get("messages", [])]
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")

        return []

    async def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """Get a single message by ID."""
        token = await self._refresh_token_if_needed()
        if not token:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "full"},
                )
                if response.status_code == 200:
                    return self._parse_message(response.json())
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")

        return None

    def _parse_message(self, data: Dict[str, Any]) -> EmailMessage:
        """Parse Gmail API message response."""
        headers = {h["name"].lower(): h["value"] for h in data.get("payload", {}).get("headers", [])}

        # Parse sender
        sender_raw = headers.get("from", "Unknown")
        sender_match = re.match(r"(.+?)\s*<(.+?)>", sender_raw)
        if sender_match:
            sender_name = sender_match.group(1).strip().strip('"')
            sender_email = sender_match.group(2)
        else:
            sender_name = sender_raw
            sender_email = sender_raw

        # Parse recipients
        recipients = []
        for h in ["to", "cc"]:
            if h in headers:
                recipients.extend([r.strip() for r in headers[h].split(",")])

        # Parse date
        date_str = headers.get("date", "")
        try:
            date = parsedate_to_datetime(date_str)
        except Exception:
            date = datetime.utcnow()

        # Get body preview
        body_preview = ""
        payload = data.get("payload", {})
        if "body" in payload and payload["body"].get("data"):
            body_preview = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body_preview = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break

        labels = data.get("labelIds", [])

        return EmailMessage(
            id=data["id"],
            thread_id=data.get("threadId", data["id"]),
            subject=headers.get("subject", "(No Subject)"),
            sender=sender_name,
            sender_email=sender_email,
            recipients=recipients,
            snippet=data.get("snippet", ""),
            body_preview=body_preview[:1000] if body_preview else "",
            date=date,
            labels=labels,
            is_unread="UNREAD" in labels,
            is_important="IMPORTANT" in labels,
            has_attachments=any(
                "filename" in p.get("body", {}) or p.get("filename")
                for p in payload.get("parts", [])
            ),
        )

    async def get_inbox_summary(self) -> InboxSummary:
        """Get a summary of inbox state."""
        token = await self._refresh_token_if_needed()
        if not token:
            return InboxSummary(
                total_unread=0,
                priority_unread=0,
                important_unread=0,
                recent_emails=[],
                priority_emails=[],
                label_counts={},
            )

        # Get unread messages
        unread_ids = await self.list_messages(max_results=50, query="is:unread")

        # Fetch message details in parallel
        messages = []
        async with httpx.AsyncClient() as client:
            tasks = [self.get_message(mid) for mid in unread_ids[:30]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            messages = [m for m in results if isinstance(m, EmailMessage)]

        # Sort by date
        messages.sort(key=lambda m: m.date, reverse=True)

        # Categorize
        priority_emails = [m for m in messages if m.is_from_priority_contact(self._priority_contacts)]
        important_emails = [m for m in messages if m.is_important]

        # Count labels
        label_counts: Dict[str, int] = {}
        for msg in messages:
            for label in msg.labels:
                label_counts[label] = label_counts.get(label, 0) + 1

        return InboxSummary(
            total_unread=len(messages),
            priority_unread=len(priority_emails),
            important_unread=len(important_emails),
            recent_emails=messages[:10],
            priority_emails=priority_emails,
            label_counts=label_counts,
        )

    async def get_recent_from_contact(self, email: str, max_results: int = 5) -> List[EmailMessage]:
        """Get recent emails from a specific contact."""
        message_ids = await self.list_messages(
            max_results=max_results,
            query=f"from:{email}",
        )

        messages = []
        for mid in message_ids:
            msg = await self.get_message(mid)
            if msg:
                messages.append(msg)

        return messages


# =============================================================================
# Pydantic Models
# =============================================================================

class PriorityContactRequest(BaseModel):
    email: str


class EmailSearchRequest(BaseModel):
    query: str = ""
    max_results: int = 20


# =============================================================================
# Singleton Client Instance
# =============================================================================

_gmail_client: Optional[GmailClient] = None


def get_gmail_client() -> GmailClient:
    """Get or create Gmail client singleton."""
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailClient()
    return _gmail_client


# =============================================================================
# FastAPI Router
# =============================================================================

def create_gmail_router() -> APIRouter:
    """Create Gmail API router."""
    router = APIRouter(prefix="/gmail", tags=["gmail"])

    @router.get("/status")
    async def get_status():
        """Get Gmail integration status."""
        client = get_gmail_client()
        authenticated = client.is_authenticated()

        return {
            "configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "authenticated": authenticated,
            "priority_contacts_count": len(client.get_priority_contacts()),
        }

    @router.get("/unread")
    async def get_unread_count():
        """Get unread message count."""
        client = get_gmail_client()
        if not client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        count = await client.get_unread_count()
        return {"unread_count": count}

    @router.get("/inbox")
    async def get_inbox_summary():
        """Get inbox summary with priority and recent emails."""
        client = get_gmail_client()
        if not client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        summary = await client.get_inbox_summary()
        return summary.to_dict()

    @router.get("/priority-contacts")
    async def get_priority_contacts():
        """Get list of priority contacts."""
        client = get_gmail_client()
        return {"contacts": client.get_priority_contacts()}

    @router.post("/priority-contacts")
    async def add_priority_contact(request: PriorityContactRequest):
        """Add a priority contact."""
        client = get_gmail_client()
        client.add_priority_contact(request.email)
        return {"status": "added", "email": request.email}

    @router.delete("/priority-contacts")
    async def remove_priority_contact(request: PriorityContactRequest):
        """Remove a priority contact."""
        client = get_gmail_client()
        client.remove_priority_contact(request.email)
        return {"status": "removed", "email": request.email}

    @router.post("/search")
    async def search_emails(request: EmailSearchRequest):
        """Search emails with Gmail query syntax."""
        client = get_gmail_client()
        if not client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        message_ids = await client.list_messages(
            max_results=request.max_results,
            query=request.query,
        )

        messages = []
        for mid in message_ids:
            msg = await client.get_message(mid)
            if msg:
                messages.append(msg.to_dict())

        return {"count": len(messages), "messages": messages}

    @router.get("/message/{message_id}")
    async def get_message(message_id: str):
        """Get a specific message by ID."""
        client = get_gmail_client()
        if not client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        msg = await client.get_message(message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        return msg.to_dict()

    @router.get("/from/{email}")
    async def get_emails_from_contact(email: str, max_results: int = 5):
        """Get recent emails from a specific contact."""
        client = get_gmail_client()
        if not client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Use /google/auth to connect.")

        messages = await client.get_recent_from_contact(email, max_results)
        return {
            "contact": email,
            "count": len(messages),
            "messages": [m.to_dict() for m in messages],
        }

    @router.get("/morning-briefing-data")
    async def get_morning_briefing_data():
        """
        Get email data formatted for morning briefing.
        Returns priority emails, important emails, and counts.
        """
        client = get_gmail_client()
        if not client.is_authenticated():
            return {
                "authenticated": False,
                "data": None,
            }

        summary = await client.get_inbox_summary()

        # Format for briefing
        briefing_data = {
            "authenticated": True,
            "unread_total": summary.total_unread,
            "unread_priority": summary.priority_unread,
            "unread_important": summary.important_unread,
            "priority_emails": [
                {
                    "from": e.sender,
                    "subject": e.subject,
                    "snippet": e.snippet,
                    "age_hours": round(e.age_hours(), 1),
                }
                for e in summary.priority_emails
            ],
            "recent_important": [
                {
                    "from": e.sender,
                    "subject": e.subject,
                    "snippet": e.snippet,
                }
                for e in summary.recent_emails
                if e.is_important
            ][:5],
        }

        return briefing_data

    return router
