#!/usr/bin/env python3
"""
Hydra Cluster - Uptime Kuma Monitor Configuration

Programmatically configures monitors for all 40+ cluster services.
Uses the Uptime Kuma Push API and socket.io API for configuration.

Usage:
    python configure-uptime-kuma.py [--dry-run] [--reset]

Options:
    --dry-run   Preview monitors without creating them
    --reset     Delete existing monitors before creating new ones

Requirements:
    pip install requests python-socketio websocket-client

Generated: December 14, 2025
"""

import argparse
import json
import time
import sys
from typing import Optional
import requests

# Uptime Kuma connection settings
UPTIME_KUMA_URL = "http://192.168.1.244:3001"
# Note: Set these after first login to Uptime Kuma
API_TOKEN = None  # Will be set from environment or config

# Cluster service definitions
# Format: (name, type, config_dict)
MONITORS = [
    # ==================== TIER 1: Infrastructure ====================
    {
        "name": "hydra-ai Node",
        "type": "ping",
        "hostname": "192.168.1.250",
        "description": "Primary inference node (NixOS)",
        "interval": 60,
        "tags": ["infrastructure", "critical"]
    },
    {
        "name": "hydra-compute Node",
        "type": "ping",
        "hostname": "192.168.1.203",
        "description": "Secondary inference node (NixOS)",
        "interval": 60,
        "tags": ["infrastructure", "critical"]
    },
    {
        "name": "hydra-storage Node",
        "type": "ping",
        "hostname": "192.168.1.244",
        "description": "Storage and services node (Unraid)",
        "interval": 60,
        "tags": ["infrastructure", "critical"]
    },

    # ==================== TIER 2: Inference Stack ====================
    {
        "name": "TabbyAPI",
        "type": "http",
        "url": "http://192.168.1.250:5000/v1/model",
        "description": "Primary LLM inference (ExLlamaV2)",
        "interval": 60,
        "retryInterval": 30,
        "maxretries": 3,
        "tags": ["inference", "critical"]
    },
    {
        "name": "LiteLLM Proxy",
        "type": "http",
        "url": "http://192.168.1.244:4000/health",
        "description": "LLM routing proxy",
        "interval": 60,
        "tags": ["inference", "critical"]
    },
    {
        "name": "Ollama",
        "type": "http",
        "url": "http://192.168.1.203:11434/api/version",
        "description": "Secondary LLM inference",
        "interval": 60,
        "tags": ["inference"]
    },
    {
        "name": "Open WebUI",
        "type": "http",
        "url": "http://192.168.1.250:3000",
        "description": "Chat interface",
        "interval": 60,
        "tags": ["inference", "ui"]
    },

    # ==================== TIER 3: Databases ====================
    {
        "name": "PostgreSQL",
        "type": "port",
        "hostname": "192.168.1.244",
        "port": 5432,
        "description": "Primary database (4 DBs)",
        "interval": 60,
        "tags": ["database", "critical"]
    },
    {
        "name": "Redis",
        "type": "port",
        "hostname": "192.168.1.244",
        "port": 6379,
        "description": "Cache and message broker",
        "interval": 60,
        "tags": ["database", "critical"]
    },
    {
        "name": "Qdrant",
        "type": "http",
        "url": "http://192.168.1.244:6333/health",
        "description": "Vector database",
        "interval": 60,
        "tags": ["database", "critical"]
    },
    {
        "name": "MinIO",
        "type": "http",
        "url": "http://192.168.1.244:9002/minio/health/live",
        "description": "Object storage",
        "interval": 120,
        "tags": ["database"]
    },

    # ==================== TIER 4: Automation ====================
    {
        "name": "n8n",
        "type": "http",
        "url": "http://192.168.1.244:5678/healthz",
        "description": "Workflow automation",
        "interval": 60,
        "tags": ["automation", "critical"]
    },
    {
        "name": "Letta Server",
        "type": "http",
        "url": "http://192.168.1.244:8283/v1/health",
        "description": "Memory-augmented agent",
        "interval": 60,
        "tags": ["automation", "intelligence"]
    },
    {
        "name": "Phase 11 Tools API",
        "type": "http",
        "url": "http://192.168.1.244:8700/health",
        "description": "Self-improvement API",
        "interval": 60,
        "tags": ["automation", "intelligence"]
    },

    # ==================== TIER 5: Observability ====================
    {
        "name": "Prometheus",
        "type": "http",
        "url": "http://192.168.1.244:9090/-/healthy",
        "description": "Metrics collection",
        "interval": 60,
        "tags": ["observability", "critical"]
    },
    {
        "name": "Grafana",
        "type": "http",
        "url": "http://192.168.1.244:3003/api/health",
        "description": "Metrics visualization",
        "interval": 60,
        "tags": ["observability"]
    },
    {
        "name": "Loki",
        "type": "http",
        "url": "http://192.168.1.244:3100/ready",
        "description": "Log aggregation",
        "interval": 60,
        "tags": ["observability"]
    },
    {
        "name": "Alertmanager",
        "type": "http",
        "url": "http://192.168.1.244:9093/-/healthy",
        "description": "Alert routing",
        "interval": 60,
        "tags": ["observability"]
    },
    {
        "name": "Node Exporter (hydra-ai)",
        "type": "http",
        "url": "http://192.168.1.250:9100/metrics",
        "description": "Host metrics exporter",
        "interval": 120,
        "tags": ["observability"]
    },
    {
        "name": "Node Exporter (hydra-compute)",
        "type": "http",
        "url": "http://192.168.1.203:9100/metrics",
        "description": "Host metrics exporter",
        "interval": 120,
        "tags": ["observability"]
    },
    {
        "name": "GPU Exporter (hydra-ai)",
        "type": "http",
        "url": "http://192.168.1.250:9835/metrics",
        "description": "GPU metrics exporter",
        "interval": 120,
        "tags": ["observability"]
    },
    {
        "name": "GPU Exporter (hydra-compute)",
        "type": "http",
        "url": "http://192.168.1.203:9835/metrics",
        "description": "GPU metrics exporter",
        "interval": 120,
        "tags": ["observability"]
    },

    # ==================== TIER 6: Search & Knowledge ====================
    {
        "name": "SearXNG",
        "type": "http",
        "url": "http://192.168.1.244:8888/healthz",
        "description": "Meta search engine",
        "interval": 120,
        "tags": ["knowledge"]
    },
    {
        "name": "Perplexica",
        "type": "http",
        "url": "http://192.168.1.244:3030",
        "description": "AI-powered search",
        "interval": 120,
        "tags": ["knowledge"]
    },
    {
        "name": "Firecrawl",
        "type": "http",
        "url": "http://192.168.1.244:3005/health",
        "description": "Web scraping service",
        "interval": 120,
        "tags": ["knowledge"]
    },
    {
        "name": "Docling",
        "type": "http",
        "url": "http://192.168.1.244:5001/health",
        "description": "Document processing",
        "interval": 120,
        "tags": ["knowledge"]
    },
    {
        "name": "Miniflux",
        "type": "http",
        "url": "http://192.168.1.244:8180/healthcheck",
        "description": "RSS reader",
        "interval": 120,
        "tags": ["knowledge"]
    },

    # ==================== TIER 7: Creative Stack ====================
    {
        "name": "ComfyUI",
        "type": "http",
        "url": "http://192.168.1.203:8188/system_stats",
        "description": "Image generation",
        "interval": 120,
        "tags": ["creative"]
    },
    {
        "name": "SillyTavern",
        "type": "http",
        "url": "http://192.168.1.244:8000",
        "description": "Character chat interface",
        "interval": 120,
        "tags": ["creative"]
    },
    {
        "name": "Kokoro TTS",
        "type": "http",
        "url": "http://192.168.1.244:8880/health",
        "description": "Text-to-speech",
        "interval": 120,
        "tags": ["creative", "voice"]
    },

    # ==================== TIER 8: Media Stack ====================
    {
        "name": "Plex",
        "type": "http",
        "url": "http://192.168.1.244:32400/identity",
        "description": "Media server",
        "interval": 120,
        "tags": ["media"]
    },
    {
        "name": "Stash",
        "type": "http",
        "url": "http://192.168.1.244:9999",
        "description": "Media organizer",
        "interval": 120,
        "tags": ["media"]
    },
    {
        "name": "Sonarr",
        "type": "http",
        "url": "http://192.168.1.244:8989/ping",
        "description": "TV show automation",
        "interval": 120,
        "tags": ["media", "arr"]
    },
    {
        "name": "Radarr",
        "type": "http",
        "url": "http://192.168.1.244:7878/ping",
        "description": "Movie automation",
        "interval": 120,
        "tags": ["media", "arr"]
    },
    {
        "name": "Lidarr",
        "type": "http",
        "url": "http://192.168.1.244:8686/ping",
        "description": "Music automation",
        "interval": 120,
        "tags": ["media", "arr"]
    },
    {
        "name": "Prowlarr",
        "type": "http",
        "url": "http://192.168.1.244:9696/ping",
        "description": "Indexer manager",
        "interval": 120,
        "tags": ["media", "arr"]
    },
    {
        "name": "Bazarr",
        "type": "http",
        "url": "http://192.168.1.244:6767/api/system/health",
        "description": "Subtitle automation",
        "interval": 120,
        "tags": ["media", "arr"]
    },
    {
        "name": "qBittorrent",
        "type": "http",
        "url": "http://192.168.1.244:8082",
        "description": "Torrent client",
        "interval": 120,
        "tags": ["media", "download"]
    },
    {
        "name": "SABnzbd",
        "type": "http",
        "url": "http://192.168.1.244:8085",
        "description": "Usenet client",
        "interval": 120,
        "tags": ["media", "download"]
    },

    # ==================== TIER 9: Home & Security ====================
    {
        "name": "Home Assistant",
        "type": "http",
        "url": "http://192.168.1.244:8123/api/",
        "description": "Home automation",
        "interval": 60,
        "tags": ["home", "critical"]
    },
    {
        "name": "AdGuard DNS",
        "type": "port",
        "hostname": "192.168.1.244",
        "port": 53,
        "description": "DNS server",
        "interval": 60,
        "tags": ["infrastructure", "critical"]
    },
    {
        "name": "Vaultwarden",
        "type": "http",
        "url": "https://192.168.1.244:8444/alive",
        "ignoreTls": True,
        "description": "Password manager",
        "interval": 120,
        "tags": ["security"]
    },

    # ==================== TIER 10: Management ====================
    {
        "name": "Portainer",
        "type": "http",
        "url": "http://192.168.1.244:9000/api/system/status",
        "description": "Container management",
        "interval": 120,
        "tags": ["management"]
    },
    {
        "name": "Homepage",
        "type": "http",
        "url": "http://192.168.1.244:3333",
        "description": "Dashboard",
        "interval": 120,
        "tags": ["management"]
    },
]

