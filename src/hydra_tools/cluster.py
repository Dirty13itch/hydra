"""
Cluster Tools for Hydra Agents

Provides SSH execution and cluster management capabilities.
"""

import subprocess
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from langchain.tools import tool

from .config import get_config


@dataclass
class SSHResult:
    """Result from SSH command execution."""
    stdout: str
    stderr: str
    return_code: int
    success: bool


@tool
def execute_ssh(
    node: str,
    command: str,
    timeout: int = 60,
) -> str:
    """
    Execute a command on a Hydra cluster node via SSH.

    Args:
        node: Node name (hydra-ai, hydra-compute, hydra-storage) or IP
        command: Command to execute
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Command output or error message
    """
    config = get_config()

    # Resolve node name to SSH details
    ssh_target = _resolve_node(node, config)
    if not ssh_target:
        return f"Unknown node: {node}. Valid nodes: hydra-ai, hydra-compute, hydra-storage"

    user = ssh_target["user"]
    host = ssh_target["host"]

    try:
        # Build SSH command
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={min(timeout, 30)}",
            f"{user}@{host}",
            command,
        ]

        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"

        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"

        return output if output.strip() else "(no output)"

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return "SSH client not found. Is OpenSSH installed?"
    except Exception as e:
        return f"SSH execution failed: {str(e)}"


def _resolve_node(node: str, config) -> Optional[Dict[str, str]]:
    """Resolve node name to SSH connection details."""
    # Check if it's a known node name
    if node in config.nodes:
        return config.nodes[node]

    # Check if it's an IP address (pass through)
    if "." in node:
        # Determine user based on IP
        if node == "192.168.1.244" or node == "100.111.54.59":
            return {"host": node, "user": "root"}
        else:
            return {"host": node, "user": "typhon"}

    # Check short names
    short_names = {
        "ai": "hydra-ai",
        "compute": "hydra-compute",
        "storage": "hydra-storage",
    }
    if node in short_names:
        return config.nodes[short_names[node]]

    return None


@tool
def get_cluster_status() -> str:
    """
    Get comprehensive status of all Hydra cluster nodes.

    Returns:
        Formatted cluster status report
    """
    config = get_config()

    status_report = ["# Hydra Cluster Status\n"]

    # Check each node
    for node_name, node_info in config.nodes.items():
        status_report.append(f"\n## {node_name}")
        status_report.append(f"Host: {node_info['host']}")

        # Ping check
        ping_ok = _check_ping(node_info["host"])
        status_report.append(f"Ping: {'✅' if ping_ok else '❌'}")

        if ping_ok:
            # Get basic system info via SSH
            info = _get_node_info(node_name, config)
            if info:
                status_report.append(f"Uptime: {info.get('uptime', 'unknown')}")
                status_report.append(f"Load: {info.get('load', 'unknown')}")
                status_report.append(f"Memory: {info.get('memory', 'unknown')}")
                if info.get("gpus"):
                    status_report.append(f"GPUs: {info['gpus']}")

    # Check key services
    status_report.append("\n## Key Services")
    services = _check_services(config)
    for svc_name, svc_status in services.items():
        icon = "✅" if svc_status["ok"] else "❌"
        status_report.append(f"{icon} {svc_name}: {svc_status['status']}")

    return "\n".join(status_report)


