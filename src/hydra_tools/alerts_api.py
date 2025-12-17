"""
Alerts API Router

Exposes alert management and notification routing capabilities.
Integrates with the hydra_alerts webhook receiver for unified alert handling.

Endpoints:
- /alerts/recent - Get recent alerts from log
- /alerts/send - Send a custom alert to notification channels
- /alerts/test - Send a test alert
- /alerts/status - Get alerting system status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


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

    @router.post("/silence")
    async def silence_alert(
        alertname: str,
        duration_minutes: int = 60,
        comment: Optional[str] = None,
    ):
        """
        Silence an alert for a specified duration.

        Note: This is a placeholder - actual silencing requires Alertmanager integration.
        """
        # This would integrate with Alertmanager's silence API
        # For now, just log the request
        return {
            "status": "silenced",
            "alertname": alertname,
            "duration_minutes": duration_minutes,
            "expires_at": datetime.utcnow().isoformat() + "Z",
            "comment": comment,
            "note": "Alertmanager integration pending",
        }

    return router
