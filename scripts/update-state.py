#!/usr/bin/env python3
"""
Hydra Cluster State Collector

Automatically gathers cluster state and updates STATE.json.
Run as a cron job or systemd timer for continuous state tracking.

Usage:
    python update-state.py [--output STATE.json] [--check-only]

Cron example (every 15 minutes):
    */15 * * * * /usr/bin/python3 /opt/hydra/scripts/update-state.py >> /var/log/hydra-state.log 2>&1
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


# Configuration
NODES = {
    "hydra-ai": {
        "ip": "192.168.1.250",
        "tailscale_ip": "100.84.120.44",
        "ssh_user": "typhon",
        "role": "primary-inference",
        "gpus": ["RTX 5090", "RTX 4090"],
    },
    "hydra-compute": {
        "ip": "192.168.1.203",
        "tailscale_ip": "100.74.73.44",
        "ssh_user": "typhon",
        "role": "secondary-inference",
        "gpus": ["RTX 5070 Ti", "RTX 3060"],
    },
    "hydra-storage": {
        "ip": "192.168.1.244",
        "tailscale_ip": "100.111.54.59",
        "ssh_user": "root",
        "role": "storage-docker",
        "gpus": ["Arc A380"],
    },
}

SERVICES = {
    "databases": [
        {"name": "hydra-postgres", "port": 5432, "check": "tcp"},
        {"name": "hydra-redis", "port": 6379, "check": "tcp"},
        {"name": "hydra-qdrant", "port": 6333, "check": "http", "path": "/health"},
        {"name": "hydra-neo4j", "port": 7474, "check": "http", "path": "/"},
    ],
    "inference": [
        {"name": "tabbyapi", "port": 5000, "node": "hydra-ai", "check": "http", "path": "/v1/model"},
        {"name": "litellm", "port": 4000, "check": "http", "path": "/health"},
        {"name": "ollama", "port": 11434, "node": "hydra-compute", "check": "http", "path": "/"},
    ],
    "observability": [
        {"name": "prometheus", "port": 9090, "check": "http", "path": "/-/healthy"},
        {"name": "grafana", "port": 3003, "check": "http", "path": "/api/health"},
        {"name": "uptime-kuma", "port": 3001, "check": "http", "path": "/"},
        {"name": "alertmanager", "port": 9093, "check": "http", "path": "/-/healthy"},
    ],
    "automation": [
        {"name": "n8n", "port": 5678, "check": "http", "path": "/healthz"},
    ],
    "search": [
        {"name": "searxng", "port": 8888, "check": "http", "path": "/"},
        {"name": "firecrawl", "port": 3005, "check": "http", "path": "/"},
        {"name": "perplexica", "port": 3030, "check": "http", "path": "/"},
    ],
    "media": [
        {"name": "plex", "port": 32400, "check": "http", "path": "/identity"},
        {"name": "sonarr", "port": 8989, "check": "http", "path": "/api/v3/health"},
        {"name": "radarr", "port": 7878, "check": "http", "path": "/api/v3/health"},
        {"name": "prowlarr", "port": 9696, "check": "http", "path": "/api/v1/health"},
    ],
    "creative": [
        {"name": "comfyui", "port": 8188, "node": "hydra-compute", "check": "http", "path": "/"},
        {"name": "sillytavern", "port": 8000, "check": "http", "path": "/"},
        {"name": "open-webui", "port": 3000, "node": "hydra-ai", "check": "http", "path": "/"},
    ],
}


def run_ssh_command(node: str, command: str, timeout: int = 10) -> tuple[bool, str]:
    """Execute command on remote node via SSH."""
    node_config = NODES.get(node)
    if not node_config:
        return False, f"Unknown node: {node}"

    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{node_config['ssh_user']}@{node_config['ip']}",
        command,
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def check_http_service(host: str, port: int, path: str = "/", timeout: float = 5.0) -> dict:
    """Check if HTTP service is responding."""
    url = f"http://{host}:{port}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            return {
                "status": "healthy" if response.status_code < 400 else "unhealthy",
                "code": response.status_code,
                "latency_ms": int(response.elapsed.total_seconds() * 1000),
            }
    except httpx.TimeoutException:
        return {"status": "timeout", "code": None, "latency_ms": None}
    except Exception as e:
        return {"status": "error", "code": None, "error": str(e)}


def check_tcp_service(host: str, port: int, timeout: float = 5.0) -> dict:
    """Check if TCP port is open."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return {
            "status": "healthy" if result == 0 else "unhealthy",
            "port_open": result == 0,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_docker_stats(node: str = "hydra-storage") -> dict:
    """Get Docker container statistics."""
    cmd = "docker ps --format '{{.Names}}|{{.Status}}|{{.State}}' 2>/dev/null"
    success, output = run_ssh_command(node, cmd, timeout=30)

    if not success:
        return {"error": output, "containers": []}

    containers = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            name, status, state = parts[0], parts[1], parts[2]
            health = "healthy"
            if "unhealthy" in status.lower():
                health = "unhealthy"
            elif "starting" in status.lower():
                health = "starting"

            containers.append({
                "name": name,
                "status": status,
                "state": state,
                "health": health,
            })

    return {
        "total": len(containers),
        "healthy": sum(1 for c in containers if c["health"] == "healthy"),
        "unhealthy": sum(1 for c in containers if c["health"] == "unhealthy"),
        "containers": containers,
    }


