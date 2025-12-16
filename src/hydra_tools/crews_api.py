"""
Crews API Router

Exposes CrewAI multi-agent capabilities via REST endpoints.
Each crew orchestrates specialized AI agents for complex tasks.

Crews:
- ResearchCrew: Autonomous research, synthesis, and reporting
- MonitoringCrew: Cluster health surveillance and alerting
- MaintenanceCrew: Automated maintenance with rollback safety

Endpoints:
- /crews/research/* - Research tasks (topic, model, technology)
- /crews/monitoring/* - Health monitoring and checks
- /crews/maintenance/* - Maintenance operations
- /crews/list - List available crews and capabilities
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field


# Request/Response Models

class ResearchDepth(str, Enum):
    """Research depth levels."""
    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class AlertThreshold(str, Enum):
    """Alert severity thresholds."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CheckType(str, Enum):
    """Health check types."""
    QUICK = "quick"
    FULL = "full"
    GPU = "gpu"
    INFERENCE = "inference"


class ResearchRequest(BaseModel):
    """Research crew request."""
    topic: str = Field(..., description="Topic to research")
    depth: ResearchDepth = Field(ResearchDepth.STANDARD, description="Research depth")


class ModelResearchRequest(BaseModel):
    """AI model research request."""
    model_name: str = Field(..., description="Model name to research (e.g., 'Qwen2.5-72B')")


class TechnologyResearchRequest(BaseModel):
    """Technology research request."""
    technology: str = Field(..., description="Technology/framework to research")


class MonitoringRequest(BaseModel):
    """Monitoring crew request."""
    check_type: CheckType = Field(CheckType.FULL, description="Type of health check")
    alert_threshold: AlertThreshold = Field(AlertThreshold.WARNING, description="Alert threshold")


class NodeCheckRequest(BaseModel):
    """Node-specific check request."""
    node: str = Field(..., description="Node name (hydra-ai, hydra-compute, hydra-storage)")


class MaintenanceRequest(BaseModel):
    """Maintenance crew request."""
    task: str = Field(..., description="Maintenance task type")
    target: str = Field(..., description="Target node or resource")


class DockerCleanupRequest(BaseModel):
    """Docker cleanup request."""
    target: str = Field("hydra-storage", description="Node to clean")


class DatabaseMaintenanceRequest(BaseModel):
    """Database maintenance request."""
    database: str = Field("postgresql", description="Database (postgresql, qdrant, redis)")


class ContainerUpdateRequest(BaseModel):
    """Container update request."""
    stack: str = Field("hydra-stack", description="Docker compose stack")


class NixGCRequest(BaseModel):
    """NixOS garbage collection request."""
    node: str = Field("hydra-ai", description="NixOS node (hydra-ai or hydra-compute)")


class CrewResponse(BaseModel):
    """Standard crew response."""
    crew: str
    task: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: str


class CrewInfo(BaseModel):
    """Crew information."""
    name: str
    description: str
    agents: List[Dict[str, str]]
    available_tasks: List[str]


# Background task storage for async crew runs
_crew_results: Dict[str, CrewResponse] = {}


