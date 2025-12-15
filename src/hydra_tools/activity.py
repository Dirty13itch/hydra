"""
Hydra Activity Logging System

Unified activity log for all autonomous actions in the cluster.
Provides transparency into what the system is doing and why.

Features:
- PostgreSQL-backed activity log
- Real-time SSE streaming
- Decision chain tracking (parent/child relationships)
- Approval workflow support
- System control mode management

Usage:
    from hydra_tools.activity import ActivityLogger, get_activities

    logger = ActivityLogger()

    # Log an activity
    activity_id = await logger.log(
        source="n8n",
        source_id="workflow-123",
        action="container_restart",
        action_type="autonomous",
        target="hydra-litellm",
        decision_reason="Container unhealthy for 3+ minutes",
    )

    # Query activities
    activities = await get_activities(source="n8n", limit=50)
"""

import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator

import asyncpg


class ActionType(Enum):
    """Types of actions."""
    AUTONOMOUS = "autonomous"  # System-initiated
    TRIGGERED = "triggered"    # Webhook/alert triggered
    MANUAL = "manual"          # User-initiated
    SCHEDULED = "scheduled"    # Cron/schedule triggered


class ActionResult(Enum):
    """Possible action results."""
    OK = "ok"
    ERROR = "error"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SystemMode(Enum):
    """System automation modes."""
    FULL_AUTO = "full_auto"       # All automation active
    SUPERVISED = "supervised"     # Protected actions need approval
    NOTIFY_ONLY = "notify_only"   # Log but don't execute
    SAFE_MODE = "safe_mode"       # All automation disabled


@dataclass
class Activity:
    """Single activity record."""
    id: int | None = None
    timestamp: str | None = None
    source: str = ""
    source_id: str | None = None
    action: str = ""
    action_type: str = ""
    target: str | None = None
    params: dict | None = None
    result: str | None = None
    result_details: dict | None = None
    decision_reason: str | None = None
    parent_id: int | None = None
    requires_approval: bool = False
    approved_by: str | None = None
    approved_at: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ActivityLogger:
    """
    Logs activities to the unified activity database.
    """

    def __init__(
        self,
        postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
    ):
        self.postgres_url = postgres_url
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=1,
                max_size=5,
            )
        return self._pool

    async def log(
        self,
        source: str,
        action: str,
        action_type: str | ActionType,
        source_id: str | None = None,
        target: str | None = None,
        params: dict | None = None,
        result: str | ActionResult | None = None,
        result_details: dict | None = None,
        decision_reason: str | None = None,
        parent_id: int | None = None,
        requires_approval: bool = False,
    ) -> int:
        """
        Log a new activity.

        Args:
            source: Source system (n8n, alert, route, letta, mcp, user)
            action: Action name (container_restart, model_route, etc.)
            action_type: Type of action (autonomous, triggered, manual, scheduled)
            source_id: ID in source system (workflow ID, alert fingerprint)
            target: Target of action (container name, model name)
            params: Action parameters
            result: Result status (ok, error, pending)
            result_details: Result details
            decision_reason: Why this action was taken
            parent_id: Parent activity ID for causal chains
            requires_approval: Whether this action needs user approval

        Returns:
            Activity ID
        """
        pool = await self._get_pool()

        # Normalize enum values
        if isinstance(action_type, ActionType):
            action_type = action_type.value
        if isinstance(result, ActionResult):
            result = result.value

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO hydra_activity (
                    source, source_id, action, action_type, target,
                    params, result, result_details, decision_reason,
                    parent_id, requires_approval
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
                """,
                source,
                source_id,
                action,
                action_type,
                target,
                json.dumps(params) if params else None,
                result,
                json.dumps(result_details) if result_details else None,
                decision_reason,
                parent_id,
                requires_approval,
            )
            return row["id"]

    async def update_result(
        self,
        activity_id: int,
        result: str | ActionResult,
        result_details: dict | None = None,
    ) -> bool:
        """Update the result of an existing activity."""
        pool = await self._get_pool()

        if isinstance(result, ActionResult):
            result = result.value

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE hydra_activity
                SET result = $1, result_details = $2
                WHERE id = $3
                """,
                result,
                json.dumps(result_details) if result_details else None,
                activity_id,
            )
        return True

    async def approve(
        self,
        activity_id: int,
        approved_by: str = "user",
    ) -> bool:
        """Approve a pending activity."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE hydra_activity
                SET result = 'approved', approved_by = $1, approved_at = NOW()
                WHERE id = $2 AND requires_approval = TRUE AND result = 'pending'
                """,
                approved_by,
                activity_id,
            )
        return True

    async def reject(
        self,
        activity_id: int,
        rejected_by: str = "user",
        reason: str | None = None,
    ) -> bool:
        """Reject a pending activity."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE hydra_activity
                SET result = 'rejected',
                    approved_by = $1,
                    approved_at = NOW(),
                    result_details = result_details || $3
                WHERE id = $2 AND requires_approval = TRUE AND result = 'pending'
                """,
                rejected_by,
                activity_id,
                json.dumps({"rejection_reason": reason}) if reason else "{}",
            )
        return True

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None


