"""
Agent-to-Agent (A2A) Protocol Implementation for Hydra

Implements Google's A2A protocol (v0.3) for agent interoperability:
- Agent Card discovery at /.well-known/agent-card.json
- JSON-RPC 2.0 message handling
- Task lifecycle management
- Multi-agent collaboration

Reference: https://a2a-protocol.org/latest/specification/

Author: Hydra Autonomous Caretaker
Created: 2025-12-19
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
import httpx

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

A2A_MESSAGES = Counter(
    "hydra_a2a_messages_total",
    "Total A2A messages",
    ["method", "direction"]  # direction: inbound/outbound
)

A2A_TASKS = Counter(
    "hydra_a2a_tasks_total",
    "Total A2A tasks",
    ["state"]
)

A2A_LATENCY = Histogram(
    "hydra_a2a_latency_seconds",
    "A2A operation latency",
    ["method"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0]
)


# =============================================================================
# Protocol Constants
# =============================================================================

A2A_VERSION = "0.3"

AGENT_CARD_PATH = "/.well-known/agent-card.json"


# =============================================================================
# Task States (per A2A spec)
# =============================================================================

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INPUT_REQUIRED = "input-required"
    REJECTED = "rejected"
    AUTH_REQUIRED = "auth-required"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AgentSkill:
    """A capability the agent can perform."""
    id: str
    name: str
    description: str
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentCard:
    """
    Agent Card - self-describing manifest for A2A discovery.
    Published at /.well-known/agent-card.json
    """
    name: str
    description: str
    url: str
    protocol_version: str = A2A_VERSION
    skills: List[AgentSkill] = field(default_factory=list)
    capabilities: Dict[str, bool] = field(default_factory=lambda: {
        "streaming": True,
        "pushNotifications": False,
        "stateSync": True,
    })
    security_schemes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "supportedInterfaces": [
                {
                    "protocol": "json-rpc",
                    "url": f"{self.url}/a2a/rpc",
                }
            ],
            "capabilities": self.capabilities,
            "skills": [s.to_dict() for s in self.skills],
            "securitySchemes": self.security_schemes,
        }


@dataclass
class MessagePart:
    """Content part within a message."""
    type: str  # "text", "file", "data"
    content: Any  # str for text, dict for file/data
    
    def to_dict(self) -> Dict[str, Any]:
        if self.type == "text":
            return {"text": self.content}
        elif self.type == "file":
            return {"file": self.content}
        else:
            return {"data": self.content}


@dataclass
class Message:
    """A2A message between agents."""
    message_id: str
    role: str  # "user" or "agent"
    parts: List[MessagePart]
    context_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "messageId": self.message_id,
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
            "contextId": self.context_id,
            "taskId": self.task_id,
        }


@dataclass
class Task:
    """A2A task with lifecycle."""
    task_id: str
    context_id: str
    state: TaskState
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "contextId": self.context_id,
            "state": self.state.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


# =============================================================================
# JSON-RPC Handler
# =============================================================================

class JsonRpcError(Exception):
    """JSON-RPC error with code and data."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# A2A-specific error codes
TASK_NOT_FOUND = -32001
TASK_CANCELLED = -32002
AGENT_BUSY = -32003
AUTH_REQUIRED = -32004


