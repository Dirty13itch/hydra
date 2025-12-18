"""
Autonomous Research Pipeline

Extends the research queue with autonomous overnight research capabilities:
- Scheduled research jobs with topics and sources
- Multi-source aggregation (web, arxiv, github, docs)
- Automated report generation
- Integration with agent scheduler for resource management
- Progress tracking and notifications

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import uuid

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

RESEARCH_JOBS = Counter(
    "hydra_research_jobs_total",
    "Total autonomous research jobs",
    ["status"]
)

RESEARCH_REPORTS = Counter(
    "hydra_research_reports_total",
    "Total research reports generated"
)

ACTIVE_RESEARCH_JOBS = Gauge(
    "hydra_active_research_jobs",
    "Currently running research jobs"
)


# =============================================================================
# Research Job Types
# =============================================================================

class ResearchJobType(Enum):
    """Types of autonomous research jobs."""
    TOPIC_EXPLORATION = "topic_exploration"        # Deep dive on a topic
    TECHNOLOGY_WATCH = "technology_watch"          # Monitor tech developments
    COMPETITOR_ANALYSIS = "competitor_analysis"    # Track competing projects
    PAPER_REVIEW = "paper_review"                  # Review academic papers
    GITHUB_SCOUT = "github_scout"                  # Find relevant repos
    DOCUMENTATION_SCAN = "documentation_scan"      # Read docs
    TREND_ANALYSIS = "trend_analysis"              # Analyze trends
    CUSTOM = "custom"                              # Custom research


class JobStatus(Enum):
    """Status of a research job."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Priority for research jobs."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


# =============================================================================
# Research Job Definition
# =============================================================================

@dataclass
class ResearchSource:
    """A source for research."""
    source_type: str  # web_search, arxiv, github, url, rss
    query: Optional[str] = None
    url: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10


@dataclass
class ResearchJob:
    """An autonomous research job."""
    job_id: str
    name: str
    job_type: ResearchJobType
    topic: str
    description: str = ""

    # Sources to research
    sources: List[ResearchSource] = field(default_factory=list)

    # Scheduling
    schedule: Optional[str] = None  # cron expression
    run_once: bool = False
    priority: JobPriority = JobPriority.NORMAL

    # Status tracking
    status: JobStatus = JobStatus.SCHEDULED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0

    # Progress
    progress_percent: int = 0
    current_phase: str = ""
    sources_processed: int = 0
    items_found: int = 0

    # Results
    findings: List[Dict[str, Any]] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    report_path: Optional[str] = None
    error: Optional[str] = None

    # Configuration
    max_duration_minutes: int = 60
    min_relevance_score: float = 0.5
    auto_store_findings: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "name": self.name,
            "job_type": self.job_type.value,
            "topic": self.topic,
            "description": self.description,
            "sources": [
                {
                    "source_type": s.source_type,
                    "query": s.query,
                    "url": s.url,
                    "filters": s.filters,
                    "max_results": s.max_results,
                }
                for s in self.sources
            ],
            "schedule": self.schedule,
            "run_once": self.run_once,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "progress_percent": self.progress_percent,
            "current_phase": self.current_phase,
            "sources_processed": self.sources_processed,
            "items_found": self.items_found,
            "findings_count": len(self.findings),
            "key_insights": self.key_insights,
            "action_items": self.action_items,
            "report_path": self.report_path,
            "error": self.error,
        }


@dataclass
class ResearchReport:
    """Generated research report."""
    report_id: str
    job_id: str
    job_name: str
    topic: str
    generated_at: datetime

    # Content
    executive_summary: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    methodology: str = ""

    # Metadata
    total_sources: int = 0
    total_items_analyzed: int = 0
    duration_minutes: float = 0


# =============================================================================
# Autonomous Research Pipeline
# =============================================================================

