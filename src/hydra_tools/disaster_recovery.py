"""
Disaster Recovery System

Provides resilience and recovery capabilities:
- Configuration backup and restore
- State snapshots
- Service recovery procedures
- Health monitoring with auto-recovery
- Rollback capabilities

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

BACKUPS_CREATED = Counter(
    "hydra_backups_created_total",
    "Total backups created"
)

RECOVERY_OPERATIONS = Counter(
    "hydra_recovery_operations_total",
    "Recovery operations performed",
    ["type", "status"]
)

BACKUP_SIZE_BYTES = Gauge(
    "hydra_backup_size_bytes",
    "Latest backup size in bytes"
)

SERVICES_RECOVERED = Counter(
    "hydra_services_recovered_total",
    "Services automatically recovered"
)


# =============================================================================
# Recovery Types
# =============================================================================

class BackupType(Enum):
    FULL = "full"
    CONFIG = "config"
    STATE = "state"
    DATA = "data"


class RecoveryStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Backup:
    """A system backup."""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    size_bytes: int
    components: List[str]
    path: str
    description: str = ""
    verified: bool = False


@dataclass
class RecoveryPoint:
    """A recovery point for rollback."""
    point_id: str
    created_at: datetime
    description: str
    state_snapshot: Dict[str, Any]
    config_snapshot: Dict[str, Any]


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    url: str
    healthy: bool
    last_check: datetime
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    auto_recover: bool = True


# =============================================================================
# Disaster Recovery Manager
# =============================================================================

class DisasterRecoveryManager:
    """
    Manages disaster recovery for Hydra.

    Features:
    - Configuration backup and restore
    - State snapshots
    - Auto-recovery for unhealthy services
    - Rollback capabilities
    """

    def __init__(
        self,
        backup_path: str = "/data/backups",
        config_path: str = "/mnt/user/appdata/hydra-dev",
        max_backups: int = 10,
    ):
        self.backup_path = Path(backup_path)
        self.config_path = Path(config_path)
        self.max_backups = max_backups

        self.backup_path.mkdir(parents=True, exist_ok=True)

        # State
        self.backups: Dict[str, Backup] = {}
        self.recovery_points: List[RecoveryPoint] = []
        self.service_health: Dict[str, ServiceHealth] = {}
        self.recovery_status = RecoveryStatus.HEALTHY

        # Services to monitor
        self.monitored_services = [
            ServiceHealth("hydra-api", "http://192.168.1.244:8700/health", True, datetime.utcnow()),
            ServiceHealth("litellm", "http://192.168.1.244:4000/health", True, datetime.utcnow()),
            ServiceHealth("qdrant", "http://192.168.1.244:6333/healthz", True, datetime.utcnow()),
            ServiceHealth("letta", "http://192.168.1.244:8283/health", True, datetime.utcnow()),
        ]

        # Initialize health tracking
        for svc in self.monitored_services:
            self.service_health[svc.service_name] = svc

        # Load existing backups
        self._load_backups()

        logger.info("Disaster recovery manager initialized")

    def _load_backups(self):
        """Load existing backups from disk."""
        try:
            index_file = self.backup_path / "index.json"
            if index_file.exists():
                data = json.loads(index_file.read_text())
                for b in data.get("backups", []):
                    backup = Backup(
                        backup_id=b["backup_id"],
                        backup_type=BackupType(b["backup_type"]),
                        created_at=datetime.fromisoformat(b["created_at"]),
                        size_bytes=b["size_bytes"],
                        components=b["components"],
                        path=b["path"],
                        description=b.get("description", ""),
                        verified=b.get("verified", False),
                    )
                    self.backups[backup.backup_id] = backup
        except Exception as e:
            logger.error(f"Failed to load backups: {e}")

    def _save_backup_index(self):
        """Save backup index to disk."""
        index_file = self.backup_path / "index.json"
        data = {
            "backups": [
                {
                    "backup_id": b.backup_id,
                    "backup_type": b.backup_type.value,
                    "created_at": b.created_at.isoformat(),
                    "size_bytes": b.size_bytes,
                    "components": b.components,
                    "path": b.path,
                    "description": b.description,
                    "verified": b.verified,
                }
                for b in self.backups.values()
            ],
            "updated_at": datetime.utcnow().isoformat(),
        }
        index_file.write_text(json.dumps(data, indent=2))

    # =========================================================================
    # Backup Operations
    # =========================================================================

    async def create_backup(
        self,
        backup_type: BackupType = BackupType.CONFIG,
        description: str = "",
    ) -> Backup:
        """Create a backup."""
        backup_id = f"backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        backup_dir = self.backup_path / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        components = []

        try:
            if backup_type in (BackupType.FULL, BackupType.CONFIG):
                # Backup configuration files
                config_files = [
                    "CLAUDE.md",
                    "STATE.json",
                    "ROADMAP.md",
                    "docker-compose.yml",
                    ".claude/rules",
                ]
                for cf in config_files:
                    src = self.config_path / cf
                    if src.exists():
                        if src.is_dir():
                            shutil.copytree(src, backup_dir / cf)
                        else:
                            shutil.copy2(src, backup_dir / cf)
                        components.append(cf)

            if backup_type in (BackupType.FULL, BackupType.STATE):
                # Backup state data
                state_dir = backup_dir / "state"
                state_dir.mkdir(exist_ok=True)

                # Export scheduler state
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get("http://192.168.1.244:8700/scheduler/status")
                        if response.status_code == 200:
                            (state_dir / "scheduler.json").write_text(response.text)
                            components.append("scheduler_state")
                except Exception as e:
                    logger.warning(f"Failed to export scheduler state: {e}")

            # Create archive
            archive_path = self.backup_path / f"{backup_id}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_id)

            # Get size
            size_bytes = archive_path.stat().st_size

            # Clean up directory (keep archive)
            shutil.rmtree(backup_dir)

            backup = Backup(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=datetime.utcnow(),
                size_bytes=size_bytes,
                components=components,
                path=str(archive_path),
                description=description,
                verified=True,
            )

            self.backups[backup_id] = backup
            self._save_backup_index()
            self._cleanup_old_backups()

            BACKUPS_CREATED.inc()
            BACKUP_SIZE_BYTES.set(size_bytes)

            logger.info(f"Created backup {backup_id}: {len(components)} components, {size_bytes} bytes")
            return backup

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise

    def _cleanup_old_backups(self):
        """Remove old backups exceeding max_backups."""
        if len(self.backups) <= self.max_backups:
            return

        sorted_backups = sorted(
            self.backups.values(),
            key=lambda b: b.created_at,
        )

        to_remove = sorted_backups[:-self.max_backups]
        for backup in to_remove:
            try:
                Path(backup.path).unlink(missing_ok=True)
                del self.backups[backup.backup_id]
            except Exception as e:
                logger.warning(f"Failed to remove old backup {backup.backup_id}: {e}")

        self._save_backup_index()

    async def restore_backup(self, backup_id: str) -> Dict[str, Any]:
        """Restore from a backup."""
        backup = self.backups.get(backup_id)
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")

        backup_path = Path(backup.path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup.path}")

        restored = []
        errors = []

        try:
            # Extract backup
            extract_dir = self.backup_path / "restore_temp"
            extract_dir.mkdir(exist_ok=True)

            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            backup_content = extract_dir / backup_id

            # Restore files
            for component in backup.components:
                src = backup_content / component
                dst = self.config_path / component

                if src.exists():
                    try:
                        if src.is_dir():
                            if dst.exists():
                                shutil.rmtree(dst)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                        restored.append(component)
                    except Exception as e:
                        errors.append(f"{component}: {e}")

            # Cleanup
            shutil.rmtree(extract_dir)

            RECOVERY_OPERATIONS.labels(type="restore", status="success").inc()

            return {
                "backup_id": backup_id,
                "restored": restored,
                "errors": errors,
                "status": "success" if not errors else "partial",
            }

        except Exception as e:
            RECOVERY_OPERATIONS.labels(type="restore", status="failed").inc()
            logger.error(f"Restore failed: {e}")
            raise

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups."""
        return [
            {
                "backup_id": b.backup_id,
                "type": b.backup_type.value,
                "created_at": b.created_at.isoformat(),
                "size_bytes": b.size_bytes,
                "components": b.components,
                "description": b.description,
            }
            for b in sorted(self.backups.values(), key=lambda x: x.created_at, reverse=True)
        ]

    # =========================================================================
    # Health Monitoring
    # =========================================================================

    async def check_service_health(self) -> Dict[str, Any]:
        """Check health of all monitored services."""
        results = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, svc in self.service_health.items():
                try:
                    response = await client.get(svc.url)
                    if response.status_code == 200:
                        svc.healthy = True
                        svc.consecutive_failures = 0
                        svc.last_error = None
                    else:
                        svc.healthy = False
                        svc.consecutive_failures += 1
                        svc.last_error = f"HTTP {response.status_code}"
                except Exception as e:
                    svc.healthy = False
                    svc.consecutive_failures += 1
                    svc.last_error = str(e)

                svc.last_check = datetime.utcnow()

                results[name] = {
                    "healthy": svc.healthy,
                    "consecutive_failures": svc.consecutive_failures,
                    "last_error": svc.last_error,
                }

                # Auto-recovery trigger
                if svc.auto_recover and svc.consecutive_failures >= 3:
                    await self._attempt_recovery(svc)

        # Update overall status
        healthy_count = sum(1 for s in self.service_health.values() if s.healthy)
        total = len(self.service_health)

        if healthy_count == total:
            self.recovery_status = RecoveryStatus.HEALTHY
        elif healthy_count >= total / 2:
            self.recovery_status = RecoveryStatus.DEGRADED
        else:
            self.recovery_status = RecoveryStatus.CRITICAL

        return {
            "overall_status": self.recovery_status.value,
            "healthy_services": healthy_count,
            "total_services": total,
            "services": results,
        }

    async def _attempt_recovery(self, service: ServiceHealth):
        """Attempt to recover a failed service."""
        logger.warning(f"Attempting recovery for {service.service_name}")

        try:
            # For Docker services, try restart
            import subprocess

            container_name = f"hydra-{service.service_name.replace('-api', '-tools-api')}"
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info(f"Successfully restarted {container_name}")
                SERVICES_RECOVERED.inc()
                RECOVERY_OPERATIONS.labels(type="auto_restart", status="success").inc()
                service.consecutive_failures = 0
            else:
                logger.error(f"Failed to restart {container_name}: {result.stderr.decode()}")
                RECOVERY_OPERATIONS.labels(type="auto_restart", status="failed").inc()

        except Exception as e:
            logger.error(f"Recovery attempt failed for {service.service_name}: {e}")
            RECOVERY_OPERATIONS.labels(type="auto_restart", status="error").inc()

    # =========================================================================
    # Recovery Points
    # =========================================================================

    async def create_recovery_point(self, description: str = "") -> RecoveryPoint:
        """Create a recovery point."""
        point_id = f"rp-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        # Capture state
        state_snapshot = {}
        config_snapshot = {}

        try:
            # Get scheduler state
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get("http://192.168.1.244:8700/scheduler/status")
                if response.status_code == 200:
                    state_snapshot["scheduler"] = response.json()

            # Read critical config files
            state_file = self.config_path / "STATE.json"
            if state_file.exists():
                config_snapshot["state"] = json.loads(state_file.read_text())

        except Exception as e:
            logger.error(f"Failed to capture state for recovery point: {e}")

        point = RecoveryPoint(
            point_id=point_id,
            created_at=datetime.utcnow(),
            description=description or f"Recovery point created at {datetime.utcnow().isoformat()}",
            state_snapshot=state_snapshot,
            config_snapshot=config_snapshot,
        )

        self.recovery_points.append(point)
        self.recovery_points = self.recovery_points[-20:]  # Keep last 20

        return point

    def get_status(self) -> Dict[str, Any]:
        """Get disaster recovery status."""
        return {
            "status": self.recovery_status.value,
            "backups": {
                "count": len(self.backups),
                "latest": self.list_backups()[:3],
            },
            "recovery_points": len(self.recovery_points),
            "service_health": {
                name: {"healthy": svc.healthy, "consecutive_failures": svc.consecutive_failures}
                for name, svc in self.service_health.items()
            },
        }


