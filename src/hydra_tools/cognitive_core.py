"""
Hydra Cognitive Core - LLM-Powered Autonomous Reasoning System

This module implements a true cognitive agent that:
1. PERCEIVES - Gathers system state from all sensors
2. REASONS - Uses LLM to understand what needs attention
3. PLANS - Generates multi-step action plans
4. ACTS - Executes via MCP tools
5. LEARNS - Stores outcomes in hybrid memory

This replaces rule-based triggers with intelligent reasoning while
maintaining constitutional constraints and audit logging.

Architecture follows Anthropic's "simple composable patterns" guidance:
- Agent loop with tools (not complex framework)
- Hybrid memory (vector + graph + keyword)
- Checkpointing for recovery
- Constitutional safety

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import traceback

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

LITELLM_URL = os.environ.get("LITELLM_URL", "http://192.168.1.244:4000")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7")
DEFAULT_MODEL = os.environ.get("COGNITIVE_MODEL", "midnight-miqu-70b")  # Primary 70B model on TabbyAPI
FALLBACK_MODEL = os.environ.get("COGNITIVE_FALLBACK_MODEL", "qwen2.5-7b")  # Fast Ollama fallback
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8700")


# =============================================================================
# Data Classes
# =============================================================================

class ActionType(str, Enum):
    """Types of actions the cognitive core can take."""
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    RESEARCH = "research"
    GENERATION = "generation"
    IMPROVEMENT = "improvement"
    NOTIFICATION = "notification"
    HEALING = "healing"
    NONE = "none"  # No action needed


class CognitiveState(str, Enum):
    """States of the cognitive core."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    PLANNING = "planning"
    ACTING = "acting"
    LEARNING = "learning"
    ERROR = "error"


@dataclass
class SystemObservation:
    """Complete observation of system state."""
    timestamp: datetime
    cluster_health: Dict[str, Any]
    container_health: Dict[str, Any]
    inference_health: Dict[str, Any]
    resource_status: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    pending_tasks: List[Dict[str, Any]]
    goals: Dict[str, Any]
    memory_context: List[str]

    def to_prompt_context(self) -> str:
        """Convert observation to prompt context string."""
        return f"""## Current System State ({self.timestamp.isoformat()})

### Cluster Health
{json.dumps(self.cluster_health, indent=2, default=str)}

### Container Health Summary
- Total: {self.container_health.get('total', 0)}
- Healthy: {self.container_health.get('healthy', 0)}
- Unhealthy: {self.container_health.get('unhealthy', [])}

### Inference Services
{json.dumps(self.inference_health, indent=2, default=str)}

### GPU Resources
{json.dumps(self.resource_status, indent=2, default=str)}

### Recent Events (last 10)
{json.dumps(self.recent_events[:10], indent=2, default=str) if self.recent_events else "No recent events"}

### Pending Tasks
{len(self.pending_tasks)} tasks in queue

### Active Goals
{json.dumps(self.goals, indent=2, default=str)}

### Relevant Memory Context
{chr(10).join(self.memory_context) if self.memory_context else "No relevant context retrieved"}
"""


@dataclass
class CognitivePlan:
    """A plan of actions to execute."""
    id: str
    reasoning: str
    actions: List[Dict[str, Any]]
    priority: str
    estimated_duration_minutes: int
    requires_human_approval: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ActionResult:
    """Result of executing an action."""
    action_id: str
    action_type: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CognitiveCheckpoint:
    """Checkpoint for recovery and time-travel debugging."""
    id: str
    session_id: str
    step_number: int
    state: CognitiveState
    observation: Optional[Dict[str, Any]]
    current_plan: Optional[Dict[str, Any]]
    completed_actions: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "step_number": self.step_number,
            "state": self.state.value,
            "observation": self.observation,
            "current_plan": self.current_plan,
            "completed_actions": self.completed_actions,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Cognitive System Prompt
# =============================================================================

COGNITIVE_SYSTEM_PROMPT = """You are the Hydra Cognitive Core - an autonomous AI steward responsible for maintaining and improving a home AI cluster 24/7.

## Your Identity
- You are proactive, not reactive. You identify work and execute without waiting.
- You maintain 3 GPU nodes: hydra-ai (inference), hydra-compute (images), hydra-storage (services)
- You operate under constitutional constraints that protect critical infrastructure

## Your Responsibilities
1. MONITOR: Keep all services healthy and performing well
2. HEAL: Fix problems automatically when possible
3. OPTIMIZE: Improve performance and efficiency continuously
4. CREATE: Generate content for projects when GPU is idle
5. RESEARCH: Stay current on AI developments
6. LEARN: Extract skills from successful operations

## Decision Framework
When analyzing system state, consider:
1. Is anything broken or degraded that needs immediate attention?
2. Are there optimization opportunities I can execute now?
3. Is there creative work I can do during idle time?
4. What can I learn from recent events?

## Constitutional Constraints (IMMUTABLE)
- Never delete databases without human approval
- Never modify network/firewall configuration
- Never disable authentication systems
- Never expose secrets or credentials
- Always maintain audit trail
- Require human approval for git push to main

## Response Format
You must respond with a JSON object containing:
{
    "analysis": "Brief analysis of current state",
    "priority": "critical|high|normal|low|idle",
    "action_needed": true/false,
    "reasoning": "Why this action is needed (or why no action)",
    "actions": [
        {
            "type": "maintenance|monitoring|research|generation|improvement|notification|healing",
            "description": "What to do",
            "tool": "tool_name to use",
            "parameters": {}
        }
    ],
    "requires_human_approval": false,
    "learning": "What to remember from this observation"
}

If no action is needed, set action_needed to false and provide empty actions array.
"""


