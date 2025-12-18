"""
SSE (Server-Sent Events) Router - Real-time streaming for Hydra Control Plane.

Provides real-time updates to the dashboard via Server-Sent Events:
- Cluster health status
- Container state changes
- GPU metrics
- Agent activity
- Alert notifications

SSE is chosen over WebSockets because:
- Unidirectional (server -> client) fits dashboard use case
- Simpler, HTTP-compatible (no firewall/proxy issues)
- Built-in browser reconnection
- Lower overhead than WebSockets
- 2025 industry standard for dashboards
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# API configuration for internal calls
API_BASE_URL = os.environ.get("HYDRA_API_URL", "http://localhost:8700")
API_KEY = os.environ.get("HYDRA_API_KEY", "hydra-dev-key")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://192.168.1.244:9090")

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType(str, Enum):
    """Types of events that can be streamed."""
    CLUSTER_HEALTH = "cluster_health"
    CONTAINER_STATUS = "container_status"
    GPU_METRICS = "gpu_metrics"
    AGENT_STATUS = "agent_status"
    ALERT = "alert"
    NOTIFICATION = "notification"
    MODEL_STATUS = "model_status"
    HEARTBEAT = "heartbeat"


@dataclass
class SSEEvent:
    """Server-Sent Event structure."""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def format(self) -> str:
        """Format as SSE message."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {json.dumps(self.data)}")
        lines.append("")  # End with blank line
        return "\n".join(lines) + "\n"


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

class ConnectionManager:
    """
    Manages SSE client connections.

    Tracks active connections and provides methods for broadcasting events.
    """

    def __init__(self):
        self.active_connections: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: str) -> asyncio.Queue:
        """Register a new client connection."""
        async with self._lock:
            queue = asyncio.Queue(maxsize=100)
            self.active_connections[client_id] = queue
            logger.info(f"SSE client connected: {client_id} (total: {len(self.active_connections)})")
            return queue

    async def disconnect(self, client_id: str):
        """Remove a client connection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                logger.info(f"SSE client disconnected: {client_id} (total: {len(self.active_connections)})")

    async def broadcast(self, event: SSEEvent):
        """Send event to all connected clients."""
        async with self._lock:
            for client_id, queue in list(self.active_connections.items()):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for client {client_id}, dropping event")

    async def send_to_client(self, client_id: str, event: SSEEvent):
        """Send event to a specific client."""
        async with self._lock:
            if client_id in self.active_connections:
                try:
                    self.active_connections[client_id].put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for client {client_id}")

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# DATA COLLECTION (Mock for now - will integrate with real data sources)
# =============================================================================

async def collect_cluster_health() -> Dict[str, Any]:
    """
    Collect current cluster health status from /autonomous/resources API.

    Integrated with:
    - ClusterResourceMonitor (Prometheus-based GPU metrics)
    - /health/cluster for services
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get cluster resources from autonomous queue
            resources_response = await client.get(
                f"{API_BASE_URL}/autonomous/resources",
                headers={"X-API-Key": API_KEY}
            )

            if resources_response.status_code == 200:
                resources = resources_response.json()
                nodes = []
                for node_data in resources.get("nodes", []):
                    gpu_utils = [g.get("utilization_percent", 0) for g in node_data.get("gpus", [])]
                    gpu_vram_pct = [
                        int((g.get("vram_used_gb", 0) / g.get("vram_total_gb", 1)) * 100)
                        for g in node_data.get("gpus", [])
                    ]
                    nodes.append({
                        "id": node_data.get("name", "unknown"),
                        "status": "online" if node_data.get("online") else "offline",
                        "cpu_percent": 0,  # Will add Prometheus query if needed
                        "memory_percent": 0,
                        "gpu_utilization": gpu_utils,
                        "gpu_vram_percent": gpu_vram_pct
                    })

                # Get service health
                health_response = await client.get(
                    f"{API_BASE_URL}/health/cluster",
                    headers={"X-API-Key": API_KEY}
                )
                services_healthy = 0
                services_total = 0
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    services = health_data.get("services", [])
                    services_total = len(services)
                    services_healthy = sum(1 for s in services if s.get("status") == "healthy")

                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "nodes": nodes,
                    "services": {
                        "healthy": services_healthy,
                        "total": services_total
                    },
                    "containers": {
                        "running": resources.get("summary", {}).get("total_gpus", 0),
                        "total": resources.get("summary", {}).get("total_gpus", 0)
                    }
                }
    except Exception as e:
        logger.warning(f"Failed to collect cluster health: {e}")

    # Fallback to minimal data
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": [],
        "services": {"healthy": 0, "total": 0},
        "containers": {"running": 0, "total": 0}
    }


