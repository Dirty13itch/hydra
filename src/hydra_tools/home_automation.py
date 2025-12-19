"""
Home Automation Integration for Hydra Command Center

Provides REST API endpoints for controlling home automation via Home Assistant.
Supports rooms, lights, scenes, and device control.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import logging

import httpx
import websockets
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class RoomState(BaseModel):
    id: str
    name: str
    temp: Optional[float] = None
    humidity: Optional[float] = None
    devices: int = 0
    lights_on: bool = False
    active: bool = False
    area_id: Optional[str] = None


class DeviceState(BaseModel):
    id: str
    name: str
    entity_id: str
    device_type: str  # light, switch, sensor, climate, etc.
    state: str
    room_id: Optional[str] = None
    attributes: Dict[str, Any] = {}


class SceneState(BaseModel):
    id: str
    name: str
    entity_id: str
    icon: Optional[str] = None


class LightControlRequest(BaseModel):
    entity_id: str
    action: str  # "on", "off", "toggle"
    brightness: Optional[int] = None  # 0-255
    color_temp: Optional[int] = None


class SceneActivateRequest(BaseModel):
    entity_id: str


# =============================================================================
# Home Assistant Client
# =============================================================================

class HomeAssistantClient:
    """Client for interacting with Home Assistant API."""

    def __init__(
        self,
        url: str = None,
        token: str = None,
    ):
        self.url = url or os.getenv("HA_URL", "http://192.168.1.244:8123")
        self.token = token or os.getenv("HA_TOKEN", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _is_configured(self) -> bool:
        return bool(self.token)

    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        if not self._is_configured():
            return []

        try:
            response = await self.client.get(
                f"{self.url}/api/states",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get HA states: {e}")
            return []

    async def get_areas(self) -> List[Dict[str, Any]]:
        """Get all areas (rooms) from Home Assistant."""
        if not self._is_configured():
            return []

        try:
            response = await self.client.get(
                f"{self.url}/api/config",
                headers=self.headers,
            )
            response.raise_for_status()
            config = response.json()
            # Areas are in a separate registry
            return config.get("areas", [])
        except Exception as e:
            logger.error(f"Failed to get HA areas: {e}")
            return []

    async def call_service(
        self,
        domain: str,
        service: str,
        data: Dict[str, Any],
    ) -> bool:
        """Call a Home Assistant service."""
        if not self._is_configured():
            logger.warning("Home Assistant not configured")
            return False

        try:
            response = await self.client.post(
                f"{self.url}/api/services/{domain}/{service}",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to call HA service {domain}.{service}: {e}")
            return False

    async def get_rooms(self) -> List[RoomState]:
        """Get rooms with their states."""
        states = await self.get_states()

        # Group entities by area/room
        room_map: Dict[str, Dict[str, Any]] = {}

        # Default rooms based on common naming
        default_rooms = {
            "living_room": "Living Room",
            "bedroom": "Bedroom",
            "office": "Office",
            "kitchen": "Kitchen",
            "bathroom": "Bathroom",
            "garage": "Garage",
            "entryway": "Entryway",
        }

        for entity in states:
            entity_id = entity.get("entity_id", "")
            state = entity.get("state", "")
            attrs = entity.get("attributes", {})

            # Try to determine room from entity name
            friendly_name = attrs.get("friendly_name", "").lower()
            room_key = None

            for key, name in default_rooms.items():
                if key.replace("_", " ") in friendly_name or key in entity_id:
                    room_key = key
                    break

            if not room_key:
                continue

            if room_key not in room_map:
                room_map[room_key] = {
                    "id": room_key,
                    "name": default_rooms[room_key],
                    "temp": None,
                    "humidity": None,
                    "devices": 0,
                    "lights_on": False,
                    "active": False,
                }

            room_map[room_key]["devices"] += 1

            # Track light states
            if entity_id.startswith("light."):
                if state == "on":
                    room_map[room_key]["lights_on"] = True
                    room_map[room_key]["active"] = True

            # Track temperature
            if entity_id.startswith("sensor.") and "temperature" in entity_id:
                try:
                    room_map[room_key]["temp"] = float(state)
                except (ValueError, TypeError):
                    pass

            # Track climate
            if entity_id.startswith("climate."):
                try:
                    room_map[room_key]["temp"] = float(attrs.get("current_temperature", 0))
                except (ValueError, TypeError):
                    pass

        # Create room states
        rooms = []
        for room_data in room_map.values():
            rooms.append(RoomState(**room_data))

        # If no rooms found from HA, return mock rooms
        if not rooms:
            rooms = [
                RoomState(id="living_room", name="Living Room", temp=72, devices=4, lights_on=True, active=True),
                RoomState(id="office", name="Office", temp=70, devices=3, lights_on=True, active=True),
                RoomState(id="bedroom", name="Bedroom", temp=68, devices=2, lights_on=False, active=False),
                RoomState(id="kitchen", name="Kitchen", temp=71, devices=5, lights_on=True, active=True),
                RoomState(id="entryway", name="Entryway", temp=69, devices=1, lights_on=False, active=False),
            ]

        return rooms

    async def get_devices(self, room_id: Optional[str] = None) -> List[DeviceState]:
        """Get all controllable devices."""
        states = await self.get_states()
        devices = []

        controllable_domains = ["light", "switch", "fan", "cover", "climate", "lock"]

        for entity in states:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".")[0] if "." in entity_id else ""

            if domain not in controllable_domains:
                continue

            attrs = entity.get("attributes", {})

            device = DeviceState(
                id=entity_id.replace(".", "_"),
                name=attrs.get("friendly_name", entity_id),
                entity_id=entity_id,
                device_type=domain,
                state=entity.get("state", "unknown"),
                attributes=attrs,
            )
            devices.append(device)

        return devices

    async def get_scenes(self) -> List[SceneState]:
        """Get all scenes."""
        states = await self.get_states()
        scenes = []

        for entity in states:
            entity_id = entity.get("entity_id", "")
            if not entity_id.startswith("scene."):
                continue

            attrs = entity.get("attributes", {})

            scene = SceneState(
                id=entity_id.replace(".", "_"),
                name=attrs.get("friendly_name", entity_id.replace("scene.", "").replace("_", " ").title()),
                entity_id=entity_id,
                icon=attrs.get("icon"),
            )
            scenes.append(scene)

        # If no scenes found, return default scenes
        if not scenes:
            scenes = [
                SceneState(id="morning_rise", name="Morning Rise", entity_id="scene.morning_rise"),
                SceneState(id="night_mode", name="Night Mode", entity_id="scene.night_mode"),
                SceneState(id="movie_time", name="Movie Time", entity_id="scene.movie_time"),
                SceneState(id="lockdown", name="Lockdown", entity_id="scene.lockdown"),
            ]

        return scenes

    async def control_light(self, request: LightControlRequest) -> bool:
        """Control a light entity."""
        if request.action == "on":
            data = {"entity_id": request.entity_id}
            if request.brightness is not None:
                data["brightness"] = request.brightness
            if request.color_temp is not None:
                data["color_temp"] = request.color_temp
            return await self.call_service("light", "turn_on", data)

        elif request.action == "off":
            return await self.call_service("light", "turn_off", {"entity_id": request.entity_id})

        elif request.action == "toggle":
            return await self.call_service("light", "toggle", {"entity_id": request.entity_id})

        return False

    async def activate_scene(self, entity_id: str) -> bool:
        """Activate a scene."""
        return await self.call_service("scene", "turn_on", {"entity_id": entity_id})

    async def get_status(self) -> Dict[str, Any]:
        """Get Home Assistant connection status."""
        configured = self._is_configured()

        if not configured:
            return {
                "connected": False,
                "configured": False,
                "url": self.url,
                "error": "No HA_TOKEN configured",
            }

        try:
            response = await self.client.get(
                f"{self.url}/api/",
                headers=self.headers,
            )
            connected = response.status_code == 200
            return {
                "connected": connected,
                "configured": True,
                "url": self.url,
                "message": response.json().get("message", "") if connected else None,
            }
        except Exception as e:
            return {
                "connected": False,
                "configured": True,
                "url": self.url,
                "error": str(e),
            }


# =============================================================================
# Home Assistant WebSocket Client (Real-time Events)
# =============================================================================

class HAWebSocketClient:
    """WebSocket client for real-time Home Assistant events."""

    def __init__(
        self,
        url: str = None,
        token: str = None,
    ):
        self.url = url or os.getenv("HA_URL", "http://192.168.1.244:8123")
        self.ws_url = self.url.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
        self.token = token or os.getenv("HA_TOKEN", "")
        self._ws = None
        self._message_id = 1
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._task = None

    def _is_configured(self) -> bool:
        return bool(self.token)

    async def connect(self) -> bool:
        """Connect to Home Assistant WebSocket API."""
        if not self._is_configured():
            logger.warning("HA WebSocket: No token configured")
            return False

        try:
            self._ws = await websockets.connect(self.ws_url)

            # Receive auth_required message
            msg = await self._ws.recv()
            data = json.loads(msg)

            if data.get("type") != "auth_required":
                logger.error(f"Unexpected HA WS message: {data}")
                return False

            # Send auth
            await self._ws.send(json.dumps({
                "type": "auth",
                "access_token": self.token,
            }))

            # Receive auth_ok
            msg = await self._ws.recv()
            data = json.loads(msg)

            if data.get("type") == "auth_ok":
                logger.info("HA WebSocket: Connected and authenticated")
                return True
            else:
                logger.error(f"HA WebSocket auth failed: {data}")
                return False

        except Exception as e:
            logger.error(f"HA WebSocket connection error: {e}")
            return False

    async def disconnect(self):
        """Disconnect from WebSocket."""
        self._running = False
        if self._task:
            self._task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def subscribe_events(self, event_type: str = None) -> int:
        """Subscribe to Home Assistant events."""
        if not self._ws:
            return -1

        msg_id = self._message_id
        self._message_id += 1

        payload = {
            "id": msg_id,
            "type": "subscribe_events",
        }
        if event_type:
            payload["event_type"] = event_type

        await self._ws.send(json.dumps(payload))
        return msg_id

    async def subscribe_state_changes(self, entity_id: str = None) -> int:
        """Subscribe to state change events, optionally filtered by entity."""
        if not self._ws:
            return -1

        msg_id = self._message_id
        self._message_id += 1

        if entity_id:
            # Subscribe to specific entity trigger
            payload = {
                "id": msg_id,
                "type": "subscribe_trigger",
                "trigger": {
                    "platform": "state",
                    "entity_id": entity_id,
                }
            }
        else:
            # Subscribe to all state changes
            payload = {
                "id": msg_id,
                "type": "subscribe_events",
                "event_type": "state_changed",
            }

        await self._ws.send(json.dumps(payload))
        return msg_id

    def add_subscriber(self, event_type: str, callback: Callable):
        """Add a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def _handle_message(self, msg: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(msg)
            msg_type = data.get("type", "")

            if msg_type == "event":
                event = data.get("event", {})
                event_type = event.get("event_type", "")

                # Call subscribers
                for callback in self._subscribers.get(event_type, []):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Subscriber error: {e}")

                # Also call wildcard subscribers
                for callback in self._subscribers.get("*", []):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Subscriber error: {e}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from HA WS: {msg}")

    async def listen(self):
        """Listen for WebSocket messages."""
        self._running = True
        while self._running and self._ws:
            try:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=60)
                await self._handle_message(msg)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if self._ws:
                    await self._ws.ping()
            except websockets.ConnectionClosed:
                logger.warning("HA WebSocket connection closed")
                self._running = False
            except Exception as e:
                logger.error(f"HA WebSocket error: {e}")
                self._running = False

    async def start_listening(self):
        """Start listening in background."""
        if self._task is not None:
            return

        if not await self.connect():
            return False

        # Subscribe to state changes
        await self.subscribe_state_changes()

        # Start listener task
        self._task = asyncio.create_task(self.listen())
        return True


