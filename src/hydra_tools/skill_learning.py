"""
Skill Learning System - Enhanced Procedural Memory

Extends MIRIX memory architecture with:
1. Agent Files (.af) - Portable agent serialization
2. Skill Library - Browsable skill repository
3. Skill Improvement - Track and improve skills over time
4. Multi-Agent Skill Sharing - Share skills between agents

Part of 2.2 Letta Memory Upgrade.

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import json
import logging
import os
import uuid
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Agent File Format (.af)
# =============================================================================

@dataclass
class AgentFile:
    """
    Agent File (.af) - Portable agent serialization format.

    Contains everything needed to recreate an agent:
    - Core identity and persona
    - Learned skills (procedural memory)
    - Key facts (semantic memory)
    - Conversation style preferences
    - Tool usage patterns
    """
    version: str = "1.0"
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    agent_type: str = "generic"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    exported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Core identity
    persona: Dict[str, Any] = field(default_factory=dict)

    # Learned skills
    skills: List[Dict[str, Any]] = field(default_factory=list)

    # Key facts
    facts: List[Dict[str, Any]] = field(default_factory=list)

    # Conversation style
    style_preferences: Dict[str, Any] = field(default_factory=dict)

    # Tool usage patterns
    tool_patterns: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentFile":
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentFile":
        return cls.from_dict(json.loads(json_str))


# =============================================================================
# Skill Library Entry
# =============================================================================

@dataclass
class SkillLibraryEntry:
    """A skill in the shared library."""
    skill_id: str
    name: str
    description: str
    category: str
    trigger_conditions: List[str]
    steps: List[str]
    success_rate: float = 0.0
    execution_count: int = 0
    avg_execution_time_ms: float = 0.0
    created_by_agent: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Skill Learning Manager
# =============================================================================

class SkillLearningManager:
    """
    Manages skill learning, improvement, and sharing across agents.

    Features:
    - Track skill execution success/failure
    - Improve skills based on feedback
    - Export/import agent files
    - Share skills between agents
    """

    def __init__(
        self,
        data_dir: str = "/data/skills",
        qdrant_url: str = "http://192.168.1.244:6333",
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skills_file = self.data_dir / "skill_library.json"
        self.agents_dir = self.data_dir / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.qdrant_url = qdrant_url

        # In-memory skill library (persisted to JSON)
        self.skill_library: Dict[str, SkillLibraryEntry] = {}
        self._load_skill_library()

    def _load_skill_library(self):
        """Load skill library from disk."""
        if self.skills_file.exists():
            try:
                with open(self.skills_file) as f:
                    data = json.load(f)
                    for skill_id, skill_data in data.items():
                        self.skill_library[skill_id] = SkillLibraryEntry(**skill_data)
                logger.info(f"Loaded {len(self.skill_library)} skills from library")
            except Exception as e:
                logger.error(f"Failed to load skill library: {e}")

    def _save_skill_library(self):
        """Save skill library to disk."""
        try:
            data = {sid: s.to_dict() for sid, s in self.skill_library.items()}
            with open(self.skills_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skill library: {e}")

    # =========================================================================
    # Skill Library Operations
    # =========================================================================

    def add_skill(
        self,
        name: str,
        description: str,
        category: str,
        trigger_conditions: List[str],
        steps: List[str],
        tags: Optional[List[str]] = None,
        created_by_agent: Optional[str] = None,
    ) -> str:
        """Add a new skill to the library."""
        skill_id = str(uuid.uuid4())[:8]

        skill = SkillLibraryEntry(
            skill_id=skill_id,
            name=name,
            description=description,
            category=category,
            trigger_conditions=trigger_conditions,
            steps=steps,
            tags=tags or [],
            created_by_agent=created_by_agent,
        )

        self.skill_library[skill_id] = skill
        self._save_skill_library()

        logger.info(f"Added skill to library: {name} (id={skill_id})")
        return skill_id

    def record_execution(
        self,
        skill_id: str,
        success: bool,
        execution_time_ms: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Record a skill execution for learning."""
        if skill_id not in self.skill_library:
            return

        skill = self.skill_library[skill_id]
        skill.execution_count += 1

        # Update success rate (running average)
        prev_successes = skill.success_rate * (skill.execution_count - 1)
        new_successes = prev_successes + (1.0 if success else 0.0)
        skill.success_rate = new_successes / skill.execution_count

        # Update average execution time
        prev_total_time = skill.avg_execution_time_ms * (skill.execution_count - 1)
        skill.avg_execution_time_ms = (prev_total_time + execution_time_ms) / skill.execution_count

        skill.updated_at = datetime.utcnow().isoformat()

        # Store example if provided
        if context:
            skill.examples.append({
                "context": context,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })
            # Keep only last 10 examples
            skill.examples = skill.examples[-10:]

        self._save_skill_library()
        logger.debug(f"Recorded execution for skill {skill_id}: success={success}")

    def get_skill(self, skill_id: str) -> Optional[SkillLibraryEntry]:
        """Get a skill by ID."""
        return self.skill_library.get(skill_id)

    def search_skills(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: float = 0.0,
    ) -> List[SkillLibraryEntry]:
        """Search skills in the library."""
        results = []

        for skill in self.skill_library.values():
            # Filter by category
            if category and skill.category != category:
                continue

            # Filter by tags
            if tags and not any(t in skill.tags for t in tags):
                continue

            # Filter by success rate
            if skill.success_rate < min_success_rate:
                continue

            # Filter by query (name or description)
            if query:
                query_lower = query.lower()
                if query_lower not in skill.name.lower() and query_lower not in skill.description.lower():
                    continue

            results.append(skill)

        # Sort by success rate and execution count
        results.sort(key=lambda s: (s.success_rate, s.execution_count), reverse=True)
        return results

    def get_categories(self) -> List[str]:
        """Get all skill categories."""
        return list(set(s.category for s in self.skill_library.values()))

    def get_top_skills(self, limit: int = 10) -> List[SkillLibraryEntry]:
        """Get top performing skills."""
        skills = list(self.skill_library.values())
        # Sort by success rate * execution_count (proven effective skills)
        skills.sort(
            key=lambda s: s.success_rate * min(s.execution_count, 100),
            reverse=True
        )
        return skills[:limit]

    # =========================================================================
    # Agent File Operations
    # =========================================================================

    async def export_agent(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str = "generic",
        include_skills: bool = True,
        include_facts: bool = True,
    ) -> AgentFile:
        """Export an agent to an Agent File."""
        af = AgentFile(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            exported_at=datetime.utcnow().isoformat(),
        )

        # Get skills from memory architecture
        if include_skills:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "http://localhost:8700/memory/procedural",
                        params={"limit": 100}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        af.skills = data.get("memories", [])
            except Exception as e:
                logger.warning(f"Failed to export skills: {e}")

        # Get key facts from semantic memory
        if include_facts:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "http://localhost:8700/memory/semantic",
                        params={"limit": 100}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        af.facts = data.get("memories", [])
            except Exception as e:
                logger.warning(f"Failed to export facts: {e}")

        # Save to disk
        agent_file_path = self.agents_dir / f"{agent_id}.af.json"
        with open(agent_file_path, "w") as f:
            f.write(af.to_json())

        logger.info(f"Exported agent {agent_name} to {agent_file_path}")
        return af

    async def import_agent(self, agent_file: AgentFile) -> Dict[str, Any]:
        """Import an agent from an Agent File."""
        result = {
            "agent_id": agent_file.agent_id,
            "agent_name": agent_file.agent_name,
            "skills_imported": 0,
            "facts_imported": 0,
            "errors": [],
        }

        # Import skills to procedural memory
        for skill in agent_file.skills:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "http://localhost:8700/memory/procedural",
                        json=skill
                    )
                    if response.status_code in [200, 201]:
                        result["skills_imported"] += 1
            except Exception as e:
                result["errors"].append(f"Skill import failed: {e}")

        # Import facts to semantic memory
        for fact in agent_file.facts:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "http://localhost:8700/memory/semantic",
                        json=fact
                    )
                    if response.status_code in [200, 201]:
                        result["facts_imported"] += 1
            except Exception as e:
                result["errors"].append(f"Fact import failed: {e}")

        logger.info(f"Imported agent {agent_file.agent_name}: {result}")
        return result

    def list_agent_files(self) -> List[Dict[str, Any]]:
        """List all exported agent files."""
        files = []
        for path in self.agents_dir.glob("*.af.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                    files.append({
                        "filename": path.name,
                        "agent_id": data.get("agent_id"),
                        "agent_name": data.get("agent_name"),
                        "agent_type": data.get("agent_type"),
                        "exported_at": data.get("exported_at"),
                        "skills_count": len(data.get("skills", [])),
                        "facts_count": len(data.get("facts", [])),
                    })
            except Exception as e:
                logger.warning(f"Failed to read agent file {path}: {e}")
        return files

    # =========================================================================
    # Multi-Agent Skill Sharing
    # =========================================================================

    def share_skill_to_agent(
        self,
        skill_id: str,
        target_agent_id: str,
    ) -> bool:
        """Share a skill with another agent."""
        skill = self.skill_library.get(skill_id)
        if not skill:
            return False

        # Create a copy for the target agent
        shared_skill = SkillLibraryEntry(
            skill_id=f"{skill_id}_shared_{target_agent_id[:8]}",
            name=skill.name,
            description=skill.description,
            category=skill.category,
            trigger_conditions=skill.trigger_conditions,
            steps=skill.steps,
            tags=skill.tags + ["shared"],
            created_by_agent=skill.created_by_agent,
        )
        shared_skill.metadata = {"shared_from": skill_id, "shared_to": target_agent_id}

        self.skill_library[shared_skill.skill_id] = shared_skill
        self._save_skill_library()

        logger.info(f"Shared skill {skill_id} to agent {target_agent_id}")
        return True

    def get_skills_for_agent(
        self,
        agent_id: str,
        include_shared: bool = True,
    ) -> List[SkillLibraryEntry]:
        """Get all skills available to an agent."""
        skills = []

        for skill in self.skill_library.values():
            # Include skills created by this agent
            if skill.created_by_agent == agent_id:
                skills.append(skill)
            # Include shared skills
            elif include_shared and "shared" in skill.tags:
                metadata = getattr(skill, "metadata", {})
                if metadata.get("shared_to") == agent_id:
                    skills.append(skill)

        return skills