def _get_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_crews_router() -> APIRouter:
    """Create and configure the crews API router."""
    router = APIRouter(prefix="/crews", tags=["crews"])

    @router.get("/list", response_model=List[CrewInfo])
    async def list_crews():
        """
        List all available crews and their capabilities.

        Returns information about each crew's agents and available tasks.
        """
        crews = [
            CrewInfo(
                name="research",
                description="Autonomous research, synthesis, and reporting crew",
                agents=[
                    {"role": "Web Researcher", "goal": "Find comprehensive, accurate information"},
                    {"role": "Research Analyst", "goal": "Synthesize findings into insights"},
                    {"role": "Research Reporter", "goal": "Create clear, actionable reports"},
                ],
                available_tasks=[
                    "research_topic",
                    "research_model",
                    "research_technology",
                ],
            ),
            CrewInfo(
                name="monitoring",
                description="Cluster health surveillance and alerting crew",
                agents=[
                    {"role": "Health Monitor", "goal": "Monitor cluster health and detect issues"},
                    {"role": "Performance Analyst", "goal": "Analyze trends and predict problems"},
                    {"role": "Alert Manager", "goal": "Prioritize issues and generate alerts"},
                ],
                available_tasks=[
                    "quick_check",
                    "full_check",
                    "check_node",
                    "check_gpus",
                    "check_inference",
                ],
            ),
            CrewInfo(
                name="maintenance",
                description="Automated maintenance with rollback safety",
                agents=[
                    {"role": "Maintenance Planner", "goal": "Create safe maintenance plans"},
                    {"role": "Maintenance Executor", "goal": "Execute tasks safely"},
                    {"role": "Maintenance Validator", "goal": "Verify task success"},
                ],
                available_tasks=[
                    "docker_cleanup",
                    "log_rotation",
                    "database_maintenance",
                    "update_containers",
                    "backup_databases",
                    "model_cache_cleanup",
                    "nixos_garbage_collect",
                    "optimize_qdrant",
                ],
            ),
        ]
        return crews

    @router.get("/status")
    async def crews_status():
        """
        Get current status of crew system.

        Returns availability and configuration info.
        """
        try:
            from hydra_crews import ResearchCrew, MonitoringCrew, MaintenanceCrew
            crews_available = True
        except ImportError:
            crews_available = False

        return {
            "crews_available": crews_available,
            "crewai_installed": crews_available,
            "default_llm": "ollama/qwen2.5:7b",
            "llm_gateway": "http://192.168.1.244:4000",
            "active_runs": len([r for r in _crew_results.values() if r.status == "running"]),
        }

    # ==================== Research Crew Endpoints ====================

    @router.post("/research/topic", response_model=CrewResponse)
    async def research_topic(request: ResearchRequest, background_tasks: BackgroundTasks):
        """
        Research a topic using the Research Crew.

        Orchestrates Web Researcher, Analyst, and Reporter agents to
        gather information, synthesize findings, and generate a report.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import ResearchCrew
            crew = ResearchCrew()
            result = crew.research(request.topic, request.depth.value)

            return CrewResponse(
                crew="research",
                task="research_topic",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed. Run: pip install crewai"
            )
        except Exception as e:
            return CrewResponse(
                crew="research",
                task="research_topic",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/research/model", response_model=CrewResponse)
    async def research_model(request: ModelResearchRequest):
        """
        Research a specific AI model.

        Gathers information about architecture, quantization options,
        VRAM requirements, benchmarks, and recommended use cases.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import ResearchCrew
            crew = ResearchCrew()
            result = crew.research_model(request.model_name)

            return CrewResponse(
                crew="research",
                task="research_model",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="research",
                task="research_model",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/research/technology", response_model=CrewResponse)
    async def research_technology(request: TechnologyResearchRequest):
        """
        Research a technology or framework.

        Investigates version history, features, integration requirements,
        performance characteristics, and alternatives.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import ResearchCrew
            crew = ResearchCrew()
            result = crew.research_technology(request.technology)

            return CrewResponse(
                crew="research",
                task="research_technology",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="research",
                task="research_technology",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    # ==================== Monitoring Crew Endpoints ====================

    @router.post("/monitoring/check", response_model=CrewResponse)
    async def monitoring_check(request: MonitoringRequest):
        """
        Run a health check using the Monitoring Crew.

        Orchestrates Health Monitor, Performance Analyst, and Alert Manager
        to check cluster health, analyze trends, and generate alerts.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.run({
                "check_type": request.check_type.value,
                "alert_threshold": request.alert_threshold.value,
            })

            return CrewResponse(
                crew="monitoring",
                task=f"{request.check_type.value}_check",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task=f"{request.check_type.value}_check",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.get("/monitoring/quick", response_model=CrewResponse)
    async def monitoring_quick_check():
        """
        Run a quick health check (critical services only).

        Faster check focusing on essential services.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.quick_check()

            return CrewResponse(
                crew="monitoring",
                task="quick_check",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task="quick_check",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.get("/monitoring/full", response_model=CrewResponse)
    async def monitoring_full_check():
        """
        Run a comprehensive health check.

        Full check of all cluster components with detailed analysis.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.full_check()

            return CrewResponse(
                crew="monitoring",
                task="full_check",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task="full_check",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/monitoring/node", response_model=CrewResponse)
    async def monitoring_check_node(request: NodeCheckRequest):
        """
        Check health of a specific node.

        Focused check on a single cluster node.
        """
        import time
        start = time.time()

        valid_nodes = ["hydra-ai", "hydra-compute", "hydra-storage"]
        if request.node not in valid_nodes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid node. Must be one of: {valid_nodes}"
            )

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.check_node(request.node)

            return CrewResponse(
                crew="monitoring",
                task=f"check_node:{request.node}",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task=f"check_node:{request.node}",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.get("/monitoring/gpus", response_model=CrewResponse)
    async def monitoring_check_gpus():
        """
        Check GPU health across all nodes.

        Monitors GPU memory, temperature, and utilization.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.check_gpus()

            return CrewResponse(
                crew="monitoring",
                task="check_gpus",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task="check_gpus",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.get("/monitoring/inference", response_model=CrewResponse)
    async def monitoring_check_inference():
        """
        Check inference pipeline health.

        Monitors TabbyAPI, Ollama, LiteLLM gateway status.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MonitoringCrew
            crew = MonitoringCrew()
            result = crew.check_inference()

            return CrewResponse(
                crew="monitoring",
                task="check_inference",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="monitoring",
                task="check_inference",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    # ==================== Maintenance Crew Endpoints ====================

    @router.post("/maintenance/run", response_model=CrewResponse)
    async def maintenance_run(request: MaintenanceRequest):
        """
        Run a custom maintenance task using the Maintenance Crew.

        Orchestrates Planner, Executor, and Validator agents for safe
        maintenance with rollback capability.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.run({
                "task": request.task,
                "target": request.target,
            })

            return CrewResponse(
                crew="maintenance",
                task=request.task,
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task=request.task,
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/docker-cleanup", response_model=CrewResponse)
    async def maintenance_docker_cleanup(request: DockerCleanupRequest):
        """
        Clean up Docker resources (images, volumes, networks).

        Removes unused resources to reclaim disk space.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.docker_cleanup(request.target)

            return CrewResponse(
                crew="maintenance",
                task="docker_cleanup",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="docker_cleanup",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/database", response_model=CrewResponse)
    async def maintenance_database(request: DatabaseMaintenanceRequest):
        """
        Run database maintenance (vacuum, analyze, etc).

        Optimizes database performance and reclaims space.
        """
        import time
        start = time.time()

        valid_databases = ["postgresql", "qdrant", "redis"]
        if request.database not in valid_databases:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid database. Must be one of: {valid_databases}"
            )

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.database_maintenance(request.database)

            return CrewResponse(
                crew="maintenance",
                task=f"database_maintenance:{request.database}",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task=f"database_maintenance:{request.database}",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/backup-databases", response_model=CrewResponse)
    async def maintenance_backup_databases():
        """
        Backup all databases to MinIO.

        Creates snapshots of PostgreSQL, Qdrant, and Redis.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.backup_databases()

            return CrewResponse(
                crew="maintenance",
                task="backup_databases",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="backup_databases",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/update-containers", response_model=CrewResponse)
    async def maintenance_update_containers(request: ContainerUpdateRequest):
        """
        Update Docker containers to latest images.

        Pulls new images and recreates containers with rollback.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.update_containers(request.stack)

            return CrewResponse(
                crew="maintenance",
                task="update_containers",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="update_containers",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/nix-gc", response_model=CrewResponse)
    async def maintenance_nix_gc(request: NixGCRequest):
        """
        Run NixOS garbage collection.

        Removes old generations and reclaims disk space.
        """
        import time
        start = time.time()

        valid_nodes = ["hydra-ai", "hydra-compute"]
        if request.node not in valid_nodes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid NixOS node. Must be one of: {valid_nodes}"
            )

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.nixos_garbage_collect(request.node)

            return CrewResponse(
                crew="maintenance",
                task=f"nix_gc:{request.node}",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task=f"nix_gc:{request.node}",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/optimize-qdrant", response_model=CrewResponse)
    async def maintenance_optimize_qdrant():
        """
        Optimize Qdrant collections.

        Runs optimization on vector indices for better performance.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.optimize_qdrant()

            return CrewResponse(
                crew="maintenance",
                task="optimize_qdrant",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="optimize_qdrant",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/model-cache-cleanup", response_model=CrewResponse)
    async def maintenance_model_cache_cleanup():
        """
        Clean up unused model cache files.

        Removes old model files to reclaim disk space on hydra-ai.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.model_cache_cleanup()

            return CrewResponse(
                crew="maintenance",
                task="model_cache_cleanup",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="model_cache_cleanup",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    @router.post("/maintenance/log-rotation")
    async def maintenance_log_rotation(target: str = "all"):
        """
        Rotate and compress logs.

        Archives old logs to save disk space.
        """
        import time
        start = time.time()

        try:
            from hydra_crews import MaintenanceCrew
            crew = MaintenanceCrew()
            result = crew.log_rotation(target)

            return CrewResponse(
                crew="maintenance",
                task="log_rotation",
                status="completed",
                result=str(result),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="CrewAI not installed"
            )
        except Exception as e:
            return CrewResponse(
                crew="maintenance",
                task="log_rotation",
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
                timestamp=_get_timestamp(),
            )

    return router
