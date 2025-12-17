"""
Unraid Management Router - REST API endpoints for Unraid server control.

Provides endpoints for:
- Array management (status, start, stop, parity checks)
- Disk health and SMART data
- Docker container control (start, stop, restart)
- Virtual machine management
- System information
- Comprehensive metrics

All endpoints wrap the Unraid GraphQL API for REST access.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from hydra_tools.clients.unraid_client import UnraidClient, get_unraid_client

router = APIRouter(prefix="/api/v1/unraid", tags=["unraid"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ArrayStatus(BaseModel):
    state: str
    numDisks: int = 0
    numProtected: int = 0
    numUnprotected: int = 0
    parityCheck: Optional[Dict[str, Any]] = None


class DiskHealthSummary(BaseModel):
    total_disks: int
    healthy: int
    warning: int
    failed: int
    avg_temperature: float
    max_temperature: int
    disks_spinning: int


class ContainerStats(BaseModel):
    total: int
    running: int
    stopped: int
    other: int


class ContainerAction(BaseModel):
    id: str
    state: str


class ParityCheckRequest(BaseModel):
    correct: bool = False


class HealthCheck(BaseModel):
    status: str
    response_time_ms: float
    version: Optional[str] = None
    kernel: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", response_model=HealthCheck)
async def unraid_health_check(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Check Unraid API connectivity and health.

    Returns connection status, response time, and Unraid version.
    """
    return await client.health_check()


# =============================================================================
# ARRAY ENDPOINTS
# =============================================================================

@router.get("/array/status", response_model=ArrayStatus)
async def get_array_status(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Get Unraid array status.

    Returns array state, disk counts, and parity check progress.
    """
    try:
        return await client.get_array_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/start")
async def start_array(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Start the Unraid array.

    Requires array to be in STOPPED state.
    """
    try:
        result = await client.start_array()
        return {"status": "success", "array": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/stop")
async def stop_array(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Stop the Unraid array.

    WARNING: This will stop all array-dependent services.
    """
    try:
        result = await client.stop_array()
        return {"status": "success", "array": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/parity-check")
async def start_parity_check(
    request: ParityCheckRequest,
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Start a parity check.

    Args:
        correct: If true, correct any errors found (correcting check)
    """
    try:
        success = await client.start_parity_check(correct=request.correct)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start parity check")
        return {
            "status": "started",
            "correcting": request.correct,
            "message": "Parity check started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/parity-check/pause")
async def pause_parity_check(
    client: UnraidClient = Depends(get_unraid_client)
):
    """Pause the current parity check."""
    try:
        success = await client.pause_parity_check()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to pause parity check")
        return {"status": "paused"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/parity-check/resume")
async def resume_parity_check(
    client: UnraidClient = Depends(get_unraid_client)
):
    """Resume a paused parity check."""
    try:
        success = await client.resume_parity_check()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to resume parity check")
        return {"status": "resumed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/array/parity-check/cancel")
async def cancel_parity_check(
    client: UnraidClient = Depends(get_unraid_client)
):
    """Cancel the current parity check."""
    try:
        success = await client.cancel_parity_check()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel parity check")
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DISK ENDPOINTS
# =============================================================================

@router.get("/disks")
async def get_disks(
    include_smart: bool = Query(False, description="Include detailed SMART attributes"),
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Get all disk information.

    Args:
        include_smart: Include detailed SMART attributes for each disk
    """
    try:
        return await client.get_disks(include_smart=include_smart)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disks/health", response_model=DiskHealthSummary)
async def get_disk_health(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Get disk health summary.

    Returns aggregated health status across all disks.
    """
    try:
        return await client.get_disk_health_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOCKER CONTAINER ENDPOINTS
# =============================================================================

@router.get("/containers")
async def list_containers(
    client: UnraidClient = Depends(get_unraid_client)
):
    """List all Docker containers on Unraid."""
    try:
        return await client.get_containers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/stats", response_model=ContainerStats)
async def get_container_stats(
    client: UnraidClient = Depends(get_unraid_client)
):
    """Get container statistics summary."""
    try:
        return await client.get_container_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_id}")
async def get_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Get a specific container by ID or name."""
    try:
        container = await client.get_container(container_id)
        if not container:
            raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
        return container
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_id}/start", response_model=ContainerAction)
async def start_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Start a Docker container."""
    try:
        result = await client.start_container(container_id)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to start container")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_id}/stop", response_model=ContainerAction)
async def stop_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Stop a Docker container."""
    try:
        result = await client.stop_container(container_id)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to stop container")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_id}/restart", response_model=ContainerAction)
async def restart_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Restart a Docker container."""
    try:
        result = await client.restart_container(container_id)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to restart container")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VIRTUAL MACHINE ENDPOINTS
# =============================================================================

@router.get("/vms")
async def list_vms(
    client: UnraidClient = Depends(get_unraid_client)
):
    """List all virtual machines."""
    try:
        return await client.get_vms()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vms/{vm_uuid}/start")
async def start_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Start a virtual machine."""
    try:
        result = await client.start_vm(vm_uuid)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to start VM")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vms/{vm_uuid}/stop")
async def stop_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Stop a virtual machine."""
    try:
        result = await client.stop_vm(vm_uuid)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to stop VM")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vms/{vm_uuid}/pause")
async def pause_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Pause a virtual machine."""
    try:
        result = await client.pause_vm(vm_uuid)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to pause VM")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vms/{vm_uuid}/resume")
async def resume_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Resume a paused virtual machine."""
    try:
        result = await client.resume_vm(vm_uuid)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to resume VM")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@router.get("/system/info")
async def get_system_info(
    client: UnraidClient = Depends(get_unraid_client)
):
    """Get Unraid system information (CPU, memory, OS)."""
    try:
        return await client.get_system_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications")
async def get_notifications(
    limit: int = Query(20, ge=1, le=100, description="Maximum notifications to return"),
    client: UnraidClient = Depends(get_unraid_client)
):
    """Get recent Unraid notifications."""
    try:
        return await client.get_notifications(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def list_users(
    client: UnraidClient = Depends(get_unraid_client)
):
    """List all Unraid users."""
    try:
        return await client.list_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPREHENSIVE METRICS (Dashboard endpoint)
# =============================================================================

@router.get("/metrics")
async def get_comprehensive_metrics(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Get comprehensive metrics for dashboard display.

    Returns aggregated data from array, disks, containers, and system.
    Efficient single endpoint for dashboard refresh.
    """
    try:
        return await client.get_comprehensive_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/simple")
async def get_simple_metrics(
    client: UnraidClient = Depends(get_unraid_client)
):
    """
    Get metrics from Unraid Simple Monitoring API (if installed).

    Returns null if the Simple Monitoring API is not installed.
    """
    try:
        metrics = await client.get_simple_metrics()
        if metrics is None:
            return {"status": "unavailable", "message": "Simple Monitoring API not installed"}
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
