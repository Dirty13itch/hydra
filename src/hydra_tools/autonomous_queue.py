"""
Autonomous Work Queue - 24/7 Resource-Aware Task Scheduling System.

This module provides an intelligent work queue that:
1. Monitors GPU/CPU resources across all cluster nodes in real-time
2. Automatically schedules work when resources are available
3. Routes tasks to appropriate nodes (inference vs image generation)
4. Runs continuously 24/7 with configurable thresholds
5. Sends notifications on completion via Discord

Key Features:
- Prometheus-based resource monitoring across hydra-ai, hydra-compute, hydra-storage
- Resource-aware scheduling: only runs tasks when GPU utilization is low
- Node affinity: routes inference to hydra-ai, images to hydra-compute
- Priority queue with dynamic scheduling
- Automatic retry with exponential backoff

Usage:
    GET /autonomous/resources - View cluster resource status
    GET /autonomous/scheduler/status - Check scheduler state
    POST /autonomous/scheduler/start - Start 24/7 scheduler
    POST /autonomous/scheduler/stop - Stop scheduler
    POST /autonomous/queue - Add work item
    GET /autonomous/queue - List pending items
"""

import os
import json
import asyncio
import sqlite3
import httpx
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict, field
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autonomous_queue")

router = APIRouter(prefix="/autonomous", tags=["autonomous"])

# Database path
DB_PATH = Path(os.environ.get("HYDRA_DATA_DIR", "/data")) / "autonomous_queue.db"

# =============================================================================
# CLUSTER CONFIGURATION
# =============================================================================

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://192.168.1.244:9090")

# Node definitions with capabilities
CLUSTER_NODES = {
    "hydra-ai": {
        "ip": "192.168.1.250",
        "prometheus_instance": "192.168.1.250:9835",
        "metrics_type": "dcgm",  # Uses DCGM_FI_* metrics
        "capabilities": ["inference", "llm", "embedding"],
        "gpus": [
            {"index": 0, "name": "RTX 5090", "vram_gb": 32},
            {"index": 1, "name": "RTX 4090", "vram_gb": 24},
        ],
    },
    "hydra-compute": {
        "ip": "192.168.1.203",
        "prometheus_instance": "192.168.1.203:9835",
        "metrics_type": "nvidia",  # Uses nvidia_gpu_* metrics
        "capabilities": ["image_generation", "comfyui", "ollama"],
        "gpus": [
            {"index": 0, "name": "RTX 5070 Ti", "vram_gb": 16},
            {"index": 1, "name": "RTX 5070 Ti", "vram_gb": 16},
        ],
    },
    "hydra-storage": {
        "ip": "192.168.1.244",
        "prometheus_instance": "192.168.1.244:9100",
        "metrics_type": "none",  # No GPU metrics
        "capabilities": ["storage", "api", "services"],
        "gpus": [],
    },
}

# Resource thresholds for scheduling
RESOURCE_THRESHOLDS = {
    "gpu_util_max": 50,  # Only schedule if GPU util < 50%
    "vram_free_min_gb": 4,  # Only schedule if at least 4GB VRAM free
    "check_interval_seconds": 30,  # How often to check for work
    "max_concurrent_tasks": 3,  # Max tasks running at once
}

# =============================================================================
# CLUSTER RESOURCE MONITOR
# =============================================================================

@dataclass
class GPUStatus:
    node: str
    gpu_index: int
    gpu_name: str
    utilization_percent: float
    vram_used_gb: float
    vram_total_gb: float
    vram_free_gb: float
    temperature_f: float
    power_watts: float
    available_for_work: bool

@dataclass
class NodeStatus:
    name: str
    ip: str
    online: bool
    capabilities: List[str]
    gpus: List[GPUStatus]
    total_vram_gb: float
    free_vram_gb: float
    avg_gpu_util: float

@dataclass
class ClusterResources:
    timestamp: str
    nodes: List[NodeStatus]
    total_gpus: int
    available_gpus: int
    total_vram_gb: float
    free_vram_gb: float
    cluster_gpu_util: float
    can_accept_inference: bool
    can_accept_image_gen: bool


