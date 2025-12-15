#!/usr/bin/env python3
"""
Hydra Alert Webhook Receiver

Receives webhooks from Alertmanager and forwards to notification channels.
Supports Discord, Slack, and file logging.

Run with: uvicorn hydra_alerts.webhook:app --host 0.0.0.0 --port 9095
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Configuration
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
LOG_DIR = Path(os.getenv("ALERT_LOG_DIR", "/var/log/hydra-alerts"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hydra-alerts")


# Models
class Alert(BaseModel):
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: str


class AlertmanagerPayload(BaseModel):
    receiver: str
    status: str
    alerts: List[Alert]
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    version: str
    groupKey: str


app = FastAPI(title="Hydra Alert Webhook", version="1.0.0")


def severity_emoji(severity: str) -> str:
    """Get emoji for severity level."""
    return {
        "critical": "🔴",
        "warning": "🟠",
        "info": "🔵",
    }.get(severity, "⚪")


def status_emoji(status: str) -> str:
    """Get emoji for alert status."""
    return "🟢" if status == "resolved" else "🔴"


def format_discord_message(payload: AlertmanagerPayload) -> Dict[str, Any]:
    """Format payload for Discord webhook."""
    embeds = []

    for alert in payload.alerts:
        severity = alert.labels.get("severity", "info")
        alertname = alert.labels.get("alertname", "Unknown")
        node = alert.labels.get("node", "cluster")

        color = {
            "critical": 0xFF0000,
            "warning": 0xFFA500,
            "info": 0x0000FF,
        }.get(severity, 0x808080)

        if alert.status == "resolved":
            color = 0x00FF00

        embed = {
            "title": f"{status_emoji(alert.status)} {alertname}",
            "color": color,
            "fields": [
                {"name": "Status", "value": alert.status.title(), "inline": True},
                {"name": "Severity", "value": severity.title(), "inline": True},
                {"name": "Node", "value": node, "inline": True},
            ],
            "timestamp": alert.startsAt,
        }

        if summary := alert.annotations.get("summary"):
            embed["description"] = summary

        if description := alert.annotations.get("description"):
            embed["fields"].append({
                "name": "Details",
                "value": description[:1024],
                "inline": False,
            })

        embeds.append(embed)

    return {
        "username": "Hydra Alerts",
        "avatar_url": "https://raw.githubusercontent.com/prometheus/prometheus/main/documentation/images/prometheus-logo.svg",
        "embeds": embeds[:10],  # Discord limit
    }


def format_slack_message(payload: AlertmanagerPayload) -> Dict[str, Any]:
    """Format payload for Slack webhook."""
    attachments = []

    for alert in payload.alerts:
        severity = alert.labels.get("severity", "info")
        alertname = alert.labels.get("alertname", "Unknown")
        node = alert.labels.get("node", "cluster")

        color = {
            "critical": "#FF0000",
            "warning": "#FFA500",
            "info": "#0000FF",
        }.get(severity, "#808080")

        if alert.status == "resolved":
            color = "#00FF00"

        attachment = {
            "color": color,
            "title": f"{alertname} ({alert.status})",
            "text": alert.annotations.get("summary", ""),
            "fields": [
                {"title": "Node", "value": node, "short": True},
                {"title": "Severity", "value": severity, "short": True},
            ],
            "footer": "Hydra Alertmanager",
            "ts": int(datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00")).timestamp()),
        }

        attachments.append(attachment)

    return {"attachments": attachments}


def log_alert(payload: AlertmanagerPayload, channel: str):
    """Log alert to file."""
    log_file = LOG_DIR / f"alerts-{datetime.now().strftime('%Y-%m-%d')}.log"

    with open(log_file, "a") as f:
        for alert in payload.alerts:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "channel": channel,
                "receiver": payload.receiver,
                "alertname": alert.labels.get("alertname"),
                "status": alert.status,
                "severity": alert.labels.get("severity"),
                "node": alert.labels.get("node"),
                "summary": alert.annotations.get("summary"),
            }
            f.write(json.dumps(log_entry) + "\n")


async def send_discord(payload: AlertmanagerPayload):
    """Send alert to Discord."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return

    message = format_discord_message(payload)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                DISCORD_WEBHOOK_URL,
                json=message,
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info(f"Discord notification sent: {payload.commonLabels.get('alertname')}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")


async def send_slack(payload: AlertmanagerPayload):
    """Send alert to Slack."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook URL not configured")
        return

    message = format_slack_message(payload)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SLACK_WEBHOOK_URL,
                json=message,
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info(f"Slack notification sent: {payload.commonLabels.get('alertname')}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")


# Routes

@app.post("/webhook")
async def webhook_default(request: Request):
    """Default webhook endpoint - logs only."""
    payload = AlertmanagerPayload(**(await request.json()))
    log_alert(payload, "default")

    logger.info(f"Received {len(payload.alerts)} alerts (receiver: {payload.receiver})")

    return {"status": "received", "alerts": len(payload.alerts)}


@app.post("/critical")
async def webhook_critical(request: Request):
    """Critical alerts - send to all channels."""
    payload = AlertmanagerPayload(**(await request.json()))
    log_alert(payload, "critical")

    # Send to all configured channels
    await send_discord(payload)
    await send_slack(payload)

    logger.warning(f"CRITICAL: {len(payload.alerts)} alerts - {payload.commonLabels.get('alertname')}")

    return {"status": "notified", "alerts": len(payload.alerts)}


@app.post("/gpu")
async def webhook_gpu(request: Request):
    """GPU-specific alerts."""
    payload = AlertmanagerPayload(**(await request.json()))
    log_alert(payload, "gpu")

    # GPU alerts go to Discord
    await send_discord(payload)

    logger.info(f"GPU alert: {payload.commonLabels.get('alertname')}")

    return {"status": "received", "alerts": len(payload.alerts)}


@app.post("/infra")
async def webhook_infra(request: Request):
    """Infrastructure alerts."""
    payload = AlertmanagerPayload(**(await request.json()))
    log_alert(payload, "infra")

    await send_discord(payload)

    return {"status": "received", "alerts": len(payload.alerts)}


@app.post("/services")
async def webhook_services(request: Request):
    """Service alerts."""
    payload = AlertmanagerPayload(**(await request.json()))
    log_alert(payload, "services")

    await send_discord(payload)

    return {"status": "received", "alerts": len(payload.alerts)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hydra-alerts"}


@app.get("/alerts/recent")
async def recent_alerts(limit: int = 50):
    """Get recent alerts from log."""
    log_file = LOG_DIR / f"alerts-{datetime.now().strftime('%Y-%m-%d')}.log"

    if not log_file.exists():
        return {"alerts": [], "count": 0}

    alerts = []
    with open(log_file, "r") as f:
        for line in f:
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Return most recent first
    alerts = list(reversed(alerts[-limit:]))

    return {"alerts": alerts, "count": len(alerts)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9095)
