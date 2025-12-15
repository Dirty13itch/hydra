"""
Hardware Discovery Module for Hydra Cluster

Provides live, on-demand hardware inventory by querying:
- Prometheus node_exporter metrics (CPU, RAM, disk)
- DCGM exporter (hydra-ai GPUs)
- nvidia-smi exporter (hydra-compute GPUs)

Usage:
    from hydra_tools.hardware_discovery import HardwareDiscovery

    discovery = HardwareDiscovery()
    inventory = await discovery.get_inventory()
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import httpx

# Prometheus and exporter endpoints
PROMETHEUS_URL = "http://192.168.1.244:9090"
DCGM_EXPORTER = "http://192.168.1.250:9835"  # hydra-ai
NVIDIA_EXPORTER = "http://192.168.1.203:9835"  # hydra-compute

# Node mapping
NODE_IPS = {
    "hydra-ai": "192.168.1.250",
    "hydra-compute": "192.168.1.203",
    "hydra-storage": "192.168.1.244",
}

# Cache TTL in seconds
CACHE_TTL = 60


@dataclass
class GPUInfo:
    """GPU hardware information."""
    index: int
    name: str
    memory_total_gb: float
    memory_used_gb: float
    memory_free_gb: float
    temperature_c: Optional[float] = None
    utilization_pct: Optional[float] = None
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None


@dataclass
class NodeInfo:
    """Node hardware information."""
    name: str
    ip: str
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    ram_total_gb: float
    ram_used_gb: float
    ram_available_gb: float
    gpus: list[GPUInfo] = field(default_factory=list)
    role: str = ""
    os: str = ""


@dataclass
class ClusterInventory:
    """Complete cluster hardware inventory."""
    nodes: dict[str, NodeInfo]
    total_cpu_cores: int
    total_cpu_threads: int
    total_ram_gb: float
    total_vram_gb: float
    vram_used_gb: float
    vram_free_gb: float
    timestamp: datetime
    cached: bool = False


class HardwareDiscovery:
    """Discovers and caches hardware information from the cluster."""

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.prometheus_url = prometheus_url
        self._cache: Optional[ClusterInventory] = None
        self._cache_time: float = 0

    async def _query_prometheus(self, query: str) -> dict:
        """Execute a PromQL query."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("result", [])
            except Exception as e:
                print(f"Prometheus query failed: {e}")
                return []

    async def _get_cpu_info(self) -> dict[str, dict]:
        """Get CPU core counts from Prometheus."""
        results = await self._query_prometheus(
            'count by (instance)(node_cpu_seconds_total{mode="idle"})'
        )

        cpu_info = {}
        for r in results:
            instance = r["metric"].get("instance", "")
            cores = int(r["value"][1])
            # Map instance to node name
            for name, ip in NODE_IPS.items():
                if ip in instance or (name == "hydra-storage" and "172.17" in instance):
                    cpu_info[name] = {"cores": cores, "threads": cores}  # threads = cores for now
                    break

        return cpu_info

    async def _get_ram_info(self) -> dict[str, dict]:
        """Get RAM info from Prometheus."""
        total_results = await self._query_prometheus("node_memory_MemTotal_bytes")
        avail_results = await self._query_prometheus("node_memory_MemAvailable_bytes")

        ram_info = {}

        for r in total_results:
            instance = r["metric"].get("instance", "")
            total_bytes = float(r["value"][1])

            for name, ip in NODE_IPS.items():
                if ip in instance or (name == "hydra-storage" and "172.17" in instance):
                    ram_info[name] = {"total_gb": total_bytes / (1024**3)}
                    break

        for r in avail_results:
            instance = r["metric"].get("instance", "")
            avail_bytes = float(r["value"][1])

            for name, ip in NODE_IPS.items():
                if ip in instance or (name == "hydra-storage" and "172.17" in instance):
                    if name in ram_info:
                        ram_info[name]["available_gb"] = avail_bytes / (1024**3)
                        ram_info[name]["used_gb"] = ram_info[name]["total_gb"] - ram_info[name]["available_gb"]
                    break

        return ram_info

    async def _get_gpu_info_dcgm(self) -> list[GPUInfo]:
        """Get GPU info from DCGM exporter (hydra-ai)."""
        gpus = []

        # Query DCGM metrics
        used = await self._query_prometheus("DCGM_FI_DEV_FB_USED")
        free = await self._query_prometheus("DCGM_FI_DEV_FB_FREE")
        temp = await self._query_prometheus("DCGM_FI_DEV_GPU_TEMP")
        util = await self._query_prometheus("DCGM_FI_DEV_GPU_UTIL")
        power = await self._query_prometheus("DCGM_FI_DEV_POWER_USAGE")

        # Build GPU list from used memory (has all GPUs)
        gpu_data = {}
        for r in used:
            idx = int(r["metric"].get("gpu", 0))
            name = r["metric"].get("modelName", "Unknown")
            used_mb = float(r["value"][1])
            gpu_data[idx] = {
                "name": name,
                "memory_used_gb": used_mb / 1024,
            }

        for r in free:
            idx = int(r["metric"].get("gpu", 0))
            if idx in gpu_data:
                gpu_data[idx]["memory_free_gb"] = float(r["value"][1]) / 1024
                gpu_data[idx]["memory_total_gb"] = (
                    gpu_data[idx]["memory_used_gb"] + gpu_data[idx]["memory_free_gb"]
                )

        for r in temp:
            idx = int(r["metric"].get("gpu", 0))
            if idx in gpu_data:
                gpu_data[idx]["temperature_c"] = float(r["value"][1])

        for r in util:
            idx = int(r["metric"].get("gpu", 0))
            if idx in gpu_data:
                gpu_data[idx]["utilization_pct"] = float(r["value"][1])

        for r in power:
            idx = int(r["metric"].get("gpu", 0))
            if idx in gpu_data:
                gpu_data[idx]["power_draw_w"] = float(r["value"][1])

        for idx, data in sorted(gpu_data.items()):
            gpus.append(GPUInfo(
                index=idx,
                name=data.get("name", "Unknown"),
                memory_total_gb=data.get("memory_total_gb", 0),
                memory_used_gb=data.get("memory_used_gb", 0),
                memory_free_gb=data.get("memory_free_gb", 0),
                temperature_c=data.get("temperature_c"),
                utilization_pct=data.get("utilization_pct"),
                power_draw_w=data.get("power_draw_w"),
            ))

        return gpus

    async def _get_gpu_info_nvidia_smi(self) -> list[GPUInfo]:
        """Get GPU info from nvidia-smi exporter (hydra-compute)."""
        gpus = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{NVIDIA_EXPORTER}/metrics")
                response.raise_for_status()
                lines = response.text.split("\n")

                gpu_data = {}
                for line in lines:
                    if line.startswith("#") or not line.strip():
                        continue

                    if "nvidia_gpu_" in line:
                        # Parse metric line: metric{labels} value
                        try:
                            metric_part, value = line.rsplit(" ", 1)
                            metric_name = metric_part.split("{")[0]

                            # Extract gpu index and name from labels
                            labels = metric_part.split("{")[1].rstrip("}") if "{" in metric_part else ""
                            gpu_idx = None
                            gpu_name = "Unknown"

                            for label in labels.split(","):
                                if "=" in label:
                                    key, val = label.split("=", 1)
                                    val = val.strip('"')
                                    if key == "gpu":
                                        gpu_idx = int(val)
                                    elif key == "name" or key == "gpu_name":
                                        gpu_name = val.replace("_", " ")

                            if gpu_idx is not None:
                                if gpu_idx not in gpu_data:
                                    gpu_data[gpu_idx] = {"name": gpu_name}

                                if "memory_total" in metric_name:
                                    gpu_data[gpu_idx]["memory_total_gb"] = float(value) / (1024**3)
                                elif "memory_used" in metric_name:
                                    gpu_data[gpu_idx]["memory_used_gb"] = float(value) / (1024**3)
                                elif "temperature" in metric_name:
                                    gpu_data[gpu_idx]["temperature_c"] = float(value)
                                elif "utilization" in metric_name:
                                    gpu_data[gpu_idx]["utilization_pct"] = float(value)
                                elif "power_draw" in metric_name:
                                    gpu_data[gpu_idx]["power_draw_w"] = float(value)
                                elif "power_limit" in metric_name:
                                    gpu_data[gpu_idx]["power_limit_w"] = float(value)
                        except Exception:
                            continue

                for idx, data in sorted(gpu_data.items()):
                    total = data.get("memory_total_gb", 0)
                    used = data.get("memory_used_gb", 0)
                    gpus.append(GPUInfo(
                        index=idx,
                        name=data.get("name", "Unknown"),
                        memory_total_gb=total,
                        memory_used_gb=used,
                        memory_free_gb=total - used,
                        temperature_c=data.get("temperature_c"),
                        utilization_pct=data.get("utilization_pct"),
                        power_draw_w=data.get("power_draw_w"),
                        power_limit_w=data.get("power_limit_w"),
                    ))

            except Exception as e:
                print(f"nvidia-smi exporter query failed: {e}")

        return gpus

    async def get_inventory(self, force_refresh: bool = False) -> ClusterInventory:
        """
        Get complete cluster hardware inventory.

        Results are cached for CACHE_TTL seconds unless force_refresh=True.
        """
        now = time.time()

        # Return cached if valid
        if not force_refresh and self._cache and (now - self._cache_time) < CACHE_TTL:
            self._cache.cached = True
            return self._cache

        # Gather all data concurrently
        cpu_info, ram_info, dcgm_gpus, nvidia_gpus = await asyncio.gather(
            self._get_cpu_info(),
            self._get_ram_info(),
            self._get_gpu_info_dcgm(),
            self._get_gpu_info_nvidia_smi(),
        )

        # Build node info
        nodes = {}

        # hydra-ai
        ai_cpu = cpu_info.get("hydra-ai", {})
        ai_ram = ram_info.get("hydra-ai", {})
        nodes["hydra-ai"] = NodeInfo(
            name="hydra-ai",
            ip=NODE_IPS["hydra-ai"],
            cpu_model="AMD Ryzen Threadripper 7960X",
            cpu_cores=ai_cpu.get("cores", 48) // 2,  # cores = threads/2
            cpu_threads=ai_cpu.get("cores", 48),
            ram_total_gb=ai_ram.get("total_gb", 125),
            ram_used_gb=ai_ram.get("used_gb", 0),
            ram_available_gb=ai_ram.get("available_gb", 0),
            gpus=dcgm_gpus,
            role="Primary Inference (70B models)",
            os="NixOS",
        )

        # hydra-compute
        compute_cpu = cpu_info.get("hydra-compute", {})
        compute_ram = ram_info.get("hydra-compute", {})
        nodes["hydra-compute"] = NodeInfo(
            name="hydra-compute",
            ip=NODE_IPS["hydra-compute"],
            cpu_model="AMD Ryzen 9 9950X",
            cpu_cores=compute_cpu.get("cores", 32) // 2,
            cpu_threads=compute_cpu.get("cores", 32),
            ram_total_gb=compute_ram.get("total_gb", 60),
            ram_used_gb=compute_ram.get("used_gb", 0),
            ram_available_gb=compute_ram.get("available_gb", 0),
            gpus=nvidia_gpus,
            role="Secondary Inference + Image Generation",
            os="NixOS",
        )

        # hydra-storage
        storage_cpu = cpu_info.get("hydra-storage", {})
        storage_ram = ram_info.get("hydra-storage", {})
        nodes["hydra-storage"] = NodeInfo(
            name="hydra-storage",
            ip=NODE_IPS["hydra-storage"],
            cpu_model="AMD EPYC 7663",
            cpu_cores=storage_cpu.get("cores", 112) // 2,
            cpu_threads=storage_cpu.get("cores", 112),
            ram_total_gb=storage_ram.get("total_gb", 251),
            ram_used_gb=storage_ram.get("used_gb", 0),
            ram_available_gb=storage_ram.get("available_gb", 0),
            gpus=[],  # Arc A380 not monitored via nvidia exporters
            role="Storage, Orchestration, 60+ Containers",
            os="Unraid",
        )

        # Calculate totals
        total_cores = sum(n.cpu_cores for n in nodes.values())
        total_threads = sum(n.cpu_threads for n in nodes.values())
        total_ram = sum(n.ram_total_gb for n in nodes.values())

        all_gpus = dcgm_gpus + nvidia_gpus
        total_vram = sum(g.memory_total_gb for g in all_gpus)
        vram_used = sum(g.memory_used_gb for g in all_gpus)
        vram_free = sum(g.memory_free_gb for g in all_gpus)

        inventory = ClusterInventory(
            nodes=nodes,
            total_cpu_cores=total_cores,
            total_cpu_threads=total_threads,
            total_ram_gb=total_ram,
            total_vram_gb=total_vram,
            vram_used_gb=vram_used,
            vram_free_gb=vram_free,
            timestamp=datetime.utcnow(),
            cached=False,
        )

        # Update cache
        self._cache = inventory
        self._cache_time = now

        return inventory

    def to_dict(self, inventory: ClusterInventory) -> dict:
        """Convert inventory to JSON-serializable dict."""
        return {
            "nodes": {
                name: {
                    "name": node.name,
                    "ip": node.ip,
                    "cpu": {
                        "model": node.cpu_model,
                        "cores": node.cpu_cores,
                        "threads": node.cpu_threads,
                    },
                    "ram": {
                        "total_gb": round(node.ram_total_gb, 1),
                        "used_gb": round(node.ram_used_gb, 1),
                        "available_gb": round(node.ram_available_gb, 1),
                        "utilization_pct": round(
                            (node.ram_used_gb / node.ram_total_gb * 100) if node.ram_total_gb > 0 else 0, 1
                        ),
                    },
                    "gpus": [
                        {
                            "index": gpu.index,
                            "name": gpu.name,
                            "memory": {
                                "total_gb": round(gpu.memory_total_gb, 1),
                                "used_gb": round(gpu.memory_used_gb, 1),
                                "free_gb": round(gpu.memory_free_gb, 1),
                                "utilization_pct": round(
                                    (gpu.memory_used_gb / gpu.memory_total_gb * 100) if gpu.memory_total_gb > 0 else 0, 1
                                ),
                            },
                            "temperature_c": gpu.temperature_c,
                            "utilization_pct": gpu.utilization_pct,
                            "power": {
                                "draw_w": gpu.power_draw_w,
                                "limit_w": gpu.power_limit_w,
                            } if gpu.power_draw_w else None,
                        }
                        for gpu in node.gpus
                    ],
                    "role": node.role,
                    "os": node.os,
                }
                for name, node in inventory.nodes.items()
            },
            "totals": {
                "cpu_cores": inventory.total_cpu_cores,
                "cpu_threads": inventory.total_cpu_threads,
                "ram_gb": round(inventory.total_ram_gb, 1),
                "vram_gb": round(inventory.total_vram_gb, 1),
                "vram_used_gb": round(inventory.vram_used_gb, 1),
                "vram_free_gb": round(inventory.vram_free_gb, 1),
                "vram_utilization_pct": round(
                    (inventory.vram_used_gb / inventory.total_vram_gb * 100) if inventory.total_vram_gb > 0 else 0, 1
                ),
            },
            "timestamp": inventory.timestamp.isoformat() + "Z",
            "cached": inventory.cached,
        }