class ClusterResourceMonitor:
    """Monitors GPU/CPU resources across all cluster nodes via Prometheus."""

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.prometheus_url = prometheus_url
        self._cache: Optional[ClusterResources] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=10)

    async def query_prometheus(self, query: str) -> List[Dict[str, Any]]:
        """Execute a Prometheus query and return results."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("result", [])
        except Exception as e:
            logger.warning(f"Prometheus query failed: {query} - {e}")
        return []

    async def get_gpu_metrics(self, node_name: str, node_config: Dict) -> List[GPUStatus]:
        """Get GPU metrics for a specific node."""
        gpus = []
        instance = node_config["prometheus_instance"]
        metrics_type = node_config["metrics_type"]

        if metrics_type == "none":
            return gpus

        for gpu_info in node_config["gpus"]:
            gpu_idx = gpu_info["index"]

            if metrics_type == "dcgm":
                # Query DCGM metrics for hydra-ai
                util_query = f'DCGM_FI_DEV_GPU_UTIL{{instance="{instance}",gpu="{gpu_idx}"}}'
                vram_used_query = f'DCGM_FI_DEV_FB_USED{{instance="{instance}",gpu="{gpu_idx}"}}'
                vram_free_query = f'DCGM_FI_DEV_FB_FREE{{instance="{instance}",gpu="{gpu_idx}"}}'
                temp_query = f'DCGM_FI_DEV_GPU_TEMP{{instance="{instance}",gpu="{gpu_idx}"}}'
                power_query = f'DCGM_FI_DEV_POWER_USAGE{{instance="{instance}",gpu="{gpu_idx}"}}'

                util_result = await self.query_prometheus(util_query)
                vram_used_result = await self.query_prometheus(vram_used_query)
                vram_free_result = await self.query_prometheus(vram_free_query)
                temp_result = await self.query_prometheus(temp_query)
                power_result = await self.query_prometheus(power_query)

                util = float(util_result[0]["value"][1]) if util_result else 0
                vram_used_mb = float(vram_used_result[0]["value"][1]) if vram_used_result else 0
                vram_free_mb = float(vram_free_result[0]["value"][1]) if vram_free_result else 0
                temp_c = float(temp_result[0]["value"][1]) if temp_result else 0
                power = float(power_result[0]["value"][1]) if power_result else 0

                vram_used_gb = vram_used_mb / 1024
                vram_free_gb = vram_free_mb / 1024
                vram_total_gb = vram_used_gb + vram_free_gb

            else:  # nvidia metrics
                util_query = f'nvidia_gpu_utilization_percent{{instance="{instance}",gpu="{gpu_idx}"}}'
                vram_used_query = f'nvidia_gpu_memory_used_bytes{{instance="{instance}",gpu="{gpu_idx}"}}'
                vram_total_query = f'nvidia_gpu_memory_total_bytes{{instance="{instance}",gpu="{gpu_idx}"}}'
                temp_query = f'nvidia_gpu_temperature_celsius{{instance="{instance}",gpu="{gpu_idx}"}}'
                power_query = f'nvidia_gpu_power_draw_watts{{instance="{instance}",gpu="{gpu_idx}"}}'

                util_result = await self.query_prometheus(util_query)
                vram_used_result = await self.query_prometheus(vram_used_query)
                vram_total_result = await self.query_prometheus(vram_total_query)
                temp_result = await self.query_prometheus(temp_query)
                power_result = await self.query_prometheus(power_query)

                util = float(util_result[0]["value"][1]) if util_result else 0
                vram_used_bytes = float(vram_used_result[0]["value"][1]) if vram_used_result else 0
                vram_total_bytes = float(vram_total_result[0]["value"][1]) if vram_total_result else 0
                temp_c = float(temp_result[0]["value"][1]) if temp_result else 0
                power = float(power_result[0]["value"][1]) if power_result else 0

                vram_used_gb = vram_used_bytes / (1024 ** 3)
                vram_total_gb = vram_total_bytes / (1024 ** 3)
                vram_free_gb = vram_total_gb - vram_used_gb

            # Convert temp to Fahrenheit
            temp_f = (temp_c * 9 / 5) + 32

            # Determine if GPU is available for work
            available = (
                util < RESOURCE_THRESHOLDS["gpu_util_max"] and
                vram_free_gb >= RESOURCE_THRESHOLDS["vram_free_min_gb"]
            )

            gpus.append(GPUStatus(
                node=node_name,
                gpu_index=gpu_idx,
                gpu_name=gpu_info["name"],
                utilization_percent=util,
                vram_used_gb=round(vram_used_gb, 2),
                vram_total_gb=round(vram_total_gb or gpu_info["vram_gb"], 2),
                vram_free_gb=round(vram_free_gb, 2),
                temperature_f=round(temp_f, 1),
                power_watts=round(power, 1),
                available_for_work=available
            ))

        return gpus

    async def get_cluster_resources(self, force_refresh: bool = False) -> ClusterResources:
        """Get current resource status across all cluster nodes."""
        now = datetime.now(timezone.utc)

        # Return cached if fresh
        if (not force_refresh and self._cache and self._cache_time and
            now - self._cache_time < self._cache_ttl):
            return self._cache

        nodes = []
        total_gpus = 0
        available_gpus = 0
        total_vram = 0.0
        free_vram = 0.0

        for node_name, node_config in CLUSTER_NODES.items():
            gpus = await self.get_gpu_metrics(node_name, node_config)

            node_total_vram = sum(g.vram_total_gb for g in gpus)
            node_free_vram = sum(g.vram_free_gb for g in gpus)
            node_avg_util = sum(g.utilization_percent for g in gpus) / len(gpus) if gpus else 0

            nodes.append(NodeStatus(
                name=node_name,
                ip=node_config["ip"],
                online=len(gpus) > 0 or node_config["metrics_type"] == "none",
                capabilities=node_config["capabilities"],
                gpus=gpus,
                total_vram_gb=round(node_total_vram, 2),
                free_vram_gb=round(node_free_vram, 2),
                avg_gpu_util=round(node_avg_util, 1)
            ))

            total_gpus += len(gpus)
            available_gpus += sum(1 for g in gpus if g.available_for_work)
            total_vram += node_total_vram
            free_vram += node_free_vram

        # Determine capability availability
        can_accept_inference = any(
            n.name == "hydra-ai" and any(g.available_for_work for g in n.gpus)
            for n in nodes
        )
        can_accept_image_gen = any(
            n.name == "hydra-compute" and any(g.available_for_work for g in n.gpus)
            for n in nodes
        )

        cluster_util = sum(g.utilization_percent for n in nodes for g in n.gpus)
        cluster_util = cluster_util / total_gpus if total_gpus > 0 else 0

        self._cache = ClusterResources(
            timestamp=now.isoformat(),
            nodes=nodes,
            total_gpus=total_gpus,
            available_gpus=available_gpus,
            total_vram_gb=round(total_vram, 2),
            free_vram_gb=round(free_vram, 2),
            cluster_gpu_util=round(cluster_util, 1),
            can_accept_inference=can_accept_inference,
            can_accept_image_gen=can_accept_image_gen
        )
        self._cache_time = now

        return self._cache


# Global resource monitor instance
resource_monitor = ClusterResourceMonitor()


# =============================================================================
# 24/7 SCHEDULER
# =============================================================================

class AutonomousScheduler:
    """
    24/7 resource-aware scheduler that continuously processes work when resources allow.

    The scheduler:
    1. Monitors cluster resources every 30 seconds
    2. When resources are available, picks the highest priority pending task
    3. Routes tasks to appropriate nodes based on type
    4. Respects concurrent task limits
    5. Handles failures with exponential backoff
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_tasks: Dict[int, asyncio.Task] = {}
        self._last_check: Optional[datetime] = None
        self._tasks_processed: int = 0
        self._tasks_failed: int = 0
        self._started_at: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "current_tasks": len(self._current_tasks),
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
            "check_interval_seconds": RESOURCE_THRESHOLDS["check_interval_seconds"],
            "max_concurrent": RESOURCE_THRESHOLDS["max_concurrent_tasks"],
        }

    def _get_task_requirements(self, work_type: str) -> Dict[str, Any]:
        """Get resource requirements for a work type."""
        requirements = {
            "chapter_generation": {
                "requires_gpu": True,
                "node_affinity": ["hydra-compute"],  # Uses Ollama + ComfyUI on hydra-compute
                "capability_needed": ["image_generation", "ollama"],
                "min_vram_gb": 8,
            },
            "research": {
                "requires_gpu": True,
                "node_affinity": ["hydra-compute"],  # CrewAI uses Ollama on hydra-compute
                "capability_needed": ["ollama"],
                "min_vram_gb": 4,
            },
            "asset_generation": {
                "requires_gpu": True,
                "node_affinity": ["hydra-compute"],  # ComfyUI on hydra-compute
                "capability_needed": ["image_generation"],
                "min_vram_gb": 8,
            },
            "quality_scoring": {
                "requires_gpu": True,
                "node_affinity": ["hydra-compute"],  # CLIP scoring on hydra-compute
                "capability_needed": ["image_generation"],
                "min_vram_gb": 4,
            },
            "inference": {
                "requires_gpu": True,
                "node_affinity": ["hydra-ai"],  # Large LLM inference (TabbyAPI)
                "capability_needed": ["inference", "llm"],
                "min_vram_gb": 8,
            },
            "maintenance": {
                "requires_gpu": False,
                "node_affinity": ["hydra-storage"],
                "capability_needed": [],
                "min_vram_gb": 0,
            },
            "custom": {
                "requires_gpu": False,
                "node_affinity": [],
                "capability_needed": [],
                "min_vram_gb": 0,
            },
        }
        return requirements.get(work_type, requirements["custom"])

    async def _can_run_task(self, work_type: str, resources: ClusterResources) -> bool:
        """Check if a task can run given current resources."""
        reqs = self._get_task_requirements(work_type)

        if not reqs["requires_gpu"]:
            return True  # Non-GPU tasks can always run

        # Check if required nodes have available GPUs
        for node in resources.nodes:
            if node.name in reqs["node_affinity"] or not reqs["node_affinity"]:
                if any(g.available_for_work and g.vram_free_gb >= reqs["min_vram_gb"] for g in node.gpus):
                    return True

        return False

    async def _pick_next_task(self) -> Optional[Dict[str, Any]]:
        """Pick the next task to run based on priority and resources."""
        resources = await resource_monitor.get_cluster_resources(force_refresh=True)

        conn = get_db()
        now = datetime.now(timezone.utc).isoformat()

        # Get pending tasks ordered by priority
        rows = conn.execute(
            """
            SELECT * FROM work_queue
            WHERE status = 'pending'
            AND (scheduled_after IS NULL OR scheduled_after <= ?)
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at ASC
            LIMIT 20
            """,
            (now,)
        ).fetchall()
        conn.close()

        # Find first task that can run with current resources
        for row in rows:
            work_type = row["work_type"]
            if await self._can_run_task(work_type, resources):
                return dict(row)

        return None

    async def _run_scheduler_loop(self):
        """Main scheduler loop - runs continuously."""
        logger.info("[Scheduler] Starting 24/7 autonomous scheduler")
        self._started_at = datetime.now(timezone.utc)

        while self._running:
            try:
                self._last_check = datetime.now(timezone.utc)

                # Clean up completed tasks
                completed = [tid for tid, task in self._current_tasks.items() if task.done()]
                for tid in completed:
                    del self._current_tasks[tid]

                # Check if we can accept more tasks
                if len(self._current_tasks) >= RESOURCE_THRESHOLDS["max_concurrent_tasks"]:
                    logger.debug(f"[Scheduler] At max concurrent tasks ({len(self._current_tasks)})")
                    await asyncio.sleep(RESOURCE_THRESHOLDS["check_interval_seconds"])
                    continue

                # Try to pick and run a task
                task_data = await self._pick_next_task()
                if task_data:
                    task_id = task_data["id"]
                    logger.info(f"[Scheduler] Starting task {task_id}: {task_data['title']}")

                    # Create async task to process
                    async_task = asyncio.create_task(self._process_task_safely(task_id))
                    self._current_tasks[task_id] = async_task
                else:
                    logger.debug("[Scheduler] No tasks ready to run")

                # Wait before next check
                await asyncio.sleep(RESOURCE_THRESHOLDS["check_interval_seconds"])

            except Exception as e:
                logger.error(f"[Scheduler] Error in scheduler loop: {e}")
                await asyncio.sleep(10)  # Brief pause on error

        logger.info("[Scheduler] Scheduler stopped")

    async def _process_task_safely(self, task_id: int):
        """Process a task with error handling."""
        try:
            await process_work_item(task_id)
            self._tasks_processed += 1
            logger.info(f"[Scheduler] Task {task_id} completed successfully")
        except Exception as e:
            self._tasks_failed += 1
            logger.error(f"[Scheduler] Task {task_id} failed: {e}")

    def start(self) -> bool:
        """Start the 24/7 scheduler."""
        if self._running:
            return False

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler_loop())
        logger.info("[Scheduler] Scheduler started")
        return True

    def stop(self) -> bool:
        """Stop the scheduler."""
        if not self._running:
            return False

        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

        logger.info("[Scheduler] Scheduler stop requested")
        return True


