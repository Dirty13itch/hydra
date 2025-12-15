#!/usr/bin/env python3
"""
Hydra CLI - Cluster Management Tool

Usage:
    hydra status          - Show cluster health status
    hydra nodes           - List cluster nodes
    hydra services        - List services by node/category
    hydra models          - Manage LLM models
    hydra gpu             - GPU status and power management
    hydra logs            - View service logs
    hydra ssh             - SSH to cluster nodes
    hydra backup          - Backup operations
    hydra config          - View/edit configurations
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

# Cluster configuration
NODES = {
    "hydra-ai": {"ip": "192.168.1.250", "user": "typhon", "role": "Primary inference"},
    "hydra-compute": {"ip": "192.168.1.203", "user": "typhon", "role": "Secondary inference"},
    "hydra-storage": {"ip": "192.168.1.244", "user": "root", "role": "Storage & services"},
}

SERVICES = {
    "tabbyapi": {"port": 5000, "node": "hydra-ai", "health": "/health"},
    "openwebui": {"port": 3000, "node": "hydra-ai", "health": "/"},
    "ollama": {"port": 11434, "node": "hydra-compute", "health": "/api/tags"},
    "comfyui": {"port": 8188, "node": "hydra-compute", "health": "/system_stats"},
    "litellm": {"port": 4000, "node": "hydra-storage", "health": "/health"},
    "qdrant": {"port": 6333, "node": "hydra-storage", "health": "/health"},
    "postgres": {"port": 5432, "node": "hydra-storage", "health": None},
    "redis": {"port": 6379, "node": "hydra-storage", "health": None},
    "prometheus": {"port": 9090, "node": "hydra-storage", "health": "/-/healthy"},
    "grafana": {"port": 3003, "node": "hydra-storage", "health": "/api/health"},
    "n8n": {"port": 5678, "node": "hydra-storage", "health": "/healthz"},
}


def get_node_ip(node: str) -> str:
    """Get IP address for a node."""
    if node in NODES:
        return NODES[node]["ip"]
    return node


def ssh_command(node: str, command: str, capture: bool = True) -> Optional[str]:
    """Execute command on remote node via SSH."""
    node_info = NODES.get(node)
    if not node_info:
        console.print(f"[red]Unknown node: {node}[/red]")
        return None

    ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", f"{node_info['user']}@{node_info['ip']}", command]

    try:
        if capture:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
            return result.stdout
        else:
            subprocess.run(ssh_cmd, timeout=300)
            return None
    except subprocess.TimeoutExpired:
        console.print(f"[red]SSH timeout connecting to {node}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]SSH error: {e}[/red]")
        return None


def check_service_health(service: str, timeout: float = 5.0) -> tuple[bool, str, float]:
    """Check if a service is healthy."""
    svc = SERVICES.get(service)
    if not svc:
        return False, "Unknown service", 0

    node_ip = get_node_ip(svc["node"])
    port = svc["port"]
    health_endpoint = svc.get("health")

    if not health_endpoint:
        # TCP check for services without HTTP health endpoint
        import socket
        try:
            start = datetime.now()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((node_ip, port))
            latency = (datetime.now() - start).total_seconds() * 1000
            sock.close()
            if result == 0:
                return True, "Port open", latency
            return False, "Connection refused", 0
        except Exception as e:
            return False, str(e), 0

    # HTTP check
    url = f"http://{node_ip}:{port}{health_endpoint}"
    try:
        start = datetime.now()
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            latency = (datetime.now() - start).total_seconds() * 1000
            if response.status_code < 400:
                return True, f"HTTP {response.status_code}", latency
            return False, f"HTTP {response.status_code}", latency
    except httpx.TimeoutException:
        return False, "Timeout", timeout * 1000
    except httpx.ConnectError:
        return False, "Connection refused", 0
    except Exception as e:
        return False, str(e), 0


# === STATUS COMMAND ===

def cmd_status(args):
    """Show cluster health status."""
    console.print(Panel.fit("[bold blue]Hydra Cluster Status[/bold blue]"))

    # Check nodes
    table = Table(title="Nodes", box=box.ROUNDED)
    table.add_column("Node", style="cyan")
    table.add_column("IP", style="dim")
    table.add_column("Status")
    table.add_column("Role")

    for node, info in NODES.items():
        # Quick SSH check
        result = ssh_command(node, "echo ok")
        if result and "ok" in result:
            status = "[green]● Online[/green]"
        else:
            status = "[red]● Offline[/red]"
        table.add_row(node, info["ip"], status, info["role"])

    console.print(table)
    console.print()

    # Check services
    table = Table(title="Services", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Node")
    table.add_column("Port")
    table.add_column("Status")
    table.add_column("Latency")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Checking services...", total=len(SERVICES))

        for service, info in SERVICES.items():
            progress.update(task, description=f"Checking {service}...")
            healthy, message, latency = check_service_health(service)

            if healthy:
                status = f"[green]● {message}[/green]"
            else:
                status = f"[red]● {message}[/red]"

            latency_str = f"{latency:.1f}ms" if latency > 0 else "-"

            table.add_row(service, info["node"], str(info["port"]), status, latency_str)
            progress.advance(task)

    console.print(table)


# === NODES COMMAND ===

def cmd_nodes(args):
    """List cluster nodes with details."""
    table = Table(title="Hydra Cluster Nodes", box=box.ROUNDED)
    table.add_column("Node", style="cyan bold")
    table.add_column("IP Address")
    table.add_column("User")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Uptime")

    for node, info in NODES.items():
        # Get uptime
        uptime = ssh_command(node, "uptime -p 2>/dev/null || uptime")
        if uptime:
            uptime = uptime.strip()[:30]
            status = "[green]● Online[/green]"
        else:
            uptime = "-"
            status = "[red]● Offline[/red]"

        table.add_row(node, info["ip"], info["user"], info["role"], status, uptime)

    console.print(table)


# === SERVICES COMMAND ===

def cmd_services(args):
    """List services with optional filtering."""
    node_filter = args.node
    category_filter = args.category

    table = Table(title="Cluster Services", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Port")
    table.add_column("Node")
    table.add_column("Status")
    table.add_column("URL")

    for service, info in sorted(SERVICES.items()):
        if node_filter and info["node"] != node_filter:
            continue

        healthy, message, _ = check_service_health(service)
        status = "[green]●[/green]" if healthy else "[red]●[/red]"
        node_ip = get_node_ip(info["node"])
        url = f"http://{node_ip}:{info['port']}"

        table.add_row(service, str(info["port"]), info["node"], status, url)

    console.print(table)


# === GPU COMMAND ===

def cmd_gpu(args):
    """Show GPU status across cluster."""
    console.print(Panel.fit("[bold blue]GPU Status[/bold blue]"))

    for node in ["hydra-ai", "hydra-compute"]:
        console.print(f"\n[bold cyan]{node}[/bold cyan]")

        output = ssh_command(
            node,
            "nvidia-smi --query-gpu=index,name,memory.used,memory.total,power.draw,temperature.gpu --format=csv,noheader"
        )

        if not output:
            console.print("[red]  Cannot retrieve GPU info[/red]")
            continue

        table = Table(box=box.SIMPLE)
        table.add_column("GPU", style="cyan")
        table.add_column("Name")
        table.add_column("VRAM Used")
        table.add_column("VRAM Total")
        table.add_column("Power")
        table.add_column("Temp")

        for line in output.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                idx, name, mem_used, mem_total, power, temp = parts[:6]

                # Color code based on usage
                mem_pct = float(mem_used.replace(" MiB", "")) / float(mem_total.replace(" MiB", "")) * 100
                if mem_pct > 90:
                    mem_style = "red"
                elif mem_pct > 70:
                    mem_style = "yellow"
                else:
                    mem_style = "green"

                table.add_row(
                    f"GPU {idx}",
                    name,
                    f"[{mem_style}]{mem_used}[/{mem_style}]",
                    mem_total,
                    power,
                    f"{temp}°C"
                )

        console.print(table)


def cmd_gpu_power(args):
    """Set GPU power limits."""
    node = args.node
    gpu_index = args.gpu
    limit = args.limit

    console.print(f"Setting GPU {gpu_index} power limit to {limit}W on {node}...")

    output = ssh_command(node, f"sudo nvidia-smi -i {gpu_index} -pl {limit}")
    if output:
        console.print(f"[green]Power limit set successfully[/green]")
        console.print(output)
    else:
        console.print("[red]Failed to set power limit[/red]")


# === MODELS COMMAND ===

def cmd_models(args):
    """List loaded and available models."""
    console.print(Panel.fit("[bold blue]LLM Models[/bold blue]"))

    # TabbyAPI current model
    console.print("\n[bold cyan]TabbyAPI (hydra-ai:5000)[/bold cyan]")
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://192.168.1.250:5000/v1/model")
            if response.status_code == 200:
                data = response.json()
                table = Table(box=box.SIMPLE)
                table.add_column("Field", style="dim")
                table.add_column("Value", style="cyan")
                for key, value in data.items():
                    if key != "loras":
                        table.add_row(key, str(value))
                console.print(table)
            else:
                console.print("[yellow]No model loaded[/yellow]")
    except Exception as e:
        console.print(f"[red]Cannot reach TabbyAPI: {e}[/red]")

    # Ollama models
    console.print("\n[bold cyan]Ollama (hydra-compute:11434)[/bold cyan]")
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://192.168.1.203:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                table = Table(box=box.SIMPLE)
                table.add_column("Model", style="cyan")
                table.add_column("Size")
                table.add_column("Modified")

                for model in models:
                    name = model.get("name", "")
                    size = f"{model.get('size', 0) / 1e9:.1f}GB"
                    modified = model.get("modified_at", "")[:10]
                    table.add_row(name, size, modified)

                console.print(table)
            else:
                console.print("[yellow]Cannot list models[/yellow]")
    except Exception as e:
        console.print(f"[red]Cannot reach Ollama: {e}[/red]")


# === LOGS COMMAND ===

def cmd_logs(args):
    """View service logs."""
    service = args.service
    lines = args.lines
    follow = args.follow

    # Determine node and get logs
    svc = SERVICES.get(service)
    if not svc:
        console.print(f"[red]Unknown service: {service}[/red]")
        return

    node = svc["node"]

    if node == "hydra-storage":
        # Docker logs
        cmd = f"docker logs --tail {lines}"
        if follow:
            cmd += " -f"
        cmd += f" hydra-{service}"
        ssh_command(node, cmd, capture=False)
    else:
        # systemd logs
        cmd = f"journalctl -u {service} -n {lines}"
        if follow:
            cmd += " -f"
        ssh_command(node, cmd, capture=False)


# === SSH COMMAND ===

def cmd_ssh(args):
    """SSH to a cluster node."""
    node = args.node

    if node not in NODES:
        console.print(f"[red]Unknown node: {node}[/red]")
        console.print(f"Available nodes: {', '.join(NODES.keys())}")
        return

    info = NODES[node]
    console.print(f"[cyan]Connecting to {node} ({info['ip']})...[/cyan]")

    subprocess.run(["ssh", f"{info['user']}@{info['ip']}"])


# === BACKUP COMMAND ===

def cmd_backup(args):
    """Backup operations."""
    if args.action == "create":
        console.print("[cyan]Creating cluster backup...[/cyan]")
        ssh_command("hydra-storage", "/mnt/user/appdata/hydra-stack/scripts/backup-create.sh", capture=False)
    elif args.action == "verify":
        console.print("[cyan]Verifying backups...[/cyan]")
        ssh_command("hydra-storage", "/mnt/user/appdata/hydra-stack/scripts/backup-verify.sh", capture=False)
    elif args.action == "list":
        console.print("[cyan]Listing backups...[/cyan]")
        output = ssh_command("hydra-storage", "ls -lh /mnt/user/backups/hydra/")
        if output:
            console.print(output)


# === CONFIG COMMAND ===

def cmd_config(args):
    """View or edit configurations."""
    if args.action == "show":
        console.print(Panel.fit("[bold blue]Cluster Configuration[/bold blue]"))

        # Show key configs
        console.print("\n[bold]Nodes:[/bold]")
        for node, info in NODES.items():
            console.print(f"  {node}: {info['ip']} ({info['role']})")

        console.print("\n[bold]Key Ports:[/bold]")
        for service, info in sorted(SERVICES.items(), key=lambda x: x[1]["port"]):
            console.print(f"  {info['port']:5d} - {service} ({info['node']})")

    elif args.action == "edit":
        target = args.target
        configs = {
            "tabbyapi": ("hydra-ai", "/opt/tabbyapi/config.yml"),
            "litellm": ("hydra-storage", "/mnt/user/appdata/hydra-stack/litellm-config.yaml"),
            "prometheus": ("hydra-storage", "/mnt/user/appdata/prometheus/prometheus.yml"),
        }

        if target not in configs:
            console.print(f"[red]Unknown config: {target}[/red]")
            console.print(f"Available: {', '.join(configs.keys())}")
            return

        node, path = configs[target]
        console.print(f"[cyan]Opening {path} on {node}...[/cyan]")
        ssh_command(node, f"$EDITOR {path} || nano {path} || vi {path}", capture=False)


# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description="Hydra Cluster CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="hydra-cli 1.0.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    p_status = subparsers.add_parser("status", help="Show cluster health status")
    p_status.set_defaults(func=cmd_status)

    # nodes
    p_nodes = subparsers.add_parser("nodes", help="List cluster nodes")
    p_nodes.set_defaults(func=cmd_nodes)

    # services
    p_services = subparsers.add_parser("services", help="List services")
    p_services.add_argument("--node", "-n", help="Filter by node")
    p_services.add_argument("--category", "-c", help="Filter by category")
    p_services.set_defaults(func=cmd_services)

    # gpu
    p_gpu = subparsers.add_parser("gpu", help="GPU status and management")
    gpu_sub = p_gpu.add_subparsers(dest="gpu_action")

    p_gpu_status = gpu_sub.add_parser("status", help="Show GPU status")
    p_gpu_status.set_defaults(func=cmd_gpu)

    p_gpu_power = gpu_sub.add_parser("power", help="Set power limit")
    p_gpu_power.add_argument("node", help="Node name")
    p_gpu_power.add_argument("gpu", type=int, help="GPU index")
    p_gpu_power.add_argument("limit", type=int, help="Power limit in watts")
    p_gpu_power.set_defaults(func=cmd_gpu_power)

    p_gpu.set_defaults(func=cmd_gpu)

    # models
    p_models = subparsers.add_parser("models", help="List LLM models")
    p_models.set_defaults(func=cmd_models)

    # logs
    p_logs = subparsers.add_parser("logs", help="View service logs")
    p_logs.add_argument("service", help="Service name")
    p_logs.add_argument("-n", "--lines", type=int, default=50, help="Number of lines")
    p_logs.add_argument("-f", "--follow", action="store_true", help="Follow logs")
    p_logs.set_defaults(func=cmd_logs)

    # ssh
    p_ssh = subparsers.add_parser("ssh", help="SSH to cluster node")
    p_ssh.add_argument("node", help="Node name")
    p_ssh.set_defaults(func=cmd_ssh)

    # backup
    p_backup = subparsers.add_parser("backup", help="Backup operations")
    p_backup.add_argument("action", choices=["create", "verify", "list"], help="Backup action")
    p_backup.set_defaults(func=cmd_backup)

    # config
    p_config = subparsers.add_parser("config", help="Configuration management")
    p_config.add_argument("action", choices=["show", "edit"], help="Config action")
    p_config.add_argument("target", nargs="?", help="Config target (for edit)")
    p_config.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        # Default to status
        args.func = cmd_status
        args.func(args)
    elif hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
