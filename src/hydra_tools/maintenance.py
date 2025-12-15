"""
Maintenance Tools for CrewAI Integration

Provides tools for agents to perform maintenance operations
on the Hydra cluster including Docker management, backups,
and service control.
"""

import os
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class ServiceDependency:
    """Represents a service dependency relationship."""
    service: str
    depends_on: List[str]
    dependents: List[str]
    priority: int  # Lower = start first


@dataclass
class MaintenanceWindow:
    """Defines a maintenance window."""
    start: datetime
    end: datetime
    affected_services: List[str]
    reason: str


@dataclass
class BackupResult:
    """Result of a backup operation."""
    service: str
    success: bool
    path: Optional[str]
    size_mb: Optional[float]
    duration_seconds: float
    error: Optional[str]


class ServiceDependencyTool:
    """
    Tool for understanding service dependencies.

    Used by maintenance planning agents to understand
    what services depend on each other.
    """

    # Known service dependencies in Hydra cluster
    DEPENDENCIES = {
        "postgresql": {
            "depends_on": [],
            "dependents": ["litellm", "n8n", "grafana", "letta"],
            "priority": 1
        },
        "redis": {
            "depends_on": [],
            "dependents": ["litellm", "n8n", "langfuse"],
            "priority": 1
        },
        "qdrant": {
            "depends_on": [],
            "dependents": ["hydra-search", "letta"],
            "priority": 1
        },
        "litellm": {
            "depends_on": ["postgresql", "redis"],
            "dependents": ["open-webui", "hydra-voice", "crewai"],
            "priority": 2
        },
        "tabbyapi": {
            "depends_on": [],
            "dependents": ["litellm"],
            "priority": 1
        },
        "ollama": {
            "depends_on": [],
            "dependents": ["litellm", "open-webui"],
            "priority": 1
        },
        "letta": {
            "depends_on": ["postgresql", "qdrant", "litellm"],
            "dependents": ["hydra-voice"],
            "priority": 3
        },
        "hydra-voice": {
            "depends_on": ["litellm", "letta", "hydra-stt", "kokoro-tts"],
            "dependents": ["hydra-wakeword"],
            "priority": 4
        },
        "hydra-stt": {
            "depends_on": [],
            "dependents": ["hydra-voice"],
            "priority": 1
        },
        "kokoro-tts": {
            "depends_on": [],
            "dependents": ["hydra-voice"],
            "priority": 1
        },
        "prometheus": {
            "depends_on": [],
            "dependents": ["grafana", "alertmanager"],
            "priority": 1
        },
        "grafana": {
            "depends_on": ["prometheus", "postgresql"],
            "dependents": [],
            "priority": 3
        },
    }

    def get_dependency(self, service: str) -> Optional[ServiceDependency]:
        """Get dependency info for a service."""
        if service not in self.DEPENDENCIES:
            return None
        dep = self.DEPENDENCIES[service]
        return ServiceDependency(
            service=service,
            depends_on=dep["depends_on"],
            dependents=dep["dependents"],
            priority=dep["priority"]
        )

    def get_restart_order(self, services: List[str]) -> List[str]:
        """
        Get the correct order to restart services.

        Args:
            services: List of services to restart

        Returns:
            Ordered list with dependencies first
        """
        ordered = []
        remaining = set(services)

        while remaining:
            # Find services with all dependencies satisfied
            for service in list(remaining):
                dep = self.DEPENDENCIES.get(service, {"depends_on": [], "priority": 99})
                deps_satisfied = all(
                    d not in remaining or d in ordered
                    for d in dep["depends_on"]
                )
                if deps_satisfied:
                    ordered.append(service)
                    remaining.remove(service)

        return ordered

    def get_impact(self, service: str) -> List[str]:
        """
        Get all services that would be affected by stopping a service.

        Args:
            service: Service to check

        Returns:
            List of affected services (recursive dependents)
        """
        affected = set()
        to_check = [service]

        while to_check:
            current = to_check.pop(0)
            if current in self.DEPENDENCIES:
                dependents = self.DEPENDENCIES[current]["dependents"]
                for dep in dependents:
                    if dep not in affected:
                        affected.add(dep)
                        to_check.append(dep)

        return list(affected)


