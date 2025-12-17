"""
HYDRA Discovery Archive System

Enables cross-session learning by archiving:
- Successful improvements (code changes that improved benchmarks)
- Discovered patterns (reusable solutions)
- Failures (what didn't work - equally valuable)
- Benchmark history (track progress over time)
- Session summaries (context for future sessions)

This is the foundation for Darwin Gödel Machine-style self-improvement.

Usage:
    # Archive a discovery
    POST /discoveries/archive
    {
        "type": "improvement",
        "title": "Fixed context handling for TabbyAPI",
        "description": "Combined system+user messages for TabbyAPI compatibility",
        "code_diff": "...",
        "benchmark_before": 55.6,
        "benchmark_after": 88.9,
        "tags": ["benchmark", "tabbyapi", "inference"]
    }

    # Search discoveries
    GET /discoveries/search?query=tabbyapi&type=improvement

    # Get relevant discoveries for current context
    POST /discoveries/relevant
    {"context": "I'm working on improving inference speed"}
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


# =============================================================================
# Configuration
# =============================================================================

ARCHIVE_BASE = os.environ.get(
    "HYDRA_DISCOVERY_DIR",
    "/data/discoveries"
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")
EMBED_MODEL = "nomic-embed-text:latest"


class DiscoveryType(str, Enum):
    """Types of discoveries that can be archived."""
    IMPROVEMENT = "improvement"      # Successful code/config improvements
    PATTERN = "pattern"              # Reusable solution patterns
    FAILURE = "failure"              # What didn't work (valuable learning)
    BENCHMARK = "benchmark"          # Historical benchmark results
    SESSION = "session"              # Session summaries


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Discovery:
    """A single archived discovery."""
    id: str
    type: DiscoveryType
    title: str
    description: str
    created_at: str
    tags: List[str] = field(default_factory=list)

    # Optional fields depending on type
    code_diff: Optional[str] = None
    benchmark_before: Optional[float] = None
    benchmark_after: Optional[float] = None
    files_modified: Optional[List[str]] = None
    error_message: Optional[str] = None
    solution: Optional[str] = None
    context: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class ArchiveRequest(BaseModel):
    """Request to archive a discovery."""
    type: str
    title: str
    description: str
    tags: Optional[List[str]] = None
    code_diff: Optional[str] = None
    benchmark_before: Optional[float] = None
    benchmark_after: Optional[float] = None
    files_modified: Optional[List[str]] = None
    error_message: Optional[str] = None
    solution: Optional[str] = None
    context: Optional[str] = None


class SearchRequest(BaseModel):
    """Request to search discoveries."""
    query: str
    type: Optional[str] = None
    limit: int = 10


class RelevantRequest(BaseModel):
    """Request to find relevant discoveries for context."""
    context: str
    limit: int = 5


# =============================================================================
# Embedding Service
# =============================================================================

class DiscoveryEmbedding:
    """Generate embeddings for semantic search of discoveries."""

    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = EMBED_MODEL):
        self.ollama_url = ollama_url
        self.model = model

    async def embed(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embed",
                    json={"model": self.model, "input": text}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embeddings", [[]])[0]
        except Exception as e:
            print(f"Embedding error: {e}")
        return None

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# =============================================================================
# Discovery Archive Manager
# =============================================================================

class DiscoveryArchive:
    """Manages the discovery archive."""

    def __init__(self, base_path: str = ARCHIVE_BASE):
        self.base_path = Path(base_path)
        self.embedder = DiscoveryEmbedding()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure archive directories exist."""
        for discovery_type in DiscoveryType:
            type_dir = self.base_path / discovery_type.value
            type_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, discovery_type: DiscoveryType, discovery_id: str) -> Path:
        """Get path for a discovery file."""
        return self.base_path / discovery_type.value / f"{discovery_id}.json"

    async def archive(self, request: ArchiveRequest) -> Discovery:
        """Archive a new discovery."""
        # Validate type
        try:
            disc_type = DiscoveryType(request.type)
        except ValueError:
            raise HTTPException(400, f"Invalid type: {request.type}")

        # Generate ID
        discovery_id = str(uuid.uuid4())[:8]

        # Generate embedding for semantic search
        embed_text = f"{request.title} {request.description}"
        embedding = await self.embedder.embed(embed_text)

        # Create discovery
        discovery = Discovery(
            id=discovery_id,
            type=disc_type,
            title=request.title,
            description=request.description,
            created_at=datetime.utcnow().isoformat() + "Z",
            tags=request.tags or [],
            code_diff=request.code_diff,
            benchmark_before=request.benchmark_before,
            benchmark_after=request.benchmark_after,
            files_modified=request.files_modified,
            error_message=request.error_message,
            solution=request.solution,
            context=request.context,
            embedding=embedding,
        )

        # Save to file
        path = self._get_path(disc_type, discovery_id)
        with open(path, "w") as f:
            json.dump(discovery.to_dict(), f, indent=2)

        return discovery

    def list_all(self, discovery_type: Optional[DiscoveryType] = None) -> List[Discovery]:
        """List all discoveries, optionally filtered by type."""
        discoveries = []

        types_to_search = [discovery_type] if discovery_type else list(DiscoveryType)

        for dt in types_to_search:
            type_dir = self.base_path / dt.value
            if type_dir.exists():
                for file in type_dir.glob("*.json"):
                    try:
                        with open(file) as f:
                            data = json.load(f)
                            # Convert type string back to enum
                            if isinstance(data.get("type"), str):
                                data["type"] = DiscoveryType(data["type"])
                            discoveries.append(Discovery(**data))
                    except Exception:
                        continue

        # Sort by created_at descending
        discoveries.sort(key=lambda d: d.created_at, reverse=True)
        return discoveries

    async def search(self, query: str, discovery_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search discoveries by query."""
        # Get all discoveries
        dt = DiscoveryType(discovery_type) if discovery_type else None
        all_discoveries = self.list_all(dt)

        # Generate query embedding
        query_embedding = await self.embedder.embed(query)

        results = []
        for discovery in all_discoveries:
            score = 0.0

            # Keyword match
            query_lower = query.lower()
            if query_lower in discovery.title.lower():
                score += 0.5
            if query_lower in discovery.description.lower():
                score += 0.3
            if any(query_lower in tag.lower() for tag in discovery.tags):
                score += 0.2

            # Semantic match
            if query_embedding and discovery.embedding:
                semantic_score = self.embedder.cosine_similarity(
                    query_embedding, discovery.embedding
                )
                score += semantic_score * 0.5

            if score > 0.1:
                result = discovery.to_dict()
                result["score"] = round(score, 3)
                results.append(result)

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def find_relevant(self, context: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find discoveries relevant to current context."""
        return await self.search(context, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get archive statistics."""
        stats = {
            "total": 0,
            "by_type": {},
            "recent": [],
        }

        for dt in DiscoveryType:
            type_dir = self.base_path / dt.value
            if type_dir.exists():
                count = len(list(type_dir.glob("*.json")))
                stats["by_type"][dt.value] = count
                stats["total"] += count

        # Get 5 most recent
        all_discoveries = self.list_all()
        stats["recent"] = [
            {"id": d.id, "type": d.type.value, "title": d.title, "created_at": d.created_at}
            for d in all_discoveries[:5]
        ]

        return stats

    def get_discovery(self, discovery_id: str) -> Optional[Discovery]:
        """Get a specific discovery by ID."""
        for dt in DiscoveryType:
            path = self._get_path(dt, discovery_id)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    return Discovery(**data)
        return None


# =============================================================================
# Global Instance
# =============================================================================

_archive: Optional[DiscoveryArchive] = None


def get_archive() -> DiscoveryArchive:
    """Get or create the global archive instance."""
    global _archive
    if _archive is None:
        _archive = DiscoveryArchive()
    return _archive


# =============================================================================
# FastAPI Router
# =============================================================================

def create_discovery_router() -> APIRouter:
    """Create FastAPI router for discovery archive endpoints."""
    router = APIRouter(prefix="/discoveries", tags=["discoveries"])

    @router.get("/status")
    async def get_status():
        """Get archive status and statistics."""
        archive = get_archive()
        return {
            "status": "operational",
            "base_path": str(archive.base_path),
            "stats": archive.get_stats(),
        }

    @router.post("/archive")
    async def archive_discovery(request: ArchiveRequest):
        """Archive a new discovery."""
        archive = get_archive()
        discovery = await archive.archive(request)
        return {
            "status": "archived",
            "discovery": {
                "id": discovery.id,
                "type": discovery.type.value,
                "title": discovery.title,
            }
        }

    @router.get("/list")
    async def list_discoveries(type: Optional[str] = None, limit: int = 50):
        """List all discoveries."""
        archive = get_archive()
        dt = DiscoveryType(type) if type else None
        discoveries = archive.list_all(dt)[:limit]
        return {
            "count": len(discoveries),
            "discoveries": [
                {
                    "id": d.id,
                    "type": d.type.value,
                    "title": d.title,
                    "description": d.description[:200] + "..." if len(d.description) > 200 else d.description,
                    "created_at": d.created_at,
                    "tags": d.tags,
                }
                for d in discoveries
            ]
        }

    @router.post("/search")
    async def search_discoveries(request: SearchRequest):
        """Search discoveries by query."""
        archive = get_archive()
        results = await archive.search(
            query=request.query,
            discovery_type=request.type,
            limit=request.limit
        )
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }

    @router.post("/relevant")
    async def find_relevant(request: RelevantRequest):
        """Find discoveries relevant to current context."""
        archive = get_archive()
        results = await archive.find_relevant(
            context=request.context,
            limit=request.limit
        )
        return {
            "context": request.context[:100] + "..." if len(request.context) > 100 else request.context,
            "count": len(results),
            "discoveries": results,
        }

    @router.get("/{discovery_id}")
    async def get_discovery(discovery_id: str):
        """Get a specific discovery by ID."""
        archive = get_archive()
        discovery = archive.get_discovery(discovery_id)
        if not discovery:
            raise HTTPException(404, f"Discovery {discovery_id} not found")
        return discovery.to_dict()

    @router.post("/archive-session")
    async def archive_session(
        summary: str,
        accomplishments: List[str],
        improvements: Optional[List[str]] = None,
        failures: Optional[List[str]] = None,
    ):
        """Archive a session summary for future reference."""
        archive = get_archive()

        # Create session discovery
        session = await archive.archive(ArchiveRequest(
            type="session",
            title=f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=summary,
            tags=["session", datetime.utcnow().strftime("%Y-%m-%d")],
            context=json.dumps({
                "accomplishments": accomplishments,
                "improvements": improvements or [],
                "failures": failures or [],
            })
        ))

        return {
            "status": "archived",
            "session_id": session.id,
        }

    @router.get("/improvements/successful")
    async def get_successful_improvements(limit: int = 20):
        """Get improvements that resulted in benchmark increases."""
        archive = get_archive()
        improvements = archive.list_all(DiscoveryType.IMPROVEMENT)

        # Filter to those with positive benchmark delta
        successful = [
            {
                "id": d.id,
                "title": d.title,
                "description": d.description,
                "benchmark_before": d.benchmark_before,
                "benchmark_after": d.benchmark_after,
                "improvement": (d.benchmark_after - d.benchmark_before) if d.benchmark_before and d.benchmark_after else None,
                "tags": d.tags,
            }
            for d in improvements
            if d.benchmark_before and d.benchmark_after and d.benchmark_after > d.benchmark_before
        ]

        successful.sort(key=lambda x: x["improvement"] or 0, reverse=True)
        return {
            "count": len(successful[:limit]),
            "improvements": successful[:limit],
        }

    return router


# =============================================================================
# Utility Functions for Other Modules
# =============================================================================

async def archive_improvement(
    title: str,
    description: str,
    code_diff: str,
    benchmark_before: float,
    benchmark_after: float,
    files_modified: List[str],
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience function to archive an improvement."""
    archive = get_archive()
    discovery = await archive.archive(ArchiveRequest(
        type="improvement",
        title=title,
        description=description,
        code_diff=code_diff,
        benchmark_before=benchmark_before,
        benchmark_after=benchmark_after,
        files_modified=files_modified,
        tags=tags or [],
    ))
    return discovery.id


async def archive_failure(
    title: str,
    description: str,
    error_message: str,
    context: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience function to archive a failure (for learning)."""
    archive = get_archive()
    discovery = await archive.archive(ArchiveRequest(
        type="failure",
        title=title,
        description=description,
        error_message=error_message,
        context=context,
        tags=tags or [],
    ))
    return discovery.id


async def archive_pattern(
    title: str,
    description: str,
    solution: str,
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience function to archive a reusable pattern."""
    archive = get_archive()
    discovery = await archive.archive(ArchiveRequest(
        type="pattern",
        title=title,
        description=description,
        solution=solution,
        tags=tags or [],
    ))
    return discovery.id