# Global scheduler instance
scheduler = AutonomousScheduler()


class WorkType(str, Enum):
    CHAPTER_GENERATION = "chapter_generation"
    RESEARCH = "research"
    ASSET_GENERATION = "asset_generation"
    QUALITY_SCORING = "quality_scoring"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"

class WorkStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Pydantic models
class WorkItemCreate(BaseModel):
    work_type: WorkType
    title: str = Field(..., description="Human-readable title")
    description: Optional[str] = None
    priority: WorkPriority = WorkPriority.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict, description="Work-specific data")
    scheduled_after: Optional[str] = Field(None, description="ISO timestamp - don't process before this time")
    notify_discord: bool = True
    notify_email: bool = False

class WorkItemResponse(BaseModel):
    id: int
    work_type: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    payload: Dict[str, Any]
    created_at: str
    scheduled_after: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    duration_ms: Optional[float]

class QueueStats(BaseModel):
    pending: int
    in_progress: int
    completed_today: int
    failed_today: int
    total_items: int
    avg_duration_ms: Optional[float]

# Database setup
def init_db():
    """Initialize the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS work_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'pending',
            payload TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            scheduled_after TEXT,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            duration_ms REAL,
            notify_discord INTEGER DEFAULT 1,
            notify_email INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON work_queue(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON work_queue(priority)")
    conn.commit()
    conn.close()

init_db()

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# Discord notification helper
async def send_discord_notification(title: str, message: str, color: int = 0x00ff00):
    """Send Discord webhook notification."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[Autonomous] Discord webhook not configured")
        return False

    embed = {
        "title": title,
        "description": message,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Hydra Autonomous System"}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json={"embeds": [embed]})
            return response.status_code == 204
    except Exception as e:
        print(f"[Autonomous] Discord notification failed: {e}")
        return False

# Work processors
async def process_chapter_generation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process chapter generation work item."""
    chapter_number = payload.get("chapter_number", 1)
    featured_characters = payload.get("featured_characters", [])
    themes = payload.get("themes", [])
    stages = payload.get("stages", ["create_structure", "generate_tts", "package"])

    api_key = os.environ.get("HYDRA_API_KEY", "hydra-dev-key")

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            "http://localhost:8700/characters/automate-chapter",
            headers={"X-API-Key": api_key},
            json={
                "chapter_number": chapter_number,
                "featured_characters": featured_characters,
                "themes": themes,
                "stages": stages
            }
        )

        if response.status_code != 200:
            raise Exception(f"Chapter automation failed: {response.text}")

        return response.json()

async def process_research(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process research work item using CrewAI."""
    topic = payload.get("topic", "general")
    depth = payload.get("depth", "standard")

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://192.168.1.244:8500/run/research",
            json={"topic": topic, "depth": depth}
        )

        if response.status_code != 200:
            raise Exception(f"Research crew failed: {response.text}")

        return response.json()