class AutonomousResearchPipeline:
    """
    Manages autonomous research jobs for overnight operation.

    Features:
    - Scheduled and on-demand research jobs
    - Multi-source aggregation
    - LLM-powered analysis and synthesis
    - Report generation
    - Integration with research queue
    """

    def __init__(
        self,
        storage_path: str = "/data/research/autonomous",
        llm_url: str = "http://192.168.1.244:4000",
        searxng_url: str = "http://192.168.1.244:8888",
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.llm_url = llm_url
        self.searxng_url = searxng_url

        # Job storage
        self.jobs: Dict[str, ResearchJob] = {}
        self.reports: Dict[str, ResearchReport] = {}

        # Runtime state
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Load existing jobs
        self._load_jobs()

        logger.info("Autonomous research pipeline initialized")

    def _load_jobs(self) -> None:
        """Load jobs from disk."""
        jobs_file = self.storage_path / "jobs.json"
        if jobs_file.exists():
            try:
                data = json.loads(jobs_file.read_text())
                for job_data in data.get("jobs", []):
                    job_data["job_type"] = ResearchJobType(job_data["job_type"])
                    job_data["status"] = JobStatus(job_data["status"])
                    job_data["priority"] = JobPriority(job_data["priority"])
                    job_data["sources"] = [
                        ResearchSource(**s) for s in job_data.get("sources", [])
                    ]
                    if job_data.get("created_at"):
                        job_data["created_at"] = datetime.fromisoformat(job_data["created_at"])
                    if job_data.get("started_at"):
                        job_data["started_at"] = datetime.fromisoformat(job_data["started_at"])
                    if job_data.get("completed_at"):
                        job_data["completed_at"] = datetime.fromisoformat(job_data["completed_at"])
                    if job_data.get("last_run"):
                        job_data["last_run"] = datetime.fromisoformat(job_data["last_run"])

                    # Remove fields not in dataclass
                    job_data.pop("findings_count", None)

                    job = ResearchJob(**job_data)
                    self.jobs[job.job_id] = job

                logger.info(f"Loaded {len(self.jobs)} research jobs")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")

    def _save_jobs(self) -> None:
        """Save jobs to disk."""
        jobs_file = self.storage_path / "jobs.json"
        data = {
            "jobs": [j.to_dict() for j in self.jobs.values()],
            "saved_at": datetime.utcnow().isoformat(),
        }
        jobs_file.write_text(json.dumps(data, indent=2, default=str))

    # =========================================================================
    # Job Management
    # =========================================================================

    def create_job(
        self,
        name: str,
        topic: str,
        job_type: ResearchJobType = ResearchJobType.TOPIC_EXPLORATION,
        description: str = "",
        sources: Optional[List[Dict[str, Any]]] = None,
        schedule: Optional[str] = None,
        run_once: bool = True,
        priority: JobPriority = JobPriority.NORMAL,
        max_duration_minutes: int = 60,
    ) -> ResearchJob:
        """Create a new research job."""
        job_id = str(uuid.uuid4())[:8]

        # Convert source dicts to ResearchSource objects
        source_objs = []
        if sources:
            for s in sources:
                source_objs.append(ResearchSource(**s))
        else:
            # Default sources based on job type
            source_objs = self._get_default_sources(job_type, topic)

        job = ResearchJob(
            job_id=job_id,
            name=name,
            topic=topic,
            job_type=job_type,
            description=description,
            sources=source_objs,
            schedule=schedule,
            run_once=run_once,
            priority=priority,
            max_duration_minutes=max_duration_minutes,
        )

        self.jobs[job_id] = job
        self._save_jobs()

        RESEARCH_JOBS.labels(status="created").inc()
        logger.info(f"Created research job {job_id}: {name}")

        return job

    def _get_default_sources(
        self,
        job_type: ResearchJobType,
        topic: str,
    ) -> List[ResearchSource]:
        """Get default sources for a job type."""
        sources = []

        if job_type == ResearchJobType.TOPIC_EXPLORATION:
            sources = [
                ResearchSource(source_type="web_search", query=topic, max_results=10),
                ResearchSource(source_type="arxiv", query=topic, max_results=5),
                ResearchSource(source_type="github", query=topic, max_results=5),
            ]
        elif job_type == ResearchJobType.PAPER_REVIEW:
            sources = [
                ResearchSource(source_type="arxiv", query=topic, max_results=20),
            ]
        elif job_type == ResearchJobType.GITHUB_SCOUT:
            sources = [
                ResearchSource(source_type="github", query=topic, max_results=20),
            ]
        elif job_type == ResearchJobType.TECHNOLOGY_WATCH:
            sources = [
                ResearchSource(source_type="web_search", query=f"{topic} latest 2025", max_results=10),
                ResearchSource(source_type="github", query=topic, max_results=5, filters={"sort": "updated"}),
            ]
        else:
            sources = [
                ResearchSource(source_type="web_search", query=topic, max_results=10),
            ]

        return sources

    def get_job(self, job_id: str) -> Optional[ResearchJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[ResearchJob]:
        """List all jobs, optionally filtered."""
        jobs = list(self.jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        jobs.sort(key=lambda j: (j.priority.value * -1, j.created_at), reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self.jobs.get(job_id)
        if job and job.status in (JobStatus.SCHEDULED, JobStatus.RUNNING, JobStatus.PAUSED):
            job.status = JobStatus.CANCELLED
            self._save_jobs()
            return True
        return False

    # =========================================================================
    # Research Execution
    # =========================================================================

    async def execute_job(self, job_id: str) -> ResearchJob:
        """Execute a research job."""
        import httpx

        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.progress_percent = 0
        job.findings = []
        job.error = None
        self._save_jobs()

        ACTIVE_RESEARCH_JOBS.inc()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Phase 1: Source Collection
                job.current_phase = "Collecting sources"
                job.progress_percent = 10
                self._save_jobs()

                all_items = []
                for i, source in enumerate(job.sources):
                    items = await self._collect_from_source(client, source, job.topic)
                    all_items.extend(items)
                    job.sources_processed = i + 1
                    job.progress_percent = 10 + int(30 * (i + 1) / len(job.sources))
                    self._save_jobs()

                job.items_found = len(all_items)

                # Phase 2: Analysis
                job.current_phase = "Analyzing content"
                job.progress_percent = 45
                self._save_jobs()

                analyzed = []
                for i, item in enumerate(all_items[:20]):  # Limit to 20 items
                    analysis = await self._analyze_item(client, item, job.topic)
                    if analysis:
                        analyzed.append(analysis)
                    job.progress_percent = 45 + int(35 * (i + 1) / min(len(all_items), 20))
                    self._save_jobs()

                job.findings = analyzed

                # Phase 3: Synthesis
                job.current_phase = "Synthesizing insights"
                job.progress_percent = 85
                self._save_jobs()

                synthesis = await self._synthesize_findings(client, job)
                job.key_insights = synthesis.get("key_insights", [])
                job.action_items = synthesis.get("action_items", [])

                # Phase 4: Report Generation
                job.current_phase = "Generating report"
                job.progress_percent = 95
                self._save_jobs()

                report = await self._generate_report(job)
                job.report_path = report.report_id if report else None

                # Complete
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress_percent = 100
                job.current_phase = "Complete"
                job.run_count += 1
                job.last_run = job.completed_at

                RESEARCH_JOBS.labels(status="completed").inc()
                logger.info(f"Research job {job_id} completed with {len(job.findings)} findings")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            RESEARCH_JOBS.labels(status="failed").inc()
            logger.error(f"Research job {job_id} failed: {e}")

        finally:
            ACTIVE_RESEARCH_JOBS.dec()
            self._save_jobs()

        return job

    async def _collect_from_source(
        self,
        client: "httpx.AsyncClient",
        source: ResearchSource,
        topic: str,
    ) -> List[Dict[str, Any]]:
        """Collect items from a research source."""
        items = []

        try:
            if source.source_type == "web_search":
                items = await self._search_web(client, source.query or topic, source.max_results)
            elif source.source_type == "arxiv":
                items = await self._search_arxiv(client, source.query or topic, source.max_results)
            elif source.source_type == "github":
                items = await self._search_github(client, source.query or topic, source.max_results)
            elif source.source_type == "url":
                if source.url:
                    content = await self._fetch_url(client, source.url)
                    if content:
                        items.append({
                            "title": source.url,
                            "url": source.url,
                            "content": content,
                            "source_type": "url",
                        })
        except Exception as e:
            logger.error(f"Failed to collect from {source.source_type}: {e}")

        return items

    async def _search_web(
        self,
        client: "httpx.AsyncClient",
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search the web using SearXNG."""
        try:
            response = await client.get(
                f"{self.searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                },
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])[:max_results]
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", ""),
                        "source_type": "web",
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"Web search failed: {e}")

        return []

    async def _search_arxiv(
        self,
        client: "httpx.AsyncClient",
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search arXiv for papers."""
        import re

        try:
            response = await client.get(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "lastUpdatedDate",
                    "sortOrder": "descending",
                },
            )

            if response.status_code == 200:
                content = response.text
                items = []

                # Simple XML parsing
                entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
                for entry in entries:
                    title_match = re.search(r'<title>([^<]+)</title>', entry)
                    summary_match = re.search(r'<summary>([^<]+)</summary>', entry, re.DOTALL)
                    id_match = re.search(r'<id>([^<]+)</id>', entry)

                    if title_match:
                        items.append({
                            "title": title_match.group(1).strip(),
                            "url": id_match.group(1).strip() if id_match else "",
                            "snippet": summary_match.group(1).strip()[:500] if summary_match else "",
                            "source_type": "arxiv",
                        })

                return items

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")

        return []

    async def _search_github(
        self,
        client: "httpx.AsyncClient",
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search GitHub for repositories."""
        try:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": query,
                    "sort": "updated",
                    "per_page": max_results,
                },
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            if response.status_code == 200:
                data = response.json()
                repos = data.get("items", [])
                return [
                    {
                        "title": r.get("full_name", ""),
                        "url": r.get("html_url", ""),
                        "snippet": r.get("description", "") or "",
                        "stars": r.get("stargazers_count", 0),
                        "language": r.get("language", ""),
                        "source_type": "github",
                    }
                    for r in repos
                ]
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")

        return []

    async def _fetch_url(
        self,
        client: "httpx.AsyncClient",
        url: str,
    ) -> Optional[str]:
        """Fetch content from a URL."""
        import re

        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                content = response.text
                # Strip HTML
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                content = re.sub(r'<[^>]+>', ' ', content)
                return re.sub(r'\s+', ' ', content).strip()[:10000]
        except Exception as e:
            logger.error(f"URL fetch failed: {e}")

        return None

    async def _analyze_item(
        self,
        client: "httpx.AsyncClient",
        item: Dict[str, Any],
        topic: str,
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single item using LLM."""
        content = item.get("content") or item.get("snippet") or ""
        if not content:
            return item

        prompt = f"""Analyze this content for relevance to: {topic}

Title: {item.get('title', 'Unknown')}
Content: {content[:2000]}

Return JSON with:
{{
  "relevance_score": 0.0-1.0,
  "key_points": ["point 1", "point 2"],
  "technologies": ["tech mentioned"],
  "potential_actions": ["what can be done with this info"]
}}"""

        try:
            response = await client.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {os.environ.get('LITELLM_API_KEY', 'sk-hydra')}"},
            )

            if response.status_code == 200:
                import re
                data = response.json()
                result_text = data["choices"][0]["message"]["content"]
                json_match = re.search(r'\{[\s\S]*\}', result_text)

                if json_match:
                    analysis = json.loads(json_match.group())
                    item.update(analysis)

        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        return item

    async def _synthesize_findings(
        self,
        client: "httpx.AsyncClient",
        job: ResearchJob,
    ) -> Dict[str, Any]:
        """Synthesize findings into insights."""
        findings_summary = "\n".join([
            f"- {f.get('title', 'Item')}: {', '.join(f.get('key_points', []))}"
            for f in job.findings[:15]
        ])

        prompt = f"""Synthesize these research findings about "{job.topic}":

{findings_summary}

Provide:
{{
  "key_insights": ["5-7 major insights for an AI infrastructure team"],
  "action_items": ["3-5 specific actionable recommendations"],
  "emerging_trends": ["notable trends or patterns"],
  "risks": ["potential risks or concerns"]
}}"""

        try:
            response = await client.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.4,
                },
                headers={"Authorization": f"Bearer {os.environ.get('LITELLM_API_KEY', 'sk-hydra')}"},
            )

            if response.status_code == 200:
                import re
                data = response.json()
                result_text = data["choices"][0]["message"]["content"]
                json_match = re.search(r'\{[\s\S]*\}', result_text)

                if json_match:
                    return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")

        return {"key_insights": [], "action_items": []}

    async def _generate_report(self, job: ResearchJob) -> Optional[ResearchReport]:
        """Generate a research report."""
        report_id = f"report-{job.job_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        report = ResearchReport(
            report_id=report_id,
            job_id=job.job_id,
            job_name=job.name,
            topic=job.topic,
            generated_at=datetime.utcnow(),
            findings=job.findings,
            key_insights=job.key_insights,
            action_items=job.action_items,
            sources_used=[f.get("url", "") for f in job.findings if f.get("url")],
            total_sources=job.sources_processed,
            total_items_analyzed=len(job.findings),
            duration_minutes=(
                (job.completed_at - job.started_at).total_seconds() / 60
                if job.completed_at and job.started_at else 0
            ),
        )

        # Generate executive summary
        report.executive_summary = f"""Research Report: {job.name}

Topic: {job.topic}
Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}

Key Insights:
{chr(10).join(['- ' + i for i in job.key_insights[:5]])}

Action Items:
{chr(10).join(['- ' + a for a in job.action_items[:3]])}

This report analyzed {report.total_items_analyzed} items from {report.total_sources} sources.
"""

        # Save report
        report_file = self.storage_path / "reports" / f"{report_id}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps({
            "report_id": report.report_id,
            "job_id": report.job_id,
            "job_name": report.job_name,
            "topic": report.topic,
            "generated_at": report.generated_at.isoformat(),
            "executive_summary": report.executive_summary,
            "key_insights": report.key_insights,
            "action_items": report.action_items,
            "sources_used": report.sources_used,
            "total_sources": report.total_sources,
            "total_items_analyzed": report.total_items_analyzed,
            "duration_minutes": report.duration_minutes,
            "findings": report.findings,
        }, indent=2))

        self.reports[report_id] = report
        RESEARCH_REPORTS.inc()

        logger.info(f"Generated report {report_id} for job {job.job_id}")
        return report

    def get_report(self, report_id: str) -> Optional[ResearchReport]:
        """Get a report by ID."""
        return self.reports.get(report_id)

    def list_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent reports."""
        reports = sorted(
            self.reports.values(),
            key=lambda r: r.generated_at,
            reverse=True,
        )[:limit]

        return [
            {
                "report_id": r.report_id,
                "job_name": r.job_name,
                "topic": r.topic,
                "generated_at": r.generated_at.isoformat(),
                "key_insights_count": len(r.key_insights),
                "action_items_count": len(r.action_items),
            }
            for r in reports
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        jobs = list(self.jobs.values())
        by_status = {}
        for status in JobStatus:
            by_status[status.value] = len([j for j in jobs if j.status == status])

        return {
            "total_jobs": len(jobs),
            "by_status": by_status,
            "total_reports": len(self.reports),
            "running": len([j for j in jobs if j.status == JobStatus.RUNNING]),
        }


# =============================================================================
# Global Instance
# =============================================================================

_pipeline: Optional[AutonomousResearchPipeline] = None


def get_research_pipeline() -> AutonomousResearchPipeline:
    """Get or create the research pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AutonomousResearchPipeline()
    return _pipeline


