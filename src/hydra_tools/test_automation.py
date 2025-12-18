"""
Comprehensive Test Automation System

Automated testing for Hydra components:
- API endpoint health checks
- Integration tests
- Performance benchmarks
- Regression detection
- CI/CD integration

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

TEST_RUNS = Counter(
    "hydra_test_runs_total",
    "Total test runs",
    ["suite", "status"]
)

TEST_DURATION = Histogram(
    "hydra_test_duration_seconds",
    "Test execution duration",
    ["suite"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)

TEST_PASS_RATE = Gauge(
    "hydra_test_pass_rate",
    "Test pass rate",
    ["suite"]
)


# =============================================================================
# Test Types
# =============================================================================

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Test Cases
# =============================================================================

@dataclass
class TestCase:
    """A single test case."""
    name: str
    description: str
    endpoint: Optional[str] = None
    method: str = "GET"
    expected_status: int = 200
    payload: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    severity: TestSeverity = TestSeverity.MEDIUM
    tags: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Result of a test execution."""
    test_name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestSuite:
    """A collection of test cases."""
    name: str
    description: str
    tests: List[TestCase] = field(default_factory=list)
    results: List[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0


# =============================================================================
# Test Automation Manager
# =============================================================================

class TestAutomationManager:
    """
    Manages automated testing for Hydra.

    Features:
    - Predefined test suites
    - API health checks
    - Performance benchmarks
    - CI/CD integration
    """

    def __init__(
        self,
        base_url: str = "http://192.168.1.244:8700",
        storage_path: str = "/data/tests",
    ):
        self.base_url = base_url
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Define test suites
        self.suites: Dict[str, TestSuite] = {}
        self._init_default_suites()

        # Test history
        self.history: List[Dict[str, Any]] = []

        logger.info("Test automation manager initialized")

    def _init_default_suites(self):
        """Initialize default test suites."""
        # Health check suite
        self.suites["health"] = TestSuite(
            name="health",
            description="Basic health checks for all services",
            tests=[
                TestCase("api_health", "API health endpoint", "/health", "GET", 200, severity=TestSeverity.CRITICAL),
                TestCase("litellm_health", "LiteLLM proxy health", "http://192.168.1.244:4000/health", "GET", 200),
                TestCase("qdrant_health", "Qdrant health", "http://192.168.1.244:6333/healthz", "GET", 200),
                TestCase("neo4j_health", "Neo4j accessibility", "http://192.168.1.244:7474", "GET", 200),
                TestCase("letta_health", "Letta health", "http://192.168.1.244:8283/health", "GET", 200),
            ],
        )

        # API endpoints suite
        self.suites["api"] = TestSuite(
            name="api",
            description="API endpoint tests",
            tests=[
                TestCase("root_endpoint", "Root endpoint", "/", "GET", 200),
                TestCase("docs_endpoint", "OpenAPI docs", "/docs", "GET", 200),
                TestCase("constitution_status", "Constitution status", "/constitution/status", "GET", 200),
                TestCase("scheduler_status", "Scheduler status", "/scheduler/status", "GET", 200),
                TestCase("graphiti_status", "Graphiti status", "/graphiti/status", "GET", 200),
                TestCase("openhands_status", "OpenHands status", "/openhands/status", "GET", 200),
                TestCase("multi_memory_status", "Multi-memory status", "/multi-memory/status", "GET", 200),
            ],
        )

        # Integration suite
        self.suites["integration"] = TestSuite(
            name="integration",
            description="Integration tests between components",
            tests=[
                TestCase("mcp_registry", "MCP registry tools", "/mcp-registry/tools", "GET", 200),
                TestCase("research_queue_stats", "Research queue stats", "/research/queue/stats", "GET", 200),
                TestCase("skill_library", "Skill library", "/skills/library", "GET", 200),
                TestCase("speculative_status", "Speculative decoding", "/speculative/status", "GET", 200),
            ],
        )

        # Performance suite
        self.suites["performance"] = TestSuite(
            name="performance",
            description="Performance benchmark tests",
            tests=[
                TestCase("health_perf", "Health check performance", "/health", "GET", 200, timeout=1.0, severity=TestSeverity.HIGH),
                TestCase("search_perf", "Search performance", "/graphiti/status", "GET", 200, timeout=5.0),
            ],
        )

    async def run_suite(self, suite_name: str) -> TestSuite:
        """Run a test suite."""
        if suite_name not in self.suites:
            raise ValueError(f"Unknown suite: {suite_name}")

        suite = self.suites[suite_name]
        suite.results = []
        suite.passed = 0
        suite.failed = 0
        suite.skipped = 0

        start_time = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            for test in suite.tests:
                result = await self._run_test(client, test)
                suite.results.append(result)

                if result.status == TestStatus.PASSED:
                    suite.passed += 1
                elif result.status == TestStatus.FAILED:
                    suite.failed += 1
                elif result.status == TestStatus.SKIPPED:
                    suite.skipped += 1

        suite.duration_ms = (time.time() - start_time) * 1000

        # Update metrics
        total = suite.passed + suite.failed
        pass_rate = suite.passed / total if total > 0 else 0
        TEST_PASS_RATE.labels(suite=suite_name).set(pass_rate)
        TEST_RUNS.labels(suite=suite_name, status="completed").inc()
        TEST_DURATION.labels(suite=suite_name).observe(suite.duration_ms / 1000)

        # Store result
        self._save_result(suite)

        return suite

    async def _run_test(self, client: httpx.AsyncClient, test: TestCase) -> TestResult:
        """Run a single test case."""
        start = time.time()

        try:
            url = test.endpoint if test.endpoint.startswith("http") else f"{self.base_url}{test.endpoint}"

            if test.method == "GET":
                response = await client.get(url, timeout=test.timeout)
            elif test.method == "POST":
                response = await client.post(url, json=test.payload or {}, timeout=test.timeout)
            else:
                return TestResult(
                    test_name=test.name,
                    status=TestStatus.SKIPPED,
                    duration_ms=(time.time() - start) * 1000,
                    message=f"Unsupported method: {test.method}",
                )

            duration_ms = (time.time() - start) * 1000

            if response.status_code == test.expected_status:
                return TestResult(
                    test_name=test.name,
                    status=TestStatus.PASSED,
                    duration_ms=duration_ms,
                    response_code=response.status_code,
                    message="OK",
                )
            else:
                return TestResult(
                    test_name=test.name,
                    status=TestStatus.FAILED,
                    duration_ms=duration_ms,
                    response_code=response.status_code,
                    message=f"Expected {test.expected_status}, got {response.status_code}",
                    response_body=response.text[:500],
                )

        except httpx.TimeoutException:
            return TestResult(
                test_name=test.name,
                status=TestStatus.FAILED,
                duration_ms=(time.time() - start) * 1000,
                message=f"Timeout after {test.timeout}s",
            )
        except Exception as e:
            return TestResult(
                test_name=test.name,
                status=TestStatus.ERROR,
                duration_ms=(time.time() - start) * 1000,
                message=str(e),
            )

    async def run_all_suites(self) -> Dict[str, TestSuite]:
        """Run all test suites."""
        results = {}
        for suite_name in self.suites:
            results[suite_name] = await self.run_suite(suite_name)
        return results

    def _save_result(self, suite: TestSuite):
        """Save test result to disk."""
        result_file = self.storage_path / f"{suite.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "suite": suite.name,
            "executed_at": datetime.utcnow().isoformat(),
            "passed": suite.passed,
            "failed": suite.failed,
            "skipped": suite.skipped,
            "duration_ms": suite.duration_ms,
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "response_code": r.response_code,
                }
                for r in suite.results
            ],
        }

        result_file.write_text(json.dumps(data, indent=2))

        # Keep history
        self.history.append({
            "suite": suite.name,
            "timestamp": datetime.utcnow().isoformat(),
            "passed": suite.passed,
            "failed": suite.failed,
            "pass_rate": suite.passed / (suite.passed + suite.failed) if (suite.passed + suite.failed) > 0 else 1,
        })
        self.history = self.history[-100:]  # Keep last 100

    def get_stats(self) -> Dict[str, Any]:
        """Get test automation statistics."""
        return {
            "suites": list(self.suites.keys()),
            "total_tests": sum(len(s.tests) for s in self.suites.values()),
            "recent_runs": len(self.history),
            "last_results": {
                name: {
                    "passed": suite.passed,
                    "failed": suite.failed,
                    "duration_ms": suite.duration_ms,
                }
                for name, suite in self.suites.items()
                if suite.results
            },
        }