# Notification targets
NOTIFICATIONS = [
    {
        "name": "n8n Webhook",
        "type": "webhook",
        "webhookURL": "http://192.168.1.244:5678/webhook/uptime-kuma-alert",
        "webhookContentType": "json"
    }
]


def print_monitor_table(monitors: list, dry_run: bool = False):
    """Print monitors in a formatted table."""
    print(f"\n{'='*80}")
    print(f"{'DRY RUN - ' if dry_run else ''}UPTIME KUMA MONITOR CONFIGURATION")
    print(f"{'='*80}\n")

    # Group by tags
    tag_groups = {}
    for m in monitors:
        primary_tag = m.get("tags", ["other"])[0]
        if primary_tag not in tag_groups:
            tag_groups[primary_tag] = []
        tag_groups[primary_tag].append(m)

    total = 0
    for tag, group in sorted(tag_groups.items()):
        print(f"\n[{tag.upper()}] ({len(group)} monitors)")
        print("-" * 60)
        for m in group:
            target = m.get("url") or f"{m.get('hostname')}:{m.get('port', '')}"
            print(f"  {m['name']:<30} {m['type']:<6} {target}")
            total += 1

    print(f"\n{'='*80}")
    print(f"TOTAL: {total} monitors")
    print(f"{'='*80}\n")


