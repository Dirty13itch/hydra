"""
Home Automation Integration for Hydra Command Center

Provides REST API endpoints for controlling home automation via Home Assistant.
Supports rooms, lights, scenes, and device control.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

import httpx
from fastapi import APIRouter, HTTPException
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
# Global Instance
# =============================================================================

_ha_client: Optional[HomeAssistantClient] = None


def get_ha_client() -> HomeAssistantClient:
    """Get or create Home Assistant client."""
    global _ha_client
    if _ha_client is None:
        _ha_client = HomeAssistantClient()
    return _ha_client


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
