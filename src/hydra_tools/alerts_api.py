"""
Alerts API Router

Exposes alert management and notification routing capabilities.
Integrates with the hydra_alerts webhook receiver for unified alert handling.

Endpoints:
- /alerts/recent - Get recent alerts from log
- /alerts/send - Send a custom alert to notification channels
- /alerts/test - Send a test alert
- /alerts/status - Get alerting system status
- /alerts/silences - List active Alertmanager silences
- /alerts/silence - Create a new silence
- /alerts/silence/{id} - Delete a silence
"""

import json
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("alerts_api")


# Configuration
ALERTS_SERVICE_URL = os.getenv("ALERTS_SERVICE_URL", "http://192.168.1.244:9093")
DISCORD_NOTIFY_URL = os.getenv("DISCORD_NOTIFY_URL", "http://192.168.1.244:5678/webhook/discord-notify")
ALERT_LOG_DIR = Path(os.getenv("ALERT_LOG_DIR", "/var/log/hydra-alerts"))


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    FIRING = "firing"
    RESOLVED = "resolved"


class SendAlertRequest(BaseModel):
    """Request to send an alert."""
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message/description")
    severity: AlertSeverity = Field(AlertSeverity.INFO, description="Alert severity")
    node: Optional[str] = Field(None, description="Node the alert relates to")
    service: Optional[str] = Field(None, description="Service the alert relates to")
    labels: Optional[Dict[str, str]] = Field(None, description="Additional labels")
    channel: Optional[str] = Field("discord", description="Notification channel (discord, slack, all)")


class AlertLogEntry(BaseModel):
    """An alert log entry."""
    timestamp: str
    channel: str
    receiver: Optional[str] = None
    alertname: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    node: Optional[str] = None
    summary: Optional[str] = None


class AlertsResponse(BaseModel):
    """Response containing alerts."""
    alerts: List[AlertLogEntry]
    count: int


class AlertSystemStatus(BaseModel):
    """Status of the alerting system."""
    alerts_service_healthy: bool
    discord_webhook_configured: bool
    slack_webhook_configured: bool
    log_directory_writable: bool
    recent_alert_count: int
    last_alert_timestamp: Optional[str] = None


# =============================================================================
# ALERTMANAGER SILENCE MODELS
# =============================================================================

class SilenceMatcher(BaseModel):
    """A matcher for silence rules."""
    name: str = Field(..., description="Label name to match (e.g., 'alertname', 'node', 'service')")
    value: str = Field(..., description="Label value to match")
    isRegex: bool = Field(False, description="Whether value is a regex pattern")
    isEqual: bool = Field(True, description="Whether to match equal (True) or not equal (False)")


class CreateSilenceRequest(BaseModel):
    """Request to create an Alertmanager silence."""
    matchers: List[SilenceMatcher] = Field(..., description="List of label matchers")
    duration_minutes: int = Field(60, ge=1, le=10080, description="Duration in minutes (max 7 days)")
    comment: str = Field("Silenced via Hydra API", description="Comment explaining the silence")
    created_by: str = Field("hydra-api", description="Who created the silence")


class SilenceResponse(BaseModel):
    """Response from silence operations."""
    id: str
    status: str
    matchers: List[Dict[str, Any]]
    starts_at: str
    ends_at: str
    created_by: str
    comment: str


class SilenceListResponse(BaseModel):
    """Response containing list of silences."""
    silences: List[SilenceResponse]
    count: int
    active_count: int