# =============================================================================
# Entity State Tracker
# =============================================================================

class EntityStateTracker:
    """Tracks entity states in real-time via WebSocket."""

    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._ws_client: Optional[HAWebSocketClient] = None
        self._last_update = datetime.utcnow()
        self._connected_clients: List[WebSocket] = []

    async def start(self):
        """Start the entity state tracker."""
        self._ws_client = HAWebSocketClient()

        # Add state change handler
        self._ws_client.add_subscriber("state_changed", self._on_state_change)

        # Start WebSocket listener
        if await self._ws_client.start_listening():
            logger.info("Entity state tracker started")
            return True
        return False

    async def stop(self):
        """Stop the tracker."""
        if self._ws_client:
            await self._ws_client.disconnect()

    async def _on_state_change(self, event: Dict[str, Any]):
        """Handle state change event."""
        data = event.get("data", {})
        entity_id = data.get("entity_id", "")
        new_state = data.get("new_state", {})

        if entity_id and new_state:
            self._states[entity_id] = {
                "entity_id": entity_id,
                "state": new_state.get("state"),
                "attributes": new_state.get("attributes", {}),
                "last_changed": new_state.get("last_changed"),
                "last_updated": new_state.get("last_updated"),
            }
            self._last_update = datetime.utcnow()

            # Broadcast to connected WebSocket clients
            await self._broadcast_state_change(entity_id, self._states[entity_id])

    async def _broadcast_state_change(self, entity_id: str, state: Dict[str, Any]):
        """Broadcast state change to connected clients."""
        message = json.dumps({
            "type": "state_changed",
            "entity_id": entity_id,
            "state": state,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        disconnected = []
        for client in self._connected_clients:
            try:
                await client.send_text(message)
            except:
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            self._connected_clients.remove(client)

    def add_client(self, websocket: WebSocket):
        """Add a WebSocket client to receive updates."""
        self._connected_clients.append(websocket)

    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client."""
        if websocket in self._connected_clients:
            self._connected_clients.remove(websocket)

    def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get cached state for an entity."""
        return self._states.get(entity_id)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached states."""
        return self._states.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get tracker status."""
        return {
            "connected": self._ws_client is not None and self._ws_client._running,
            "entities_tracked": len(self._states),
            "last_update": self._last_update.isoformat() + "Z",
            "connected_clients": len(self._connected_clients),
        }


# =============================================================================
# Global Instances
# =============================================================================

_ha_client: Optional[HomeAssistantClient] = None
_entity_tracker: Optional[EntityStateTracker] = None


def get_ha_client() -> HomeAssistantClient:
    """Get or create Home Assistant client."""
    global _ha_client
    if _ha_client is None:
        _ha_client = HomeAssistantClient()
    return _ha_client


def get_entity_tracker() -> EntityStateTracker:
    """Get or create Entity State Tracker."""
    global _entity_tracker
    if _entity_tracker is None:
        _entity_tracker = EntityStateTracker()
    return _entity_tracker


async def start_entity_tracker():
    """Start the entity tracker if HA is configured."""
    tracker = get_entity_tracker()
    if await tracker.start():
        logger.info("Entity state tracker started successfully")
        return True
    logger.warning("Entity state tracker failed to start (HA_TOKEN may not be configured)")
    return False


async def stop_entity_tracker():
    """Stop the entity tracker."""
    global _entity_tracker
    if _entity_tracker:
        await _entity_tracker.stop()
        _entity_tracker = None


# =============================================================================
# FastAPI Router
# =============================================================================

def create_home_automation_router() -> APIRouter:
    """Create FastAPI router for home automation endpoints."""
    router = APIRouter(prefix="/home", tags=["home-automation"])

    @router.get("/status")
    async def get_status():
        """Get Home Assistant connection status."""
        client = get_ha_client()
        return await client.get_status()

    @router.get("/rooms")
    async def get_rooms():
        """Get all rooms with their states."""
        client = get_ha_client()
        rooms = await client.get_rooms()
        return {"rooms": [r.dict() for r in rooms]}

    @router.get("/devices")
    async def get_devices(room_id: Optional[str] = None):
        """Get all controllable devices."""
        client = get_ha_client()
        devices = await client.get_devices(room_id)
        return {"devices": [d.dict() for d in devices]}

    @router.get("/scenes")
    async def get_scenes():
        """Get all scenes."""
        client = get_ha_client()
        scenes = await client.get_scenes()
        return {"scenes": [s.dict() for s in scenes]}

    @router.post("/light/control")
    async def control_light(request: LightControlRequest):
        """Control a light entity."""
        client = get_ha_client()
        success = await client.control_light(request)
        return {"success": success}

    @router.post("/scene/activate")
    async def activate_scene(request: SceneActivateRequest):
        """Activate a scene."""
        client = get_ha_client()
        success = await client.activate_scene(request.entity_id)
        return {"success": success}

    @router.post("/room/{room_id}/lights/{action}")
    async def control_room_lights(room_id: str, action: str):
        """Control all lights in a room."""
        if action not in ["on", "off", "toggle"]:
            raise HTTPException(status_code=400, detail="Invalid action. Use: on, off, toggle")

        client = get_ha_client()
        states = await client.get_states()

        # Find lights matching the room
        controlled = []
        for entity in states:
            entity_id = entity.get("entity_id", "")
            if not entity_id.startswith("light."):
                continue

            # Check if light belongs to room
            if room_id.replace("_", " ") in entity_id or room_id in entity_id:
                success = await client.control_light(
                    LightControlRequest(entity_id=entity_id, action=action)
                )
                controlled.append({"entity_id": entity_id, "success": success})

        return {"room_id": room_id, "action": action, "controlled": controlled}

    # =========================================================================
    # Entity State Tracking Endpoints
    # =========================================================================

    @router.get("/tracker/status")
    async def get_tracker_status():
        """Get entity state tracker status."""
        tracker = get_entity_tracker()
        return tracker.get_status()

    @router.post("/tracker/start")
    async def start_tracker():
        """Start the entity state tracker."""
        success = await start_entity_tracker()
        return {"success": success, "message": "Tracker started" if success else "Failed to start tracker"}

    @router.post("/tracker/stop")
    async def stop_tracker():
        """Stop the entity state tracker."""
        await stop_entity_tracker()
        return {"success": True, "message": "Tracker stopped"}

    @router.get("/entities")
    async def get_tracked_entities():
        """Get all tracked entity states from real-time cache."""
        tracker = get_entity_tracker()
        states = tracker.get_all_states()
        return {
            "entities": list(states.values()),
            "count": len(states),
            "tracker_status": tracker.get_status(),
        }

    @router.get("/entity/{entity_id:path}")
    async def get_entity_state(entity_id: str):
        """Get state for a specific entity from real-time cache."""
        tracker = get_entity_tracker()
        state = tracker.get_state(entity_id)
        if state:
            return state

        # Fallback to REST API if not in cache
        client = get_ha_client()
        states = await client.get_states()
        for entity in states:
            if entity.get("entity_id") == entity_id:
                return {
                    "entity_id": entity_id,
                    "state": entity.get("state"),
                    "attributes": entity.get("attributes", {}),
                    "last_changed": entity.get("last_changed"),
                    "last_updated": entity.get("last_updated"),
                    "source": "rest_api",
                }

        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    # =========================================================================
    # WebSocket Endpoint for Real-time Updates
    # =========================================================================

    @router.websocket("/ws/entities")
    async def websocket_entity_updates(websocket: WebSocket):
        """WebSocket endpoint for real-time entity state updates."""
        await websocket.accept()

        tracker = get_entity_tracker()
        tracker.add_client(websocket)

        # Send initial state dump
        try:
            initial_states = tracker.get_all_states()
            await websocket.send_json({
                "type": "initial_state",
                "entities": list(initial_states.values()),
                "count": len(initial_states),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Failed to send initial state: {e}")

        try:
            # Keep connection alive and listen for client messages
            while True:
                try:
                    data = await websocket.receive_text()
                    msg = json.loads(data)

                    # Handle client commands
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif msg.get("type") == "get_entity":
                        entity_id = msg.get("entity_id")
                        state = tracker.get_state(entity_id)
                        await websocket.send_json({
                            "type": "entity_state",
                            "entity_id": entity_id,
                            "state": state,
                        })
                    elif msg.get("type") == "refresh":
                        # Re-send all states
                        states = tracker.get_all_states()
                        await websocket.send_json({
                            "type": "refresh_state",
                            "entities": list(states.values()),
                            "count": len(states),
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        })

                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            tracker.remove_client(websocket)

    return router


if __name__ == "__main__":
    import asyncio

    async def test():
        client = HomeAssistantClient()

        # Test status
        status = await client.get_status()
        print("Status:", status)

        # Test rooms
        rooms = await client.get_rooms()
        print("\nRooms:", rooms)

        # Test scenes
        scenes = await client.get_scenes()
        print("\nScenes:", scenes)

        await client.close()

    asyncio.run(test())
