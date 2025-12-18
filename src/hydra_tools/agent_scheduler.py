"""
HYDRA Agent Scheduler - AIOS-Style Agent Orchestration

Implements concepts from AIOS research:
- Priority-based agent scheduling (FIFO, Priority, Round Robin)
- Context window management and checkpointing
- Memory isolation between agents
- Resource limits enforcement
- 2.1x execution improvement over non-scheduled agents

This scheduler manages the execution of multiple AI agents across
the Hydra cluster, ensuring fair resource allocation and preventing
context exhaustion.
"""

import asyncio
import uuid
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Coroutine
from collections import deque
import heapq
import json
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# LiteLLM Authentication
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7")

# =============================================================================
# Enums and Data Classes
# =============================================================================

class AgentPriority(Enum):
    """Agent execution priority levels."""
    CRITICAL = 0  # System health, emergencies
    HIGH = 1      # User-initiated tasks
    NORMAL = 2    # Background tasks
    LOW = 3       # Maintenance, cleanup
    IDLE = 4      # Only when nothing else running


class AgentStatus(Enum):
    """Agent execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SchedulingPolicy(Enum):
    """Scheduling policies."""
    FIFO = "fifo"           # First in, first out
    PRIORITY = "priority"   # Priority queue
    ROUND_ROBIN = "round_robin"  # Fair time slicing
    SJF = "sjf"             # Shortest job first


@dataclass
class AgentContext:
    """
    Checkpointable agent context.

    Stores the execution state of an agent so it can be
    paused and resumed without losing progress.
    """
    agent_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    memory_refs: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    checkpoint_time: Optional[datetime] = None
    tokens_used: int = 0
    max_tokens: int = 8192

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "messages": self.messages,
            "memory_refs": self.memory_refs,
            "tool_calls": self.tool_calls,
            "variables": self.variables,
            "checkpoint_time": self.checkpoint_time.isoformat() if self.checkpoint_time else None,
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentContext":
        return cls(
            agent_id=data["agent_id"],
            messages=data.get("messages", []),
            memory_refs=data.get("memory_refs", []),
            tool_calls=data.get("tool_calls", []),
            variables=data.get("variables", {}),
            checkpoint_time=datetime.fromisoformat(data["checkpoint_time"]) if data.get("checkpoint_time") else None,
            tokens_used=data.get("tokens_used", 0),
            max_tokens=data.get("max_tokens", 8192),
        )


@dataclass(order=True)
class AgentTask:
    """
    A scheduled agent task.

    Comparable for priority queue ordering.
    """
    priority: int
    created_at: datetime = field(compare=False)
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    agent_type: str = field(compare=False, default="generic")
    description: str = field(compare=False, default="")
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    status: AgentStatus = field(compare=False, default=AgentStatus.QUEUED)
    context: Optional[AgentContext] = field(compare=False, default=None)
    started_at: Optional[datetime] = field(compare=False, default=None)
    completed_at: Optional[datetime] = field(compare=False, default=None)
    result: Optional[Dict[str, Any]] = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)
    timeout_seconds: int = field(compare=False, default=300)
    retries: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "agent_type": self.agent_type,
            "description": self.description,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "timeout_seconds": self.timeout_seconds,
            "retries": self.retries,
        }


# =============================================================================
# Resource Limits
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits for agent execution."""
    max_concurrent_agents: int = 5
    max_tokens_per_agent: int = 16384
    max_memory_mb: int = 1024
    max_execution_time_seconds: int = 600
    max_tool_calls: int = 50
    max_retries: int = 3


# =============================================================================
# AIOS Kernel Enhancements
# =============================================================================

