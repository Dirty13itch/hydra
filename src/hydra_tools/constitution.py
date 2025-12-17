"""
Hydra Constitutional Enforcement Module

This module enforces immutable safety constraints that enable aggressive
autonomous operation. It provides:
- Constraint checking before dangerous operations
- Audit logging of all actions
- Emergency stop capabilities
- Self-improvement guardrails

The constitution is loaded from CONSTITUTION.yaml and cannot be modified
by any autonomous process.
"""

import yaml
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from functools import wraps
import hashlib

# Configure logging
logger = logging.getLogger(__name__)

class EnforcementLevel(Enum):
    """Enforcement action levels"""
    HARD_BLOCK = "hard_block"      # Operation completely prevented
    SOFT_BLOCK = "soft_block"      # Requires confirmation/delay
    AUDIT_ONLY = "audit_only"      # Allowed but logged

class OperationResult(Enum):
    """Result of constitutional check"""
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    REQUIRES_APPROVAL = "requires_approval"

@dataclass
class AuditEntry:
    """Audit log entry"""
    timestamp: str
    operation_type: str
    target_resource: str
    actor: str  # "autonomous" or "human:name"
    result: str  # "success", "blocked", "failed"
    constraint_id: Optional[str] = None
    constraint_rule: Optional[str] = None
    rollback_available: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConstitutionalCheck:
    """Result of a constitutional constraint check"""
    allowed: bool
    enforcement_level: EnforcementLevel
    constraint_id: Optional[str] = None
    constraint_rule: Optional[str] = None
    message: str = ""

