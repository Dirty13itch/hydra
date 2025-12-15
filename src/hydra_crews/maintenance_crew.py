"""
Maintenance Crew - Multi-agent system for cluster maintenance tasks.

Uses CrewAI to coordinate agents that plan, execute, and verify
maintenance operations on the Hydra cluster.
"""

from typing import Optional, Dict, Any, List
from hydra_crews.base import HydraCrewBase, CrewConfig


class MaintenanceCrew(HydraCrewBase):
    """
    Maintenance crew for autonomous cluster upkeep.

    Agents:
    - Planner: Creates maintenance plans and schedules
    - Executor: Runs maintenance tasks safely
    - Validator: Verifies maintenance success

    Example:
        crew = MaintenanceCrew()
        result = crew.run({
            "task": "docker_cleanup",
            "target": "hydra-storage"
        })
    """

    def _default_config(self) -> CrewConfig:
        return CrewConfig(
            name="maintenance_crew",
            description="Cluster maintenance and optimization crew",
            llm_model="ollama/qwen2.5:7b",
            llm_base_url="http://192.168.1.244:4000",
            verbose=True,
            max_iterations=10,
            memory=True
        )

    def _create_agents(self):
        """Create the maintenance crew agents."""
        try:
            from crewai import Agent
        except ImportError:
            print("CrewAI not installed. Run: pip install crewai")
            return

        # Planner - creates safe maintenance plans
        self.planner = Agent(
            role="Maintenance Planner",
            goal="Create safe, efficient maintenance plans with rollback strategies",
            backstory="""You are a senior systems architect who has planned
            thousands of maintenance windows. You always consider impact,
            timing, dependencies, and rollback procedures. You never rush
            and always validate prerequisites before recommending action.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=True,
            tools=self._get_planning_tools()
        )

        # Executor - runs maintenance tasks
        self.executor = Agent(
            role="Maintenance Executor",
            goal="Execute maintenance tasks safely and efficiently",
            backstory="""You are a careful operator who has executed countless
            maintenance procedures. You always verify before acting, check
            status after each step, and stop immediately if something is wrong.
            You document every action for audit purposes.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=False,
            tools=self._get_execution_tools()
        )

        # Validator - verifies success
        self.validator = Agent(
            role="Maintenance Validator",
            goal="Verify maintenance tasks completed successfully",
            backstory="""You are a QA engineer who validates system changes.
            You never assume success - you verify. You check that services
            are healthy, data is intact, and performance is acceptable.
            You document findings thoroughly.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=False,
            tools=self._get_validation_tools()
        )

        self._agents = [self.planner, self.executor, self.validator]

    def _create_tasks(self):
        """Create the maintenance workflow tasks."""
        try:
            from crewai import Task
        except ImportError:
            return

        # Task 1: Planning
        planning_task = Task(
            description="""Create a maintenance plan for: {task}

            Target: {target}

            Include:
            1. Prerequisites check list
            2. Impact assessment (which services affected)
            3. Step-by-step procedure
            4. Verification steps after each action
            5. Rollback procedure if something fails
            6. Estimated duration

            Be conservative - safety over speed.""",
            expected_output="Detailed maintenance plan with rollback",
            agent=self.planner
        )

        # Task 2: Execution
        execution_task = Task(
            description="""Execute the maintenance plan:

            1. Verify all prerequisites are met
            2. Execute each step in order
            3. Check status after each step
            4. Document any deviations
            5. Stop and report if any step fails

            Do NOT proceed if prerequisites fail.
            Document everything for audit trail.""",
            expected_output="Execution log with status of each step",
            agent=self.executor,
            context=[planning_task]
        )

        # Task 3: Validation
        validation_task = Task(
            description="""Validate maintenance success:

            1. Check all affected services are healthy
            2. Verify data integrity where applicable
            3. Compare before/after metrics
            4. Confirm rollback is not needed
            5. Generate completion report

            Be thorough - missed issues cause bigger problems later.""",
            expected_output="Validation report with health confirmation",
            agent=self.validator,
            context=[planning_task, execution_task]
        )

        self._tasks = [planning_task, execution_task, validation_task]

    def _get_planning_tools(self) -> List:
        """Get tools for maintenance planning."""
        tools = []
        try:
            from hydra_tools.maintenance import (
                ServiceDependencyTool,
                MaintenanceWindowTool
            )
            tools.extend([
                ServiceDependencyTool(),
                MaintenanceWindowTool()
            ])
        except ImportError:
            pass
        return tools

    def _get_execution_tools(self) -> List:
        """Get tools for maintenance execution."""
        tools = []
        try:
            from hydra_tools.maintenance import (
                DockerComposeTool,
                SystemctlTool,
                BackupTool
            )
            tools.extend([
                DockerComposeTool(),
                SystemctlTool(),
                BackupTool()
            ])
        except ImportError:
            pass
        return tools

    def _get_validation_tools(self) -> List:
        """Get tools for validation."""
        tools = []
        try:
            from hydra_tools.monitoring import (
                PrometheusQueryTool,
                DockerStatusTool,
                HealthCheckTool
            )
            tools.extend([
                PrometheusQueryTool(base_url="http://192.168.1.244:9090"),
                DockerStatusTool(host="192.168.1.244"),
                HealthCheckTool()
            ])
        except ImportError:
            pass
        return tools

    # Convenience methods for common maintenance tasks

    def docker_cleanup(self, target: str = "hydra-storage") -> str:
        """
        Clean up Docker resources (images, volumes, networks).

        Args:
            target: Node to clean (default: hydra-storage)

        Returns:
            Cleanup report with space reclaimed
        """
        return self.run({
            "task": "docker_cleanup",
            "target": target
        })

    def log_rotation(self, target: str = "all") -> str:
        """
        Rotate and compress logs.

        Args:
            target: Node or "all" for cluster-wide

        Returns:
            Log rotation report
        """
        return self.run({
            "task": "log_rotation",
            "target": target
        })

    def database_maintenance(self, database: str = "postgresql") -> str:
        """
        Run database maintenance (vacuum, analyze, etc).

        Args:
            database: Database to maintain (postgresql, qdrant, redis)

        Returns:
            Database maintenance report
        """
        return self.run({
            "task": f"database_maintenance:{database}",
            "target": "hydra-storage"
        })

    def update_containers(self, stack: str = "hydra-stack") -> str:
        """
        Update Docker containers to latest images.

        Args:
            stack: Docker compose stack to update

        Returns:
            Update report with versions
        """
        return self.run({
            "task": "container_update",
            "target": stack
        })

    def backup_databases(self) -> str:
        """
        Backup all databases to MinIO.

        Returns:
            Backup report with locations
        """
        return self.run({
            "task": "database_backup",
            "target": "all"
        })

    def model_cache_cleanup(self) -> str:
        """
        Clean up unused model cache files.

        Returns:
            Cleanup report with space reclaimed
        """
        return self.run({
            "task": "model_cache_cleanup",
            "target": "hydra-ai"
        })

    def nixos_garbage_collect(self, node: str = "hydra-ai") -> str:
        """
        Run NixOS garbage collection.

        Args:
            node: NixOS node (hydra-ai or hydra-compute)

        Returns:
            Garbage collection report
        """
        return self.run({
            "task": "nix_gc",
            "target": node
        })

    def optimize_qdrant(self) -> str:
        """
        Optimize Qdrant collections.

        Returns:
            Optimization report
        """
        return self.run({
            "task": "qdrant_optimization",
            "target": "hydra-storage"
        })
