"""Hydra CrewAI Crews - Multi-agent orchestration for autonomous operations."""

__version__ = "1.0.0"

from hydra_crews.research_crew import ResearchCrew
from hydra_crews.monitoring_crew import MonitoringCrew
from hydra_crews.maintenance_crew import MaintenanceCrew

__all__ = ["ResearchCrew", "MonitoringCrew", "MaintenanceCrew"]
