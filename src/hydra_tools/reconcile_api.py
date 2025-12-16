"""
Reconcile API Router

Exposes cluster state reconciliation capabilities via the Hydra Tools API.
Uses the hydra_reconcile module for state management and drift detection.

Endpoints:
- /reconcile/state - Get current cluster state
- /reconcile/drift - Detect drift from desired state
- /reconcile/plan - Generate reconciliation plan
- /reconcile/apply - Apply reconciliation (with dry-run support)
- /reconcile/desired - Manage desired state configuration
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


# Node configuration
NODES = {
    "hydra-ai": {
        "ip": "192.168.1.250",
        "user": "typhon",
        "os_type": "nixos",
    },
    "hydra-compute": {
        "ip": "192.168.1.203",
        "user": "typhon",
        "os_type": "nixos",
    },
    "hydra-storage": {
        "ip": "192.168.1.244",
        "user": "root",
        "os_type": "unraid",
    },
}

CRITICAL_SERVICES = {"tabbyapi", "litellm", "postgres", "qdrant", "redis", "ollama"}


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DriftSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ServiceState(BaseModel):
    """State of a single service."""
    name: str
    node: str
    status: ServiceStatus
    port: Optional[int] = None
    uptime: Optional[str] = None


class NodeState(BaseModel):
    """State of a cluster node."""
    name: str
    ip: str
    status: NodeStatus
    os_type: str
    services: List[ServiceState] = []
    gpu_count: int = 0
    gpu_temps: List[float] = []
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0


class ClusterState(BaseModel):
    """Current state of the cluster."""
    nodes: List[NodeState]
    timestamp: str
    overall_status: NodeStatus


class Drift(BaseModel):
    """A detected drift from desired state."""
    service: str
    node: str
    drift_type: str
    expected: Any
    actual: Any
    severity: DriftSeverity
    auto_fixable: bool


class ReconcileAction(BaseModel):
    """An action to fix drift."""
    action_type: str
    target: str
    node: str
    command: Optional[str] = None


class ReconcilePlan(BaseModel):
    """Plan for reconciling state."""
    drifts: List[Drift]
    actions: List[ReconcileAction]
    estimated_impact: str
    requires_downtime: bool


class ReconcileResult(BaseModel):
    """Result of reconciliation."""
    applied: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
    skipped: List[Dict[str, Any]]
    dry_run: bool
    timestamp: str


def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _check_node_online(ip: str) -> bool:
    """Check if a node is online via ping."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "2", ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception:
        return False


async def _get_docker_services(ip: str, user: str) -> List[ServiceState]:
    """Get Docker container status from a node."""
    services = []
    try:
        cmd = (
            f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
            f"{user}@{ip} "
            "'docker ps -a --format \"{{.Names}}|{{.Status}}\"'"
        )
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if proc.returncode == 0:
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 2:
                    name = parts[0]
                    status_str = parts[1].lower()

                    if "up" in status_str and "healthy" in status_str:
                        status = ServiceStatus.RUNNING
                    elif "up" in status_str and "unhealthy" in status_str:
                        status = ServiceStatus.UNHEALTHY
                    elif "up" in status_str:
                        status = ServiceStatus.RUNNING
                    else:
                        status = ServiceStatus.STOPPED

                    services.append(ServiceState(
                        name=name,
                        node="hydra-storage",
                        status=status,
                    ))
    except Exception:
        pass
    return services


