"""
Monitoring Crew - Multi-agent system for cluster health monitoring.

Uses CrewAI to coordinate agents that monitor, analyze, and report
on cluster health and performance.
"""

from typing import Optional, Dict, Any, List
from hydra_crews.base import HydraCrewBase, CrewConfig


class MonitoringCrew(HydraCrewBase):
    """
    Monitoring crew for autonomous cluster health surveillance.

    Agents:
    - Health Monitor: Checks service health and metrics
    - Performance Analyst: Analyzes trends and anomalies
    - Alert Manager: Prioritizes issues and generates alerts

    Example:
        crew = MonitoringCrew()
        result = crew.run({
            "check_type": "full",
            "alert_threshold": "warning"
        })
    """

    def _default_config(self) -> CrewConfig:
        return CrewConfig(
            name="monitoring_crew",
            description="Cluster health monitoring and alerting crew",
            llm_model="ollama/qwen2.5:7b",
            llm_base_url="http://192.168.1.244:4000",
            verbose=True,
            max_iterations=10,
            memory=True
        )

    def _create_agents(self):
        """Create the monitoring crew agents."""
        try:
            from crewai import Agent
        except ImportError:
            print("CrewAI not installed. Run: pip install crewai")
            return

        # Health Monitor - checks all services
        self.health_monitor = Agent(
            role="Health Monitor",
            goal="Continuously monitor cluster health and detect issues early",
            backstory="""You are an experienced SRE who has monitored large-scale
            distributed systems. You know the critical health indicators for each
            service type and can quickly identify when something is degrading.
            You check proactively, not just reactively.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=True,
            tools=self._get_monitoring_tools()
        )

        # Performance Analyst - trends and anomalies
        self.performance_analyst = Agent(
            role="Performance Analyst",
            goal="Analyze performance trends and predict potential issues",
            backstory="""You are a performance engineer who understands system
            behavior patterns. You can identify anomalies before they become
            outages, correlate metrics across services, and understand the
            impact of one service's performance on others.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=True
        )

        # Alert Manager - prioritization and notification
        self.alert_manager = Agent(
            role="Alert Manager",
            goal="Prioritize issues and generate actionable alerts",
            backstory="""You are an incident commander who has handled countless
            production issues. You know which alerts are critical vs noise,
            how to write actionable alert messages, and when to escalate.
            You prevent alert fatigue while ensuring nothing critical is missed.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=False
        )

        self._agents = [self.health_monitor, self.performance_analyst, self.alert_manager]

    def _create_tasks(self):
        """Create the monitoring workflow tasks."""
        try:
            from crewai import Task
        except ImportError:
            return

        # Task 1: Health check
        health_task = Task(
            description="""Perform {check_type} health check on the Hydra cluster:

            Check these components:
            1. GPU nodes (hydra-ai, hydra-compute)
               - GPU memory usage and temperature
               - Service availability (TabbyAPI, Ollama, ComfyUI)

            2. Storage node (hydra-storage)
               - Disk space and array health
               - Docker container status
               - Database connectivity

            3. Core services
               - LiteLLM gateway
               - Prometheus/Grafana
               - Redis/PostgreSQL/Qdrant

            Report any issues found with severity level.""",
            expected_output="Health check report with issues and severities",
            agent=self.health_monitor
        )

        # Task 2: Performance analysis
        analysis_task = Task(
            description="""Analyze the health check results:

            1. Compare current metrics to historical baselines
            2. Identify any anomalous patterns
            3. Correlate issues across services
            4. Predict potential upcoming problems
            5. Assess overall cluster health score (0-100)

            Focus on actionable insights, not just data.""",
            expected_output="Performance analysis with predictions",
            agent=self.performance_analyst,
            context=[health_task]
        )

        # Task 3: Alert generation
        alert_task = Task(
            description="""Generate alerts based on findings:

            Alert threshold: {alert_threshold}

            For each issue:
            1. Assign severity (CRITICAL, WARNING, INFO)
            2. Write actionable alert message
            3. Include recommended remediation
            4. Note if manual intervention required

            Format as structured alert list.
            Only include alerts at or above the threshold level.""",
            expected_output="Prioritized alert list with remediation steps",
            agent=self.alert_manager,
            context=[health_task, analysis_task]
        )

        self._tasks = [health_task, analysis_task, alert_task]

    def _get_monitoring_tools(self) -> List:
        """Get tools for health monitoring."""
        tools = []

        try:
            from hydra_tools.monitoring import (
                PrometheusQueryTool,
                DockerStatusTool,
                GPUStatusTool,
                DiskStatusTool
            )
            tools.extend([
                PrometheusQueryTool(base_url="http://192.168.1.244:9090"),
                DockerStatusTool(host="192.168.1.244"),
                GPUStatusTool(),
                DiskStatusTool()
            ])
        except ImportError:
            pass

        return tools

    def quick_check(self) -> str:
        """
        Run a quick health check (critical services only).

        Returns:
            Quick health status report
        """
        return self.run({
            "check_type": "quick",
            "alert_threshold": "critical"
        })

    def full_check(self) -> str:
        """
        Run a comprehensive health check.

        Returns:
            Full health report with all alerts
        """
        return self.run({
            "check_type": "full",
            "alert_threshold": "info"
        })

    def check_node(self, node: str) -> str:
        """
        Check health of a specific node.

        Args:
            node: Node name (hydra-ai, hydra-compute, hydra-storage)

        Returns:
            Node-specific health report
        """
        return self.run({
            "check_type": f"node:{node}",
            "alert_threshold": "warning"
        })

    def check_gpus(self) -> str:
        """
        Check GPU health across all nodes.

        Returns:
            GPU health report
        """
        return self.run({
            "check_type": "gpu",
            "alert_threshold": "warning"
        })

    def check_inference(self) -> str:
        """
        Check inference pipeline health.

        Returns:
            Inference stack health report
        """
        return self.run({
            "check_type": "inference",
            "alert_threshold": "warning"
        })