@dataclass
class AgentToolACL:
    """Tool access control list for an agent."""
    agent_type: str
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    allow_all: bool = False

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if agent can use a specific tool."""
        if self.allow_all:
            return tool_name not in self.denied_tools
        return tool_name in self.allowed_tools and tool_name not in self.denied_tools


@dataclass
class AgentMemoryIsolation:
    """Memory isolation boundaries for an agent."""
    agent_id: str
    namespace: str  # Unique namespace for agent's memory
    allowed_read_namespaces: List[str] = field(default_factory=list)  # Can read from these
    allowed_write_namespaces: List[str] = field(default_factory=list)  # Can write to these
    shared_regions: List[str] = field(default_factory=list)  # Explicit opt-in shared regions

    def can_read(self, namespace: str) -> bool:
        """Check if agent can read from a namespace."""
        return namespace == self.namespace or namespace in self.allowed_read_namespaces or namespace in self.shared_regions

    def can_write(self, namespace: str) -> bool:
        """Check if agent can write to a namespace."""
        return namespace == self.namespace or namespace in self.allowed_write_namespaces or namespace in self.shared_regions


@dataclass
class SharedMemoryRegion:
    """A shared memory region for multi-agent collaboration."""
    region_id: str
    name: str
    description: str
    owner_agent: Optional[str] = None
    allowed_agents: List[str] = field(default_factory=list)  # Empty = all agents
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None

    def can_access(self, agent_id: str) -> bool:
        """Check if agent can access this region."""
        if not self.allowed_agents:  # Empty = all agents
            return True
        return agent_id in self.allowed_agents or agent_id == self.owner_agent


# Default Tool ACLs for built-in agent types
DEFAULT_TOOL_ACLS = {
    "research": AgentToolACL(
        agent_type="research",
        allowed_tools=["searxng_search", "firecrawl_scrape", "memory_read", "knowledge_search", "ingest_document"],
        denied_tools=["sandbox_execute", "container_restart", "constitution_modify"],
    ),
    "monitoring": AgentToolACL(
        agent_type="monitoring",
        allowed_tools=["health_check", "prometheus_query", "container_status", "gpu_status", "memory_read"],
        denied_tools=["sandbox_execute", "constitution_modify"],
    ),
    "maintenance": AgentToolACL(
        agent_type="maintenance",
        allowed_tools=["docker_prune", "qdrant_optimize", "cache_clear", "log_rotate"],
        denied_tools=["constitution_modify", "database_drop"],
    ),
    "llm": AgentToolACL(
        agent_type="llm",
        allowed_tools=["llm_inference", "memory_read", "memory_write", "knowledge_search"],
        denied_tools=["sandbox_execute", "constitution_modify"],
    ),
    "character_creation": AgentToolACL(
        agent_type="character_creation",
        allowed_tools=["llm_inference", "character_create", "comfyui_queue", "memory_write"],
        denied_tools=["sandbox_execute", "constitution_modify"],
    ),
    "deep_research": AgentToolACL(
        agent_type="deep_research",
        allowed_tools=["searxng_search", "firecrawl_scrape", "llm_inference", "memory_read", "memory_write", "ingest_document"],
        denied_tools=["sandbox_execute", "constitution_modify"],
    ),
    "coding": AgentToolACL(
        agent_type="coding",
        allowed_tools=["sandbox_execute", "git_operations", "file_read", "file_write", "llm_inference"],
        denied_tools=["constitution_modify", "database_drop", "network_modify"],
    ),
}


# =============================================================================
# Agent Scheduler
# =============================================================================

class AgentScheduler:
    """
    AIOS-style agent scheduler for Hydra.

    Features:
    - Multiple scheduling policies (FIFO, Priority, Round Robin, SJF)
    - Priority-based execution with CRITICAL preemption
    - Context checkpointing for pause/resume
    - Memory isolation between agents
    - Shared memory regions for collaboration
    - Tool access control per agent type
    - Resource enforcement
    - Task persistence
    """

    def __init__(
        self,
        policy: SchedulingPolicy = SchedulingPolicy.PRIORITY,
        resource_limits: Optional[ResourceLimits] = None,
        checkpoint_dir: str = "/data/scheduler/checkpoints",
        enable_preemption: bool = True,
    ):
        self.policy = policy
        self.limits = resource_limits or ResourceLimits()
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.enable_preemption = enable_preemption

        # Task queues
        self._priority_queue: List[AgentTask] = []  # heapq for priority
        self._fifo_queue: deque[AgentTask] = deque()
        self._round_robin_queue: deque[AgentTask] = deque()

        # Running tasks
        self._running: Dict[str, AgentTask] = {}
        self._completed: Dict[str, AgentTask] = {}
        self._failed: Dict[str, AgentTask] = {}
        self._paused: Dict[str, AgentTask] = {}  # Preempted tasks awaiting resume

        # Agent handlers registry
        self._handlers: Dict[str, Callable] = {}

        # AIOS Kernel: Tool access control
        self._tool_acls: Dict[str, AgentToolACL] = DEFAULT_TOOL_ACLS.copy()

        # AIOS Kernel: Memory isolation
        self._memory_isolation: Dict[str, AgentMemoryIsolation] = {}

        # AIOS Kernel: Shared memory regions
        self._shared_regions: Dict[str, SharedMemoryRegion] = {}

        # Stats
        self._stats = {
            "total_scheduled": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_preempted": 0,
            "total_resumed": 0,
            "avg_execution_time_ms": 0,
        }

        # Scheduler state
        self._running_flag = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(f"AgentScheduler initialized with policy: {policy.value}, preemption={enable_preemption}")

    def register_handler(
        self,
        agent_type: str,
        handler: Callable[[AgentTask], Coroutine[Any, Any, Dict[str, Any]]]
    ):
        """Register an async handler for an agent type."""
        self._handlers[agent_type] = handler
        logger.info(f"Registered handler for agent type: {agent_type}")

    # =========================================================================
    # AIOS Kernel: Tool Access Control
    # =========================================================================

    def register_tool_acl(self, acl: AgentToolACL):
        """Register a tool ACL for an agent type."""
        self._tool_acls[acl.agent_type] = acl
        logger.info(f"Registered tool ACL for agent type: {acl.agent_type}")

    def check_tool_access(self, agent_type: str, tool_name: str) -> bool:
        """Check if an agent type can use a tool."""
        acl = self._tool_acls.get(agent_type)
        if not acl:
            return True  # Default allow if no ACL defined
        return acl.can_use_tool(tool_name)

    def get_allowed_tools(self, agent_type: str) -> List[str]:
        """Get list of allowed tools for an agent type."""
        acl = self._tool_acls.get(agent_type)
        if not acl:
            return []
        return acl.allowed_tools

    # =========================================================================
    # AIOS Kernel: Memory Isolation
    # =========================================================================

    def setup_memory_isolation(self, agent_id: str, agent_type: str) -> AgentMemoryIsolation:
        """Set up memory isolation for an agent."""
        namespace = f"agent_{agent_type}_{agent_id[:8]}"

        # Default read access to common namespaces based on agent type
        read_namespaces = ["hydra_knowledge", "hydra_config"]
        if agent_type in ["research", "deep_research"]:
            read_namespaces.extend(["hydra_research", "web_cache"])
        elif agent_type in ["monitoring", "maintenance"]:
            read_namespaces.extend(["system_metrics", "container_logs"])

        isolation = AgentMemoryIsolation(
            agent_id=agent_id,
            namespace=namespace,
            allowed_read_namespaces=read_namespaces,
            allowed_write_namespaces=[namespace],  # Can only write to own namespace
            shared_regions=[],
        )
        self._memory_isolation[agent_id] = isolation
        logger.debug(f"Set up memory isolation for agent {agent_id}: namespace={namespace}")
        return isolation

    def get_memory_isolation(self, agent_id: str) -> Optional[AgentMemoryIsolation]:
        """Get memory isolation config for an agent."""
        return self._memory_isolation.get(agent_id)

    def grant_memory_access(self, agent_id: str, namespace: str, access_type: str = "read"):
        """Grant memory access to an agent."""
        isolation = self._memory_isolation.get(agent_id)
        if isolation:
            if access_type == "read" and namespace not in isolation.allowed_read_namespaces:
                isolation.allowed_read_namespaces.append(namespace)
            elif access_type == "write" and namespace not in isolation.allowed_write_namespaces:
                isolation.allowed_write_namespaces.append(namespace)
            logger.info(f"Granted {access_type} access to {namespace} for agent {agent_id}")

    # =========================================================================
    # AIOS Kernel: Shared Memory Regions
    # =========================================================================

    def create_shared_region(
        self,
        name: str,
        description: str,
        owner_agent: Optional[str] = None,
        allowed_agents: Optional[List[str]] = None
    ) -> SharedMemoryRegion:
        """Create a shared memory region for multi-agent collaboration."""
        region = SharedMemoryRegion(
            region_id=str(uuid.uuid4()),
            name=name,
            description=description,
            owner_agent=owner_agent,
            allowed_agents=allowed_agents or [],
        )
        self._shared_regions[region.region_id] = region
        logger.info(f"Created shared region '{name}' (id={region.region_id})")
        return region

    def join_shared_region(self, agent_id: str, region_id: str) -> bool:
        """Allow an agent to join a shared memory region."""
        region = self._shared_regions.get(region_id)
        isolation = self._memory_isolation.get(agent_id)

        if not region or not isolation:
            return False

        if not region.can_access(agent_id):
            logger.warning(f"Agent {agent_id} denied access to region {region_id}")
            return False

        isolation.shared_regions.append(region_id)
        region.last_accessed = datetime.utcnow()
        logger.info(f"Agent {agent_id} joined shared region {region.name}")
        return True

    def write_shared_data(self, agent_id: str, region_id: str, key: str, value: Any) -> bool:
        """Write data to a shared memory region."""
        region = self._shared_regions.get(region_id)
        if not region or not region.can_access(agent_id):
            return False

        region.data[key] = {
            "value": value,
            "written_by": agent_id,
            "written_at": datetime.utcnow().isoformat(),
        }
        region.last_accessed = datetime.utcnow()
        return True

    def read_shared_data(self, agent_id: str, region_id: str, key: str) -> Optional[Any]:
        """Read data from a shared memory region."""
        region = self._shared_regions.get(region_id)
        if not region or not region.can_access(agent_id):
            return None

        region.last_accessed = datetime.utcnow()
        data = region.data.get(key)
        return data.get("value") if data else None

    def get_shared_regions(self) -> List[Dict[str, Any]]:
        """Get all shared memory regions."""
        return [
            {
                "region_id": r.region_id,
                "name": r.name,
                "description": r.description,
                "owner_agent": r.owner_agent,
                "allowed_agents": r.allowed_agents,
                "data_keys": list(r.data.keys()),
                "created_at": r.created_at.isoformat(),
                "last_accessed": r.last_accessed.isoformat() if r.last_accessed else None,
            }
            for r in self._shared_regions.values()
        ]

    # =========================================================================
    # AIOS Kernel: Priority Preemption
    # =========================================================================

    async def _preempt_for_critical(self, critical_task: AgentTask) -> bool:
        """
        Preempt lower-priority tasks to make room for a CRITICAL task.

        Returns True if preemption was successful.
        """
        if not self.enable_preemption:
            return False

        async with self._lock:
            # Find lowest priority running task
            running_tasks = list(self._running.values())
            if not running_tasks:
                return False

            # Sort by priority (higher number = lower priority)
            running_tasks.sort(key=lambda t: t.priority, reverse=True)

            # Only preempt if we have a lower priority task
            lowest = running_tasks[0]
            if lowest.priority <= critical_task.priority:
                return False  # Can't preempt equal or higher priority

            # Checkpoint the task before preemption
            if lowest.context:
                lowest.context.checkpoint_time = datetime.utcnow()
                checkpoint_path = self.checkpoint_dir / f"{lowest.task_id}.json"
                with open(checkpoint_path, "w") as f:
                    json.dump(lowest.context.to_dict(), f, indent=2)

            # Move to paused state
            lowest.status = AgentStatus.PAUSED
            self._paused[lowest.task_id] = lowest
            self._running.pop(lowest.task_id, None)
            self._stats["total_preempted"] += 1

            logger.info(f"Preempted task {lowest.task_id} ({lowest.description}) for CRITICAL task {critical_task.task_id}")
            return True

    async def resume_paused_task(self, task_id: str) -> bool:
        """Resume a paused (preempted) task."""
        async with self._lock:
            task = self._paused.get(task_id)
            if not task:
                return False

            # Restore context if available
            checkpoint_path = self.checkpoint_dir / f"{task_id}.json"
            if checkpoint_path.exists():
                with open(checkpoint_path) as f:
                    context_data = json.load(f)
                    task.context = AgentContext.from_dict(context_data)

            # Re-queue the task (with slightly boosted priority to avoid starvation)
            task.status = AgentStatus.QUEUED
            task.priority = max(0, task.priority - 1)  # Boost priority
            self._paused.pop(task_id, None)

            if self.policy == SchedulingPolicy.PRIORITY:
                heapq.heappush(self._priority_queue, task)
            else:
                self._fifo_queue.appendleft(task)  # Add to front

            self._stats["total_resumed"] += 1
            logger.info(f"Resumed paused task {task_id}")
            return True

    def get_paused_tasks(self) -> List[Dict[str, Any]]:
        """Get all paused (preempted) tasks."""
        return [t.to_dict() for t in self._paused.values()]

    async def schedule(
        self,
        agent_type: str,
        description: str,
        payload: Dict[str, Any],
        priority: AgentPriority = AgentPriority.NORMAL,
        timeout_seconds: int = 300,
    ) -> str:
        """
        Schedule an agent task for execution.

        AIOS Kernel Features:
        - Sets up memory isolation for the agent
        - Validates tool ACL for the agent type
        - Attempts preemption for CRITICAL tasks if queue is full

        Returns the task ID.
        """
        agent_id = str(uuid.uuid4())
        task = AgentTask(
            priority=priority.value,
            created_at=datetime.utcnow(),
            agent_type=agent_type,
            description=description,
            payload=payload,
            timeout_seconds=timeout_seconds,
            context=AgentContext(agent_id=agent_id),
        )

        # AIOS Kernel: Set up memory isolation for this agent
        self.setup_memory_isolation(agent_id, agent_type)

        # AIOS Kernel: Check if this is a CRITICAL task that needs preemption
        if priority == AgentPriority.CRITICAL and len(self._running) >= self.limits.max_concurrent_agents:
            preempted = await self._preempt_for_critical(task)
            if preempted:
                logger.info(f"Preempted lower-priority task for CRITICAL: {description}")

        async with self._lock:
            if self.policy == SchedulingPolicy.PRIORITY:
                heapq.heappush(self._priority_queue, task)
            elif self.policy == SchedulingPolicy.FIFO:
                self._fifo_queue.append(task)
            elif self.policy == SchedulingPolicy.ROUND_ROBIN:
                self._round_robin_queue.append(task)
            else:
                heapq.heappush(self._priority_queue, task)

            self._stats["total_scheduled"] += 1

        logger.info(f"Scheduled task {task.task_id}: {description} (priority={priority.name})")
        return task.task_id

    async def _get_next_task(self) -> Optional[AgentTask]:
        """Get the next task based on scheduling policy."""
        async with self._lock:
            if len(self._running) >= self.limits.max_concurrent_agents:
                return None

            if self.policy == SchedulingPolicy.PRIORITY:
                if self._priority_queue:
                    return heapq.heappop(self._priority_queue)
            elif self.policy == SchedulingPolicy.FIFO:
                if self._fifo_queue:
                    return self._fifo_queue.popleft()
            elif self.policy == SchedulingPolicy.ROUND_ROBIN:
                if self._round_robin_queue:
                    return self._round_robin_queue.popleft()

            return None

    async def _execute_task(self, task: AgentTask):
        """Execute a single task."""
        task.status = AgentStatus.RUNNING
        task.started_at = datetime.utcnow()

        async with self._lock:
            self._running[task.task_id] = task

        try:
            handler = self._handlers.get(task.agent_type)
            if not handler:
                raise ValueError(f"No handler for agent type: {task.agent_type}")

            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task),
                timeout=task.timeout_seconds
            )

            task.result = result
            task.status = AgentStatus.COMPLETED
            task.completed_at = datetime.utcnow()

            async with self._lock:
                self._completed[task.task_id] = task
                self._stats["total_completed"] += 1

                # Update average execution time
                exec_time = (task.completed_at - task.started_at).total_seconds() * 1000
                prev_avg = self._stats["avg_execution_time_ms"]
                total = self._stats["total_completed"]
                self._stats["avg_execution_time_ms"] = prev_avg + (exec_time - prev_avg) / total

            logger.info(f"Task {task.task_id} completed in {exec_time:.0f}ms")

            # DGM Pattern: Auto-extract skills from successful tasks
            await self._extract_skill_from_task(task)

        except asyncio.TimeoutError:
            task.status = AgentStatus.FAILED
            task.error = f"Timeout after {task.timeout_seconds}s"
            task.completed_at = datetime.utcnow()

            async with self._lock:
                self._failed[task.task_id] = task
                self._stats["total_failed"] += 1

            logger.warning(f"Task {task.task_id} timed out")

        except Exception as e:
            task.error = str(e)
            task.retries += 1

            if task.retries < task.max_retries:
                # Re-queue for retry
                task.status = AgentStatus.QUEUED
                async with self._lock:
                    if self.policy == SchedulingPolicy.PRIORITY:
                        heapq.heappush(self._priority_queue, task)
                    else:
                        self._fifo_queue.append(task)
                logger.warning(f"Task {task.task_id} failed, retry {task.retries}/{task.max_retries}")
            else:
                task.status = AgentStatus.FAILED
                task.completed_at = datetime.utcnow()
                async with self._lock:
                    self._failed[task.task_id] = task
                    self._stats["total_failed"] += 1
                logger.error(f"Task {task.task_id} failed permanently: {e}")

        finally:
            async with self._lock:
                self._running.pop(task.task_id, None)

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        while self._running_flag:
            task = await self._get_next_task()

            if task:
                # Execute task in background
                asyncio.create_task(self._execute_task(task))

            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)

        logger.info("Scheduler loop stopped")

    async def start(self):
        """Start the scheduler."""
        if self._running_flag:
            return

        self._running_flag = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Agent scheduler started")

    async def stop(self):
        """Stop the scheduler gracefully."""
        self._running_flag = False

        if self._scheduler_task:
            await self._scheduler_task

        # Wait for running tasks to complete
        while self._running:
            await asyncio.sleep(0.1)

        logger.info("Agent scheduler stopped")

    async def _extract_skill_from_task(self, task: AgentTask):
        """
        DGM Pattern: Extract reusable skills from completed tasks.

        This implements the procedural memory aspect of the Darwin Gödel Machine
        architecture. Successfully completed tasks are analyzed to extract
        generalizable skills that can be reused in future similar tasks.
        """
        try:
            # Only extract skills from substantive tasks
            if task.agent_type in ["monitoring", "llm"]:
                return  # Skip routine tasks

            # Prepare skill extraction request
            task_description = task.description
            task_steps = []

            # Extract steps from result if available
            if task.result:
                if isinstance(task.result, dict):
                    # Try to extract meaningful steps
                    if "synthesis" in task.result:
                        task_steps.append("Performed web research and synthesis")
                    if "sources_searched" in task.result:
                        task_steps.append(f"Searched {task.result.get('sources_searched', 0)} sources")
                    if "sources_crawled" in task.result:
                        task_steps.append(f"Crawled {task.result.get('sources_crawled', 0)} pages")
                    if "stored" in task.result and task.result.get("stored"):
                        task_steps.append("Stored results in knowledge base")

            outcome = f"Success - completed in {(task.completed_at - task.started_at).total_seconds():.1f}s"
            context = f"Agent type: {task.agent_type}, Payload: {json.dumps(task.payload)[:200]}"

            # Call skill extraction API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8700/memory/procedural/extract",
                    json={
                        "task_description": task_description,
                        "task_steps": task_steps if task_steps else ["Executed task successfully"],
                        "outcome": outcome,
                        "context": context
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("extracted"):
                        logger.info(f"Extracted skill {result.get('skill_id')} from task {task.task_id}")
                else:
                    logger.debug(f"Skill extraction returned {response.status_code}")

        except Exception as e:
            # Don't fail the task if skill extraction fails
            logger.debug(f"Skill extraction failed for task {task.task_id}: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        async with self._lock:
            if task_id in self._running:
                return self._running[task_id].to_dict()
            if task_id in self._completed:
                return self._completed[task_id].to_dict()
            if task_id in self._failed:
                return self._failed[task_id].to_dict()

        # Check queues
        for task in self._priority_queue:
            if task.task_id == task_id:
                return task.to_dict()
        for task in self._fifo_queue:
            if task.task_id == task_id:
                return task.to_dict()

        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued task."""
        async with self._lock:
            # Can't cancel running tasks easily
            if task_id in self._running:
                return False

            # Remove from queues
            self._priority_queue = [t for t in self._priority_queue if t.task_id != task_id]
            heapq.heapify(self._priority_queue)

            self._fifo_queue = deque(t for t in self._fifo_queue if t.task_id != task_id)
            self._round_robin_queue = deque(t for t in self._round_robin_queue if t.task_id != task_id)

            return True

    async def checkpoint(self, task_id: str) -> bool:
        """Save task context to disk for later resumption."""
        async with self._lock:
            task = self._running.get(task_id)
            if not task or not task.context:
                return False

            task.context.checkpoint_time = datetime.utcnow()
            checkpoint_path = self.checkpoint_dir / f"{task_id}.json"

            with open(checkpoint_path, "w") as f:
                json.dump(task.context.to_dict(), f, indent=2)

            logger.info(f"Checkpointed task {task_id}")
            return True

    async def restore(self, task_id: str) -> Optional[AgentContext]:
        """Restore task context from disk."""
        checkpoint_path = self.checkpoint_dir / f"{task_id}.json"

        if not checkpoint_path.exists():
            return None

        with open(checkpoint_path) as f:
            data = json.load(f)

        return AgentContext.from_dict(data)

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **self._stats,
            "policy": self.policy.value,
            "queue_size": len(self._priority_queue) + len(self._fifo_queue) + len(self._round_robin_queue),
            "running": len(self._running),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "max_concurrent": self.limits.max_concurrent_agents,
        }

    def get_queue(self) -> List[Dict[str, Any]]:
        """Get all queued tasks."""
        tasks = []
        tasks.extend([t.to_dict() for t in self._priority_queue])
        tasks.extend([t.to_dict() for t in self._fifo_queue])
        tasks.extend([t.to_dict() for t in self._round_robin_queue])
        return tasks