async def get_activities(
    postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
    source: str | None = None,
    action_type: str | None = None,
    result: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    include_chain: bool = False,
) -> list[Activity]:
    """
    Query activities from the database.

    Args:
        source: Filter by source
        action_type: Filter by action type
        result: Filter by result
        since: Filter activities after this time
        until: Filter activities before this time
        limit: Maximum number of results
        offset: Pagination offset
        include_chain: Include parent/child chain

    Returns:
        List of Activity objects
    """
    conn = await asyncpg.connect(postgres_url)

    try:
        # Build query dynamically
        conditions = []
        params = []
        param_idx = 1

        if source:
            conditions.append(f"source = ${param_idx}")
            params.append(source)
            param_idx += 1

        if action_type:
            conditions.append(f"action_type = ${param_idx}")
            params.append(action_type)
            param_idx += 1

        if result:
            conditions.append(f"result = ${param_idx}")
            params.append(result)
            param_idx += 1

        if since:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(since)
            param_idx += 1

        if until:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(until)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT id, timestamp, source, source_id, action, action_type,
                   target, params, result, result_details, decision_reason,
                   parent_id, requires_approval, approved_by, approved_at
            FROM hydra_activity
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        activities = []
        for row in rows:
            activities.append(Activity(
                id=row["id"],
                timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
                source=row["source"],
                source_id=row["source_id"],
                action=row["action"],
                action_type=row["action_type"],
                target=row["target"],
                params=json.loads(row["params"]) if row["params"] else None,
                result=row["result"],
                result_details=json.loads(row["result_details"]) if row["result_details"] else None,
                decision_reason=row["decision_reason"],
                parent_id=row["parent_id"],
                requires_approval=row["requires_approval"],
                approved_by=row["approved_by"],
                approved_at=row["approved_at"].isoformat() if row["approved_at"] else None,
            ))

        return activities
    finally:
        await conn.close()


async def get_pending_approvals(
    postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
) -> list[Activity]:
    """Get all pending approval activities."""
    return await get_activities(
        postgres_url=postgres_url,
        result="pending",
        limit=100,
    )


