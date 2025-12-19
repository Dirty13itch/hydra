"""
News & Research Integration for Hydra

Miniflux RSS integration for:
- Feed aggregation and monitoring
- Topic-based filtering
- Priority news detection
- Morning briefing integration

Author: Hydra Autonomous System
Phase: 14 - External Intelligence (Week 24)
Created: 2025-12-18
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

MINIFLUX_URL = os.getenv("MINIFLUX_URL", "http://192.168.1.244:8180")
MINIFLUX_API_KEY = os.getenv("MINIFLUX_API_KEY", "")
MINIFLUX_USERNAME = os.getenv("MINIFLUX_USERNAME", "")
MINIFLUX_PASSWORD = os.getenv("MINIFLUX_PASSWORD", "")

DATA_DIR = Path(os.getenv("HYDRA_DATA_DIR", "/data"))
TOPICS_FILE = DATA_DIR / "news_topics.json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NewsEntry:
    """A news entry from Miniflux."""
    id: int
    feed_id: int
    feed_title: str
    title: str
    url: str
    content: str
    author: str
    published_at: datetime
    reading_time: int
    starred: bool
    status: str  # unread, read

    def matches_topics(self, topics: List[str]) -> List[str]:
        """Check which topics this entry matches."""
        text = f"{self.title} {self.content}".lower()
        matched = []
        for topic in topics:
            # Support simple keyword and phrase matching
            keywords = topic.lower().split()
            if all(kw in text for kw in keywords):
                matched.append(topic)
        return matched

    def age_hours(self) -> float:
        """Get age of entry in hours."""
        now = datetime.utcnow()
        if self.published_at.tzinfo:
            now = now.replace(tzinfo=self.published_at.tzinfo)
        return (now - self.published_at).total_seconds() / 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "feed_title": self.feed_title,
            "title": self.title,
            "url": self.url,
            "content_preview": self.content[:500] if self.content else "",
            "author": self.author,
            "published_at": self.published_at.isoformat(),
            "reading_time": self.reading_time,
            "starred": self.starred,
            "status": self.status,
            "age_hours": round(self.age_hours(), 1),
        }


@dataclass
class Feed:
    """A Miniflux feed."""
    id: int
    title: str
    site_url: str
    feed_url: str
    category_id: int
    category_title: str
    icon_id: Optional[int]
    checked_at: Optional[datetime]
    parsing_error_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "site_url": self.site_url,
            "feed_url": self.feed_url,
            "category": self.category_title,
            "parsing_errors": self.parsing_error_count,
            "last_checked": self.checked_at.isoformat() if self.checked_at else None,
        }


@dataclass
class NewsSummary:
    """Summary of news state."""
    total_unread: int
    feeds_count: int
    categories: Dict[str, int]
    recent_entries: List[NewsEntry]
    topic_matches: Dict[str, List[NewsEntry]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_unread": self.total_unread,
            "feeds_count": self.feeds_count,
            "categories": self.categories,
            "recent_entries": [e.to_dict() for e in self.recent_entries[:10]],
            "topic_matches": {
                topic: [e.to_dict() for e in entries[:5]]
                for topic, entries in self.topic_matches.items()
            },
        }


# =============================================================================
# Topic Monitor
# =============================================================================

class TopicMonitor:
    """Monitors news for specific topics."""

    def __init__(self):
        self._topics: Set[str] = set()
        self._load_topics()

    def _load_topics(self):
        """Load monitored topics from file."""
        if TOPICS_FILE.exists():
            try:
                data = json.loads(TOPICS_FILE.read_text())
                self._topics = set(data.get("topics", []))
                logger.info(f"Loaded {len(self._topics)} monitored topics")
            except Exception as e:
                logger.warning(f"Failed to load topics: {e}")

    def _save_topics(self):
        """Save topics to file."""
        try:
            TOPICS_FILE.write_text(json.dumps({
                "topics": list(self._topics),
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save topics: {e}")

    def add_topic(self, topic: str):
        """Add a topic to monitor."""
        self._topics.add(topic.lower())
        self._save_topics()

    def remove_topic(self, topic: str):
        """Remove a monitored topic."""
        self._topics.discard(topic.lower())
        self._save_topics()

    def get_topics(self) -> List[str]:
        """Get list of monitored topics."""
        return sorted(self._topics)

    def filter_entries(self, entries: List[NewsEntry]) -> Dict[str, List[NewsEntry]]:
        """Filter entries by monitored topics."""
        results: Dict[str, List[NewsEntry]] = {t: [] for t in self._topics}

        for entry in entries:
            matches = entry.matches_topics(list(self._topics))
            for topic in matches:
                results[topic].append(entry)

        # Remove empty topics
        return {k: v for k, v in results.items() if v}


# =============================================================================
# Miniflux Client
# =============================================================================

class MinifluxClient:
    """Client for Miniflux API."""

    def __init__(self):
        self.base_url = MINIFLUX_URL
        self.topic_monitor = TopicMonitor()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if MINIFLUX_API_KEY:
            return {"X-Auth-Token": MINIFLUX_API_KEY}
        return {}

    def _get_auth(self) -> Optional[tuple]:
        """Get basic auth tuple."""
        if MINIFLUX_USERNAME and MINIFLUX_PASSWORD:
            return (MINIFLUX_USERNAME, MINIFLUX_PASSWORD)
        return None

    def is_configured(self) -> bool:
        """Check if Miniflux credentials are configured."""
        return bool(MINIFLUX_API_KEY or (MINIFLUX_USERNAME and MINIFLUX_PASSWORD))

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request to Miniflux API."""
        url = f"{self.base_url}/v1{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._get_auth_headers(),
                    auth=self._get_auth(),
                    timeout=30,
                    **kwargs,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error("Miniflux authentication failed")
                else:
                    logger.warning(f"Miniflux API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Miniflux request failed: {e}")

        return None

    async def get_me(self) -> Optional[Dict]:
        """Get current user info."""
        return await self._request("GET", "/me")

    async def get_feeds(self) -> List[Feed]:
        """Get all feeds."""
        data = await self._request("GET", "/feeds")
        if not data:
            return []

        feeds = []
        for f in data:
            category = f.get("category", {})
            feeds.append(Feed(
                id=f["id"],
                title=f.get("title", ""),
                site_url=f.get("site_url", ""),
                feed_url=f.get("feed_url", ""),
                category_id=category.get("id", 0),
                category_title=category.get("title", "Uncategorized"),
                icon_id=f.get("icon", {}).get("icon_id") if f.get("icon") else None,
                checked_at=datetime.fromisoformat(f["checked_at"].replace("Z", "+00:00")) if f.get("checked_at") else None,
                parsing_error_count=f.get("parsing_error_count", 0),
            ))

        return feeds

    async def get_entries(
        self,
        status: str = "unread",
        limit: int = 50,
        order: str = "published_at",
        direction: str = "desc",
    ) -> List[NewsEntry]:
        """Get entries with filters."""
        params = {
            "status": status,
            "limit": limit,
            "order": order,
            "direction": direction,
        }

        data = await self._request("GET", "/entries", params=params)
        if not data or "entries" not in data:
            return []

        entries = []
        for e in data["entries"]:
            feed = e.get("feed", {})
            pub_date = e.get("published_at", "")

            try:
                published = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except Exception:
                published = datetime.utcnow()

            entries.append(NewsEntry(
                id=e["id"],
                feed_id=e.get("feed_id", 0),
                feed_title=feed.get("title", "Unknown Feed"),
                title=e.get("title", ""),
                url=e.get("url", ""),
                content=e.get("content", ""),
                author=e.get("author", ""),
                published_at=published,
                reading_time=e.get("reading_time", 0),
                starred=e.get("starred", False),
                status=e.get("status", "unread"),
            ))

        return entries

    async def get_unread_count(self) -> int:
        """Get total unread count."""
        data = await self._request("GET", "/entries", params={"status": "unread", "limit": 1})
        if data and "total" in data:
            return data["total"]
        return 0

    async def mark_entry_read(self, entry_id: int) -> bool:
        """Mark an entry as read."""
        result = await self._request(
            "PUT",
            f"/entries/{entry_id}",
            json={"status": "read"},
        )
        return result is not None

    async def star_entry(self, entry_id: int) -> bool:
        """Star/bookmark an entry."""
        result = await self._request("PUT", f"/entries/{entry_id}/bookmark")
        return result is not None

    async def refresh_feeds(self) -> bool:
        """Trigger feed refresh."""
        result = await self._request("PUT", "/feeds/refresh")
        return result is not None

    async def get_summary(self) -> NewsSummary:
        """Get comprehensive news summary."""
        # Get feeds and entries in parallel
        feeds_task = asyncio.create_task(self.get_feeds())
        entries_task = asyncio.create_task(self.get_entries(limit=100))
        unread_task = asyncio.create_task(self.get_unread_count())

        feeds = await feeds_task
        entries = await entries_task
        unread_count = await unread_task

        # Category counts
        categories: Dict[str, int] = {}
        for feed in feeds:
            cat = feed.category_title
            categories[cat] = categories.get(cat, 0) + 1

        # Filter by topics
        topic_matches = self.topic_monitor.filter_entries(entries)

        # Sort entries by date
        entries.sort(key=lambda e: e.published_at, reverse=True)

        return NewsSummary(
            total_unread=unread_count,
            feeds_count=len(feeds),
            categories=categories,
            recent_entries=entries[:20],
            topic_matches=topic_matches,
        )

    async def get_morning_briefing_data(self) -> Dict[str, Any]:
        """Get news data formatted for morning briefing."""
        if not self.is_configured():
            return {
                "configured": False,
                "data": None,
            }

        summary = await self.get_summary()
        topics = self.topic_monitor.get_topics()

        # Format for briefing
        return {
            "configured": True,
            "unread_total": summary.total_unread,
            "feeds_count": summary.feeds_count,
            "monitored_topics": topics,
            "topic_alerts": [
                {
                    "topic": topic,
                    "count": len(entries),
                    "headlines": [e.title for e in entries[:3]],
                }
                for topic, entries in summary.topic_matches.items()
            ],
            "top_headlines": [
                {
                    "title": e.title,
                    "source": e.feed_title,
                    "age_hours": round(e.age_hours(), 1),
                }
                for e in summary.recent_entries[:5]
            ],
        }