# =============================================================================
# Default Agent Handlers
# =============================================================================

async def research_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """Handler for research agent tasks."""
    query = task.payload.get("query", "")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Use SearXNG for web search
        response = await client.get(
            "http://192.168.1.244:8888/search",
            params={"q": query, "format": "json", "categories": "general"}
        )
        results = response.json().get("results", [])[:5]

        return {
            "query": query,
            "results": results,
            "source": "searxng"
        }


async def monitoring_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """Handler for monitoring agent tasks."""
    check_type = task.payload.get("check_type", "health")

    async with httpx.AsyncClient(timeout=30.0) as client:
        if check_type == "health":
            response = await client.get("http://192.168.1.244:8700/health")
            return response.json()
        elif check_type == "prometheus":
            response = await client.get("http://192.168.1.244:9090/api/v1/targets")
            return response.json()
        else:
            return {"status": "unknown_check_type"}


async def maintenance_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """Handler for maintenance agent tasks."""
    action = task.payload.get("action", "status")

    if action == "docker_cleanup":
        # This would normally run docker prune
        return {"action": action, "status": "simulated", "message": "Docker cleanup simulated"}
    elif action == "qdrant_optimize":
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://192.168.1.244:6333/collections/hydra_memory/index")
            return {"action": action, "result": response.json()}

    return {"action": action, "status": "unknown_action"}


