"""
Hydra Autonomous Controller - Proactive Task Spawning System

This module implements the main autonomous loop that enables Hydra to:
1. PERCEIVE - Monitor system state from all sensors
2. DECIDE - Evaluate trigger rules against current state
3. ACT - Spawn tasks for triggered conditions
4. LEARN - Update memory with observations

The controller runs continuously, transforming Hydra from a reactive system
(responds to requests) to a proactive system (identifies and executes work).

Constitutional constraints are enforced for all autonomous actions.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import yaml

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Local imports
from hydra_tools.agent_scheduler import (
    get_scheduler,
    AgentPriority,
    AgentStatus,
)
from hydra_tools.constitution import get_enforcer
from hydra_tools.memory_architecture import get_memory_manager, MemoryTier

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class TriggerType(str, Enum):
    """Types of triggers for autonomous actions."""
    HEALTH = "health"           # Based on service/container health
    METRIC = "metric"           # Based on Prometheus metrics
    SCHEDULE = "schedule"       # Time-based (cron-like)
    EVENT = "event"             # Reactive to events
    BENCHMARK = "benchmark"     # Based on benchmark scores
    LEARNING = "learning"       # Learning/improvement triggers


@dataclass
class TriggerRule:
    """A rule that triggers autonomous action when conditions are met."""
    id: str
    name: str
    trigger_type: TriggerType
    condition: str
    action_type: str
    action_description: str
    priority: AgentPriority = AgentPriority.NORMAL
    cooldown_minutes: int = 15
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type.value,
            "condition": self.condition,
            "action_type": self.action_type,
            "action_description": self.action_description,
            "priority": self.priority.name,
            "cooldown_minutes": self.cooldown_minutes,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
        }


@dataclass
class SystemState:
    """Current state of the Hydra system."""
    timestamp: datetime
    containers: Dict[str, Any]
    prometheus_targets: Dict[str, Any]
    metrics: Dict[str, float]
    benchmarks: Dict[str, Any]
    memory_stats: Dict[str, Any]
    pending_tasks: List[Dict[str, Any]]
    recent_events: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "containers": self.containers,
            "prometheus_targets": self.prometheus_targets,
            "metrics": self.metrics,
            "benchmarks": self.benchmarks,
            "memory_stats": self.memory_stats,
            "pending_tasks_count": len(self.pending_tasks),
            "recent_events_count": len(self.recent_events),
        }


@dataclass
class AutonomousAction:
    """An action to be taken autonomously."""
    trigger_id: str
    trigger_name: str
    action_type: str
    description: str
    priority: AgentPriority
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


# =============================================================================
# Default Trigger Rules
# =============================================================================

DEFAULT_TRIGGER_RULES = [
    # Health-based triggers
    TriggerRule(
        id="health-001",
        name="Unhealthy Container",
        trigger_type=TriggerType.HEALTH,
        condition="container.status == 'unhealthy' for > 5 minutes",
        action_type="maintenance",
        action_description="Diagnose and attempt to fix unhealthy container",
        priority=AgentPriority.HIGH,
        cooldown_minutes=15,
    ),
    TriggerRule(
        id="health-002",
        name="Service Down",
        trigger_type=TriggerType.HEALTH,
        condition="prometheus_target.up == 0",
        action_type="monitoring",
        action_description="Investigate down service",
        priority=AgentPriority.CRITICAL,
        cooldown_minutes=5,
    ),
    TriggerRule(
        id="health-003",
        name="Container Restart Required",
        trigger_type=TriggerType.HEALTH,
        condition="container.restart_needed == true",
        action_type="maintenance",
        action_description="Restart container with constitutional protection",
        priority=AgentPriority.HIGH,
        cooldown_minutes=30,
    ),

    # Metric-based triggers
    TriggerRule(
        id="metric-001",
        name="High Disk Usage",
        trigger_type=TriggerType.METRIC,
        condition="disk_usage_percent > 85",
        action_type="maintenance",
        action_description="Run disk cleanup to free space",
        priority=AgentPriority.HIGH,
        cooldown_minutes=60,
    ),
    TriggerRule(
        id="metric-002",
        name="Slow Inference",
        trigger_type=TriggerType.METRIC,
        condition="avg_inference_latency_ms > 3000",
        action_type="research",
        action_description="Research inference optimization options",
        priority=AgentPriority.NORMAL,
        cooldown_minutes=120,
    ),
    TriggerRule(
        id="metric-003",
        name="High GPU Temperature",
        trigger_type=TriggerType.METRIC,
        condition="gpu_temp_celsius > 80",
        action_type="monitoring",
        action_description="Monitor GPU temperature and alert if sustained",
        priority=AgentPriority.HIGH,
        cooldown_minutes=10,
    ),

    # Benchmark-based triggers
    TriggerRule(
        id="bench-001",
        name="Benchmark Regression",
        trigger_type=TriggerType.BENCHMARK,
        condition="benchmark_score < previous_score - 5",
        action_type="llm",
        action_description="Analyze benchmark regression and propose fixes",
        priority=AgentPriority.HIGH,
        cooldown_minutes=60,
    ),
    TriggerRule(
        id="bench-002",
        name="Low Benchmark Score",
        trigger_type=TriggerType.BENCHMARK,
        condition="benchmark_score < 80",
        action_type="llm",
        action_description="Generate improvement proposals for low-scoring areas",
        priority=AgentPriority.NORMAL,
        cooldown_minutes=1440,  # Daily
    ),

    # Learning triggers
    TriggerRule(
        id="learn-001",
        name="Skill Extraction",
        trigger_type=TriggerType.LEARNING,
        condition="task_completed_successfully",
        action_type="llm",
        action_description="Extract reusable skill from completed task",
        priority=AgentPriority.LOW,
        cooldown_minutes=0,  # Run for every completion
    ),
    TriggerRule(
        id="learn-002",
        name="Memory Consolidation",
        trigger_type=TriggerType.SCHEDULE,
        condition="cron: 0 4 * * *",  # 4 AM daily
        action_type="maintenance",
        action_description="Consolidate and archive old memories",
        priority=AgentPriority.LOW,
        cooldown_minutes=1440,
    ),

    # Schedule-based triggers
    TriggerRule(
        id="sched-001",
        name="Daily Knowledge Refresh",
        trigger_type=TriggerType.SCHEDULE,
        condition="cron: 0 2 * * *",  # 2 AM daily
        action_type="deep_research",
        action_description="Research latest developments in AI and infrastructure",
        priority=AgentPriority.LOW,
        cooldown_minutes=1440,
    ),
    TriggerRule(
        id="sched-002",
        name="Weekly Self-Improvement",
        trigger_type=TriggerType.SCHEDULE,
        condition="cron: 0 3 * * 0",  # 3 AM Sunday
        action_type="llm",
        action_description="Run benchmarks and generate improvement proposals",
        priority=AgentPriority.LOW,
        cooldown_minutes=10080,  # Weekly
    ),
]


# =============================================================================
# Autonomous Controller
# =============================================================================

class AutonomousController:
    """
    Main control loop for proactive autonomous operation.

    The controller continuously:
    1. Perceives current system state
    2. Evaluates trigger rules
    3. Spawns tasks for triggered conditions
    4. Records actions to memory

    All actions are subject to constitutional constraints.
    """

    def __init__(
        self,
        rules_file: Optional[str] = None,
        check_interval_seconds: int = 30,
        api_base_url: str = "http://localhost:8700",
    ):
        self.api_base_url = api_base_url
        self.check_interval = check_interval_seconds
        self.rules_file = rules_file or "/data/autonomous/trigger_rules.yaml"

        # Load trigger rules
        self.rules: List[TriggerRule] = self._load_rules()

        # Get references to other systems
        self._scheduler = None
        self._enforcer = None
        self._memory = None

        # Controller state
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._last_state: Optional[SystemState] = None

        # Action history
        self._action_history: List[Dict[str, Any]] = []
        self._max_history = 1000

        # Stats
        self._stats = {
            "started_at": None,
            "checks_performed": 0,
            "actions_spawned": 0,
            "actions_blocked": 0,
            "errors": 0,
        }

        logger.info(f"AutonomousController initialized with {len(self.rules)} rules")

    @property
    def scheduler(self):
        if self._scheduler is None:
            self._scheduler = get_scheduler()
        return self._scheduler

    @property
    def enforcer(self):
        if self._enforcer is None:
            self._enforcer = get_enforcer()
        return self._enforcer

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_manager()
        return self._memory

    def _load_rules(self) -> List[TriggerRule]:
        """Load trigger rules from file or use defaults."""
        rules = []

        # Try to load from file
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r") as f:
                    data = yaml.safe_load(f)
                    for rule_data in data.get("rules", []):
                        rules.append(TriggerRule(
                            id=rule_data["id"],
                            name=rule_data["name"],
                            trigger_type=TriggerType(rule_data["trigger_type"]),
                            condition=rule_data["condition"],
                            action_type=rule_data["action_type"],
                            action_description=rule_data["action_description"],
                            priority=AgentPriority[rule_data.get("priority", "NORMAL")],
                            cooldown_minutes=rule_data.get("cooldown_minutes", 15),
                            enabled=rule_data.get("enabled", True),
                        ))
                logger.info(f"Loaded {len(rules)} rules from {self.rules_file}")
            except Exception as e:
                logger.warning(f"Error loading rules file: {e}, using defaults")

        # Use defaults if no file rules
        if not rules:
            rules = DEFAULT_TRIGGER_RULES.copy()
            self._save_rules(rules)

        return rules

    def _save_rules(self, rules: List[TriggerRule]):
        """Save trigger rules to file."""
        Path(self.rules_file).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "rules": [r.to_dict() for r in rules]
        }

        with open(self.rules_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    # =========================================================================
    # Perceive - Gather System State
    # =========================================================================

    async def perceive(self) -> SystemState:
        """Gather current system state from all sensors."""
        now = datetime.utcnow()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get container health
            try:
                resp = await client.get(f"{self.api_base_url}/container-health/")
                containers = resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                logger.warning(f"Error getting container health: {e}")
                containers = {"error": str(e)}

            # Get Prometheus targets
            try:
                resp = await client.get("http://192.168.1.244:9090/api/v1/targets")
                prom_data = resp.json() if resp.status_code == 200 else {}
                targets = prom_data.get("data", {}).get("activeTargets", [])
                prometheus_targets = {
                    "total": len(targets),
                    "up": sum(1 for t in targets if t.get("health") == "up"),
                    "down": [t.get("labels", {}).get("job") for t in targets if t.get("health") != "up"],
                }
            except Exception as e:
                logger.warning(f"Error getting Prometheus targets: {e}")
                prometheus_targets = {"error": str(e)}

            # Get key metrics
            metrics = {}
            try:
                # Inference latency
                resp = await client.get(f"{self.api_base_url}/diagnosis/inference")
                if resp.status_code == 200:
                    inference = resp.json()
                    if inference.get("latency_ms"):
                        metrics["avg_inference_latency_ms"] = inference["latency_ms"]
                    if inference.get("tokens_per_second"):
                        metrics["tokens_per_second"] = inference["tokens_per_second"]
            except Exception:
                pass

            try:
                # GPU metrics
                resp = await client.get(f"{self.api_base_url}/hardware/gpus")
                if resp.status_code == 200:
                    gpus = resp.json().get("gpus", [])
                    if gpus:
                        metrics["gpu_temp_celsius"] = max(g.get("temp_celsius", 0) for g in gpus)
                        metrics["gpu_vram_used_gb"] = sum(g.get("vram_used_gb", 0) for g in gpus)
            except Exception:
                pass

            # Get latest benchmarks
            try:
                resp = await client.get(f"{self.api_base_url}/self-improvement/benchmarks/latest")
                benchmarks = resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                benchmarks = {"error": str(e)}

            # Get memory stats
            try:
                memory_stats = await self.memory.get_stats()
            except Exception as e:
                memory_stats = {"error": str(e)}

            # Get pending tasks
            pending_tasks = self.scheduler.get_queue()

            # Get recent events from episodic memory
            try:
                recent_events = await self.memory.get_recent_episodes(limit=10)
                recent_events = [e.to_dict() for e in recent_events]
            except Exception:
                recent_events = []

        return SystemState(
            timestamp=now,
            containers=containers,
            prometheus_targets=prometheus_targets,
            metrics=metrics,
            benchmarks=benchmarks,
            memory_stats=memory_stats,
            pending_tasks=pending_tasks,
            recent_events=recent_events,
        )

    # =========================================================================
    # Decide - Evaluate Trigger Rules
    # =========================================================================

    async def decide(self, state: SystemState) -> List[AutonomousAction]:
        """Evaluate trigger rules and return actions to take."""
        actions = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check cooldown
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if datetime.utcnow() < cooldown_end:
                    continue

            # Evaluate the rule
            triggered, reason = self._evaluate_rule(rule, state)

            if triggered:
                # Check for duplicate pending action
                if self._is_duplicate_action(rule, actions):
                    continue

                actions.append(AutonomousAction(
                    trigger_id=rule.id,
                    trigger_name=rule.name,
                    action_type=rule.action_type,
                    description=rule.action_description,
                    priority=rule.priority,
                    payload=self._build_payload(rule, state, reason),
                    reason=reason,
                ))

        return actions

    def _evaluate_rule(self, rule: TriggerRule, state: SystemState) -> Tuple[bool, str]:
        """Evaluate a single rule against current state."""

        # Health-based triggers
        if rule.trigger_type == TriggerType.HEALTH:
            if "unhealthy" in rule.condition.lower():
                # Check for unhealthy containers
                containers = state.containers.get("containers", [])
                for c in containers:
                    if c.get("health") == "unhealthy":
                        return True, f"Container {c.get('name')} is unhealthy"

            if "prometheus_target" in rule.condition.lower():
                # Check for down Prometheus targets
                down = state.prometheus_targets.get("down", [])
                if down:
                    return True, f"Services down: {', '.join(down)}"

        # Metric-based triggers
        elif rule.trigger_type == TriggerType.METRIC:
            if "disk_usage_percent" in rule.condition:
                # Would need to add disk metrics to perceive
                pass

            if "avg_inference_latency_ms" in rule.condition:
                latency = state.metrics.get("avg_inference_latency_ms", 0)
                if latency > 3000:
                    return True, f"Inference latency {latency}ms exceeds threshold"

            if "gpu_temp_celsius" in rule.condition:
                temp = state.metrics.get("gpu_temp_celsius", 0)
                if temp > 80:
                    return True, f"GPU temperature {temp}C exceeds threshold"

        # Benchmark-based triggers
        elif rule.trigger_type == TriggerType.BENCHMARK:
            score = state.benchmarks.get("overall_score", 100)

            if "benchmark_score < 80" in rule.condition:
                if score < 80:
                    return True, f"Benchmark score {score}% below threshold"

            if "regression" in rule.condition.lower():
                # Would need to track previous scores
                pass

        # Schedule-based triggers (simple implementation)
        elif rule.trigger_type == TriggerType.SCHEDULE:
            # Parse cron-like condition
            if "cron:" in rule.condition:
                # Simplified: check if we're in the right hour
                cron_parts = rule.condition.replace("cron:", "").strip().split()
                if len(cron_parts) >= 2:
                    minute, hour = int(cron_parts[0]), int(cron_parts[1])
                    now = datetime.utcnow()
                    if now.hour == hour and now.minute == minute:
                        return True, f"Scheduled trigger at {hour:02d}:{minute:02d}"

        return False, ""

    def _is_duplicate_action(self, rule: TriggerRule, pending_actions: List[AutonomousAction]) -> bool:
        """Check if this action is already pending."""
        # Check in current batch
        for action in pending_actions:
            if action.trigger_id == rule.id:
                return True

        # Check in scheduler queue
        for task in self.scheduler.get_queue():
            if f"Autonomous: {rule.name}" in task.get("description", ""):
                return True

        return False

    def _build_payload(self, rule: TriggerRule, state: SystemState, reason: str) -> Dict[str, Any]:
        """Build action payload with context."""
        return {
            "trigger_id": rule.id,
            "trigger_name": rule.name,
            "reason": reason,
            "system_state_summary": {
                "containers": state.containers.get("summary", {}),
                "prometheus": state.prometheus_targets,
                "metrics": state.metrics,
            },
            "triggered_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Act - Spawn Tasks
    # =========================================================================

    async def act(self, actions: List[AutonomousAction]) -> List[str]:
        """Spawn tasks for each action, respecting constitutional constraints."""
        spawned_task_ids = []

        for action in actions:
            # Constitutional check
            check = self.enforcer.check_operation(
                operation_type="autonomous_spawn",
                target_resource=action.action_type,
                details={
                    "trigger_id": action.trigger_id,
                    "reason": action.reason,
                }
            )

            if not check.allowed:
                logger.warning(f"Action blocked by constitution: {check.message}")
                self.enforcer.log_action(
                    operation_type="autonomous_spawn",
                    target_resource=action.action_type,
                    result="blocked",
                    constraint_id=check.constraint_id,
                    constraint_rule=check.constraint_rule,
                    details={"trigger": action.trigger_name, "reason": action.reason}
                )
                self._stats["actions_blocked"] += 1
                continue

            try:
                # Schedule the task
                task_id = await self.scheduler.schedule(
                    agent_type=action.action_type,
                    description=f"Autonomous: {action.trigger_name} - {action.description}",
                    payload=action.payload,
                    priority=action.priority,
                    timeout_seconds=600,  # 10 minute default
                )

                # Update rule state
                rule = next((r for r in self.rules if r.id == action.trigger_id), None)
                if rule:
                    rule.last_triggered = datetime.utcnow()
                    rule.trigger_count += 1

                # Log success
                self.enforcer.log_action(
                    operation_type="autonomous_spawn",
                    target_resource=action.action_type,
                    result="success",
                    details={
                        "task_id": task_id,
                        "trigger": action.trigger_name,
                        "reason": action.reason,
                    }
                )

                # Record to history
                self._action_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "task_id": task_id,
                    "trigger_id": action.trigger_id,
                    "trigger_name": action.trigger_name,
                    "action_type": action.action_type,
                    "reason": action.reason,
                    "priority": action.priority.name,
                })

                spawned_task_ids.append(task_id)
                self._stats["actions_spawned"] += 1
                logger.info(f"Spawned autonomous task {task_id}: {action.trigger_name}")

            except Exception as e:
                logger.error(f"Error spawning action {action.trigger_name}: {e}")
                self._stats["errors"] += 1

        # Trim history
        if len(self._action_history) > self._max_history:
            self._action_history = self._action_history[-self._max_history:]

        return spawned_task_ids

    # =========================================================================
    # Learn - Update Memory
    # =========================================================================

    async def learn(self, state: SystemState, actions: List[AutonomousAction]):
        """Update memory with observations and actions."""
        try:
            # Record state observation as episodic memory
            if actions:  # Only record if we took action
                for action in actions:
                    await self.memory.record_episode(
                        content=f"Autonomous trigger: {action.trigger_name}. Reason: {action.reason}. Action: {action.action_type}",
                        event_type="autonomous_action",
                        outcome=f"Spawned {action.action_type} task",
                        tags=["autonomous", action.action_type, action.trigger_id],
                    )

            # Store system state summary as semantic memory if interesting
            if state.prometheus_targets.get("down"):
                await self.memory.store_fact(
                    content=f"Services down at {state.timestamp}: {state.prometheus_targets['down']}",
                    domain="infrastructure",
                    confidence=1.0,
                    source="autonomous_observation",
                    tags=["service_down", "infrastructure"],
                )

        except Exception as e:
            logger.warning(f"Error updating memory: {e}")

    # =========================================================================
    # Main Loop
    # =========================================================================

    async def _main_loop(self):
        """Main autonomous loop - runs continuously."""
        logger.info("Autonomous controller main loop started")

        while self._running:
            try:
                # 1. Perceive - gather current state
                state = await self.perceive()
                self._last_state = state

                # 2. Decide - evaluate triggers
                actions = await self.decide(state)

                # 3. Act - spawn tasks
                if actions:
                    await self.act(actions)

                # 4. Learn - update memory
                await self.learn(state, actions)

                self._stats["checks_performed"] += 1

            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}")
                self._stats["errors"] += 1

            # Wait before next check
            await asyncio.sleep(self.check_interval)

        logger.info("Autonomous controller main loop stopped")

    async def start(self):
        """Start the autonomous controller."""
        if self._running:
            return

        # Start the scheduler if not running
        if not self.scheduler._running_flag:
            await self.scheduler.start()

        self._running = True
        self._stats["started_at"] = datetime.utcnow().isoformat()
        self._loop_task = asyncio.create_task(self._main_loop())
        logger.info("Autonomous controller started")

    async def stop(self):
        """Stop the autonomous controller."""
        self._running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        logger.info("Autonomous controller stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get controller status."""
        return {
            "running": self._running,
            "stats": self._stats,
            "rules_count": len(self.rules),
            "rules_enabled": sum(1 for r in self.rules if r.enabled),
            "check_interval_seconds": self.check_interval,
            "last_state": self._last_state.to_dict() if self._last_state else None,
        }

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all trigger rules."""
        return [r.to_dict() for r in self.rules]

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get action history."""
        return self._action_history[-limit:]

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a trigger rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = True
                self._save_rules(self.rules)
                return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a trigger rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = False
                self._save_rules(self.rules)
                return True
        return False


