"""State definitions for cluster reconciliation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServiceStatus(Enum):
    """Service status enumeration."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MISSING = "missing"


class NodeStatus(Enum):
    """Node status enumeration."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


@dataclass
class ServiceState:
    """State of a single service."""

    name: str
    node: str
    status: ServiceStatus
    port: int | None = None
    image: str | None = None
    version: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "node": self.node,
            "status": self.status.value,
            "port": self.port,
            "image": self.image,
            "version": self.version,
            "config": self.config,
        }


@dataclass
class NodeState:
    """State of a cluster node."""

    name: str
    ip: str
    status: NodeStatus
    os_type: str  # "nixos" or "unraid"
    services: list[ServiceState] = field(default_factory=list)
    gpu_count: int = 0
    gpu_temps: list[float] = field(default_factory=list)
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "ip": self.ip,
            "status": self.status.value,
            "os_type": self.os_type,
            "services": [s.to_dict() for s in self.services],
            "gpu_count": self.gpu_count,
            "gpu_temps": self.gpu_temps,
            "memory_used_gb": self.memory_used_gb,
            "memory_total_gb": self.memory_total_gb,
        }


@dataclass
class ClusterState:
    """Current actual state of the cluster."""

    nodes: list[NodeState] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    def get_service(self, name: str) -> ServiceState | None:
        """Get a service by name."""
        for node in self.nodes:
            for service in node.services:
                if service.name == name:
                    return service
        return None

    def get_node(self, name: str) -> NodeState | None:
        """Get a node by name."""
        for node in self.nodes:
            if node.name == name:
                return node
        return None


@dataclass
class DesiredServiceState:
    """Desired state for a service."""

    name: str
    node: str
    enabled: bool = True
    port: int | None = None
    image: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class DesiredNodeState:
    """Desired state for a node."""

    name: str
    ip: str
    services: list[DesiredServiceState] = field(default_factory=list)


@dataclass
class DesiredState:
    """Desired cluster state from configuration."""

    nodes: list[DesiredNodeState] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> "DesiredState":
        """Load desired state from YAML file."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)

        nodes = []
        for node_data in data.get("nodes", []):
            services = []
            for svc_data in node_data.get("services", []):
                services.append(
                    DesiredServiceState(
                        name=svc_data["name"],
                        node=node_data["name"],
                        enabled=svc_data.get("enabled", True),
                        port=svc_data.get("port"),
                        image=svc_data.get("image"),
                        config=svc_data.get("config", {}),
                        dependencies=svc_data.get("dependencies", []),
                    )
                )
            nodes.append(
                DesiredNodeState(
                    name=node_data["name"],
                    ip=node_data["ip"],
                    services=services,
                )
            )

        return cls(nodes=nodes)

    def get_service(self, name: str) -> DesiredServiceState | None:
        """Get a service by name."""
        for node in self.nodes:
            for service in node.services:
                if service.name == name:
                    return service
        return None


@dataclass
class Drift:
    """A single drift item between desired and actual state."""

    service: str
    node: str
    drift_type: str  # "missing", "extra", "config_mismatch", "status_unhealthy"
    expected: Any = None
    actual: Any = None
    severity: str = "warning"  # "critical", "warning", "info"
    auto_fixable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service": self.service,
            "node": self.node,
            "drift_type": self.drift_type,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class ReconciliationPlan:
    """Plan for reconciling cluster state."""

    drifts: list[Drift] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    def add_drift(self, drift: Drift) -> None:
        """Add a drift item."""
        self.drifts.append(drift)

    def add_action(
        self, action_type: str, target: str, node: str, details: dict[str, Any] | None = None
    ) -> None:
        """Add a reconciliation action."""
        self.actions.append(
            {
                "type": action_type,
                "target": target,
                "node": node,
                "details": details or {},
            }
        )

    @property
    def has_critical_drifts(self) -> bool:
        """Check if there are critical drifts."""
        return any(d.severity == "critical" for d in self.drifts)

    @property
    def auto_fixable_count(self) -> int:
        """Count of auto-fixable drifts."""
        return sum(1 for d in self.drifts if d.auto_fixable)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "drift_count": len(self.drifts),
            "critical_count": sum(1 for d in self.drifts if d.severity == "critical"),
            "auto_fixable_count": self.auto_fixable_count,
            "drifts": [d.to_dict() for d in self.drifts],
            "actions": self.actions,
        }
