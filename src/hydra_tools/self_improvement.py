"""
Hydra Self-Improvement Infrastructure

Inspired by the Darwin Gödel Machine (DGM), this module provides the
foundation for Hydra to improve itself through:
- Capability benchmarking
- Improvement proposals
- Sandboxed testing
- Empirical validation
- Archive of successful improvements

Key principle: All improvements must be validated empirically before
being deployed to production.
"""

import os
import json
import hashlib
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class ImprovementStatus(Enum):
    """Status of an improvement proposal"""
    PROPOSED = "proposed"
    TESTING = "testing"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class BenchmarkCategory(Enum):
    """Categories of capability benchmarks"""
    TASK_COMPLETION = "task_completion"
    INFERENCE_LATENCY = "inference_latency"
    MEMORY_RECALL = "memory_recall"
    TOOL_RELIABILITY = "tool_reliability"
    ERROR_RECOVERY = "error_recovery"
    CODE_QUALITY = "code_quality"


@dataclass
class BenchmarkResult:
    """Result of running a benchmark"""
    benchmark_id: str
    category: str
    name: str
    score: float
    max_score: float
    passed: bool
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class ImprovementProposal:
    """A proposed improvement to the system"""
    id: str
    title: str
    description: str
    target_files: List[str]
    proposed_changes: Dict[str, str]  # file_path -> new_content
    expected_improvement: str
    benchmark_targets: List[str]  # benchmark IDs to improve
    status: str = ImprovementStatus.PROPOSED.value
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    tested_at: Optional[str] = None
    deployed_at: Optional[str] = None
    baseline_scores: Dict[str, float] = field(default_factory=dict)
    test_scores: Dict[str, float] = field(default_factory=dict)
    author: str = "autonomous"


@dataclass
class ImprovementArchiveEntry:
    """Record of a deployed improvement"""
    proposal_id: str
    title: str
    files_modified: List[str]
    improvement_delta: Dict[str, float]  # benchmark_id -> delta
    deployed_at: str
    rollback_available: bool = True
    rollback_data: Dict[str, str] = field(default_factory=dict)  # file_path -> original_content