# =============================================================================
# Pydantic Models
# =============================================================================

class TopicRequest(BaseModel):
    topic: str


class EntryActionRequest(BaseModel):
    entry_id: int


# =============================================================================
# Singleton Client Instance
# =============================================================================

_miniflux_client: Optional[MinifluxClient] = None


def get_miniflux_client() -> MinifluxClient:
    """Get or create Miniflux client singleton."""
    global _miniflux_client
    if _miniflux_client is None:
        _miniflux_client = MinifluxClient()
    return _miniflux_client


# =============================================================================
# FastAPI Router
# =============================================================================

def create_news_router() -> APIRouter:
    """Create news API router."""
    router = APIRouter(prefix="/news", tags=["news"])

    @router.get("/status")
    async def get_status():
        """Get news integration status."""
        client = get_miniflux_client()
        configured = client.is_configured()

        result = {
            "configured": configured,
            "miniflux_url": MINIFLUX_URL,
            "monitored_topics": client.topic_monitor.get_topics(),
        }

        if configured:
            user = await client.get_me()
            if user:
                result["authenticated"] = True
                result["username"] = user.get("username")
            else:
                result["authenticated"] = False

        return result

    @router.get("/summary")
    async def get_summary():
        """Get comprehensive news summary."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(
                status_code=401,
                detail="Miniflux not configured. Set MINIFLUX_API_KEY or MINIFLUX_USERNAME/PASSWORD",
            )

        summary = await client.get_summary()
        return summary.to_dict()

    @router.get("/feeds")
    async def get_feeds():
        """Get all subscribed feeds."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        feeds = await client.get_feeds()
        return {
            "count": len(feeds),
            "feeds": [f.to_dict() for f in feeds],
        }

    @router.get("/entries")
    async def get_entries(
        status: str = Query("unread", description="Filter by status: unread, read, removed"),
        limit: int = Query(50, ge=1, le=100),
        topic: Optional[str] = Query(None, description="Filter by topic keyword"),
    ):
        """Get news entries."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        entries = await client.get_entries(status=status, limit=limit)

        # Filter by topic if specified
        if topic:
            entries = [e for e in entries if e.matches_topics([topic])]

        return {
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }

    @router.get("/unread")
    async def get_unread_count():
        """Get unread entry count."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        count = await client.get_unread_count()
        return {"unread_count": count}

    @router.post("/refresh")
    async def refresh_feeds():
        """Trigger feed refresh."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        success = await client.refresh_feeds()
        return {"status": "refreshing" if success else "failed"}

    @router.post("/entries/read")
    async def mark_read(request: EntryActionRequest):
        """Mark an entry as read."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        success = await client.mark_entry_read(request.entry_id)
        return {"status": "read" if success else "failed"}

    @router.post("/entries/star")
    async def star_entry(request: EntryActionRequest):
        """Star/bookmark an entry."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        success = await client.star_entry(request.entry_id)
        return {"status": "starred" if success else "failed"}

    # Topic monitoring endpoints
    @router.get("/topics")
    async def get_topics():
        """Get monitored topics."""
        client = get_miniflux_client()
        return {"topics": client.topic_monitor.get_topics()}

    @router.post("/topics")
    async def add_topic(request: TopicRequest):
        """Add a topic to monitor."""
        client = get_miniflux_client()
        client.topic_monitor.add_topic(request.topic)
        return {"status": "added", "topic": request.topic}

    @router.delete("/topics")
    async def remove_topic(request: TopicRequest):
        """Remove a monitored topic."""
        client = get_miniflux_client()
        client.topic_monitor.remove_topic(request.topic)
        return {"status": "removed", "topic": request.topic}

    @router.get("/topics/matches")
    async def get_topic_matches():
        """Get entries matching monitored topics."""
        client = get_miniflux_client()
        if not client.is_configured():
            raise HTTPException(status_code=401, detail="Miniflux not configured")

        entries = await client.get_entries(limit=100)
        matches = client.topic_monitor.filter_entries(entries)

        return {
            "topics": client.topic_monitor.get_topics(),
            "matches": {
                topic: [e.to_dict() for e in entries_list[:10]]
                for topic, entries_list in matches.items()
            },
        }

    @router.get("/morning-briefing-data")
    async def get_morning_briefing_data():
        """Get news data formatted for morning briefing."""
        client = get_miniflux_client()
        return await client.get_morning_briefing_data()

    return router