# =============================================================================
# Global Instance
# =============================================================================

_test_manager: Optional[TestAutomationManager] = None


def get_test_manager() -> TestAutomationManager:
    """Get or create test manager."""
    global _test_manager
    if _test_manager is None:
        _test_manager = TestAutomationManager()
    return _test_manager


# =============================================================================
# FastAPI Router
# =============================================================================

def create_test_automation_router():
    """Create FastAPI router for test automation endpoints."""
    from fastapi import APIRouter, BackgroundTasks

    router = APIRouter(prefix="/tests", tags=["test-automation"])

    @router.get("/status")
    async def test_status():
        """Get test automation status."""
        manager = get_test_manager()
        return manager.get_stats()

    @router.get("/suites")
    async def list_suites():
        """List available test suites."""
        manager = get_test_manager()
        return {
            "suites": [
                {
                    "name": s.name,
                    "description": s.description,
                    "test_count": len(s.tests),
                }
                for s in manager.suites.values()
            ]
        }

    @router.post("/suites/{suite_name}/run")
    async def run_suite(suite_name: str):
        """Run a specific test suite."""
        manager = get_test_manager()
        suite = await manager.run_suite(suite_name)

        return {
            "suite": suite.name,
            "passed": suite.passed,
            "failed": suite.failed,
            "skipped": suite.skipped,
            "duration_ms": round(suite.duration_ms, 2),
            "results": [
                {
                    "test": r.test_name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 2),
                    "message": r.message,
                }
                for r in suite.results
            ],
        }

    @router.post("/run-all")
    async def run_all(background_tasks: BackgroundTasks):
        """Run all test suites."""
        manager = get_test_manager()
        results = await manager.run_all_suites()

        return {
            "suites_run": len(results),
            "summary": {
                name: {
                    "passed": suite.passed,
                    "failed": suite.failed,
                    "pass_rate": f"{suite.passed / (suite.passed + suite.failed) * 100:.1f}%" if (suite.passed + suite.failed) > 0 else "N/A",
                }
                for name, suite in results.items()
            },
        }

    @router.get("/history")
    async def get_history(limit: int = 20):
        """Get test run history."""
        manager = get_test_manager()
        return {"history": manager.history[-limit:]}

    return router