def create_uptime_kuma_config_json():
    """Generate a JSON configuration file for manual import."""
    config = {
        "version": "1.23.0",
        "notificationList": NOTIFICATIONS,
        "monitorList": []
    }

    for i, monitor in enumerate(MONITORS, start=1):
        m = {
            "id": i,
            "name": monitor["name"],
            "description": monitor.get("description", ""),
            "type": monitor["type"],
            "interval": monitor.get("interval", 60),
            "retryInterval": monitor.get("retryInterval", 60),
            "maxretries": monitor.get("maxretries", 1),
            "active": True,
            "notificationIDList": {"1": True}  # Link to first notification
        }

        if monitor["type"] == "http":
            m["url"] = monitor["url"]
            m["method"] = "GET"
            m["maxredirects"] = 10
            m["accepted_statuscodes"] = ["200-299"]
            if monitor.get("ignoreTls"):
                m["ignoreTls"] = True
        elif monitor["type"] == "port":
            m["hostname"] = monitor["hostname"]
            m["port"] = monitor["port"]
        elif monitor["type"] == "ping":
            m["hostname"] = monitor["hostname"]

        config["monitorList"].append(m)

    return config


def generate_curl_commands():
    """Generate curl commands for manual API setup."""
    commands = []

    commands.append("# Uptime Kuma API Configuration Commands")
    commands.append("# Run these after logging into Uptime Kuma and getting your API token")
    commands.append(f"# Base URL: {UPTIME_KUMA_URL}")
    commands.append("")
    commands.append("# Set your API token:")
    commands.append("export KUMA_TOKEN='your-api-token-here'")
    commands.append("")

    for monitor in MONITORS:
        if monitor["type"] == "http":
            cmd = f'''curl -X POST "{UPTIME_KUMA_URL}/api/push/add" \\
  -H "Authorization: Bearer $KUMA_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"name": "{monitor['name']}", "type": "http", "url": "{monitor['url']}", "interval": {monitor.get('interval', 60)}}}'
'''
        elif monitor["type"] == "port":
            cmd = f'''curl -X POST "{UPTIME_KUMA_URL}/api/push/add" \\
  -H "Authorization: Bearer $KUMA_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"name": "{monitor['name']}", "type": "port", "hostname": "{monitor['hostname']}", "port": {monitor['port']}, "interval": {monitor.get('interval', 60)}}}'
'''
        elif monitor["type"] == "ping":
            cmd = f'''curl -X POST "{UPTIME_KUMA_URL}/api/push/add" \\
  -H "Authorization: Bearer $KUMA_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"name": "{monitor['name']}", "type": "ping", "hostname": "{monitor['hostname']}", "interval": {monitor.get('interval', 60)}}}'
'''
        commands.append(f"# {monitor['name']}")
        commands.append(cmd)

    return "\n".join(commands)


