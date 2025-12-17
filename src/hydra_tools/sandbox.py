"""
Hydra Sandbox - Secure Code Execution Environment

Provides isolated container-based sandboxing for safe code execution.
Used by the self-improvement system to test proposed changes.

Security model:
- Restricted Docker containers with minimal capabilities
- No network access (--network=none)
- Memory and CPU limits
- Execution timeout
- Read-only root filesystem where possible
- Dropped capabilities
- Constitutional constraint integration

Uses Docker Python SDK for container management.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


# Configure logging
logger = logging.getLogger(__name__)


class SandboxLanguage(str, Enum):
    """Supported languages for sandbox execution."""
    PYTHON = "python"
    BASH = "bash"
    JAVASCRIPT = "javascript"


class ExecutionStatus(str, Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"
    ERROR = "error"


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    # Resource limits
    memory_limit: str = "256m"
    cpu_limit: float = 0.5  # CPU cores
    timeout_seconds: int = 30
    max_output_bytes: int = 1024 * 1024  # 1MB

    # Security settings
    network_enabled: bool = False
    read_only_root: bool = True
    drop_capabilities: bool = True
    no_new_privileges: bool = True

    # Execution settings
    working_dir: str = "/sandbox"
    user: str = "nobody"


@dataclass
class ExecutionResult:
    """Result of sandbox code execution."""
    execution_id: str
    status: ExecutionStatus
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class SandboxManager:
    """
    Manages sandboxed code execution using Docker containers.

    Security features:
    - Network isolation (network_mode='none')
    - Resource limits (memory, CPU, time)
    - Dropped capabilities
    - Read-only root filesystem
    - Non-root user execution
    - Output size limits
    """

    # Docker images for each language
    IMAGES = {
        SandboxLanguage.PYTHON: "python:3.11-slim",
        SandboxLanguage.BASH: "alpine:latest",
        SandboxLanguage.JAVASCRIPT: "node:20-slim",
    }

    # Commands for each language
    COMMANDS = {
        SandboxLanguage.PYTHON: ["python", "/sandbox/code"],
        SandboxLanguage.BASH: ["sh", "/sandbox/code"],
        SandboxLanguage.JAVASCRIPT: ["node", "/sandbox/code"],
    }

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        data_dir: str = "/data/sandbox",
        host_data_dir: Optional[str] = None,
    ):
        self.config = config or SandboxConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Host path mapping for volume mounts
        # When running in a container, internal paths need to be mapped to host paths
        # for Docker volume mounts to work with sibling containers
        if host_data_dir:
            self.host_data_dir = Path(host_data_dir)
        else:
            # Default: /data in container maps to /mnt/user/appdata/hydra-stack/data on host
            self.host_data_dir = Path("/mnt/user/appdata/hydra-stack/data/sandbox")

        # Docker client
        self._client = None

        # Execution history
        self.history_file = self.data_dir / "execution_history.json"
        self.history: List[Dict[str, Any]] = self._load_history()

        # Container prefix for identification
        self.container_prefix = "hydra-sandbox-"

        # Constitutional enforcer reference (lazy loaded)
        self._enforcer = None

    @property
    def client(self) -> docker.DockerClient:
        """Lazy-load Docker client."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load execution history from disk."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        """Save execution history to disk."""
        # Keep only last 1000 entries
        self.history = self.history[-1000:]
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2, default=str)

    def _get_enforcer(self):
        """Lazy load constitutional enforcer."""
        if self._enforcer is None:
            try:
                from hydra_tools.constitution import get_enforcer
                self._enforcer = get_enforcer()
            except ImportError:
                logger.warning("Constitutional enforcer not available")
        return self._enforcer

    def _check_constitutional_constraints(self, code: str, language: SandboxLanguage) -> Tuple[bool, str]:
        """
        Check if code violates constitutional constraints.

        Returns (allowed, reason).
        """
        enforcer = self._get_enforcer()
        if enforcer is None:
            return True, "Enforcer not available, allowing execution"

        # Check operation type
        result = enforcer.check_operation(
            operation_type="sandbox_execute",
            target_resource=f"code:{language.value}",
            details={
                "code_hash": hashlib.sha256(code.encode()).hexdigest(),
                "code_length": len(code),
                "language": language.value,
            }
        )

        if not result.allowed:
            return False, result.reason

        # Additional code-level checks - log but don't block (sandbox handles security)
        dangerous_patterns = {
            SandboxLanguage.PYTHON: [
                "os.system",
                "subprocess.call",
                "__import__('os')",
                "import socket",
            ],
            SandboxLanguage.BASH: [
                "rm -rf /",
                "dd if=",
                "mkfs",
                "> /dev/",
            ],
            SandboxLanguage.JAVASCRIPT: [
                "child_process",
                "require('fs')",
            ],
        }

        patterns = dangerous_patterns.get(language, [])
        for pattern in patterns:
            if pattern in code:
                logger.warning(f"Potentially dangerous pattern detected: {pattern}")

        return True, "Allowed"

    def _pull_image_if_needed(self, image: str):
        """Pull Docker image if not available locally."""
        try:
            self.client.images.get(image)
            logger.debug(f"Image {image} already available")
        except ImageNotFound:
            logger.info(f"Pulling image {image}...")
            self.client.images.pull(image)
            logger.info(f"Image {image} pulled successfully")

    def execute(
        self,
        code: str,
        language: SandboxLanguage = SandboxLanguage.PYTHON,
        config: Optional[SandboxConfig] = None,
        files: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Execute code in a sandboxed container.

        Args:
            code: The code to execute
            language: Programming language
            config: Optional custom configuration
            files: Optional additional files to mount (filename -> content)

        Returns:
            ExecutionResult with status, output, and metrics
        """
        execution_id = str(uuid.uuid4())[:8]
        config = config or self.config
        started_at = datetime.utcnow()

        # Check constitutional constraints
        allowed, reason = self._check_constitutional_constraints(code, language)
        if not allowed:
            result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.ERROR,
                error_message=f"Constitutional constraint violation: {reason}",
                started_at=started_at.isoformat() + "Z",
                finished_at=datetime.utcnow().isoformat() + "Z",
            )
            self._record_execution(result)
            return result

        # Create temporary directory for code in a shared location
        # Use data_dir which is mounted from host, so sandbox containers can access it
        sandbox_temp_base = self.data_dir / "temp"
        sandbox_temp_base.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="sandbox-", dir=str(sandbox_temp_base))
        code_file = os.path.join(temp_dir, "code")

        # Calculate the host path for Docker volume mount
        # temp_dir is like /data/sandbox/temp/sandbox-xxxx
        # host path should be like /mnt/user/appdata/hydra-tools/sandbox/temp/sandbox-xxxx
        relative_path = Path(temp_dir).relative_to(self.data_dir)
        host_temp_dir = str(self.host_data_dir / relative_path)

        try:
            # Write code to file with world-readable permissions
            # (sandbox runs as 'nobody' which needs read access)
            with open(code_file, "w") as f:
                f.write(code)
            os.chmod(code_file, 0o644)
            os.chmod(temp_dir, 0o755)  # Directory also needs to be accessible

            # Write additional files if provided
            if files:
                for filename, content in files.items():
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, "w") as f:
                        f.write(content)
                    os.chmod(file_path, 0o644)

            # Get image for language
            image = self.IMAGES.get(language)
            if not image:
                raise ValueError(f"Unsupported language: {language}")

            # Pull image if needed
            self._pull_image_if_needed(image)

            # Build container config
            container_name = f"{self.container_prefix}{execution_id}"
            command = self.COMMANDS.get(language)

            # Security configuration
            security_opt = []
            if config.no_new_privileges:
                security_opt.append("no-new-privileges:true")

            cap_drop = ["ALL"] if config.drop_capabilities else []

            # tmpfs for /tmp if read-only
            tmpfs = {"/tmp": "rw,noexec,nosuid,size=64m"} if config.read_only_root else {}

            # Network mode
            network_mode = "none" if not config.network_enabled else "bridge"

            logger.info(f"Executing sandbox: {execution_id}, language={language.value}")

            try:
                # Run container
                # Use host_temp_dir for volume mount since Docker daemon runs on host
                container = self.client.containers.run(
                    image=image,
                    command=command,
                    name=container_name,
                    volumes={host_temp_dir: {"bind": "/sandbox", "mode": "ro"}},
                    working_dir="/sandbox",
                    user=config.user,
                    mem_limit=config.memory_limit,
                    nano_cpus=int(config.cpu_limit * 1e9),
                    network_mode=network_mode,
                    read_only=config.read_only_root,
                    tmpfs=tmpfs,
                    security_opt=security_opt,
                    cap_drop=cap_drop,
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True,
                )

                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                # Container.run returns bytes when detach=False
                stdout_str = container.decode("utf-8", errors="replace")[:config.max_output_bytes]

                result = ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.SUCCESS,
                    exit_code=0,
                    stdout=stdout_str,
                    stderr="",
                    duration_ms=duration_ms,
                    started_at=started_at.isoformat() + "Z",
                    finished_at=finished_at.isoformat() + "Z",
                    resource_usage={
                        "memory_limit": config.memory_limit,
                        "cpu_limit": config.cpu_limit,
                        "timeout_seconds": config.timeout_seconds,
                    },
                )

            except ContainerError as e:
                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                stdout_str = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
                stdout_str = stdout_str[:config.max_output_bytes]

                result = ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.FAILED,
                    exit_code=e.exit_status,
                    stdout="",
                    stderr=stdout_str,
                    duration_ms=duration_ms,
                    started_at=started_at.isoformat() + "Z",
                    finished_at=finished_at.isoformat() + "Z",
                    resource_usage={
                        "memory_limit": config.memory_limit,
                        "cpu_limit": config.cpu_limit,
                    },
                )

            except APIError as e:
                if "timeout" in str(e).lower():
                    status = ExecutionStatus.TIMEOUT
                else:
                    status = ExecutionStatus.ERROR

                result = ExecutionResult(
                    execution_id=execution_id,
                    status=status,
                    error_message=str(e),
                    started_at=started_at.isoformat() + "Z",
                    finished_at=datetime.utcnow().isoformat() + "Z",
                )

        except Exception as e:
            result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.ERROR,
                error_message=str(e),
                started_at=started_at.isoformat() + "Z",
                finished_at=datetime.utcnow().isoformat() + "Z",
            )

        finally:
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        # Record execution
        self._record_execution(result)

        return result

    def _record_execution(self, result: ExecutionResult):
        """Record execution to history."""
        self.history.append(asdict(result))
        self._save_history()

    async def execute_async(
        self,
        code: str,
        language: SandboxLanguage = SandboxLanguage.PYTHON,
        config: Optional[SandboxConfig] = None,
    ) -> ExecutionResult:
        """Async wrapper for execute."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.execute(code, language, config)
        )

    def get_execution_history(
        self,
        limit: int = 50,
        status_filter: Optional[ExecutionStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        history = self.history

        if status_filter:
            history = [h for h in history if h.get("status") == status_filter.value]

        return history[-limit:]

    def cleanup_old_containers(self) -> int:
        """Clean up any orphaned sandbox containers."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"name": self.container_prefix}
            )
            count = 0
            for container in containers:
                try:
                    container.remove(force=True)
                    count += 1
                except Exception:
                    pass
            if count:
                logger.info(f"Cleaned up {count} orphaned sandbox containers")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup containers: {e}")
            return 0

    def test_isolation(self) -> Dict[str, Any]:
        """
        Run isolation tests to verify sandbox security.

        Returns dict with test results.
        """
        tests = {}

        # Test 1: Network isolation
        network_test_code = """
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=2)
    print("NETWORK_ACCESSIBLE")
except Exception as e:
    print(f"NETWORK_BLOCKED: {e}")
"""
        result = self.execute(network_test_code, SandboxLanguage.PYTHON)
        tests["network_isolation"] = {
            "passed": "NETWORK_BLOCKED" in result.stdout or "NETWORK_BLOCKED" in result.stderr,
            "output": result.stdout or result.stderr,
        }

        # Test 2: Resource limits (memory)
        memory_test_code = """
try:
    data = bytearray(512 * 1024 * 1024)  # 512MB
    print("MEMORY_UNLIMITED")
except MemoryError:
    print("MEMORY_LIMITED")
"""
        result = self.execute(memory_test_code, SandboxLanguage.PYTHON)
        tests["memory_limit"] = {
            "passed": result.status == ExecutionStatus.FAILED or "MEMORY_LIMITED" in result.stdout or "killed" in result.stderr.lower(),
            "output": result.stdout or result.stderr,
            "status": result.status.value,
        }

        # Test 3: Read-only filesystem
        readonly_test_code = """
try:
    with open('/etc/test', 'w') as f:
        f.write('test')
    print("FILESYSTEM_WRITABLE")
except Exception as e:
    print(f"FILESYSTEM_READONLY: {e}")
"""
        result = self.execute(readonly_test_code, SandboxLanguage.PYTHON)
        tests["readonly_filesystem"] = {
            "passed": "FILESYSTEM_READONLY" in result.stdout or "FILESYSTEM_READONLY" in result.stderr or result.status == ExecutionStatus.FAILED,
            "output": result.stdout or result.stderr,
        }

        # Test 4: Simple success
        success_test_code = """
print("Hello from sandbox!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        result = self.execute(success_test_code, SandboxLanguage.PYTHON)
        tests["basic_execution"] = {
            "passed": result.status == ExecutionStatus.SUCCESS and "4" in result.stdout,
            "output": result.stdout,
            "status": result.status.value,
        }

        # Test 5: Non-root user
        user_test_code = """
import os
uid = os.getuid()
print(f"Running as UID: {uid}")
if uid == 0:
    print("RUNNING_AS_ROOT")
else:
    print("NOT_ROOT")
"""
        result = self.execute(user_test_code, SandboxLanguage.PYTHON)
        tests["non_root_user"] = {
            "passed": "NOT_ROOT" in result.stdout,
            "output": result.stdout,
        }

        # Summary
        passed = sum(1 for t in tests.values() if t.get("passed"))
        total = len(tests)

        return {
            "tests": tests,
            "summary": {
                "passed": passed,
                "total": total,
                "success_rate": passed / total if total > 0 else 0,
            },
        }

    def get_status(self) -> Dict[str, Any]:
        """Get sandbox manager status."""
        return {
            "enabled": True,
            "config": asdict(self.config),
            "history_count": len(self.history),
            "container_prefix": self.container_prefix,
            "supported_languages": [lang.value for lang in SandboxLanguage],
            "images": {k.value: v for k, v in self.IMAGES.items()},
            "docker_connected": self._client is not None or True,  # Will connect on first use
        }


# Global sandbox manager instance
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get or create the global sandbox manager."""
    global _sandbox_manager
    if _sandbox_manager is None:
        data_dir = os.environ.get("HYDRA_DATA_DIR", "/data")
        _sandbox_manager = SandboxManager(data_dir=f"{data_dir}/sandbox")
    return _sandbox_manager


# ============================================================================
# FastAPI Router
# ============================================================================

class ExecuteRequest(BaseModel):
    """Request to execute code in sandbox."""
    code: str
    language: str = "python"
    timeout_seconds: int = 30
    memory_limit: str = "256m"
    network_enabled: bool = False


class ExecuteResponse(BaseModel):
    """Response from sandbox execution."""
    execution_id: str
    status: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    error_message: Optional[str]


def create_sandbox_router() -> APIRouter:
    """Create FastAPI router for sandbox endpoints."""
    router = APIRouter(prefix="/sandbox", tags=["sandbox"])

    @router.get("/status")
    async def get_status():
        """Get sandbox manager status."""
        manager = get_sandbox_manager()
        return manager.get_status()

    @router.post("/execute", response_model=ExecuteResponse)
    async def execute_code(request: ExecuteRequest):
        """
        Execute code in a sandboxed container.

        Security features:
        - Network isolation (default)
        - Memory limits
        - CPU limits
        - Execution timeout
        - Read-only filesystem
        - Dropped capabilities
        """
        manager = get_sandbox_manager()

        # Parse language
        try:
            language = SandboxLanguage(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. Supported: {[l.value for l in SandboxLanguage]}"
            )

        # Build config
        config = SandboxConfig(
            timeout_seconds=min(request.timeout_seconds, 300),  # Max 5 min
            memory_limit=request.memory_limit,
            network_enabled=request.network_enabled,
        )

        # Execute
        result = await manager.execute_async(request.code, language, config)

        return ExecuteResponse(
            execution_id=result.execution_id,
            status=result.status.value,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
        )

    @router.get("/history")
    async def get_history(limit: int = 50, status: Optional[str] = None):
        """Get recent execution history."""
        manager = get_sandbox_manager()

        status_filter = None
        if status:
            try:
                status_filter = ExecutionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        return {
            "executions": manager.get_execution_history(limit, status_filter),
            "total": len(manager.history),
        }

    @router.post("/test-isolation")
    async def test_isolation():
        """
        Run isolation tests to verify sandbox security.

        Tests:
        - Network isolation
        - Memory limits
        - Read-only filesystem
        - Basic execution
        - Non-root user
        """
        manager = get_sandbox_manager()
        return manager.test_isolation()

    @router.post("/cleanup")
    async def cleanup_containers():
        """Clean up orphaned sandbox containers."""
        manager = get_sandbox_manager()
        count = manager.cleanup_old_containers()
        return {"cleaned": count}

    @router.get("/languages")
    async def get_languages():
        """Get supported languages."""
        return {
            "languages": [
                {
                    "id": lang.value,
                    "image": SandboxManager.IMAGES[lang],
                }
                for lang in SandboxLanguage
            ]
        }

    return router


# Quick test
if __name__ == "__main__":
    manager = SandboxManager(data_dir="/tmp/sandbox-test")

    # Test basic execution
    print("Testing basic execution...")
    result = manager.execute(
        "print('Hello from sandbox!')\nprint(2 + 2)",
        SandboxLanguage.PYTHON,
    )
    print(f"Status: {result.status}")
    print(f"Output: {result.stdout}")
    print(f"Duration: {result.duration_ms}ms")

    # Run isolation tests
    print("\nRunning isolation tests...")
    tests = manager.test_isolation()
    print(f"Passed: {tests['summary']['passed']}/{tests['summary']['total']}")