class MaintenanceWindowTool:
    """Tool for managing maintenance windows."""

    def __init__(self):
        self.windows: List[MaintenanceWindow] = []

    def schedule_window(
        self,
        start: datetime,
        duration_minutes: int,
        services: List[str],
        reason: str
    ) -> MaintenanceWindow:
        """
        Schedule a maintenance window.

        Args:
            start: Start time
            duration_minutes: Duration in minutes
            services: Services affected
            reason: Reason for maintenance

        Returns:
            Created maintenance window
        """
        from datetime import timedelta
        window = MaintenanceWindow(
            start=start,
            end=start + timedelta(minutes=duration_minutes),
            affected_services=services,
            reason=reason
        )
        self.windows.append(window)
        return window

    def get_active_windows(self) -> List[MaintenanceWindow]:
        """Get currently active maintenance windows."""
        now = datetime.now()
        return [w for w in self.windows if w.start <= now <= w.end]

    def is_in_maintenance(self, service: str) -> bool:
        """Check if a service is currently in maintenance."""
        active = self.get_active_windows()
        return any(service in w.affected_services for w in active)


class DockerComposeTool:
    """
    Tool for managing Docker Compose services.

    Provides safe service control with validation.
    """

    def __init__(
        self,
        host: str = "192.168.1.244",
        compose_dir: str = "/mnt/user/appdata/hydra-stack"
    ):
        self.host = host
        self.compose_dir = compose_dir

    async def _run_ssh_command(self, command: str) -> tuple[bool, str]:
        """Run SSH command on the host."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ssh", f"root@{self.host}", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            success = process.returncode == 0
            output = stdout.decode() if success else stderr.decode()
            return success, output
        except Exception as e:
            return False, str(e)

    async def restart_service(self, service: str) -> Dict[str, Any]:
        """
        Restart a Docker Compose service.

        Args:
            service: Service name to restart

        Returns:
            Result dict with success status
        """
        cmd = f"cd {self.compose_dir} && docker-compose restart {service}"
        success, output = await self._run_ssh_command(cmd)
        return {
            "service": service,
            "action": "restart",
            "success": success,
            "output": output
        }

    async def stop_service(self, service: str) -> Dict[str, Any]:
        """Stop a service."""
        cmd = f"cd {self.compose_dir} && docker-compose stop {service}"
        success, output = await self._run_ssh_command(cmd)
        return {
            "service": service,
            "action": "stop",
            "success": success,
            "output": output
        }

    async def start_service(self, service: str) -> Dict[str, Any]:
        """Start a service."""
        cmd = f"cd {self.compose_dir} && docker-compose start {service}"
        success, output = await self._run_ssh_command(cmd)
        return {
            "service": service,
            "action": "start",
            "success": success,
            "output": output
        }

    async def pull_service(self, service: str) -> Dict[str, Any]:
        """Pull latest image for a service."""
        cmd = f"cd {self.compose_dir} && docker-compose pull {service}"
        success, output = await self._run_ssh_command(cmd)
        return {
            "service": service,
            "action": "pull",
            "success": success,
            "output": output
        }

    async def recreate_service(self, service: str) -> Dict[str, Any]:
        """Recreate a service (pull + up)."""
        cmd = f"cd {self.compose_dir} && docker-compose pull {service} && docker-compose up -d {service}"
        success, output = await self._run_ssh_command(cmd)
        return {
            "service": service,
            "action": "recreate",
            "success": success,
            "output": output
        }


class SystemctlTool:
    """Tool for managing systemd services on NixOS nodes."""

    def __init__(self):
        self.nodes = {
            "hydra-ai": "192.168.1.250",
            "hydra-compute": "192.168.1.203"
        }

    async def _run_ssh_command(self, node: str, command: str) -> tuple[bool, str]:
        """Run SSH command on a NixOS node."""
        host = self.nodes.get(node)
        if not host:
            return False, f"Unknown node: {node}"

        try:
            process = await asyncio.create_subprocess_exec(
                "ssh", f"typhon@{host}", f"sudo {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            success = process.returncode == 0
            output = stdout.decode() if success else stderr.decode()
            return success, output
        except Exception as e:
            return False, str(e)

    async def restart_service(self, node: str, service: str) -> Dict[str, Any]:
        """Restart a systemd service."""
        success, output = await self._run_ssh_command(
            node, f"systemctl restart {service}"
        )
        return {
            "node": node,
            "service": service,
            "action": "restart",
            "success": success,
            "output": output
        }

    async def get_service_status(self, node: str, service: str) -> Dict[str, Any]:
        """Get status of a systemd service."""
        success, output = await self._run_ssh_command(
            node, f"systemctl status {service} --no-pager"
        )
        return {
            "node": node,
            "service": service,
            "active": "active (running)" in output,
            "output": output
        }

    async def run_nixos_rebuild(self, node: str) -> Dict[str, Any]:
        """Run nixos-rebuild switch on a node."""
        success, output = await self._run_ssh_command(
            node, "nixos-rebuild switch"
        )
        return {
            "node": node,
            "action": "nixos-rebuild",
            "success": success,
            "output": output[:1000]  # Truncate long output
        }


class BackupTool:
    """Tool for managing backups."""

    def __init__(self, host: str = "192.168.1.244"):
        self.host = host
        self.backup_dir = "/mnt/user/backups"

    async def _run_ssh_command(self, command: str) -> tuple[bool, str]:
        """Run SSH command on the host."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ssh", f"root@{self.host}", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            success = process.returncode == 0
            output = stdout.decode() if success else stderr.decode()
            return success, output
        except Exception as e:
            return False, str(e)

    async def backup_postgresql(self, database: str = "all") -> BackupResult:
        """
        Backup PostgreSQL database.

        Args:
            database: Database name or "all" for all databases

        Returns:
            Backup result
        """
        start = datetime.now()
        timestamp = start.strftime("%Y%m%d_%H%M%S")

        if database == "all":
            filename = f"postgres_all_{timestamp}.sql.gz"
            cmd = f"docker exec hydra-postgres pg_dumpall -U hydra | gzip > {self.backup_dir}/{filename}"
        else:
            filename = f"postgres_{database}_{timestamp}.sql.gz"
            cmd = f"docker exec hydra-postgres pg_dump -U hydra {database} | gzip > {self.backup_dir}/{filename}"

        success, output = await self._run_ssh_command(cmd)
        duration = (datetime.now() - start).total_seconds()

        if success:
            # Get file size
            size_cmd = f"ls -l {self.backup_dir}/{filename} | awk '{{print $5}}'"
            _, size_output = await self._run_ssh_command(size_cmd)
            try:
                size_mb = int(size_output.strip()) / (1024 * 1024)
            except:
                size_mb = None

            return BackupResult(
                service="postgresql",
                success=True,
                path=f"{self.backup_dir}/{filename}",
                size_mb=size_mb,
                duration_seconds=duration,
                error=None
            )
        else:
            return BackupResult(
                service="postgresql",
                success=False,
                path=None,
                size_mb=None,
                duration_seconds=duration,
                error=output
            )

    async def backup_qdrant(self) -> BackupResult:
        """Backup Qdrant collections."""
        start = datetime.now()
        timestamp = start.strftime("%Y%m%d_%H%M%S")
        snapshot_dir = f"{self.backup_dir}/qdrant_{timestamp}"

        cmd = f"""
        mkdir -p {snapshot_dir} && \
        curl -X POST 'http://localhost:6333/snapshots' && \
        cp -r /mnt/user/appdata/qdrant/snapshots/* {snapshot_dir}/
        """

        success, output = await self._run_ssh_command(cmd)
        duration = (datetime.now() - start).total_seconds()

        return BackupResult(
            service="qdrant",
            success=success,
            path=snapshot_dir if success else None,
            size_mb=None,
            duration_seconds=duration,
            error=output if not success else None
        )

    async def backup_redis(self) -> BackupResult:
        """Backup Redis database."""
        start = datetime.now()
        timestamp = start.strftime("%Y%m%d_%H%M%S")
        filename = f"redis_{timestamp}.rdb"

        # Trigger BGSAVE and copy the dump
        cmd = f"""
        docker exec hydra-redis redis-cli BGSAVE && \
        sleep 2 && \
        cp /mnt/user/appdata/redis/data/dump.rdb {self.backup_dir}/{filename}
        """

        success, output = await self._run_ssh_command(cmd)
        duration = (datetime.now() - start).total_seconds()

        return BackupResult(
            service="redis",
            success=success,
            path=f"{self.backup_dir}/{filename}" if success else None,
            size_mb=None,
            duration_seconds=duration,
            error=output if not success else None
        )

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups in backup directory."""
        cmd = f"ls -lh {self.backup_dir} | tail -n +2"
        success, output = await self._run_ssh_command(cmd)

        backups = []
        if success:
            for line in output.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 9:
                        backups.append({
                            "name": parts[-1],
                            "size": parts[4],
                            "date": f"{parts[5]} {parts[6]} {parts[7]}"
                        })

        return backups

    async def cleanup_old_backups(self, days: int = 30) -> Dict[str, Any]:
        """Remove backups older than specified days."""
        cmd = f"find {self.backup_dir} -type f -mtime +{days} -delete -print"
        success, output = await self._run_ssh_command(cmd)

        deleted = output.strip().split("\n") if output.strip() else []
        return {
            "success": success,
            "deleted_count": len(deleted),
            "deleted_files": deleted
        }
