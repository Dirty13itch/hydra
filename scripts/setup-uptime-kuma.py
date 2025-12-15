#!/usr/bin/env python3
"""
Uptime Kuma Monitor Setup Script

Configures all Hydra cluster monitors in Uptime Kuma via API.
Run this after Uptime Kuma is deployed to set up comprehensive monitoring.

Prerequisites:
  1. Uptime Kuma running at http://192.168.1.244:3001
  2. Admin account created
  3. API key generated (Settings > API Keys)

Usage:
  export UPTIME_KUMA_URL="http://192.168.1.244:3001"
  export UPTIME_KUMA_USERNAME="admin"
  export UPTIME_KUMA_PASSWORD="your-password"
  python setup-uptime-kuma.py
"""

import os
import sys
import json
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

try:
    from uptime_kuma_api import UptimeKumaApi, MonitorType
except ImportError:
    print("Installing uptime-kuma-api...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "uptime-kuma-api"])
    from uptime_kuma_api import UptimeKumaApi, MonitorType

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()

# Configuration
UPTIME_KUMA_URL = os.getenv("UPTIME_KUMA_URL", "http://192.168.1.244:3001")
UPTIME_KUMA_USERNAME = os.getenv("UPTIME_KUMA_USERNAME", "admin")
UPTIME_KUMA_PASSWORD = os.getenv("UPTIME_KUMA_PASSWORD", "")


@dataclass
class MonitorConfig:
    """Monitor configuration."""
    name: str
    type: str  # http, tcp, ping, docker
    target: str  # URL, host:port, or container name
    interval: int = 60
    retry_interval: int = 30
    max_retries: int = 3
    timeout: int = 10
    tags: List[str] = field(default_factory=list)
    description: str = ""
    # HTTP specific
    method: str = "GET"
    expected_status: List[int] = field(default_factory=lambda: [200, 201, 204])
    # Group
    group: Optional[str] = None


# Monitor definitions organized by category
MONITORS: Dict[str, List[MonitorConfig]] = {
    "Inference": [
        MonitorConfig(
            name="TabbyAPI",
            type="http",
            target="http://192.168.1.250:5000/health",
            interval=30,
            tags=["critical", "inference", "hydra-ai"],
            description="Primary LLM inference (70B models)",
        ),
        MonitorConfig(
            name="TabbyAPI - Model Loaded",
            type="http",
            target="http://192.168.1.250:5000/v1/model",
            interval=60,
            tags=["inference", "hydra-ai"],
            description="Verify model is loaded",
        ),
        MonitorConfig(
            name="Ollama",
            type="http",
            target="http://192.168.1.203:11434/api/tags",
            interval=30,
            tags=["critical", "inference", "hydra-compute"],
            description="Secondary inference (7B-14B models)",
        ),
        MonitorConfig(
            name="LiteLLM Gateway",
            type="http",
            target="http://192.168.1.244:4000/health",
            interval=30,
            tags=["critical", "inference", "hydra-storage"],
            description="Unified API gateway",
        ),
        MonitorConfig(
            name="ComfyUI",
            type="http",
            target="http://192.168.1.203:8188/system_stats",
            interval=60,
            tags=["inference", "hydra-compute"],
            description="Image generation",
        ),
    ],
    "Databases": [
        MonitorConfig(
            name="PostgreSQL",
            type="tcp",
            target="192.168.1.244:5432",
            interval=30,
            tags=["critical", "database", "hydra-storage"],
            description="Primary database",
        ),
        MonitorConfig(
            name="Qdrant",
            type="http",
            target="http://192.168.1.244:6333/health",
            interval=30,
            tags=["critical", "database", "hydra-storage"],
            description="Vector database",
        ),
        MonitorConfig(
            name="Redis",
            type="tcp",
            target="192.168.1.244:6379",
            interval=30,
            tags=["critical", "database", "hydra-storage"],
            description="Cache and sessions",
        ),
        MonitorConfig(
            name="Meilisearch",
            type="http",
            target="http://192.168.1.244:7700/health",
            interval=60,
            tags=["database", "hydra-storage"],
            description="Full-text search",
        ),
    ],
    "Observability": [
        MonitorConfig(
            name="Prometheus",
            type="http",
            target="http://192.168.1.244:9090/-/healthy",
            interval=60,
            tags=["observability", "hydra-storage"],
            description="Metrics collection",
        ),
        MonitorConfig(
            name="Grafana",
            type="http",
            target="http://192.168.1.244:3003/api/health",
            interval=60,
            tags=["observability", "hydra-storage"],
            description="Dashboards",
        ),
        MonitorConfig(
            name="Loki",
            type="http",
            target="http://192.168.1.244:3100/ready",
            interval=60,
            tags=["observability", "hydra-storage"],
            description="Log aggregation",
        ),
    ],
    "Automation": [
        MonitorConfig(
            name="n8n",
            type="http",
            target="http://192.168.1.244:5678/healthz",
            interval=60,
            tags=["automation", "hydra-storage"],
            description="Workflow automation",
        ),
        MonitorConfig(
            name="SearXNG",
            type="http",
            target="http://192.168.1.244:8888/healthz",
            interval=60,
            tags=["automation", "hydra-storage"],
            description="Meta search engine",
        ),
        MonitorConfig(
            name="Firecrawl",
            type="http",
            target="http://192.168.1.244:3005/health",
            interval=120,
            tags=["automation", "hydra-storage"],
            description="Web scraping",
        ),
        MonitorConfig(
            name="Docling",
            type="http",
            target="http://192.168.1.244:5001/health",
            interval=120,
            tags=["automation", "hydra-storage"],
            description="Document processing",
        ),
    ],
    "Web UIs": [
        MonitorConfig(
            name="Open WebUI",
            type="http",
            target="http://192.168.1.250:3000",
            interval=60,
            tags=["ui", "hydra-ai"],
            description="Chat interface",
        ),
        MonitorConfig(
            name="SillyTavern",
            type="http",
            target="http://192.168.1.244:8000",
            interval=120,
            tags=["ui", "hydra-storage"],
            description="Roleplay interface",
        ),
        MonitorConfig(
            name="Perplexica",
            type="http",
            target="http://192.168.1.244:3030",
            interval=120,
            tags=["ui", "hydra-storage"],
            description="AI search interface",
        ),
    ],
    "Media": [
        MonitorConfig(
            name="Sonarr",
            type="http",
            target="http://192.168.1.244:8989/ping",
            interval=120,
            tags=["media", "hydra-storage"],
            description="TV management",
        ),
        MonitorConfig(
            name="Radarr",
            type="http",
            target="http://192.168.1.244:7878/ping",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Movie management",
        ),
        MonitorConfig(
            name="Prowlarr",
            type="http",
            target="http://192.168.1.244:9696/ping",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Indexer management",
        ),
        MonitorConfig(
            name="Plex",
            type="http",
            target="http://192.168.1.244:32400/web",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Media server",
        ),
    ],
    "Infrastructure": [
        MonitorConfig(
            name="hydra-ai",
            type="ping",
            target="192.168.1.250",
            interval=30,
            tags=["critical", "node"],
            description="Primary inference node",
        ),
        MonitorConfig(
            name="hydra-compute",
            type="ping",
            target="192.168.1.203",
            interval=30,
            tags=["critical", "node"],
            description="Secondary inference node",
        ),
        MonitorConfig(
            name="hydra-storage",
            type="ping",
            target="192.168.1.244",
            interval=30,
            tags=["critical", "node"],
            description="Storage and services node",
        ),
        MonitorConfig(
            name="AdGuard DNS",
            type="tcp",
            target="192.168.1.244:53",
            interval=60,
            tags=["infrastructure", "hydra-storage"],
            description="DNS server",
        ),
        MonitorConfig(
            name="Portainer",
            type="http",
            target="http://192.168.1.244:9000",
            interval=120,
            tags=["infrastructure", "hydra-storage"],
            description="Container management",
        ),
        MonitorConfig(
            name="Vaultwarden",
            type="http",
            target="https://192.168.1.244:8444",
            interval=120,
            tags=["infrastructure", "hydra-storage"],
            description="Password manager",
            # Note: Will need to configure to accept self-signed cert
        ),
    ],
    "Home Automation": [
        MonitorConfig(
            name="Home Assistant",
            type="http",
            target="http://192.168.1.244:8123/api/",
            interval=60,
            tags=["home", "hydra-storage"],
            description="Home automation hub",
        ),
    ],
    "Agents & AI": [
        MonitorConfig(
            name="Letta API",
            type="http",
            target="http://192.168.1.244:8283/v1/health",
            interval=60,
            tags=["critical", "agent", "hydra-storage"],
            description="Agent memory & orchestration",
        ),
        MonitorConfig(
            name="Hydra MCP",
            type="http",
            target="http://192.168.1.244:8600/health",
            interval=30,
            tags=["critical", "mcp", "hydra-storage"],
            description="Model Context Protocol server",
        ),
        MonitorConfig(
            name="Hydra Tools API",
            type="http",
            target="http://192.168.1.244:8700/health",
            interval=60,
            tags=["agent", "hydra-storage"],
            description="Transparency framework API",
        ),
        MonitorConfig(
            name="Alertmanager",
            type="http",
            target="http://192.168.1.244:9093/-/healthy",
            interval=60,
            tags=["observability", "hydra-storage"],
            description="Alert routing",
        ),
        MonitorConfig(
            name="Kokoro TTS",
            type="http",
            target="http://192.168.1.244:8880/health",
            interval=120,
            tags=["inference", "hydra-storage"],
            description="Text-to-speech",
        ),
    ],
    "Downloads": [
        MonitorConfig(
            name="qBittorrent",
            type="http",
            target="http://192.168.1.244:8082",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Torrent client",
        ),
        MonitorConfig(
            name="SABnzbd",
            type="http",
            target="http://192.168.1.244:8085",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Usenet client",
        ),
        MonitorConfig(
            name="Lidarr",
            type="http",
            target="http://192.168.1.244:8686/ping",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Music management",
        ),
        MonitorConfig(
            name="Bazarr",
            type="http",
            target="http://192.168.1.244:6767/api/system/health",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Subtitle management",
        ),
    ],
    "Additional Services": [
        MonitorConfig(
            name="Stash",
            type="http",
            target="http://192.168.1.244:9999",
            interval=120,
            tags=["media", "hydra-storage"],
            description="Media organizer",
        ),
        MonitorConfig(
            name="Miniflux",
            type="http",
            target="http://192.168.1.244:8180/healthcheck",
            interval=120,
            tags=["automation", "hydra-storage"],
            description="RSS reader",
        ),
        MonitorConfig(
            name="Homepage",
            type="http",
            target="http://192.168.1.244:3333",
            interval=120,
            tags=["ui", "hydra-storage"],
            description="Dashboard homepage",
        ),
        MonitorConfig(
            name="Uptime Kuma",
            type="http",
            target="http://192.168.1.244:3001",
            interval=60,
            tags=["observability", "hydra-storage"],
            description="Status monitoring",
        ),
    ],
}


def create_monitor(api: UptimeKumaApi, config: MonitorConfig, group_id: Optional[int] = None) -> Optional[int]:
    """Create a single monitor."""
    try:
        monitor_type = {
            "http": MonitorType.HTTP,
            "tcp": MonitorType.PORT,
            "ping": MonitorType.PING,
            "docker": MonitorType.DOCKER,
        }.get(config.type, MonitorType.HTTP)

        params = {
            "type": monitor_type,
            "name": config.name,
            "interval": config.interval,
            "retryInterval": config.retry_interval,
            "maxretries": config.max_retries,
            "timeout": config.timeout,
            "description": config.description,
        }

        if config.type == "http":
            params["url"] = config.target
            params["method"] = config.method
            params["accepted_statuscodes"] = config.expected_status
            # Accept self-signed certs for internal services
            if "https" in config.target:
                params["ignoreTls"] = True

        elif config.type == "tcp":
            host, port = config.target.rsplit(":", 1)
            params["hostname"] = host
            params["port"] = int(port)

        elif config.type == "ping":
            params["hostname"] = config.target

        if group_id:
            params["parent"] = group_id

        result = api.add_monitor(**params)
        return result.get("monitorID")

    except Exception as e:
        console.print(f"[red]  Failed to create {config.name}: {e}[/red]")
        return None


def create_group(api: UptimeKumaApi, name: str) -> Optional[int]:
    """Create a monitor group."""
    try:
        result = api.add_monitor(
            type=MonitorType.GROUP,
            name=name,
        )
        return result.get("monitorID")
    except Exception as e:
        console.print(f"[red]Failed to create group {name}: {e}[/red]")
        return None


def get_or_create_tags(api: UptimeKumaApi, tag_names: List[str]) -> Dict[str, int]:
    """Get or create tags and return name->id mapping."""
    existing_tags = {t["name"]: t["id"] for t in api.get_tags()}
    tag_ids = {}

    # Define tag colors
    tag_colors = {
        "critical": "#dc3545",
        "inference": "#6f42c1",
        "database": "#0d6efd",
        "observability": "#20c997",
        "automation": "#fd7e14",
        "ui": "#0dcaf0",
        "media": "#198754",
        "infrastructure": "#6c757d",
        "home": "#ffc107",
        "node": "#343a40",
        "hydra-ai": "#e83e8c",
        "hydra-compute": "#17a2b8",
        "hydra-storage": "#28a745",
        "agent": "#9c27b0",
        "mcp": "#ff5722",
    }

    for tag_name in tag_names:
        if tag_name in existing_tags:
            tag_ids[tag_name] = existing_tags[tag_name]
        else:
            try:
                color = tag_colors.get(tag_name, "#6c757d")
                result = api.add_tag(name=tag_name, color=color)
                tag_ids[tag_name] = result["id"]
            except Exception as e:
                console.print(f"[yellow]Could not create tag {tag_name}: {e}[/yellow]")

    return tag_ids


def apply_tags(api: UptimeKumaApi, monitor_id: int, tag_names: List[str], tag_map: Dict[str, int]):
    """Apply tags to a monitor."""
    for tag_name in tag_names:
        if tag_name in tag_map:
            try:
                api.add_monitor_tag(tag_id=tag_map[tag_name], monitor_id=monitor_id)
            except Exception:
                pass  # Tag might already be applied


def setup_notifications(api: UptimeKumaApi):
    """Set up notification channels."""
    console.print("\n[cyan]Setting up notifications...[/cyan]")

    # Check existing notifications
    existing = api.get_notifications()
    existing_names = {n["name"] for n in existing}

    # Discord webhook (if configured)
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url and "Discord - Hydra Alerts" not in existing_names:
        try:
            api.add_notification(
                name="Discord - Hydra Alerts",
                type="discord",
                discordWebhookUrl=discord_url,
                isDefault=True,
            )
            console.print("[green]  ✓ Discord notification created[/green]")
        except Exception as e:
            console.print(f"[yellow]  Could not create Discord notification: {e}[/yellow]")

    # Webhook to hydra-alerts
    if "Hydra Alert Webhook" not in existing_names:
        try:
            api.add_notification(
                name="Hydra Alert Webhook",
                type="webhook",
                webhookURL="http://192.168.1.244:9095/webhook",
                webhookContentType="application/json",
                isDefault=True,
            )
            console.print("[green]  ✓ Webhook notification created[/green]")
        except Exception as e:
            console.print(f"[yellow]  Could not create webhook notification: {e}[/yellow]")


def main():
    if not UPTIME_KUMA_PASSWORD:
        console.print("[red]Error: UPTIME_KUMA_PASSWORD environment variable required[/red]")
        console.print("Usage:")
        console.print('  export UPTIME_KUMA_PASSWORD="your-password"')
        console.print("  python setup-uptime-kuma.py")
        sys.exit(1)

    console.print(f"[cyan]Connecting to Uptime Kuma at {UPTIME_KUMA_URL}...[/cyan]")

    try:
        api = UptimeKumaApi(UPTIME_KUMA_URL)
        api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
        console.print("[green]✓ Connected successfully[/green]")
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        sys.exit(1)

    # Get all unique tags
    all_tags = set()
    for monitors in MONITORS.values():
        for monitor in monitors:
            all_tags.update(monitor.tags)

    console.print(f"\n[cyan]Creating {len(all_tags)} tags...[/cyan]")
    tag_map = get_or_create_tags(api, list(all_tags))

    # Set up notifications
    setup_notifications(api)

    # Create monitors by group
    total_monitors = sum(len(m) for m in MONITORS.values())
    created = 0
    failed = 0

    console.print(f"\n[cyan]Creating {total_monitors} monitors...[/cyan]\n")

    for group_name, monitors in MONITORS.items():
        console.print(f"[bold]{group_name}[/bold]")

        # Create group
        group_id = create_group(api, group_name)

        for config in monitors:
            monitor_id = create_monitor(api, config, group_id)

            if monitor_id:
                # Apply tags
                apply_tags(api, monitor_id, config.tags, tag_map)
                console.print(f"  [green]✓[/green] {config.name}")
                created += 1
            else:
                console.print(f"  [red]✗[/red] {config.name}")
                failed += 1

            time.sleep(0.1)  # Rate limiting

        console.print()

    # Summary
    console.print("[bold]═══════════════════════════════════════[/bold]")
    console.print(f"[green]Created: {created}[/green]")
    if failed:
        console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"\nView monitors at: {UPTIME_KUMA_URL}/dashboard")

    api.disconnect()


if __name__ == "__main__":
    main()