def get_gpu_info(node: str) -> list[dict]:
    """Get GPU information from node."""
    cmd = "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits 2>/dev/null"
    success, output = run_ssh_command(node, cmd, timeout=15)

    if not success:
        return []

    gpus = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5:
            gpus.append({
                "name": parts[0],
                "memory_used_mb": int(float(parts[1])) if parts[1] != "[N/A]" else None,
                "memory_total_mb": int(float(parts[2])) if parts[2] != "[N/A]" else None,
                "temperature_c": int(float(parts[3])) if parts[3] != "[N/A]" else None,
                "power_draw_w": float(parts[4]) if parts[4] != "[N/A]" else None,
            })

    return gpus


def get_disk_usage(node: str = "hydra-storage") -> dict:
    """Get disk usage information."""
    cmd = "df -h /mnt/user 2>/dev/null | tail -1 | awk '{print $2,$3,$4,$5}'"
    success, output = run_ssh_command(node, cmd, timeout=10)

    if not success or not output:
        return {"error": "Failed to get disk info"}

    parts = output.split()
    if len(parts) >= 4:
        return {
            "total": parts[0],
            "used": parts[1],
            "available": parts[2],
            "percent_used": parts[3].rstrip("%"),
        }
    return {"error": "Parse error"}


def get_loaded_model() -> dict | None:
    """Get currently loaded model from TabbyAPI."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("http://192.168.1.250:5000/v1/model")
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("model_name", "unknown"),
                    "context_length": data.get("max_seq_len"),
                    "parameters": data.get("parameters"),
                }
    except Exception:
        pass
    return None


def collect_state() -> dict:
    """Collect complete cluster state."""
    timestamp = datetime.utcnow().isoformat() + "Z"

    state = {
        "version": "2.2.0",
        "timestamp": timestamp,
        "generated_by": "update-state.py",
        "cluster": {
            "name": "hydra",
            "phase": 11,
            "phase_name": "Evolution & Self-Improvement",
        },
        "nodes": {},
        "services": {},
        "docker": {},
        "storage": {},
        "inference": {},
    }

    # Collect node information
    for node_name, node_config in NODES.items():
        node_state = {
            "ip": node_config["ip"],
            "tailscale_ip": node_config["tailscale_ip"],
            "role": node_config["role"],
            "reachable": False,
            "gpus": [],
        }

        # Check if node is reachable
        success, _ = run_ssh_command(node_name, "echo ok", timeout=5)
        node_state["reachable"] = success

        if success and node_config.get("gpus"):
            node_state["gpus"] = get_gpu_info(node_name)

        state["nodes"][node_name] = node_state

    # Collect Docker stats from hydra-storage
    state["docker"] = get_docker_stats("hydra-storage")

    # Collect storage info
    state["storage"] = get_disk_usage("hydra-storage")

    # Check services
    default_host = "192.168.1.244"  # hydra-storage
    for category, services in SERVICES.items():
        state["services"][category] = {}
        for svc in services:
            host = NODES.get(svc.get("node", ""), {}).get("ip", default_host)
            port = svc["port"]

            if svc["check"] == "http":
                result = check_http_service(host, port, svc.get("path", "/"))
            else:
                result = check_tcp_service(host, port)

            state["services"][category][svc["name"]] = {
                "port": port,
                "host": host,
                **result,
            }

    # Get inference info
    model_info = get_loaded_model()
    if model_info:
        state["inference"]["current_model"] = model_info

    # Calculate health summary
    total_services = 0
    healthy_services = 0
    for category, services in state["services"].items():
        for svc_name, svc_state in services.items():
            total_services += 1
            if svc_state.get("status") == "healthy":
                healthy_services += 1

    state["health_summary"] = {
        "nodes_reachable": sum(1 for n in state["nodes"].values() if n["reachable"]),
        "nodes_total": len(state["nodes"]),
        "services_healthy": healthy_services,
        "services_total": total_services,
        "containers_healthy": state["docker"].get("healthy", 0),
        "containers_total": state["docker"].get("total", 0),
        "health_percentage": round(
            (healthy_services / total_services * 100) if total_services > 0 else 0, 1
        ),
    }

    return state


def main():
    parser = argparse.ArgumentParser(description="Collect Hydra cluster state")
    parser.add_argument(
        "--output", "-o",
        default="STATE.json",
        help="Output file path (default: STATE.json)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check and print, don't write file",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Collecting cluster state...")

    state = collect_state()

    if args.check_only:
        indent = 2 if args.pretty else None
        print(json.dumps(state, indent=indent))
        return

    # Write state file
    output_path = Path(args.output)
    indent = 2 if args.pretty else None
    output_path.write_text(json.dumps(state, indent=indent))

    # Print summary
    summary = state["health_summary"]
    print(f"  Nodes: {summary['nodes_reachable']}/{summary['nodes_total']} reachable")
    print(f"  Services: {summary['services_healthy']}/{summary['services_total']} healthy")
    print(f"  Containers: {summary['containers_healthy']}/{summary['containers_total']} healthy")
    print(f"  Health: {summary['health_percentage']}%")
    print(f"  Written to: {output_path}")


if __name__ == "__main__":
    main()