async def collect_container_status() -> Dict[str, Any]:
    """
    Collect container status updates from /container-health/list API.

    Integrated with Docker API via container health router.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/container-health/list",
                headers={"X-API-Key": API_KEY}
            )

            if response.status_code == 200:
                data = response.json()
                containers = data.get("containers", [])
                running = sum(1 for c in containers if c.get("status") == "running")
                unhealthy = sum(1 for c in containers if c.get("health") == "unhealthy")
                stopped = len(containers) - running

                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "changes": [],  # Would need delta tracking
                    "summary": {
                        "running": running,
                        "stopped": stopped,
                        "unhealthy": unhealthy
                    }
                }
    except Exception as e:
        logger.warning(f"Failed to collect container status: {e}")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "changes": [],
        "summary": {"running": 0, "stopped": 0, "unhealthy": 0}
    }


async def collect_gpu_metrics() -> Dict[str, Any]:
    """
    Collect GPU metrics from all nodes via /autonomous/resources API.

    Integrated with ClusterResourceMonitor (Prometheus-based):
    - DCGM metrics for hydra-ai (RTX 5090, RTX 4090)
    - nvidia-exporter metrics for hydra-compute (2x RTX 5070 Ti)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/autonomous/resources",
                headers={"X-API-Key": API_KEY}
            )

            if response.status_code == 200:
                data = response.json()
                gpus = []
                total_power = 0
                total_vram_used = 0
                total_vram_total = 0

                for node in data.get("nodes", []):
                    node_name = node.get("name", "unknown")
                    for gpu_data in node.get("gpus", []):
                        vram_used_mb = int(gpu_data.get("vram_used_gb", 0) * 1024)
                        vram_total_mb = int(gpu_data.get("vram_total_gb", 0) * 1024)
                        power = gpu_data.get("power_watts", 0)

                        gpus.append({
                            "node": node_name,
                            "name": gpu_data.get("name", "Unknown GPU"),
                            "utilization": gpu_data.get("utilization_percent", 0),
                            "memory_used": vram_used_mb,
                            "memory_total": vram_total_mb,
                            "temperature": gpu_data.get("temperature_f", 0),  # Already in F
                            "power": power
                        })

                        total_power += power
                        total_vram_used += vram_used_mb
                        total_vram_total += vram_total_mb

                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "gpus": gpus,
                    "total_power": total_power,
                    "total_vram_used": total_vram_used,
                    "total_vram_total": total_vram_total
                }
    except Exception as e:
        logger.warning(f"Failed to collect GPU metrics: {e}")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "gpus": [],
        "total_power": 0,
        "total_vram_used": 0,
        "total_vram_total": 0
    }


