"""
Research Crew - Multi-agent system for autonomous research tasks.

Uses CrewAI to coordinate specialized agents for web research,
synthesis, and report generation.
"""

from typing import Optional, Dict, Any, List
from hydra_crews.base import HydraCrewBase, CrewConfig


class ResearchCrew(HydraCrewBase):
    """
    Research crew for autonomous information gathering and synthesis.

    Agents:
    - Web Researcher: Finds and extracts relevant information
    - Analyst: Synthesizes findings and identifies patterns
    - Reporter: Generates structured reports

    Example:
        crew = ResearchCrew()
        result = crew.run({
            "topic": "ExLlamaV3 tensor parallelism support",
            "depth": "comprehensive"
        })
    """

    def _default_config(self) -> CrewConfig:
        return CrewConfig(
            name="research_crew",
            description="Autonomous research and synthesis crew",
            llm_model="ollama/qwen2.5:7b",
            llm_base_url="http://192.168.1.244:4000",
            verbose=True,
            max_iterations=15,
            memory=True
        )

    def _create_agents(self):
        """Create the research crew agents."""
        try:
            from crewai import Agent
        except ImportError:
            print("CrewAI not installed. Run: pip install crewai")
            return

        # Web Researcher - finds and extracts information
        self.web_researcher = Agent(
            role="Web Researcher",
            goal="Find comprehensive, accurate information on the given topic",
            backstory="""You are an expert web researcher with years of experience
            finding reliable sources. You excel at identifying authoritative sources,
            extracting key facts, and distinguishing between speculation and confirmed
            information. You always cite your sources.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=True,
            tools=self._get_research_tools()
        )

        # Analyst - synthesizes and identifies patterns
        self.analyst = Agent(
            role="Research Analyst",
            goal="Synthesize research findings into coherent insights",
            backstory="""You are a senior research analyst who excels at finding
            patterns in complex information. You can identify gaps in knowledge,
            contradictions between sources, and emerging trends. You provide
            balanced analysis with clear confidence levels.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=True
        )

        # Reporter - generates structured output
        self.reporter = Agent(
            role="Research Reporter",
            goal="Create clear, actionable research reports",
            backstory="""You are a technical writer who transforms complex research
            into accessible reports. You structure information logically, highlight
            key findings, and provide clear recommendations. Your reports are
            concise but comprehensive.""",
            llm=self.config.llm_model,
            verbose=self.config.verbose,
            allow_delegation=False
        )

        self._agents = [self.web_researcher, self.analyst, self.reporter]

    def _create_tasks(self):
        """Create the research workflow tasks."""
        try:
            from crewai import Task
        except ImportError:
            return

        # Task 1: Initial research
        research_task = Task(
            description="""Research the topic: {topic}

            Depth level: {depth}

            Find:
            1. Current state of the technology/topic
            2. Key players and contributors
            3. Recent developments (last 6 months)
            4. Known limitations or challenges
            5. Future roadmap or plans (if available)

            Cite all sources with URLs where possible.""",
            expected_output="Comprehensive research notes with citations",
            agent=self.web_researcher
        )

        # Task 2: Analysis
        analysis_task = Task(
            description="""Analyze the research findings:

            1. Identify key patterns and themes
            2. Note any contradictions between sources
            3. Assess confidence level for each finding
            4. Identify gaps that need further research
            5. Draw preliminary conclusions

            Be objective and note uncertainty where it exists.""",
            expected_output="Analytical summary with confidence assessments",
            agent=self.analyst,
            context=[research_task]
        )

        # Task 3: Report generation
        report_task = Task(
            description="""Generate a structured research report:

            Include:
            - Executive Summary (2-3 sentences)
            - Key Findings (bullet points)
            - Detailed Analysis
            - Recommendations
            - Sources
            - Confidence Level (High/Medium/Low)

            Format in Markdown for easy reading.""",
            expected_output="Markdown-formatted research report",
            agent=self.reporter,
            context=[research_task, analysis_task]
        )

        self._tasks = [research_task, analysis_task, report_task]

    def _get_research_tools(self) -> List:
        """Get tools for web research."""
        tools = []

        try:
            # Try to import SearXNG tool if available
            from crewai_tools import SerperDevTool, ScrapeWebsiteTool
            tools.extend([
                SerperDevTool(),
                ScrapeWebsiteTool()
            ])
        except ImportError:
            pass

        try:
            # Custom Hydra tools
            from hydra_tools.web_tools import SearXNGTool, FirecrawlTool
            tools.extend([
                SearXNGTool(base_url="http://192.168.1.244:8888"),
                FirecrawlTool(base_url="http://192.168.1.244:3005")
            ])
        except ImportError:
            pass

        return tools

    def research(self, topic: str, depth: str = "standard") -> str:
        """
        Convenience method to run research on a topic.

        Args:
            topic: The subject to research
            depth: Research depth - "quick", "standard", or "comprehensive"

        Returns:
            Research report as markdown string
        """
        return self.run({"topic": topic, "depth": depth})

    def research_model(self, model_name: str) -> str:
        """
        Research a specific AI model.

        Args:
            model_name: Name of the model to research

        Returns:
            Research report about the model
        """
        topic = f"""AI Model: {model_name}

        Focus on:
        - Architecture and capabilities
        - Quantization options (EXL2, GGUF, AWQ)
        - VRAM requirements at different quant levels
        - Benchmark results vs similar models
        - Known issues or limitations
        - Recommended use cases"""

        return self.run({"topic": topic, "depth": "comprehensive"})

    def research_technology(self, tech: str) -> str:
        """
        Research a technology or framework.

        Args:
            tech: Technology to research

        Returns:
            Research report
        """
        topic = f"""Technology: {tech}

        Focus on:
        - Current version and release history
        - Key features and capabilities
        - Integration requirements
        - Performance characteristics
        - Community adoption
        - Comparison with alternatives"""

        return self.run({"topic": topic, "depth": "comprehensive"})
