# Hydra Tools - API Routers
"""
FastAPI routers for the Hydra Unified Control Plane:
- Unraid management (arrays, disks, containers, VMs)
- SSE event streaming
- Infrastructure metrics
"""

from .unraid import router as unraid_router
from .events import router as events_router

__all__ = ['unraid_router', 'events_router']