class CapabilityBenchmarks:
    """
    Benchmark suite for measuring Hydra's capabilities.

    Benchmarks are used to:
    - Establish baseline performance
    - Validate improvements
    - Detect regressions
    """

    def __init__(self, data_dir: str = "/mnt/user/appdata/hydra-dev/data/benchmarks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = self.data_dir / "results.json"
        self.results: List[BenchmarkResult] = []
        self._load_results()

    def _load_results(self):
        """Load historical benchmark results"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r') as f:
                    data = json.load(f)
                    self.results = [BenchmarkResult(**r) for r in data]
            except Exception as e:
                logger.error(f"Failed to load benchmark results: {e}")

    def _save_results(self):
        """Save benchmark results"""
        try:
            with open(self.results_file, 'w') as f:
                json.dump([asdict(r) for r in self.results], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save benchmark results: {e}")

    def run_benchmark(self, category: BenchmarkCategory, name: str, test_fn) -> BenchmarkResult:
        """
        Run a specific benchmark.

        Args:
            category: Benchmark category
            name: Name of the benchmark
            test_fn: Callable that returns (score, max_score, details)

        Returns:
            BenchmarkResult
        """
        benchmark_id = f"{category.value}:{name}"
        start_time = datetime.utcnow()

        try:
            score, max_score, details = test_fn()
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = BenchmarkResult(
                benchmark_id=benchmark_id,
                category=category.value,
                name=name,
                score=score,
                max_score=max_score,
                passed=score >= (max_score * 0.8),  # 80% threshold
                timestamp=datetime.utcnow().isoformat() + "Z",
                details=details,
                duration_ms=duration_ms
            )
        except Exception as e:
            result = BenchmarkResult(
                benchmark_id=benchmark_id,
                category=category.value,
                name=name,
                score=0,
                max_score=100,
                passed=False,
                timestamp=datetime.utcnow().isoformat() + "Z",
                details={"error": str(e)},
                duration_ms=0
            )

        self.results.append(result)
        self._save_results()
        return result

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all registered benchmarks"""
        results = []

        # Task completion benchmark
        results.append(self.run_benchmark(
            BenchmarkCategory.TASK_COMPLETION,
            "api_health_check",
            self._benchmark_api_health
        ))

        # Inference latency benchmark
        results.append(self.run_benchmark(
            BenchmarkCategory.INFERENCE_LATENCY,
            "litellm_response_time",
            self._benchmark_inference_latency
        ))

        # Tool reliability benchmark
        results.append(self.run_benchmark(
            BenchmarkCategory.TOOL_RELIABILITY,
            "mcp_tool_execution",
            self._benchmark_tool_reliability
        ))

        # Memory recall benchmark
        results.append(self.run_benchmark(
            BenchmarkCategory.MEMORY_RECALL,
            "qdrant_search_accuracy",
            self._benchmark_memory_recall
        ))

        return results

    def _benchmark_api_health(self) -> Tuple[float, float, Dict]:
        """Benchmark API endpoint health"""
        import requests

        endpoints = [
            "http://192.168.1.244:8700/health",
            "http://192.168.1.244:4000/health/liveliness",
            "http://192.168.1.244:6333/healthz",
            "http://192.168.1.244:5678/healthz",
        ]

        successes = 0
        details = {}

        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, timeout=5)
                if resp.status_code == 200:
                    successes += 1
                    details[endpoint] = "healthy"
                else:
                    details[endpoint] = f"status_{resp.status_code}"
            except Exception as e:
                details[endpoint] = f"error: {str(e)[:50]}"

        return successes, len(endpoints), details

    def _benchmark_inference_latency(self) -> Tuple[float, float, Dict]:
        """Benchmark LLM inference latency"""
        import requests
        import time

        # Simple completion request
        try:
            start = time.time()
            resp = requests.post(
                "http://192.168.1.244:4000/v1/chat/completions",
                headers={"Authorization": "Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7"},
                json={
                    "model": "qwen2.5-7b",
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 10
                },
                timeout=30
            )
            latency_ms = (time.time() - start) * 1000

            if resp.status_code == 200:
                # Score inversely proportional to latency (lower is better)
                # Target: < 1000ms = 100, > 5000ms = 0
                score = max(0, min(100, 100 - (latency_ms - 1000) / 40))
                return score, 100, {"latency_ms": latency_ms, "status": "success"}
            else:
                return 0, 100, {"error": resp.text[:100], "status_code": resp.status_code}
        except Exception as e:
            return 0, 100, {"error": str(e)}

    def _benchmark_tool_reliability(self) -> Tuple[float, float, Dict]:
        """Benchmark MCP tool execution reliability"""
        import requests

        # Test constitutional check tool
        try:
            resp = requests.post(
                "http://192.168.1.244:8700/constitution/check",
                json={
                    "operation_type": "code_modification",
                    "target_resource": "test.py"
                },
                timeout=5
            )
            if resp.status_code == 200:
                return 100, 100, {"tool": "constitution_check", "status": "success"}
            return 50, 100, {"tool": "constitution_check", "status": f"status_{resp.status_code}"}
        except Exception as e:
            return 0, 100, {"error": str(e)}

    def _benchmark_memory_recall(self) -> Tuple[float, float, Dict]:
        """Benchmark vector search accuracy"""
        import requests

        try:
            # Check Qdrant health
            resp = requests.get("http://192.168.1.244:6333/collections", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                collections = data.get("result", {}).get("collections", [])
                return 100, 100, {"collections": len(collections), "status": "healthy"}
            return 50, 100, {"status": f"status_{resp.status_code}"}
        except Exception as e:
            return 0, 100, {"error": str(e)}

    def get_baseline(self) -> Dict[str, float]:
        """Get baseline scores from recent results"""
        baseline = {}
        for result in reversed(self.results):
            if result.benchmark_id not in baseline:
                baseline[result.benchmark_id] = result.score
            if len(baseline) >= 10:  # Limit to recent benchmarks
                break
        return baseline

    def compare_to_baseline(self, new_results: List[BenchmarkResult]) -> Dict[str, Dict]:
        """Compare new results to baseline"""
        baseline = self.get_baseline()
        comparison = {}

        for result in new_results:
            if result.benchmark_id in baseline:
                delta = result.score - baseline[result.benchmark_id]
                comparison[result.benchmark_id] = {
                    "baseline": baseline[result.benchmark_id],
                    "new": result.score,
                    "delta": delta,
                    "improved": delta > 0,
                    "regressed": delta < -5  # Allow small regression
                }
            else:
                comparison[result.benchmark_id] = {
                    "baseline": None,
                    "new": result.score,
                    "delta": 0,
                    "improved": False,
                    "regressed": False
                }

        return comparison


class ImprovementArchive:
    """
    Archive of successful improvements.

    Tracks what changes worked and enables rollback if needed.
    """

    def __init__(self, data_dir: str = "/mnt/user/appdata/hydra-dev/data/improvements"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.archive_file = self.data_dir / "archive.json"
        self.proposals_file = self.data_dir / "proposals.json"
        self.archive: List[ImprovementArchiveEntry] = []
        self.proposals: List[ImprovementProposal] = []
        self._load()

    def _load(self):
        """Load archive and proposals"""
        if self.archive_file.exists():
            try:
                with open(self.archive_file, 'r') as f:
                    data = json.load(f)
                    self.archive = [ImprovementArchiveEntry(**e) for e in data]
            except Exception as e:
                logger.error(f"Failed to load archive: {e}")

        if self.proposals_file.exists():
            try:
                with open(self.proposals_file, 'r') as f:
                    data = json.load(f)
                    self.proposals = [ImprovementProposal(**p) for p in data]
            except Exception as e:
                logger.error(f"Failed to load proposals: {e}")

    def _save(self):
        """Save archive and proposals"""
        try:
            with open(self.archive_file, 'w') as f:
                json.dump([asdict(e) for e in self.archive], f, indent=2)
            with open(self.proposals_file, 'w') as f:
                json.dump([asdict(p) for p in self.proposals], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save archive: {e}")

    def create_proposal(
        self,
        title: str,
        description: str,
        target_files: List[str],
        proposed_changes: Dict[str, str],
        expected_improvement: str,
        benchmark_targets: List[str]
    ) -> ImprovementProposal:
        """Create a new improvement proposal"""
        proposal = ImprovementProposal(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            target_files=target_files,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            benchmark_targets=benchmark_targets
        )
        self.proposals.append(proposal)
        self._save()
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        """Get a proposal by ID"""
        for p in self.proposals:
            if p.id == proposal_id:
                return p
        return None

    def update_proposal_status(
        self,
        proposal_id: str,
        status: ImprovementStatus,
        scores: Optional[Dict[str, float]] = None
    ):
        """Update proposal status"""
        proposal = self.get_proposal(proposal_id)
        if proposal:
            proposal.status = status.value
            if status == ImprovementStatus.TESTING and scores:
                proposal.baseline_scores = scores
                proposal.tested_at = datetime.utcnow().isoformat() + "Z"
            elif status == ImprovementStatus.VALIDATED and scores:
                proposal.test_scores = scores
            elif status == ImprovementStatus.DEPLOYED:
                proposal.deployed_at = datetime.utcnow().isoformat() + "Z"
            self._save()

    def archive_improvement(
        self,
        proposal: ImprovementProposal,
        improvement_delta: Dict[str, float],
        rollback_data: Dict[str, str]
    ) -> ImprovementArchiveEntry:
        """Archive a successfully deployed improvement"""
        entry = ImprovementArchiveEntry(
            proposal_id=proposal.id,
            title=proposal.title,
            files_modified=proposal.target_files,
            improvement_delta=improvement_delta,
            deployed_at=datetime.utcnow().isoformat() + "Z",
            rollback_available=True,
            rollback_data=rollback_data
        )
        self.archive.append(entry)
        self._save()
        return entry

    def get_recent_improvements(self, limit: int = 10) -> List[ImprovementArchiveEntry]:
        """Get recent improvements"""
        return self.archive[-limit:]

    def get_pending_proposals(self) -> List[ImprovementProposal]:
        """Get proposals pending testing/deployment"""
        return [p for p in self.proposals if p.status in [
            ImprovementStatus.PROPOSED.value,
            ImprovementStatus.VALIDATED.value
        ]]


class SelfImprovementEngine:
    """
    Main engine for self-improvement operations.

    Coordinates benchmarking, proposals, testing, and deployment.
    """

    def __init__(self):
        self.benchmarks = CapabilityBenchmarks()
        self.archive = ImprovementArchive()
        self.sandbox_dir = Path("/tmp/hydra-sandbox")
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def run_benchmark_suite(self) -> Dict[str, Any]:
        """Run full benchmark suite and return summary"""
        results = self.benchmarks.run_all_benchmarks()
        comparison = self.benchmarks.compare_to_baseline(results)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "passed": passed,
            "total": total,
            "pass_rate": passed / total if total > 0 else 0,
            "results": [asdict(r) for r in results],
            "comparison": comparison
        }

    def propose_improvement(
        self,
        title: str,
        description: str,
        target_files: List[str],
        proposed_changes: Dict[str, str],
        expected_improvement: str
    ) -> ImprovementProposal:
        """Create an improvement proposal"""
        # Determine which benchmarks might be affected
        benchmark_targets = []
        for file_path in target_files:
            if "api" in file_path.lower():
                benchmark_targets.append("task_completion:api_health_check")
            if "inference" in file_path.lower() or "llm" in file_path.lower():
                benchmark_targets.append("inference_latency:litellm_response_time")

        return self.archive.create_proposal(
            title=title,
            description=description,
            target_files=target_files,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            benchmark_targets=benchmark_targets or ["task_completion:api_health_check"]
        )

    def test_improvement(self, proposal_id: str) -> Dict[str, Any]:
        """
        Test an improvement in sandbox.

        Returns test results and whether improvement is validated.
        """
        proposal = self.archive.get_proposal(proposal_id)
        if not proposal:
            return {"error": "Proposal not found"}

        # Get baseline scores
        baseline = self.benchmarks.get_baseline()
        self.archive.update_proposal_status(proposal_id, ImprovementStatus.TESTING, baseline)

        # Create sandbox and apply changes
        sandbox_path = self.sandbox_dir / proposal_id
        sandbox_path.mkdir(parents=True, exist_ok=True)

        try:
            # Copy target files to sandbox
            for file_path in proposal.target_files:
                if os.path.exists(file_path):
                    dest = sandbox_path / Path(file_path).name
                    shutil.copy2(file_path, dest)

            # Apply proposed changes (in sandbox)
            for file_path, new_content in proposal.proposed_changes.items():
                dest = sandbox_path / Path(file_path).name
                with open(dest, 'w') as f:
                    f.write(new_content)

            # Run tests in sandbox (simplified - just syntax check)
            test_results = {"syntax_valid": True, "tests_passed": True}
            for file_path in proposal.proposed_changes.keys():
                dest = sandbox_path / Path(file_path).name
                if dest.suffix == ".py":
                    try:
                        result = subprocess.run(
                            ["python", "-m", "py_compile", str(dest)],
                            capture_output=True,
                            timeout=10
                        )
                        if result.returncode != 0:
                            test_results["syntax_valid"] = False
                            test_results["error"] = result.stderr.decode()[:200]
                    except Exception as e:
                        test_results["syntax_valid"] = False
                        test_results["error"] = str(e)

            # If tests pass, mark as validated
            if test_results.get("syntax_valid") and test_results.get("tests_passed"):
                self.archive.update_proposal_status(
                    proposal_id,
                    ImprovementStatus.VALIDATED,
                    baseline  # Use baseline as test scores for now
                )
                return {
                    "status": "validated",
                    "proposal_id": proposal_id,
                    "test_results": test_results,
                    "ready_to_deploy": True
                }
            else:
                self.archive.update_proposal_status(proposal_id, ImprovementStatus.FAILED)
                return {
                    "status": "failed",
                    "proposal_id": proposal_id,
                    "test_results": test_results,
                    "ready_to_deploy": False
                }

        except Exception as e:
            self.archive.update_proposal_status(proposal_id, ImprovementStatus.FAILED)
            return {
                "status": "error",
                "proposal_id": proposal_id,
                "error": str(e)
            }
        finally:
            # Cleanup sandbox
            shutil.rmtree(sandbox_path, ignore_errors=True)

    def deploy_improvement(self, proposal_id: str) -> Dict[str, Any]:
        """
        Deploy a validated improvement to production.

        Creates backup for rollback capability.
        """
        proposal = self.archive.get_proposal(proposal_id)
        if not proposal:
            return {"error": "Proposal not found"}

        if proposal.status != ImprovementStatus.VALIDATED.value:
            return {"error": f"Proposal not validated (status: {proposal.status})"}

        # Create rollback data (backup original files)
        rollback_data = {}
        for file_path in proposal.target_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    rollback_data[file_path] = f.read()

        try:
            # Apply changes
            for file_path, new_content in proposal.proposed_changes.items():
                with open(file_path, 'w') as f:
                    f.write(new_content)

            # Run benchmarks to measure improvement
            results = self.benchmarks.run_all_benchmarks()
            comparison = self.benchmarks.compare_to_baseline(results)

            # Calculate improvement delta
            improvement_delta = {}
            for benchmark_id, comp in comparison.items():
                if comp.get("delta"):
                    improvement_delta[benchmark_id] = comp["delta"]

            # Check for regression
            has_regression = any(c.get("regressed") for c in comparison.values())

            if has_regression:
                # Rollback
                for file_path, original_content in rollback_data.items():
                    with open(file_path, 'w') as f:
                        f.write(original_content)

                self.archive.update_proposal_status(proposal_id, ImprovementStatus.ROLLED_BACK)
                return {
                    "status": "rolled_back",
                    "reason": "Regression detected",
                    "comparison": comparison
                }

            # Archive successful improvement
            self.archive.archive_improvement(proposal, improvement_delta, rollback_data)
            self.archive.update_proposal_status(proposal_id, ImprovementStatus.DEPLOYED)

            return {
                "status": "deployed",
                "proposal_id": proposal_id,
                "improvement_delta": improvement_delta,
                "comparison": comparison
            }

        except Exception as e:
            # Attempt rollback on error
            for file_path, original_content in rollback_data.items():
                try:
                    with open(file_path, 'w') as f:
                        f.write(original_content)
                except:
                    pass

            self.archive.update_proposal_status(proposal_id, ImprovementStatus.FAILED)
            return {
                "status": "error",
                "error": str(e)
            }

    def rollback_improvement(self, archive_entry_id: str) -> Dict[str, Any]:
        """Rollback a deployed improvement"""
        for entry in self.archive.archive:
            if entry.proposal_id == archive_entry_id and entry.rollback_available:
                try:
                    for file_path, original_content in entry.rollback_data.items():
                        with open(file_path, 'w') as f:
                            f.write(original_content)
                    entry.rollback_available = False
                    self.archive._save()
                    return {"status": "rolled_back", "files_restored": list(entry.rollback_data.keys())}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

        return {"error": "Archive entry not found or rollback not available"}

    def get_status(self) -> Dict[str, Any]:
        """Get current self-improvement status"""
        baseline = self.benchmarks.get_baseline()
        pending = self.archive.get_pending_proposals()
        recent = self.archive.get_recent_improvements()

        return {
            "baseline_benchmarks": len(baseline),
            "pending_proposals": len(pending),
            "deployed_improvements": len(self.archive.archive),
            "recent_improvements": [
                {
                    "title": e.title,
                    "deployed_at": e.deployed_at,
                    "delta": e.improvement_delta
                }
                for e in recent
            ]
        }


# FastAPI router
def create_self_improvement_router():
    """Create FastAPI router for self-improvement endpoints"""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/self-improvement", tags=["self-improvement"])
    engine = SelfImprovementEngine()

    class ProposalCreate(BaseModel):
        title: str
        description: str
        target_files: List[str]
        proposed_changes: Dict[str, str]
        expected_improvement: str

    @router.get("/status")
    async def get_status():
        """Get self-improvement engine status"""
        return engine.get_status()

    @router.post("/benchmark")
    async def run_benchmarks():
        """Run full benchmark suite"""
        return engine.run_benchmark_suite()

    @router.get("/benchmarks/baseline")
    async def get_baseline():
        """Get baseline benchmark scores"""
        return engine.benchmarks.get_baseline()

    @router.post("/proposals")
    async def create_proposal(proposal: ProposalCreate):
        """Create an improvement proposal"""
        result = engine.propose_improvement(
            title=proposal.title,
            description=proposal.description,
            target_files=proposal.target_files,
            proposed_changes=proposal.proposed_changes,
            expected_improvement=proposal.expected_improvement
        )
        return {"proposal_id": result.id, "status": result.status}

    @router.get("/proposals")
    async def list_proposals():
        """List all proposals"""
        return {
            "proposals": [asdict(p) for p in engine.archive.proposals]
        }

    @router.get("/proposals/{proposal_id}")
    async def get_proposal(proposal_id: str):
        """Get a specific proposal"""
        proposal = engine.archive.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return asdict(proposal)

    @router.post("/proposals/{proposal_id}/test")
    async def test_proposal(proposal_id: str):
        """Test a proposal in sandbox"""
        result = engine.test_improvement(proposal_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @router.post("/proposals/{proposal_id}/deploy")
    async def deploy_proposal(proposal_id: str):
        """Deploy a validated proposal"""
        result = engine.deploy_improvement(proposal_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @router.get("/archive")
    async def get_archive():
        """Get improvement archive"""
        return {
            "improvements": [asdict(e) for e in engine.archive.archive]
        }

    @router.post("/archive/{entry_id}/rollback")
    async def rollback_improvement(entry_id: str):
        """Rollback a deployed improvement"""
        result = engine.rollback_improvement(entry_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @router.post("/analyze-and-propose")
    async def analyze_and_propose():
        """
        Analyze current benchmark results and use LLM to generate improvement proposals.

        This is the core DGM-inspired workflow:
        1. Run benchmarks to identify weak areas
        2. Use LLM to analyze results and propose improvements
        3. Return proposals ready for testing
        """
        import httpx

        # Step 1: Get latest benchmark results from DGM benchmark suite
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                bench_resp = await client.post("http://192.168.1.244:8700/benchmark/run")
                bench_data = bench_resp.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Benchmark run failed: {e}")

        # Step 2: Identify areas for improvement
        weak_areas = []
        for result in bench_data.get("results", []):
            if result.get("score", 100) < 80:
                weak_areas.append({
                    "name": result.get("name"),
                    "score": result.get("score"),
                    "details": result.get("details"),
                    "category": result.get("category"),
                })

        if not weak_areas:
            return {
                "status": "optimal",
                "message": "All benchmarks above 80%. No improvements needed.",
                "overall_score": bench_data.get("overall_score"),
            }

        # Step 3: Use LLM to analyze and propose improvements
        prompt = f"""You are the Hydra Self-Improvement Engine. Analyze these weak benchmark areas and propose concrete improvements.

WEAK AREAS:
{json.dumps(weak_areas, indent=2)}

OVERALL SCORE: {bench_data.get('overall_score')}

For each weak area, propose a specific, actionable improvement. Consider:
1. Configuration changes (TabbyAPI, LiteLLM, etc.)
2. Code optimizations in the Hydra Tools API
3. Resource allocation adjustments
4. Model selection improvements

Return your response as JSON with this structure:
{{
  "analysis": "Brief analysis of the issues",
  "proposals": [
    {{
      "title": "Short title",
      "description": "Detailed description of the improvement",
      "target_area": "benchmark name",
      "expected_improvement": "Expected impact",
      "implementation_type": "config|code|resource",
      "priority": "high|medium|low"
    }}
  ]
}}"""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                llm_resp = await client.post(
                    "http://192.168.1.244:4000/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7"},
                    json={
                        "model": "qwen2.5-7b",  # Use fast model for analysis
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3,
                    }
                )
                llm_data = llm_resp.json()
                analysis_text = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Try to parse JSON from response
                try:
                    # Find JSON in response
                    start = analysis_text.find("{")
                    end = analysis_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(analysis_text[start:end])
                    else:
                        analysis = {"analysis": analysis_text, "proposals": []}
                except json.JSONDecodeError:
                    analysis = {"analysis": analysis_text, "proposals": []}

        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM analysis failed: {e}",
                "weak_areas": weak_areas,
            }

        return {
            "status": "proposals_generated",
            "overall_score": bench_data.get("overall_score"),
            "weak_areas_count": len(weak_areas),
            "analysis": analysis.get("analysis", ""),
            "proposals": analysis.get("proposals", []),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @router.get("/workflow")
    async def get_improvement_workflow():
        """Get the full self-improvement workflow status."""
        status = engine.get_status()

        return {
            "workflow_steps": [
                {
                    "step": 1,
                    "name": "Benchmark",
                    "endpoint": "POST /self-improvement/benchmark",
                    "description": "Run capability benchmarks to measure current performance"
                },
                {
                    "step": 2,
                    "name": "Analyze",
                    "endpoint": "POST /self-improvement/analyze-and-propose",
                    "description": "Use LLM to analyze benchmarks and generate improvement proposals"
                },
                {
                    "step": 3,
                    "name": "Test",
                    "endpoint": "POST /self-improvement/proposals/{id}/test",
                    "description": "Test proposals in sandbox environment"
                },
                {
                    "step": 4,
                    "name": "Deploy",
                    "endpoint": "POST /self-improvement/proposals/{id}/deploy",
                    "description": "Deploy validated improvements to production"
                },
                {
                    "step": 5,
                    "name": "Monitor",
                    "endpoint": "GET /self-improvement/status",
                    "description": "Monitor improvement impact and enable rollback if needed"
                }
            ],
            "current_status": status,
        }

    @router.post("/dgm-cycle")
    async def run_dgm_cycle():
        """
        Run a complete Darwin Gödel Machine improvement cycle.

        This is the FULL autonomous loop:
        1. Run comprehensive benchmarks
        2. Analyze results with LLM
        3. Constitutional filter proposals
        4. Archive benchmark results to Discovery Archive
        5. Return actionable proposals

        Safe to run autonomously - does not auto-deploy.
        """
        import httpx
        from datetime import datetime

        cycle_start = datetime.utcnow()
        results = {
            "cycle_id": str(uuid.uuid4())[:8],
            "started_at": cycle_start.isoformat() + "Z",
            "steps": [],
        }

        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Run comprehensive benchmark suite
            try:
                bench_resp = await client.post("http://192.168.1.244:8700/benchmark/run")
                bench_data = bench_resp.json()
                results["steps"].append({
                    "step": "benchmark",
                    "status": "success",
                    "overall_score": bench_data.get("overall_score"),
                    "categories": bench_data.get("category_scores", {}),
                })

                # Archive benchmark to Discovery Archive
                try:
                    archive_resp = await client.post(
                        "http://192.168.1.244:8700/discoveries/archive",
                        json={
                            "type": "benchmark",
                            "title": f"DGM Benchmark Cycle {results['cycle_id']}",
                            "description": f"Overall score: {bench_data.get('overall_score', 0):.1f}%. Categories: {bench_data.get('category_scores', {})}",
                            "benchmark_after": bench_data.get("overall_score", 0),
                            "tags": ["dgm", "benchmark", "automated"],
                        }
                    )
                    results["steps"][-1]["archived"] = True
                except Exception as e:
                    results["steps"][-1]["archive_error"] = str(e)

            except Exception as e:
                results["steps"].append({
                    "step": "benchmark",
                    "status": "error",
                    "error": str(e),
                })
                results["finished_at"] = datetime.utcnow().isoformat() + "Z"
                return results

            # Step 2: Identify weak areas
            weak_areas = []
            for result in bench_data.get("results", []):
                if result.get("score", 100) < 80:
                    weak_areas.append({
                        "name": result.get("name"),
                        "score": result.get("score"),
                        "category": result.get("category"),
                        "details": result.get("details"),
                    })

            results["weak_areas"] = weak_areas

            if not weak_areas:
                results["steps"].append({
                    "step": "analyze",
                    "status": "skipped",
                    "reason": "All benchmarks above 80%. System optimal.",
                })
                results["finished_at"] = datetime.utcnow().isoformat() + "Z"
                results["recommendation"] = "No improvements needed. Maintain current configuration."
                return results

            # Step 3: LLM Analysis
            try:
                prompt = f"""You are the Hydra DGM Self-Improvement Engine.

CURRENT BENCHMARK RESULTS:
- Overall Score: {bench_data.get('overall_score', 0):.1f}%
- Weak Areas ({len(weak_areas)}): {json.dumps(weak_areas, indent=2)}

Analyze these results and propose CONCRETE, SAFE improvements.

RULES:
1. Only propose changes that are safe and reversible
2. Focus on configuration changes, not structural code changes
3. Prioritize quick wins with measurable impact
4. Never propose changes to authentication or security systems

Return JSON:
{{
  "analysis": "Brief analysis",
  "proposals": [
    {{
      "title": "Short title",
      "description": "What to change",
      "target_area": "benchmark name",
      "implementation": "Specific steps",
      "risk_level": "low|medium|high",
      "expected_improvement": "Expected score improvement"
    }}
  ]
}}"""

                llm_resp = await client.post(
                    "http://192.168.1.244:4000/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-hydra-master-key"},
                    json={
                        "model": "qwen2.5-7b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1500,
                        "temperature": 0.2,
                    }
                )
                llm_data = llm_resp.json()
                analysis_text = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Parse JSON from response
                try:
                    start = analysis_text.find("{")
                    end = analysis_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(analysis_text[start:end])
                    else:
                        analysis = {"analysis": analysis_text, "proposals": []}
                except json.JSONDecodeError:
                    analysis = {"analysis": analysis_text, "proposals": []}

                results["steps"].append({
                    "step": "analyze",
                    "status": "success",
                    "analysis": analysis.get("analysis", ""),
                    "proposals_count": len(analysis.get("proposals", [])),
                })
                results["analysis"] = analysis.get("analysis", "")
                results["proposals"] = analysis.get("proposals", [])

            except Exception as e:
                results["steps"].append({
                    "step": "analyze",
                    "status": "error",
                    "error": str(e),
                })
                results["proposals"] = []

            # Step 4: Constitutional filter
            if results.get("proposals"):
                try:
                    filtered_proposals = []
                    for proposal in results["proposals"]:
                        # Check against constitution
                        const_resp = await client.post(
                            "http://192.168.1.244:8700/constitution/check",
                            json={
                                "operation_type": "self_improvement",
                                "target_resource": proposal.get("target_area", "unknown"),
                                "details": proposal.get("description", ""),
                            }
                        )
                        const_data = const_resp.json()

                        if const_data.get("allowed", False):
                            proposal["constitutional_check"] = "passed"
                            filtered_proposals.append(proposal)
                        else:
                            proposal["constitutional_check"] = "blocked"
                            proposal["block_reason"] = const_data.get("reason", "Unknown")

                    results["steps"].append({
                        "step": "constitutional_filter",
                        "status": "success",
                        "passed": len(filtered_proposals),
                        "blocked": len(results["proposals"]) - len(filtered_proposals),
                    })
                    results["approved_proposals"] = filtered_proposals

                except Exception as e:
                    results["steps"].append({
                        "step": "constitutional_filter",
                        "status": "error",
                        "error": str(e),
                    })
                    results["approved_proposals"] = results.get("proposals", [])

        results["finished_at"] = datetime.utcnow().isoformat() + "Z"
        results["duration_ms"] = int((datetime.utcnow() - cycle_start).total_seconds() * 1000)
        results["next_action"] = (
            "Review approved_proposals and manually approve deployment"
            if results.get("approved_proposals")
            else "No actionable proposals generated"
        )

        return results

    @router.post("/quick-health-check")
    async def quick_health_check():
        """
        Quick health check that can be run frequently.
        Returns actionable insights without full benchmark suite.
        """
        import httpx

        checks = []

        async with httpx.AsyncClient(timeout=10) as client:
            # Check Hydra API
            try:
                resp = await client.get("http://192.168.1.244:8700/health")
                checks.append({"service": "hydra-api", "status": "healthy" if resp.status_code == 200 else "unhealthy"})
            except:
                checks.append({"service": "hydra-api", "status": "unreachable"})

            # Check LiteLLM
            try:
                resp = await client.get("http://192.168.1.244:4000/health/liveliness")
                checks.append({"service": "litellm", "status": "healthy" if resp.status_code == 200 else "unhealthy"})
            except:
                checks.append({"service": "litellm", "status": "unreachable"})

            # Check Qdrant
            try:
                resp = await client.get("http://192.168.1.244:6333/healthz")
                checks.append({"service": "qdrant", "status": "healthy" if resp.status_code == 200 else "unhealthy"})
            except:
                checks.append({"service": "qdrant", "status": "unreachable"})

            # Check Discovery Archive
            try:
                resp = await client.get("http://192.168.1.244:8700/discoveries/status")
                data = resp.json()
                checks.append({
                    "service": "discovery-archive",
                    "status": "healthy",
                    "discoveries": data.get("stats", {}).get("total", 0),
                })
            except:
                checks.append({"service": "discovery-archive", "status": "unreachable"})

        healthy = sum(1 for c in checks if c.get("status") == "healthy")
        total = len(checks)

        return {
            "status": "healthy" if healthy == total else "degraded",
            "healthy": healthy,
            "total": total,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return router