# =============================================================================
# LLM Client
# =============================================================================

class CognitiveLLMClient:
    """Client for LLM reasoning operations."""

    def __init__(
        self,
        base_url: str = LITELLM_URL,
        api_key: str = LITELLM_API_KEY,
        default_model: str = DEFAULT_MODEL,
        fallback_model: str = FALLBACK_MODEL,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.default_model = default_model
        self.fallback_model = fallback_model
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def reason(
        self,
        observation: SystemObservation,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to reason about current state and decide actions.

        Returns a structured decision with analysis, actions, and learnings.
        """
        model = model or self.default_model
        client = await self.get_client()

        # Build the prompt
        user_message = f"""Analyze the current system state and decide what actions, if any, are needed.

{observation.to_prompt_context()}

Respond with a JSON object as specified in your instructions. Think carefully about:
1. What is the most important issue right now?
2. What can be done autonomously vs requires human input?
3. What should be learned and remembered?
"""

        try:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": COGNITIVE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,  # Lower for more consistent reasoning
                    "max_tokens": 2000,
                    # Note: response_format not supported by Ollama models
                },
            )

            if response.status_code != 200:
                # Try fallback model
                logger.warning(f"Primary model failed ({response.status_code}), trying fallback")
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.fallback_model,
                        "messages": [
                            {"role": "system", "content": COGNITIVE_SYSTEM_PROMPT},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                )

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

            # Parse JSON response
            try:
                decision = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                    decision = json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                    decision = json.loads(json_str)
                else:
                    decision = {
                        "analysis": content,
                        "priority": "low",
                        "action_needed": False,
                        "reasoning": "Could not parse structured response",
                        "actions": [],
                        "learning": "",
                    }

            return decision

        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return {
                "analysis": f"Reasoning error: {str(e)}",
                "priority": "normal",
                "action_needed": False,
                "reasoning": "LLM reasoning failed, will retry next cycle",
                "actions": [],
                "error": str(e),
            }

    async def close(self):
        if self._client:
            await self._client.aclose()


# =============================================================================
# Hybrid Memory Interface
# =============================================================================

class HybridMemoryInterface:
    """
    Interface to hybrid memory system (Qdrant + Neo4j + Meilisearch).

    Uses the full hybrid memory module with Reciprocal Rank Fusion
    for 18.5%+ accuracy improvement over vector-only search.
    """

    def __init__(self, api_base: str = API_BASE_URL):
        self.api_base = api_base
        self._client: Optional[httpx.AsyncClient] = None
        self._hybrid_memory = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def get_hybrid_memory(self):
        """Get the hybrid memory manager."""
        if self._hybrid_memory is None:
            try:
                from hydra_tools.hybrid_memory import get_hybrid_memory
                self._hybrid_memory = get_hybrid_memory()
                await self._hybrid_memory.initialize()
            except Exception as e:
                logger.warning(f"Hybrid memory not available: {e}")
        return self._hybrid_memory

    async def retrieve_context(
        self,
        query: str,
        limit: int = 5,
        tiers: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Retrieve relevant memory context using hybrid search.

        Combines results from:
        - Qdrant (vector similarity)
        - Neo4j (graph relationships)
        - Meilisearch (keyword matching)

        Uses Reciprocal Rank Fusion for optimal result combination.
        """
        # Try hybrid search first
        hybrid = await self.get_hybrid_memory()
        if hybrid:
            try:
                result = await hybrid.search(
                    query=query,
                    limit=limit,
                    backends=["vector", "graph", "keyword"],
                    use_fusion=True,
                )
                return [r.content for r in result.results if r.content]
            except Exception as e:
                logger.warning(f"Hybrid search failed, falling back to API: {e}")

        # Fallback to API-based search
        client = await self.get_client()

        try:
            response = await client.post(
                f"{self.api_base}/hybrid-memory/search",
                json={
                    "query": query,
                    "limit": limit,
                    "use_fusion": True,
                },
            )

            if response.status_code == 200:
                results = response.json().get("results", [])
                return [r.get("content", "") for r in results]

        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")

        return []

    async def store_learning(
        self,
        content: str,
        tier: str = "episodic",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a learning in all memory backends."""
        # Try hybrid store first
        hybrid = await self.get_hybrid_memory()
        if hybrid:
            try:
                return await hybrid.store(
                    content=content,
                    tier=tier,
                    tags=tags or ["cognitive_core", "learning"],
                    metadata=metadata,
                )
            except Exception as e:
                logger.warning(f"Hybrid store failed, falling back to API: {e}")

        # Fallback to API-based store
        client = await self.get_client()

        try:
            response = await client.post(
                f"{self.api_base}/hybrid-memory/store",
                json={
                    "content": content,
                    "tier": tier,
                    "tags": tags or ["cognitive_core", "learning"],
                    "metadata": metadata or {},
                },
            )

            if response.status_code == 200:
                return response.json().get("id")

        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")

        return None

    async def close(self):
        if self._client:
            await self._client.aclose()
        if self._hybrid_memory:
            await self._hybrid_memory.close()


# =============================================================================
# Action Executor
# =============================================================================

class ActionExecutor:
    """Executes actions via the Hydra Tools API."""

    # Map action types to API endpoints
    ACTION_HANDLERS = {
        "maintenance": "/autonomous/queue",
        "monitoring": "/autonomous/queue",
        "research": "/autonomous/queue",
        "generation": "/autonomous/queue",
        "improvement": "/autonomous/queue",
        "notification": "/notifications/send",
        "healing": "/container-health/remediate",
    }

    # Map cognitive action types to autonomous queue work types
    WORK_TYPE_MAP = {
        "maintenance": "maintenance",
        "monitoring": "maintenance",
        "research": "research",
        "generation": "chapter_generation",
        "improvement": "maintenance",
    }

    def __init__(self, api_base: str = API_BASE_URL):
        self.api_base = api_base
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def execute(
        self,
        action: Dict[str, Any],
        dry_run: bool = False,
    ) -> ActionResult:
        """Execute a single action."""
        action_type = action.get("type", "maintenance")
        action_id = hashlib.sha256(
            f"{action_type}:{action.get('description', '')}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        start_time = datetime.utcnow()

        if dry_run:
            return ActionResult(
                action_id=action_id,
                action_type=action_type,
                success=True,
                result={"dry_run": True, "would_execute": action},
                duration_seconds=0.0,
            )

        client = await self.get_client()

        try:
            # Route to appropriate handler
            endpoint = self.ACTION_HANDLERS.get(action_type, "/autonomous/queue")

            if endpoint == "/autonomous/queue":
                # Queue as autonomous task
                # Map action type to valid autonomous queue work type
                work_type = self.WORK_TYPE_MAP.get(action_type, "custom")
                payload = {
                    "work_type": work_type,
                    "title": action.get("description", "Cognitive core action")[:100],
                    "description": action.get("description", "Cognitive core action"),
                    "payload": action.get("parameters", {}),
                    "priority": action.get("priority", "normal"),
                    "source": "cognitive_core",
                }

                response = await client.post(
                    f"{self.api_base}{endpoint}",
                    json=payload,
                )

            elif endpoint == "/container-health/remediate":
                # Direct container remediation
                container = action.get("parameters", {}).get("container")
                if container:
                    response = await client.post(
                        f"{self.api_base}/container-health/remediate/{container}",
                        json={"action": action.get("parameters", {}).get("remediation", "restart")},
                    )
                else:
                    return ActionResult(
                        action_id=action_id,
                        action_type=action_type,
                        success=False,
                        result=None,
                        error="No container specified for remediation",
                        duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    )

            else:
                # Generic POST
                response = await client.post(
                    f"{self.api_base}{endpoint}",
                    json=action.get("parameters", {}),
                )

            duration = (datetime.utcnow() - start_time).total_seconds()

            if response.status_code in (200, 201, 202):
                return ActionResult(
                    action_id=action_id,
                    action_type=action_type,
                    success=True,
                    result=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    duration_seconds=duration,
                )
            else:
                return ActionResult(
                    action_id=action_id,
                    action_type=action_type,
                    success=False,
                    result=None,
                    error=f"HTTP {response.status_code}: {response.text[:500]}",
                    duration_seconds=duration,
                )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return ActionResult(
                action_id=action_id,
                action_type=action_type,
                success=False,
                result=None,
                error=str(e),
                duration_seconds=duration,
            )

    async def close(self):
        if self._client:
            await self._client.aclose()


# =============================================================================
# Checkpoint Manager (PostgreSQL-backed)
# =============================================================================

POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://hydra:HydraPostgres2024@192.168.1.244:5432/hydra")


class CheckpointManager:
    """
    Manages cognitive checkpoints for recovery and debugging.

    Uses PostgreSQL for persistent storage with automatic table creation.
    Falls back to JSON file if PostgreSQL is unavailable.
    """

    def __init__(self, data_dir: str = "/data/cognitive"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "checkpoints.json"
        self._checkpoints: List[CognitiveCheckpoint] = []
        self._use_postgres = False
        self._pg_pool = None
        self._initialized = False

    async def initialize(self):
        """Initialize PostgreSQL connection and tables."""
        if self._initialized:
            return

        try:
            import asyncpg

            # Create connection pool
            self._pg_pool = await asyncpg.create_pool(
                POSTGRES_URL,
                min_size=1,
                max_size=5,
            )

            # Create tables
            async with self._pg_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cognitive_checkpoints (
                        id VARCHAR(32) PRIMARY KEY,
                        session_id VARCHAR(32) NOT NULL,
                        step_number INTEGER NOT NULL,
                        state VARCHAR(32) NOT NULL,
                        observation JSONB,
                        current_plan JSONB,
                        completed_actions JSONB,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                # Create index for session lookups
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_session
                    ON cognitive_checkpoints (session_id, step_number DESC)
                """)

            self._use_postgres = True
            logger.info("Checkpoint manager initialized with PostgreSQL")

        except Exception as e:
            logger.warning(f"PostgreSQL not available, using JSON fallback: {e}")
            self._load_json()

        self._initialized = True

    def _load_json(self):
        """Load checkpoints from JSON file (fallback)."""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self._checkpoints = []
                    for cp_data in data.get("checkpoints", []):
                        self._checkpoints.append(CognitiveCheckpoint(
                            id=cp_data["id"],
                            session_id=cp_data["session_id"],
                            step_number=cp_data["step_number"],
                            state=CognitiveState(cp_data["state"]),
                            observation=cp_data.get("observation"),
                            current_plan=cp_data.get("current_plan"),
                            completed_actions=cp_data.get("completed_actions", []),
                            timestamp=datetime.fromisoformat(cp_data["timestamp"]),
                        ))
            except Exception as e:
                logger.warning(f"Error loading checkpoints from JSON: {e}")

    def _save_json(self):
        """Save checkpoints to JSON file (fallback)."""
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "checkpoints": [cp.to_dict() for cp in self._checkpoints[-100:]]
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving checkpoints to JSON: {e}")

    async def save_checkpoint(
        self,
        session_id: str,
        step_number: int,
        state: CognitiveState,
        observation: Optional[SystemObservation] = None,
        current_plan: Optional[CognitivePlan] = None,
        completed_actions: Optional[List[ActionResult]] = None,
    ) -> str:
        """Save a checkpoint and return its ID."""
        checkpoint_id = hashlib.sha256(
            f"{session_id}:{step_number}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        checkpoint = CognitiveCheckpoint(
            id=checkpoint_id,
            session_id=session_id,
            step_number=step_number,
            state=state,
            observation=asdict(observation) if observation else None,
            current_plan=asdict(current_plan) if current_plan else None,
            completed_actions=[asdict(a) for a in (completed_actions or [])],
        )

        if self._use_postgres and self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO cognitive_checkpoints
                        (id, session_id, step_number, state, observation, current_plan, completed_actions, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (id) DO UPDATE SET
                            state = EXCLUDED.state,
                            observation = EXCLUDED.observation,
                            current_plan = EXCLUDED.current_plan,
                            completed_actions = EXCLUDED.completed_actions,
                            timestamp = EXCLUDED.timestamp
                    """,
                        checkpoint_id,
                        session_id,
                        step_number,
                        state.value,
                        json.dumps(checkpoint.observation) if checkpoint.observation else None,
                        json.dumps(checkpoint.current_plan) if checkpoint.current_plan else None,
                        json.dumps(checkpoint.completed_actions),
                        checkpoint.timestamp,
                    )
            except Exception as e:
                logger.warning(f"PostgreSQL save failed, using JSON: {e}")
                self._checkpoints.append(checkpoint)
                self._save_json()
        else:
            self._checkpoints.append(checkpoint)
            self._save_json()

        return checkpoint_id

    # Sync wrapper for compatibility
    def save_checkpoint_sync(self, *args, **kwargs) -> str:
        """Synchronous wrapper for save_checkpoint."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create task and return immediately with generated ID
                checkpoint_id = hashlib.sha256(
                    f"{args[0]}:{args[1]}:{datetime.utcnow().isoformat()}".encode()
                ).hexdigest()[:16]
                asyncio.create_task(self.save_checkpoint(*args, **kwargs))
                return checkpoint_id
            else:
                return loop.run_until_complete(self.save_checkpoint(*args, **kwargs))
        except RuntimeError:
            # No event loop, use JSON fallback
            return self._save_checkpoint_json(*args, **kwargs)

    def _save_checkpoint_json(
        self,
        session_id: str,
        step_number: int,
        state: CognitiveState,
        observation=None,
        current_plan=None,
        completed_actions=None,
    ) -> str:
        """Save checkpoint to JSON (synchronous fallback)."""
        checkpoint_id = hashlib.sha256(
            f"{session_id}:{step_number}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        checkpoint = CognitiveCheckpoint(
            id=checkpoint_id,
            session_id=session_id,
            step_number=step_number,
            state=state,
            observation=asdict(observation) if observation else None,
            current_plan=asdict(current_plan) if current_plan else None,
            completed_actions=[asdict(a) for a in (completed_actions or [])],
        )

        self._checkpoints.append(checkpoint)
        self._save_json()
        return checkpoint_id

    async def get_latest_checkpoint(self, session_id: str) -> Optional[CognitiveCheckpoint]:
        """Get the latest checkpoint for a session."""
        if self._use_postgres and self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT * FROM cognitive_checkpoints
                        WHERE session_id = $1
                        ORDER BY step_number DESC
                        LIMIT 1
                    """, session_id)

                    if row:
                        return CognitiveCheckpoint(
                            id=row["id"],
                            session_id=row["session_id"],
                            step_number=row["step_number"],
                            state=CognitiveState(row["state"]),
                            observation=json.loads(row["observation"]) if row["observation"] else None,
                            current_plan=json.loads(row["current_plan"]) if row["current_plan"] else None,
                            completed_actions=json.loads(row["completed_actions"]) if row["completed_actions"] else [],
                            timestamp=row["timestamp"],
                        )
            except Exception as e:
                logger.warning(f"PostgreSQL query failed: {e}")

        # Fallback to in-memory
        session_checkpoints = [cp for cp in self._checkpoints if cp.session_id == session_id]
        return session_checkpoints[-1] if session_checkpoints else None

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[CognitiveCheckpoint]:
        """Get a specific checkpoint by ID."""
        if self._use_postgres and self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT * FROM cognitive_checkpoints
                        WHERE id = $1
                    """, checkpoint_id)

                    if row:
                        return CognitiveCheckpoint(
                            id=row["id"],
                            session_id=row["session_id"],
                            step_number=row["step_number"],
                            state=CognitiveState(row["state"]),
                            observation=json.loads(row["observation"]) if row["observation"] else None,
                            current_plan=json.loads(row["current_plan"]) if row["current_plan"] else None,
                            completed_actions=json.loads(row["completed_actions"]) if row["completed_actions"] else [],
                            timestamp=row["timestamp"],
                        )
            except Exception as e:
                logger.warning(f"PostgreSQL query failed: {e}")

        # Fallback to in-memory
        for cp in self._checkpoints:
            if cp.id == checkpoint_id:
                return cp
        return None

    async def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover a session from its last checkpoint.

        Returns recovery information including last state, step, and any
        incomplete actions.
        """
        checkpoint = await self.get_latest_checkpoint(session_id)
        if not checkpoint:
            return None

        return {
            "checkpoint_id": checkpoint.id,
            "session_id": checkpoint.session_id,
            "step_number": checkpoint.step_number,
            "state": checkpoint.state.value,
            "timestamp": checkpoint.timestamp.isoformat(),
            "has_observation": checkpoint.observation is not None,
            "has_plan": checkpoint.current_plan is not None,
            "completed_actions_count": len(checkpoint.completed_actions),
            "can_resume": checkpoint.state in [CognitiveState.PERCEIVING, CognitiveState.REASONING, CognitiveState.IDLE],
        }

    async def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent sessions with their latest checkpoints."""
        if self._use_postgres and self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT DISTINCT ON (session_id)
                            session_id, step_number, state, timestamp
                        FROM cognitive_checkpoints
                        ORDER BY session_id, step_number DESC
                        LIMIT $1
                    """, limit)

                    return [
                        {
                            "session_id": row["session_id"],
                            "step_number": row["step_number"],
                            "state": row["state"],
                            "timestamp": row["timestamp"].isoformat(),
                        }
                        for row in rows
                    ]
            except Exception as e:
                logger.warning(f"PostgreSQL query failed: {e}")

        # Fallback to in-memory
        sessions = {}
        for cp in self._checkpoints:
            if cp.session_id not in sessions or cp.step_number > sessions[cp.session_id].step_number:
                sessions[cp.session_id] = cp

        return [
            {
                "session_id": cp.session_id,
                "step_number": cp.step_number,
                "state": cp.state.value,
                "timestamp": cp.timestamp.isoformat(),
            }
            for cp in list(sessions.values())[:limit]
        ]

    async def close(self):
        """Close database connections."""
        if self._pg_pool:
            await self._pg_pool.close()


# =============================================================================
# Cognitive Core
# =============================================================================

class CognitiveCore:
    """
    LLM-powered cognitive agent for autonomous Hydra operation.

    Implements the perceive-reason-plan-act-learn loop with:
    - LLM reasoning for intelligent decision-making
    - Hybrid memory for context retrieval
    - Checkpointing for recovery
    - Constitutional constraints for safety
    """

    def __init__(
        self,
        api_base: str = API_BASE_URL,
        loop_interval_seconds: int = 60,
        model: str = DEFAULT_MODEL,
    ):
        self.api_base = api_base
        self.loop_interval = loop_interval_seconds
        self.model = model

        # Components
        self.llm = CognitiveLLMClient()
        self.memory = HybridMemoryInterface(api_base)
        self.executor = ActionExecutor(api_base)
        self.checkpoints = CheckpointManager()

        # State
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._session_id = hashlib.sha256(
            f"session:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        self._step_number = 0
        self._state = CognitiveState.IDLE
        self._current_observation: Optional[SystemObservation] = None
        self._current_plan: Optional[CognitivePlan] = None

        # Goals - loaded from file or defaults
        self._goals = self._load_goals()

        # Stats
        self._stats = {
            "started_at": None,
            "cycles_completed": 0,
            "actions_executed": 0,
            "actions_succeeded": 0,
            "actions_failed": 0,
            "learnings_stored": 0,
            "errors": 0,
            "last_cycle_at": None,
            "last_action_at": None,
        }

        # History
        self._action_history: List[ActionResult] = []
        self._decision_history: List[Dict[str, Any]] = []

        logger.info(f"CognitiveCore initialized with session {self._session_id}")

    def _load_goals(self) -> Dict[str, Any]:
        """Load goals from file or return defaults."""
        goals_file = Path("/data/cognitive/goals.json")

        if goals_file.exists():
            try:
                with open(goals_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        # Default goals based on CLAUDE.md
        return {
            "mission": [
                "Run 70B+ models at interactive speeds",
                "Operate 24/7 without human intervention",
                "Self-improve continuously",
                "Maintain perfect reliability",
            ],
            "projects": {
                "empire_of_broken_queens": {
                    "goal": "Generate all 21 chapters with assets",
                    "priority": "normal",
                },
                "infrastructure": {
                    "goal": "Keep all 41+ containers healthy",
                    "priority": "high",
                },
            },
            "session": [],  # Updated each session
        }

    # =========================================================================
    # Perceive
    # =========================================================================

    async def perceive(self) -> SystemObservation:
        """Gather comprehensive system state."""
        self._state = CognitiveState.PERCEIVING

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Cluster health
            try:
                resp = await client.get(f"{self.api_base}/health")
                cluster_health = resp.json() if resp.status_code == 200 else {"error": "unavailable"}
            except Exception as e:
                cluster_health = {"error": str(e)}

            # Container health
            try:
                resp = await client.get(f"{self.api_base}/container-health/")
                container_data = resp.json() if resp.status_code == 200 else {}
                container_health = {
                    "total": container_data.get("summary", {}).get("total", 0),
                    "healthy": container_data.get("summary", {}).get("healthy", 0),
                    "unhealthy": [
                        c.get("name") for c in container_data.get("containers", [])
                        if c.get("status") == "unhealthy"
                    ],
                }
            except Exception as e:
                container_health = {"error": str(e)}

            # Inference health
            try:
                resp = await client.get(f"{self.api_base}/diagnosis/inference")
                inference_health = resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                inference_health = {"error": str(e)}

            # Resources
            try:
                resp = await client.get(f"{self.api_base}/autonomous/resources")
                resource_status = resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                resource_status = {"error": str(e)}

            # Recent events from memory
            try:
                resp = await client.get(f"{self.api_base}/memory/recent?limit=10")
                recent_events = resp.json().get("memories", []) if resp.status_code == 200 else []
            except Exception:
                recent_events = []

            # Pending tasks
            try:
                resp = await client.get(f"{self.api_base}/autonomous/queue")
                queue_data = resp.json() if resp.status_code == 200 else {}
                pending_tasks = queue_data.get("pending", [])
            except Exception:
                pending_tasks = []

        # Retrieve relevant memory context
        context_query = "What are the most important things to know about current system state and recent issues?"
        memory_context = await self.memory.retrieve_context(context_query, limit=5)

        observation = SystemObservation(
            timestamp=datetime.utcnow(),
            cluster_health=cluster_health,
            container_health=container_health,
            inference_health=inference_health,
            resource_status=resource_status,
            recent_events=recent_events,
            pending_tasks=pending_tasks,
            goals=self._goals,
            memory_context=memory_context,
        )

        self._current_observation = observation
        return observation

    # =========================================================================
    # Reason
    # =========================================================================

    async def reason(self, observation: SystemObservation) -> Dict[str, Any]:
        """Use LLM to analyze state and decide actions."""
        self._state = CognitiveState.REASONING

        decision = await self.llm.reason(observation, model=self.model)

        # Store decision in history
        self._decision_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
        })

        # Trim history
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-100:]

        return decision

    # =========================================================================
    # Plan
    # =========================================================================

    async def plan(self, decision: Dict[str, Any]) -> Optional[CognitivePlan]:
        """Create an execution plan from the decision."""
        self._state = CognitiveState.PLANNING

        if not decision.get("action_needed", False):
            return None

        actions = decision.get("actions", [])
        if not actions:
            return None

        plan_id = hashlib.sha256(
            f"plan:{datetime.utcnow().isoformat()}:{len(actions)}".encode()
        ).hexdigest()[:16]

        plan = CognitivePlan(
            id=plan_id,
            reasoning=decision.get("reasoning", ""),
            actions=actions,
            priority=decision.get("priority", "normal"),
            estimated_duration_minutes=len(actions) * 2,  # Rough estimate
            requires_human_approval=decision.get("requires_human_approval", False),
        )

        self._current_plan = plan
        return plan

    # =========================================================================
    # Act
    # =========================================================================

    async def act(self, plan: CognitivePlan, dry_run: bool = False) -> List[ActionResult]:
        """Execute the plan's actions."""
        self._state = CognitiveState.ACTING

        results = []

        for action in plan.actions:
            # Check for human approval if required
            if plan.requires_human_approval:
                logger.info(f"Action requires human approval, skipping: {action}")
                continue

            # Execute the action
            result = await self.executor.execute(action, dry_run=dry_run)
            results.append(result)

            self._action_history.append(result)
            self._stats["actions_executed"] += 1

            if result.success:
                self._stats["actions_succeeded"] += 1
                self._stats["last_action_at"] = datetime.utcnow().isoformat()
            else:
                self._stats["actions_failed"] += 1
                logger.warning(f"Action failed: {result.error}")

        # Trim action history
        if len(self._action_history) > 500:
            self._action_history = self._action_history[-500:]

        return results

    # =========================================================================
    # Learn
    # =========================================================================

    async def learn(
        self,
        decision: Dict[str, Any],
        results: List[ActionResult],
    ):
        """Store learnings in memory."""
        self._state = CognitiveState.LEARNING

        # Store the learning from the LLM's analysis
        learning = decision.get("learning", "")
        if learning:
            await self.memory.store_learning(
                content=learning,
                tier="episodic",
                tags=["cognitive_core", "learning", "autonomous"],
                metadata={
                    "session_id": self._session_id,
                    "step_number": self._step_number,
                    "action_count": len(results),
                    "success_rate": sum(1 for r in results if r.success) / len(results) if results else 0,
                },
            )
            self._stats["learnings_stored"] += 1

        # Store action outcomes
        for result in results:
            content = (
                f"Action: {result.action_type}. "
                f"Success: {result.success}. "
                f"Duration: {result.duration_seconds:.1f}s. "
            )
            if result.error:
                content += f"Error: {result.error}"

            await self.memory.store_learning(
                content=content,
                tier="episodic",
                tags=["cognitive_core", "action_result", result.action_type],
                metadata={"action_id": result.action_id},
            )

    # =========================================================================
    # Main Loop
    # =========================================================================

    async def _cognitive_loop(self):
        """Main cognitive loop - runs continuously."""
        logger.info(f"Cognitive loop started for session {self._session_id}")

        while self._running:
            try:
                self._step_number += 1

                # 1. Perceive
                observation = await self.perceive()

                # Save checkpoint after perception
                self.checkpoints.save_checkpoint(
                    session_id=self._session_id,
                    step_number=self._step_number,
                    state=self._state,
                    observation=observation,
                )

                # 2. Reason
                decision = await self.reason(observation)

                # 3. Plan
                plan = await self.plan(decision)

                # 4. Act (if we have a plan)
                results = []
                if plan:
                    # Save checkpoint before acting
                    self.checkpoints.save_checkpoint(
                        session_id=self._session_id,
                        step_number=self._step_number,
                        state=CognitiveState.ACTING,
                        observation=observation,
                        current_plan=plan,
                    )

                    results = await self.act(plan)

                # 5. Learn
                await self.learn(decision, results)

                # Update stats
                self._stats["cycles_completed"] += 1
                self._stats["last_cycle_at"] = datetime.utcnow().isoformat()
                self._state = CognitiveState.IDLE

                # Log summary
                if plan:
                    success_count = sum(1 for r in results if r.success)
                    logger.info(
                        f"Cycle {self._step_number}: {len(results)} actions "
                        f"({success_count} succeeded)"
                    )
                else:
                    logger.debug(f"Cycle {self._step_number}: No action needed")

            except Exception as e:
                self._state = CognitiveState.ERROR
                self._stats["errors"] += 1
                logger.error(f"Error in cognitive loop: {e}\n{traceback.format_exc()}")

            # Wait before next cycle
            await asyncio.sleep(self.loop_interval)

        logger.info("Cognitive loop stopped")

    async def start(self):
        """Start the cognitive core."""
        if self._running:
            return

        self._running = True
        self._stats["started_at"] = datetime.utcnow().isoformat()
        self._loop_task = asyncio.create_task(self._cognitive_loop())
        logger.info("Cognitive core started")

    async def stop(self):
        """Stop the cognitive core."""
        self._running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        # Cleanup
        await self.llm.close()
        await self.memory.close()
        await self.executor.close()

        logger.info("Cognitive core stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get cognitive core status."""
        return {
            "running": self._running,
            "session_id": self._session_id,
            "state": self._state.value,
            "step_number": self._step_number,
            "model": self.model,
            "loop_interval_seconds": self.loop_interval,
            "stats": self._stats,
            "current_observation_age_seconds": (
                (datetime.utcnow() - self._current_observation.timestamp).total_seconds()
                if self._current_observation else None
            ),
            "has_current_plan": self._current_plan is not None,
        }

    def get_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get action and decision history."""
        return {
            "actions": [asdict(a) for a in self._action_history[-limit:]],
            "decisions": self._decision_history[-limit:],
        }

    async def force_cycle(self) -> Dict[str, Any]:
        """Force an immediate cognitive cycle."""
        try:
            self._step_number += 1
            observation = await self.perceive()
            decision = await self.reason(observation)
            plan = await self.plan(decision)

            results = []
            if plan:
                results = await self.act(plan)
                await self.learn(decision, results)

            return {
                "success": True,
                "step_number": self._step_number,
                "decision": decision,
                "actions_executed": len(results),
                "actions_succeeded": sum(1 for r in results if r.success),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# =============================================================================
# Global Instance
# =============================================================================

_cognitive_core: Optional[CognitiveCore] = None


def get_cognitive_core() -> CognitiveCore:
    """Get or create the global cognitive core."""
    global _cognitive_core
    if _cognitive_core is None:
        _cognitive_core = CognitiveCore()
    return _cognitive_core


# =============================================================================
# FastAPI Router
# =============================================================================

def create_cognitive_router() -> APIRouter:
    """Create FastAPI router for cognitive core endpoints."""
    router = APIRouter(prefix="/cognitive", tags=["cognitive"])

    @router.get("/status")
    async def get_status():
        """Get cognitive core status."""
        core = get_cognitive_core()
        return core.get_status()

    @router.post("/start")
    async def start_core():
        """Start the cognitive core."""
        core = get_cognitive_core()
        await core.start()
        return {"status": "started", "session_id": core._session_id}

    @router.post("/stop")
    async def stop_core():
        """Stop the cognitive core."""
        core = get_cognitive_core()
        await core.stop()
        return {"status": "stopped"}

    @router.get("/history")
    async def get_history(limit: int = 50):
        """Get action and decision history."""
        core = get_cognitive_core()
        return core.get_history(limit)

    @router.post("/cycle")
    async def force_cycle():
        """Force an immediate cognitive cycle."""
        core = get_cognitive_core()
        return await core.force_cycle()

    @router.get("/observation")
    async def get_observation():
        """Get current observation."""
        core = get_cognitive_core()
        if core._current_observation:
            return asdict(core._current_observation)
        # Force a fresh observation
        observation = await core.perceive()
        return asdict(observation)

    @router.get("/goals")
    async def get_goals():
        """Get current goals."""
        core = get_cognitive_core()
        return core._goals

    @router.put("/goals")
    async def update_goals(goals: Dict[str, Any]):
        """Update goals."""
        core = get_cognitive_core()
        core._goals.update(goals)
        # Save to file
        goals_file = Path("/data/cognitive/goals.json")
        goals_file.parent.mkdir(parents=True, exist_ok=True)
        with open(goals_file, "w") as f:
            json.dump(core._goals, f, indent=2)
        return {"status": "updated", "goals": core._goals}

    @router.get("/checkpoints")
    async def get_checkpoints(session_id: Optional[str] = None, limit: int = 20):
        """Get checkpoints."""
        core = get_cognitive_core()
        checkpoints = core.checkpoints._checkpoints
        if session_id:
            checkpoints = [cp for cp in checkpoints if cp.session_id == session_id]
        return {
            "checkpoints": [cp.to_dict() for cp in checkpoints[-limit:]],
        }

    @router.post("/config")
    async def update_config(model: Optional[str] = None, loop_interval: Optional[int] = None):
        """Update cognitive core configuration."""
        core = get_cognitive_core()

        if model:
            core.model = model
        if loop_interval:
            core.loop_interval = loop_interval

        return {
            "model": core.model,
            "loop_interval_seconds": core.loop_interval,
        }

    return router