class A2AServer:
    """
    A2A Protocol Server - handles incoming A2A requests.
    """
    
    def __init__(
        self,
        agent_card: AgentCard,
        task_handler: Callable[[Message, Task], Awaitable[Message]],
    ):
        self.agent_card = agent_card
        self.task_handler = task_handler
        self.tasks: Dict[str, Task] = {}
        self.contexts: Dict[str, List[str]] = {}  # context_id -> task_ids
    
    async def handle_rpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC request.
        """
        # Validate request structure
        if not isinstance(request, dict):
            return self._error_response(None, PARSE_ERROR, "Invalid JSON")
        
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not method:
            return self._error_response(request_id, INVALID_REQUEST, "Missing method")
        
        A2A_MESSAGES.labels(method=method, direction="inbound").inc()
        
        try:
            # Route to handler
            handlers = {
                "SendMessage": self._handle_send_message,
                "GetTask": self._handle_get_task,
                "ListTasks": self._handle_list_tasks,
                "CancelTask": self._handle_cancel_task,
            }
            
            handler = handlers.get(method)
            if not handler:
                raise JsonRpcError(METHOD_NOT_FOUND, f"Unknown method: {method}")
            
            result = await handler(params)
            return self._success_response(request_id, result)
            
        except JsonRpcError as e:
            return self._error_response(request_id, e.code, e.message, e.data)
        except Exception as e:
            logger.exception(f"A2A RPC error: {e}")
            return self._error_response(request_id, INTERNAL_ERROR, str(e))
    
    async def _handle_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SendMessage - create or continue a task."""
        # Parse message
        message_data = params.get("message", {})
        parts = []
        for part in message_data.get("parts", []):
            if "text" in part:
                parts.append(MessagePart("text", part["text"]))
            elif "file" in part:
                parts.append(MessagePart("file", part["file"]))
            elif "data" in part:
                parts.append(MessagePart("data", part["data"]))
        
        message = Message(
            message_id=message_data.get("messageId", str(uuid.uuid4())),
            role="user",
            parts=parts,
            context_id=message_data.get("contextId"),
            task_id=message_data.get("taskId"),
        )
        
        # Get or create task
        if message.task_id and message.task_id in self.tasks:
            task = self.tasks[message.task_id]
        else:
            context_id = message.context_id or str(uuid.uuid4())
            task = Task(
                task_id=str(uuid.uuid4()),
                context_id=context_id,
                state=TaskState.SUBMITTED,
            )
            self.tasks[task.task_id] = task
            
            # Track by context
            if context_id not in self.contexts:
                self.contexts[context_id] = []
            self.contexts[context_id].append(task.task_id)
            
            A2A_TASKS.labels(state="submitted").inc()
        
        # Add message to task
        message.task_id = task.task_id
        message.context_id = task.context_id
        task.messages.append(message)
        task.state = TaskState.WORKING
        task.updated_at = datetime.utcnow()
        
        # Process message
        try:
            response = await self.task_handler(message, task)
            task.messages.append(response)
            task.state = TaskState.COMPLETED
            task.updated_at = datetime.utcnow()
            A2A_TASKS.labels(state="completed").inc()
            
            return {
                "task": task.to_dict(),
                "message": response.to_dict(),
            }
            
        except Exception as e:
            task.state = TaskState.FAILED
            task.metadata["error"] = str(e)
            task.updated_at = datetime.utcnow()
            A2A_TASKS.labels(state="failed").inc()
            raise
    
    async def _handle_get_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GetTask - retrieve task state."""
        task_id = params.get("taskId")
        if not task_id or task_id not in self.tasks:
            raise JsonRpcError(TASK_NOT_FOUND, f"Task not found: {task_id}")
        
        return {"task": self.tasks[task_id].to_dict()}
    
    async def _handle_list_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ListTasks - list tasks with optional filtering."""
        context_id = params.get("contextId")
        state = params.get("state")
        limit = params.get("limit", 50)
        
        tasks = list(self.tasks.values())
        
        # Apply filters
        if context_id:
            tasks = [t for t in tasks if t.context_id == context_id]
        if state:
            tasks = [t for t in tasks if t.state.value == state]
        
        # Sort by updated_at descending
        tasks.sort(key=lambda t: t.updated_at, reverse=True)
        tasks = tasks[:limit]
        
        return {
            "tasks": [t.to_dict() for t in tasks],
            "total": len(tasks),
        }
    
    async def _handle_cancel_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CancelTask - cancel a running task."""
        task_id = params.get("taskId")
        if not task_id or task_id not in self.tasks:
            raise JsonRpcError(TASK_NOT_FOUND, f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Only non-terminal tasks can be cancelled
        terminal_states = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.REJECTED}
        if task.state in terminal_states:
            raise JsonRpcError(TASK_CANCELLED, f"Task already in terminal state: {task.state.value}")
        
        task.state = TaskState.CANCELLED
        task.updated_at = datetime.utcnow()
        A2A_TASKS.labels(state="cancelled").inc()
        
        return {"task": task.to_dict()}
    
    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }
    
    def _error_response(self, request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error,
        }


# =============================================================================
# A2A Client
# =============================================================================

class A2AClient:
    """
    A2A Protocol Client - for communicating with remote agents.
    """
    
    def __init__(self, agent_url: str):
        self.agent_url = agent_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._agent_card: Optional[AgentCard] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def discover(self) -> Optional[Dict[str, Any]]:
        """Discover remote agent by fetching Agent Card."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.agent_url}{AGENT_CARD_PATH}")
            
            if response.status_code == 200:
                return response.json()
            
            logger.warning(f"Agent discovery failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Agent discovery error: {e}")
            return None
    
    async def send_message(
        self,
        text: str,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the remote agent."""
        client = await self._get_client()
        
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": text}],
                    "contextId": context_id,
                    "taskId": task_id,
                }
            }
        }
        
        A2A_MESSAGES.labels(method="SendMessage", direction="outbound").inc()
        
        # Get RPC endpoint from agent card if available
        card = await self.discover()
        rpc_url = f"{self.agent_url}/a2a/rpc"
        if card and card.get("supportedInterfaces"):
            for iface in card["supportedInterfaces"]:
                if iface.get("protocol") == "json-rpc":
                    rpc_url = iface.get("url", rpc_url)
                    break
        
        response = await client.post(
            rpc_url,
            json=request,
            headers={
                "Content-Type": "application/json",
                "A2A-Version": A2A_VERSION,
            }
        )
        
        return response.json()
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task status from remote agent."""
        client = await self._get_client()
        
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "GetTask",
            "params": {"taskId": task_id}
        }
        
        response = await client.post(
            f"{self.agent_url}/a2a/rpc",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
    
    async def close(self):
        if self._client:
            await self._client.aclose()


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Registry of known A2A agents.
    """
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.last_discovery: Dict[str, datetime] = {}
        self.discovery_interval = timedelta(minutes=5)
    
    async def register(self, agent_url: str) -> Optional[Dict[str, Any]]:
        """Register an agent by discovering its capabilities."""
        client = A2AClient(agent_url)
        card = await client.discover()
        await client.close()
        
        if card:
            self.agents[agent_url] = card
            self.last_discovery[agent_url] = datetime.utcnow()
            logger.info(f"Registered A2A agent: {card.get('name')} at {agent_url}")
        
        return card
    
    def find_by_skill(self, skill_id: str) -> List[str]:
        """Find agents that have a specific skill."""
        matches = []
        for url, card in self.agents.items():
            for skill in card.get("skills", []):
                if skill.get("id") == skill_id:
                    matches.append(url)
                    break
        return matches
    
    def find_by_capability(self, capability: str) -> List[str]:
        """Find agents with a specific capability."""
        return [
            url for url, card in self.agents.items()
            if card.get("capabilities", {}).get(capability)
        ]
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {"url": url, **card}
            for url, card in self.agents.items()
        ]


# =============================================================================
# Hydra Agent Card Factory
# =============================================================================

def create_hydra_agent_card(base_url: str = "http://192.168.1.244:8700") -> AgentCard:
    """Create the Agent Card for Hydra AI system."""
    return AgentCard(
        name="Hydra AI Steward",
        description="Autonomous AI system caretaker with multi-modal capabilities",
        url=base_url,
        skills=[
            AgentSkill(
                id="code-generation",
                name="Code Generation",
                description="Generate, review, and refactor code across multiple languages",
                examples=["Write a Python function to parse JSON", "Review this code for bugs"],
                tags=["code", "development", "python", "typescript"],
            ),
            AgentSkill(
                id="image-generation",
                name="Image Generation",
                description="Generate images using ComfyUI and Flux models",
                examples=["Generate a portrait of a fantasy character", "Create a landscape image"],
                tags=["image", "art", "creative"],
            ),
            AgentSkill(
                id="knowledge-retrieval",
                name="Knowledge Retrieval",
                description="Search and retrieve information from the Hydra knowledge base",
                examples=["What is the TabbyAPI configuration?", "Find information about GPU limits"],
                tags=["search", "knowledge", "rag"],
            ),
            AgentSkill(
                id="system-monitoring",
                name="System Monitoring",
                description="Monitor and report on cluster health, GPU status, and services",
                examples=["Check GPU utilization", "What services are running?"],
                tags=["monitoring", "infrastructure", "health"],
            ),
            AgentSkill(
                id="home-automation",
                name="Home Automation",
                description="Control and monitor smart home devices via Home Assistant",
                examples=["Turn on the living room lights", "What's the thermostat set to?"],
                tags=["home", "iot", "automation"],
            ),
        ],
        capabilities={
            "streaming": True,
            "pushNotifications": False,
            "stateSync": True,
            "multimodal": True,
        },
    )


# =============================================================================
# Global Instances
# =============================================================================

_registry: Optional[AgentRegistry] = None
_server: Optional[A2AServer] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_server() -> Optional[A2AServer]:
    return _server


def set_server(server: A2AServer):
    global _server
    _server = server


# =============================================================================
# FastAPI Router
# =============================================================================

def create_a2a_router(task_handler: Optional[Callable] = None):
    """Create FastAPI router for A2A protocol endpoints."""
    from fastapi import APIRouter, Request, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    
    router = APIRouter(tags=["a2a"])
    
    # Default task handler if none provided
    async def default_handler(message: Message, task: Task) -> Message:
        """Default handler that echoes the message."""
        text_content = ""
        for part in message.parts:
            if part.type == "text":
                text_content += part.content
        
        return Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[MessagePart("text", f"Received: {text_content}")],
            context_id=task.context_id,
            task_id=task.task_id,
        )
    
    handler = task_handler or default_handler
    
    # Create server with Hydra agent card
    agent_card = create_hydra_agent_card()
    server = A2AServer(agent_card, handler)
    set_server(server)
    
    @router.get("/.well-known/agent-card.json")
    async def get_agent_card():
        """Return the A2A Agent Card for discovery."""
        return JSONResponse(
            content=agent_card.to_dict(),
            headers={"A2A-Version": A2A_VERSION}
        )
    
    @router.post("/a2a/rpc")
    async def handle_rpc(request: Request):
        """Handle A2A JSON-RPC requests."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": PARSE_ERROR, "message": "Invalid JSON"}
                },
                status_code=400
            )
        
        result = await server.handle_rpc(body)
        return JSONResponse(
            content=result,
            headers={"A2A-Version": A2A_VERSION}
        )
    
    # Registry endpoints
    class RegisterRequest(BaseModel):
        url: str
    
    @router.post("/a2a/registry/register")
    async def register_agent(request: RegisterRequest):
        """Register a remote A2A agent."""
        registry = get_registry()
        card = await registry.register(request.url)
        
        if card:
            return {"status": "registered", "agent": card}
        raise HTTPException(status_code=400, detail="Failed to discover agent")
    
    @router.get("/a2a/registry/agents")
    async def list_agents():
        """List all registered A2A agents."""
        registry = get_registry()
        return {"agents": registry.list_all()}
    
    @router.get("/a2a/registry/find")
    async def find_agents(skill: Optional[str] = None, capability: Optional[str] = None):
        """Find agents by skill or capability."""
        registry = get_registry()
        
        if skill:
            urls = registry.find_by_skill(skill)
        elif capability:
            urls = registry.find_by_capability(capability)
        else:
            urls = list(registry.agents.keys())
        
        return {"agents": [registry.agents.get(url) for url in urls if url in registry.agents]}
    
    @router.get("/a2a/tasks")
    async def list_tasks(context_id: Optional[str] = None, state: Optional[str] = None):
        """List A2A tasks."""
        tasks = list(server.tasks.values())
        
        if context_id:
            tasks = [t for t in tasks if t.context_id == context_id]
        if state:
            tasks = [t for t in tasks if t.state.value == state]
        
        return {"tasks": [t.to_dict() for t in tasks]}
    
    @router.get("/a2a/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get a specific A2A task."""
        if task_id not in server.tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"task": server.tasks[task_id].to_dict()}
    
    return router