# =============================================================================
# Global Instance
# =============================================================================

_dr_manager: Optional[DisasterRecoveryManager] = None


def get_dr_manager() -> DisasterRecoveryManager:
    """Get or create disaster recovery manager."""
    global _dr_manager
    if _dr_manager is None:
        _dr_manager = DisasterRecoveryManager()
    return _dr_manager


# =============================================================================
# FastAPI Router
# =============================================================================

def create_disaster_recovery_router():
    """Create FastAPI router for disaster recovery endpoints."""
    from fastapi import APIRouter, HTTPException, BackgroundTasks
    from pydantic import BaseModel

    router = APIRouter(prefix="/disaster-recovery", tags=["disaster-recovery"])

    class CreateBackupRequest(BaseModel):
        backup_type: str = "config"
        description: str = ""

    @router.get("/status")
    async def dr_status():
        """Get disaster recovery status."""
        manager = get_dr_manager()
        return manager.get_status()

    @router.post("/backups")
    async def create_backup(request: CreateBackupRequest):
        """Create a new backup."""
        manager = get_dr_manager()

        try:
            backup_type = BackupType(request.backup_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid backup type: {request.backup_type}")

        backup = await manager.create_backup(
            backup_type=backup_type,
            description=request.description,
        )

        return {
            "backup_id": backup.backup_id,
            "type": backup.backup_type.value,
            "size_bytes": backup.size_bytes,
            "components": backup.components,
        }

    @router.get("/backups")
    async def list_backups():
        """List all backups."""
        manager = get_dr_manager()
        return {"backups": manager.list_backups()}

    @router.post("/backups/{backup_id}/restore")
    async def restore_backup(backup_id: str):
        """Restore from a backup."""
        manager = get_dr_manager()
        result = await manager.restore_backup(backup_id)
        return result

    @router.get("/health-check")
    async def health_check():
        """Check health of all monitored services."""
        manager = get_dr_manager()
        return await manager.check_service_health()

    @router.post("/recovery-point")
    async def create_recovery_point(description: str = ""):
        """Create a recovery point."""
        manager = get_dr_manager()
        point = await manager.create_recovery_point(description)
        return {
            "point_id": point.point_id,
            "created_at": point.created_at.isoformat(),
            "description": point.description,
        }

    @router.get("/recovery-points")
    async def list_recovery_points():
        """List recovery points."""
        manager = get_dr_manager()
        return {
            "recovery_points": [
                {
                    "point_id": rp.point_id,
                    "created_at": rp.created_at.isoformat(),
                    "description": rp.description,
                }
                for rp in manager.recovery_points
            ]
        }

    return router
