"""
Base classes for Hydra CrewAI integration.

Provides common utilities and configuration for all crews.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class CrewConfig:
    """Configuration for a Hydra crew."""
    name: str
    description: str
    llm_model: str = "ollama/qwen2.5:7b"  # Default to local Ollama
    llm_base_url: str = "http://192.168.1.244:4000"  # LiteLLM gateway
    verbose: bool = True
    max_iterations: int = 10
    memory: bool = True


class HydraCrewBase:
    """Base class for all Hydra crews."""

    def __init__(self, config: Optional[CrewConfig] = None):
        self.config = config or self._default_config()
        self._crew = None
        self._agents = []
        self._tasks = []

    def _default_config(self) -> CrewConfig:
        """Override in subclass to provide default config."""
        return CrewConfig(
            name="base_crew",
            description="Base Hydra crew"
        )

    def _create_agents(self):
        """Override in subclass to create agents."""
        raise NotImplementedError

    def _create_tasks(self):
        """Override in subclass to create tasks."""
        raise NotImplementedError

    def _build_crew(self):
        """Build the crew with agents and tasks."""
        try:
            from crewai import Crew, Process

            self._create_agents()
            self._create_tasks()

            self._crew = Crew(
                agents=self._agents,
                tasks=self._tasks,
                verbose=self.config.verbose,
                process=Process.sequential,
                memory=self.config.memory,
            )
            return self._crew
        except ImportError:
            print("CrewAI not installed. Run: pip install crewai")
            return None

    def run(self, inputs: Optional[Dict[str, Any]] = None) -> str:
        """Execute the crew with given inputs."""
        if self._crew is None:
            self._build_crew()

        if self._crew is None:
            return "CrewAI not available"

        return self._crew.kickoff(inputs=inputs or {})

    def get_agent_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all agents in the crew."""
        return {
            agent.role: agent.goal
            for agent in self._agents
        }
