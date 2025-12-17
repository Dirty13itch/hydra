"""
Monitoring Tools for CrewAI Integration

Provides tools for agents to query Prometheus, Docker status,
GPU status, and other monitoring data from the Hydra cluster.
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class MetricResult:
    """Result from a Prometheus query."""
    metric_name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime


@dataclass
class ContainerStatus:
    """Docker container status."""
    name: str
    status: str
    health: Optional[str]
    uptime: str
    ports: List[str]
    image: str


@dataclass
class GPUStatus:
    """GPU status from nvidia-smi."""
    name: str
    index: int
    memory_used_gb: float
    memory_total_gb: float
    memory_percent: float
    temperature_c: int
    power_draw_w: float
    utilization_percent: int


class PrometheusQueryTool:
    """
    Tool for querying Prometheus metrics.

    Used by CrewAI agents to fetch cluster metrics for analysis.
    """

    def __init__(self, base_url: str = "http://192.168.1.244:9090"):
        self.base_url = base_url

    async def query(self, promql: str) -> List[MetricResult]:
        """
        Execute a PromQL query.

        Args:
            promql: The PromQL query string

        Returns:
            List of metric results
        """
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params={"query": promql}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        for result in data.get("data", {}).get("result", []):
                            metric = result.get("metric", {})
                            value = result.get("value", [0, "0"])
                            results.append(MetricResult(
                                metric_name=metric.get("__name__", ""),
                                value=float(value[1]),
                                labels=metric,
                                timestamp=datetime.fromtimestamp(float(value[0]))
                            ))
        except Exception as e:
            print(f"Prometheus query error: {e}")
        return results

    async def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: str = "1m"
    ) -> List[Dict[str, Any]]:
        """
        Execute a range query.

        Args:
            promql: The PromQL query string
            start: Start time
            end: End time
            step: Query resolution step

        Returns:
            List of time series data
        """
        results = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/query_range",
                    params={
                        "query": promql,
                        "start": start.isoformat() + "Z",
                        "end": end.isoformat() + "Z",
                        "step": step
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        results = data.get("data", {}).get("result", [])
        except Exception as e:
            print(f"Prometheus range query error: {e}")
        return results

    async def get_gpu_metrics(self) -> List[Dict[str, Any]]:
        """Get current GPU metrics for all nodes."""
        metrics = {}

        # Memory usage
        mem_results = await self.query("nvidia_smi_memory_used_bytes / nvidia_smi_memory_total_bytes * 100")
        for r in mem_results:
            node = r.labels.get("instance", "unknown").split(":")[0]
            gpu = r.labels.get("gpu", "0")
            key = f"{node}_gpu{gpu}"
            if key not in metrics:
                metrics[key] = {"node": node, "gpu": gpu}
            metrics[key]["memory_percent"] = r.value

        # Temperature
        temp_results = await self.query("nvidia_smi_temperature_gpu")
        for r in temp_results:
            node = r.labels.get("instance", "unknown").split(":")[0]
            gpu = r.labels.get("gpu", "0")
            key = f"{node}_gpu{gpu}"
            if key in metrics:
                metrics[key]["temperature_c"] = r.value

        # Power
        power_results = await self.query("nvidia_smi_power_draw_watts")
        for r in power_results:
            node = r.labels.get("instance", "unknown").split(":")[0]
            gpu = r.labels.get("gpu", "0")
            key = f"{node}_gpu{gpu}"
            if key in metrics:
                metrics[key]["power_watts"] = r.value

        return list(metrics.values())

    async def get_node_health(self, node: str) -> Dict[str, Any]:
        """Get health metrics for a specific node."""
        health = {
            "node": node,
            "up": False,
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0
        }

        # Check if node is up
        up_results = await self.query(f'up{{instance=~"{node}.*"}}')
        if up_results and up_results[0].value == 1:
            health["up"] = True

        # CPU usage
        cpu_results = await self.query(
            f'100 - (avg by(instance) (irate(node_cpu_seconds_total{{mode="idle", instance=~"{node}.*"}}[5m])) * 100)'
        )
        if cpu_results:
            health["cpu_percent"] = cpu_results[0].value

        # Memory usage
        mem_results = await self.query(
            f'(1 - (node_memory_MemAvailable_bytes{{instance=~"{node}.*"}} / node_memory_MemTotal_bytes{{instance=~"{node}.*"}})) * 100'
        )
        if mem_results:
            health["memory_percent"] = mem_results[0].value

        # Disk usage
        disk_results = await self.query(
            f'100 - ((node_filesystem_avail_bytes{{instance=~"{node}.*",mountpoint="/"}} / node_filesystem_size_bytes{{instance=~"{node}.*",mountpoint="/"}}) * 100)'
        )
        if disk_results:
            health["disk_percent"] = disk_results[0].value

        return health


class DockerStatusTool:
    """
    Tool for checking Docker container status.

    Connects to Docker API on Unraid to check container health.
    """

    def __init__(self, host: str = "192.168.1.244", port: int = 2375):
        self.base_url = f"http://{host}:{port}"

    async def list_containers(self, all: bool = False) -> List[ContainerStatus]:
        """
        List Docker containers.

        Args:
            all: Include stopped containers

        Returns:
            List of container statuses
        """
        containers = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/containers/json",
                    params={"all": "true" if all else "false"}
                )
                if resp.status_code == 200:
                    for c in resp.json():
                        # Parse port bindings
                        ports = []
                        for p in c.get("Ports", []):
                            if p.get("PublicPort"):
                                ports.append(f"{p['PublicPort']}:{p['PrivatePort']}")

                        containers.append(ContainerStatus(
                            name=c.get("Names", ["/unknown"])[0].lstrip("/"),
                            status=c.get("Status", "unknown"),
                            health=c.get("State", "unknown"),
                            uptime=c.get("Status", ""),
                            ports=ports,
                            image=c.get("Image", "")
                        ))
        except Exception as e:
            print(f"Docker API error: {e}")
        return containers

    async def get_container_stats(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific container."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/containers/{container_name}/stats",
                    params={"stream": "false"}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"Docker stats error: {e}")
        return None

    async def get_unhealthy_containers(self) -> List[ContainerStatus]:
        """Get list of unhealthy or stopped containers."""
        all_containers = await self.list_containers(all=True)
        unhealthy = []
        for c in all_containers:
            if c.health not in ("running", "healthy") or "Exited" in c.status:
                unhealthy.append(c)
        return unhealthy

    async def restart_container(self, container_name: str) -> bool:
        """Restart a container."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/containers/{container_name}/restart"
                )
                return resp.status_code == 204
        except Exception as e:
            print(f"Docker restart error: {e}")
        return False