def create_reconcile_router() -> APIRouter:
    """Create and configure the reconcile API router."""
    router = APIRouter(prefix="/reconcile", tags=["reconcile"])

    @router.get("/state", response_model=ClusterState)
    async def get_cluster_state():
        """
        Get current cluster state.

        Queries all nodes for their current status and running services.
        """
        nodes = []

        for node_name, config in NODES.items():
            ip = config["ip"]
            os_type = config["os_type"]

            # Check if node is online
            is_online = await _check_node_online(ip)

            if not is_online:
                nodes.append(NodeState(
                    name=node_name,
                    ip=ip,
                    status=NodeStatus.OFFLINE,
                    os_type=os_type,
                ))
                continue

            # Get services
            if os_type == "unraid":
                services = await _get_docker_services(ip, config["user"])
            else:
                services = []  # NixOS systemd service check would go here

            # Check for critical service issues
            unhealthy = [s for s in services if s.status != ServiceStatus.RUNNING]
            critical_down = [s for s in unhealthy if s.name.lower() in CRITICAL_SERVICES]

            if critical_down:
                status = NodeStatus.DEGRADED
            else:
                status = NodeStatus.ONLINE

            nodes.append(NodeState(
                name=node_name,
                ip=ip,
                status=status,
                os_type=os_type,
                services=services,
            ))

        # Determine overall status
        if any(n.status == NodeStatus.OFFLINE for n in nodes):
            overall = NodeStatus.DEGRADED
        elif any(n.status == NodeStatus.DEGRADED for n in nodes):
            overall = NodeStatus.DEGRADED
        else:
            overall = NodeStatus.ONLINE

        return ClusterState(
            nodes=nodes,
            timestamp=_get_timestamp(),
            overall_status=overall,
        )

    @router.get("/drift", response_model=List[Drift])
    async def detect_drift():
        """
        Detect drift from desired state.

        Compares current state against expected services and configuration.
        """
        state = await get_cluster_state()
        drifts = []

        # Expected services (simplified - would load from config)
        expected_services = {
            "hydra-storage": [
                ("litellm", True),
                ("qdrant", True),
                ("postgres", True),
                ("redis", True),
                ("n8n", True),
                ("prometheus", True),
                ("grafana", False),
            ],
            "hydra-ai": [
                ("tabbyapi", True),
            ],
            "hydra-compute": [
                ("ollama", True),
            ],
        }

        for node in state.nodes:
            if node.status == NodeStatus.OFFLINE:
                drifts.append(Drift(
                    service="*",
                    node=node.name,
                    drift_type="node_offline",
                    expected="online",
                    actual="offline",
                    severity=DriftSeverity.CRITICAL,
                    auto_fixable=False,
                ))
                continue

            # Check expected services
            running_names = {s.name.lower() for s in node.services if s.status == ServiceStatus.RUNNING}

            for svc_name, is_critical in expected_services.get(node.name, []):
                if svc_name.lower() not in running_names:
                    # Check if it exists but is stopped
                    all_names = {s.name.lower() for s in node.services}
                    if svc_name.lower() in all_names:
                        drift_type = "stopped"
                    else:
                        drift_type = "missing"

                    drifts.append(Drift(
                        service=svc_name,
                        node=node.name,
                        drift_type=drift_type,
                        expected="running",
                        actual=drift_type,
                        severity=DriftSeverity.CRITICAL if is_critical else DriftSeverity.WARNING,
                        auto_fixable=drift_type == "stopped",
                    ))

            # Check for unhealthy services
            for svc in node.services:
                if svc.status == ServiceStatus.UNHEALTHY:
                    drifts.append(Drift(
                        service=svc.name,
                        node=node.name,
                        drift_type="unhealthy",
                        expected="healthy",
                        actual="unhealthy",
                        severity=DriftSeverity.WARNING,
                        auto_fixable=True,
                    ))

        return drifts

    @router.get("/plan", response_model=ReconcilePlan)
    async def generate_plan():
        """
        Generate reconciliation plan.

        Creates a plan of actions to fix detected drift.
        """
        drifts = await detect_drift()
        actions = []

        for drift in drifts:
            if not drift.auto_fixable:
                continue

            if drift.drift_type == "stopped":
                actions.append(ReconcileAction(
                    action_type="start",
                    target=drift.service,
                    node=drift.node,
                    command=f"docker start {drift.service}" if NODES[drift.node]["os_type"] == "unraid" else f"systemctl start {drift.service}",
                ))
            elif drift.drift_type == "unhealthy":
                actions.append(ReconcileAction(
                    action_type="restart",
                    target=drift.service,
                    node=drift.node,
                    command=f"docker restart {drift.service}" if NODES[drift.node]["os_type"] == "unraid" else f"systemctl restart {drift.service}",
                ))

        # Determine impact
        critical_actions = [a for a in actions if a.target.lower() in CRITICAL_SERVICES]
        if critical_actions:
            impact = "high"
            requires_downtime = True
        elif actions:
            impact = "medium"
            requires_downtime = False
        else:
            impact = "low"
            requires_downtime = False

        return ReconcilePlan(
            drifts=drifts,
            actions=actions,
            estimated_impact=impact,
            requires_downtime=requires_downtime,
        )

    @router.post("/apply", response_model=ReconcileResult)
    async def apply_reconciliation(
        dry_run: bool = Query(True, description="Dry run (don't apply changes)"),
    ):
        """
        Apply reconciliation plan.

        Executes actions to fix drift. Use dry_run=true to preview changes.
        """
        plan = await generate_plan()
        results = {
            "applied": [],
            "failed": [],
            "skipped": [],
        }

        for action in plan.actions:
            if dry_run:
                results["skipped"].append({
                    "action": action.dict(),
                    "reason": "dry_run",
                })
                continue

            # Execute the action
            node_config = NODES.get(action.node)
            if not node_config:
                results["failed"].append({
                    "action": action.dict(),
                    "reason": "unknown_node",
                })
                continue

            try:
                ssh_cmd = (
                    f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "
                    f"{node_config['user']}@{node_config['ip']} '{action.command}'"
                )

                proc = await asyncio.create_subprocess_shell(
                    ssh_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode == 0:
                    results["applied"].append({
                        "action": action.dict(),
                        "output": stdout.decode()[:500],
                    })
                else:
                    results["failed"].append({
                        "action": action.dict(),
                        "reason": stderr.decode()[:500],
                    })
            except Exception as e:
                results["failed"].append({
                    "action": action.dict(),
                    "reason": str(e),
                })

        return ReconcileResult(
            applied=results["applied"],
            failed=results["failed"],
            skipped=results["skipped"],
            dry_run=dry_run,
            timestamp=_get_timestamp(),
        )

    @router.get("/desired")
    async def get_desired_state():
        """
        Get desired state configuration.

        Returns the expected cluster configuration.
        """
        # This would load from a YAML file in production
        return {
            "nodes": [
                {
                    "name": "hydra-storage",
                    "expected_services": [
                        {"name": "litellm", "enabled": True, "port": 4000, "critical": True},
                        {"name": "qdrant", "enabled": True, "port": 6333, "critical": True},
                        {"name": "postgres", "enabled": True, "port": 5432, "critical": True},
                        {"name": "redis", "enabled": True, "port": 6379, "critical": True},
                        {"name": "n8n", "enabled": True, "port": 5678, "critical": True},
                        {"name": "prometheus", "enabled": True, "port": 9090, "critical": True},
                        {"name": "grafana", "enabled": True, "port": 3003, "critical": False},
                        {"name": "hydra-tools-api", "enabled": True, "port": 8700, "critical": True},
                    ],
                },
                {
                    "name": "hydra-ai",
                    "expected_services": [
                        {"name": "tabbyapi", "enabled": True, "port": 5000, "critical": True},
                        {"name": "open-webui", "enabled": True, "port": 3000, "critical": False},
                    ],
                },
                {
                    "name": "hydra-compute",
                    "expected_services": [
                        {"name": "ollama", "enabled": True, "port": 11434, "critical": True},
                        {"name": "comfyui", "enabled": True, "port": 8188, "critical": False},
                    ],
                },
            ],
            "version": "1.0.0",
            "last_updated": _get_timestamp(),
        }

    @router.post("/desired")
    async def update_desired_state(config: Dict[str, Any]):
        """
        Update desired state configuration.

        Modifies the expected cluster configuration.
        Note: This is a placeholder - actual persistence requires file/database storage.
        """
        return {
            "status": "accepted",
            "message": "Desired state update queued",
            "config_hash": hash(str(config)),
            "timestamp": _get_timestamp(),
        }

    @router.get("/history")
    async def get_reconciliation_history(limit: int = 10):
        """
        Get reconciliation history.

        Returns recent reconciliation operations and their results.
        Note: This is a placeholder - actual history requires persistence.
        """
        return {
            "history": [],
            "message": "History tracking not yet implemented",
            "timestamp": _get_timestamp(),
        }

    return router
