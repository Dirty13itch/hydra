"""
Hydra Dashboard API - Unified data layer for Command Center UI

Provides endpoints for:
- Agents with thinking streams
- Projects with real-time status
- Infrastructure nodes with GPU metrics
- Services with health status
- Knowledge collections
- Loaded AI models
- WebSocket for real-time updates
- Persistent agent configurations (JSON file storage)
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

# Persistence directory
HYDRA_DATA_DIR = Path(os.environ.get("HYDRA_DATA_DIR", "/mnt/user/appdata/hydra-stack/data"))
DASHBOARD_DATA_DIR = HYDRA_DATA_DIR / "dashboard"
AGENTS_FILE = DASHBOARD_DATA_DIR / "agents.json"
PROJECTS_FILE = DASHBOARD_DATA_DIR / "projects.json"


# ============= Data Models =============

class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    THINKING = "thinking"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentType(str, Enum):
    RESEARCH = "research"
    CODING = "coding"
    CREATIVE = "creative"
    COORDINATOR = "coordinator"


@dataclass
class ThinkingStep:
    """Single step in agent's thinking stream"""
    step_id: str
    timestamp: str
    content: str
    step_type: str = "reasoning"  # reasoning, tool_call, observation, conclusion


@dataclass
class AgentConfig:
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_output_tokens: int = 8192
    system_instruction: str = ""


@dataclass
class Agent:
    id: str
    name: str
    agent_type: AgentType
    status: AgentStatus
    model: str
    task: str
    progress: int
    uptime: str
    tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config: AgentConfig = field(default_factory=AgentConfig)
    thinking_stream: List[ThinkingStep] = field(default_factory=list)
    last_activity: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "model": self.model,
            "task": self.task,
            "progress": self.progress,
            "uptime": self.uptime,
            "tools": self.tools,
            "dependencies": self.dependencies,
            "config": asdict(self.config),
            "thinkingStream": [asdict(s) for s in self.thinking_stream[-20:]],  # Last 20 steps
            "lastActivity": self.last_activity,
        }


@dataclass
class Project:
    id: str
    name: str
    status: str  # active, paused, complete, blocked
    agent_count: int
    agent_ids: List[str]
    progress: int
    description: str
    last_updated: str

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "agentCount": self.agent_count,
            "agentIds": self.agent_ids,
            "progress": self.progress,
            "description": self.description,
            "lastUpdated": self.last_updated,
        }


# ============= In-Memory State =============

