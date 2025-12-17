"""
Unraid GraphQL API Client for Hydra Unified Control Plane

Provides comprehensive access to Unraid server management:
- Array status and operations
- Disk health and SMART data
- Docker container management
- Virtual machine control
- System information and metrics
- User management

Requires: Unraid 7.2+ with API enabled
API Key: Settings -> Management Access -> API Keys
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import httpx
import asyncio

logger = logging.getLogger(__name__)


class UnraidArrayState(str, Enum):
    """Unraid array states"""
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    MAINTENANCE = "MAINTENANCE"


class UnraidContainerState(str, Enum):
    """Docker container states"""
    RUNNING = "running"
    EXITED = "exited"
    PAUSED = "paused"
    RESTARTING = "restarting"
    CREATED = "created"


class UnraidVMState(str, Enum):
    """Virtual machine states"""
    RUNNING = "running"
    PAUSED = "paused"
    SHUT_OFF = "shut off"
    BLOCKED = "blocked"


@dataclass
class DiskInfo:
    """Disk information from Unraid"""
    device: str
    name: str
    size: int
    temperature: Optional[int]
    smart_status: str
    interface_type: str
    spun_down: bool
    smart_attributes: Optional[List[Dict[str, Any]]] = None


@dataclass
class ContainerInfo:
    """Docker container information"""
    id: str
    names: List[str]
    image: str
    state: str
    status: str
    auto_start: bool
    ports: List[Dict[str, Any]]


@dataclass
class VMInfo:
    """Virtual machine information"""
    uuid: str
    name: str
    state: str
    vcpu: int
    memory: int
    autostart: bool


class UnraidClient:
    """
    Comprehensive Unraid GraphQL API client.

    Usage:
        client = UnraidClient(
            base_url="http://192.168.1.244",
            api_key="your-api-key"
        )

        # Get array status
        status = await client.get_array_status()

        # List containers
        containers = await client.get_containers()

        # Restart a container
        await client.restart_container("container-id")
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: float = 30.0
    ):
        """
        Initialize Unraid client.

        Args:
            base_url: Unraid server URL (default from UNRAID_API_URL env)
            api_key: API key for authentication (default from UNRAID_API_KEY env)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("UNRAID_API_URL", "http://192.168.1.244")
        self.api_key = api_key or os.getenv("UNRAID_API_KEY", "")
        self.graphql_url = f"{self.base_url}/graphql"
        self.timeout = timeout

        # Simple monitoring API URL (if installed)
        self.monitoring_url = os.getenv(
            "UNRAID_MONITORING_API_URL",
            f"{self.base_url.replace('http://', 'http://').rsplit(':', 1)[0]}:24940"
        )

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query result data

        Raises:
            Exception: On query failure
        """
        client = await self._get_client()

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = await client.post(self.graphql_url, json=payload)
            response.raise_for_status()

            result = response.json()

            if "errors" in result:
                errors = result["errors"]
                error_msgs = [e.get("message", str(e)) for e in errors]
                raise Exception(f"GraphQL errors: {'; '.join(error_msgs)}")

            return result.get("data", {})

        except httpx.RequestError as e:
            logger.error(f"Unraid API request failed: {e}")
            raise Exception(f"Failed to connect to Unraid API: {e}")

    # =========================================================================
    # ARRAY MANAGEMENT
    # =========================================================================

    async def get_array_status(self) -> Dict[str, Any]:
        """
        Get Unraid array status.

        Returns:
            dict with state, numDisks, numProtected, numUnprotected, parityCheck
        """
        query = """
            query {
                array {
                    state
                    numDisks
                    numProtected
                    numUnprotected
                    parityCheck {
                        status
                        progress
                        errors
                    }
                }
            }
        """
        result = await self._execute_query(query)
        return result.get("array", {})

    async def start_array(self) -> Dict[str, Any]:
        """Start the Unraid array."""
        mutation = """
            mutation {
                arrayStart {
                    state
                }
            }
        """
        result = await self._execute_query(mutation)
        return result.get("arrayStart", {})

    async def stop_array(self) -> Dict[str, Any]:
        """Stop the Unraid array."""
        mutation = """
            mutation {
                arrayStop {
                    state
                }
            }
        """
        result = await self._execute_query(mutation)
        return result.get("arrayStop", {})

    async def start_parity_check(self, correct: bool = False) -> bool:
        """
        Start a parity check.

        Args:
            correct: If True, correct any errors found

        Returns:
            True if parity check started successfully
        """
        mutation = """
            mutation($correct: Boolean!) {
                startParityCheck(correct: $correct)
            }
        """
        result = await self._execute_query(mutation, {"correct": correct})
        return result.get("startParityCheck", False)

    async def pause_parity_check(self) -> bool:
        """Pause the current parity check."""
        mutation = """
            mutation {
                pauseParityCheck
            }
        """
        result = await self._execute_query(mutation)
        return result.get("pauseParityCheck", False)

    async def resume_parity_check(self) -> bool:
        """Resume a paused parity check."""
        mutation = """
            mutation {
                resumeParityCheck
            }
        """
        result = await self._execute_query(mutation)
        return result.get("resumeParityCheck", False)

    async def cancel_parity_check(self) -> bool:
        """Cancel the current parity check."""
        mutation = """
            mutation {
                cancelParityCheck
            }
        """
        result = await self._execute_query(mutation)
        return result.get("cancelParityCheck", False)

    # =========================================================================
    # DISK MANAGEMENT
    # =========================================================================

    async def get_disks(self, include_smart: bool = False) -> List[Dict[str, Any]]:
        """
        Get disk information.

        Args:
            include_smart: Include detailed SMART attributes

        Returns:
            List of disk info dictionaries
        """
        smart_fragment = """
            smartAttributes {
                id
                name
                value
                worst
                threshold
                raw
            }
        """ if include_smart else ""

        query = f"""
            query {{
                disks {{
                    device
                    name
                    size
                    temperature
                    smartStatus
                    interfaceType
                    spundown
                    {smart_fragment}
                }}
            }}
        """
        result = await self._execute_query(query)
        return result.get("disks", [])

    async def get_disk_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of disk health across all disks.

        Returns:
            dict with total_disks, healthy, warning, failed, avg_temperature
        """
        disks = await self.get_disks()

        healthy = sum(1 for d in disks if d.get("smartStatus") == "PASS")
        warning = sum(1 for d in disks if d.get("smartStatus") == "WARNING")
        failed = sum(1 for d in disks if d.get("smartStatus") == "FAIL")

        temps = [d.get("temperature", 0) for d in disks if d.get("temperature")]
        avg_temp = sum(temps) / len(temps) if temps else 0

        return {
            "total_disks": len(disks),
            "healthy": healthy,
            "warning": warning,
            "failed": failed,
            "avg_temperature": round(avg_temp, 1),
            "max_temperature": max(temps) if temps else 0,
            "disks_spinning": sum(1 for d in disks if not d.get("spundown", True))
        }

    # =========================================================================
    # DOCKER CONTAINER MANAGEMENT
    # =========================================================================

    async def get_containers(self) -> List[Dict[str, Any]]:
        """Get all Docker containers."""
        query = """
            query {
                dockerContainers {
                    id
                    names
                    image
                    state
                    status
                    autoStart
                    ports {
                        ip
                        privatePort
                        publicPort
                        type
                    }
                }
            }
        """
        result = await self._execute_query(query)
        return result.get("dockerContainers", [])

    async def get_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific container by ID."""
        containers = await self.get_containers()
        for container in containers:
            if container.get("id") == container_id:
                return container
            # Also check names
            if container_id in container.get("names", []):
                return container
        return None

    async def start_container(self, container_id: str) -> Dict[str, Any]:
        """
        Start a Docker container.

        Args:
            container_id: Container ID or name

        Returns:
            dict with id and state
        """
        mutation = """
            mutation($id: ID!) {
                dockerContainerStart(id: $id) {
                    id
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"id": container_id})
        return result.get("dockerContainerStart", {})

    async def stop_container(self, container_id: str) -> Dict[str, Any]:
        """
        Stop a Docker container.

        Args:
            container_id: Container ID or name

        Returns:
            dict with id and state
        """
        mutation = """
            mutation($id: ID!) {
                dockerContainerStop(id: $id) {
                    id
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"id": container_id})
        return result.get("dockerContainerStop", {})

    async def restart_container(self, container_id: str) -> Dict[str, Any]:
        """
        Restart a Docker container.

        Args:
            container_id: Container ID or name

        Returns:
            dict with id and state
        """
        mutation = """
            mutation($id: ID!) {
                dockerContainerRestart(id: $id) {
                    id
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"id": container_id})
        return result.get("dockerContainerRestart", {})

    async def get_container_stats(self) -> Dict[str, Any]:
        """Get container statistics summary."""
        containers = await self.get_containers()

        running = sum(1 for c in containers if c.get("state") == "running")
        stopped = sum(1 for c in containers if c.get("state") == "exited")

        return {
            "total": len(containers),
            "running": running,
            "stopped": stopped,
            "other": len(containers) - running - stopped
        }

    # =========================================================================
    # VIRTUAL MACHINE MANAGEMENT
    # =========================================================================

    async def get_vms(self) -> List[Dict[str, Any]]:
        """Get all virtual machines."""
        query = """
            query {
                vms {
                    domain {
                        uuid
                        name
                        state
                        vcpu
                        memory
                        autostart
                    }
                }
            }
        """
        result = await self._execute_query(query)
        vms_data = result.get("vms", [])
        # Flatten the domain structure
        return [vm.get("domain", vm) for vm in vms_data if vm]

    async def start_vm(self, vm_uuid: str) -> Dict[str, Any]:
        """Start a virtual machine."""
        mutation = """
            mutation($uuid: ID!) {
                vmStart(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"uuid": vm_uuid})
        return result.get("vmStart", {})

    async def stop_vm(self, vm_uuid: str) -> Dict[str, Any]:
        """Stop a virtual machine."""
        mutation = """
            mutation($uuid: ID!) {
                vmStop(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"uuid": vm_uuid})
        return result.get("vmStop", {})

    async def pause_vm(self, vm_uuid: str) -> Dict[str, Any]:
        """Pause a virtual machine."""
        mutation = """
            mutation($uuid: ID!) {
                vmPause(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"uuid": vm_uuid})
        return result.get("vmPause", {})

    async def resume_vm(self, vm_uuid: str) -> Dict[str, Any]:
        """Resume a paused virtual machine."""
        mutation = """
            mutation($uuid: ID!) {
                vmResume(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """
        result = await self._execute_query(mutation, {"uuid": vm_uuid})
        return result.get("vmResume", {})

    # =========================================================================
    # SYSTEM INFORMATION
    # =========================================================================

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        query = """
            query {
                systemInfo {
                    cpu {
                        model
                        cores
                        threads
                    }
                    memory {
                        total
                        available
                        used
                    }
                    os {
                        version
                        kernel
                    }
                }
            }
        """
        result = await self._execute_query(query)
        return result.get("systemInfo", {})

    async def get_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        query = """
            query {
                notifications {
                    id
                    timestamp
                    subject
                    description
                    importance
                }
            }
        """
        result = await self._execute_query(query)
        notifications = result.get("notifications", [])
        return notifications[:limit]

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    async def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        query = """
            query {
                users {
                    id
                    name
                    description
                    roles
                }
            }
        """
        result = await self._execute_query(query)
        return result.get("users", [])

    # =========================================================================
    # SIMPLE MONITORING API (Optional addon)
    # =========================================================================

    async def get_simple_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get metrics from Unraid Simple Monitoring API (if installed).

        Returns:
            dict with array_total, cache_total, network_total, cpu, memory
            or None if not available
        """
        try:
            client = await self._get_client()
            response = await client.get(self.monitoring_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Simple monitoring API not available: {e}")
            return None

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the Unraid API connection.

        Returns:
            dict with status, response_time_ms, version
        """
        import time

        start = time.time()
        try:
            system_info = await self.get_system_info()
            elapsed = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "response_time_ms": round(elapsed, 2),
                "version": system_info.get("os", {}).get("version", "unknown"),
                "kernel": system_info.get("os", {}).get("kernel", "unknown")
            }
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {
                "status": "unhealthy",
                "response_time_ms": round(elapsed, 2),
                "error": str(e)
            }

    # =========================================================================
    # COMPREHENSIVE METRICS (for dashboard)
    # =========================================================================

    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for dashboard display.

        Returns aggregated data from multiple queries for efficiency.
        """
        # Run queries in parallel
        array_task = asyncio.create_task(self.get_array_status())
        disks_task = asyncio.create_task(self.get_disk_health_summary())
        containers_task = asyncio.create_task(self.get_container_stats())
        system_task = asyncio.create_task(self.get_system_info())
        simple_task = asyncio.create_task(self.get_simple_metrics())

        array, disks, containers, system, simple = await asyncio.gather(
            array_task, disks_task, containers_task, system_task, simple_task,
            return_exceptions=True
        )

        # Handle any errors gracefully
        def safe_result(result, default):
            return result if not isinstance(result, Exception) else default

        return {
            "array": safe_result(array, {}),
            "disks": safe_result(disks, {}),
            "containers": safe_result(containers, {}),
            "system": safe_result(system, {}),
            "metrics": safe_result(simple, None)
        }


# Module-level singleton for dependency injection
_unraid_client: Optional[UnraidClient] = None


def get_unraid_client() -> UnraidClient:
    """
    Get the singleton Unraid client instance.

    Used for FastAPI dependency injection.
    """
    global _unraid_client
    if _unraid_client is None:
        _unraid_client = UnraidClient()
    return _unraid_client


async def close_unraid_client():
    """Close the Unraid client connection."""
    global _unraid_client
    if _unraid_client:
        await _unraid_client.close()
        _unraid_client = None