# =============================================================================
# FastAPI Router
# =============================================================================

def create_autonomous_research_router():
    """Create FastAPI router for autonomous research endpoints."""
    from fastapi import APIRouter, HTTPException, BackgroundTasks
    from pydantic import BaseModel

    router = APIRouter(prefix="/autonomous-research", tags=["autonomous-research"])

    class CreateJobRequest(BaseModel):
        name: str
        topic: str
        job_type: str = "topic_exploration"
        description: str = ""
        sources: Optional[List[Dict[str, Any]]] = None
        schedule: Optional[str] = None
        run_once: bool = True
        priority: int = 1
        max_duration_minutes: int = 60

    @router.get("/status")
    async def pipeline_status():
        """Get autonomous research pipeline status."""
        pipeline = get_research_pipeline()
        return pipeline.get_stats()

    @router.post("/jobs")
    async def create_job(request: CreateJobRequest):
        """Create a new autonomous research job."""
        pipeline = get_research_pipeline()

        try:
            job_type = ResearchJobType(request.job_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid job type: {request.job_type}")

        try:
            priority = JobPriority(request.priority)
        except ValueError:
            priority = JobPriority.NORMAL

        job = pipeline.create_job(
            name=request.name,
            topic=request.topic,
            job_type=job_type,
            description=request.description,
            sources=request.sources,
            schedule=request.schedule,
            run_once=request.run_once,
            priority=priority,
            max_duration_minutes=request.max_duration_minutes,
        )

        return {
            "job_id": job.job_id,
            "name": job.name,
            "status": job.status.value,
            "message": f"Job created. Use /autonomous-research/jobs/{job.job_id}/run to execute.",
        }

    @router.get("/jobs")
    async def list_jobs(status: Optional[str] = None, limit: int = 50):
        """List all research jobs."""
        pipeline = get_research_pipeline()

        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status)
            except ValueError:
                pass

        jobs = pipeline.list_jobs(status=status_filter, limit=limit)
        return {"jobs": [j.to_dict() for j in jobs]}

    @router.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        """Get a specific job."""
        pipeline = get_research_pipeline()
        job = pipeline.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.to_dict()

    @router.post("/jobs/{job_id}/run")
    async def run_job(job_id: str, background_tasks: BackgroundTasks):
        """Execute a research job."""
        pipeline = get_research_pipeline()
        job = pipeline.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == JobStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Job is already running")

        background_tasks.add_task(pipeline.execute_job, job_id)

        return {
            "job_id": job_id,
            "status": "started",
            "message": f"Job execution started. Check /autonomous-research/jobs/{job_id} for progress.",
        }

    @router.post("/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str):
        """Cancel a research job."""
        pipeline = get_research_pipeline()

        if pipeline.cancel_job(job_id):
            return {"status": "cancelled", "job_id": job_id}
        raise HTTPException(status_code=400, detail="Cannot cancel job")

    @router.get("/reports")
    async def list_reports(limit: int = 20):
        """List recent research reports."""
        pipeline = get_research_pipeline()
        return {"reports": pipeline.list_reports(limit=limit)}

    @router.get("/reports/{report_id}")
    async def get_report(report_id: str):
        """Get a specific report."""
        pipeline = get_research_pipeline()
        report = pipeline.get_report(report_id)

        if not report:
            # Try loading from disk
            report_file = pipeline.storage_path / "reports" / f"{report_id}.json"
            if report_file.exists():
                return json.loads(report_file.read_text())
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "report_id": report.report_id,
            "job_name": report.job_name,
            "topic": report.topic,
            "generated_at": report.generated_at.isoformat(),
            "executive_summary": report.executive_summary,
            "key_insights": report.key_insights,
            "action_items": report.action_items,
            "total_sources": report.total_sources,
            "total_items_analyzed": report.total_items_analyzed,
            "duration_minutes": report.duration_minutes,
        }

    @router.get("/job-types")
    async def list_job_types():
        """List available job types."""
        return {
            "job_types": [
                {"type": t.value, "name": t.name.replace("_", " ").title()}
                for t in ResearchJobType
            ]
        }

    return router