async def process_asset_generation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process asset generation work item."""
    asset_type = payload.get("asset_type", "portrait")
    character_ids = payload.get("character_ids", [])

    api_key = os.environ.get("HYDRA_API_KEY", "hydra-dev-key")

    if asset_type == "portrait":
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "http://localhost:8700/characters/generate-missing",
                headers={"X-API-Key": api_key}
            )
            return response.json()

    return {"status": "unknown_asset_type", "type": asset_type}

async def process_quality_scoring(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process quality scoring work item."""
    chapter_number = payload.get("chapter_number")

    api_key = os.environ.get("HYDRA_API_KEY", "hydra-dev-key")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8700/characters/batch-quality-score",
            headers={"X-API-Key": api_key},
            json={"chapter_number": chapter_number}
        )
        return response.json()

async def process_work_item(item_id: int) -> Dict[str, Any]:
    """Process a single work item."""
    conn = get_db()

    try:
        # Get item
        row = conn.execute("SELECT * FROM work_queue WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise Exception(f"Work item {item_id} not found")

        work_type = row["work_type"]
        payload = json.loads(row["payload"])

        # Mark as in progress
        started_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE work_queue SET status = ?, started_at = ? WHERE id = ?",
            (WorkStatus.IN_PROGRESS.value, started_at, item_id)
        )
        conn.commit()

        # Process based on type
        start_time = datetime.now(timezone.utc)

        if work_type == WorkType.CHAPTER_GENERATION.value:
            result = await process_chapter_generation(payload)
        elif work_type == WorkType.RESEARCH.value:
            result = await process_research(payload)
        elif work_type == WorkType.ASSET_GENERATION.value:
            result = await process_asset_generation(payload)
        elif work_type == WorkType.QUALITY_SCORING.value:
            result = await process_quality_scoring(payload)
        else:
            result = {"status": "no_processor", "work_type": work_type}

        # Calculate duration
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        completed_at = datetime.now(timezone.utc).isoformat()

        # Mark as completed
        conn.execute(
            "UPDATE work_queue SET status = ?, completed_at = ?, result = ?, duration_ms = ? WHERE id = ?",
            (WorkStatus.COMPLETED.value, completed_at, json.dumps(result), duration_ms, item_id)
        )
        conn.commit()

        # Send notification
        if row["notify_discord"]:
            await send_discord_notification(
                f"✅ Work Complete: {row['title']}",
                f"Type: {work_type}\nDuration: {duration_ms/1000:.1f}s\nStatus: Success",
                color=0x00ff00
            )

        return {"status": "completed", "result": result, "duration_ms": duration_ms}

    except Exception as e:
        # Mark as failed
        error_msg = str(e)
        conn.execute(
            "UPDATE work_queue SET status = ?, error = ?, completed_at = ? WHERE id = ?",
            (WorkStatus.FAILED.value, error_msg, datetime.now(timezone.utc).isoformat(), item_id)
        )
        conn.commit()

        # Send failure notification
        row = conn.execute("SELECT * FROM work_queue WHERE id = ?", (item_id,)).fetchone()
        if row and row["notify_discord"]:
            await send_discord_notification(
                f"❌ Work Failed: {row['title']}",
                f"Error: {error_msg[:500]}",
                color=0xff0000
            )

        raise
    finally:
        conn.close()