# =============================================================================
# Global Instance
# =============================================================================

_manager: Optional[SkillLearningManager] = None


def get_skill_manager() -> SkillLearningManager:
    """Get or create the global skill learning manager."""
    global _manager
    if _manager is None:
        _manager = SkillLearningManager()
    return _manager


# =============================================================================
# FastAPI Router
# =============================================================================

class AddSkillRequest(BaseModel):
    name: str
    description: str
    category: str
    trigger_conditions: List[str]
    steps: List[str]
    tags: Optional[List[str]] = None


class RecordExecutionRequest(BaseModel):
    skill_id: str
    success: bool
    execution_time_ms: float
    context: Optional[Dict[str, Any]] = None


class ExportAgentRequest(BaseModel):
    agent_id: str
    agent_name: str
    agent_type: str = "generic"
    include_skills: bool = True
    include_facts: bool = True


def create_skill_learning_router() -> APIRouter:
    """Create FastAPI router for skill learning endpoints."""
    router = APIRouter(prefix="/skills", tags=["skill-learning"])

    @router.get("/library")
    async def get_skill_library(
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50,
    ):
        """Search the skill library."""
        manager = get_skill_manager()
        skills = manager.search_skills(
            query=query,
            category=category,
            min_success_rate=min_success_rate,
        )[:limit]
        return {
            "skills": [s.to_dict() for s in skills],
            "count": len(skills),
            "total": len(manager.skill_library),
        }

    @router.get("/library/categories")
    async def get_categories():
        """Get all skill categories."""
        manager = get_skill_manager()
        return {"categories": manager.get_categories()}

    @router.get("/library/top")
    async def get_top_skills(limit: int = 10):
        """Get top performing skills."""
        manager = get_skill_manager()
        skills = manager.get_top_skills(limit)
        return {"skills": [s.to_dict() for s in skills]}

    @router.get("/library/{skill_id}")
    async def get_skill(skill_id: str):
        """Get a specific skill."""
        manager = get_skill_manager()
        skill = manager.get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return skill.to_dict()

    @router.post("/library")
    async def add_skill(request: AddSkillRequest):
        """Add a new skill to the library."""
        manager = get_skill_manager()
        skill_id = manager.add_skill(
            name=request.name,
            description=request.description,
            category=request.category,
            trigger_conditions=request.trigger_conditions,
            steps=request.steps,
            tags=request.tags,
        )
        return {"skill_id": skill_id, "status": "added"}

    @router.post("/execution")
    async def record_execution(request: RecordExecutionRequest):
        """Record a skill execution."""
        manager = get_skill_manager()
        manager.record_execution(
            skill_id=request.skill_id,
            success=request.success,
            execution_time_ms=request.execution_time_ms,
            context=request.context,
        )
        return {"status": "recorded"}

    # =========================================================================
    # Agent File Endpoints
    # =========================================================================

    @router.get("/agents")
    async def list_agent_files():
        """List all exported agent files."""
        manager = get_skill_manager()
        return {"agents": manager.list_agent_files()}

    @router.post("/agents/export")
    async def export_agent(request: ExportAgentRequest):
        """Export an agent to an Agent File."""
        manager = get_skill_manager()
        af = await manager.export_agent(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            agent_type=request.agent_type,
            include_skills=request.include_skills,
            include_facts=request.include_facts,
        )
        return {
            "status": "exported",
            "agent_file": af.to_dict(),
        }

    @router.post("/agents/import")
    async def import_agent(file: UploadFile = File(...)):
        """Import an agent from an Agent File."""
        manager = get_skill_manager()

        try:
            content = await file.read()
            af = AgentFile.from_json(content.decode("utf-8"))
            result = await manager.import_agent(af)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid agent file: {e}")

    @router.get("/agents/{agent_id}/download")
    async def download_agent_file(agent_id: str):
        """Download an agent file."""
        manager = get_skill_manager()
        agent_file_path = manager.agents_dir / f"{agent_id}.af.json"

        if not agent_file_path.exists():
            raise HTTPException(status_code=404, detail="Agent file not found")

        with open(agent_file_path, "rb") as f:
            content = f.read()

        return StreamingResponse(
            BytesIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={agent_id}.af.json"}
        )

    # =========================================================================
    # Skill Sharing Endpoints
    # =========================================================================

    @router.post("/share")
    async def share_skill(skill_id: str, target_agent_id: str):
        """Share a skill with another agent."""
        manager = get_skill_manager()
        success = manager.share_skill_to_agent(skill_id, target_agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"status": "shared", "skill_id": skill_id, "target_agent": target_agent_id}

    @router.get("/agent/{agent_id}")
    async def get_agent_skills(agent_id: str, include_shared: bool = True):
        """Get all skills available to an agent."""
        manager = get_skill_manager()
        skills = manager.get_skills_for_agent(agent_id, include_shared)
        return {"skills": [s.to_dict() for s in skills], "count": len(skills)}

    @router.get("/stats")
    async def get_stats():
        """Get skill learning statistics."""
        manager = get_skill_manager()

        total_skills = len(manager.skill_library)
        total_executions = sum(s.execution_count for s in manager.skill_library.values())
        avg_success_rate = (
            sum(s.success_rate for s in manager.skill_library.values()) / total_skills
            if total_skills > 0 else 0
        )
        categories = manager.get_categories()

        return {
            "total_skills": total_skills,
            "total_executions": total_executions,
            "avg_success_rate": round(avg_success_rate, 3),
            "categories": len(categories),
            "agent_files": len(manager.list_agent_files()),
        }

    return router