def _get_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_alerts_router() -> APIRouter:
    """Create and configure the alerts API router."""
    router = APIRouter(prefix="/alerts", tags=["alerts"])

    @router.get("/recent", response_model=AlertsResponse)
    async def get_recent_alerts(
        limit: int = 50,
        severity: Optional[AlertSeverity] = None,
        node: Optional[str] = None,
    ):
        """
        Get recent alerts from the log.

        Returns alerts from today's log file, optionally filtered by severity or node.
        """
        log_file = ALERT_LOG_DIR / f"alerts-{datetime.now().strftime('%Y-%m-%d')}.log"

        alerts = []
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            # Apply filters
                            if severity and entry.get("severity") != severity.value:
                                continue
                            if node and entry.get("node") != node:
                                continue
                            alerts.append(AlertLogEntry(**entry))
                        except (json.JSONDecodeError, Exception):
                            continue
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to read alerts: {e}")

        # Return most recent first, limited
        alerts = list(reversed(alerts[-limit:]))

        return AlertsResponse(alerts=alerts, count=len(alerts))

    @router.post("/send")
    async def send_alert(request: SendAlertRequest):
        """
        Send a custom alert to notification channels.

        Routes to Discord, Slack, or both based on channel parameter.
        """
        # Build Discord embed format
        color_map = {
            AlertSeverity.INFO: 0x0000FF,
            AlertSeverity.WARNING: 0xFFA500,
            AlertSeverity.CRITICAL: 0xFF0000,
        }

        emoji_map = {
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.CRITICAL: ":rotating_light:",
        }

        payload = {
            "severity": request.severity.value,
            "title": request.title,
            "message": request.message,
            "embed": {
                "title": f"{emoji_map[request.severity]} {request.title}",
                "description": request.message,
                "color": color_map[request.severity],
                "fields": [],
                "timestamp": _get_timestamp(),
                "footer": {"text": "Hydra Alert System"},
            }
        }

        if request.node:
            payload["embed"]["fields"].append({
                "name": "Node",
                "value": request.node,
                "inline": True
            })

        if request.service:
            payload["embed"]["fields"].append({
                "name": "Service",
                "value": request.service,
                "inline": True
            })

        if request.labels:
            for key, value in list(request.labels.items())[:5]:
                payload["embed"]["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })

        # Send to Discord via n8n webhook
        results = {"discord": None, "slack": None}

        async with httpx.AsyncClient(timeout=10.0) as client:
            if request.channel in ("discord", "all"):
                try:
                    resp = await client.post(
                        DISCORD_NOTIFY_URL,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    results["discord"] = "sent" if resp.status_code < 400 else f"error: {resp.status_code}"
                except Exception as e:
                    results["discord"] = f"error: {str(e)}"

            # Add Slack support if configured
            # results["slack"] = await send_to_slack(payload)

        # Log the alert
        log_entry = {
            "timestamp": _get_timestamp(),
            "channel": request.channel,
            "alertname": request.title,
            "status": "firing",
            "severity": request.severity.value,
            "node": request.node,
            "summary": request.message,
        }

        try:
            ALERT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = ALERT_LOG_DIR / f"alerts-{datetime.now().strftime('%Y-%m-%d')}.log"
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass  # Non-fatal if logging fails

        return {
            "status": "sent",
            "results": results,
            "timestamp": _get_timestamp(),
        }

    @router.post("/test")
    async def send_test_alert():
        """
        Send a test alert to verify notification channels.

        Sends an INFO-level test alert to Discord.
        """
        request = SendAlertRequest(
            title="Test Alert",
            message="This is a test alert from the Hydra Alert System.",
            severity=AlertSeverity.INFO,
            service="hydra-alerts-api",
            labels={"test": "true"},
        )
        return await send_alert(request)

    @router.get("/status", response_model=AlertSystemStatus)
    async def get_alert_status():
        """
        Get the status of the alerting system.

        Checks connectivity to notification services and log availability.
        """
        status = AlertSystemStatus(
            alerts_service_healthy=False,
            discord_webhook_configured=bool(DISCORD_NOTIFY_URL),
            slack_webhook_configured=False,
            log_directory_writable=False,
            recent_alert_count=0,
            last_alert_timestamp=None,
        )

        # Check alerts service (Alertmanager uses /-/healthy endpoint)
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{ALERTS_SERVICE_URL}/-/healthy")
                status.alerts_service_healthy = resp.status_code == 200
            except Exception:
                pass

        # Check log directory
        try:
            ALERT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            test_file = ALERT_LOG_DIR / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            status.log_directory_writable = True
        except Exception:
            pass

        # Count recent alerts
        log_file = ALERT_LOG_DIR / f"alerts-{datetime.now().strftime('%Y-%m-%d')}.log"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    status.recent_alert_count = len(lines)
                    if lines:
                        last = json.loads(lines[-1])
                        status.last_alert_timestamp = last.get("timestamp")
            except Exception:
                pass

        return status

    @router.get("/channels")
    async def list_channels():
        """
        List available notification channels.

        Returns configured channels and their status.
        """
        channels = {
            "discord": {
                "configured": bool(DISCORD_NOTIFY_URL),
                "webhook_url": DISCORD_NOTIFY_URL[:50] + "..." if len(DISCORD_NOTIFY_URL) > 50 else DISCORD_NOTIFY_URL,
                "via": "n8n webhook",
            },
            "slack": {
                "configured": False,
                "webhook_url": None,
                "via": "direct webhook",
            },
            "file": {
                "configured": True,
                "log_directory": str(ALERT_LOG_DIR),
                "via": "local filesystem",
            },
        }

        return {"channels": channels}

    # =========================================================================
    # ALERTMANAGER SILENCE ENDPOINTS
    # =========================================================================

    @router.get("/silences", response_model=SilenceListResponse)
    async def list_silences(active_only: bool = True):
        """
        List Alertmanager silences.

        Returns all silences or only active ones based on the active_only parameter.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{ALERTS_SERVICE_URL}/api/v2/silences")
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Alertmanager returned error: {resp.text}"
                    )

                all_silences = resp.json()
                silences = []
                active_count = 0

                for s in all_silences:
                    status = s.get("status", {}).get("state", "unknown")
                    if status == "active":
                        active_count += 1

                    if active_only and status != "active":
                        continue

                    silences.append(SilenceResponse(
                        id=s.get("id", ""),
                        status=status,
                        matchers=s.get("matchers", []),
                        starts_at=s.get("startsAt", ""),
                        ends_at=s.get("endsAt", ""),
                        created_by=s.get("createdBy", "unknown"),
                        comment=s.get("comment", ""),
                    ))

                return SilenceListResponse(
                    silences=silences,
                    count=len(silences),
                    active_count=active_count,
                )

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to Alertmanager: {str(e)}"
                )

    @router.post("/silence", response_model=SilenceResponse)
    async def create_silence(request: CreateSilenceRequest):
        """
        Create an Alertmanager silence.

        Silences matching alerts for the specified duration.
        Matchers define which alerts to silence based on label matching.
        """
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(minutes=request.duration_minutes)

        # Build Alertmanager silence payload
        silence_payload = {
            "matchers": [
                {
                    "name": m.name,
                    "value": m.value,
                    "isRegex": m.isRegex,
                    "isEqual": m.isEqual,
                }
                for m in request.matchers
            ],
            "startsAt": now.isoformat().replace("+00:00", "Z"),
            "endsAt": ends_at.isoformat().replace("+00:00", "Z"),
            "createdBy": request.created_by,
            "comment": request.comment,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{ALERTS_SERVICE_URL}/api/v2/silences",
                    json=silence_payload,
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code not in (200, 201):
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Alertmanager returned error: {resp.text}"
                    )

                result = resp.json()
                silence_id = result.get("silenceID", result.get("id", ""))

                logger.info(f"Created silence {silence_id} for {request.duration_minutes} minutes")

                return SilenceResponse(
                    id=silence_id,
                    status="active",
                    matchers=[m.model_dump() for m in request.matchers],
                    starts_at=silence_payload["startsAt"],
                    ends_at=silence_payload["endsAt"],
                    created_by=request.created_by,
                    comment=request.comment,
                )

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to Alertmanager: {str(e)}"
                )

    @router.delete("/silence/{silence_id}")
    async def delete_silence(silence_id: str):
        """
        Delete (expire) an Alertmanager silence.

        This immediately expires the silence, allowing matching alerts to fire again.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.delete(
                    f"{ALERTS_SERVICE_URL}/api/v2/silence/{silence_id}"
                )

                if resp.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Silence {silence_id} not found"
                    )

                if resp.status_code not in (200, 204):
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Alertmanager returned error: {resp.text}"
                    )

                logger.info(f"Deleted silence {silence_id}")

                return {
                    "status": "deleted",
                    "silence_id": silence_id,
                    "message": "Silence has been expired",
                }

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to Alertmanager: {str(e)}"
                )

    # =========================================================================
    # CONVENIENCE SILENCE ENDPOINTS
    # =========================================================================

    @router.post("/silence/alert/{alertname}")
    async def silence_by_alertname(
        alertname: str,
        duration_minutes: int = 60,
        comment: Optional[str] = None,
    ):
        """
        Silence a specific alert by name.

        Convenience endpoint to silence all instances of a specific alert.
        """
        request = CreateSilenceRequest(
            matchers=[
                SilenceMatcher(name="alertname", value=alertname, isRegex=False, isEqual=True)
            ],
            duration_minutes=duration_minutes,
            comment=comment or f"Silencing {alertname} via Hydra API",
            created_by="hydra-api",
        )
        return await create_silence(request)

    @router.post("/silence/node/{node}")
    async def silence_by_node(
        node: str,
        duration_minutes: int = 60,
        comment: Optional[str] = None,
    ):
        """
        Silence all alerts for a specific node.

        Useful during planned maintenance on a specific node.
        """
        request = CreateSilenceRequest(
            matchers=[
                SilenceMatcher(name="node", value=node, isRegex=False, isEqual=True)
            ],
            duration_minutes=duration_minutes,
            comment=comment or f"Silencing all alerts for node {node}",
            created_by="hydra-api",
        )
        return await create_silence(request)

    @router.post("/silence/service/{service}")
    async def silence_by_service(
        service: str,
        duration_minutes: int = 60,
        comment: Optional[str] = None,
    ):
        """
        Silence all alerts for a specific service.

        Useful during service deployments or known maintenance.
        """
        request = CreateSilenceRequest(
            matchers=[
                SilenceMatcher(name="service", value=service, isRegex=False, isEqual=True)
            ],
            duration_minutes=duration_minutes,
            comment=comment or f"Silencing all alerts for service {service}",
            created_by="hydra-api",
        )
        return await create_silence(request)

    @router.post("/silence/maintenance")
    async def silence_for_maintenance(
        nodes: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        duration_minutes: int = 120,
        comment: Optional[str] = None,
    ):
        """
        Create silences for planned maintenance.

        Silences alerts for specified nodes and/or services.
        If neither is specified, silences all non-critical alerts.
        """
        created_silences = []

        if nodes:
            for node in nodes:
                result = await silence_by_node(
                    node=node,
                    duration_minutes=duration_minutes,
                    comment=comment or f"Planned maintenance on {node}",
                )
                created_silences.append({"type": "node", "target": node, "silence_id": result.id})

        if services:
            for service in services:
                result = await silence_by_service(
                    service=service,
                    duration_minutes=duration_minutes,
                    comment=comment or f"Planned maintenance for {service}",
                )
                created_silences.append({"type": "service", "target": service, "silence_id": result.id})

        # If nothing specified, silence all warnings (not criticals)
        if not nodes and not services:
            request = CreateSilenceRequest(
                matchers=[
                    SilenceMatcher(name="severity", value="warning", isRegex=False, isEqual=True)
                ],
                duration_minutes=duration_minutes,
                comment=comment or "General maintenance - silencing warnings",
                created_by="hydra-api",
            )
            result = await create_silence(request)
            created_silences.append({"type": "severity", "target": "warning", "silence_id": result.id})

        return {
            "status": "silenced",
            "duration_minutes": duration_minutes,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat(),
            "silences_created": len(created_silences),
            "silences": created_silences,
        }

    @router.get("/silence/check/{alertname}")
    async def check_if_silenced(alertname: str):
        """
        Check if a specific alert is currently silenced.

        Returns silence information if the alert is silenced, or indicates it's active.
        """
        silences = await list_silences(active_only=True)

        matching_silences = []
        for silence in silences.silences:
            for matcher in silence.matchers:
                if matcher.get("name") == "alertname" and matcher.get("value") == alertname:
                    matching_silences.append(silence)
                    break

        if matching_silences:
            return {
                "alertname": alertname,
                "is_silenced": True,
                "silences": [s.model_dump() for s in matching_silences],
            }
        else:
            return {
                "alertname": alertname,
                "is_silenced": False,
                "silences": [],
            }

    return router
