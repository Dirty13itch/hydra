"""Cluster state reconciliation engine."""

import asyncio
import subprocess
from datetime import datetime, timezone
from typing import Any

import httpx

from hydra_reconcile.state import (
    ClusterState,
    DesiredState,
    Drift,
    NodeState,
    NodeStatus,
    ReconciliationPlan,
    ServiceState,
    ServiceStatus,
)

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

# Critical services that affect overall cluster health
CRITICAL_SERVICES = {"tabbyapi", "litellm", "postgres", "qdrant", "redis"}


class ClusterReconciler:
    """Reconciles cluster state between desired and actual."""

    def __init__(
        self,
        desired_state: DesiredState | None = None,
        desired_state_path: str | None = None,
        health_endpoint: str = "http://192.168.1.244:8600",
    ):
        """Initialize reconciler."""
        self.health_endpoint = health_endpoint
        self.http_client = httpx.AsyncClient(timeout=30.0)

        if desired_state:
            self.desired_state = desired_state
        elif desired_state_path:
            self.desired_state = DesiredState.from_yaml(desired_state_path)
        else:
            self.desired_state = None

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def __aenter__(self) -> "ClusterReconciler":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def get_current_state(self) -> ClusterState:
        """Fetch current cluster state."""
        nodes = []

        for node_name, node_config in NODES.items():
            node_state = await self._get_node_state(node_name, node_config)
            nodes.append(node_state)

        return ClusterState(
            nodes=nodes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _get_node_state(self, name: str, config: dict[str, Any]) -> NodeState:
        """Get state of a single node."""
        ip = config["ip"]
        os_type = config["os_type"]

        # Check node availability
        node_online = await self._check_node_online(ip)

        if not node_online:
            return NodeState(
                name=name,
                ip=ip,
                status=NodeStatus.OFFLINE,
                os_type=os_type,
            )

        # Get services
        services = await self._get_node_services(name, config)

        # Get GPU info (if NixOS node)
        gpu_info = await self._get_gpu_info(config) if os_type == "nixos" else {}

        # Get memory info
        memory_info = await self._get_memory_info(config)

        # Determine node status
        unhealthy_services = [s for s in services if s.status == ServiceStatus.UNHEALTHY]
        if any(s.name in CRITICAL_SERVICES for s in unhealthy_services):
            status = NodeStatus.DEGRADED
        else:
            status = NodeStatus.ONLINE

        return NodeState(
            name=name,
            ip=ip,
            status=status,
            os_type=os_type,
            services=services,
            gpu_count=gpu_info.get("count", 0),
            gpu_temps=gpu_info.get("temps", []),
            memory_used_gb=memory_info.get("used_gb", 0.0),
            memory_total_gb=memory_info.get("total_gb", 0.0),
        )

    async def _check_node_online(self, ip: str) -> bool:
        """Check if node is online via ping."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "1",
                "-W",
                "2",
                ip,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    async def _get_node_services(
        self, node_name: str, config: dict[str, Any]
    ) -> list[ServiceState]:
        """Get services running on a node."""
        services = []
        os_type = config["os_type"]

        if os_type == "unraid":
            # Get Docker container status
            services = await self._get_docker_services(config)
        else:
            # Get systemd service status
            services = await self._get_systemd_services(node_name, config)

        return services

    async def _get_docker_services(self, config: dict[str, Any]) -> list[ServiceState]:
        """Get Docker container status from Unraid."""
        services = []
        ip = config["ip"]

        try:
            # Get container list via SSH
            cmd = (
                f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
                f"{config['user']}@{ip} "
                "'docker ps -a --format \"{{.Names}}|{{.Status}}|{{.Ports}}\"'"
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
                        ports = parts[2] if len(parts) > 2 else ""

                        # Parse status
                        if "up" in status_str and "healthy" in status_str:
                            status = ServiceStatus.RUNNING
                        elif "up" in status_str and "unhealthy" in status_str:
                            status = ServiceStatus.UNHEALTHY
                        elif "up" in status_str:
                            status = ServiceStatus.RUNNING
                        else:
                            status = ServiceStatus.STOPPED

                        # Extract port
                        port = None
                        if ":" in ports:
                            try:
                                port_str = ports.split(":")[1].split("->")[0]
                                port = int(port_str)
                            except (IndexError, ValueError):
                                pass

                        services.append(
                            ServiceState(
                                name=name,
                                node="hydra-storage",
                                status=status,
                                port=port,
                            )
                        )
        except Exception:
            pass

        return services

    async def _get_systemd_services(
        self, node_name: str, config: dict[str, Any]
    ) -> list[ServiceState]:
        """Get systemd service status from NixOS."""
        services = []
        ip = config["ip"]

        # Known services per node
        node_services = {
            "hydra-ai": ["tabbyapi", "open-webui"],
            "hydra-compute": ["ollama", "comfyui"],
        }

        for svc_name in node_services.get(node_name, []):
            try:
                cmd = (
                    f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
                    f"{config['user']}@{ip} "
                    f"'systemctl is-active {svc_name} 2>/dev/null || echo unknown'"
                )

                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()

                status_str = stdout.decode().strip()
                if status_str == "active":
                    status = ServiceStatus.RUNNING
                elif status_str in ("inactive", "failed"):
                    status = ServiceStatus.STOPPED
                else:
                    status = ServiceStatus.UNKNOWN

                services.append(
                    ServiceState(
                        name=svc_name,
                        node=node_name,
                        status=status,
                    )
                )
            except Exception:
                services.append(
                    ServiceState(
                        name=svc_name,
                        node=node_name,
                        status=ServiceStatus.UNKNOWN,
                    )
                )

        return services

    async def _get_gpu_info(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get GPU information from node."""
        ip = config["ip"]

        try:
            cmd = (
                f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
                f"{config['user']}@{ip} "
                "'nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits'"
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                temps = []
                for line in stdout.decode().strip().split("\n"):
                    if line.strip():
                        temps.append(float(line.strip()))
                return {"count": len(temps), "temps": temps}
        except Exception:
            pass

        return {"count": 0, "temps": []}

    async def _get_memory_info(self, config: dict[str, Any]) -> dict[str, float]:
        """Get memory information from node."""
        ip = config["ip"]

        try:
            cmd = (
                f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "
                f"{config['user']}@{ip} "
                "'free -g | grep Mem'"
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                parts = stdout.decode().strip().split()
                if len(parts) >= 3:
                    return {
                        "total_gb": float(parts[1]),
                        "used_gb": float(parts[2]),
                    }
        except Exception:
            pass

        return {"total_gb": 0.0, "used_gb": 0.0}

    def compare_states(
        self, desired: DesiredState, actual: ClusterState
    ) -> ReconciliationPlan:
        """Compare desired and actual states, return reconciliation plan."""
        plan = ReconciliationPlan()

        # Check for missing or unhealthy services
        for node in desired.nodes:
            for desired_svc in node.services:
                if not desired_svc.enabled:
                    continue

                actual_svc = actual.get_service(desired_svc.name)

                if actual_svc is None:
                    # Service missing
                    plan.add_drift(
                        Drift(
                            service=desired_svc.name,
                            node=desired_svc.node,
                            drift_type="missing",
                            expected="running",
                            actual="not found",
                            severity="critical" if desired_svc.name in CRITICAL_SERVICES else "warning",
                            auto_fixable=True,
                        )
                    )
                    plan.add_action(
                        action_type="start",
                        target=desired_svc.name,
                        node=desired_svc.node,
                    )
                elif actual_svc.status == ServiceStatus.STOPPED:
                    # Service stopped
                    plan.add_drift(
                        Drift(
                            service=desired_svc.name,
                            node=desired_svc.node,
                            drift_type="stopped",
                            expected="running",
                            actual="stopped",
                            severity="critical" if desired_svc.name in CRITICAL_SERVICES else "warning",
                            auto_fixable=True,
                        )
                    )
                    plan.add_action(
                        action_type="start",
                        target=desired_svc.name,
                        node=desired_svc.node,
                    )
                elif actual_svc.status == ServiceStatus.UNHEALTHY:
                    # Service unhealthy
                    plan.add_drift(
                        Drift(
                            service=desired_svc.name,
                            node=desired_svc.node,
                            drift_type="unhealthy",
                            expected="healthy",
                            actual="unhealthy",
                            severity="warning",
                            auto_fixable=True,
                        )
                    )
                    plan.add_action(
                        action_type="restart",
                        target=desired_svc.name,
                        node=desired_svc.node,
                    )

                # Check port mismatch
                if desired_svc.port and actual_svc and actual_svc.port:
                    if desired_svc.port != actual_svc.port:
                        plan.add_drift(
                            Drift(
                                service=desired_svc.name,
                                node=desired_svc.node,
                                drift_type="port_mismatch",
                                expected=desired_svc.port,
                                actual=actual_svc.port,
                                severity="info",
                                auto_fixable=False,
                            )
                        )

        # Check for extra services (running but not in desired state)
        # This is informational only
        desired_service_names = {
            svc.name for node in desired.nodes for svc in node.services
        }
        for node in actual.nodes:
            for svc in node.services:
                if svc.name not in desired_service_names and svc.status == ServiceStatus.RUNNING:
                    plan.add_drift(
                        Drift(
                            service=svc.name,
                            node=node.name,
                            drift_type="extra",
                            expected="not defined",
                            actual="running",
                            severity="info",
                            auto_fixable=False,
                        )
                    )

        return plan

    async def apply_plan(
        self, plan: ReconciliationPlan, dry_run: bool = True
    ) -> dict[str, Any]:
        """Apply reconciliation plan."""
        results = {"applied": [], "failed": [], "skipped": []}

        for action in plan.actions:
            if dry_run:
                results["skipped"].append(
                    {"action": action, "reason": "dry_run"}
                )
                continue

            try:
                success = await self._execute_action(action)
                if success:
                    results["applied"].append(action)
                else:
                    results["failed"].append(
                        {"action": action, "reason": "execution_failed"}
                    )
            except Exception as e:
                results["failed"].append(
                    {"action": action, "reason": str(e)}
                )

        return results

    async def _execute_action(self, action: dict[str, Any]) -> bool:
        """Execute a single reconciliation action."""
        action_type = action["type"]
        target = action["target"]
        node = action["node"]

        node_config = NODES.get(node)
        if not node_config:
            return False

        if node_config["os_type"] == "unraid":
            # Docker action
            if action_type == "start":
                cmd = f"docker start {target}"
            elif action_type == "restart":
                cmd = f"docker restart {target}"
            elif action_type == "stop":
                cmd = f"docker stop {target}"
            else:
                return False
        else:
            # Systemd action
            if action_type == "start":
                cmd = f"sudo systemctl start {target}"
            elif action_type == "restart":
                cmd = f"sudo systemctl restart {target}"
            elif action_type == "stop":
                cmd = f"sudo systemctl stop {target}"
            else:
                return False

        ssh_cmd = (
            f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "
            f"{node_config['user']}@{node_config['ip']} '{cmd}'"
        )

        proc = await asyncio.create_subprocess_shell(
            ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await proc.communicate()

        return proc.returncode == 0

    async def reconcile(self, dry_run: bool = True) -> dict[str, Any]:
        """Full reconciliation: detect drift and optionally fix."""
        if not self.desired_state:
            raise ValueError("No desired state configured")

        # Get current state
        current = await self.get_current_state()

        # Compare states
        plan = self.compare_states(self.desired_state, current)

        # Apply if not dry run
        results = await self.apply_plan(plan, dry_run=dry_run)

        return {
            "timestamp": current.timestamp,
            "drift_count": len(plan.drifts),
            "plan": plan.to_dict(),
            "results": results,
            "dry_run": dry_run,
        }