# FastAPI router
def create_hardware_router():
    """Create FastAPI router for hardware discovery endpoints."""
    from fastapi import APIRouter, Query

    router = APIRouter(prefix="/hardware", tags=["hardware"])
    discovery = HardwareDiscovery()

    @router.get("/inventory")
    async def get_hardware_inventory(
        refresh: bool = Query(False, description="Force refresh (bypass cache)")
    ):
        """
        Get complete cluster hardware inventory.

        Returns CPU, RAM, and GPU information for all nodes.
        Results are cached for 60 seconds unless refresh=True.
        """
        inventory = await discovery.get_inventory(force_refresh=refresh)
        return discovery.to_dict(inventory)

    @router.get("/gpus")
    async def get_gpu_status(
        refresh: bool = Query(False, description="Force refresh (bypass cache)")
    ):
        """Get GPU status for all nodes."""
        inventory = await discovery.get_inventory(force_refresh=refresh)

        gpus = []
        for name, node in inventory.nodes.items():
            for gpu in node.gpus:
                gpus.append({
                    "node": name,
                    "index": gpu.index,
                    "name": gpu.name,
                    "vram_total_gb": round(gpu.memory_total_gb, 1),
                    "vram_used_gb": round(gpu.memory_used_gb, 1),
                    "vram_free_gb": round(gpu.memory_free_gb, 1),
                    "temperature_c": gpu.temperature_c,
                    "utilization_pct": gpu.utilization_pct,
                })

        return {
            "gpus": gpus,
            "total_vram_gb": round(inventory.total_vram_gb, 1),
            "vram_used_gb": round(inventory.vram_used_gb, 1),
            "timestamp": inventory.timestamp.isoformat() + "Z",
        }

    @router.get("/summary")
    async def get_hardware_summary():
        """Get a quick summary of cluster hardware."""
        inventory = await discovery.get_inventory()

        return {
            "cluster": {
                "total_cpu_cores": inventory.total_cpu_cores,
                "total_cpu_threads": inventory.total_cpu_threads,
                "total_ram_gb": round(inventory.total_ram_gb, 1),
                "total_vram_gb": round(inventory.total_vram_gb, 1),
                "gpu_count": sum(len(n.gpus) for n in inventory.nodes.values()),
            },
            "nodes": {
                name: {
                    "cpu": f"{node.cpu_model} ({node.cpu_cores}c/{node.cpu_threads}t)",
                    "ram_gb": round(node.ram_total_gb, 1),
                    "gpus": [f"{g.name} ({round(g.memory_total_gb)}GB)" for g in node.gpus],
                    "role": node.role,
                }
                for name, node in inventory.nodes.items()
            },
            "timestamp": inventory.timestamp.isoformat() + "Z",
        }

    return router