def main():
    parser = argparse.ArgumentParser(description="Configure Uptime Kuma monitors for Hydra cluster")
    parser.add_argument("--dry-run", action="store_true", help="Preview monitors without creating them")
    parser.add_argument("--json", action="store_true", help="Output JSON config for import")
    parser.add_argument("--curl", action="store_true", help="Output curl commands for API setup")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    if args.dry_run or (not args.json and not args.curl):
        print_monitor_table(MONITORS, dry_run=args.dry_run)

    if args.json:
        config = create_uptime_kuma_config_json()
        output = json.dumps(config, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"JSON config written to: {args.output}")
        else:
            print(output)

    if args.curl:
        commands = generate_curl_commands()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(commands)
            print(f"Curl commands written to: {args.output}")
        else:
            print(commands)

    if not args.json and not args.curl:
        print("\nUsage options:")
        print("  --dry-run    Preview all monitors")
        print("  --json       Generate JSON config for Uptime Kuma import")
        print("  --curl       Generate curl commands for API setup")
        print("  -o FILE      Write output to file")
        print("")
        print("Recommended workflow:")
        print("  1. Log into Uptime Kuma at http://192.168.1.244:3001")
        print("  2. Create initial admin account if first time")
        print("  3. Go to Settings > Backup > Import")
        print("  4. Run: python configure-uptime-kuma.py --json -o kuma-config.json")
        print("  5. Import the generated JSON file")
        print("  6. Configure notification webhook to n8n")


if __name__ == "__main__":
    main()
