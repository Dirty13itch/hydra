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

    async def _announce_presence_change(self, state: PresenceState) -> Optional[str]:
        """Announce presence change via voice synthesis."""
        announcements = {
            PresenceState.HOME: "Welcome back. Hydra systems are now at full capacity.",
            PresenceState.AWAY: "Away mode activated. Systems entering power saving mode.",
            PresenceState.SLEEP: "Sleep mode activated. Good night.",
            PresenceState.VACATION: "Vacation mode enabled. Systems will operate at minimal capacity.",
        }
        text = announcements.get(state, f"Presence mode changed to {state.value}.")

        try:
            response = await self.client.post(
                f"{self.hydra_api_url}/voice/speak",
                json={"text": text, "voice": "af_sky"},  # Use default Kokoro voice
                timeout=10,
            )
            if response.status_code == 200:
                return f"Announced: {text}"
            return f"Voice announcement failed: {response.status_code}"
        except Exception as e:
            return f"Voice announcement error: {str(e)}"

    async def _set_gpu_power_limit(self, host: str, power_limit: int) -> Optional[str]:
        """Set GPU power limit on a node via SSH."""
        try:
            cmd = f"ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o UserKnownHostsFile=/dev/null typhon@{host} 'sudo nvidia-smi -pl {power_limit}'"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

            if proc.returncode == 0:
                return f"Set {host} GPU power to {power_limit}W"
            else:
                return f"Failed on {host}: {stderr.decode().strip()}"
        except asyncio.TimeoutError:
            return f"Timeout setting power on {host}"
        except Exception as e:
            return f"Error on {host}: {str(e)}"

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

        # 3. Adjust GPU power limits via SSH
        # Power limits per node (adjust as needed for each GPU)
        gpu_hosts = {
            "192.168.1.250": config.gpu_power_limit,  # hydra-ai: RTX 5090 + RTX 4090
            "192.168.1.203": min(config.gpu_power_limit, 250),  # hydra-compute: 2x RTX 5070 Ti
        }

        for host, power in gpu_hosts.items():
            result = await self._set_gpu_power_limit(host, power)
            if result:
                results["actions"].append(result)

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

        # 5. Voice announcement (optional, non-blocking)
        try:
            announcement_result = await self._announce_presence_change(state)
            if announcement_result:
                results["actions"].append(announcement_result)
        except Exception as e:
            results["actions"].append(f"Voice announcement skipped: {e}")

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
# Presence Triggers (Real-time Entity Monitoring)
# =============================================================================

@dataclass
class PresenceTrigger:
    """Defines a trigger for presence state changes."""
    entity_id: str
    condition: str  # "equals", "not_equals", "any_of", "changed_to"
    target_value: Any  # Value or list of values to match
    target_state: PresenceState
    priority: int = 0  # Higher priority wins


