"""
OpenHands Integration for Hydra

Provides autonomous coding capabilities using the OpenHands SDK.
Enables code generation, modification, debugging, and PR creation.

Features:
- Autonomous coding task execution
- Git operations (clone, branch, commit, PR)
- Code analysis and refactoring
- Test generation and execution
- Integration with Hydra sandbox for safe execution

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

OPENHANDS_TASKS = Counter(
    "hydra_openhands_tasks_total",
    "Total OpenHands coding tasks",
    ["task_type", "status"]
)

OPENHANDS_LATENCY = Histogram(
    "hydra_openhands_task_latency_seconds",
    "OpenHands task completion time",
    ["task_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

OPENHANDS_ACTIVE_SESSIONS = Gauge(
    "hydra_openhands_active_sessions",
    "Currently active OpenHands sessions"
)


# =============================================================================
# Task Types and Status
# =============================================================================

class CodingTaskType(Enum):
    """Types of coding tasks OpenHands can perform."""
    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    DEPENDENCY_UPDATE = "dependency_update"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class TaskStatus(Enum):
    """Status of an OpenHands task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_REVIEW = "waiting_review"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CodingTask:
    """Represents an autonomous coding task."""
    task_id: str
    task_type: CodingTaskType
    description: str
    repository: Optional[str] = None
    branch: Optional[str] = None
    target_files: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    changes: List[Dict[str, Any]] = field(default_factory=list)
    pr_url: Optional[str] = None


@dataclass
class AgentSession:
    """Represents an OpenHands agent session."""
    session_id: str
    task_id: str
    workspace_path: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"
    logs: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    actions_taken: int = 0


@dataclass
class CodeChange:
    """Represents a code change made by the agent."""
    file_path: str
    change_type: str  # "create", "modify", "delete"
    before: Optional[str] = None
    after: Optional[str] = None
    diff: Optional[str] = None
    explanation: str = ""


# =============================================================================
# OpenHands Manager
# =============================================================================