async def get_activity_by_id(
    activity_id: int,
    postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
    include_chain: bool = False,
) -> Activity | None:
    """Get a single activity by ID, optionally with its chain."""
    conn = await asyncpg.connect(postgres_url)

    try:
        row = await conn.fetchrow(
            """
            SELECT id, timestamp, source, source_id, action, action_type,
                   target, params, result, result_details, decision_reason,
                   parent_id, requires_approval, approved_by, approved_at
            FROM hydra_activity
            WHERE id = $1
            """,
            activity_id,
        )

        if not row:
            return None

        activity = Activity(
            id=row["id"],
            timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
            source=row["source"],
            source_id=row["source_id"],
            action=row["action"],
            action_type=row["action_type"],
            target=row["target"],
            params=json.loads(row["params"]) if row["params"] else None,
            result=row["result"],
            result_details=json.loads(row["result_details"]) if row["result_details"] else None,
            decision_reason=row["decision_reason"],
            parent_id=row["parent_id"],
            requires_approval=row["requires_approval"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"].isoformat() if row["approved_at"] else None,
        )

        return activity
    finally:
        await conn.close()


class SystemControl:
    """
    Manages system control state (mode, workflow overrides).
    """

    def __init__(
        self,
        postgres_url: str = "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra",
    ):
        self.postgres_url = postgres_url

    async def get_mode(self) -> dict:
        """Get current system mode."""
        conn = await asyncpg.connect(self.postgres_url)

        try:
            row = await conn.fetchrow(
                "SELECT value, updated_at FROM hydra_control_state WHERE key = 'system_mode'"
            )

            if row:
                return {
                    "mode": json.loads(row["value"]),
                    "since": row["updated_at"].isoformat() if row["updated_at"] else None,
                }
            return {"mode": "full_auto", "since": None}
        finally:
            await conn.close()

    async def set_mode(
        self,
        mode: str | SystemMode,
        duration_seconds: int | None = None,
        set_by: str = "user",
    ) -> dict:
        """
        Set system mode.

        Args:
            mode: New mode to set
            duration_seconds: Auto-revert after this many seconds
            set_by: Who set this mode

        Returns:
            New mode state
        """
        if isinstance(mode, SystemMode):
            mode = mode.value

        conn = await asyncpg.connect(self.postgres_url)

        try:
            await conn.execute(
                """
                INSERT INTO hydra_control_state (key, value, updated_at, updated_by)
                VALUES ('system_mode', $1, NOW(), $2)
                ON CONFLICT (key) DO UPDATE
                SET value = $1, updated_at = NOW(), updated_by = $2
                """,
                json.dumps(mode),
                set_by,
            )

            # Log this as an activity
            logger = ActivityLogger(self.postgres_url)
            await logger.log(
                source="control",
                action="mode_change",
                action_type=ActionType.MANUAL,
                target=mode,
                params={"duration_seconds": duration_seconds},
                result=ActionResult.OK,
                decision_reason=f"User requested mode change to {mode}",
            )
            await logger.close()

            return await self.get_mode()
        finally:
            await conn.close()

    async def is_action_allowed(self, action: str, target: str | None = None) -> dict:
        """
        Check if an action is allowed under current mode.

        Returns:
            {"allowed": bool, "reason": str, "requires_approval": bool}
        """
        mode_info = await self.get_mode()
        mode = mode_info["mode"]

        # Safe mode blocks everything
        if mode == "safe_mode":
            return {
                "allowed": False,
                "reason": "System is in safe mode - all automation disabled",
                "requires_approval": False,
            }

        # Notify only mode logs but doesn't execute
        if mode == "notify_only":
            return {
                "allowed": False,
                "reason": "System is in notify-only mode - actions logged but not executed",
                "requires_approval": False,
            }

        # Supervised mode requires approval for protected actions
        protected_actions = [
            "container_restart",
            "memory_update",
            "disk_cleanup",
            "model_switch",
        ]

        if mode == "supervised" and action in protected_actions:
            return {
                "allowed": True,
                "reason": "Action requires approval in supervised mode",
                "requires_approval": True,
            }

        # Full auto allows everything
        return {
            "allowed": True,
            "reason": "Action permitted in current mode",
            "requires_approval": False,
        }


# FastAPI Router
def create_activity_router():
    """Create FastAPI router for activity endpoints."""
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel

    router = APIRouter(prefix="/activity", tags=["activity"])

    class LogActivityRequest(BaseModel):
        source: str
        source_id: str | None = None
        action: str
        action_type: str
        target: str | None = None
        params: dict | None = None
        result: str | None = None
        result_details: dict | None = None
        decision_reason: str | None = None
        parent_id: int | None = None
        requires_approval: bool = False

    class UpdateResultRequest(BaseModel):
        result: str
        result_details: dict | None = None

    class ApprovalRequest(BaseModel):
        approved_by: str = "user"
        reason: str | None = None

    @router.post("")
    async def log_activity(req: LogActivityRequest):
        """Log a new activity."""
        logger = ActivityLogger()
        try:
            activity_id = await logger.log(
                source=req.source,
                source_id=req.source_id,
                action=req.action,
                action_type=req.action_type,
                target=req.target,
                params=req.params,
                result=req.result,
                result_details=req.result_details,
                decision_reason=req.decision_reason,
                parent_id=req.parent_id,
                requires_approval=req.requires_approval,
            )
            return {"id": activity_id, "status": "logged"}
        finally:
            await logger.close()

    @router.get("")
    async def query_activities(
        source: str | None = None,
        action_type: str | None = None,
        result: str | None = None,
        since: str | None = None,
        limit: int = Query(default=100, le=500),
        offset: int = 0,
    ):
        """Query activities with filters."""
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

        activities = await get_activities(
            source=source,
            action_type=action_type,
            result=result,
            since=since_dt,
            limit=limit,
            offset=offset,
        )

        return {
            "activities": [a.to_dict() for a in activities],
            "count": len(activities),
        }

    @router.get("/pending")
    async def get_pending():
        """Get all pending approval activities."""
        activities = await get_pending_approvals()
        return {
            "pending": [a.to_dict() for a in activities],
            "count": len(activities),
        }

    @router.get("/{activity_id}")
    async def get_activity(activity_id: int, include_chain: bool = False):
        """Get a single activity by ID."""
        activity = await get_activity_by_id(activity_id, include_chain=include_chain)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        return activity.to_dict()

    @router.put("/{activity_id}/result")
    async def update_activity_result(activity_id: int, req: UpdateResultRequest):
        """Update the result of an activity."""
        logger = ActivityLogger()
        try:
            await logger.update_result(
                activity_id=activity_id,
                result=req.result,
                result_details=req.result_details,
            )
            return {"status": "updated"}
        finally:
            await logger.close()

    @router.post("/{activity_id}/approve")
    async def approve_activity(activity_id: int, req: ApprovalRequest):
        """Approve a pending activity."""
        logger = ActivityLogger()
        try:
            await logger.approve(activity_id, req.approved_by)
            return {"status": "approved"}
        finally:
            await logger.close()

    @router.post("/{activity_id}/reject")
    async def reject_activity(activity_id: int, req: ApprovalRequest):
        """Reject a pending activity."""
        logger = ActivityLogger()
        try:
            await logger.reject(activity_id, req.approved_by, req.reason)
            return {"status": "rejected"}
        finally:
            await logger.close()

    return router


def create_control_router():
    """Create FastAPI router for control endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/control", tags=["control"])

    class SetModeRequest(BaseModel):
        mode: str
        duration_seconds: int | None = None
        set_by: str = "user"

    class CheckActionRequest(BaseModel):
        action: str
        target: str | None = None

    @router.get("/mode")
    async def get_mode():
        """Get current system mode."""
        control = SystemControl()
        return await control.get_mode()

    @router.post("/mode")
    async def set_mode(req: SetModeRequest):
        """Set system mode."""
        control = SystemControl()
        return await control.set_mode(
            mode=req.mode,
            duration_seconds=req.duration_seconds,
            set_by=req.set_by,
        )

    @router.post("/check-action")
    async def check_action(req: CheckActionRequest):
        """Check if an action is allowed under current mode."""
        control = SystemControl()
        return await control.is_action_allowed(req.action, req.target)

    @router.post("/emergency-stop")
    async def emergency_stop():
        """Emergency stop - set safe mode immediately."""
        control = SystemControl()
        result = await control.set_mode(
            mode=SystemMode.SAFE_MODE,
            set_by="emergency_stop",
        )

        # Log as high-priority activity
        logger = ActivityLogger()
        await logger.log(
            source="control",
            action="emergency_stop",
            action_type=ActionType.MANUAL,
            target="system",
            result=ActionResult.OK,
            decision_reason="User triggered emergency stop",
        )
        await logger.close()

        return {
            "status": "safe_mode_activated",
            "mode": result,
            "message": "All automation has been disabled. Use /control/mode to restore.",
        }

    return router


if __name__ == "__main__":
    # Test the activity logger
    import asyncio

    async def test():
        logger = ActivityLogger()

        # Log a test activity
        activity_id = await logger.log(
            source="test",
            action="test_action",
            action_type=ActionType.MANUAL,
            target="test_target",
            params={"test": True},
            result=ActionResult.OK,
            decision_reason="Testing the activity logger",
        )
        print(f"Logged activity: {activity_id}")

        # Query activities
        activities = await get_activities(source="test", limit=5)
        print(f"Found {len(activities)} test activities")
        for a in activities:
            print(f"  - {a.id}: {a.action} @ {a.timestamp}")

        # Test system control
        control = SystemControl()
        mode = await control.get_mode()
        print(f"Current mode: {mode}")

        await logger.close()

    asyncio.run(test())