def _check_ping(host: str) -> bool:
    """Check if host responds to ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", host],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_node_info(node: str, config) -> Optional[Dict[str, str]]:
    """Get basic system info from a node."""
    try:
        # Single SSH call with multiple commands
        cmd = "uptime -p 2>/dev/null || uptime | cut -d',' -f1; " \
              "cat /proc/loadavg | cut -d' ' -f1-3; " \
              "free -h | grep Mem | awk '{print $3\"/\"$2}'; " \
              "which nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader || echo 'no-gpu'"

        ssh_target = _resolve_node(node, config)
        if not ssh_target:
            return None

        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10",
                f"{ssh_target['user']}@{ssh_target['host']}",
                cmd,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        info = {}

        if len(lines) >= 1:
            info["uptime"] = lines[0].strip()
        if len(lines) >= 2:
            info["load"] = lines[1].strip()
        if len(lines) >= 3:
            info["memory"] = lines[2].strip()
        if len(lines) >= 4 and lines[3] != "no-gpu":
            info["gpus"] = "; ".join(lines[3:])

        return info

    except Exception:
        return None


def _check_services(config) -> Dict[str, Dict[str, Any]]:
    """Check status of key services."""
    services = {}

    # TabbyAPI
    try:
        r = requests.get(f"{config.tabbyapi_url}/v1/model", timeout=5)
        model = r.json().get("model_name", "unknown") if r.ok else "error"
        services["TabbyAPI"] = {"ok": r.ok, "status": model}
    except Exception:
        services["TabbyAPI"] = {"ok": False, "status": "unreachable"}

    # LiteLLM
    try:
        r = requests.get(f"{config.litellm_url}/health", timeout=5)
        services["LiteLLM"] = {"ok": r.ok, "status": "healthy" if r.ok else "unhealthy"}
    except Exception:
        services["LiteLLM"] = {"ok": False, "status": "unreachable"}

    # Ollama
    try:
        r = requests.get(f"{config.ollama_url}/api/tags", timeout=5)
        count = len(r.json().get("models", [])) if r.ok else 0
        services["Ollama"] = {"ok": r.ok, "status": f"{count} models"}
    except Exception:
        services["Ollama"] = {"ok": False, "status": "unreachable"}

    # Qdrant
    try:
        r = requests.get(f"{config.qdrant_url}/health", timeout=5)
        services["Qdrant"] = {"ok": r.ok, "status": "healthy" if r.ok else "unhealthy"}
    except Exception:
        services["Qdrant"] = {"ok": False, "status": "unreachable"}

    # PostgreSQL (via LiteLLM health which depends on it)
    # Already checked above

    # n8n
    try:
        r = requests.get("http://192.168.1.244:5678/healthz", timeout=5)
        services["n8n"] = {"ok": r.ok, "status": "healthy" if r.ok else "unhealthy"}
    except Exception:
        services["n8n"] = {"ok": False, "status": "unreachable"}

    # SearXNG
    try:
        r = requests.get(f"{config.searxng_url}/healthz", timeout=5)
        services["SearXNG"] = {"ok": r.ok, "status": "healthy" if r.ok else "unhealthy"}
    except Exception:
        services["SearXNG"] = {"ok": False, "status": "unreachable"}

    # ComfyUI
    try:
        r = requests.get(f"{config.comfyui_url}/system_stats", timeout=5)
        services["ComfyUI"] = {"ok": r.ok, "status": "healthy" if r.ok else "unhealthy"}
    except Exception:
        services["ComfyUI"] = {"ok": False, "status": "unreachable"}

    return services


def get_gpu_status(node: str = "all") -> Dict[str, Any]:
    """
    Get detailed GPU status from cluster nodes.

    Args:
        node: Node name or 'all' for all GPU nodes

    Returns:
        Dict with GPU information per node
    """
    config = get_config()
    gpu_nodes = ["hydra-ai", "hydra-compute"]

    if node != "all":
        gpu_nodes = [node] if node in gpu_nodes else []

    results = {}

    for n in gpu_nodes:
        try:
            cmd = "nvidia-smi --query-gpu=index,name,memory.used,memory.total,memory.free,temperature.gpu,power.draw,power.limit,utilization.gpu --format=csv,noheader,nounits"

            ssh_target = _resolve_node(n, config)
            if not ssh_target:
                continue

            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=10",
                    f"{ssh_target['user']}@{ssh_target['host']}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 9:
                        gpus.append({
                            "index": int(parts[0]),
                            "name": parts[1],
                            "memory_used_mb": int(parts[2]),
                            "memory_total_mb": int(parts[3]),
                            "memory_free_mb": int(parts[4]),
                            "temperature_c": int(parts[5]),
                            "power_draw_w": float(parts[6]),
                            "power_limit_w": float(parts[7]),
                            "utilization_pct": int(parts[8]),
                        })
                results[n] = {"gpus": gpus}
            else:
                results[n] = {"error": result.stderr}

        except Exception as e:
            results[n] = {"error": str(e)}

    return results


def restart_service(node: str, service: str) -> str:
    """
    Restart a systemd service on a cluster node.

    Args:
        node: Node name
        service: Service name (without .service suffix)

    Returns:
        Status message
    """
    config = get_config()

    # Safety check - only allow known services
    allowed_services = [
        "tabbyapi",
        "ollama",
        "comfyui",
        "nvidia-persistenced",
    ]

    if service not in allowed_services:
        return f"Service '{service}' not in allowed list: {allowed_services}"

    ssh_target = _resolve_node(node, config)
    if not ssh_target:
        return f"Unknown node: {node}"

    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                f"{ssh_target['user']}@{ssh_target['host']}",
                f"sudo systemctl restart {service} && systemctl is-active {service}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return f"Service {service} restarted successfully on {node}. Status: {result.stdout.strip()}"
        else:
            return f"Failed to restart {service}: {result.stderr}"

    except Exception as e:
        return f"Error restarting service: {str(e)}"


def docker_status(container: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Docker container status from hydra-storage.

    Args:
        container: Optional specific container name

    Returns:
        Dict with container status information
    """
    config = get_config()

    try:
        if container:
            cmd = f"docker inspect {container} --format '{{{{.State.Status}}}}'"
        else:
            cmd = "docker ps --format '{{.Names}}\\t{{.Status}}\\t{{.Ports}}' | head -50"

        ssh_target = _resolve_node("hydra-storage", config)

        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                f"{ssh_target['user']}@{ssh_target['host']}",
                cmd,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if container:
            return {
                "container": container,
                "status": result.stdout.strip() if result.returncode == 0 else "not found",
            }

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                containers.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "status": parts[1] if len(parts) > 1 else "",
                    "ports": parts[2] if len(parts) > 2 else "",
                })

        return {"containers": containers, "count": len(containers)}

    except Exception as e:
        return {"error": str(e)}