class GPUStatusTool:
    """
    Tool for getting GPU status via SSH commands.

    Falls back to Prometheus metrics if SSH not available.
    """

    def __init__(
        self,
        hydra_ai_host: str = "192.168.1.250",
        hydra_compute_host: str = "192.168.1.203",
        prometheus_url: str = "http://192.168.1.244:9090"
    ):
        self.hosts = {
            "hydra-ai": hydra_ai_host,
            "hydra-compute": hydra_compute_host
        }
        self.prometheus = PrometheusQueryTool(prometheus_url)

    async def get_all_gpus(self) -> List[GPUStatus]:
        """Get status of all GPUs across all nodes."""
        gpus = []

        # Try to get from Prometheus first (more reliable)
        metrics = await self.prometheus.get_gpu_metrics()
        for m in metrics:
            gpus.append(GPUStatus(
                name=f"GPU {m.get('gpu', 0)}",
                index=int(m.get("gpu", 0)),
                memory_used_gb=0,  # Would need additional query
                memory_total_gb=0,
                memory_percent=m.get("memory_percent", 0),
                temperature_c=int(m.get("temperature_c", 0)),
                power_draw_w=m.get("power_watts", 0),
                utilization_percent=0
            ))

        return gpus

    async def check_vram_available(self, required_gb: float) -> Dict[str, bool]:
        """
        Check if nodes have enough VRAM available.

        Args:
            required_gb: VRAM required in GB

        Returns:
            Dict mapping node names to availability
        """
        availability = {}
        metrics = await self.prometheus.get_gpu_metrics()

        for m in metrics:
            node = m.get("node", "unknown")
            memory_percent = m.get("memory_percent", 100)
            # Assuming we know total VRAM from config
            # hydra-ai: 32GB + 24GB, hydra-compute: 16GB + 12GB
            total_vram = 32 if "ai" in node else 16
            available_gb = total_vram * (100 - memory_percent) / 100

            if node not in availability:
                availability[node] = False
            if available_gb >= required_gb:
                availability[node] = True

        return availability


class DiskStatusTool:
    """Tool for checking disk status."""

    def __init__(self, prometheus_url: str = "http://192.168.1.244:9090"):
        self.prometheus = PrometheusQueryTool(prometheus_url)

    async def get_disk_usage(self) -> List[Dict[str, Any]]:
        """Get disk usage for all nodes."""
        results = []

        query = '100 - ((node_filesystem_avail_bytes{mountpoint=~"/|/mnt/.*"} / node_filesystem_size_bytes{mountpoint=~"/|/mnt/.*"}) * 100)'
        metrics = await self.prometheus.query(query)

        for m in metrics:
            results.append({
                "node": m.labels.get("instance", "").split(":")[0],
                "mountpoint": m.labels.get("mountpoint", "/"),
                "usage_percent": m.value
            })

        return results

    async def check_disk_alerts(self, threshold: float = 90.0) -> List[Dict[str, Any]]:
        """Get disks above threshold usage."""
        all_disks = await self.get_disk_usage()
        return [d for d in all_disks if d["usage_percent"] >= threshold]


class HealthCheckTool:
    """Tool for running health checks on services."""

    def __init__(self):
        self.endpoints = {
            "litellm": "http://192.168.1.244:4000/health/liveliness",
            "prometheus": "http://192.168.1.244:9090/-/healthy",
            "grafana": "http://192.168.1.244:3003/api/health",
            "qdrant": "http://192.168.1.244:6333/healthz",
            "tabbyapi": "http://192.168.1.250:5000/health",
            "ollama": "http://192.168.1.203:11434/api/tags",
            "comfyui": "http://192.168.1.203:8188/system_stats",
            "letta": "http://192.168.1.244:8283/v1/health",
            "voice": "http://192.168.1.244:8850/health",
            "stt": "http://192.168.1.203:9001/health",
            "tools_api": "http://192.168.1.244:8700/health",
        }

    async def check_endpoint(self, name: str, url: str) -> Dict[str, Any]:
        """Check a single endpoint."""
        result = {
            "name": name,
            "url": url,
            "healthy": False,
            "latency_ms": None,
            "error": None
        }

        try:
            start = datetime.now()
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                latency = (datetime.now() - start).total_seconds() * 1000
                result["latency_ms"] = latency
                result["healthy"] = resp.status_code in (200, 204)
        except Exception as e:
            result["error"] = str(e)

        return result

    async def check_all(self) -> List[Dict[str, Any]]:
        """Check all known endpoints."""
        results = []
        for name, url in self.endpoints.items():
            result = await self.check_endpoint(name, url)
            results.append(result)
        return results

    async def get_unhealthy_services(self) -> List[Dict[str, Any]]:
        """Get list of unhealthy services."""
        all_results = await self.check_all()
        return [r for r in all_results if not r["healthy"]]