class DashboardState:
    """Manages dashboard state and WebSocket connections with file-based persistence"""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.projects: Dict[str, Project] = {}
        self.websockets: List[WebSocket] = []
        self._lock = asyncio.Lock()

        # Ensure data directory exists
        DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load persisted state or initialize defaults
        if not self._load_agents():
            self._init_system_agents()
        if not self._load_projects():
            self._init_default_projects()

    def _load_agents(self) -> bool:
        """Load agents from persistent storage"""
        try:
            if AGENTS_FILE.exists():
                with open(AGENTS_FILE, 'r') as f:
                    data = json.load(f)

                for agent_data in data.get("agents", []):
                    agent = Agent(
                        id=agent_data["id"],
                        name=agent_data["name"],
                        agent_type=AgentType(agent_data["type"]),
                        status=AgentStatus(agent_data.get("status", "idle")),
                        model=agent_data["model"],
                        task=agent_data.get("task", "Awaiting assignment"),
                        progress=agent_data.get("progress", 0),
                        uptime=agent_data.get("uptime", "on-demand"),
                        tools=agent_data.get("tools", []),
                        dependencies=agent_data.get("dependencies", []),
                        config=AgentConfig(
                            temperature=agent_data.get("config", {}).get("temperature", 0.7),
                            top_p=agent_data.get("config", {}).get("top_p", 0.9),
                            top_k=agent_data.get("config", {}).get("top_k", 40),
                            max_output_tokens=agent_data.get("config", {}).get("max_output_tokens", 8192),
                            system_instruction=agent_data.get("config", {}).get("system_instruction", ""),
                        ),
                    )
                    self.agents[agent.id] = agent

                print(f"[Dashboard] Loaded {len(self.agents)} agents from {AGENTS_FILE}")
                return len(self.agents) > 0
        except Exception as e:
            print(f"[Dashboard] Failed to load agents: {e}")
        return False

    def _load_projects(self) -> bool:
        """Load projects from persistent storage"""
        try:
            if PROJECTS_FILE.exists():
                with open(PROJECTS_FILE, 'r') as f:
                    data = json.load(f)

                for proj_data in data.get("projects", []):
                    project = Project(
                        id=proj_data["id"],
                        name=proj_data["name"],
                        status=proj_data.get("status", "active"),
                        agent_count=proj_data.get("agentCount", 0),
                        agent_ids=proj_data.get("agentIds", []),
                        progress=proj_data.get("progress", 0),
                        description=proj_data.get("description", ""),
                        last_updated=proj_data.get("lastUpdated", datetime.now().strftime("%Y-%m-%d")),
                    )
                    self.projects[project.id] = project

                print(f"[Dashboard] Loaded {len(self.projects)} projects from {PROJECTS_FILE}")
                return len(self.projects) > 0
        except Exception as e:
            print(f"[Dashboard] Failed to load projects: {e}")
        return False

    def _save_agents(self):
        """Save agents to persistent storage"""
        try:
            data = {
                "agents": [a.to_dict() for a in self.agents.values()],
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
            with open(AGENTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[Dashboard] Saved {len(self.agents)} agents to {AGENTS_FILE}")
        except Exception as e:
            print(f"[Dashboard] Failed to save agents: {e}")

    def _save_projects(self):
        """Save projects to persistent storage"""
        try:
            data = {
                "projects": [p.to_dict() for p in self.projects.values()],
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[Dashboard] Saved {len(self.projects)} projects to {PROJECTS_FILE}")
        except Exception as e:
            print(f"[Dashboard] Failed to save projects: {e}")

    def _init_system_agents(self):
        """Initialize system agent definitions"""
        self.agents = {
            "sys-coordinator": Agent(
                id="sys-coordinator",
                name="System-Coordinator",
                agent_type=AgentType.COORDINATOR,
                status=AgentStatus.ACTIVE,
                model="claude-3-opus",
                task="Orchestrating cluster operations",
                progress=100,
                uptime="continuous",
                tools=["Docker API", "SSH", "Health Monitor", "Alert Router"],
                config=AgentConfig(
                    temperature=0.0,
                    system_instruction="You are the HYDRA system kernel. Manage all operations."
                ),
            ),
            "research-alpha": Agent(
                id="research-alpha",
                name="Research-Alpha",
                agent_type=AgentType.RESEARCH,
                status=AgentStatus.IDLE,
                model="qwen2.5-72b",
                task="Awaiting research task",
                progress=0,
                uptime="on-demand",
                tools=["Web Search", "ArXiv API", "Qdrant", "Firecrawl"],
                config=AgentConfig(
                    temperature=0.3,
                    system_instruction="Research analyst focusing on AI/ML papers."
                ),
            ),
            "code-prime": Agent(
                id="code-prime",
                name="Code-Prime",
                agent_type=AgentType.CODING,
                status=AgentStatus.IDLE,
                model="devstral-small",
                task="Awaiting coding task",
                progress=0,
                uptime="on-demand",
                tools=["FileSystem", "Git", "LSP", "Test Runner"],
                config=AgentConfig(
                    temperature=0.1,
                    system_instruction="10x engineer. Write clean, tested code."
                ),
            ),
            "creative-director": Agent(
                id="creative-director",
                name="Creative-Director",
                agent_type=AgentType.CREATIVE,
                status=AgentStatus.IDLE,
                model="euryale-70b",
                task="Awaiting creative task",
                progress=0,
                uptime="on-demand",
                tools=["ComfyUI", "Character Generator", "Style Transfer"],
                config=AgentConfig(
                    temperature=0.9,
                    system_instruction="Visionary art director for game assets."
                ),
            ),
        }

    def _init_default_projects(self):
        """Initialize default projects"""
        self.projects = {
            "hydra-core": Project(
                id="hydra-core",
                name="Hydra Core System",
                status="active",
                agent_count=1,
                agent_ids=["sys-coordinator"],
                progress=85,
                description="Core infrastructure and self-improvement capabilities.",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
            "empire-queens": Project(
                id="empire-queens",
                name="Empire of Broken Queens",
                status="paused",
                agent_count=1,
                agent_ids=["creative-director"],
                progress=23,
                description="Adult visual novel with 21 unique queens.",
                last_updated="2025-12-15",
            ),
            "rag-pipeline": Project(
                id="rag-pipeline",
                name="Knowledge Pipeline",
                status="active",
                agent_count=1,
                agent_ids=["research-alpha"],
                progress=78,
                description="RAG pipeline for research and documentation.",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        }

    async def broadcast(self, event_type: str, data: Any):
        """Broadcast event to all connected WebSocket clients"""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        disconnected = []
        for ws in self.websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.websockets.remove(ws)

    async def update_agent(self, agent_id: str, updates: Dict, persist: bool = True):
        """Update agent and broadcast change"""
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                for key, value in updates.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)
                agent.last_activity = datetime.utcnow().isoformat() + "Z"

                # Persist changes
                if persist:
                    self._save_agents()

                await self.broadcast("agent_update", agent.to_dict())
                return agent.to_dict()
        return None

    async def update_agent_config(self, agent_id: str, config_updates: Dict) -> Optional[Dict]:
        """Update agent configuration and persist"""
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]

                # Update config fields
                if "temperature" in config_updates:
                    agent.config.temperature = config_updates["temperature"]
                if "top_p" in config_updates:
                    agent.config.top_p = config_updates["top_p"]
                if "top_k" in config_updates:
                    agent.config.top_k = config_updates["top_k"]
                if "max_output_tokens" in config_updates:
                    agent.config.max_output_tokens = config_updates["max_output_tokens"]
                if "system_instruction" in config_updates:
                    agent.config.system_instruction = config_updates["system_instruction"]

                agent.last_activity = datetime.utcnow().isoformat() + "Z"

                # Persist changes
                self._save_agents()

                await self.broadcast("agent_config_update", {
                    "agentId": agent_id,
                    "config": asdict(agent.config),
                })
                return agent.to_dict()
        return None

    async def create_agent(self, agent_data: Dict) -> Dict:
        """Create a new agent and persist"""
        async with self._lock:
            agent_id = agent_data.get("id") or f"agent-{uuid.uuid4().hex[:8]}"

            agent = Agent(
                id=agent_id,
                name=agent_data.get("name", f"Agent-{agent_id[:8]}"),
                agent_type=AgentType(agent_data.get("type", "research")),
                status=AgentStatus(agent_data.get("status", "idle")),
                model=agent_data.get("model", "qwen2.5-72b"),
                task=agent_data.get("task", "Awaiting assignment"),
                progress=agent_data.get("progress", 0),
                uptime=agent_data.get("uptime", "on-demand"),
                tools=agent_data.get("tools", []),
                dependencies=agent_data.get("dependencies", []),
                config=AgentConfig(
                    temperature=agent_data.get("config", {}).get("temperature", 0.7),
                    top_p=agent_data.get("config", {}).get("top_p", 0.9),
                    top_k=agent_data.get("config", {}).get("top_k", 40),
                    max_output_tokens=agent_data.get("config", {}).get("max_output_tokens", 8192),
                    system_instruction=agent_data.get("config", {}).get("system_instruction", ""),
                ),
            )

            self.agents[agent_id] = agent
            self._save_agents()

            await self.broadcast("agent_created", agent.to_dict())
            return agent.to_dict()

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent and persist"""
        async with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self._save_agents()

                await self.broadcast("agent_deleted", {"agentId": agent_id})
                return True
        return False

    async def add_thinking_step(self, agent_id: str, content: str, step_type: str = "reasoning"):
        """Add thinking step to agent's stream"""
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                step = ThinkingStep(
                    step_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    content=content,
                    step_type=step_type,
                )
                agent.thinking_stream.append(step)

                # Keep only last 100 steps
                if len(agent.thinking_stream) > 100:
                    agent.thinking_stream = agent.thinking_stream[-100:]

                await self.broadcast("thinking_step", {
                    "agentId": agent_id,
                    "step": asdict(step),
                })
                return asdict(step)
        return None


# Global state instance
dashboard_state = DashboardState()


# ============= API Router =============

def create_dashboard_router() -> APIRouter:
    """Create the dashboard API router"""

    router = APIRouter(prefix="/dashboard", tags=["dashboard"])

    # ============= Agents =============

    @router.get("/agents")
    async def get_agents():
        """Get all agents with their current status"""
        return {
            "agents": [a.to_dict() for a in dashboard_state.agents.values()],
            "count": len(dashboard_state.agents),
        }

    @router.get("/agents/{agent_id}")
    async def get_agent(agent_id: str):
        """Get specific agent details"""
        if agent_id not in dashboard_state.agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        return dashboard_state.agents[agent_id].to_dict()

    @router.get("/agents/{agent_id}/thinking")
    async def get_agent_thinking(agent_id: str, limit: int = 20):
        """Get agent's thinking stream"""
        if agent_id not in dashboard_state.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent = dashboard_state.agents[agent_id]
        return {
            "agentId": agent_id,
            "agentName": agent.name,
            "steps": [asdict(s) for s in agent.thinking_stream[-limit:]],
        }

    class AgentUpdateRequest(BaseModel):
        status: Optional[str] = None
        task: Optional[str] = None
        progress: Optional[int] = None

    @router.patch("/agents/{agent_id}")
    async def update_agent(agent_id: str, request: AgentUpdateRequest):
        """Update agent status/task"""
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        if "status" in updates:
            updates["status"] = AgentStatus(updates["status"])

        result = await dashboard_state.update_agent(agent_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return result

    class ThinkingStepRequest(BaseModel):
        content: str
        step_type: str = "reasoning"

    @router.post("/agents/{agent_id}/thinking")
    async def add_thinking_step(agent_id: str, request: ThinkingStepRequest):
        """Add a thinking step to agent's stream"""
        result = await dashboard_state.add_thinking_step(
            agent_id, request.content, request.step_type
        )
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return result

    class AgentConfigRequest(BaseModel):
        temperature: Optional[float] = None
        top_p: Optional[float] = None
        top_k: Optional[int] = None
        max_output_tokens: Optional[int] = None
        system_instruction: Optional[str] = None

    @router.patch("/agents/{agent_id}/config")
    async def update_agent_config(agent_id: str, request: AgentConfigRequest):
        """Update agent configuration (persisted)"""
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        result = await dashboard_state.update_agent_config(agent_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return result

    class CreateAgentRequest(BaseModel):
        name: str
        type: str = "research"
        model: str = "qwen2.5-72b"
        task: str = "Awaiting assignment"
        tools: List[str] = []
        config: Optional[dict] = None

    @router.post("/agents")
    async def create_agent(request: CreateAgentRequest):
        """Create a new agent (persisted)"""
        agent_data = request.model_dump()
        result = await dashboard_state.create_agent(agent_data)
        return result

    @router.delete("/agents/{agent_id}")
    async def delete_agent(agent_id: str):
        """Delete an agent (persisted)"""
        success = await dashboard_state.delete_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"success": True, "agentId": agent_id}

    # ============= Projects =============

    @router.get("/projects")
    async def get_projects():
        """Get all projects"""
        return {
            "projects": [p.to_dict() for p in dashboard_state.projects.values()],
            "count": len(dashboard_state.projects),
        }

    @router.get("/projects/{project_id}")
    async def get_project(project_id: str):
        """Get specific project"""
        if project_id not in dashboard_state.projects:
            raise HTTPException(status_code=404, detail="Project not found")
        return dashboard_state.projects[project_id].to_dict()

    # ============= Infrastructure =============

    async def fetch_prometheus_gpu_metrics() -> Dict[str, List[Dict]]:
        """Fetch GPU metrics from Prometheus for all nodes.

        Handles two metric formats:
        - nvidia_gpu_* metrics from hydra-compute (custom nvidia-smi exporter)
        - DCGM_FI_* metrics from hydra-ai (DCGM exporter)
        """
        import httpx

        gpu_data = {"hydra-ai": [], "hydra-compute": []}
        prometheus_url = "http://192.168.1.244:9090/api/v1/query"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # === Fetch nvidia_gpu_* metrics (hydra-compute) ===
                nvidia_queries = {
                    "memory_used": "nvidia_gpu_memory_used_bytes",
                    "memory_total": "nvidia_gpu_memory_total_bytes",
                    "utilization": "nvidia_gpu_utilization_gpu",
                    "temperature": "nvidia_gpu_temperature_celsius",
                    "power": "nvidia_gpu_power_usage_milliwatts",
                }

                nvidia_results = {}
                for metric_name, query in nvidia_queries.items():
                    try:
                        resp = await client.get(prometheus_url, params={"query": query})
                        if resp.status_code == 200:
                            data = resp.json()
                            nvidia_results[metric_name] = data.get("data", {}).get("result", [])
                    except Exception:
                        nvidia_results[metric_name] = []

                # Process nvidia_gpu_* metrics
                nvidia_gpu_metrics = {}
                for metric_name, result_list in nvidia_results.items():
                    for item in result_list:
                        metric = item.get("metric", {})
                        gpu_id = metric.get("gpu", "0")
                        instance = metric.get("instance", "")
                        name = metric.get("name", "Unknown GPU").replace("_", " ")
                        value = item.get("value", [None, "0"])[1]

                        node = "hydra-compute" if "203" in instance else None
                        if not node:
                            continue

                        key = f"{node}_{gpu_id}"
                        if key not in nvidia_gpu_metrics:
                            nvidia_gpu_metrics[key] = {"node": node, "name": name, "gpu_id": gpu_id}
                        nvidia_gpu_metrics[key][metric_name] = value

                for key, metrics in nvidia_gpu_metrics.items():
                    gpu_data["hydra-compute"].append({
                        "name": metrics.get("name", "Unknown GPU"),
                        "util": int(float(metrics.get("utilization", 0))),
                        "vram": round(float(metrics.get("memory_used", 0)) / (1024**3), 1),
                        "totalVram": round(float(metrics.get("memory_total", 0)) / (1024**3), 0),
                        "temp": int(float(metrics.get("temperature", 0))),
                        "power": int(float(metrics.get("power", 0)) / 1000),
                    })

                # === Fetch DCGM_FI_* metrics (hydra-ai) ===
                dcgm_queries = {
                    "memory_used": "DCGM_FI_DEV_FB_USED",        # in MB
                    "memory_total": "DCGM_FI_DEV_FB_FREE",       # in MB (will add to used)
                    "utilization": "DCGM_FI_DEV_GPU_UTIL",       # percentage
                    "temperature": "DCGM_FI_DEV_GPU_TEMP",       # celsius
                    "power": "DCGM_FI_DEV_POWER_USAGE",          # watts
                }

                dcgm_results = {}
                for metric_name, query in dcgm_queries.items():
                    try:
                        resp = await client.get(prometheus_url, params={"query": query})
                        if resp.status_code == 200:
                            data = resp.json()
                            dcgm_results[metric_name] = data.get("data", {}).get("result", [])
                    except Exception:
                        dcgm_results[metric_name] = []

                # Process DCGM metrics
                dcgm_gpu_metrics = {}
                for metric_name, result_list in dcgm_results.items():
                    for item in result_list:
                        metric = item.get("metric", {})
                        gpu_id = metric.get("gpu", "0")
                        instance = metric.get("instance", "")
                        name = metric.get("modelName", "Unknown GPU").replace("_", " ")
                        value = item.get("value", [None, "0"])[1]

                        node = "hydra-ai" if "250" in instance else None
                        if not node:
                            continue

                        key = f"{node}_{gpu_id}"
                        if key not in dcgm_gpu_metrics:
                            dcgm_gpu_metrics[key] = {"node": node, "name": name, "gpu_id": gpu_id}
                        dcgm_gpu_metrics[key][metric_name] = value

                for key, metrics in dcgm_gpu_metrics.items():
                    mem_used_mb = float(metrics.get("memory_used", 0))
                    mem_free_mb = float(metrics.get("memory_total", 0))
                    mem_total_mb = mem_used_mb + mem_free_mb

                    gpu_data["hydra-ai"].append({
                        "name": metrics.get("name", "Unknown GPU"),
                        "util": int(float(metrics.get("utilization", 0))),
                        "vram": round(mem_used_mb / 1024, 1),        # MB to GB
                        "totalVram": round(mem_total_mb / 1024, 0),  # MB to GB
                        "temp": int(float(metrics.get("temperature", 0))),
                        "power": int(float(metrics.get("power", 0))),
                    })

        except Exception as e:
            print(f"[Dashboard] Prometheus GPU fetch failed: {e}")

        return gpu_data

    @router.get("/nodes")
    async def get_nodes():
        """Get cluster node status with GPU metrics from Prometheus"""
        nodes = []

        # Fetch real GPU data from Prometheus
        gpu_data = await fetch_prometheus_gpu_metrics()

        # hydra-ai node
        hydra_ai_gpus = gpu_data.get("hydra-ai", [])
        if not hydra_ai_gpus:
            # Fallback if no Prometheus data for hydra-ai
            hydra_ai_gpus = [
                {"name": "RTX 5090", "util": 0, "vram": 0, "totalVram": 32, "temp": 35, "power": 50},
                {"name": "RTX 4090", "util": 0, "vram": 0, "totalVram": 24, "temp": 32, "power": 40},
            ]

        nodes.append({
            "id": "hydra-ai",
            "name": "hydra-ai",
            "ip": "192.168.1.250",
            "cpu": 24,
            "ram": {"used": 48, "total": 128},
            "gpus": hydra_ai_gpus,
            "status": "online",
            "uptime": "14d+",
        })

        # hydra-compute node
        hydra_compute_gpus = gpu_data.get("hydra-compute", [])
        if not hydra_compute_gpus:
            # Fallback if no Prometheus data for hydra-compute
            hydra_compute_gpus = [
                {"name": "RTX 5070 Ti", "util": 0, "vram": 0, "totalVram": 16, "temp": 30, "power": 30},
                {"name": "RTX 5070 Ti", "util": 0, "vram": 0, "totalVram": 16, "temp": 30, "power": 30},
            ]

        nodes.append({
            "id": "hydra-compute",
            "name": "hydra-compute",
            "ip": "192.168.1.203",
            "cpu": 16,
            "ram": {"used": 16, "total": 64},
            "gpus": hydra_compute_gpus,
            "status": "online",
            "uptime": "5d+",
        })

        # hydra-storage (local, no GPUs)
        nodes.append({
            "id": "hydra-storage",
            "name": "hydra-storage",
            "ip": "192.168.1.244",
            "cpu": 56,
            "ram": {"used": 89, "total": 256},
            "gpus": [],
            "status": "online",
            "uptime": "45d+",
        })

        return {"nodes": nodes, "count": len(nodes)}

    @router.get("/services")
    async def get_services():
        """Get service status from cluster health API"""
        services = []

        try:
            import httpx
            # Use the cluster health endpoint for accurate service status
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("http://127.0.0.1:8700/health/cluster")
                if resp.status_code == 200:
                    data = resp.json()
                    for svc in data.get("services", []):
                        # Map health status to service format
                        status = "running" if svc.get("status") == "healthy" else "stopped"

                        services.append({
                            "id": svc.get("service", "").lower().replace(" ", "-"),
                            "name": svc.get("service", "Unknown"),
                            "node": svc.get("node", "hydra-storage"),
                            "port": 0,  # Port not included in health check
                            "status": status,
                            "uptime": f"{int(svc.get('latency_ms', 0))}ms",
                            "category": svc.get("category", "unknown"),
                            "latency_ms": svc.get("latency_ms", 0),
                        })
        except Exception as e:
            # Fallback to static list if health endpoint fails
            services = [
                {"id": "tabbyapi", "name": "TabbyAPI", "node": "hydra-ai", "port": 5000, "status": "running", "uptime": "14d+"},
                {"id": "ollama", "name": "Ollama", "node": "hydra-compute", "port": 11434, "status": "running", "uptime": "5d+"},
                {"id": "litellm", "name": "LiteLLM", "node": "hydra-storage", "port": 4000, "status": "running", "uptime": "14d+"},
                {"id": "qdrant", "name": "Qdrant", "node": "hydra-storage", "port": 6333, "status": "running", "uptime": "14d+"},
                {"id": "prometheus", "name": "Prometheus", "node": "hydra-storage", "port": 9090, "status": "running", "uptime": "14d+"},
                {"id": "grafana", "name": "Grafana", "node": "hydra-storage", "port": 3003, "status": "running", "uptime": "14d+"},
                {"id": "n8n", "name": "n8n", "node": "hydra-storage", "port": 5678, "status": "running", "uptime": "14d+"},
            ]

        return {"services": services, "count": len(services)}

    # ============= Models =============

    @router.get("/models")
    async def get_models():
        """Get loaded and available AI models"""
        models = []

        # Check TabbyAPI for loaded model
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://192.168.1.250:5000/v1/model")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("id"):
                        models.append({
                            "id": "tabby-primary",
                            "name": data.get("id", "Unknown"),
                            "paramSize": "70B",
                            "quantization": "ExL2",
                            "vramUsage": 45,
                            "contextLength": "32K",
                            "status": "loaded",
                            "provider": "local",
                        })
        except Exception:
            pass

        # Check Ollama for models
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://192.168.1.203:11434/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for model in data.get("models", [])[:5]:
                        name = model.get("name", "unknown")
                        size_gb = model.get("size", 0) / (1024**3)
                        models.append({
                            "id": f"ollama-{name}",
                            "name": name,
                            "paramSize": f"{size_gb:.0f}GB" if size_gb > 1 else f"{model.get('size', 0) / (1024**2):.0f}MB",
                            "quantization": "GGUF",
                            "vramUsage": 0,
                            "contextLength": "8K",
                            "status": "loaded",
                            "provider": "local",
                        })
        except Exception:
            pass

        # Add API models
        models.extend([
            {
                "id": "claude-opus",
                "name": "claude-3-opus",
                "paramSize": "Unknown",
                "quantization": "N/A",
                "vramUsage": 0,
                "contextLength": "200K",
                "status": "loaded",
                "provider": "api",
            },
            {
                "id": "claude-sonnet",
                "name": "claude-3.5-sonnet",
                "paramSize": "Unknown",
                "quantization": "N/A",
                "vramUsage": 0,
                "contextLength": "200K",
                "status": "loaded",
                "provider": "api",
            },
        ])

        return {"models": models, "count": len(models)}

    # ============= Knowledge Collections =============

    @router.get("/collections")
    async def get_collections():
        """Get knowledge base collections from Qdrant"""
        collections = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://192.168.1.244:6333/collections")
                if resp.status_code == 200:
                    data = resp.json()
                    for coll in data.get("result", {}).get("collections", []):
                        name = coll.get("name", "unknown")

                        # Get collection info
                        info_resp = await client.get(f"http://192.168.1.244:6333/collections/{name}")
                        if info_resp.status_code == 200:
                            info = info_resp.json().get("result", {})
                            point_count = info.get("points_count", 0)

                            collections.append({
                                "id": name,
                                "name": name.replace("_", " ").title(),
                                "docCount": point_count // 10,  # Estimate docs from chunks
                                "chunkCount": point_count,
                                "lastIngested": "recently",
                                "topics": [],
                                "status": "ready",
                            })
        except Exception:
            # Fallback
            collections = [
                {"id": "hydra_knowledge", "name": "Hydra Knowledge", "docCount": 50, "chunkCount": 2000, "lastIngested": "2h ago", "topics": ["infrastructure", "AI"], "status": "ready"},
            ]

        return {"collections": collections, "count": len(collections)}

    # ============= System Stats =============

    @router.get("/stats")
    async def get_system_stats():
        """Get aggregated system statistics with real GPU metrics"""
        agents = list(dashboard_state.agents.values())
        active_agents = sum(1 for a in agents if a.status in [AgentStatus.ACTIVE, AgentStatus.THINKING])

        # Fetch real GPU data from Prometheus
        gpu_data = await fetch_prometheus_gpu_metrics()

        # Calculate total power and VRAM from all GPUs
        total_power = 150  # Base system power estimate
        vram_used = 0.0
        vram_total = 0.0

        for node_gpus in gpu_data.values():
            for gpu in node_gpus:
                total_power += gpu.get("power", 0)
                vram_used += gpu.get("vram", 0)
                vram_total += gpu.get("totalVram", 0)

        # Fallback values if no Prometheus data
        if vram_total == 0:
            vram_total = 88  # 32 + 24 + 16 + 16
            vram_used = 0
            total_power = 400

        return {
            "activeAgents": active_agents,
            "totalAgents": len(agents),
            "systemPower": int(total_power),
            "vramUsed": round(vram_used, 1),
            "vramTotal": round(vram_total, 0),
            "uptime": "14d 3h",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # ============= WebSocket =============

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket for real-time updates"""
        await websocket.accept()
        dashboard_state.websockets.append(websocket)

        try:
            # Send initial state
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "message": "Connected to Hydra Command Center",
                    "agents": len(dashboard_state.agents),
                    "projects": len(dashboard_state.projects),
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    message = json.loads(data)

                    # Handle client commands
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat() + "Z"})
                    elif message.get("type") == "subscribe":
                        # Client subscribing to specific agent
                        pass

                except asyncio.TimeoutError:
                    # Send keepalive
                    await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat() + "Z"})

        except WebSocketDisconnect:
            pass
        finally:
            if websocket in dashboard_state.websockets:
                dashboard_state.websockets.remove(websocket)

    return router


# Export for main API
def get_dashboard_state() -> DashboardState:
    """Get the global dashboard state"""
    return dashboard_state