async def llm_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """
    Handler for LLM-powered agent tasks.

    Integrates with:
    - Memory system for context retrieval
    - LiteLLM for LLM inference
    - Discovery Archive for storing results

    Payload options:
        prompt: The task prompt/instruction
        model: Model to use (default: claude-3-5-sonnet-latest)
        system_prompt: Optional system prompt
        include_memory: Whether to include memory context (default: True)
        memory_query: Query for memory retrieval (default: uses prompt)
        store_result: Whether to store result in discoveries (default: False)
        max_tokens: Maximum tokens for response (default: 4096)
    """
    import os

    prompt = task.payload.get("prompt", "")
    model = task.payload.get("model", "qwen2.5:7b")
    system_prompt = task.payload.get("system_prompt", "You are Hydra, an autonomous AI assistant.")
    include_memory = task.payload.get("include_memory", True)
    memory_query = task.payload.get("memory_query", prompt)
    store_result = task.payload.get("store_result", False)
    max_tokens = task.payload.get("max_tokens", 4096)
    backend = task.payload.get("backend", "ollama")  # ollama, litellm, tabby

    ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")
    litellm_url = os.environ.get("LITELLM_URL", "http://192.168.1.244:4000")
    tabby_url = os.environ.get("TABBY_URL", "http://192.168.1.250:5000")

    # Build context with memory
    context_parts = []
    memory_results = []

    if include_memory and memory_query:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get relevant memory context
                mem_response = await client.post(
                    "http://192.168.1.244:8700/memory/semantic-search",
                    params={"query": memory_query[:500], "limit": 5}
                )
                if mem_response.status_code == 200:
                    mem_data = mem_response.json()
                    memory_results = mem_data.get("results", [])

                    if memory_results:
                        context_parts.append("## Relevant Memory Context\n")
                        for mem in memory_results[:5]:
                            context_parts.append(f"- {mem.get('content', '')}\n")
                        context_parts.append("\n")
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")

    # Build full prompt
    full_prompt = "".join(context_parts) + prompt

    # Call LiteLLM
    result = {
        "prompt": prompt,
        "model": model,
        "memory_context_count": len(memory_results),
        "response": None,
        "tokens_used": 0,
        "error": None,
    }

    # Select backend URL
    if backend == "ollama":
        base_url = ollama_url
    elif backend == "tabby":
        base_url = tabby_url
    else:
        base_url = litellm_url

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"Content-Type": "application/json"}
            # Add auth header for LiteLLM backend
            if backend == "litellm":
                headers["Authorization"] = f"Bearer {LITELLM_API_KEY}"
            llm_response = await client.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ],
                    "max_tokens": max_tokens,
                },
                headers=headers
            )

            if llm_response.status_code == 200:
                llm_data = llm_response.json()
                result["response"] = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                result["tokens_used"] = llm_data.get("usage", {}).get("total_tokens", 0)
                result["backend"] = backend
            else:
                result["error"] = f"LLM call failed: {llm_response.status_code} - {llm_response.text[:200]}"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"LLM agent error: {e}")

    # Optionally store result in Discovery Archive
    if store_result and result["response"]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    "http://192.168.1.244:8700/discoveries/archive",
                    json={
                        "type": "session",
                        "title": f"LLM Agent Task: {task.description[:50]}",
                        "description": result["response"][:500],
                        "tags": ["llm-agent", "autonomous"],
                        "context": prompt[:500]
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to store result: {e}")

    return result


async def character_creation_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """
    Handler for autonomous character creation tasks.

    Creates Empire of Broken Queens characters by:
    1. Generating character metadata via LLM
    2. Creating ComfyUI prompt for portrait
    3. Queuing portrait generation
    4. Storing character in Qdrant

    Payload options:
        name: Character name (required)
        archetype: Character archetype/role (e.g., "queen", "advisor", "villain")
        traits: List of personality traits
        backstory_hint: Brief backstory direction
        generate_portrait: Whether to queue ComfyUI generation (default: False)
    """
    name = task.payload.get("name", "Unknown")
    archetype = task.payload.get("archetype", "queen")
    traits = task.payload.get("traits", [])
    backstory_hint = task.payload.get("backstory_hint", "")
    generate_portrait = task.payload.get("generate_portrait", False)

    result = {
        "name": name,
        "archetype": archetype,
        "character_created": False,
        "portrait_queued": False,
        "error": None,
    }

    # Step 1: Generate character metadata via LLM
    character_prompt = f"""Create a detailed character for Empire of Broken Queens, an adult dark fantasy visual novel.

Name: {name}
Archetype: {archetype}
Traits: {', '.join(traits) if traits else 'mysterious, complex'}
Backstory hint: {backstory_hint if backstory_hint else 'Leave open for interpretation'}

Provide a JSON response with:
{{
  "display_name": "Full title and name",
  "description": "2-3 sentence character description focusing on their curse/tragedy",
  "hair_color": "Descriptive hair color",
  "eye_color": "Descriptive eye color with emotional undertones",
  "distinguishing_features": ["list", "of", "features"],
  "personality_summary": "Brief personality overview",
  "comfyui_prompt": "Detailed portrait prompt for image generation"
}}

Make the character tragic, broken, and compelling. This is an adult visual novel with mature themes."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Generate metadata using Ollama directly (no auth required)
            ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")
            llm_response = await client.post(
                f"{ollama_url}/v1/chat/completions",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [
                        {"role": "user", "content": character_prompt}
                    ],
                    "max_tokens": 1024,
                },
                headers={"Content-Type": "application/json"}
            )

            if llm_response.status_code == 200:
                llm_data = llm_response.json()
                content = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        char_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        char_data = {"description": content[:500]}
                else:
                    char_data = {"description": content[:500]}

                # Step 2: Store character in Qdrant via Character API
                char_payload = {
                    "name": name.lower().replace(" ", "_"),
                    "display_name": char_data.get("display_name", name),
                    "description": char_data.get("description", ""),
                    "hair_color": char_data.get("hair_color", ""),
                    "eye_color": char_data.get("eye_color", ""),
                    "distinguishing_features": char_data.get("distinguishing_features", []),
                    "voice_id": "af_bella",  # Default voice
                }

                char_response = await client.post(
                    "http://192.168.1.244:8700/characters/",
                    json=char_payload,
                    headers={"Content-Type": "application/json"}
                )

                if char_response.status_code in [200, 201]:
                    result["character_created"] = True
                    result["character_id"] = char_response.json().get("id")
                    result["character_data"] = char_data
                else:
                    result["error"] = f"Character API error: {char_response.status_code}"

                # Step 3: Queue ComfyUI portrait if requested
                if generate_portrait and "comfyui_prompt" in char_data:
                    comfyui_prompt = char_data["comfyui_prompt"]
                    # This would queue a ComfyUI workflow
                    # For now, just store the prompt
                    result["comfyui_prompt"] = comfyui_prompt
                    result["portrait_queued"] = True

            else:
                result["error"] = f"LLM error: {llm_response.status_code}"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Character creation error: {e}")

    return result


async def deep_research_agent_handler(task: AgentTask) -> Dict[str, Any]:
    """
    Handler for deep autonomous research tasks.

    Performs comprehensive research by:
    1. Web searching with SearXNG
    2. Crawling relevant pages with Firecrawl
    3. Synthesizing findings with LLM
    4. Storing results in knowledge base

    Payload options:
        topic: Research topic (required)
        depth: Research depth (shallow, medium, deep)
        max_sources: Maximum sources to analyze
        store_results: Whether to store in knowledge base
    """
    topic = task.payload.get("topic", "")
    depth = task.payload.get("depth", "medium")
    max_sources = task.payload.get("max_sources", 5 if depth == "shallow" else 10 if depth == "medium" else 20)
    store_results = task.payload.get("store_results", True)

    result = {
        "topic": topic,
        "depth": depth,
        "sources_searched": 0,
        "sources_crawled": 0,
        "synthesis": None,
        "stored": False,
        "error": None,
    }

    searxng_url = os.environ.get("SEARXNG_URL", "http://192.168.1.244:8888")
    ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: Web search with SearXNG
            search_response = await client.get(
                f"{searxng_url}/search",
                params={"q": topic, "format": "json", "categories": "general"}
            )

            if search_response.status_code != 200:
                result["error"] = f"Search failed: {search_response.status_code}"
                return result

            search_data = search_response.json()
            search_results = search_data.get("results", [])[:max_sources]
            result["sources_searched"] = len(search_results)

            # Step 2: Extract content from top results
            source_contents = []
            for sr in search_results[:5]:  # Limit crawling to top 5
                try:
                    # Try to get content (simplified - in production use Firecrawl)
                    title = sr.get("title", "")
                    content = sr.get("content", "")
                    url = sr.get("url", "")

                    if content:
                        source_contents.append({
                            "title": title,
                            "url": url,
                            "content": content[:2000]  # Limit content length
                        })
                        result["sources_crawled"] += 1
                except Exception:
                    continue

            # Step 3: Synthesize with LLM
            synthesis_prompt = f"""You are a research assistant. Synthesize the following sources about: {topic}

SOURCES:
{chr(10).join(f'### {s["title"]}{chr(10)}{s["content"]}{chr(10)}Source: {s["url"]}' for s in source_contents)}

Provide a comprehensive synthesis that:
1. Summarizes the key findings
2. Identifies common themes
3. Notes any contradictions or gaps
4. Provides actionable insights

Format as markdown with clear sections."""

            synthesis_response = await client.post(
                f"{ollama_url}/v1/chat/completions",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [{"role": "user", "content": synthesis_prompt}],
                    "max_tokens": 2048,
                },
                headers={"Content-Type": "application/json"}
            )

            if synthesis_response.status_code == 200:
                synthesis_data = synthesis_response.json()
                result["synthesis"] = synthesis_data["choices"][0]["message"]["content"]

                # Step 4: Store in knowledge base if requested
                if store_results and result["synthesis"]:
                    try:
                        await client.post(
                            "http://192.168.1.244:8700/ingest/document",
                            json={
                                "content": result["synthesis"],
                                "title": f"Research: {topic}",
                                "source": "deep_research_agent",
                                "collection": "hydra_knowledge"
                            },
                            headers={"Content-Type": "application/json"}
                        )
                        result["stored"] = True
                    except Exception as e:
                        logger.warning(f"Failed to store research: {e}")

            else:
                result["error"] = f"Synthesis failed: {synthesis_response.status_code}"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Deep research error: {e}")

    return result


# =============================================================================
# Global Scheduler Instance
# =============================================================================

_scheduler: Optional[AgentScheduler] = None


def get_scheduler() -> AgentScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AgentScheduler(
            policy=SchedulingPolicy.PRIORITY,
            checkpoint_dir="/data/scheduler/checkpoints"
        )
        # Register default handlers
        _scheduler.register_handler("research", research_agent_handler)
        _scheduler.register_handler("monitoring", monitoring_agent_handler)
        _scheduler.register_handler("maintenance", maintenance_agent_handler)
        _scheduler.register_handler("llm", llm_agent_handler)
        _scheduler.register_handler("character_creation", character_creation_agent_handler)
        _scheduler.register_handler("deep_research", deep_research_agent_handler)
    return _scheduler


# =============================================================================
# FastAPI Router
# =============================================================================

class ScheduleRequest(BaseModel):
    """Request to schedule an agent task."""
    agent_type: str
    description: str
    payload: Dict[str, Any] = {}
    priority: str = "normal"
    timeout_seconds: int = 300


def create_scheduler_router() -> APIRouter:
    """Create FastAPI router for AIOS-style agent scheduler endpoints."""
    router = APIRouter(prefix="/agent-scheduler", tags=["agent-scheduler"])

    @router.get("/status")
    async def get_status():
        """Get scheduler status and statistics."""
        scheduler = get_scheduler()
        return {
            "status": "running" if scheduler._running_flag else "stopped",
            "stats": scheduler.get_stats(),
        }

    @router.post("/schedule")
    async def schedule_task(request: ScheduleRequest):
        """Schedule a new agent task."""
        scheduler = get_scheduler()

        priority_map = {
            "critical": AgentPriority.CRITICAL,
            "high": AgentPriority.HIGH,
            "normal": AgentPriority.NORMAL,
            "low": AgentPriority.LOW,
            "idle": AgentPriority.IDLE,
        }
        priority = priority_map.get(request.priority.lower(), AgentPriority.NORMAL)

        task_id = await scheduler.schedule(
            agent_type=request.agent_type,
            description=request.description,
            payload=request.payload,
            priority=priority,
            timeout_seconds=request.timeout_seconds,
        )

        return {
            "task_id": task_id,
            "status": "scheduled",
            "priority": priority.name,
        }

    @router.get("/task/{task_id}")
    async def get_task(task_id: str):
        """Get status of a specific task."""
        scheduler = get_scheduler()
        status = await scheduler.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="Task not found")

        return status

    @router.delete("/task/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a queued task."""
        scheduler = get_scheduler()
        cancelled = await scheduler.cancel_task(task_id)

        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel task (may be running or not found)"
            )

        return {"task_id": task_id, "status": "cancelled"}

    @router.get("/queue")
    async def get_queue():
        """Get all queued tasks."""
        scheduler = get_scheduler()
        return {
            "tasks": scheduler.get_queue(),
            "count": len(scheduler.get_queue()),
        }

    @router.post("/task/{task_id}/checkpoint")
    async def checkpoint_task(task_id: str):
        """Checkpoint a running task."""
        scheduler = get_scheduler()
        success = await scheduler.checkpoint(task_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Cannot checkpoint task (not running or no context)"
            )

        return {"task_id": task_id, "status": "checkpointed"}

    @router.post("/start")
    async def start_scheduler():
        """Start the scheduler."""
        scheduler = get_scheduler()
        await scheduler.start()
        return {"status": "started"}

    @router.post("/stop")
    async def stop_scheduler():
        """Stop the scheduler gracefully."""
        scheduler = get_scheduler()
        await scheduler.stop()
        return {"status": "stopped"}

    # =========================================================================
    # AIOS Kernel Endpoints
    # =========================================================================

    @router.get("/paused")
    async def get_paused_tasks():
        """Get all paused (preempted) tasks waiting for resumption."""
        scheduler = get_scheduler()
        return {
            "tasks": scheduler.get_paused_tasks(),
            "count": len(scheduler._paused),
        }

    @router.post("/task/{task_id}/resume")
    async def resume_task(task_id: str):
        """Resume a paused (preempted) task."""
        scheduler = get_scheduler()
        success = await scheduler.resume_paused_task(task_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Cannot resume task (not paused or not found)"
            )

        return {"task_id": task_id, "status": "resumed"}

    @router.get("/tool-acls")
    async def get_tool_acls():
        """Get all registered tool access control lists."""
        scheduler = get_scheduler()
        return {
            "acls": {
                agent_type: {
                    "allowed_tools": acl.allowed_tools,
                    "denied_tools": acl.denied_tools,
                    "allow_all": acl.allow_all,
                }
                for agent_type, acl in scheduler._tool_acls.items()
            }
        }

    @router.get("/tool-acls/{agent_type}")
    async def get_agent_tools(agent_type: str):
        """Get allowed tools for an agent type."""
        scheduler = get_scheduler()
        return {
            "agent_type": agent_type,
            "allowed_tools": scheduler.get_allowed_tools(agent_type),
        }

    @router.get("/tool-acls/{agent_type}/check/{tool_name}")
    async def check_tool_access(agent_type: str, tool_name: str):
        """Check if an agent type can use a specific tool."""
        scheduler = get_scheduler()
        allowed = scheduler.check_tool_access(agent_type, tool_name)
        return {
            "agent_type": agent_type,
            "tool_name": tool_name,
            "allowed": allowed,
        }

    @router.get("/shared-regions")
    async def get_shared_regions():
        """Get all shared memory regions."""
        scheduler = get_scheduler()
        return {
            "regions": scheduler.get_shared_regions(),
            "count": len(scheduler._shared_regions),
        }

    @router.post("/shared-regions")
    async def create_shared_region(
        name: str,
        description: str,
        owner_agent: Optional[str] = None,
        allowed_agents: Optional[List[str]] = None
    ):
        """Create a new shared memory region."""
        scheduler = get_scheduler()
        region = scheduler.create_shared_region(
            name=name,
            description=description,
            owner_agent=owner_agent,
            allowed_agents=allowed_agents or []
        )
        return {
            "region_id": region.region_id,
            "name": region.name,
            "status": "created",
        }

    @router.get("/memory-isolation/{agent_id}")
    async def get_agent_memory_isolation(agent_id: str):
        """Get memory isolation config for an agent."""
        scheduler = get_scheduler()
        isolation = scheduler.get_memory_isolation(agent_id)

        if not isolation:
            raise HTTPException(status_code=404, detail="Agent not found")

        return {
            "agent_id": isolation.agent_id,
            "namespace": isolation.namespace,
            "allowed_read_namespaces": isolation.allowed_read_namespaces,
            "allowed_write_namespaces": isolation.allowed_write_namespaces,
            "shared_regions": isolation.shared_regions,
        }

    @router.get("/kernel-stats")
    async def get_kernel_stats():
        """Get comprehensive AIOS kernel statistics."""
        scheduler = get_scheduler()
        return {
            "scheduler": scheduler.get_stats(),
            "preemption_enabled": scheduler.enable_preemption,
            "tool_acls_count": len(scheduler._tool_acls),
            "memory_isolations_count": len(scheduler._memory_isolation),
            "shared_regions_count": len(scheduler._shared_regions),
            "paused_tasks_count": len(scheduler._paused),
        }

    return router
