#!/usr/bin/env python3
"""Generate STATE.json from Hydra cluster state.

Queries the MCP server and other endpoints to create a comprehensive
state file that Claude Code can read at session start.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict

MCP_URL = "http://192.168.1.244:8600"
LETTA_URL = "http://192.168.1.244:8283"
OLLAMA_URL = "http://192.168.1.203:11434"

def safe_get(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Safely get JSON from URL."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Unknown error"}


def get_cluster_status() -> Dict[str, Any]:
    """Get cluster status from MCP server."""
    return safe_get(f"{MCP_URL}/cluster/status")


def get_services_status() -> Dict[str, Any]:
    """Get services status from MCP server."""
    return safe_get(f"{MCP_URL}/services/status")


def get_containers() -> Dict[str, Any]:
    """Get container list from MCP server."""
    return safe_get(f"{MCP_URL}/containers/list")


def parse_health_from_status(status: str) -> str:
    """Parse health status from docker status string.

    Examples:
      "Up 12 minutes (unhealthy)" -> "unhealthy"
      "Up 3 hours (healthy)" -> "healthy"
      "Up 8 hours" -> "running"
      "Exited (1) 2 hours ago" -> "exited"
    """
    if "(healthy)" in status:
        return "healthy"
    elif "(unhealthy)" in status:
        return "unhealthy"
    elif "Up" in status:
        return "running"
    elif "Exited" in status:
        return "exited"
    elif "Restarting" in status:
        return "restarting"
    return "unknown"


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary from MCP server."""
    return safe_get(f"{MCP_URL}/metrics/summary")


def get_ollama_models() -> list:
    """Get available Ollama models."""
    data = safe_get(f"{OLLAMA_URL}/api/tags")
    if "models" in data:
        return [m.get("name") for m in data["models"]]
    return []


def get_letta_agent_info() -> Dict[str, Any]:
    """Get Letta agent information."""
    # hydra-steward agent ID
    agent_id = "agent-b3fb1747-1a5b-4c94-b713-11d6403350bf"
    return safe_get(f"{LETTA_URL}/v1/agents/{agent_id}")


def generate_state() -> Dict[str, Any]:
    """Generate complete state object."""
    state = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "1.0",
        "cluster": {},
        "services": {},
        "containers": [],
        "metrics": {},
        "models": [],
        "agents": {}
    }

    # Cluster status
    cluster = get_cluster_status()
    if "error" not in cluster:
        state["cluster"] = {
            "prometheus_targets": cluster.get("prometheus", {}),
            "letta": cluster.get("letta", {}),
            "crewai": cluster.get("crewai", {}),
            "qdrant_collections": cluster.get("qdrant", {}).get("collections", 0)
        }

    # Services
    services = get_services_status()
    if "error" not in services:
        state["services"] = services

    # Containers
    containers = get_containers()
    if "error" not in containers and "containers" in containers:
        state["containers"] = [
            {
                "name": c.get("name"),
                "status": c.get("status"),
                "health": parse_health_from_status(c.get("status", ""))
            }
            for c in containers["containers"]
        ]

    # Metrics summary
    metrics = get_metrics_summary()
    if "error" not in metrics:
        state["metrics"] = metrics

    # Ollama models
    state["models"] = get_ollama_models()

    # Letta agent
    agent = get_letta_agent_info()
    if "error" not in agent:
        state["agents"] = {
            "hydra-steward": {
                "id": agent.get("id"),
                "name": agent.get("name"),
                "created_at": agent.get("created_at")
            }
        }

    # Summary
    running_containers = len([c for c in state["containers"] if c.get("health") in ("running", "healthy", "unhealthy")])
    healthy_containers = len([c for c in state["containers"] if c.get("health") == "healthy"])
    unhealthy_containers = len([c for c in state["containers"] if c.get("health") == "unhealthy"])

    state["summary"] = {
        "total_containers": len(state["containers"]),
        "running_containers": running_containers,
        "healthy_containers": healthy_containers,
        "unhealthy_containers": unhealthy_containers,
        "available_models": len(state["models"]),
        "status": "healthy" if unhealthy_containers == 0 and running_containers > 40 else "degraded"
    }

    return state


def main():
    """Generate and output STATE.json."""
    state = generate_state()
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