async def collect_agent_status() -> Dict[str, Any]:
    """
    Collect AI agent status from /autonomous/scheduler/status API.

    Integrated with:
    - AutonomousScheduler for 24/7 task processing
    - /autonomous/queue for pending tasks
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get scheduler status
            scheduler_response = await client.get(
                f"{API_BASE_URL}/autonomous/scheduler/status",
                headers={"X-API-Key": API_KEY}
            )

            # Get queue stats
            queue_response = await client.get(
                f"{API_BASE_URL}/autonomous/queue/stats",
                headers={"X-API-Key": API_KEY}
            )

            scheduler_data = {}
            queue_data = {}

            if scheduler_response.status_code == 200:
                scheduler_data = scheduler_response.json()
            if queue_response.status_code == 200:
                queue_data = queue_response.json()

            # Build agent list from scheduler state
            agents = []
            current_tasks = scheduler_data.get("current_tasks", 0)
            if current_tasks > 0:
                agents.append({
                    "id": "scheduler-main",
                    "status": "active",
                    "task": f"Processing {current_tasks} task(s)",
                    "progress": 50
                })

            # Add queue info
            pending = queue_data.get("pending", 0)
            if pending > 0:
                agents.append({
                    "id": "queue-monitor",
                    "status": "waiting",
                    "task": f"{pending} tasks pending",
                    "progress": 0
                })

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "agents": agents,
                "active_count": current_tasks,
                "total_count": pending + current_tasks,
                "scheduler_running": scheduler_data.get("running", False),
                "tasks_processed": scheduler_data.get("tasks_processed", 0),
                "tasks_failed": scheduler_data.get("tasks_failed", 0)
            }
    except Exception as e:
        logger.warning(f"Failed to collect agent status: {e}")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": [],
        "active_count": 0,
        "total_count": 0,
        "scheduler_running": False,
        "tasks_processed": 0,
        "tasks_failed": 0
    }


# =============================================================================
# SSE STREAMING ENDPOINT
# =============================================================================

@router.get("/stream")
async def event_stream(
    request: Request,
    client_id: Optional[str] = Query(None, description="Optional client identifier"),
    events: Optional[str] = Query(
        "cluster_health,container_status,gpu_metrics,agent_status,heartbeat",
        description="Comma-separated list of event types to subscribe to"
    )
):
    """
    SSE endpoint for real-time dashboard updates.

    Streams events to the client as they occur. The connection remains open
    and events are pushed in real-time.

    Args:
        client_id: Optional identifier for the client (auto-generated if not provided)
        events: Comma-separated list of event types to subscribe to

    Event Types:
        - cluster_health: Overall cluster status (every 5s)
        - container_status: Container state changes
        - gpu_metrics: GPU utilization and temperature (every 5s)
        - agent_status: AI agent activity
        - alert: Alert notifications
        - heartbeat: Keep-alive signal (every 30s)

    Returns:
        StreamingResponse with SSE content type
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())[:8]

    # Parse requested event types
    requested_events = set(e.strip() for e in events.split(","))

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        queue = await manager.connect(client_id)

        # Send initial connection event
        welcome_event = SSEEvent(
            event="connected",
            data={
                "client_id": client_id,
                "subscribed_events": list(requested_events),
                "timestamp": datetime.utcnow().isoformat()
            },
            retry=3000  # Reconnect after 3 seconds if disconnected
        )
        yield welcome_event.format()

        # Start background tasks for data collection
        collection_task = asyncio.create_task(
            _collect_and_queue_events(queue, requested_events)
        )

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event.format()
                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            pass
        finally:
            collection_task.cancel()
            await manager.disconnect(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


async def _collect_and_queue_events(
    queue: asyncio.Queue,
    requested_events: Set[str]
):
    """
    Background task to collect data and queue events.

    Runs different collection tasks at different intervals:
    - Cluster health: every 5 seconds
    - GPU metrics: every 5 seconds
    - Agent status: every 10 seconds
    - Heartbeat: every 30 seconds
    """
    last_health = 0
    last_gpu = 0
    last_agent = 0
    last_heartbeat = 0

    event_id = 0

    while True:
        try:
            now = asyncio.get_event_loop().time()

            # Cluster health - every 5 seconds
            if "cluster_health" in requested_events and now - last_health >= 5:
                data = await collect_cluster_health()
                event_id += 1
                event = SSEEvent(
                    event=EventType.CLUSTER_HEALTH.value,
                    data=data,
                    id=str(event_id)
                )
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
                last_health = now

            # GPU metrics - every 5 seconds
            if "gpu_metrics" in requested_events and now - last_gpu >= 5:
                data = await collect_gpu_metrics()
                event_id += 1
                event = SSEEvent(
                    event=EventType.GPU_METRICS.value,
                    data=data,
                    id=str(event_id)
                )
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
                last_gpu = now

            # Agent status - every 10 seconds
            if "agent_status" in requested_events and now - last_agent >= 10:
                data = await collect_agent_status()
                event_id += 1
                event = SSEEvent(
                    event=EventType.AGENT_STATUS.value,
                    data=data,
                    id=str(event_id)
                )
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
                last_agent = now

            # Heartbeat - every 30 seconds
            if "heartbeat" in requested_events and now - last_heartbeat >= 30:
                event_id += 1
                event = SSEEvent(
                    event=EventType.HEARTBEAT.value,
                    data={
                        "timestamp": datetime.utcnow().isoformat(),
                        "connections": manager.connection_count
                    },
                    id=str(event_id)
                )
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
                last_heartbeat = now

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error collecting events: {e}")
            await asyncio.sleep(5)


# =============================================================================
# BROADCAST ENDPOINTS (for other services to push events)
# =============================================================================

@router.post("/broadcast/alert")
async def broadcast_alert(
    alert: Dict[str, Any]
):
    """
    Broadcast an alert to all connected clients.

    Used by other services to push alert notifications.
    """
    event = SSEEvent(
        event=EventType.ALERT.value,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            **alert
        }
    )
    await manager.broadcast(event)
    return {"status": "broadcast", "connections": manager.connection_count}


@router.post("/broadcast/notification")
async def broadcast_notification(
    notification: Dict[str, Any]
):
    """
    Broadcast a notification to all connected clients.

    Used for general notifications (not alerts).
    """
    event = SSEEvent(
        event=EventType.NOTIFICATION.value,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            **notification
        }
    )
    await manager.broadcast(event)
    return {"status": "broadcast", "connections": manager.connection_count}


@router.post("/broadcast/container-update")
async def broadcast_container_update(
    update: Dict[str, Any]
):
    """
    Broadcast a container status update.

    Called when a container starts, stops, or changes state.
    """
    event = SSEEvent(
        event=EventType.CONTAINER_STATUS.value,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            **update
        }
    )
    await manager.broadcast(event)
    return {"status": "broadcast", "connections": manager.connection_count}


@router.post("/broadcast/model-update")
async def broadcast_model_update(
    update: Dict[str, Any]
):
    """
    Broadcast a model status update.

    Called when a model loads, unloads, or changes status.
    """
    event = SSEEvent(
        event=EventType.MODEL_STATUS.value,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            **update
        }
    )
    await manager.broadcast(event)
    return {"status": "broadcast", "connections": manager.connection_count}


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/status")
async def get_sse_status():
    """Get SSE connection statistics."""
    return {
        "active_connections": manager.connection_count,
        "timestamp": datetime.utcnow().isoformat()
    }
