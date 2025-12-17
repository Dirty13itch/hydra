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
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

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
    Collect current cluster health status.

    TODO: Integrate with real data sources:
    - Prometheus metrics
    - Unraid API
    - Docker API
    - TabbyAPI status
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": [
            {
                "id": "hydra-ai",
                "status": "online",
                "cpu_percent": 45,
                "memory_percent": 37,
                "gpu_utilization": [78, 65],
                "gpu_vram_percent": [87, 75]
            },
            {
                "id": "hydra-compute",
                "status": "online",
                "cpu_percent": 32,
                "memory_percent": 35,
                "gpu_utilization": [42, 38],
                "gpu_vram_percent": [50, 38]
            },
            {
                "id": "hydra-storage",
                "status": "online",
                "cpu_percent": 28,
                "memory_percent": 40,
                "gpu_utilization": [],
                "gpu_vram_percent": []
            }
        ],
        "services": {
            "healthy": 22,
            "total": 25
        },
        "containers": {
            "running": 58,
            "total": 64
        }
    }


async def collect_container_status() -> Dict[str, Any]:
    """Collect container status updates."""
    # TODO: Integrate with Docker API / Unraid API
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "changes": [],  # List of containers with status changes
        "summary": {
            "running": 58,
            "stopped": 4,
            "unhealthy": 2
        }
    }


async def collect_gpu_metrics() -> Dict[str, Any]:
    """Collect GPU metrics from all nodes."""
    # TODO: Integrate with nvidia-smi via SSH or agent
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "gpus": [
            {
                "node": "hydra-ai",
                "name": "RTX 5090",
                "utilization": 78,
                "memory_used": 28672,
                "memory_total": 32768,
                "temperature": 72,
                "power": 420
            },
            {
                "node": "hydra-ai",
                "name": "RTX 4090",
                "utilization": 65,
                "memory_used": 18432,
                "memory_total": 24576,
                "temperature": 68,
                "power": 280
            },
            {
                "node": "hydra-compute",
                "name": "RTX 5070 Ti #1",
                "utilization": 42,
                "memory_used": 8192,
                "memory_total": 16384,
                "temperature": 58,
                "power": 180
            },
            {
                "node": "hydra-compute",
                "name": "RTX 5070 Ti #2",
                "utilization": 38,
                "memory_used": 6144,
                "memory_total": 16384,
                "temperature": 55,
                "power": 165
            }
        ],
        "total_power": 1045,
        "total_vram_used": 61440,
        "total_vram_total": 89088
    }


async def collect_agent_status() -> Dict[str, Any]:
    """Collect AI agent status."""
    # TODO: Integrate with agent scheduler
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": [
            {
                "id": "research-alpha",
                "status": "active",
                "task": "Analyzing quantum computing papers",
                "progress": 67
            },
            {
                "id": "code-prime",
                "status": "thinking",
                "task": "Implementing autonomous controller",
                "progress": 45
            }
        ],
        "active_count": 2,
        "total_count": 4
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
                    event=EventType.CLUSTER_HEALTH,
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
                    event=EventType.GPU_METRICS,
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
                    event=EventType.AGENT_STATUS,
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
                    event=EventType.HEARTBEAT,
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
        event=EventType.ALERT,
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
        event=EventType.NOTIFICATION,
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
        event=EventType.CONTAINER_STATUS,
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
        event=EventType.MODEL_STATUS,
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
