"""
Resource Optimization Tools for Hydra Cluster.

Analyzes GPU utilization patterns, suggests model loading efficiency
improvements, and optimizes resource allocation across the cluster.
"""

import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
import statistics


class ResourceType(Enum):
    """Types of resources to optimize."""
    GPU_MEMORY = "gpu_memory"
    GPU_COMPUTE = "gpu_compute"
    CPU = "cpu"
    RAM = "ram"
    DISK = "disk"
    NETWORK = "network"


class OptimizationPriority(Enum):
    """Priority levels for optimization suggestions."""
    CRITICAL = "critical"  # Immediate action needed
    HIGH = "high"          # Should address soon
    MEDIUM = "medium"      # Efficiency improvement
    LOW = "low"            # Nice to have


@dataclass
class ResourceSnapshot:
    """Point-in-time resource usage snapshot."""
    timestamp: str
    node: str
    gpu_memory_used_mb: list[int]
    gpu_memory_total_mb: list[int]
    gpu_utilization_pct: list[int]
    gpu_power_watts: list[float]
    gpu_temperature_c: list[int]
    cpu_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_used_gb: float
    disk_total_gb: float


@dataclass
class UtilizationPattern:
    """Detected utilization pattern over time."""
    resource: str
    node: str
    avg_utilization: float
    peak_utilization: float
    min_utilization: float
    std_deviation: float
    samples: int
    period_hours: int
    pattern_type: str  # "consistent", "bursty", "idle", "overloaded"


@dataclass
class OptimizationSuggestion:
    """Actionable optimization suggestion."""
    id: str
    priority: str
    resource_type: str
    node: str
    title: str
    description: str
    expected_improvement: str
    action: Optional[str] = None  # Command to execute
    risk_level: str = "low"       # low, medium, high


@dataclass
class ModelLoadingSuggestion:
    """Suggestion for optimizing model loading."""
    model_name: str
    current_location: str
    suggested_location: str
    reason: str
    vram_impact_mb: int
    latency_impact_ms: float