class ConstitutionalEnforcer:
    """
    Enforces Hydra's constitutional constraints.

    This class loads the constitution from YAML and provides methods to:
    - Check if operations are allowed
    - Log all actions for audit
    - Enforce safety constraints
    """

    def __init__(self, constitution_path: Optional[str] = None):
        """Initialize the enforcer with constitution file"""
        if constitution_path is None:
            # Default locations to search (including Docker mount path)
            search_paths = [
                "/app/repo/CONSTITUTION.yaml",  # Docker mount in hydra-tools-api
                "/mnt/user/appdata/hydra-dev/CONSTITUTION.yaml",  # Host path
                "./CONSTITUTION.yaml",
                os.path.expanduser("~/.hydra/CONSTITUTION.yaml"),
            ]
            for path in search_paths:
                if os.path.exists(path):
                    constitution_path = path
                    break

        self.constitution_path = constitution_path
        self.constitution: Dict[str, Any] = {}
        self.audit_log: List[AuditEntry] = []
        self.audit_file: Optional[Path] = None
        self._constitution_hash: Optional[str] = None
        self._emergency_stop = False

        self._load_constitution()
        self._setup_audit_log()

    def _load_constitution(self) -> None:
        """Load constitution from YAML file"""
        if not self.constitution_path or not os.path.exists(self.constitution_path):
            logger.warning(f"Constitution file not found at {self.constitution_path}")
            self.constitution = self._default_constitution()
            return

        try:
            with open(self.constitution_path, 'r') as f:
                content = f.read()
                self._constitution_hash = hashlib.sha256(content.encode()).hexdigest()
                self.constitution = yaml.safe_load(content)
            logger.info(f"Loaded constitution from {self.constitution_path}")
        except Exception as e:
            logger.error(f"Failed to load constitution: {e}")
            self.constitution = self._default_constitution()

    def _default_constitution(self) -> Dict[str, Any]:
        """Return minimal default constitution if file not found"""
        return {
            "version": "default",
            "immutable_constraints": {
                "data_protection": [
                    {"id": "DATA-001", "rule": "Never delete databases without human approval", "severity": "critical", "enforcement": "hard_block"}
                ],
                "security": [
                    {"id": "SEC-001", "rule": "Never disable authentication systems", "severity": "critical", "enforcement": "hard_block"}
                ]
            },
            "autonomous_operations": {
                "allowed": ["code_modifications", "config_file_updates", "documentation_updates"]
            }
        }

    def _setup_audit_log(self) -> None:
        """Setup audit log file"""
        audit_config = self.constitution.get("audit", {})
        log_location = audit_config.get("log_location", "/mnt/user/appdata/hydra-dev/logs/audit.log")

        self.audit_file = Path(log_location)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

    def check_operation(
        self,
        operation_type: str,
        target_resource: str,
        details: Optional[Dict[str, Any]] = None
    ) -> ConstitutionalCheck:
        """
        Check if an operation is allowed by the constitution.

        Args:
            operation_type: Type of operation (e.g., "database_delete", "service_restart")
            target_resource: Resource being operated on
            details: Additional context about the operation

        Returns:
            ConstitutionalCheck with result and enforcement info
        """
        if self._emergency_stop:
            return ConstitutionalCheck(
                allowed=False,
                enforcement_level=EnforcementLevel.HARD_BLOCK,
                message="Emergency stop is active. All autonomous operations halted."
            )

        # Check immutable constraints
        immutable = self.constitution.get("immutable_constraints", {})

        for category, constraints in immutable.items():
            if not isinstance(constraints, list):
                continue
            for constraint in constraints:
                if self._constraint_matches(constraint, operation_type, target_resource, details):
                    enforcement = EnforcementLevel(constraint.get("enforcement", "hard_block"))
                    return ConstitutionalCheck(
                        allowed=(enforcement == EnforcementLevel.AUDIT_ONLY),
                        enforcement_level=enforcement,
                        constraint_id=constraint.get("id"),
                        constraint_rule=constraint.get("rule"),
                        message=f"Blocked by constraint {constraint.get('id')}: {constraint.get('rule')}"
                    )

        # Check if operation is in supervised list
        supervised = self.constitution.get("supervised_operations", [])
        for op in supervised:
            if op.get("operation") == operation_type:
                return ConstitutionalCheck(
                    allowed=True,
                    enforcement_level=EnforcementLevel.AUDIT_ONLY,
                    message=f"Supervised operation: {op.get('requires', 'audit_log')}"
                )

        # Check if operation is in autonomous allowed list
        autonomous = self.constitution.get("autonomous_operations", {})
        allowed_ops = autonomous.get("allowed", [])

        if operation_type in allowed_ops:
            return ConstitutionalCheck(
                allowed=True,
                enforcement_level=EnforcementLevel.AUDIT_ONLY,
                message="Autonomous operation allowed"
            )

        # Default: allow with audit
        return ConstitutionalCheck(
            allowed=True,
            enforcement_level=EnforcementLevel.AUDIT_ONLY,
            message="Operation allowed (not explicitly constrained)"
        )

    def _constraint_matches(
        self,
        constraint: Dict[str, Any],
        operation_type: str,
        target_resource: str,
        details: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if a constraint matches the operation"""
        rule = constraint.get("rule", "").lower()
        constraint_id = constraint.get("id", "")

        # Pattern matching for common constraint types
        patterns = {
            "DATA-001": operation_type == "database_delete" and "database" in target_resource.lower(),
            "DATA-002": operation_type in ["table_drop", "collection_drop"],
            "DATA-003": operation_type in ["database_delete", "table_drop"] and not (details or {}).get("backup_created"),
            "SEC-001": operation_type == "auth_disable",
            "SEC-002": operation_type == "secret_expose",
            "SEC-003": operation_type == "firewall_modify" and "allow_all" in str(details),
            "INFRA-001": operation_type == "network_modify",
            "INFRA-002": operation_type == "nixos_delete",
            "AUTO-001": target_resource == "CONSTITUTION.yaml" and operation_type in ["file_modify", "file_delete"],
            "GIT-001": operation_type == "git_force_push",
            "GIT-002": operation_type == "git_commit" and "secret" in str(details).lower(),
        }

        return patterns.get(constraint_id, False)

    def log_action(
        self,
        operation_type: str,
        target_resource: str,
        actor: str = "autonomous",
        result: str = "success",
        constraint_id: Optional[str] = None,
        constraint_rule: Optional[str] = None,
        rollback_available: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Log an action to the audit trail.

        Args:
            operation_type: Type of operation performed
            target_resource: Resource that was operated on
            actor: Who performed the action ("autonomous" or "human:name")
            result: Result of the operation ("success", "blocked", "failed")
            constraint_id: If blocked, which constraint
            constraint_rule: If blocked, what rule
            rollback_available: Whether rollback is possible
            details: Additional context

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            operation_type=operation_type,
            target_resource=target_resource,
            actor=actor,
            result=result,
            constraint_id=constraint_id,
            constraint_rule=constraint_rule,
            rollback_available=rollback_available,
            details=details or {}
        )

        self.audit_log.append(entry)

        # Persist to file
        if self.audit_file:
            try:
                with open(self.audit_file, 'a') as f:
                    f.write(json.dumps(asdict(entry)) + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

        # Check if we should alert
        if result == "blocked":
            self._send_alert(entry)

        return entry

    def _send_alert(self, entry: AuditEntry) -> None:
        """Send alert for blocked operations"""
        alert_config = self.constitution.get("audit", {}).get("alert_on", [])

        if "constraint_violation_attempt" in alert_config:
            logger.warning(f"CONSTITUTIONAL VIOLATION ATTEMPT: {entry.constraint_id} - {entry.operation_type} on {entry.target_resource}")
            # Could integrate with Discord/alertmanager here

    def emergency_stop(self) -> None:
        """Activate emergency stop - halt all autonomous operations"""
        self._emergency_stop = True
        self.log_action(
            operation_type="emergency_stop",
            target_resource="hydra_system",
            actor="autonomous",
            result="success",
            details={"reason": "Emergency stop activated"}
        )
        logger.critical("EMERGENCY STOP ACTIVATED - All autonomous operations halted")

    def emergency_resume(self, actor: str = "human:unknown") -> None:
        """Resume operations after emergency stop (requires human)"""
        if not actor.startswith("human:"):
            raise PermissionError("Only humans can resume after emergency stop")

        self._emergency_stop = False
        self.log_action(
            operation_type="emergency_resume",
            target_resource="hydra_system",
            actor=actor,
            result="success",
            details={"reason": "Emergency stop cleared by human"}
        )
        logger.info(f"Emergency stop cleared by {actor}")

    def get_audit_log(self, limit: int = 100, operation_type: Optional[str] = None) -> List[AuditEntry]:
        """Get recent audit log entries"""
        entries = self.audit_log

        if operation_type:
            entries = [e for e in entries if e.operation_type == operation_type]

        return entries[-limit:]

    def get_constitution_hash(self) -> str:
        """Get hash of current constitution for integrity checking"""
        return self._constitution_hash or "unknown"

    def verify_constitution_integrity(self) -> bool:
        """Verify constitution file hasn't been modified"""
        if not self.constitution_path or not os.path.exists(self.constitution_path):
            return False

        with open(self.constitution_path, 'r') as f:
            current_hash = hashlib.sha256(f.read().encode()).hexdigest()

        return current_hash == self._constitution_hash

    def check_self_improvement(
        self,
        file_path: str,
        modification_type: str
    ) -> ConstitutionalCheck:
        """
        Special check for self-improvement operations.

        Args:
            file_path: Path to file being modified
            modification_type: Type of modification

        Returns:
            ConstitutionalCheck result
        """
        self_improvement = self.constitution.get("self_improvement", {})

        # Check forbidden paths
        forbidden = self_improvement.get("forbidden_modifications", [])
        for pattern in forbidden:
            if pattern.replace("*", "") in file_path:
                return ConstitutionalCheck(
                    allowed=False,
                    enforcement_level=EnforcementLevel.HARD_BLOCK,
                    constraint_id="SELF-FORBIDDEN",
                    constraint_rule=f"Modification of {pattern} is forbidden",
                    message=f"Self-improvement cannot modify: {file_path}"
                )

        # Check allowed paths
        allowed = self_improvement.get("allowed_modifications", [])
        is_allowed = False
        for pattern in allowed:
            pattern_base = pattern.replace("**", "").replace("*", "")
            if pattern_base in file_path:
                is_allowed = True
                break

        if not is_allowed and allowed:  # Only enforce if allowed list exists
            return ConstitutionalCheck(
                allowed=False,
                enforcement_level=EnforcementLevel.HARD_BLOCK,
                constraint_id="SELF-SCOPE",
                constraint_rule="File outside allowed modification scope",
                message=f"Self-improvement cannot modify files outside allowed paths: {file_path}"
            )

        # Check if sandbox is required
        if self_improvement.get("sandbox_required", True):
            return ConstitutionalCheck(
                allowed=True,
                enforcement_level=EnforcementLevel.AUDIT_ONLY,
                message="Self-improvement allowed (sandbox required)"
            )

        return ConstitutionalCheck(
            allowed=True,
            enforcement_level=EnforcementLevel.AUDIT_ONLY,
            message="Self-improvement allowed"
        )


# Global enforcer instance
_enforcer: Optional[ConstitutionalEnforcer] = None

def get_enforcer() -> ConstitutionalEnforcer:
    """Get or create the global constitutional enforcer"""
    global _enforcer
    if _enforcer is None:
        _enforcer = ConstitutionalEnforcer()
    return _enforcer

def constitutional_check(operation_type: str):
    """
    Decorator for functions that need constitutional checking.

    Usage:
        @constitutional_check("database_delete")
        def delete_database(name: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            enforcer = get_enforcer()

            # Extract target resource from args/kwargs
            target = str(args[0]) if args else str(kwargs.get('target', 'unknown'))

            check = enforcer.check_operation(operation_type, target, kwargs)

            if not check.allowed:
                enforcer.log_action(
                    operation_type=operation_type,
                    target_resource=target,
                    result="blocked",
                    constraint_id=check.constraint_id,
                    constraint_rule=check.constraint_rule,
                    details=kwargs
                )
                raise PermissionError(check.message)

            # Execute the function
            try:
                result = func(*args, **kwargs)
                enforcer.log_action(
                    operation_type=operation_type,
                    target_resource=target,
                    result="success",
                    details=kwargs
                )
                return result
            except Exception as e:
                enforcer.log_action(
                    operation_type=operation_type,
                    target_resource=target,
                    result="failed",
                    details={"error": str(e), **kwargs}
                )
                raise

        return wrapper
    return decorator


# FastAPI router for constitutional endpoints
def create_constitution_router():
    """Create FastAPI router for constitutional endpoints"""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/constitution", tags=["constitution"])

    class OperationCheck(BaseModel):
        operation_type: str
        target_resource: str
        details: Optional[Dict[str, Any]] = None

    class EmergencyAction(BaseModel):
        actor: str

    @router.get("/status")
    async def get_status():
        """Get constitutional enforcer status"""
        enforcer = get_enforcer()
        return {
            "version": enforcer.constitution.get("version", "unknown"),
            "hash": enforcer.get_constitution_hash(),
            "integrity_valid": enforcer.verify_constitution_integrity(),
            "emergency_stop_active": enforcer._emergency_stop,
            "audit_entries": len(enforcer.audit_log)
        }

    @router.post("/check")
    async def check_operation(check: OperationCheck):
        """Check if an operation is allowed"""
        enforcer = get_enforcer()
        result = enforcer.check_operation(
            check.operation_type,
            check.target_resource,
            check.details
        )
        return {
            "allowed": result.allowed,
            "enforcement_level": result.enforcement_level.value,
            "constraint_id": result.constraint_id,
            "constraint_rule": result.constraint_rule,
            "message": result.message
        }

    @router.get("/audit")
    async def get_audit_log(limit: int = 100, operation_type: Optional[str] = None):
        """Get audit log entries"""
        enforcer = get_enforcer()
        entries = enforcer.get_audit_log(limit, operation_type)
        return {"entries": [asdict(e) for e in entries]}

    @router.post("/emergency/stop")
    async def emergency_stop():
        """Activate emergency stop"""
        enforcer = get_enforcer()
        enforcer.emergency_stop()
        return {"status": "emergency_stop_activated"}

    @router.post("/emergency/resume")
    async def emergency_resume(action: EmergencyAction):
        """Resume after emergency stop (requires human actor)"""
        enforcer = get_enforcer()
        try:
            enforcer.emergency_resume(action.actor)
            return {"status": "operations_resumed", "actor": action.actor}
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.get("/constraints")
    async def get_constraints():
        """Get all constitutional constraints"""
        enforcer = get_enforcer()
        return {
            "immutable_constraints": enforcer.constitution.get("immutable_constraints", {}),
            "supervised_operations": enforcer.constitution.get("supervised_operations", []),
            "autonomous_operations": enforcer.constitution.get("autonomous_operations", {})
        }

    return router
