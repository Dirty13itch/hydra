"""
Hydra Discord Bot - System Control Interface

Provides Discord-based control interface for the Hydra cluster:
- /status - Get cluster status
- /health - Run health check
- /benchmark - Run benchmarks
- /presence [state] - Set presence mode
- /alert - Get active alerts

Requires DISCORD_BOT_TOKEN environment variable.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class DiscordWebhook:
    """Send messages via Discord webhook."""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def send(
        self,
        content: str,
        username: str = "Hydra",
        embeds: list = None,
    ) -> bool:
        """Send a message to Discord."""
        if not self.webhook_url:
            logger.warning("No Discord webhook URL configured")
            return False

        payload = {
            "content": content,
            "username": username,
        }
        if embeds:
            payload["embeds"] = embeds

        try:
            response = await self.client.post(self.webhook_url, json=payload)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False

    async def send_embed(
        self,
        title: str,
        description: str,
        color: int = 0x00FF00,  # Green
        fields: list = None,
    ) -> bool:
        """Send an embedded message."""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {"text": "Hydra Cluster"},
        }
        if fields:
            embed["fields"] = fields

        return await self.send("", embeds=[embed])


class DiscordCommandHandler:
    """Handle Discord slash commands via interactions."""

    def __init__(
        self,
        hydra_api_url: str = "http://192.168.1.244:8700",
    ):
        self.hydra_api_url = hydra_api_url
        self._client = None
        self.webhook = DiscordWebhook()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def handle_status(self) -> Dict[str, Any]:
        """Handle /status command."""
        try:
            # Get multiple status endpoints
            health = await self.client.get(f"{self.hydra_api_url}/health")
            container = await self.client.get(f"{self.hydra_api_url}/container-health/status")
            calendar = await self.client.get(f"{self.hydra_api_url}/calendar/status")

            health_data = health.json() if health.status_code == 200 else {}
            container_data = container.json() if container.status_code == 200 else {}
            calendar_data = calendar.json() if calendar.status_code == 200 else {}

            return {
                "status": "success",
                "response": {
                    "api_status": health_data.get("status", "unknown"),
                    "container_health": container_data.get("summary", {}).get("health_rate", 0),
                    "time_slot": calendar_data.get("time_slot", "unknown"),
                    "power_mode": calendar_data.get("config", {}).get("power_mode", "unknown"),
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_health(self) -> Dict[str, Any]:
        """Handle /health command."""
        try:
            response = await self.client.get(
                f"{self.hydra_api_url}/container-health/check-all",
                timeout=120,
            )
            data = response.json()
            summary = data.get("summary", {})

            return {
                "status": "success",
                "response": {
                    "total": summary.get("total", 0),
                    "healthy": summary.get("healthy", 0),
                    "unhealthy": summary.get("unhealthy", 0),
                    "health_rate": f"{summary.get('health_rate', 0):.1f}%",
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_benchmark(self, benchmark_name: str = None) -> Dict[str, Any]:
        """Handle /benchmark command."""
        try:
            if benchmark_name:
                response = await self.client.post(
                    f"{self.hydra_api_url}/benchmark/single/{benchmark_name}",
                    timeout=120,
                )
            else:
                response = await self.client.post(
                    f"{self.hydra_api_url}/benchmark/run",
                    timeout=300,
                )

            data = response.json()
            return {"status": "success", "response": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_presence(self, state: str) -> Dict[str, Any]:
        """Handle /presence command."""
        try:
            response = await self.client.post(
                f"{self.hydra_api_url}/presence/set/{state}",
            )
            data = response.json()
            return {"status": "success", "response": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_alerts(self) -> Dict[str, Any]:
        """Handle /alerts command."""
        try:
            response = await self.client.get(f"{self.hydra_api_url}/alerts/active")
            data = response.json()
            return {"status": "success", "response": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
    ) -> bool:
        """Send a notification to Discord."""
        colors = {
            "info": 0x00BFFF,    # Light blue
            "success": 0x00FF00, # Green
            "warning": 0xFFFF00, # Yellow
            "error": 0xFF0000,   # Red
            "critical": 0xFF0000,
        }
        color = colors.get(severity, 0x808080)

        return await self.webhook.send_embed(
            title=title,
            description=message,
            color=color,
        )


# =============================================================================
# Global Instance
# =============================================================================

_command_handler: Optional[DiscordCommandHandler] = None


def get_command_handler() -> DiscordCommandHandler:
    """Get or create command handler."""
    global _command_handler
    if _command_handler is None:
        _command_handler = DiscordCommandHandler()
    return _command_handler


# =============================================================================
# FastAPI Router
# =============================================================================

class DiscordNotifyRequest(BaseModel):
    title: str
    message: str
    severity: str = "info"


def create_discord_router() -> APIRouter:
    """Create FastAPI router for Discord endpoints."""
    router = APIRouter(prefix="/discord", tags=["discord"])

    @router.get("/status")
    async def discord_status():
        """Check Discord integration status."""
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        bot_token = os.getenv("DISCORD_BOT_TOKEN", "")

        return {
            "webhook_configured": bool(webhook_url),
            "bot_configured": bool(bot_token),
            "commands": ["/status", "/health", "/benchmark", "/presence", "/alerts"],
        }

    @router.post("/notify")
    async def send_notification(request: DiscordNotifyRequest):
        """Send a notification to Discord."""
        handler = get_command_handler()
        success = await handler.send_notification(
            title=request.title,
            message=request.message,
            severity=request.severity,
        )
        return {"sent": success}

    @router.post("/command/{command}")
    async def execute_command(command: str, arg: str = None):
        """Execute a Discord command (for testing)."""
        handler = get_command_handler()

        command_map = {
            "status": handler.handle_status,
            "health": handler.handle_health,
            "alerts": handler.handle_alerts,
        }

        if command == "benchmark":
            return await handler.handle_benchmark(arg)
        elif command == "presence" and arg:
            return await handler.handle_presence(arg)
        elif command in command_map:
            return await command_map[command]()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

    # =========================================================================
    # MORNING BRIEFING SYSTEM
    # =========================================================================

    class MorningBriefingConfig(BaseModel):
        """Configuration for morning briefing."""
        include_health: bool = True
        include_containers: bool = True
        include_alerts: bool = True
        include_gpu: bool = True
        include_memory: bool = True
        include_tasks: bool = True
        send_to_discord: bool = True

    @router.post("/briefing/morning")
    async def send_morning_briefing(config: MorningBriefingConfig = MorningBriefingConfig()):
        """
        Generate and send a comprehensive morning briefing.

        Gathers:
        - Cluster health status
        - Container health summary
        - Recent alerts
        - GPU utilization
        - Memory system status
        - Pending tasks

        Sends formatted briefing to Discord if configured.
        """
        handler = get_command_handler()
        briefing_sections = []
        overall_status = "healthy"
        issues = []

        # Gather all data
        try:
            # 1. System Health
            if config.include_health:
                health_resp = await handler.client.get(f"{handler.hydra_api_url}/health")
                if health_resp.status_code == 200:
                    health = health_resp.json()
                    briefing_sections.append(
                        f"**System Status:** {health.get('status', 'unknown').upper()}"
                    )
                    if health.get('status') != 'healthy':
                        overall_status = "degraded"
                        issues.append("API health check not healthy")

            # 2. Container Health
            if config.include_containers:
                containers_resp = await handler.client.get(
                    f"{handler.hydra_api_url}/container-health/status",
                    timeout=30,
                )
                if containers_resp.status_code == 200:
                    containers = containers_resp.json()
                    summary = containers.get("summary", {})
                    health_rate = summary.get("health_rate", 0)
                    healthy = summary.get("healthy", 0)
                    total = summary.get("total", 0)
                    unhealthy = summary.get("unhealthy", 0)

                    briefing_sections.append(
                        f"**Containers:** {healthy}/{total} healthy ({health_rate:.0f}%)"
                    )

                    if unhealthy > 0:
                        overall_status = "degraded"
                        issues.append(f"{unhealthy} container(s) unhealthy")

            # 3. Recent Alerts
            if config.include_alerts:
                alerts_resp = await handler.client.get(
                    f"{handler.hydra_api_url}/alerts/recent?limit=5"
                )
                if alerts_resp.status_code == 200:
                    alerts_data = alerts_resp.json()
                    alert_count = alerts_data.get("count", 0)
                    if alert_count > 0:
                        briefing_sections.append(f"**Recent Alerts:** {alert_count} in last 24h")
                        # Check for critical alerts
                        alerts = alerts_data.get("alerts", [])
                        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
                        if critical_count > 0:
                            overall_status = "critical"
                            issues.append(f"{critical_count} critical alert(s)")
                    else:
                        briefing_sections.append("**Alerts:** None in last 24h")

            # 4. GPU Status (via SSH or endpoint)
            if config.include_gpu:
                try:
                    # Try to get GPU info if available
                    gpu_resp = await handler.client.get(
                        f"{handler.hydra_api_url}/gpu/status",
                        timeout=5,
                    )
                    if gpu_resp.status_code == 200:
                        gpu_data = gpu_resp.json()
                        gpu_info = []
                        for gpu in gpu_data.get("gpus", []):
                            name = gpu.get("name", "GPU")
                            util = gpu.get("utilization", 0)
                            mem_used = gpu.get("memory_used_mb", 0)
                            mem_total = gpu.get("memory_total_mb", 1)
                            gpu_info.append(f"{name}: {util}% util, {mem_used}/{mem_total}MB")
                        if gpu_info:
                            briefing_sections.append("**GPUs:**\n" + "\n".join(gpu_info))
                except Exception:
                    briefing_sections.append("**GPUs:** Status unavailable")

            # 5. Memory System
            if config.include_memory:
                try:
                    mem_resp = await handler.client.get(f"{handler.hydra_api_url}/memory/stats")
                    if mem_resp.status_code == 200:
                        mem_data = mem_resp.json()
                        total_memories = mem_data.get("total_memories", 0)
                        briefing_sections.append(f"**Memory System:** {total_memories} memories stored")
                except Exception:
                    pass

            # Build the full briefing message
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            status_emoji = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}.get(overall_status, "⚪")

            briefing_text = "\n".join(briefing_sections)

            if issues:
                briefing_text += "\n\n**Issues:**\n" + "\n".join(f"• {i}" for i in issues)

            # Send to Discord
            discord_sent = False
            if config.send_to_discord:
                colors = {"healthy": 0x00FF00, "degraded": 0xFFFF00, "critical": 0xFF0000}
                discord_sent = await handler.webhook.send_embed(
                    title=f"{status_emoji} Morning Briefing - {timestamp}",
                    description=briefing_text,
                    color=colors.get(overall_status, 0x808080),
                    fields=[
                        {"name": "Overall Status", "value": overall_status.upper(), "inline": True},
                        {"name": "Issues", "value": str(len(issues)), "inline": True},
                    ],
                )

            return {
                "status": "success",
                "overall_status": overall_status,
                "issues": issues,
                "sections": briefing_sections,
                "discord_sent": discord_sent,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Morning briefing error: {e}")
            return {"status": "error", "message": str(e)}

    @router.get("/briefing/preview")
    async def preview_briefing():
        """Preview what the morning briefing would contain without sending."""
        config = MorningBriefingConfig(send_to_discord=False)
        return await send_morning_briefing(config)

    @router.post("/webhook/interaction")
    async def discord_interaction(request: Request):
        """
        Handle Discord interaction webhook.

        This endpoint receives slash command interactions from Discord.
        Requires setting up a Discord application with slash commands.
        """
        try:
            body = await request.json()
            interaction_type = body.get("type")

            # Ping (type 1) - verification
            if interaction_type == 1:
                return {"type": 1}

            # Application Command (type 2)
            if interaction_type == 2:
                handler = get_command_handler()
                command_name = body.get("data", {}).get("name", "")
                options = {
                    opt.get("name"): opt.get("value")
                    for opt in body.get("data", {}).get("options", [])
                }

                # Execute command
                if command_name == "status":
                    result = await handler.handle_status()
                elif command_name == "health":
                    result = await handler.handle_health()
                elif command_name == "benchmark":
                    result = await handler.handle_benchmark(options.get("name"))
                elif command_name == "presence":
                    result = await handler.handle_presence(options.get("state", "home"))
                elif command_name == "alerts":
                    result = await handler.handle_alerts()
                else:
                    result = {"status": "error", "message": f"Unknown command: {command_name}"}

                # Format response
                if result.get("status") == "success":
                    content = f"```json\n{result.get('response')}\n```"
                else:
                    content = f"Error: {result.get('message')}"

                return {
                    "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
                    "data": {"content": content[:2000]},  # Discord limit
                }

            return {"type": 1}

        except Exception as e:
            logger.error(f"Discord interaction error: {e}")
            return {"type": 4, "data": {"content": f"Error: {e}"}}

    return router


if __name__ == "__main__":
    import asyncio

    async def test():
        handler = DiscordCommandHandler()

        # Test status command
        result = await handler.handle_status()
        print("Status:", result)

        # Test health command
        result = await handler.handle_health()
        print("Health:", result)

        await handler.client.aclose()

    asyncio.run(test())