# API Endpoints
@router.post("/queue", response_model=WorkItemResponse)
async def add_to_queue(item: WorkItemCreate):
    """Add a work item to the autonomous queue."""
    conn = get_db()

    created_at = datetime.now(timezone.utc).isoformat()

    cursor = conn.execute(
        """
        INSERT INTO work_queue
        (work_type, title, description, priority, payload, created_at, scheduled_after, notify_discord, notify_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.work_type.value,
            item.title,
            item.description,
            item.priority.value,
            json.dumps(item.payload),
            created_at,
            item.scheduled_after,
            1 if item.notify_discord else 0,
            1 if item.notify_email else 0
        )
    )
    conn.commit()

    item_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM work_queue WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    return WorkItemResponse(
        id=row["id"],
        work_type=row["work_type"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        payload=json.loads(row["payload"]),
        created_at=row["created_at"],
        scheduled_after=row["scheduled_after"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        result=json.loads(row["result"]) if row["result"] else None,
        error=row["error"],
        duration_ms=row["duration_ms"]
    )

@router.get("/queue", response_model=List[WorkItemResponse])
async def list_queue(status: Optional[str] = None, limit: int = 50):
    """List items in the work queue."""
    conn = get_db()

    if status:
        rows = conn.execute(
            "SELECT * FROM work_queue WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM work_queue ORDER BY status ASC, priority DESC, created_at ASC LIMIT ?",
            (limit,)
        ).fetchall()

    conn.close()

    return [
        WorkItemResponse(
            id=row["id"],
            work_type=row["work_type"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            status=row["status"],
            payload=json.loads(row["payload"]),
            created_at=row["created_at"],
            scheduled_after=row["scheduled_after"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            duration_ms=row["duration_ms"]
        )
        for row in rows
    ]

@router.get("/queue/stats", response_model=QueueStats)
async def get_queue_stats():
    """Get queue statistics."""
    conn = get_db()

    today = datetime.now(timezone.utc).date().isoformat()

    pending = conn.execute("SELECT COUNT(*) FROM work_queue WHERE status = 'pending'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM work_queue WHERE status = 'in_progress'").fetchone()[0]
    completed_today = conn.execute(
        "SELECT COUNT(*) FROM work_queue WHERE status = 'completed' AND completed_at LIKE ?",
        (f"{today}%",)
    ).fetchone()[0]
    failed_today = conn.execute(
        "SELECT COUNT(*) FROM work_queue WHERE status = 'failed' AND completed_at LIKE ?",
        (f"{today}%",)
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM work_queue").fetchone()[0]
    avg_duration = conn.execute(
        "SELECT AVG(duration_ms) FROM work_queue WHERE status = 'completed' AND duration_ms IS NOT NULL"
    ).fetchone()[0]

    conn.close()

    return QueueStats(
        pending=pending,
        in_progress=in_progress,
        completed_today=completed_today,
        failed_today=failed_today,
        total_items=total,
        avg_duration_ms=avg_duration
    )

@router.post("/process")
async def process_queue(background_tasks: BackgroundTasks, limit: int = 10):
    """Process pending items in the queue (runs in background)."""
    conn = get_db()

    now = datetime.now(timezone.utc).isoformat()

    # Get pending items that are ready to process
    rows = conn.execute(
        """
        SELECT id FROM work_queue
        WHERE status = 'pending'
        AND (scheduled_after IS NULL OR scheduled_after <= ?)
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
        """,
        (now, limit)
    ).fetchall()

    conn.close()

    item_ids = [row["id"] for row in rows]

    if not item_ids:
        return {"status": "empty", "message": "No pending items to process"}

    # Process items in background
    async def process_all():
        results = []
        for item_id in item_ids:
            try:
                result = await process_work_item(item_id)
                results.append({"id": item_id, **result})
            except Exception as e:
                results.append({"id": item_id, "status": "failed", "error": str(e)})
        return results

    background_tasks.add_task(process_all)

    return {
        "status": "processing",
        "items_queued": len(item_ids),
        "item_ids": item_ids
    }

@router.post("/process/{item_id}")
async def process_single_item(item_id: int):
    """Process a single work item immediately."""
    try:
        result = await process_work_item(item_id)
        return {"status": "completed", "item_id": item_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/queue/{item_id}")
async def cancel_work_item(item_id: int):
    """Cancel a pending work item."""
    conn = get_db()

    row = conn.execute("SELECT status FROM work_queue WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Work item not found")

    if row["status"] != "pending":
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel item with status: {row['status']}")

    conn.execute(
        "UPDATE work_queue SET status = ? WHERE id = ?",
        (WorkStatus.CANCELLED.value, item_id)
    )
    conn.commit()
    conn.close()

    return {"status": "cancelled", "item_id": item_id}

# Convenience endpoints for common work types
@router.post("/queue/chapter")
async def queue_chapter_generation(
    chapter_number: int,
    featured_characters: List[str] = [],
    themes: List[str] = [],
    stages: List[str] = ["create_structure", "generate_tts", "generate_assets", "package"],
    priority: WorkPriority = WorkPriority.NORMAL,
    scheduled_after: Optional[str] = None
):
    """Queue a chapter for generation."""
    return await add_to_queue(WorkItemCreate(
        work_type=WorkType.CHAPTER_GENERATION,
        title=f"Generate Chapter {chapter_number}",
        description=f"Characters: {', '.join(featured_characters) or 'TBD'}. Themes: {', '.join(themes) or 'TBD'}",
        priority=priority,
        payload={
            "chapter_number": chapter_number,
            "featured_characters": featured_characters,
            "themes": themes,
            "stages": stages
        },
        scheduled_after=scheduled_after
    ))

@router.post("/queue/research")
async def queue_research(
    topic: str,
    depth: str = "standard",
    priority: WorkPriority = WorkPriority.NORMAL
):
    """Queue a research task."""
    return await add_to_queue(WorkItemCreate(
        work_type=WorkType.RESEARCH,
        title=f"Research: {topic}",
        description=f"Depth: {depth}",
        priority=priority,
        payload={"topic": topic, "depth": depth}
    ))

@router.post("/queue/overnight")
async def queue_overnight_batch(
    chapters: List[int] = [],
    research_topics: List[str] = [],
    generate_missing_assets: bool = True
):
    """Queue a batch of overnight work items."""
    items_queued = []

    # Schedule chapters for 2 AM
    for chapter_num in chapters:
        item = await queue_chapter_generation(
            chapter_number=chapter_num,
            priority=WorkPriority.HIGH
        )
        items_queued.append({"type": "chapter", "id": item.id, "chapter": chapter_num})

    # Schedule research for 3 AM
    for topic in research_topics:
        item = await queue_research(topic=topic, depth="deep")
        items_queued.append({"type": "research", "id": item.id, "topic": topic})

    # Schedule asset generation
    if generate_missing_assets:
        item = await add_to_queue(WorkItemCreate(
            work_type=WorkType.ASSET_GENERATION,
            title="Generate Missing Character Assets",
            priority=WorkPriority.NORMAL,
            payload={"asset_type": "portrait"}
        ))
        items_queued.append({"type": "asset_generation", "id": item.id})

    return {
        "status": "queued",
        "items_queued": len(items_queued),
        "items": items_queued,
        "message": "Items queued. Scheduler will process when resources are available."
    }


# =============================================================================
# CLUSTER RESOURCE ENDPOINTS
# =============================================================================

@router.get("/resources")
async def get_cluster_resources(force_refresh: bool = False):
    """Get current resource status across all cluster nodes."""
    resources = await resource_monitor.get_cluster_resources(force_refresh)

    # Convert dataclasses to dicts for JSON response
    return {
        "timestamp": resources.timestamp,
        "summary": {
            "total_gpus": resources.total_gpus,
            "available_gpus": resources.available_gpus,
            "total_vram_gb": resources.total_vram_gb,
            "free_vram_gb": resources.free_vram_gb,
            "cluster_gpu_util": resources.cluster_gpu_util,
            "can_accept_inference": resources.can_accept_inference,
            "can_accept_image_gen": resources.can_accept_image_gen,
        },
        "nodes": [
            {
                "name": n.name,
                "ip": n.ip,
                "online": n.online,
                "capabilities": n.capabilities,
                "total_vram_gb": n.total_vram_gb,
                "free_vram_gb": n.free_vram_gb,
                "avg_gpu_util": n.avg_gpu_util,
                "gpus": [
                    {
                        "index": g.gpu_index,
                        "name": g.gpu_name,
                        "utilization_percent": g.utilization_percent,
                        "vram_used_gb": g.vram_used_gb,
                        "vram_total_gb": g.vram_total_gb,
                        "vram_free_gb": g.vram_free_gb,
                        "temperature_f": g.temperature_f,
                        "power_watts": g.power_watts,
                        "available_for_work": g.available_for_work,
                    }
                    for g in n.gpus
                ]
            }
            for n in resources.nodes
        ],
        "thresholds": RESOURCE_THRESHOLDS,
    }


@router.get("/resources/summary")
async def get_resource_summary():
    """Get a quick summary of cluster resources."""
    resources = await resource_monitor.get_cluster_resources()

    return {
        "timestamp": resources.timestamp,
        "available_gpus": f"{resources.available_gpus}/{resources.total_gpus}",
        "free_vram_gb": resources.free_vram_gb,
        "cluster_util": f"{resources.cluster_gpu_util}%",
        "can_accept_inference": resources.can_accept_inference,
        "can_accept_image_gen": resources.can_accept_image_gen,
        "scheduler_running": scheduler.is_running,
    }


# =============================================================================
# SCHEDULER CONTROL ENDPOINTS
# =============================================================================

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get current status of the 24/7 autonomous scheduler."""
    status = scheduler.status

    # Add queue stats
    conn = get_db()
    pending = conn.execute("SELECT COUNT(*) FROM work_queue WHERE status = 'pending'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM work_queue WHERE status = 'in_progress'").fetchone()[0]
    conn.close()

    return {
        **status,
        "queue": {
            "pending": pending,
            "in_progress": in_progress,
        }
    }


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the 24/7 autonomous scheduler."""
    if scheduler.is_running:
        return {"status": "already_running", "message": "Scheduler is already running"}

    success = scheduler.start()
    if success:
        return {
            "status": "started",
            "message": "24/7 autonomous scheduler started. It will process tasks when resources are available.",
            "thresholds": RESOURCE_THRESHOLDS,
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the 24/7 autonomous scheduler."""
    if not scheduler.is_running:
        return {"status": "not_running", "message": "Scheduler is not running"}

    success = scheduler.stop()
    if success:
        return {
            "status": "stopped",
            "message": "Scheduler stop requested. Current tasks will complete.",
            "stats": {
                "tasks_processed": scheduler._tasks_processed,
                "tasks_failed": scheduler._tasks_failed,
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")


class ThresholdUpdate(BaseModel):
    gpu_util_max: Optional[int] = Field(None, ge=0, le=100)
    vram_free_min_gb: Optional[float] = Field(None, ge=0)
    check_interval_seconds: Optional[int] = Field(None, ge=5, le=300)
    max_concurrent_tasks: Optional[int] = Field(None, ge=1, le=10)


@router.put("/scheduler/thresholds")
async def update_thresholds(thresholds: ThresholdUpdate):
    """Update resource thresholds for the scheduler."""
    updated = {}

    if thresholds.gpu_util_max is not None:
        RESOURCE_THRESHOLDS["gpu_util_max"] = thresholds.gpu_util_max
        updated["gpu_util_max"] = thresholds.gpu_util_max

    if thresholds.vram_free_min_gb is not None:
        RESOURCE_THRESHOLDS["vram_free_min_gb"] = thresholds.vram_free_min_gb
        updated["vram_free_min_gb"] = thresholds.vram_free_min_gb

    if thresholds.check_interval_seconds is not None:
        RESOURCE_THRESHOLDS["check_interval_seconds"] = thresholds.check_interval_seconds
        updated["check_interval_seconds"] = thresholds.check_interval_seconds

    if thresholds.max_concurrent_tasks is not None:
        RESOURCE_THRESHOLDS["max_concurrent_tasks"] = thresholds.max_concurrent_tasks
        updated["max_concurrent_tasks"] = thresholds.max_concurrent_tasks

    return {
        "status": "updated",
        "updated": updated,
        "current_thresholds": RESOURCE_THRESHOLDS,
    }


# =============================================================================
# AUTO-START SCHEDULER ON IMPORT (Optional - controlled by env var)
# =============================================================================

def auto_start_scheduler():
    """Auto-start the scheduler if configured."""
    if os.environ.get("HYDRA_AUTOSTART_SCHEDULER", "").lower() == "true":
        logger.info("[Scheduler] Auto-starting scheduler (HYDRA_AUTOSTART_SCHEDULER=true)")
        # Note: This will be called during import, so we need to schedule it
        # to run after the event loop starts
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon(scheduler.start)
            else:
                scheduler.start()
        except RuntimeError:
            # No event loop yet, will start on first request
            pass


# Try to auto-start on import
auto_start_scheduler()
