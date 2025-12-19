"""
News Intelligence for Hydra

Proactive news analysis and research suggestion generation:
- Trending topic detection
- Research opportunity identification
- Automatic research queue integration
- Topic relevance scoring

Author: Hydra Autonomous System
Phase: 14 - News & Research Enhancement (Week 24)
Created: 2025-12-18
"""

import asyncio
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(os.getenv("HYDRA_DATA_DIR", "/data"))
INTELLIGENCE_DIR = DATA_DIR / "research"
INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)

TRENDING_FILE = INTELLIGENCE_DIR / "trending_topics.json"
SUGGESTIONS_FILE = INTELLIGENCE_DIR / "research_suggestions.json"

# LLM endpoint for analysis
LITELLM_URL = os.getenv("LITELLM_URL", "http://192.168.1.244:4000")
RESEARCH_QUEUE_INTERNAL = "http://localhost:8700"

# Hydra's focus areas for relevance scoring
HYDRA_FOCUS_AREAS = [
    "artificial intelligence",
    "large language models",
    "autonomous agents",
    "local inference",
    "gpu optimization",
    "home automation",
    "smart home",
    "knowledge graphs",
    "memory systems",
    "speculative decoding",
    "model quantization",
    "mcp protocol",
    "rag systems",
    "voice synthesis",
    "computer vision",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TrendingTopic:
    """A trending topic detected from news."""
    topic: str
    mentions: int
    first_seen: datetime
    last_seen: datetime
    sources: List[str]
    relevance_score: float  # 0-1, how relevant to Hydra
    sample_headlines: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "mentions": self.mentions,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "sources": self.sources[:5],
            "relevance_score": self.relevance_score,
            "sample_headlines": self.sample_headlines[:3],
            "trending_hours": (datetime.utcnow() - self.first_seen).total_seconds() / 3600,
        }


@dataclass
class ResearchSuggestion:
    """A suggested research task based on news analysis."""
    id: str
    title: str
    description: str
    source_topic: str
    source_headlines: List[str]
    relevance_score: float
    priority: str  # high, normal, low
    suggested_queries: List[str]
    created_at: datetime
    status: str  # pending, queued, dismissed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source_topic": self.source_topic,
            "source_headlines": self.source_headlines[:3],
            "relevance_score": self.relevance_score,
            "priority": self.priority,
            "suggested_queries": self.suggested_queries,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


# =============================================================================
# News Intelligence Engine
# =============================================================================

