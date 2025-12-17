"""
Health Check CLI

Command-line interface for checking Hydra cluster health.
"""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

import requests
from rich.console import Console
from rich.live import Live
from rich.table import Table

from ..config import get_config

console = Console()


@dataclass
class ServiceStatus:
    """Service health status."""
    name: str
    url: str
    healthy: bool
    latency_ms: float
    error: Optional[str] = None


# Service definitions
SERVICES = {
    # Core API
    "Hydra Tools API": ("http://192.168.1.244:8700/health", "hydra-storage"),

    # Inference
    "TabbyAPI": ("http://192.168.1.250:5000/health", "hydra-ai"),
    "Ollama": ("http://192.168.1.203:11434/api/tags", "hydra-compute"),
    "LiteLLM": ("http://192.168.1.244:4000/health/liveliness", "hydra-storage"),
    "ComfyUI": ("http://192.168.1.203:8188/system_stats", "hydra-compute"),

    # Databases
    "PostgreSQL": ("tcp://192.168.1.244:5432", "hydra-storage"),
    "Qdrant": ("http://192.168.1.244:6333/healthz", "hydra-storage"),
    "Redis": ("tcp://192.168.1.244:6379", "hydra-storage"),
    "Meilisearch": ("http://192.168.1.244:7700/health", "hydra-storage"),

    # Observability
    "Prometheus": ("http://192.168.1.244:9090/-/healthy", "hydra-storage"),
    "Grafana": ("http://192.168.1.244:3003/api/health", "hydra-storage"),
    "Loki": ("http://192.168.1.244:3100/ready", "hydra-storage"),

    # Automation
    "n8n": ("http://192.168.1.244:5678/healthz", "hydra-storage"),

    # Search & Research
    "SearXNG": ("http://192.168.1.244:8888/healthz", "hydra-storage"),
    "Firecrawl": ("http://192.168.1.244:3005", "hydra-storage"),

    # Voice
    "Kokoro TTS": ("http://192.168.1.244:8880/health", "hydra-storage"),

    # Document Processing
    "Docling": ("http://192.168.1.244:5001/health", "hydra-storage"),

    # Memory & Agents
    "Letta": ("http://192.168.1.244:8283/v1/health", "hydra-storage"),

    # Web UIs
    "Open WebUI": ("http://192.168.1.250:3000", "hydra-ai"),
    "Perplexica": ("http://192.168.1.244:3030", "hydra-storage"),
    "SillyTavern": ("http://192.168.1.244:8000", "hydra-storage"),
    "Homepage": ("http://192.168.1.244:3333", "hydra-storage"),
    "Portainer": ("http://192.168.1.244:9000/api/status", "hydra-storage"),
}


def check_service(name: str, url: str) -> ServiceStatus:
    """Check a single service health."""
    import time

    start = time.time()

    try:
        if url.startswith("tcp://"):
            # TCP check
            host_port = url.replace("tcp://", "")
            host, port = host_port.split(":")
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            latency = (time.time() - start) * 1000

            if result == 0:
                return ServiceStatus(name, url, True, latency)
            else:
                return ServiceStatus(name, url, False, latency, "Connection refused")

        else:
            # HTTP check
            resp = requests.get(url, timeout=5)
            latency = (time.time() - start) * 1000

            if resp.status_code < 400:
                return ServiceStatus(name, url, True, latency)
            else:
                return ServiceStatus(name, url, False, latency, f"HTTP {resp.status_code}")

    except requests.exceptions.Timeout:
        return ServiceStatus(name, url, False, 5000, "Timeout")
    except requests.exceptions.ConnectionError:
        return ServiceStatus(name, url, False, 0, "Connection failed")
    except Exception as e:
        return ServiceStatus(name, url, False, 0, str(e))


def check_all_services() -> List[ServiceStatus]:
    """Check all services in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_service, name, url): name
            for name, (url, _) in SERVICES.items()
        }

        for future in as_completed(futures):
            results.append(future.result())

    return sorted(results, key=lambda x: (not x.healthy, x.name))


def check_nodes() -> dict:
    """Check node connectivity."""
    nodes = {
        "hydra-ai": "192.168.1.250",
        "hydra-compute": "192.168.1.203",
        "hydra-storage": "192.168.1.244",
    }

    results = {}

    for name, ip in nodes.items():
        try:
            # Ping check
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", ip],
                capture_output=True,
                timeout=5,
            )
            results[name] = {
                "ip": ip,
                "reachable": result.returncode == 0,
            }
        except Exception:
            results[name] = {"ip": ip, "reachable": False}

    return results


def check_gpus() -> dict:
    """Check GPU status on inference nodes."""
    gpus = {}

    # hydra-ai
    try:
        output = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             "typhon@192.168.1.250",
             "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if output.returncode == 0:
            gpus["hydra-ai"] = output.stdout.strip().split("\n")
    except Exception:
        gpus["hydra-ai"] = []

    # hydra-compute
    try:
        output = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             "typhon@192.168.1.203",
             "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if output.returncode == 0:
            gpus["hydra-compute"] = output.stdout.strip().split("\n")
    except Exception:
        gpus["hydra-compute"] = []

    return gpus


def print_health_report():
    """Print comprehensive health report."""
    console.print("\n[bold cyan]═══ HYDRA CLUSTER HEALTH REPORT ═══[/bold cyan]\n")

    # Node connectivity
    console.print("[bold]Node Connectivity[/bold]")
    nodes = check_nodes()
    for name, info in nodes.items():
        status = "✅" if info["reachable"] else "❌"
        console.print(f"  {status} {name} ({info['ip']})")
    console.print()

    # Services
    console.print("[bold]Service Status[/bold]")
    statuses = check_all_services()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Service")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Node")

    for status in statuses:
        node = SERVICES.get(status.name, ("", ""))[1]
        if status.healthy:
            table.add_row(
                status.name,
                "[green]✅ UP[/green]",
                f"{status.latency_ms:.0f}ms",
                node
            )
        else:
            table.add_row(
                status.name,
                f"[red]❌ {status.error or 'DOWN'}[/red]",
                "-",
                node
            )

    console.print(table)

    # Summary
    healthy = sum(1 for s in statuses if s.healthy)
    total = len(statuses)
    console.print(f"\n[bold]Summary:[/bold] {healthy}/{total} services healthy")

    # GPUs
    console.print("\n[bold]GPU Status[/bold]")
    gpus = check_gpus()
    for node, gpu_list in gpus.items():
        console.print(f"  {node}:")
        if gpu_list:
            for gpu in gpu_list:
                console.print(f"    {gpu}")
        else:
            console.print("    [yellow]No GPU data available[/yellow]")

    console.print()

    return healthy == total


def watch_mode(interval: int = 30):
    """Continuously monitor health."""
    import time

    console.print(f"[cyan]Monitoring cluster health (refresh every {interval}s, Ctrl+C to stop)[/cyan]\n")

    try:
        while True:
            console.clear()
            console.print(f"[dim]Last update: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            print_health_report()
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Hydra Health Check")
    parser.add_argument("--watch", "-w", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Watch interval (seconds)")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")

    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    elif args.json:
        import json
        statuses = check_all_services()
        output = {
            s.name: {
                "healthy": s.healthy,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in statuses
        }
        print(json.dumps(output, indent=2))
    else:
        healthy = print_health_report()
        sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
