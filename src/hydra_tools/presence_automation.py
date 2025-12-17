"""
Home Assistant Presence Automation for Hydra

Adjusts cluster behavior based on presence state:
- Away Mode: Reduce inference power limits, pause non-essential services
- Home Mode: Full inference capacity, enable all services
- Sleep Mode: Minimal operation, health monitoring only

Integrates with Home Assistant via REST API.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class PresenceState(str, Enum):
    """Presence states."""
    HOME = "home"
    AWAY = "away"
    SLEEP = "sleep"
    VACATION = "vacation"


@dataclass
class PresenceConfig:
    """Configuration for each presence state."""
    state: PresenceState
    gpu_power_limit: int  # Watts
    inference_enabled: bool
    container_policy: str  # "all", "essential", "minimal"
    monitoring_interval: int  # seconds


# Default configurations per state
DEFAULT_CONFIGS = {
    PresenceState.HOME: PresenceConfig(
        state=PresenceState.HOME,
        gpu_power_limit=450,  # Full power
        inference_enabled=True,
        container_policy="all",
        monitoring_interval=60,
    ),
    PresenceState.AWAY: PresenceConfig(
        state=PresenceState.AWAY,
        gpu_power_limit=200,  # Reduced power
        inference_enabled=True,
        container_policy="essential",
        monitoring_interval=300,
    ),
    PresenceState.SLEEP: PresenceConfig(
        state=PresenceState.SLEEP,
        gpu_power_limit=100,  # Minimal power
        inference_enabled=False,
        container_policy="minimal",
        monitoring_interval=600,
    ),
    PresenceState.VACATION: PresenceConfig(
        state=PresenceState.VACATION,
        gpu_power_limit=100,
        inference_enabled=False,
        container_policy="minimal",
        monitoring_interval=3600,
    ),
}


# Essential containers (always running)
ESSENTIAL_CONTAINERS = [
    "hydra-prometheus",
    "hydra-grafana",
    "hydra-loki",
    "hydra-alertmanager",
    "hydra-postgres",
    "hydra-redis",
    "hydra-qdrant",
    "hydra-n8n",
    "homeassistant",
    "adguard",
]

# Minimal containers (health monitoring only)
MINIMAL_CONTAINERS = [
    "hydra-prometheus",
    "hydra-alertmanager",
    "hydra-postgres",
    "adguard",
]


class PresenceManager:
    """Manages presence-based automation."""

    def __init__(
        self,
        ha_url: str = None,
        ha_token: str = None,
        hydra_api_url: str = "http://192.168.1.244:8700",
    ):
        self.ha_url = ha_url or os.getenv("HA_URL", "http://192.168.1.244:8123")
        self.ha_token = ha_token or os.getenv("HA_TOKEN", "")
        self.hydra_api_url = hydra_api_url
        self._client = None
        self._current_state = PresenceState.HOME
        self._last_state_change = datetime.utcnow()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_presence_from_ha(self) -> Optional[PresenceState]:
        """
        Get presence state from Home Assistant.

        Looks for common presence entities:
        - person.* entities
        - device_tracker.* entities
        - input_select.presence_mode
        """
        if not self.ha_token:
            logger.warning("No HA_TOKEN configured, using default HOME state")
            return None

        try:
            # Try to get presence mode input_select
            response = await self.client.get(
                f"{self.ha_url}/api/states/input_select.presence_mode",
                headers={"Authorization": f"Bearer {self.ha_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                state = data.get("state", "home").lower()
                return PresenceState(state) if state in PresenceState.__members__ else PresenceState.HOME

            # Fallback: check person entities
            response = await self.client.get(
                f"{self.ha_url}/api/states",
                headers={"Authorization": f"Bearer {self.ha_token}"},
            )

            if response.status_code == 200:
                states = response.json()
                for entity in states:
                    if entity["entity_id"].startswith("person."):
                        if entity["state"] == "home":
                            return PresenceState.HOME

                # If no person is home
                return PresenceState.AWAY

        except Exception as e:
            logger.error(f"Error getting HA presence: {e}")
            return None

        return PresenceState.HOME

    async def apply_presence_config(self, state: PresenceState) -> Dict[str, Any]:
        """Apply configuration for the given presence state."""
        config = DEFAULT_CONFIGS[state]
        results = {
            "state": state.value,
            "actions": [],
        }

        # 1. Record state change
        self._current_state = state
        self._last_state_change = datetime.utcnow()
        results["actions"].append(f"Set presence state to {state.value}")

        # 2. Log to activity system
        try:
            await self.client.post(
                f"{self.hydra_api_url}/activity/log",
                json={
                    "action_type": "presence_change",
                    "component": "presence_automation",
                    "description": f"Presence changed to {state.value}",
                    "metadata": {"config": config.__dict__},
                },
            )
            results["actions"].append("Logged presence change to activity system")
        except Exception as e:
            results["actions"].append(f"Failed to log activity: {e}")

        # 3. Adjust GPU power limits (would need SSH access)
        # This is a placeholder - actual implementation would SSH to nodes
        results["actions"].append(f"GPU power limit target: {config.gpu_power_limit}W")

        # 4. Store presence state in memory system
        try:
            await self.client.post(
                f"{self.hydra_api_url}/memory/episodic",
                params={
                    "content": f"Presence changed to {state.value}",
                    "event_type": "presence_change",
                    "outcome": f"Applied {state.value} configuration",
                },
            )
            results["actions"].append("Recorded presence change in episodic memory")
        except Exception as e:
            results["actions"].append(f"Failed to record memory: {e}")

        return results

    async def get_status(self) -> Dict[str, Any]:
        """Get current presence status."""
        return {
            "current_state": self._current_state.value,
            "last_state_change": self._last_state_change.isoformat() + "Z",
            "config": DEFAULT_CONFIGS[self._current_state].__dict__,
            "ha_configured": bool(self.ha_token),
        }

    async def sync_with_ha(self) -> Dict[str, Any]:
        """Sync presence state with Home Assistant."""
        ha_state = await self.get_presence_from_ha()

        if ha_state is None:
            return {
                "status": "skipped",
                "reason": "Could not determine HA presence state",
            }

        if ha_state != self._current_state:
            results = await self.apply_presence_config(ha_state)
            return {
                "status": "changed",
                "previous_state": self._current_state.value,
                "new_state": ha_state.value,
                "results": results,
            }

        return {
            "status": "unchanged",
            "current_state": self._current_state.value,
        }


# =============================================================================
# Global Instance
# =============================================================================

_presence_manager: Optional[PresenceManager] = None


def get_presence_manager() -> PresenceManager:
    """Get or create presence manager."""
    global _presence_manager
    if _presence_manager is None:
        _presence_manager = PresenceManager()
    return _presence_manager


# =============================================================================
# FastAPI Router
# =============================================================================

def create_presence_router() -> APIRouter:
    """Create FastAPI router for presence endpoints."""
    router = APIRouter(prefix="/presence", tags=["presence"])

    @router.get("/status")
    async def get_status():
        """Get current presence status."""
        manager = get_presence_manager()
        return await manager.get_status()

    @router.post("/sync")
    async def sync_presence():
        """Sync presence state with Home Assistant."""
        manager = get_presence_manager()
        return await manager.sync_with_ha()

    @router.post("/set/{state}")
    async def set_presence(state: str):
        """Manually set presence state."""
        try:
            presence_state = PresenceState(state.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state: {state}. Valid: {[s.value for s in PresenceState]}"
            )

        manager = get_presence_manager()
        results = await manager.apply_presence_config(presence_state)
        return results

    @router.get("/configs")
    async def get_configs():
        """Get presence configurations."""
        return {
            state.value: {
                "gpu_power_limit": config.gpu_power_limit,
                "inference_enabled": config.inference_enabled,
                "container_policy": config.container_policy,
                "monitoring_interval": config.monitoring_interval,
            }
            for state, config in DEFAULT_CONFIGS.items()
        }

    return router


if __name__ == "__main__":
    import asyncio

    async def test():
        manager = PresenceManager()

        # Test status
        status = await manager.get_status()
        print("Status:", status)

        # Test setting presence
        results = await manager.apply_presence_config(PresenceState.AWAY)
        print("\nSet to AWAY:", results)

        status = await manager.get_status()
        print("\nNew status:", status)

        await manager.close()

    asyncio.run(test())
