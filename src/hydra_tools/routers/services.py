"""
Unified Services Router

Merges Homepage services.yaml with live health data from /health/cluster
to provide a single pane of glass for all cluster services.

Endpoints:
- GET /services/unified - All services with live health status
- GET /services/config - Parsed Homepage configuration
- GET /services/categories - Available service categories
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum

import httpx
import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


# Configuration
HOMEPAGE_SERVICES_PATH = os.getenv(
    "HOMEPAGE_SERVICES_PATH",
    "/mnt/user/appdata/hydra-stack/homepage/services.yaml"
)
HEALTH_API_URL = os.getenv("HEALTH_API_URL", "http://127.0.0.1:8700")

# Cache for parsed services
_services_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 30

# Embedded Homepage services (fallback if YAML not accessible)
EMBEDDED_HOMEPAGE_SERVICES = [
    {"category": "AI Chat & LLMs", "services": [
        {"name": "Open WebUI", "href": "http://192.168.1.250:3000", "description": "Chat interface for LLMs", "icon": "openai.svg"},
        {"name": "SillyTavern", "href": "http://192.168.1.244:8000", "description": "Character roleplay with uncensored models", "icon": "si-openai"},
        {"name": "TabbyAPI", "href": "http://192.168.1.250:5000/docs", "description": "70B Uncensored LLM API (Midnight-Miqu)", "icon": "si-api"},
        {"name": "Ollama", "href": "http://192.168.1.203:11434", "description": "Additional models on hydra-compute", "icon": "ollama.svg"},
    ]},
    {"category": "Image Generation", "services": [
        {"name": "ComfyUI", "href": "http://192.168.1.203:8188", "description": "Stable Diffusion XL - 6 models available", "icon": "si-stable-diffusion"},
        {"name": "Stash", "href": "http://192.168.1.244:9999", "description": "Adult content library & organization", "icon": "stash.svg"},
    ]},
    {"category": "Media & Entertainment", "services": [
        {"name": "Plex", "href": "http://192.168.1.244:32400/web", "description": "Media streaming server", "icon": "plex.svg"},
        {"name": "Sonarr", "href": "http://192.168.1.244:8989", "description": "TV show management", "icon": "sonarr.svg"},
        {"name": "Radarr", "href": "http://192.168.1.244:7878", "description": "Movie management", "icon": "radarr.svg"},
        {"name": "Lidarr", "href": "http://192.168.1.244:8686", "description": "Music management", "icon": "lidarr.svg"},
    ]},
    {"category": "Downloads", "services": [
        {"name": "qBittorrent", "href": "http://192.168.1.244:8082", "description": "Torrent client", "icon": "qbittorrent.svg"},
        {"name": "SABnzbd", "href": "http://192.168.1.244:8085", "description": "Usenet downloader", "icon": "sabnzbd.svg"},
        {"name": "Prowlarr", "href": "http://192.168.1.244:9696", "description": "Indexer management", "icon": "prowlarr.svg"},
    ]},
    {"category": "Automation & Tools", "services": [
        {"name": "n8n", "href": "http://192.168.1.244:5678", "description": "Workflow automation", "icon": "n8n.svg"},
        {"name": "Home Assistant", "href": "http://192.168.1.244:8123", "description": "Smart home control", "icon": "home-assistant.svg"},
        {"name": "Perplexica", "href": "http://192.168.1.244:3030", "description": "AI-powered search", "icon": "si-perplexity"},
        {"name": "SearXNG", "href": "http://192.168.1.244:8888", "description": "Privacy search engine", "icon": "searxng.svg"},
    ]},
    {"category": "Monitoring", "services": [
        {"name": "Grafana", "href": "http://192.168.1.244:3003", "description": "Metrics & dashboards", "icon": "grafana.svg"},
        {"name": "Portainer", "href": "http://192.168.1.244:9000", "description": "Docker management", "icon": "portainer.svg"},
        {"name": "Prometheus", "href": "http://192.168.1.244:9090", "description": "Metrics collection", "icon": "prometheus.svg"},
    ]},
    {"category": "Infrastructure", "services": [
        {"name": "AdGuard DNS", "href": "http://192.168.1.244:3053", "description": "DNS & ad blocking", "icon": "adguard-home.svg"},
        {"name": "Miniflux", "href": "http://192.168.1.244:8083", "description": "RSS reader", "icon": "miniflux.svg"},
    ]},
]


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceSource(str, Enum):
    HYDRA = "hydra"  # Monitored by Hydra health checks
    HOMEPAGE = "homepage"  # Static from Homepage config


class Service(BaseModel):
    """Unified service representation."""
    id: str
    name: str
    category: str
    url: str
    icon: Optional[str] = None
    description: Optional[str] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    latency_ms: Optional[float] = None
    source: ServiceSource
    node: str = "hydra-storage"


class UnifiedServicesResponse(BaseModel):
    """Response from /services/unified."""
    services: List[Service]
    categories: List[str]
    counts: Dict[str, int]
    timestamp: str


class ServiceConfigResponse(BaseModel):
    """Response from /services/config."""
    services: List[Dict[str, Any]]
    source_path: str
    parsed_at: str


def _parse_homepage_services() -> List[Dict[str, Any]]:
    """Parse Homepage services.yaml into normalized format."""
    global _services_cache, _cache_timestamp

    # Check cache
    now = datetime.utcnow()
    if _cache_timestamp and (now - _cache_timestamp).total_seconds() < CACHE_TTL_SECONDS:
        if "homepage_services" in _services_cache:
            return _services_cache["homepage_services"]

    services = []
    data = None

    # Try to load from YAML file first
    try:
        if Path(HOMEPAGE_SERVICES_PATH).exists():
            with open(HOMEPAGE_SERVICES_PATH, "r") as f:
                data = yaml.safe_load(f)
    except Exception as e:
        print(f"Could not read Homepage YAML: {e}")

    # Fall back to embedded config if YAML not available
    if not data:
        data = [{cat["category"]: {s["name"]: s for s in cat["services"]}} for cat in EMBEDDED_HOMEPAGE_SERVICES]

    if not isinstance(data, list):
        # Use embedded fallback
        data = [{cat["category"]: {s["name"]: s for s in cat["services"]}} for cat in EMBEDDED_HOMEPAGE_SERVICES]

    for category_block in data:
        if not isinstance(category_block, dict):
            continue

        for category_name, service_list in category_block.items():
            if not isinstance(service_list, dict):
                continue

            for service_name, config in service_list.items():
                if not isinstance(config, dict):
                    continue

                service_id = service_name.lower().replace(" ", "-").replace("_", "-")

                # Extract node from URL
                url = config.get("href", "")
                node = "hydra-storage"
                if "192.168.1.250" in url:
                    node = "hydra-ai"
                elif "192.168.1.203" in url:
                    node = "hydra-compute"

                services.append({
                    "id": service_id,
                    "name": service_name,
                    "category": _normalize_category(category_name),
                    "url": url,
                    "icon": config.get("icon"),
                    "description": config.get("description"),
                    "node": node,
                })

    # Update cache
    _services_cache["homepage_services"] = services
    _cache_timestamp = now

    return services


def _normalize_category(category: str) -> str:
    """Normalize category names."""
    category_map = {
        "AI Chat & LLMs": "inference",
        "Image Generation": "inference",
        "Media & Entertainment": "media",
        "Downloads": "downloads",
        "Automation & Tools": "automation",
        "Monitoring": "observability",
        "Infrastructure": "infrastructure",
    }
    return category_map.get(category, category.lower().replace(" ", "_"))


async def _get_health_data() -> Dict[str, Dict[str, Any]]:
    """Fetch live health data from /health/cluster."""
    health_map = {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{HEALTH_API_URL}/health/cluster")
            if resp.status_code == 200:
                data = resp.json()
                for svc in data.get("services", []):
                    service_name = svc.get("service", "")
                    # Create multiple lookup keys for matching
                    # Original name, lowercase with hyphens, and just lowercase
                    svc_id = service_name.lower().replace(" ", "-")
                    svc_id_alt = service_name.lower().replace(" ", "")

                    health_info = {
                        "status": ServiceStatus.HEALTHY if svc.get("status") == "healthy" else ServiceStatus.UNHEALTHY,
                        "latency_ms": svc.get("latency_ms"),
                        "node": svc.get("node", "hydra-storage"),
                        "category": svc.get("category", "unknown"),
                        "original_name": service_name,
                    }
                    health_map[svc_id] = health_info
                    health_map[svc_id_alt] = health_info  # Alternative key
    except Exception as e:
        print(f"Error fetching health data: {e}")

    return health_map


def create_services_router() -> APIRouter:
    """Create the unified services router."""
    router = APIRouter(prefix="/services", tags=["services"])

    @router.get("/unified", response_model=UnifiedServicesResponse)
    async def get_unified_services():
        """
        Get all services with unified health status.

        Merges:
        - Homepage services.yaml (static config: name, url, icon)
        - /health/cluster (live health: status, latency)

        Returns services organized by category with real-time status.
        """
        # Parse Homepage config
        homepage_services = _parse_homepage_services()

        # Get live health data
        health_data = await _get_health_data()

        # Build unified service list
        services = []
        seen_ids = set()

        # First, add all Homepage services with health overlay
        for svc in homepage_services:
            svc_id = svc["id"]
            seen_ids.add(svc_id)

            # Try multiple ID variations to find health data
            # e.g., "open-webui", "openwebui", original name
            svc_id_nohyphen = svc_id.replace("-", "")
            health = health_data.get(svc_id) or health_data.get(svc_id_nohyphen) or {}

            # Mark these IDs as seen to avoid duplicates
            if health:
                seen_ids.add(svc_id_nohyphen)

            service = Service(
                id=svc_id,
                name=svc["name"],
                category=svc["category"],
                url=svc["url"],
                icon=svc.get("icon"),
                description=svc.get("description"),
                status=health.get("status", ServiceStatus.UNKNOWN),
                latency_ms=health.get("latency_ms"),
                source=ServiceSource.HYDRA if health else ServiceSource.HOMEPAGE,
                node=health.get("node", svc.get("node", "hydra-storage")),
            )
            services.append(service)

        # Add any Hydra-monitored services not in Homepage (avoid duplicates)
        added_health_names = set()
        for svc_id, health in health_data.items():
            original_name = health.get("original_name", "")
            # Skip if we've already processed this service or its variations
            if svc_id in seen_ids or original_name in added_health_names:
                continue
            added_health_names.add(original_name)

            # Infer name from original or ID
            name = original_name if original_name else svc_id.replace("-", " ").title()

            service = Service(
                id=svc_id,
                name=name,
                category=health.get("category", "infrastructure"),
                url=f"http://192.168.1.244:8700",  # Default to API
                status=health.get("status", ServiceStatus.UNKNOWN),
                latency_ms=health.get("latency_ms"),
                source=ServiceSource.HYDRA,
                node=health.get("node", "hydra-storage"),
            )
            services.append(service)
            seen_ids.add(svc_id)

        # Sort by category, then name
        services.sort(key=lambda s: (s.category, s.name))

        # Build response
        categories = sorted(set(s.category for s in services))
        counts = {
            "total": len(services),
            "healthy": sum(1 for s in services if s.status == ServiceStatus.HEALTHY),
            "unhealthy": sum(1 for s in services if s.status == ServiceStatus.UNHEALTHY),
            "unknown": sum(1 for s in services if s.status == ServiceStatus.UNKNOWN),
        }

        return UnifiedServicesResponse(
            services=services,
            categories=categories,
            counts=counts,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    @router.get("/config", response_model=ServiceConfigResponse)
    async def get_services_config():
        """
        Get raw parsed Homepage services configuration.

        Returns the parsed services.yaml without health data overlay.
        """
        services = _parse_homepage_services()

        return ServiceConfigResponse(
            services=services,
            source_path=HOMEPAGE_SERVICES_PATH,
            parsed_at=datetime.utcnow().isoformat() + "Z",
        )

    @router.get("/categories")
    async def get_categories():
        """
        Get available service categories.

        Returns list of categories and service counts per category.
        """
        homepage_services = _parse_homepage_services()
        health_data = await _get_health_data()

        # Combine categories from both sources
        categories = {}

        for svc in homepage_services:
            cat = svc["category"]
            if cat not in categories:
                categories[cat] = {"name": cat, "count": 0, "healthy": 0}
            categories[cat]["count"] += 1

            # Check health
            svc_id = svc["id"]
            if svc_id in health_data:
                if health_data[svc_id].get("status") == ServiceStatus.HEALTHY:
                    categories[cat]["healthy"] += 1

        return {
            "categories": list(categories.values()),
            "total_categories": len(categories),
        }

    @router.get("/by-category/{category}")
    async def get_services_by_category(category: str):
        """
        Get services filtered by category.

        Returns only services in the specified category with health status.
        """
        # Get all unified services
        all_services = await get_unified_services()

        # Filter by category
        filtered = [s for s in all_services.services if s.category == category]

        if not filtered:
            raise HTTPException(
                status_code=404,
                detail=f"No services found in category: {category}"
            )

        return {
            "category": category,
            "services": filtered,
            "count": len(filtered),
        }

    @router.get("/by-node/{node}")
    async def get_services_by_node(node: str):
        """
        Get services filtered by cluster node.

        Returns only services running on the specified node.
        """
        # Get all unified services
        all_services = await get_unified_services()

        # Filter by node
        filtered = [s for s in all_services.services if s.node == node]

        return {
            "node": node,
            "services": filtered,
            "count": len(filtered),
        }

    @router.get("/health-summary")
    async def get_health_summary():
        """
        Get aggregated health summary across all services.

        Quick overview of system health without full service details.
        """
        health_data = await _get_health_data()
        homepage_count = len(_parse_homepage_services())

        monitored = len(health_data)
        healthy = sum(1 for h in health_data.values() if h.get("status") == ServiceStatus.HEALTHY)

        return {
            "homepage_services": homepage_count,
            "monitored_services": monitored,
            "healthy": healthy,
            "unhealthy": monitored - healthy,
            "unmonitored": homepage_count - monitored if homepage_count > monitored else 0,
            "health_percentage": round(healthy / monitored * 100, 1) if monitored > 0 else 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @router.get("/stream")
    async def stream_service_updates():
        """
        Server-Sent Events stream for real-time service status updates.

        Pushes updates every 10 seconds with current service health status.
        Clients can use EventSource to subscribe to this stream.
        """
        async def generate_events() -> AsyncGenerator[str, None]:
            """Generate SSE events with service status updates."""
            try:
                while True:
                    # Get current health data
                    health_data = await _get_health_data()
                    homepage_services = _parse_homepage_services()

                    # Build status update
                    total = len(homepage_services)
                    monitored = len(health_data)
                    healthy = sum(1 for h in health_data.values() if h.get("status") == ServiceStatus.HEALTHY)

                    # Get individual service statuses for changed detection
                    service_statuses = {}
                    for svc in homepage_services:
                        svc_id = svc["id"]
                        svc_id_nohyphen = svc_id.replace("-", "")
                        health = health_data.get(svc_id) or health_data.get(svc_id_nohyphen) or {}
                        status = health.get("status", ServiceStatus.UNKNOWN)
                        latency = health.get("latency_ms")
                        service_statuses[svc_id] = {
                            "status": status.value if hasattr(status, 'value') else str(status),
                            "latency_ms": latency,
                        }

                    event_data = {
                        "type": "status_update",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "summary": {
                            "total": total,
                            "monitored": monitored,
                            "healthy": healthy,
                            "unhealthy": monitored - healthy,
                            "health_percentage": round(healthy / monitored * 100, 1) if monitored > 0 else 0,
                        },
                        "services": service_statuses,
                    }

                    # SSE format: "data: <json>\n\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    # Wait 10 seconds before next update
                    await asyncio.sleep(10)

            except asyncio.CancelledError:
                # Client disconnected
                pass
            except Exception as e:
                # Send error event
                error_data = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    return router