class PresenceTriggerEngine:
    """
    Monitors entity state changes and triggers presence mode changes.

    Connects to EntityStateTracker and watches for changes that match
    defined triggers.
    """

    def __init__(self, manager: PresenceManager):
        self.manager = manager
        self.triggers: List[PresenceTrigger] = []
        self._running = False
        self._last_trigger_time = None
        self._cooldown_seconds = 30  # Prevent rapid state changes

        # Default triggers
        self._register_default_triggers()

    def _register_default_triggers(self):
        """Register default presence triggers."""
        # Person entities - home/away
        self.triggers.append(PresenceTrigger(
            entity_id="person.*",  # Wildcard for all persons
            condition="equals",
            target_value="home",
            target_state=PresenceState.HOME,
            priority=10,
        ))
        self.triggers.append(PresenceTrigger(
            entity_id="person.*",
            condition="equals",
            target_value="not_home",
            target_state=PresenceState.AWAY,
            priority=5,  # Lower priority - only if no one is home
        ))

        # Input select for manual mode override
        self.triggers.append(PresenceTrigger(
            entity_id="input_select.presence_mode",
            condition="any_of",
            target_value=["home", "away", "sleep", "vacation"],
            target_state=PresenceState.HOME,  # Will be resolved dynamically
            priority=100,  # Highest priority - manual override
        ))

        # Time-based sleep mode (via HA binary sensor or time)
        self.triggers.append(PresenceTrigger(
            entity_id="binary_sensor.night_mode",
            condition="equals",
            target_value="on",
            target_state=PresenceState.SLEEP,
            priority=20,
        ))

        # Motion sensors - detect activity
        self.triggers.append(PresenceTrigger(
            entity_id="binary_sensor.*_motion",  # Any motion sensor
            condition="equals",
            target_value="on",
            target_state=PresenceState.HOME,
            priority=3,  # Low priority - supplemental detection
        ))

        # Door sensors - detect arrivals
        self.triggers.append(PresenceTrigger(
            entity_id="binary_sensor.*_door",  # Front door, garage door, etc.
            condition="changed_to",
            target_value="on",
            target_state=PresenceState.HOME,
            priority=8,  # Medium priority
        ))

        # Media player - entertainment mode indicator
        self.triggers.append(PresenceTrigger(
            entity_id="media_player.*",  # Any media player
            condition="any_of",
            target_value=["playing", "paused"],
            target_state=PresenceState.HOME,
            priority=4,  # Low-medium priority
        ))

        # Workday binary sensor - work schedule
        self.triggers.append(PresenceTrigger(
            entity_id="binary_sensor.workday",
            condition="equals",
            target_value="on",
            target_state=PresenceState.HOME,
            priority=2,  # Very low - just a hint
        ))

        # Vacation mode calendar
        self.triggers.append(PresenceTrigger(
            entity_id="calendar.vacation",
            condition="equals",
            target_value="on",
            target_state=PresenceState.VACATION,
            priority=50,  # High priority - explicit vacation
        ))

    def add_trigger(self, trigger: PresenceTrigger):
        """Add a custom trigger."""
        self.triggers.append(trigger)
        # Sort by priority (highest first)
        self.triggers.sort(key=lambda t: t.priority, reverse=True)

    def remove_trigger(self, entity_id: str):
        """Remove triggers for an entity."""
        self.triggers = [t for t in self.triggers if t.entity_id != entity_id]

    def _matches_pattern(self, entity_id: str, pattern: str) -> bool:
        """Check if entity_id matches a pattern (supports * wildcard)."""
        if "*" in pattern:
            import fnmatch
            return fnmatch.fnmatch(entity_id, pattern)
        return entity_id == pattern

    def _evaluate_condition(
        self,
        trigger: PresenceTrigger,
        current_value: str,
        previous_value: Optional[str] = None,
    ) -> bool:
        """Evaluate if a trigger condition is met."""
        if trigger.condition == "equals":
            return current_value == trigger.target_value
        elif trigger.condition == "not_equals":
            return current_value != trigger.target_value
        elif trigger.condition == "any_of":
            return current_value in trigger.target_value
        elif trigger.condition == "changed_to":
            return current_value == trigger.target_value and previous_value != trigger.target_value
        return False

    async def on_state_change(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle state change event from Home Assistant.

        Returns trigger results if a presence change was triggered.
        """
        data = event.get("data", {})
        entity_id = data.get("entity_id", "")
        new_state = data.get("new_state", {})
        old_state = data.get("old_state", {})

        current_value = new_state.get("state") if new_state else None
        previous_value = old_state.get("state") if old_state else None

        if not current_value:
            return None

        # Check cooldown
        if self._last_trigger_time:
            elapsed = (datetime.utcnow() - self._last_trigger_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                return None

        # Find matching triggers (sorted by priority)
        for trigger in self.triggers:
            if not self._matches_pattern(entity_id, trigger.entity_id):
                continue

            if self._evaluate_condition(trigger, current_value, previous_value):
                # Determine target state
                target_state = trigger.target_state

                # Special handling for input_select
                if trigger.entity_id == "input_select.presence_mode":
                    try:
                        target_state = PresenceState(current_value.lower())
                    except ValueError:
                        continue

                # Check if state actually changed
                current_presence = self.manager._current_state
                if target_state == current_presence:
                    return None

                # Apply new presence state
                self._last_trigger_time = datetime.utcnow()
                results = await self.manager.apply_presence_config(target_state)

                return {
                    "trigger_entity": entity_id,
                    "trigger_value": current_value,
                    "previous_value": previous_value,
                    "new_presence": target_state.value,
                    "results": results,
                }

        return None

    def get_triggers(self) -> List[Dict[str, Any]]:
        """Get list of configured triggers."""
        return [
            {
                "entity_id": t.entity_id,
                "condition": t.condition,
                "target_value": t.target_value,
                "target_state": t.target_state.value,
                "priority": t.priority,
            }
            for t in self.triggers
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get trigger engine status."""
        return {
            "running": self._running,
            "trigger_count": len(self.triggers),
            "last_trigger_time": self._last_trigger_time.isoformat() + "Z" if self._last_trigger_time else None,
            "cooldown_seconds": self._cooldown_seconds,
        }


# =============================================================================
# Global Instance
# =============================================================================

_presence_manager: Optional[PresenceManager] = None
_trigger_engine: Optional[PresenceTriggerEngine] = None


def get_presence_manager() -> PresenceManager:
    """Get or create presence manager."""
    global _presence_manager
    if _presence_manager is None:
        _presence_manager = PresenceManager()
    return _presence_manager


def get_trigger_engine() -> PresenceTriggerEngine:
    """Get or create trigger engine."""
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = PresenceTriggerEngine(get_presence_manager())
    return _trigger_engine


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

    # =========================================================================
    # Trigger Engine Endpoints
    # =========================================================================

    @router.get("/triggers")
    async def get_triggers():
        """Get all configured presence triggers."""
        engine = get_trigger_engine()
        return {
            "triggers": engine.get_triggers(),
            "status": engine.get_status(),
        }

    @router.get("/triggers/status")
    async def get_trigger_status():
        """Get trigger engine status."""
        engine = get_trigger_engine()
        return engine.get_status()

    @router.post("/triggers/add")
    async def add_trigger(
        entity_id: str,
        condition: str,
        target_value: str,
        target_state: str,
        priority: int = 0,
    ):
        """Add a custom presence trigger."""
        try:
            state = PresenceState(target_state.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target_state: {target_state}. Valid: {[s.value for s in PresenceState]}"
            )

        if condition not in ["equals", "not_equals", "any_of", "changed_to"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid condition: {condition}. Valid: equals, not_equals, any_of, changed_to"
            )

        # Parse target_value for any_of
        parsed_value = target_value
        if condition == "any_of":
            parsed_value = [v.strip() for v in target_value.split(",")]

        trigger = PresenceTrigger(
            entity_id=entity_id,
            condition=condition,
            target_value=parsed_value,
            target_state=state,
            priority=priority,
        )

        engine = get_trigger_engine()
        engine.add_trigger(trigger)

        return {
            "success": True,
            "trigger": {
                "entity_id": entity_id,
                "condition": condition,
                "target_value": parsed_value,
                "target_state": target_state,
                "priority": priority,
            }
        }

    @router.delete("/triggers/{entity_id:path}")
    async def remove_trigger(entity_id: str):
        """Remove triggers for an entity."""
        engine = get_trigger_engine()
        engine.remove_trigger(entity_id)
        return {"success": True, "removed_entity": entity_id}

    @router.post("/triggers/test")
    async def test_trigger(entity_id: str, state_value: str):
        """Test a trigger with a simulated state change event."""
        engine = get_trigger_engine()

        # Create simulated event
        event = {
            "event_type": "state_changed",
            "data": {
                "entity_id": entity_id,
                "new_state": {"state": state_value},
                "old_state": {"state": None},
            }
        }

        result = await engine.on_state_change(event)
        return {
            "triggered": result is not None,
            "result": result,
        }

    # =========================================================================
    # Prometheus Metrics Endpoint
    # =========================================================================

    @router.get("/metrics")
    async def get_presence_metrics():
        """
        Get Prometheus-compatible metrics for presence automation.

        Returns metrics in Prometheus text format.
        """
        manager = get_presence_manager()
        engine = get_trigger_engine()
        status = await manager.get_status()
        trigger_status = engine.get_status()

        # Calculate time since last state change
        last_change = datetime.fromisoformat(status["last_state_change"].rstrip("Z"))
        seconds_in_state = (datetime.utcnow() - last_change).total_seconds()

        # State value for metrics (home=1, away=2, sleep=3, vacation=4)
        state_values = {"home": 1, "away": 2, "sleep": 3, "vacation": 4}
        state_value = state_values.get(status["current_state"], 0)

        # Build Prometheus metrics
        lines = [
            "# HELP hydra_presence_state Current presence state (1=home, 2=away, 3=sleep, 4=vacation)",
            "# TYPE hydra_presence_state gauge",
            f'hydra_presence_state{{state="{status["current_state"]}"}} {state_value}',
            "",
            "# HELP hydra_presence_seconds_in_state Seconds in current presence state",
            "# TYPE hydra_presence_seconds_in_state gauge",
            f"hydra_presence_seconds_in_state {seconds_in_state:.0f}",
            "",
            "# HELP hydra_presence_trigger_count Total number of configured triggers",
            "# TYPE hydra_presence_trigger_count gauge",
            f"hydra_presence_trigger_count {trigger_status['trigger_count']}",
            "",
            "# HELP hydra_presence_gpu_power_limit_watts Target GPU power limit in watts",
            "# TYPE hydra_presence_gpu_power_limit_watts gauge",
            f"hydra_presence_gpu_power_limit_watts {status['config']['gpu_power_limit']}",
            "",
            "# HELP hydra_presence_inference_enabled Whether inference is enabled (1=yes, 0=no)",
            "# TYPE hydra_presence_inference_enabled gauge",
            f"hydra_presence_inference_enabled {1 if status['config']['inference_enabled'] else 0}",
            "",
            "# HELP hydra_presence_ha_configured Whether Home Assistant is configured (1=yes, 0=no)",
            "# TYPE hydra_presence_ha_configured gauge",
            f"hydra_presence_ha_configured {1 if status['ha_configured'] else 0}",
        ]

        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

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