class NewsIntelligenceEngine:
    """Analyzes news for trends and research opportunities."""

    def __init__(self):
        self.trending_topics: Dict[str, TrendingTopic] = {}
        self.suggestions: Dict[str, ResearchSuggestion] = {}
        self._load_state()

    def _load_state(self):
        """Load persisted state."""
        if TRENDING_FILE.exists():
            try:
                data = json.loads(TRENDING_FILE.read_text())
                for topic_data in data.get("topics", []):
                    topic = TrendingTopic(
                        topic=topic_data["topic"],
                        mentions=topic_data["mentions"],
                        first_seen=datetime.fromisoformat(topic_data["first_seen"]),
                        last_seen=datetime.fromisoformat(topic_data["last_seen"]),
                        sources=topic_data.get("sources", []),
                        relevance_score=topic_data.get("relevance_score", 0),
                        sample_headlines=topic_data.get("sample_headlines", []),
                    )
                    self.trending_topics[topic.topic] = topic
            except Exception as e:
                logger.warning(f"Failed to load trending topics: {e}")

        if SUGGESTIONS_FILE.exists():
            try:
                data = json.loads(SUGGESTIONS_FILE.read_text())
                for sugg_data in data.get("suggestions", []):
                    sugg = ResearchSuggestion(
                        id=sugg_data["id"],
                        title=sugg_data["title"],
                        description=sugg_data["description"],
                        source_topic=sugg_data["source_topic"],
                        source_headlines=sugg_data.get("source_headlines", []),
                        relevance_score=sugg_data.get("relevance_score", 0),
                        priority=sugg_data.get("priority", "normal"),
                        suggested_queries=sugg_data.get("suggested_queries", []),
                        created_at=datetime.fromisoformat(sugg_data["created_at"]),
                        status=sugg_data.get("status", "pending"),
                    )
                    self.suggestions[sugg.id] = sugg
            except Exception as e:
                logger.warning(f"Failed to load suggestions: {e}")

    def _save_state(self):
        """Persist state to files."""
        try:
            TRENDING_FILE.write_text(json.dumps({
                "topics": [t.to_dict() for t in self.trending_topics.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))

            SUGGESTIONS_FILE.write_text(json.dumps({
                "suggestions": [s.to_dict() for s in self.suggestions.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _extract_topics(self, text: str) -> List[str]:
        """Extract potential topics from text."""
        # Normalize
        text = text.lower()

        # Extract n-grams that might be topics
        words = re.findall(r'\b[a-z]{3,}\b', text)

        # Bigrams and trigrams
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]

        # Filter for potential tech/AI topics
        tech_indicators = [
            "ai", "model", "llm", "gpt", "claude", "gemini", "agent",
            "inference", "gpu", "nvidia", "amd", "memory", "rag",
            "vector", "embedding", "transformer", "attention", "token",
            "api", "cloud", "edge", "local", "open", "source", "weight",
            "quantization", "fine", "tune", "training", "benchmark",
            "performance", "speed", "latency", "throughput", "context",
            "reasoning", "chain", "thought", "multimodal", "vision",
            "voice", "speech", "synthesis", "tts", "stt", "assistant",
            "autonomous", "automation", "workflow", "pipeline", "mcp",
        ]

        potential_topics = []
        for phrase in bigrams + trigrams:
            if any(ind in phrase for ind in tech_indicators):
                potential_topics.append(phrase)

        return potential_topics

    def _calculate_relevance(self, topic: str) -> float:
        """Calculate relevance score for Hydra."""
        topic_lower = topic.lower()
        score = 0.0

        for focus in HYDRA_FOCUS_AREAS:
            if focus in topic_lower or topic_lower in focus:
                score += 0.3
            elif any(word in topic_lower for word in focus.split()):
                score += 0.1

        return min(score, 1.0)

    async def analyze_news_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze news entries for trends and opportunities."""
        now = datetime.utcnow()

        # Extract topics from all entries
        topic_counter: Counter = Counter()
        topic_sources: Dict[str, Set[str]] = {}
        topic_headlines: Dict[str, List[str]] = {}

        for entry in entries:
            title = entry.get("title", "")
            content = entry.get("content_preview", "")
            source = entry.get("feed_title", "Unknown")

            text = f"{title} {content}"
            topics = self._extract_topics(text)

            for topic in topics:
                topic_counter[topic] += 1
                if topic not in topic_sources:
                    topic_sources[topic] = set()
                    topic_headlines[topic] = []
                topic_sources[topic].add(source)
                if title and title not in topic_headlines[topic]:
                    topic_headlines[topic].append(title)

        # Update trending topics (minimum 2 mentions)
        new_trending = 0
        for topic, count in topic_counter.most_common(50):
            if count < 2:
                continue

            relevance = self._calculate_relevance(topic)

            if topic in self.trending_topics:
                # Update existing
                existing = self.trending_topics[topic]
                existing.mentions += count
                existing.last_seen = now
                existing.sources = list(set(existing.sources) | topic_sources[topic])[:10]
                existing.sample_headlines = list(set(existing.sample_headlines) | set(topic_headlines[topic]))[:5]
            else:
                # New trending topic
                self.trending_topics[topic] = TrendingTopic(
                    topic=topic,
                    mentions=count,
                    first_seen=now,
                    last_seen=now,
                    sources=list(topic_sources[topic])[:10],
                    relevance_score=relevance,
                    sample_headlines=topic_headlines[topic][:5],
                )
                new_trending += 1

        # Prune old topics (>48 hours without update)
        cutoff = now - timedelta(hours=48)
        self.trending_topics = {
            k: v for k, v in self.trending_topics.items()
            if v.last_seen > cutoff
        }

        self._save_state()

        return {
            "analyzed_entries": len(entries),
            "topics_detected": len(topic_counter),
            "trending_topics": len(self.trending_topics),
            "new_trending": new_trending,
            "top_topics": [
                self.trending_topics[t].to_dict()
                for t in sorted(
                    self.trending_topics.keys(),
                    key=lambda x: self.trending_topics[x].mentions,
                    reverse=True
                )[:10]
            ],
        }

    async def generate_research_suggestions(self) -> List[ResearchSuggestion]:
        """Generate research suggestions from trending topics."""
        suggestions = []

        # Get high-relevance trending topics
        relevant_topics = [
            t for t in self.trending_topics.values()
            if t.relevance_score >= 0.3 and t.mentions >= 3
        ]

        # Sort by relevance * mentions (impact score)
        relevant_topics.sort(
            key=lambda t: t.relevance_score * t.mentions,
            reverse=True
        )

        for topic in relevant_topics[:5]:
            # Check if we already have a suggestion for this topic
            existing = [s for s in self.suggestions.values() if s.source_topic == topic.topic]
            if existing and existing[0].status != "dismissed":
                continue

            # Generate suggestion
            suggestion_id = f"sugg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hash(topic.topic) % 10000}"

            # Determine priority based on relevance and mentions
            if topic.relevance_score >= 0.6 and topic.mentions >= 5:
                priority = "high"
            elif topic.relevance_score >= 0.4:
                priority = "normal"
            else:
                priority = "low"

            suggestion = ResearchSuggestion(
                id=suggestion_id,
                title=f"Research: {topic.topic.title()}",
                description=f"Trending topic '{topic.topic}' detected in {topic.mentions} articles from {len(topic.sources)} sources. "
                           f"Relevance to Hydra: {topic.relevance_score:.0%}",
                source_topic=topic.topic,
                source_headlines=topic.sample_headlines,
                relevance_score=topic.relevance_score,
                priority=priority,
                suggested_queries=[
                    f"{topic.topic} latest developments 2025",
                    f"{topic.topic} implementation guide",
                    f"{topic.topic} vs alternatives comparison",
                ],
                created_at=datetime.utcnow(),
                status="pending",
            )

            self.suggestions[suggestion.id] = suggestion
            suggestions.append(suggestion)

        self._save_state()
        return suggestions

    async def queue_suggestion(self, suggestion_id: str) -> Dict[str, Any]:
        """Queue a research suggestion for processing."""
        if suggestion_id not in self.suggestions:
            raise ValueError(f"Suggestion not found: {suggestion_id}")

        suggestion = self.suggestions[suggestion_id]

        # Queue to research system
        try:
            async with httpx.AsyncClient() as client:
                # Queue the main topic as a research item
                response = await client.post(
                    f"{RESEARCH_QUEUE_INTERNAL}/research/queue",
                    json={
                        "source": suggestion.suggested_queries[0],
                        "source_type": "text",
                        "topic": suggestion.source_topic,
                        "priority": suggestion.priority,
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    suggestion.status = "queued"
                    self._save_state()
                    return {
                        "success": True,
                        "message": f"Research queued for '{suggestion.source_topic}'",
                        "suggestion_id": suggestion_id,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to queue: {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Failed to queue suggestion: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        """Dismiss a research suggestion."""
        if suggestion_id in self.suggestions:
            self.suggestions[suggestion_id].status = "dismissed"
            self._save_state()
            return True
        return False

    def get_trending_summary(self) -> Dict[str, Any]:
        """Get summary of trending topics."""
        topics = list(self.trending_topics.values())
        topics.sort(key=lambda t: t.mentions, reverse=True)

        high_relevance = [t for t in topics if t.relevance_score >= 0.5]
        medium_relevance = [t for t in topics if 0.2 <= t.relevance_score < 0.5]

        return {
            "total_trending": len(topics),
            "high_relevance_count": len(high_relevance),
            "medium_relevance_count": len(medium_relevance),
            "top_10": [t.to_dict() for t in topics[:10]],
            "high_relevance": [t.to_dict() for t in high_relevance[:5]],
            "pending_suggestions": len([s for s in self.suggestions.values() if s.status == "pending"]),
        }

    def get_suggestions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get research suggestions."""
        suggestions = list(self.suggestions.values())
        if status:
            suggestions = [s for s in suggestions if s.status == status]
        suggestions.sort(key=lambda s: s.created_at, reverse=True)
        return [s.to_dict() for s in suggestions]


# =============================================================================
# Singleton Instance
# =============================================================================

_intelligence_engine: Optional[NewsIntelligenceEngine] = None


def get_intelligence_engine() -> NewsIntelligenceEngine:
    """Get or create intelligence engine singleton."""
    global _intelligence_engine
    if _intelligence_engine is None:
        _intelligence_engine = NewsIntelligenceEngine()
    return _intelligence_engine


# =============================================================================
# Pydantic Models
# =============================================================================

class AnalyzeRequest(BaseModel):
    entries: List[Dict[str, Any]]


class SuggestionActionRequest(BaseModel):
    suggestion_id: str


# =============================================================================
# FastAPI Router
# =============================================================================

def create_news_intelligence_router() -> APIRouter:
    """Create news intelligence API router."""
    router = APIRouter(prefix="/news/intelligence", tags=["news-intelligence"])

    @router.get("/status")
    async def get_status():
        """Get news intelligence status."""
        engine = get_intelligence_engine()
        return engine.get_trending_summary()

    @router.get("/trending")
    async def get_trending(
        min_relevance: float = Query(0.0, ge=0.0, le=1.0),
        limit: int = Query(20, ge=1, le=100),
    ):
        """Get trending topics."""
        engine = get_intelligence_engine()
        topics = list(engine.trending_topics.values())
        topics = [t for t in topics if t.relevance_score >= min_relevance]
        topics.sort(key=lambda t: t.mentions * t.relevance_score, reverse=True)
        return {
            "count": len(topics),
            "topics": [t.to_dict() for t in topics[:limit]],
        }

    @router.post("/analyze")
    async def analyze_entries(request: AnalyzeRequest, background_tasks: BackgroundTasks):
        """Analyze news entries for trends."""
        engine = get_intelligence_engine()
        result = await engine.analyze_news_entries(request.entries)

        # Generate suggestions in background
        background_tasks.add_task(engine.generate_research_suggestions)

        return result

    @router.post("/analyze-from-feed")
    async def analyze_from_feed():
        """Fetch and analyze latest news from Miniflux."""
        engine = get_intelligence_engine()

        # Fetch from news endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{RESEARCH_QUEUE_INTERNAL}/news/entries",
                    params={"limit": 100},
                    timeout=30,
                )
                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": "Failed to fetch news entries",
                        "status_code": response.status_code,
                    }

                data = response.json()
                entries = data.get("entries", [])

                if not entries:
                    return {
                        "success": True,
                        "message": "No entries to analyze",
                        "analyzed": 0,
                    }

                result = await engine.analyze_news_entries(entries)
                suggestions = await engine.generate_research_suggestions()

                return {
                    "success": True,
                    **result,
                    "new_suggestions": len(suggestions),
                }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "message": f"News fetch failed: {e}",
            }

    @router.get("/suggestions")
    async def get_suggestions(
        status: Optional[str] = Query(None, description="Filter by status: pending, queued, dismissed"),
    ):
        """Get research suggestions."""
        engine = get_intelligence_engine()
        suggestions = engine.get_suggestions(status)
        return {
            "count": len(suggestions),
            "suggestions": suggestions,
        }

    @router.post("/suggestions/generate")
    async def generate_suggestions():
        """Generate new research suggestions from trending topics."""
        engine = get_intelligence_engine()
        suggestions = await engine.generate_research_suggestions()
        return {
            "generated": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }

    @router.post("/suggestions/queue")
    async def queue_suggestion(request: SuggestionActionRequest):
        """Queue a research suggestion for processing."""
        engine = get_intelligence_engine()
        try:
            result = await engine.queue_suggestion(request.suggestion_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/suggestions/dismiss")
    async def dismiss_suggestion(request: SuggestionActionRequest):
        """Dismiss a research suggestion."""
        engine = get_intelligence_engine()
        if engine.dismiss_suggestion(request.suggestion_id):
            return {"success": True, "message": "Suggestion dismissed"}
        raise HTTPException(status_code=404, detail="Suggestion not found")

    @router.get("/focus-areas")
    async def get_focus_areas():
        """Get Hydra's focus areas for relevance scoring."""
        return {
            "focus_areas": HYDRA_FOCUS_AREAS,
            "description": "Topics matching these areas receive higher relevance scores",
        }

    @router.post("/focus-areas/add")
    async def add_focus_area(area: str = Query(..., min_length=3)):
        """Add a focus area for relevance scoring."""
        if area.lower() not in HYDRA_FOCUS_AREAS:
            HYDRA_FOCUS_AREAS.append(area.lower())
            return {"success": True, "message": f"Added focus area: {area}"}
        return {"success": False, "message": "Focus area already exists"}

    return router
