"""
Hydra Agent Orchestrator
========================

Multi-agent orchestration layer enabling switching between different AI coding assistants:
- Aider (CLI-based, any model)
- OpenHands (autonomous SDK)
- Local models via TabbyAPI/Ollama
- Claude Code (via MCP)

Architecture:
- AgentProtocol: Abstract interface all agents implement
- AgentRegistry: Manages available agents
- TaskRouter: Routes tasks to optimal agent
- AgentOrchestrator: Main coordination layer
"""

import os
import json
import asyncio
import subprocess
import tempfile
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import intelligent model selector for proactive model loading
try:
    from hydra_tools.intelligent_model_selector import get_model_selector, classify_task as classify_task_type
    INTELLIGENT_MODEL_SELECTOR_AVAILABLE = True
except ImportError:
    INTELLIGENT_MODEL_SELECTOR_AVAILABLE = False
    logger.warning("Intelligent model selector not available")

# ============================================================================
# Data Models
# ============================================================================

class AgentCapability(str, Enum):
    """Capabilities an agent can have."""
    CODE_GENERATION = "code_generation"
    CODE_EDITING = "code_editing"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    WEB_BROWSING = "web_browsing"
    FILE_OPERATIONS = "file_operations"
    SHELL_COMMANDS = "shell_commands"
    AUTONOMOUS = "autonomous"
    UNCENSORED = "uncensored"  # No content restrictions


class AgentStatus(str, Enum):
    """Agent operational status."""
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    id: str
    name: str
    type: Literal["aider", "openhands", "local", "claude", "mistral"]
    model: str
    endpoint: Optional[str] = None
    capabilities: List[AgentCapability] = field(default_factory=list)
    cost_tier: Literal["free", "low", "medium", "high"] = "medium"
    max_concurrent: int = 1
    timeout_seconds: int = 300
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class TaskRequest:
    """A task to be executed by an agent."""
    id: str
    prompt: str
    files: List[str] = field(default_factory=list)
    working_dir: str = "/mnt/user/appdata/hydra-dev"
    capabilities_required: List[AgentCapability] = field(default_factory=list)
    prefer_agent: Optional[str] = None
    prefer_local: bool = False
    max_cost_tier: Literal["free", "low", "medium", "high"] = "high"
    timeout_seconds: int = 300


@dataclass
class TaskResult:
    """Result from an agent task execution."""
    task_id: str
    agent_id: str
    status: Literal["success", "error", "timeout", "cancelled"]
    output: str
    files_modified: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None


# ============================================================================
# Agent Protocol (Abstract Base)
# ============================================================================

class AgentProtocol(ABC):
    """Abstract protocol that all agents must implement."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.AVAILABLE
        self._current_task: Optional[str] = None

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute a task and return the result."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the agent is healthy and available."""
        pass

    def can_handle(self, task: TaskRequest) -> bool:
        """Check if this agent can handle the given task."""
        # Check capability requirements
        for cap in task.capabilities_required:
            if cap not in self.config.capabilities:
                return False

        # Check cost tier
        cost_order = ["free", "low", "medium", "high"]
        if cost_order.index(self.config.cost_tier) > cost_order.index(task.max_cost_tier):
            return False

        return True


# ============================================================================
# Aider Agent Implementation
# ============================================================================