class ResourceOptimizer:
    """
    Resource optimization engine for the Hydra cluster.

    Collects metrics, analyzes patterns, and provides optimization suggestions.
    """

    # Node configurations
    NODES = {
        "hydra-ai": {
            "ip": "192.168.1.250",
            "gpus": [
                {"name": "RTX 5090", "vram_mb": 32768, "power_limit_w": 450},
                {"name": "RTX 4090", "vram_mb": 24576, "power_limit_w": 300},
            ],
            "ram_mb": 131072,  # 128GB
            "role": "primary-inference",
        },
        "hydra-compute": {
            "ip": "192.168.1.203",
            "gpus": [
                {"name": "RTX 5070 Ti", "vram_mb": 16384, "power_limit_w": 250},
                {"name": "RTX 3060", "vram_mb": 12288, "power_limit_w": 170},
            ],
            "ram_mb": 65536,  # 64GB
            "role": "secondary-inference",
        },
        "hydra-storage": {
            "ip": "192.168.1.244",
            "gpus": [
                {"name": "Arc A380", "vram_mb": 6144, "power_limit_w": 75},
            ],
            "ram_mb": 131072,  # 128GB
            "role": "storage-docker",
        },
    }

    # Thresholds for optimization
    THRESHOLDS = {
        "gpu_memory_high": 0.90,      # 90% VRAM usage
        "gpu_memory_low": 0.30,       # 30% VRAM usage (underutilized)
        "gpu_compute_high": 0.95,     # 95% GPU utilization
        "gpu_compute_idle": 0.05,     # 5% GPU utilization
        "gpu_temp_warning": 80,       # 80C temperature
        "gpu_temp_critical": 90,      # 90C temperature
        "cpu_high": 0.85,             # 85% CPU usage
        "ram_high": 0.90,             # 90% RAM usage
        "disk_high": 0.85,            # 85% disk usage
    }

    def __init__(
        self,
        data_dir: str = "/mnt/user/appdata/hydra-stack/data/optimization",
        retention_hours: int = 168,  # 1 week
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots_file = self.data_dir / "resource_snapshots.json"
        self.suggestions_file = self.data_dir / "optimization_suggestions.json"

        self.retention_hours = retention_hours
        self.snapshots: list[ResourceSnapshot] = []
        self.suggestions: list[OptimizationSuggestion] = []

        self._load_data()

    def _load_data(self):
        """Load persisted data."""
        if self.snapshots_file.exists():
            try:
                with open(self.snapshots_file) as f:
                    data = json.load(f)
                    self.snapshots = [ResourceSnapshot(**s) for s in data]
            except (json.JSONDecodeError, TypeError):
                self.snapshots = []

        if self.suggestions_file.exists():
            try:
                with open(self.suggestions_file) as f:
                    data = json.load(f)
                    self.suggestions = [OptimizationSuggestion(**s) for s in data]
            except (json.JSONDecodeError, TypeError):
                self.suggestions = []

    def _save_data(self):
        """Persist data with retention policy."""
        # Apply retention
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        self.snapshots = [
            s for s in self.snapshots
            if datetime.fromisoformat(s.timestamp.rstrip("Z")) >= cutoff
        ]

        with open(self.snapshots_file, "w") as f:
            json.dump([asdict(s) for s in self.snapshots], f, indent=2)

        with open(self.suggestions_file, "w") as f:
            json.dump([asdict(s) for s in self.suggestions], f, indent=2)

    def collect_snapshot(self, node: str) -> Optional[ResourceSnapshot]:
        """
        Collect current resource snapshot from a node.

        In production, this would SSH to the node or query Prometheus.
        """
        if node not in self.NODES:
            return None

        node_config = self.NODES[node]
        now = datetime.utcnow()

        # For demonstration, create realistic placeholder data
        # In production, this queries nvidia-smi, free, df, etc.
        snapshot = ResourceSnapshot(
            timestamp=now.isoformat() + "Z",
            node=node,
            gpu_memory_used_mb=[int(g["vram_mb"] * 0.7) for g in node_config["gpus"]],
            gpu_memory_total_mb=[g["vram_mb"] for g in node_config["gpus"]],
            gpu_utilization_pct=[45] * len(node_config["gpus"]),
            gpu_power_watts=[g["power_limit_w"] * 0.6 for g in node_config["gpus"]],
            gpu_temperature_c=[65] * len(node_config["gpus"]),
            cpu_percent=35.0,
            ram_used_mb=int(node_config["ram_mb"] * 0.5),
            ram_total_mb=node_config["ram_mb"],
            disk_used_gb=500.0,
            disk_total_gb=2000.0,
        )

        self.snapshots.append(snapshot)
        self._save_data()
        return snapshot

    def analyze_patterns(
        self,
        node: str,
        hours: int = 24,
    ) -> list[UtilizationPattern]:
        """Analyze resource utilization patterns over time."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        relevant_snapshots = [
            s for s in self.snapshots
            if s.node == node
            and datetime.fromisoformat(s.timestamp.rstrip("Z")) >= cutoff
        ]

        if len(relevant_snapshots) < 3:
            return []

        patterns = []

        # GPU Memory pattern
        for gpu_idx in range(len(self.NODES[node]["gpus"])):
            usage_pcts = [
                s.gpu_memory_used_mb[gpu_idx] / s.gpu_memory_total_mb[gpu_idx] * 100
                for s in relevant_snapshots
                if gpu_idx < len(s.gpu_memory_used_mb)
            ]

            if usage_pcts:
                avg = statistics.mean(usage_pcts)
                std = statistics.stdev(usage_pcts) if len(usage_pcts) > 1 else 0

                # Determine pattern type
                if avg > 90:
                    pattern_type = "overloaded"
                elif avg < 20:
                    pattern_type = "idle"
                elif std > 20:
                    pattern_type = "bursty"
                else:
                    pattern_type = "consistent"

                patterns.append(UtilizationPattern(
                    resource=f"gpu_{gpu_idx}_memory",
                    node=node,
                    avg_utilization=avg,
                    peak_utilization=max(usage_pcts),
                    min_utilization=min(usage_pcts),
                    std_deviation=std,
                    samples=len(usage_pcts),
                    period_hours=hours,
                    pattern_type=pattern_type,
                ))

        # CPU pattern
        cpu_pcts = [s.cpu_percent for s in relevant_snapshots]
        if cpu_pcts:
            patterns.append(UtilizationPattern(
                resource="cpu",
                node=node,
                avg_utilization=statistics.mean(cpu_pcts),
                peak_utilization=max(cpu_pcts),
                min_utilization=min(cpu_pcts),
                std_deviation=statistics.stdev(cpu_pcts) if len(cpu_pcts) > 1 else 0,
                samples=len(cpu_pcts),
                period_hours=hours,
                pattern_type=self._classify_pattern(cpu_pcts),
            ))

        # RAM pattern
        ram_pcts = [
            s.ram_used_mb / s.ram_total_mb * 100
            for s in relevant_snapshots
        ]
        if ram_pcts:
            patterns.append(UtilizationPattern(
                resource="ram",
                node=node,
                avg_utilization=statistics.mean(ram_pcts),
                peak_utilization=max(ram_pcts),
                min_utilization=min(ram_pcts),
                std_deviation=statistics.stdev(ram_pcts) if len(ram_pcts) > 1 else 0,
                samples=len(ram_pcts),
                period_hours=hours,
                pattern_type=self._classify_pattern(ram_pcts),
            ))

        return patterns

    def _classify_pattern(self, values: list[float]) -> str:
        """Classify utilization pattern."""
        avg = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0

        if avg > 90:
            return "overloaded"
        elif avg < 20:
            return "idle"
        elif std > 20:
            return "bursty"
        else:
            return "consistent"

    def generate_suggestions(self) -> list[OptimizationSuggestion]:
        """Generate optimization suggestions based on current state."""
        suggestions = []
        now = datetime.utcnow()
        suggestion_id = 0

        for node_name, node_config in self.NODES.items():
            patterns = self.analyze_patterns(node_name, hours=24)

            for pattern in patterns:
                # GPU Memory suggestions
                if "gpu" in pattern.resource and "memory" in pattern.resource:
                    gpu_idx = int(pattern.resource.split("_")[1])
                    gpu_name = node_config["gpus"][gpu_idx]["name"]

                    if pattern.pattern_type == "overloaded":
                        suggestions.append(OptimizationSuggestion(
                            id=f"opt-{now.strftime('%Y%m%d')}-{suggestion_id:04d}",
                            priority=OptimizationPriority.HIGH.value,
                            resource_type=ResourceType.GPU_MEMORY.value,
                            node=node_name,
                            title=f"High VRAM usage on {gpu_name}",
                            description=(
                                f"Average VRAM usage is {pattern.avg_utilization:.1f}% "
                                f"with peaks at {pattern.peak_utilization:.1f}%. "
                                "Risk of OOM errors during peak inference."
                            ),
                            expected_improvement="Reduce OOM risk, improve stability",
                            action=self._get_memory_optimization_action(node_name, gpu_idx),
                            risk_level="medium",
                        ))
                        suggestion_id += 1

                    elif pattern.pattern_type == "idle":
                        suggestions.append(OptimizationSuggestion(
                            id=f"opt-{now.strftime('%Y%m%d')}-{suggestion_id:04d}",
                            priority=OptimizationPriority.LOW.value,
                            resource_type=ResourceType.GPU_MEMORY.value,
                            node=node_name,
                            title=f"Underutilized GPU: {gpu_name}",
                            description=(
                                f"Average VRAM usage is only {pattern.avg_utilization:.1f}%. "
                                "Consider loading additional models or offloading work here."
                            ),
                            expected_improvement="Better resource utilization",
                            risk_level="low",
                        ))
                        suggestion_id += 1

                # CPU suggestions
                elif pattern.resource == "cpu":
                    if pattern.pattern_type == "overloaded":
                        suggestions.append(OptimizationSuggestion(
                            id=f"opt-{now.strftime('%Y%m%d')}-{suggestion_id:04d}",
                            priority=OptimizationPriority.MEDIUM.value,
                            resource_type=ResourceType.CPU.value,
                            node=node_name,
                            title="High CPU utilization",
                            description=(
                                f"CPU averaging {pattern.avg_utilization:.1f}% utilization. "
                                "May impact inference tokenization and pre/post processing."
                            ),
                            expected_improvement="Reduced latency, better responsiveness",
                            risk_level="low",
                        ))
                        suggestion_id += 1

                # RAM suggestions
                elif pattern.resource == "ram":
                    if pattern.avg_utilization > 85:
                        suggestions.append(OptimizationSuggestion(
                            id=f"opt-{now.strftime('%Y%m%d')}-{suggestion_id:04d}",
                            priority=OptimizationPriority.HIGH.value,
                            resource_type=ResourceType.RAM.value,
                            node=node_name,
                            title="High RAM usage",
                            description=(
                                f"RAM at {pattern.avg_utilization:.1f}% average. "
                                "System may swap, impacting performance significantly."
                            ),
                            expected_improvement="Prevent swapping, maintain performance",
                            action="Check for memory leaks in containers: docker stats",
                            risk_level="medium",
                        ))
                        suggestion_id += 1

        # Cross-node optimization suggestions
        suggestions.extend(self._generate_cross_node_suggestions(suggestion_id))

        self.suggestions = suggestions
        self._save_data()
        return suggestions

    def _get_memory_optimization_action(self, node: str, gpu_idx: int) -> str:
        """Get specific action for GPU memory optimization."""
        if node == "hydra-ai":
            if gpu_idx == 0:  # RTX 5090
                return (
                    "Consider reducing context length or using smaller quantization. "
                    "Check: nvidia-smi -i 0 --query-compute-apps=pid,used_memory --format=csv"
                )
            else:  # RTX 4090
                return (
                    "Offload secondary model layers to RTX 5090 if using tensor parallelism. "
                    "Or reduce draft model size for speculative decoding."
                )
        elif node == "hydra-compute":
            return (
                "Consider routing complex tasks to hydra-ai. "
                "Use 7B models for simple queries, offload 13B+ tasks."
            )
        return "Review model loading configuration"

    def _generate_cross_node_suggestions(
        self,
        start_id: int,
    ) -> list[OptimizationSuggestion]:
        """Generate suggestions that span multiple nodes."""
        suggestions = []
        now = datetime.utcnow()
        suggestion_id = start_id

        # Check for load imbalance
        ai_patterns = self.analyze_patterns("hydra-ai", hours=24)
        compute_patterns = self.analyze_patterns("hydra-compute", hours=24)

        ai_gpu_avg = next(
            (p.avg_utilization for p in ai_patterns if "gpu_0" in p.resource),
            50.0,
        )
        compute_gpu_avg = next(
            (p.avg_utilization for p in compute_patterns if "gpu_0" in p.resource),
            50.0,
        )

        # Significant imbalance
        if ai_gpu_avg > 80 and compute_gpu_avg < 30:
            suggestions.append(OptimizationSuggestion(
                id=f"opt-{now.strftime('%Y%m%d')}-{suggestion_id:04d}",
                priority=OptimizationPriority.MEDIUM.value,
                resource_type=ResourceType.GPU_COMPUTE.value,
                node="cluster",
                title="GPU load imbalance detected",
                description=(
                    f"hydra-ai GPU at {ai_gpu_avg:.1f}% while "
                    f"hydra-compute at {compute_gpu_avg:.1f}%. "
                    "Consider routing more requests to hydra-compute."
                ),
                expected_improvement="Better latency distribution, reduced queue times",
                action="Update LiteLLM routing weights or RouteLLM thresholds",
                risk_level="low",
            ))
            suggestion_id += 1

        return suggestions

    def suggest_model_placement(self) -> list[ModelLoadingSuggestion]:
        """Suggest optimal model placement across GPUs."""
        suggestions = []

        # Model placement recommendations based on typical usage
        model_placements = [
            {
                "model": "70B EXL2 (4bpw)",
                "size_mb": 35000,
                "optimal": "hydra-ai (RTX 5090 + 4090)",
                "reason": "Requires tensor parallelism across both GPUs",
            },
            {
                "model": "8B EXL2 (6bpw)",
                "size_mb": 8000,
                "optimal": "hydra-compute (RTX 5070 Ti)",
                "reason": "Fast responses for simple queries, frees hydra-ai for complex tasks",
            },
            {
                "model": "Codestral 22B",
                "size_mb": 15000,
                "optimal": "hydra-ai (RTX 5090)",
                "reason": "Code completion benefits from fastest GPU",
            },
            {
                "model": "Embedding model",
                "size_mb": 2000,
                "optimal": "hydra-compute (RTX 3060)",
                "reason": "Embeddings don't need fast inference, conserve primary GPUs",
            },
            {
                "model": "Image generation (SD/Flux)",
                "size_mb": 10000,
                "optimal": "hydra-compute (RTX 5070 Ti)",
                "reason": "Dedicated GPU for image tasks, parallel with LLM inference",
            },
        ]

        for placement in model_placements:
            suggestions.append(ModelLoadingSuggestion(
                model_name=placement["model"],
                current_location="Check TabbyAPI/Ollama config",
                suggested_location=placement["optimal"],
                reason=placement["reason"],
                vram_impact_mb=placement["size_mb"],
                latency_impact_ms=-50,  # Estimated improvement
            ))

        return suggestions

    def get_power_recommendations(self) -> list[dict]:
        """Get power management recommendations."""
        recommendations = []

        # Check recent temperatures
        recent_snapshots = [
            s for s in self.snapshots[-20:]
        ]

        for node_name, node_config in self.NODES.items():
            node_snapshots = [s for s in recent_snapshots if s.node == node_name]

            if not node_snapshots:
                continue

            for gpu_idx, gpu_config in enumerate(node_config["gpus"]):
                temps = [
                    s.gpu_temperature_c[gpu_idx]
                    for s in node_snapshots
                    if gpu_idx < len(s.gpu_temperature_c)
                ]

                if temps:
                    avg_temp = statistics.mean(temps)
                    max_temp = max(temps)

                    if max_temp > self.THRESHOLDS["gpu_temp_critical"]:
                        recommendations.append({
                            "node": node_name,
                            "gpu": gpu_config["name"],
                            "priority": "critical",
                            "issue": f"Critical temperature: {max_temp}C",
                            "action": "Reduce power limit immediately",
                            "command": f"nvidia-smi -i {gpu_idx} -pl {int(gpu_config['power_limit_w'] * 0.7)}",
                        })
                    elif max_temp > self.THRESHOLDS["gpu_temp_warning"]:
                        recommendations.append({
                            "node": node_name,
                            "gpu": gpu_config["name"],
                            "priority": "high",
                            "issue": f"Elevated temperature: {max_temp}C",
                            "action": "Consider reducing power limit",
                            "command": f"nvidia-smi -i {gpu_idx} -pl {int(gpu_config['power_limit_w'] * 0.85)}",
                        })

        return recommendations

    def export_report(self) -> dict:
        """Export comprehensive optimization report."""
        suggestions = self.generate_suggestions()
        model_placements = self.suggest_model_placement()
        power_recs = self.get_power_recommendations()

        # Aggregate patterns
        all_patterns = []
        for node in self.NODES.keys():
            all_patterns.extend(self.analyze_patterns(node, hours=24))

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_suggestions": len(suggestions),
                "critical": sum(1 for s in suggestions if s.priority == "critical"),
                "high": sum(1 for s in suggestions if s.priority == "high"),
                "medium": sum(1 for s in suggestions if s.priority == "medium"),
                "low": sum(1 for s in suggestions if s.priority == "low"),
            },
            "suggestions": [asdict(s) for s in suggestions],
            "model_placement": [asdict(m) for m in model_placements],
            "power_recommendations": power_recs,
            "patterns": [asdict(p) for p in all_patterns],
            "cluster_health": self._calculate_cluster_health(),
        }

    def _calculate_cluster_health(self) -> dict:
        """Calculate overall cluster resource health."""
        health = {
            "score": 100,
            "status": "healthy",
            "issues": [],
        }

        for node in self.NODES.keys():
            patterns = self.analyze_patterns(node, hours=1)

            for pattern in patterns:
                if pattern.pattern_type == "overloaded":
                    health["score"] -= 15
                    health["issues"].append(
                        f"{node}: {pattern.resource} overloaded"
                    )

        if health["score"] < 50:
            health["status"] = "critical"
        elif health["score"] < 75:
            health["status"] = "degraded"

        health["score"] = max(0, health["score"])
        return health


# FastAPI integration
def create_optimization_router():
    """Create FastAPI router for optimization endpoints."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/optimization", tags=["optimization"])
    optimizer = ResourceOptimizer()

    @router.get("/suggestions")
    async def get_suggestions():
        """Get current optimization suggestions."""
        return {"suggestions": [asdict(s) for s in optimizer.generate_suggestions()]}

    @router.get("/patterns/{node}")
    async def get_patterns(node: str, hours: int = 24):
        """Get utilization patterns for a node."""
        patterns = optimizer.analyze_patterns(node, hours)
        return {"node": node, "patterns": [asdict(p) for p in patterns]}

    @router.get("/model-placement")
    async def get_model_placement():
        """Get model placement suggestions."""
        placements = optimizer.suggest_model_placement()
        return {"placements": [asdict(p) for p in placements]}

    @router.get("/power")
    async def get_power_recommendations():
        """Get power management recommendations."""
        return {"recommendations": optimizer.get_power_recommendations()}

    @router.get("/report")
    async def get_report():
        """Get comprehensive optimization report."""
        return optimizer.export_report()

    @router.post("/collect/{node}")
    async def collect_snapshot(node: str):
        """Collect resource snapshot from node."""
        snapshot = optimizer.collect_snapshot(node)
        if snapshot:
            return {"status": "collected", "snapshot": asdict(snapshot)}
        return {"status": "error", "message": f"Unknown node: {node}"}

    @router.get("/health")
    async def get_cluster_health():
        """Get cluster resource health summary."""
        return optimizer._calculate_cluster_health()

    return router
