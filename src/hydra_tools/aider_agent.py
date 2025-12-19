"""
Aider Agent Integration for Hydra Autonomous Caretaker

Provides autonomous coding capabilities using Aider with local models.
Supports TabbyAPI (hydra-ai) and Ollama (hydra-compute) as backends.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import httpx

logger = logging.getLogger(__name__)


class AiderBackend(Enum):
    """Available backends for Aider."""
    TABBY_API = "tabbyapi"      # hydra-ai:5000 - 70B models
    OLLAMA = "ollama"           # hydra-compute:11434 - 7B-32B models
    LITELLM = "litellm"         # hydra-storage:4000 - Unified gateway


@dataclass
class AiderConfig:
    """Configuration for Aider execution."""
    backend: AiderBackend = AiderBackend.OLLAMA
    model: str = "ollama/qwen2.5-coder:32b"
    api_base: str = "http://192.168.1.203:11434"

    # Aider behavior
    auto_commits: bool = True
    edit_format: str = "diff"  # "diff", "whole", "udiff"
    architect_mode: bool = False

    # Safety
    dry_run: bool = False
    no_git: bool = False

    # Paths
    working_dir: str = "/mnt/user/appdata/hydra-dev"


@dataclass
class AiderTask:
    """A task for Aider to execute."""
    id: str
    prompt: str
    files: List[str] = field(default_factory=list)
    config: Optional[AiderConfig] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


# Model configurations for different backends
MODEL_CONFIGS = {
    # Ollama models on hydra-compute
    "qwen2.5-coder:32b": {
        "backend": AiderBackend.OLLAMA,
        "api_base": "http://192.168.1.203:11434",
        "model": "ollama/qwen2.5-coder:32b",
        "capabilities": ["coding", "refactoring", "documentation"],
        "vram_gb": 18,
    },
    "qwen2.5-coder:7b": {
        "backend": AiderBackend.OLLAMA,
        "api_base": "http://192.168.1.203:11434",
        "model": "ollama/qwen2.5-coder:7b",
        "capabilities": ["quick_fixes", "simple_edits"],
        "vram_gb": 5,
    },
    "dolphin-llama3:70b": {
        "backend": AiderBackend.OLLAMA,
        "api_base": "http://192.168.1.203:11434",
        "model": "ollama/dolphin-llama3:70b",
        "capabilities": ["coding", "refactoring", "uncensored", "creative"],
        "vram_gb": 40,
        "uncensored": True,
    },
    "deepseek-r1:8b": {
        "backend": AiderBackend.OLLAMA,
        "api_base": "http://192.168.1.203:11434",
        "model": "ollama/deepseek-r1:8b",
        "capabilities": ["reasoning", "architecture", "planning"],
        "vram_gb": 5,
    },
    # TabbyAPI models on hydra-ai
    "tabby-default": {
        "backend": AiderBackend.TABBY_API,
        "api_base": "http://192.168.1.250:5000/v1",
        "model": "openai/current-model",
        "capabilities": ["coding", "refactoring", "creative", "uncensored"],
        "vram_gb": 50,
        "uncensored": True,
    },
    # LiteLLM gateway
    "litellm-tabby": {
        "backend": AiderBackend.LITELLM,
        "api_base": "http://192.168.1.244:4000",
        "model": "tabby",
        "capabilities": ["coding", "refactoring", "creative"],
    },
}


class AiderAgent:
    """
    Autonomous coding agent using Aider.

    Provides:
    - Code generation and editing
    - Multi-file refactoring
    - Git integration
    - Multiple model backends
    """

    def __init__(self, config: Optional[AiderConfig] = None):
        self.config = config or AiderConfig()
        self._task_history: List[AiderTask] = []
        self._current_task: Optional[AiderTask] = None

    def _build_aider_command(
        self,
        prompt: str,
        files: List[str],
        config: AiderConfig,
    ) -> List[str]:
        """Build the Aider command line."""
        cmd = ["aider"]

        # Model configuration
        cmd.extend(["--model", config.model])

        # API base for the backend
        if config.backend == AiderBackend.OLLAMA:
            cmd.extend(["--openai-api-base", config.api_base])
            cmd.extend(["--openai-api-key", "ollama"])
        elif config.backend == AiderBackend.TABBY_API:
            cmd.extend(["--openai-api-base", config.api_base])
            cmd.extend(["--openai-api-key", "hydra-local"])
        elif config.backend == AiderBackend.LITELLM:
            cmd.extend(["--openai-api-base", config.api_base])
            # LiteLLM key from environment
            litellm_key = os.environ.get("LITELLM_KEY", "sk-hydra-local")
            cmd.extend(["--openai-api-key", litellm_key])

        # Edit format
        cmd.extend(["--edit-format", config.edit_format])

        # Architect mode for complex tasks
        if config.architect_mode:
            cmd.append("--architect")

        # Git behavior
        if config.auto_commits:
            cmd.append("--auto-commits")
        else:
            cmd.append("--no-auto-commits")

        if config.no_git:
            cmd.append("--no-git")

        if config.dry_run:
            cmd.append("--dry-run")

        # Non-interactive mode
        cmd.append("--yes")
        cmd.append("--no-stream")

        # Add the message
        cmd.extend(["--message", prompt])

        # Add files to edit
        cmd.extend(files)

        return cmd

    async def execute_task(
        self,
        prompt: str,
        files: Optional[List[str]] = None,
        config: Optional[AiderConfig] = None,
        task_id: Optional[str] = None,
    ) -> AiderTask:
        """
        Execute an Aider task asynchronously.

        Args:
            prompt: The instruction for Aider
            files: List of files to edit (relative to working_dir)
            config: Optional override configuration
            task_id: Optional task identifier

        Returns:
            AiderTask with results
        """
        config = config or self.config
        files = files or []
        task_id = task_id or f"aider-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        task = AiderTask(
            id=task_id,
            prompt=prompt,
            files=files,
            config=config,
            status="running",
        )
        self._current_task = task
        self._task_history.append(task)

        start_time = datetime.utcnow()

        try:
            # Build command
            cmd = self._build_aider_command(prompt, files, config)

            logger.info(f"Executing Aider task {task_id}: {prompt[:100]}...")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Execute in working directory
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=config.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "TERM": "dumb"},
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600,  # 10 minute timeout
            )

            task.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            if process.returncode == 0:
                task.status = "completed"
                task.result = stdout.decode("utf-8", errors="replace")
                logger.info(f"Task {task_id} completed in {task.duration_seconds:.1f}s")
            else:
                task.status = "failed"
                task.error = stderr.decode("utf-8", errors="replace")
                logger.error(f"Task {task_id} failed: {task.error[:200]}")

        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = "Task timed out after 600 seconds"
            task.duration_seconds = 600
            logger.error(f"Task {task_id} timed out")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            logger.exception(f"Task {task_id} error: {e}")

        finally:
            self._current_task = None

        return task

    async def quick_edit(
        self,
        prompt: str,
        file: str,
        use_fast_model: bool = True,
    ) -> AiderTask:
        """
        Quick edit a single file with a fast model.

        Best for: Simple fixes, docstrings, type hints.
        """
        config = AiderConfig(
            backend=AiderBackend.OLLAMA,
            model="ollama/qwen2.5-coder:7b" if use_fast_model else "ollama/qwen2.5-coder:32b",
            api_base="http://192.168.1.203:11434",
            auto_commits=False,
            edit_format="diff",
        )
        return await self.execute_task(prompt, [file], config)

    async def refactor(
        self,
        prompt: str,
        files: List[str],
        use_architect: bool = True,
    ) -> AiderTask:
        """
        Multi-file refactoring with architect mode.

        Best for: Complex changes spanning multiple files.
        """
        config = AiderConfig(
            backend=AiderBackend.OLLAMA,
            model="ollama/qwen2.5-coder:32b",
            api_base="http://192.168.1.203:11434",
            auto_commits=True,
            architect_mode=use_architect,
            edit_format="diff",
        )
        return await self.execute_task(prompt, files, config)

    async def creative_coding(
        self,
        prompt: str,
        files: List[str],
    ) -> AiderTask:
        """
        Creative/uncensored coding task using Dolphin.

        Best for: Adult content, unrestricted generation.
        """
        config = AiderConfig(
            backend=AiderBackend.OLLAMA,
            model="ollama/dolphin-llama3:70b",
            api_base="http://192.168.1.203:11434",
            auto_commits=True,
            edit_format="whole",  # Dolphin works better with whole file
        )
        return await self.execute_task(prompt, files, config)

    async def check_backend_health(self, backend: AiderBackend) -> Dict[str, Any]:
        """Check if a backend is available."""
        endpoints = {
            AiderBackend.OLLAMA: "http://192.168.1.203:11434/api/tags",
            AiderBackend.TABBY_API: "http://192.168.1.250:5000/health",
            AiderBackend.LITELLM: "http://192.168.1.244:4000/health",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoints[backend])
                return {
                    "backend": backend.value,
                    "healthy": resp.status_code < 400,
                    "status_code": resp.status_code,
                }
        except Exception as e:
            return {
                "backend": backend.value,
                "healthy": False,
                "error": str(e),
            }

    def get_task_history(self) -> List[Dict]:
        """Get history of executed tasks."""
        return [
            {
                "id": t.id,
                "prompt": t.prompt[:100] + "..." if len(t.prompt) > 100 else t.prompt,
                "files": t.files,
                "status": t.status,
                "duration_seconds": t.duration_seconds,
                "created_at": t.created_at.isoformat(),
            }
            for t in self._task_history
        ]

    @property
    def current_task(self) -> Optional[Dict]:
        """Get the currently running task, if any."""
        if self._current_task:
            return {
                "id": self._current_task.id,
                "prompt": self._current_task.prompt,
                "status": self._current_task.status,
                "started_at": self._current_task.created_at.isoformat(),
            }
        return None


# Global agent instance
_aider_agent: Optional[AiderAgent] = None


def get_aider_agent() -> AiderAgent:
    """Get or create the global Aider agent."""
    global _aider_agent
    if _aider_agent is None:
        _aider_agent = AiderAgent()
    return _aider_agent


# FastAPI router for Aider endpoints
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel


class AiderTaskRequest(BaseModel):
    prompt: str
    files: List[str] = []
    model: Optional[str] = None
    architect_mode: bool = False
    auto_commits: bool = True
    dry_run: bool = False


class AiderQuickEditRequest(BaseModel):
    prompt: str
    file: str
    use_fast_model: bool = True


def create_aider_router() -> APIRouter:
    """Create the Aider API router."""
    router = APIRouter(prefix="/aider", tags=["aider"])

    @router.get("/health")
    async def aider_health():
        """Check Aider and backend health."""
        agent = get_aider_agent()

        backends = await asyncio.gather(
            agent.check_backend_health(AiderBackend.OLLAMA),
            agent.check_backend_health(AiderBackend.TABBY_API),
            agent.check_backend_health(AiderBackend.LITELLM),
        )

        return {
            "aider_installed": True,
            "backends": backends,
            "current_task": agent.current_task,
        }

    @router.get("/models")
    async def list_models():
        """List available models for Aider."""
        return {"models": MODEL_CONFIGS}

    @router.get("/history")
    async def get_history():
        """Get task execution history."""
        agent = get_aider_agent()
        return {"tasks": agent.get_task_history()}

    @router.post("/execute")
    async def execute_task(request: AiderTaskRequest, background_tasks: BackgroundTasks):
        """Execute an Aider coding task."""
        agent = get_aider_agent()

        if agent.current_task:
            raise HTTPException(
                status_code=409,
                detail=f"Task already running: {agent.current_task['id']}"
            )

        # Build config from request
        config = AiderConfig(
            architect_mode=request.architect_mode,
            auto_commits=request.auto_commits,
            dry_run=request.dry_run,
        )

        # Select model
        if request.model and request.model in MODEL_CONFIGS:
            model_config = MODEL_CONFIGS[request.model]
            config.backend = model_config["backend"]
            config.model = model_config["model"]
            config.api_base = model_config["api_base"]

        # Execute in background
        task_id = f"aider-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        async def run_task():
            await agent.execute_task(
                prompt=request.prompt,
                files=request.files,
                config=config,
                task_id=task_id,
            )

        background_tasks.add_task(asyncio.create_task, run_task())

        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Task started in background",
        }

    @router.post("/quick-edit")
    async def quick_edit(request: AiderQuickEditRequest):
        """Quick edit a single file."""
        agent = get_aider_agent()

        if agent.current_task:
            raise HTTPException(
                status_code=409,
                detail=f"Task already running: {agent.current_task['id']}"
            )

        task = await agent.quick_edit(
            prompt=request.prompt,
            file=request.file,
            use_fast_model=request.use_fast_model,
        )

        return {
            "task_id": task.id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "duration_seconds": task.duration_seconds,
        }

    @router.get("/current")
    async def get_current_task():
        """Get the currently running task."""
        agent = get_aider_agent()
        if agent.current_task:
            return agent.current_task
        return {"message": "No task currently running"}

    return router