class AiderAgent(AgentProtocol):
    """
    Aider CLI integration.

    Aider supports multiple model backends:
    - OpenAI GPT-4
    - Anthropic Claude
    - Ollama (local)
    - Any OpenAI-compatible API (TabbyAPI, LiteLLM)
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.aider_path = config.env_vars.get("AIDER_PATH", "aider")
        self._cached_model: Optional[str] = None

    async def _get_tabby_model(self) -> str:
        """Get the currently loaded model from TabbyAPI."""
        import httpx
        if self._cached_model:
            return self._cached_model
        try:
            # Extract base URL from endpoint (remove /v1 if present)
            base_url = self.config.endpoint.rstrip('/').replace('/v1', '')
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{base_url}/v1/model")
                if response.status_code == 200:
                    data = response.json()
                    self._cached_model = data.get("id", "gpt-4")
                    return self._cached_model
        except Exception as e:
            logger.warning(f"Could not detect TabbyAPI model: {e}")
        return "gpt-4"  # Fallback

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute task using Aider CLI."""
        start_time = datetime.now()
        self.status = AgentStatus.BUSY
        self._current_task = task.id

        try:
            # Build aider command
            cmd = [self.aider_path]

            # Model configuration
            if "ollama" in self.config.model.lower():
                # Ollama models: ollama/model-name
                cmd.extend(["--model", self.config.model])
            elif self.config.endpoint:
                # Custom OpenAI-compatible endpoint (TabbyAPI, LiteLLM)
                # Get actual model name from TabbyAPI
                model_name = await self._get_tabby_model()
                # Use text-completion-openai prefix for better compatibility
                cmd.extend([
                    "--openai-api-base", self.config.endpoint,
                    "--model", f"text-completion-openai/{model_name}"
                ])
            else:
                cmd.extend(["--model", self.config.model])

            # Add files to edit
            for f in task.files:
                cmd.extend(["--file", f])

            # Non-interactive mode with message
            cmd.extend([
                "--yes",  # Auto-confirm
                "--no-git",  # We'll handle git ourselves
                "--no-show-model-warnings",  # Suppress model warnings
                "--no-check-update",  # Skip update check
                "--no-stream",  # Disable streaming for compatibility
                "--no-auto-lint",  # Disable auto-lint
                "--edit-format", "diff",  # Use simpler diff format
                "--message", task.prompt
            ])

            # Set environment
            env = os.environ.copy()
            env.update(self.config.env_vars)
            # TabbyAPI doesn't need a real API key but LiteLLM requires one
            if "OPENAI_API_KEY" not in env:
                env["OPENAI_API_KEY"] = "sk-dummy-key-for-local-api"
            # Disable analytics to avoid network calls
            env["AIDER_ANALYTICS"] = "false"
            # For local APIs, disable some features that may cause issues
            env["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

            # Execute
            logger.info(f"Executing Aider: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=task.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=task.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="timeout",
                    output="",
                    error=f"Task timed out after {task.timeout_seconds}s",
                    execution_time_ms=task.timeout_seconds * 1000
                )

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            if process.returncode == 0:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="success",
                    output=stdout.decode(),
                    files_modified=task.files,  # Aider modifies in place
                    execution_time_ms=execution_time
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="error",
                    output=stdout.decode(),
                    error=stderr.decode(),
                    execution_time_ms=execution_time
                )

        except Exception as e:
            logger.exception(f"Aider execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="error",
                output="",
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        finally:
            self.status = AgentStatus.AVAILABLE
            self._current_task = None

    async def health_check(self) -> bool:
        """Check if Aider is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.aider_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False


# ============================================================================
# Local LLM Agent (TabbyAPI/Ollama)
# ============================================================================

class LocalLLMAgent(AgentProtocol):
    """
    Direct integration with local LLMs via TabbyAPI or Ollama.

    For coding tasks without the Aider wrapper - useful for:
    - Quick completions
    - Chat-based assistance
    - Uncensored models (Dolphin, etc.)
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._cached_model: Optional[str] = None

    async def _get_loaded_model(self) -> str:
        """Get the currently loaded model from TabbyAPI."""
        import httpx

        if self._cached_model:
            return self._cached_model

        if self.config.model != "default" and self.config.model:
            return self.config.model

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                if "ollama" not in self.config.endpoint.lower():
                    # TabbyAPI - query loaded model
                    response = await client.get(f"{self.config.endpoint}/v1/model")
                    if response.status_code == 200:
                        data = response.json()
                        self._cached_model = data.get("id", "default")
                        return self._cached_model
        except Exception as e:
            logger.warning(f"Could not detect model: {e}")

        return self.config.model or "default"

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute task using local LLM API."""
        import httpx

        start_time = datetime.now()
        self.status = AgentStatus.BUSY

        try:
            # Build prompt with file context
            context = ""
            for f in task.files:
                try:
                    with open(f, 'r') as fp:
                        context += f"\n### File: {f}\n```\n{fp.read()}\n```\n"
                except Exception as e:
                    context += f"\n### File: {f}\nError reading: {e}\n"

            full_prompt = f"{context}\n\n### Task:\n{task.prompt}"

            # Call API
            async with httpx.AsyncClient(timeout=task.timeout_seconds) as client:
                if "ollama" in self.config.endpoint.lower():
                    # Ollama API
                    response = await client.post(
                        f"{self.config.endpoint}/api/generate",
                        json={
                            "model": self.config.model,
                            "prompt": full_prompt,
                            "stream": False
                        }
                    )
                    result = response.json()
                    output = result.get("response", "")
                else:
                    # OpenAI-compatible API (TabbyAPI, LiteLLM)
                    model_name = await self._get_loaded_model()
                    # Some models (Mistral) don't support system messages - include in user prompt
                    enhanced_prompt = f"You are an expert coding assistant. Provide clear, working code with brief explanations.\n\n{full_prompt}"
                    response = await client.post(
                        f"{self.config.endpoint}/v1/chat/completions",
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "user", "content": enhanced_prompt}
                            ],
                            "max_tokens": 4096,
                            "temperature": 0.7
                        }
                    )
                    result = response.json()
                    # Handle error responses
                    if "error" in result:
                        raise Exception(f"API error: {result['error']}")
                    if "choices" not in result:
                        raise Exception(f"Unexpected response format: {result}")
                    output = result["choices"][0]["message"]["content"]

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="success",
                output=output,
                execution_time_ms=execution_time,
                tokens_used=result.get("usage", {}).get("total_tokens")
            )

        except Exception as e:
            logger.exception(f"Local LLM execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="error",
                output="",
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        finally:
            self.status = AgentStatus.AVAILABLE

    async def health_check(self) -> bool:
        """Check if the LLM API is available."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                if "ollama" in self.config.endpoint.lower():
                    response = await client.get(f"{self.config.endpoint}/api/tags")
                else:
                    response = await client.get(f"{self.config.endpoint}/v1/models")
                return response.status_code == 200
        except Exception:
            return False


# ============================================================================
# System Agents (SSH, Docker, Git)
# ============================================================================

class SSHExecutorAgent(AgentProtocol):
    """
    Execute commands on remote Hydra cluster nodes via SSH.

    Supports:
    - hydra-ai (192.168.1.250) - NixOS, TabbyAPI
    - hydra-compute (192.168.1.203) - NixOS, Ollama, ComfyUI
    - hydra-storage (192.168.1.244) - Unraid, Docker services
    """

    NODES = {
        "hydra-ai": {"host": "192.168.1.250", "user": "typhon"},
        "hydra-compute": {"host": "192.168.1.203", "user": "typhon"},
        "hydra-storage": {"host": "192.168.1.244", "user": "root"},
    }

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute SSH command on specified node."""
        start_time = datetime.now()
        self.status = AgentStatus.BUSY

        try:
            # Parse node from prompt (format: "node:command" or just command for local)
            prompt = task.prompt.strip()
            if ":" in prompt and prompt.split(":")[0] in self.NODES:
                node_name, command = prompt.split(":", 1)
                node = self.NODES[node_name.strip()]
            else:
                # Default to hydra-storage for local commands
                node = self.NODES["hydra-storage"]
                command = prompt

            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                f"{node['user']}@{node['host']}",
                command.strip()
            ]

            logger.info(f"SSH executing: {' '.join(ssh_cmd)}")

            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=task.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="timeout",
                    output="",
                    error=f"SSH command timed out after {task.timeout_seconds}s"
                )

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            if process.returncode == 0:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="success",
                    output=stdout.decode(),
                    execution_time_ms=execution_time
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="error",
                    output=stdout.decode(),
                    error=stderr.decode(),
                    execution_time_ms=execution_time
                )

        except Exception as e:
            logger.exception(f"SSH execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="error",
                output="",
                error=str(e)
            )
        finally:
            self.status = AgentStatus.AVAILABLE

    async def health_check(self) -> bool:
        """Check SSH connectivity to at least one node."""
        for node_name, node in self.NODES.items():
            try:
                process = await asyncio.create_subprocess_exec(
                    "ssh", "-o", "StrictHostKeyChecking=no",
                    "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                    f"{node['user']}@{node['host']}", "echo ok",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(process.communicate(), timeout=10)
                if process.returncode == 0:
                    return True
            except Exception:
                continue
        return False


class DockerManagerAgent(AgentProtocol):
    """
    Manage Docker containers on hydra-storage.

    Capabilities:
    - List containers
    - Start/stop/restart containers
    - View logs
    - Execute commands in containers
    """

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute Docker management command."""
        import docker
        start_time = datetime.now()
        self.status = AgentStatus.BUSY

        try:
            client = docker.from_env()
            prompt = task.prompt.strip().lower()

            # Parse command
            if prompt.startswith("list") or prompt == "ps":
                containers = client.containers.list(all=True)
                output = "\n".join([
                    f"{c.short_id} | {c.name:40} | {c.status:15} | {c.image.tags[0] if c.image.tags else 'no-tag'}"
                    for c in containers
                ])
                output = f"{'ID':12} | {'NAME':40} | {'STATUS':15} | IMAGE\n{'-'*90}\n{output}"

            elif prompt.startswith("restart "):
                container_name = prompt.replace("restart ", "").strip()
                container = client.containers.get(container_name)
                container.restart()
                output = f"Restarted container: {container_name}"

            elif prompt.startswith("stop "):
                container_name = prompt.replace("stop ", "").strip()
                container = client.containers.get(container_name)
                container.stop()
                output = f"Stopped container: {container_name}"

            elif prompt.startswith("start "):
                container_name = prompt.replace("start ", "").strip()
                container = client.containers.get(container_name)
                container.start()
                output = f"Started container: {container_name}"

            elif prompt.startswith("logs "):
                parts = prompt.replace("logs ", "").strip().split()
                container_name = parts[0]
                tail = int(parts[1]) if len(parts) > 1 else 100
                container = client.containers.get(container_name)
                output = container.logs(tail=tail).decode()

            elif prompt.startswith("health"):
                containers = client.containers.list()
                healthy = sum(1 for c in containers if c.status == "running")
                output = f"Running: {healthy}/{len(client.containers.list(all=True))} containers"

            else:
                output = f"Unknown Docker command: {prompt}\nAvailable: list, restart <name>, stop <name>, start <name>, logs <name> [lines], health"

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="success",
                output=output,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.exception(f"Docker operation failed: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="error",
                output="",
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        finally:
            self.status = AgentStatus.AVAILABLE

    async def health_check(self) -> bool:
        """Check Docker daemon connectivity."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False


class GitOperatorAgent(AgentProtocol):
    """
    Git operations for Hydra codebase.

    Capabilities:
    - Status, diff, log
    - Add, commit (never push without approval)
    - Branch management
    """

    async def execute(self, task: TaskRequest) -> TaskResult:
        """Execute Git operation."""
        start_time = datetime.now()
        self.status = AgentStatus.BUSY

        try:
            prompt = task.prompt.strip().lower()
            working_dir = task.working_dir

            # Parse command
            if prompt == "status":
                cmd = ["git", "status", "--short"]
            elif prompt == "diff":
                cmd = ["git", "diff", "--stat"]
            elif prompt.startswith("log"):
                count = prompt.replace("log", "").strip() or "10"
                cmd = ["git", "log", f"-{count}", "--oneline"]
            elif prompt == "branch":
                cmd = ["git", "branch", "-a"]
            elif prompt.startswith("add "):
                files = prompt.replace("add ", "").strip()
                cmd = ["git", "add"] + files.split()
            elif prompt.startswith("commit "):
                message = prompt.replace("commit ", "").strip()
                cmd = ["git", "commit", "-m", message]
            elif prompt.startswith("checkout "):
                branch = prompt.replace("checkout ", "").strip()
                cmd = ["git", "checkout", branch]
            elif prompt.startswith("branch "):
                branch = prompt.replace("branch ", "").strip()
                cmd = ["git", "checkout", "-b", branch]
            elif prompt == "pull":
                cmd = ["git", "pull", "--rebase"]
            else:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="error",
                    output="",
                    error=f"Unknown git command: {prompt}\nAvailable: status, diff, log [n], branch, add <files>, commit <msg>, checkout <branch>, pull"
                )

            logger.info(f"Git executing: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            if process.returncode == 0:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="success",
                    output=stdout.decode(),
                    execution_time_ms=execution_time
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    agent_id=self.id,
                    status="error",
                    output=stdout.decode(),
                    error=stderr.decode(),
                    execution_time_ms=execution_time
                )

        except Exception as e:
            logger.exception(f"Git operation failed: {e}")
            return TaskResult(
                task_id=task.id,
                agent_id=self.id,
                status="error",
                output="",
                error=str(e)
            )
        finally:
            self.status = AgentStatus.AVAILABLE

    async def health_check(self) -> bool:
        """Check if we're in a git repository."""
        try:
            # Try /app first (Docker), then /mnt/user/appdata/hydra-dev (host)
            for cwd in ["/app", "/mnt/user/appdata/hydra-dev"]:
                process = await asyncio.create_subprocess_exec(
                    "git", "rev-parse", "--is-inside-work-tree",
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                if b"true" in stdout:
                    return True
            return False
        except Exception:
            return False


# ============================================================================
# Agent Registry
# ============================================================================

class AgentRegistry:
    """Registry of all available agents."""

    def __init__(self):
        self._agents: Dict[str, AgentProtocol] = {}
        self._configs: Dict[str, AgentConfig] = {}

    def register(self, config: AgentConfig) -> AgentProtocol:
        """Register a new agent from config."""
        # Create appropriate agent type
        if config.type == "aider":
            agent = AiderAgent(config)
        elif config.type == "local":
            agent = LocalLLMAgent(config)
        elif config.type == "ssh":
            agent = SSHExecutorAgent(config)
        elif config.type == "docker":
            agent = DockerManagerAgent(config)
        elif config.type == "git":
            agent = GitOperatorAgent(config)
        else:
            raise ValueError(f"Unknown agent type: {config.type}")

        self._agents[config.id] = agent
        self._configs[config.id] = config
        logger.info(f"Registered agent: {config.id} ({config.type})")
        return agent

    def get(self, agent_id: str) -> Optional[AgentProtocol]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_all(self) -> List[AgentConfig]:
        """List all registered agent configs."""
        return list(self._configs.values())

    def find_capable(self, task: TaskRequest) -> List[AgentProtocol]:
        """Find all agents capable of handling a task."""
        return [
            agent for agent in self._agents.values()
            if agent.can_handle(task) and agent.status == AgentStatus.AVAILABLE
        ]


# ============================================================================
# Task Router
# ============================================================================

class TaskRouter:
    """Routes tasks to the optimal agent."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def select_agent(self, task: TaskRequest) -> Optional[AgentProtocol]:
        """Select the best agent for a task."""

        # If user specified an agent, try to use it
        if task.prefer_agent:
            agent = self.registry.get(task.prefer_agent)
            if agent and agent.can_handle(task):
                return agent

        # Find capable agents
        capable = self.registry.find_capable(task)

        if not capable:
            return None

        # Prioritize based on preferences
        if task.prefer_local:
            # Prefer local/free agents
            local_agents = [a for a in capable if a.config.cost_tier == "free"]
            if local_agents:
                return local_agents[0]

        # Sort by cost tier (prefer cheaper)
        cost_order = {"free": 0, "low": 1, "medium": 2, "high": 3}
        capable.sort(key=lambda a: cost_order[a.config.cost_tier])

        return capable[0]


# ============================================================================
# Agent Orchestrator (Main Interface)
# ============================================================================

class AgentOrchestrator:
    """
    Main orchestration layer for multi-agent system.

    Provides unified interface to:
    - Register and manage agents
    - Route tasks to optimal agents
    - Execute tasks with fallback
    - Track execution history
    """

    def __init__(self):
        self.registry = AgentRegistry()
        self.router = TaskRouter(self.registry)
        self._task_history: List[TaskResult] = []
        self._initialize_default_agents()

    def _initialize_default_agents(self):
        """Initialize default agent configurations."""

        # Aider with Ollama (local, free, 32B coding model)
        self.registry.register(AgentConfig(
            id="aider-ollama",
            name="Aider + Qwen2.5-Coder-32B",
            type="aider",
            model="ollama/qwen2.5-coder:32b",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_EDITING,
                AgentCapability.REFACTORING,
                AgentCapability.FILE_OPERATIONS,
                AgentCapability.SHELL_COMMANDS,
                AgentCapability.ARCHITECTURE,
            ],
            cost_tier="free",
            env_vars={
                "OLLAMA_API_BASE": "http://192.168.1.203:11434"
            }
        ))

        # Aider with TabbyAPI (local, free, Devstral 24B coding model)
        self.registry.register(AgentConfig(
            id="aider-tabby",
            name="Aider + Devstral-24B",
            type="aider",
            model="Devstral-Small-2505-exl2-4.25bpw",  # 24B coding model from Mistral
            endpoint="http://192.168.1.250:5000/v1",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_EDITING,
                AgentCapability.REFACTORING,
                AgentCapability.ARCHITECTURE,
                AgentCapability.FILE_OPERATIONS,
                AgentCapability.SHELL_COMMANDS,
                AgentCapability.DEBUGGING,
            ],
            cost_tier="free"
        ))

        # Direct TabbyAPI for chat (uncensored if using Dolphin/etc)
        self.registry.register(AgentConfig(
            id="tabby-direct",
            name="TabbyAPI Direct",
            type="local",
            model="default",
            endpoint="http://192.168.1.250:5000",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.DOCUMENTATION,
                AgentCapability.UNCENSORED,
            ],
            cost_tier="free"
        ))

        # Ollama direct for coding tasks (32B model)
        self.registry.register(AgentConfig(
            id="ollama-coder",
            name="Ollama Qwen2.5-Coder-32B",
            type="local",
            model="qwen2.5-coder:32b",
            endpoint="http://192.168.1.203:11434",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.DEBUGGING,
                AgentCapability.REFACTORING,
                AgentCapability.ARCHITECTURE,
            ],
            cost_tier="free"
        ))

        # Ollama Dolphin for uncensored tasks (70B model)
        self.registry.register(AgentConfig(
            id="ollama-dolphin",
            name="Ollama Dolphin (Uncensored)",
            type="local",
            model="dolphin-llama3:70b",
            endpoint="http://192.168.1.203:11434",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.DOCUMENTATION,
                AgentCapability.UNCENSORED,
                AgentCapability.ARCHITECTURE,
            ],
            cost_tier="free"
        ))

        # --- System Agents ---

        # SSH Executor for remote cluster commands
        self.registry.register(AgentConfig(
            id="ssh-executor",
            name="SSH Executor",
            type="ssh",
            model="n/a",
            capabilities=[
                AgentCapability.SHELL_COMMANDS,
                AgentCapability.AUTONOMOUS,
            ],
            cost_tier="free"
        ))

        # Docker Manager for container operations
        self.registry.register(AgentConfig(
            id="docker-manager",
            name="Docker Manager",
            type="docker",
            model="n/a",
            capabilities=[
                AgentCapability.SHELL_COMMANDS,
                AgentCapability.AUTONOMOUS,
            ],
            cost_tier="free"
        ))

        # Git Operator for version control
        self.registry.register(AgentConfig(
            id="git-operator",
            name="Git Operator",
            type="git",
            model="n/a",
            capabilities=[
                AgentCapability.FILE_OPERATIONS,
                AgentCapability.AUTONOMOUS,
            ],
            cost_tier="free"
        ))

    async def execute_task(self, task: TaskRequest) -> TaskResult:
        """Execute a task using the best available agent.

        This method now integrates with the intelligent model selector to
        ensure the optimal model is loaded before task execution.
        """
        # Proactively ensure optimal model is loaded
        if INTELLIGENT_MODEL_SELECTOR_AVAILABLE:
            try:
                selector = get_model_selector()
                model_result = await selector.ensure_optimal_model(
                    prompt=task.prompt,
                    files=task.files,
                    auto_load=True,
                    prefer_speed=False
                )
                if model_result.get("action_taken") == "loaded":
                    logger.info(
                        f"Auto-loaded optimal model for task: {model_result['recommended_model'].model_name}"
                    )
            except Exception as e:
                logger.warning(f"Intelligent model selection failed, continuing with current model: {e}")

        agent = self.router.select_agent(task)

        if not agent:
            return TaskResult(
                task_id=task.id,
                agent_id="none",
                status="error",
                output="",
                error="No capable agent available for this task"
            )

        logger.info(f"Routing task {task.id} to agent {agent.id}")

        result = await agent.execute(task)
        self._task_history.append(result)

        return result

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered agents."""
        results = {}
        for agent_id, agent in self.registry._agents.items():
            results[agent_id] = await agent.health_check()
        return results

    def get_history(self, limit: int = 50) -> List[TaskResult]:
        """Get recent task execution history."""
        return self._task_history[-limit:]


# ============================================================================
# FastAPI Router
# ============================================================================

def create_agent_orchestrator_router() -> APIRouter:
    """Create FastAPI router for agent orchestration."""

    router = APIRouter(prefix="/agents", tags=["Agent Orchestrator"])
    orchestrator = AgentOrchestrator()

    # Pydantic models for API
    class TaskRequestModel(BaseModel):
        prompt: str
        files: List[str] = []
        working_dir: str = "/mnt/user/appdata/hydra-dev"
        capabilities_required: List[str] = []
        prefer_agent: Optional[str] = None
        prefer_local: bool = True
        max_cost_tier: str = "high"
        timeout_seconds: int = 300

    class TaskResultModel(BaseModel):
        task_id: str
        agent_id: str
        status: str
        output: str
        files_modified: List[str] = []
        execution_time_ms: int = 0
        tokens_used: Optional[int] = None
        cost_estimate: Optional[float] = None
        error: Optional[str] = None

    @router.get("/")
    async def list_agents():
        """List all registered agents."""
        agents = orchestrator.registry.list_all()
        agent_list = []
        for a in agents:
            agent_obj = orchestrator.registry.get(a.id)
            model_display = a.model
            # For LocalLLMAgent, try to get the actual loaded model
            if isinstance(agent_obj, LocalLLMAgent) and a.model == "default":
                try:
                    model_display = await agent_obj._get_loaded_model()
                except Exception:
                    model_display = f"{a.model} (detection failed)"
            agent_list.append({
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "model": model_display,
                "endpoint": a.endpoint,
                "capabilities": [c.value for c in a.capabilities],
                "cost_tier": a.cost_tier,
                "status": agent_obj.status.value
            })
        return {"agents": agent_list}

    @router.get("/health")
    async def health_check():
        """Check health of all agents."""
        health = await orchestrator.health_check_all()
        return {"agents": health, "any_available": any(health.values())}

    @router.post("/execute", response_model=TaskResultModel)
    async def execute_task(request: TaskRequestModel):
        """Execute a task using the best available agent."""
        import uuid

        task = TaskRequest(
            id=str(uuid.uuid4()),
            prompt=request.prompt,
            files=request.files,
            working_dir=request.working_dir,
            capabilities_required=[AgentCapability(c) for c in request.capabilities_required],
            prefer_agent=request.prefer_agent,
            prefer_local=request.prefer_local,
            max_cost_tier=request.max_cost_tier,
            timeout_seconds=request.timeout_seconds
        )

        result = await orchestrator.execute_task(task)

        return TaskResultModel(
            task_id=result.task_id,
            agent_id=result.agent_id,
            status=result.status,
            output=result.output,
            files_modified=result.files_modified,
            execution_time_ms=result.execution_time_ms,
            tokens_used=result.tokens_used,
            cost_estimate=result.cost_estimate,
            error=result.error
        )

    @router.get("/history")
    async def get_history(limit: int = 50):
        """Get recent task execution history."""
        history = orchestrator.get_history(limit)
        return {
            "tasks": [
                {
                    "task_id": r.task_id,
                    "agent_id": r.agent_id,
                    "status": r.status,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in history
            ]
        }

    return router


# ============================================================================
# Autonomous Caretaker Configuration
# ============================================================================

AUTONOMOUS_CARETAKER_CONFIG = """
# Hydra Autonomous Caretaker Architecture
# =======================================

## Recommended Setup for 24/7 Autonomous Operation

### Primary Coding Agent: Aider + TabbyAPI
- Model: Devstral-Small-2 (24B) or DeepSeek-Coder-33B
- Why: Excellent coding, runs locally, no API costs
- Capabilities: Code generation, refactoring, file editing

### Secondary/Fallback: Aider + Ollama
- Model: Qwen2.5-Coder-32B or DeepSeek-Coder-33B
- Why: Redundancy on second GPU cluster
- Node: hydra-compute (192.168.1.203)

### Uncensored Assistant: Dolphin-Mixtral via TabbyAPI
- Model: cognitivecomputations/dolphin-2.9-mixtral-8x22b
- Why: No content restrictions, excellent reasoning
- Use for: Creative content, unrestricted assistance

### Autonomous Orchestration: OpenHands (Future)
- For fully autonomous multi-step tasks
- Runs in Docker sandbox
- Can execute shell commands, browse web

## Model Recommendations by Task

| Task Type | Recommended Model | Node |
|-----------|------------------|------|
| Complex coding | Claude Sonnet 4 (via API) | API |
| Bulk refactoring | Devstral-Small-2 | hydra-ai |
| Quick completions | Qwen2.5-Coder-7B | hydra-compute |
| Uncensored chat | Dolphin-Mixtral | hydra-ai |
| Architecture | DeepSeek-R1-Distill | hydra-ai |

## Cost Optimization Strategy

1. **Default to local** - Use TabbyAPI/Ollama first
2. **Escalate for complexity** - Use Claude for hard problems
3. **Batch similar tasks** - Group operations for efficiency
4. **Cache responses** - Store common patterns
"""