# =============================================================================
# Global Instance
# =============================================================================

_controller: Optional[AutonomousController] = None


def get_controller() -> AutonomousController:
    """Get or create the global autonomous controller."""
    global _controller
    if _controller is None:
        _controller = AutonomousController()
    return _controller


# =============================================================================
# FastAPI Router
# =============================================================================

class SpawnTaskRequest(BaseModel):
    """Request to spawn an autonomous task."""
    task_type: str
    description: str
    trigger: str
    payload: Dict[str, Any] = {}
    priority: str = "normal"


def create_autonomous_router() -> APIRouter:
    """Create FastAPI router for autonomous controller endpoints."""
    router = APIRouter(prefix="/autonomous", tags=["autonomous"])

    @router.get("/status")
    async def get_status():
        """Get autonomous controller status."""
        controller = get_controller()
        return controller.get_status()

    @router.post("/start")
    async def start_controller():
        """Start the autonomous controller."""
        controller = get_controller()
        await controller.start()
        return {"status": "started"}

    @router.post("/stop")
    async def stop_controller():
        """Stop the autonomous controller."""
        controller = get_controller()
        await controller.stop()
        return {"status": "stopped"}

    @router.get("/rules")
    async def get_rules():
        """Get all trigger rules."""
        controller = get_controller()
        return {"rules": controller.get_rules()}

    @router.post("/rules/{rule_id}/enable")
    async def enable_rule(rule_id: str):
        """Enable a trigger rule."""
        controller = get_controller()
        if controller.enable_rule(rule_id):
            return {"status": "enabled", "rule_id": rule_id}
        raise HTTPException(404, f"Rule {rule_id} not found")

    @router.post("/rules/{rule_id}/disable")
    async def disable_rule(rule_id: str):
        """Disable a trigger rule."""
        controller = get_controller()
        if controller.disable_rule(rule_id):
            return {"status": "disabled", "rule_id": rule_id}
        raise HTTPException(404, f"Rule {rule_id} not found")

    @router.get("/history")
    async def get_history(limit: int = 100):
        """Get autonomous action history."""
        controller = get_controller()
        return {"history": controller.get_history(limit)}

    @router.post("/spawn")
    async def spawn_task(request: SpawnTaskRequest):
        """
        Manually spawn an autonomous task.

        This bypasses trigger rules but still respects constitutional constraints.
        """
        controller = get_controller()

        # Map priority string to enum
        priority_map = {
            "critical": AgentPriority.CRITICAL,
            "high": AgentPriority.HIGH,
            "normal": AgentPriority.NORMAL,
            "low": AgentPriority.LOW,
            "idle": AgentPriority.IDLE,
        }
        priority = priority_map.get(request.priority.lower(), AgentPriority.NORMAL)

        # Create action
        action = AutonomousAction(
            trigger_id="manual",
            trigger_name=f"Manual: {request.trigger}",
            action_type=request.task_type,
            description=request.description,
            priority=priority,
            payload=request.payload,
            reason=request.trigger,
        )

        # Spawn via controller (respects constitution)
        task_ids = await controller.act([action])

        if task_ids:
            return {"status": "spawned", "task_id": task_ids[0]}
        raise HTTPException(403, "Task spawn blocked by constitutional constraints")

    @router.get("/state")
    async def get_current_state():
        """Get current system state as perceived by the controller."""
        controller = get_controller()
        if controller._last_state:
            return controller._last_state.to_dict()
        # Force a perception if no cached state
        state = await controller.perceive()
        return state.to_dict()

    @router.post("/perceive")
    async def force_perceive():
        """Force a perception cycle."""
        controller = get_controller()
        state = await controller.perceive()
        return state.to_dict()

    @router.post("/evaluate")
    async def evaluate_rules():
        """Evaluate all rules against current state without acting."""
        controller = get_controller()
        state = await controller.perceive()
        actions = await controller.decide(state)
        return {
            "state": state.to_dict(),
            "triggered_rules": [
                {
                    "trigger_id": a.trigger_id,
                    "trigger_name": a.trigger_name,
                    "action_type": a.action_type,
                    "reason": a.reason,
                    "priority": a.priority.name,
                }
                for a in actions
            ],
            "would_spawn": len(actions),
        }

    return router