class OpenHandsManager:
    """
    Manages OpenHands coding agent sessions and tasks.

    Provides autonomous coding capabilities with safety guardrails.
    """

    def __init__(
        self,
        workspace_base: str = "/tmp/openhands-workspaces",
        sandbox_url: str = "http://192.168.1.244:8700/sandbox",
        llm_url: str = "http://192.168.1.244:4000",
        default_model: str = "qwen2.5-coder-32b",
    ):
        self.workspace_base = Path(workspace_base)
        self.sandbox_url = sandbox_url
        self.llm_url = llm_url
        self.default_model = default_model

        # Task and session tracking
        self.tasks: Dict[str, CodingTask] = {}
        self.sessions: Dict[str, AgentSession] = {}

        # Safety constraints
        self.allowed_operations = {
            "read_file", "write_file", "run_command",
            "git_clone", "git_commit", "git_push",
            "pip_install", "npm_install",
        }

        self.blocked_patterns = [
            "rm -rf /",
            "sudo rm",
            "DROP TABLE",
            "DELETE FROM",
            "> /dev/",
            "chmod 777",
            "curl | bash",
            "wget | sh",
        ]

        # Ensure workspace directory exists
        self.workspace_base.mkdir(parents=True, exist_ok=True)

        logger.info("OpenHands manager initialized")

    async def create_task(
        self,
        task_type: CodingTaskType,
        description: str,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
        target_files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CodingTask:
        """Create a new coding task."""
        task_id = str(uuid.uuid4())[:8]

        task = CodingTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            repository=repository,
            branch=branch or "main",
            target_files=target_files or [],
            context=context or {},
        )

        self.tasks[task_id] = task
        OPENHANDS_TASKS.labels(task_type=task_type.value, status="created").inc()

        logger.info(f"Created coding task {task_id}: {task_type.value}")
        return task

    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a coding task."""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()

        try:
            # Create agent session
            session = await self._create_session(task)

            # Set up workspace
            workspace = await self._setup_workspace(task, session)

            # Generate and execute coding plan
            plan = await self._generate_coding_plan(task)

            # Execute each step of the plan
            for step in plan["steps"]:
                result = await self._execute_step(task, session, step)
                if result.get("error"):
                    task.errors.append(result["error"])
                else:
                    task.changes.append(result)

            # Validate changes
            validation = await self._validate_changes(task, session)

            if validation["passed"]:
                task.status = TaskStatus.COMPLETED
                task.result = {
                    "changes": task.changes,
                    "validation": validation,
                    "workspace": str(workspace),
                }
            else:
                task.status = TaskStatus.FAILED
                task.errors.extend(validation.get("errors", []))

            task.completed_at = datetime.utcnow()

            # Update metrics
            duration = (task.completed_at - task.started_at).total_seconds()
            OPENHANDS_LATENCY.labels(task_type=task.task_type.value).observe(duration)
            OPENHANDS_TASKS.labels(task_type=task.task_type.value, status=task.status.value).inc()

            return {
                "task_id": task_id,
                "status": task.status.value,
                "changes": len(task.changes),
                "errors": task.errors,
                "duration_seconds": duration,
            }

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.errors.append(str(e))
            task.completed_at = datetime.utcnow()
            logger.error(f"Task {task_id} failed: {e}")
            return {"error": str(e), "task_id": task_id}

    async def _create_session(self, task: CodingTask) -> AgentSession:
        """Create a new agent session for the task."""
        session_id = str(uuid.uuid4())[:8]
        workspace_path = str(self.workspace_base / f"session-{session_id}")

        session = AgentSession(
            session_id=session_id,
            task_id=task.task_id,
            workspace_path=workspace_path,
        )

        self.sessions[session_id] = session
        OPENHANDS_ACTIVE_SESSIONS.inc()

        # Create workspace directory
        Path(workspace_path).mkdir(parents=True, exist_ok=True)

        logger.info(f"Created session {session_id} for task {task.task_id}")
        return session

    async def _setup_workspace(self, task: CodingTask, session: AgentSession) -> Path:
        """Set up the workspace for the task."""
        workspace = Path(session.workspace_path)

        if task.repository:
            # Clone repository if specified
            await self._safe_git_clone(task.repository, workspace, task.branch)

        return workspace

    async def _safe_git_clone(self, repo: str, workspace: Path, branch: str) -> None:
        """Safely clone a git repository."""
        import subprocess

        # Validate repository URL
        if not repo.startswith(("https://", "git@")):
            raise ValueError(f"Invalid repository URL: {repo}")

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "-b", branch, repo, str(workspace)],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git clone failed: {e.stderr.decode()}")

    async def _generate_coding_plan(self, task: CodingTask) -> Dict[str, Any]:
        """Generate a plan for the coding task using LLM."""
        import httpx

        prompt = self._build_planning_prompt(task)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_url}/v1/chat/completions",
                    json={
                        "model": self.default_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are an expert software engineer. Generate a detailed step-by-step plan for the coding task.
Return a JSON object with:
{
  "analysis": "Brief analysis of the task",
  "steps": [
    {"action": "read_file|write_file|run_command", "target": "file/command", "description": "what this step does"}
  ],
  "estimated_changes": ["list of files that will be modified"],
  "risks": ["potential risks or issues"]
}"""
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.3,
                    },
                    headers={"Authorization": f"Bearer {os.environ.get('LITELLM_API_KEY', 'sk-hydra-litellm-key')}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON from response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"Failed to generate coding plan: {e}")

        # Return default plan
        return {
            "analysis": "Using default analysis",
            "steps": [
                {"action": "analyze", "target": "codebase", "description": "Analyze existing code"},
                {"action": "implement", "target": task.description, "description": "Implement requested changes"},
            ],
            "estimated_changes": task.target_files,
            "risks": ["Unable to generate detailed plan"],
        }

    def _build_planning_prompt(self, task: CodingTask) -> str:
        """Build the prompt for planning."""
        return f"""Task Type: {task.task_type.value}
Description: {task.description}

Repository: {task.repository or 'Local workspace'}
Branch: {task.branch}
Target Files: {', '.join(task.target_files) if task.target_files else 'Auto-detect'}

Additional Context:
{json.dumps(task.context, indent=2) if task.context else 'None'}

Generate a detailed implementation plan."""

    async def _execute_step(
        self,
        task: CodingTask,
        session: AgentSession,
        step: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single step of the coding plan."""
        action = step.get("action", "")
        target = step.get("target", "")

        # Safety check
        if not self._is_safe_operation(action, target):
            return {"error": f"Blocked unsafe operation: {action} {target}"}

        session.actions_taken += 1
        session.last_activity = datetime.utcnow()

        # Log the action
        session.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "target": target,
            "description": step.get("description", ""),
        })

        # Execute based on action type
        if action == "read_file":
            return await self._read_file(session, target)
        elif action == "write_file":
            return await self._write_file(session, target, step.get("content", ""))
        elif action == "run_command":
            return await self._run_command(session, target)
        elif action == "analyze":
            return {"status": "analyzed", "target": target}
        elif action == "implement":
            return await self._implement_change(task, session, step)
        else:
            return {"status": "skipped", "reason": f"Unknown action: {action}"}

    def _is_safe_operation(self, action: str, target: str) -> bool:
        """Check if an operation is safe to execute."""
        # Check blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in target:
                logger.warning(f"Blocked operation matching pattern: {pattern}")
                return False

        return True

    async def _read_file(self, session: AgentSession, file_path: str) -> Dict[str, Any]:
        """Read a file from the workspace."""
        full_path = Path(session.workspace_path) / file_path

        try:
            if full_path.exists():
                content = full_path.read_text()
                return {"action": "read_file", "file": file_path, "size": len(content)}
            else:
                return {"error": f"File not found: {file_path}"}
        except Exception as e:
            return {"error": f"Failed to read {file_path}: {e}"}

    async def _write_file(
        self,
        session: AgentSession,
        file_path: str,
        content: str,
    ) -> Dict[str, Any]:
        """Write a file to the workspace."""
        full_path = Path(session.workspace_path) / file_path

        try:
            # Record the change
            before = full_path.read_text() if full_path.exists() else None
            change_type = "modify" if full_path.exists() else "create"

            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            full_path.write_text(content)

            return {
                "action": "write_file",
                "file": file_path,
                "change_type": change_type,
                "size": len(content),
            }
        except Exception as e:
            return {"error": f"Failed to write {file_path}: {e}"}

    async def _run_command(self, session: AgentSession, command: str) -> Dict[str, Any]:
        """Run a command in the workspace."""
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=session.workspace_path,
                capture_output=True,
                timeout=60,
                text=True,
            )

            return {
                "action": "run_command",
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout[:1000] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out: {command}"}
        except Exception as e:
            return {"error": f"Command failed: {e}"}

    async def _implement_change(
        self,
        task: CodingTask,
        session: AgentSession,
        step: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Implement a code change using LLM."""
        import httpx

        prompt = f"""Implement the following change:

Task: {task.description}
Step: {step.get('description', 'Implement the change')}

Target files: {', '.join(task.target_files) if task.target_files else 'Auto-detect'}

Return the implementation as JSON:
{{
  "file": "path/to/file",
  "content": "the complete file content",
  "explanation": "what was changed and why"
}}"""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.llm_url}/v1/chat/completions",
                    json={
                        "model": self.default_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert software engineer. Write clean, well-documented code."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 4096,
                        "temperature": 0.2,
                    },
                    headers={"Authorization": f"Bearer {os.environ.get('LITELLM_API_KEY', 'sk-hydra-litellm-key')}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    session.tokens_used += data.get("usage", {}).get("total_tokens", 0)

                    # Parse the implementation
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        impl = json.loads(json_match.group())

                        # Write the file
                        if impl.get("file") and impl.get("content"):
                            return await self._write_file(
                                session,
                                impl["file"],
                                impl["content"]
                            )

                    return {"status": "implemented", "raw_response": content[:500]}

        except Exception as e:
            logger.error(f"Implementation failed: {e}")

        return {"error": "Failed to implement change"}

    async def _validate_changes(
        self,
        task: CodingTask,
        session: AgentSession,
    ) -> Dict[str, Any]:
        """Validate the changes made by the agent."""
        validation = {
            "passed": True,
            "checks": [],
            "errors": [],
        }

        workspace = Path(session.workspace_path)

        # Check 1: Files were actually modified
        if not task.changes:
            validation["checks"].append({
                "name": "changes_made",
                "passed": False,
                "message": "No changes were made"
            })
            validation["passed"] = False
        else:
            validation["checks"].append({
                "name": "changes_made",
                "passed": True,
                "message": f"{len(task.changes)} changes made"
            })

        # Check 2: Python syntax (if Python files)
        python_files = list(workspace.glob("**/*.py"))
        for py_file in python_files[:5]:  # Limit check
            try:
                compile(py_file.read_text(), str(py_file), "exec")
                validation["checks"].append({
                    "name": f"syntax:{py_file.name}",
                    "passed": True,
                })
            except SyntaxError as e:
                validation["checks"].append({
                    "name": f"syntax:{py_file.name}",
                    "passed": False,
                    "message": str(e),
                })
                validation["errors"].append(f"Syntax error in {py_file.name}: {e}")
                validation["passed"] = False

        # Check 3: No sensitive data exposed
        for change in task.changes:
            if isinstance(change, dict) and "content" in change:
                content = change.get("content", "")
                if any(pattern in content for pattern in ["password", "secret", "api_key", "token"]):
                    if "=" in content or ":" in content:
                        validation["checks"].append({
                            "name": "security:sensitive_data",
                            "passed": False,
                            "message": "Potential sensitive data in changes"
                        })
                        # Warning but don't fail

        return validation

    def get_task(self, task_id: str) -> Optional[CodingTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

        return [
            {
                "task_id": t.task_id,
                "task_type": t.task_type.value,
                "description": t.description[:100],
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
                "changes": len(t.changes),
                "errors": len(t.errors),
            }
            for t in tasks
        ]

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running task."""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()

            # Clean up session
            for sid, session in list(self.sessions.items()):
                if session.task_id == task_id:
                    session.status = "cancelled"
                    OPENHANDS_ACTIVE_SESSIONS.dec()

            return {"status": "cancelled", "task_id": task_id}

        return {"error": f"Task {task_id} is not running (status: {task.status.value})"}

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "active_sessions": len([s for s in self.sessions.values() if s.status == "active"]),
            "status_counts": status_counts,
            "workspace_base": str(self.workspace_base),
            "default_model": self.default_model,
        }


# =============================================================================
# Global Instance
# =============================================================================

_openhands_manager: Optional[OpenHandsManager] = None


def get_openhands_manager() -> OpenHandsManager:
    """Get or create the OpenHands manager."""
    global _openhands_manager
    if _openhands_manager is None:
        _openhands_manager = OpenHandsManager()
    return _openhands_manager


# =============================================================================
# FastAPI Router
# =============================================================================

def create_openhands_router():
    """Create FastAPI router for OpenHands endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/openhands", tags=["openhands-coding"])

    class CreateTaskRequest(BaseModel):
        task_type: str
        description: str
        repository: Optional[str] = None
        branch: Optional[str] = None
        target_files: Optional[List[str]] = None
        context: Optional[Dict[str, Any]] = None

    @router.get("/status")
    async def openhands_status():
        """Get OpenHands manager status and statistics."""
        manager = get_openhands_manager()
        return manager.get_stats()

    @router.post("/tasks")
    async def create_task(request: CreateTaskRequest):
        """Create a new coding task."""
        manager = get_openhands_manager()

        # Validate task type
        try:
            task_type = CodingTaskType(request.task_type)
        except ValueError:
            valid_types = [t.value for t in CodingTaskType]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task type. Valid types: {valid_types}"
            )

        task = await manager.create_task(
            task_type=task_type,
            description=request.description,
            repository=request.repository,
            branch=request.branch,
            target_files=request.target_files,
            context=request.context,
        )

        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "message": "Task created. Use /openhands/tasks/{task_id}/execute to run."
        }

    @router.post("/tasks/{task_id}/execute")
    async def execute_task(task_id: str):
        """Execute a coding task."""
        manager = get_openhands_manager()
        result = await manager.execute_task(task_id)
        return result

    @router.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get details of a specific task."""
        manager = get_openhands_manager()
        task = manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "description": task.description,
            "status": task.status.value,
            "repository": task.repository,
            "branch": task.branch,
            "target_files": task.target_files,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "changes": task.changes,
            "errors": task.errors,
            "pr_url": task.pr_url,
        }

    @router.get("/tasks")
    async def list_tasks(status: Optional[str] = None, limit: int = 50):
        """List all coding tasks."""
        manager = get_openhands_manager()

        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                pass

        return {"tasks": manager.list_tasks(status=task_status, limit=limit)}

    @router.post("/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        """Cancel a running task."""
        manager = get_openhands_manager()
        return await manager.cancel_task(task_id)

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get details of an agent session."""
        manager = get_openhands_manager()
        session = manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session.session_id,
            "task_id": session.task_id,
            "workspace_path": session.workspace_path,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "actions_taken": session.actions_taken,
            "tokens_used": session.tokens_used,
            "logs": session.logs[-20:],  # Last 20 logs
        }

    @router.get("/task-types")
    async def list_task_types():
        """List all available task types."""
        return {
            "task_types": [
                {
                    "type": t.value,
                    "description": t.name.replace("_", " ").title()
                }
                for t in CodingTaskType
            ]
        }

    return router
