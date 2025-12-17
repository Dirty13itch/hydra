"""
Cluster Logs API for Hydra Command Center

Provides REST API endpoints for querying logs from Loki.
Supports filtering by service, level, time range, and text search.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
import re

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

LOKI_URL = os.getenv("LOKI_URL", "http://192.168.1.244:3100")


# =============================================================================
# Data Models
# =============================================================================

class LogEntry(BaseModel):
    timestamp: str
    level: str
    service: str
    message: str
    labels: Dict[str, str] = {}


class LogQueryResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    query: str
    time_range: Dict[str, str]


# =============================================================================
# Loki Client
# =============================================================================

class LokiClient:
    """Client for querying Loki logs."""

    def __init__(self, url: str = None):
        self.url = url or LOKI_URL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_labels(self) -> List[str]:
        """Get available log labels."""
        try:
            response = await self.client.get(f"{self.url}/loki/api/v1/labels")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return []

    async def get_label_values(self, label: str) -> List[str]:
        """Get values for a specific label."""
        try:
            response = await self.client.get(f"{self.url}/loki/api/v1/label/{label}/values")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get label values: {e}")
            return []

    def _parse_log_level(self, message: str) -> str:
        """Extract log level from message."""
        message_lower = message.lower()
        if "error" in message_lower or "err" in message_lower:
            return "ERROR"
        if "warn" in message_lower:
            return "WARN"
        if "debug" in message_lower:
            return "DEBUG"
        if "info" in message_lower:
            return "INFO"
        return "INFO"

    async def query_logs(
        self,
        service: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None,
        hours: int = 1,
        limit: int = 100,
    ) -> LogQueryResponse:
        """Query logs from Loki."""
        # Build LogQL query
        label_selectors = []
        if service:
            # Match service in various label fields
            label_selectors.append(f'container=~".*{service}.*"')

        if label_selectors:
            label_query = ",".join(label_selectors)
            query = f"{{{label_query}}}"
        else:
            query = '{job=~".+"}'

        # Add line filters
        line_filters = []
        if level:
            line_filters.append(f"|~ \"(?i){level}\"")
        if search:
            line_filters.append(f"|~ \"(?i){search}\"")

        if line_filters:
            query += " " + " ".join(line_filters)

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        start_ns = int(start_time.timestamp() * 1e9)
        end_ns = int(end_time.timestamp() * 1e9)

        try:
            response = await self.client.get(
                f"{self.url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(start_ns),
                    "end": str(end_ns),
                    "limit": limit,
                    "direction": "backward",  # Most recent first
                },
            )
            response.raise_for_status()
            data = response.json()

            logs = []
            results = data.get("data", {}).get("result", [])

            for stream in results:
                labels = stream.get("stream", {})
                service_name = labels.get("container", labels.get("service", labels.get("job", "unknown")))

                for value in stream.get("values", []):
                    timestamp_ns, message = value
                    timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)

                    logs.append(LogEntry(
                        timestamp=timestamp.isoformat(),
                        level=self._parse_log_level(message),
                        service=service_name,
                        message=message[:500],  # Truncate long messages
                        labels=labels,
                    ))

            # Sort by timestamp descending
            logs.sort(key=lambda x: x.timestamp, reverse=True)

            return LogQueryResponse(
                logs=logs[:limit],
                total=len(logs),
                query=query,
                time_range={
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                },
            )

        except Exception as e:
            logger.error(f"Failed to query logs: {e}")
            return LogQueryResponse(
                logs=[],
                total=0,
                query=query,
                time_range={
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                },
            )

    async def get_services(self) -> List[str]:
        """Get list of services with logs."""
        containers = await self.get_label_values("container")
        services = await self.get_label_values("service")
        # Combine and deduplicate
        all_services = list(set(containers + services))
        return sorted(all_services)

    async def check_health(self) -> Dict[str, Any]:
        """Check Loki health status."""
        try:
            response = await self.client.get(f"{self.url}/ready")
            is_ready = response.status_code == 200 and response.text.strip() == "ready"
            return {
                "status": "healthy" if is_ready else "unhealthy",
                "url": self.url,
                "ready": is_ready,
            }
        except Exception as e:
            return {
                "status": "error",
                "url": self.url,
                "error": str(e),
            }


# =============================================================================
# Global Instance
# =============================================================================

_loki_client: Optional[LokiClient] = None


def get_loki_client() -> LokiClient:
    """Get or create Loki client."""
    global _loki_client
    if _loki_client is None:
        _loki_client = LokiClient()
    return _loki_client


# =============================================================================
# FastAPI Router
# =============================================================================

def create_logs_router() -> APIRouter:
    """Create FastAPI router for logs endpoints."""
    router = APIRouter(prefix="/logs", tags=["logs"])

    @router.get("/health")
    async def get_health():
        """Get Loki health status."""
        client = get_loki_client()
        return await client.check_health()

    @router.get("/services")
    async def get_services():
        """Get list of services with logs."""
        client = get_loki_client()
        services = await client.get_services()
        return {"services": services}

    @router.get("/query")
    async def query_logs(
        service: Optional[str] = Query(None, description="Filter by service/container name"),
        level: Optional[str] = Query(None, description="Filter by log level (INFO, WARN, ERROR, DEBUG)"),
        search: Optional[str] = Query(None, description="Text search in log messages"),
        hours: int = Query(1, ge=1, le=168, description="Hours of logs to fetch (1-168)"),
        limit: int = Query(100, ge=10, le=1000, description="Maximum number of logs to return"),
    ):
        """Query logs from Loki."""
        client = get_loki_client()
        return await client.query_logs(
            service=service,
            level=level,
            search=search,
            hours=hours,
            limit=limit,
        )

    @router.get("/labels")
    async def get_labels():
        """Get available log labels."""
        client = get_loki_client()
        labels = await client.get_labels()
        return {"labels": labels}

    @router.get("/labels/{label}/values")
    async def get_label_values(label: str):
        """Get values for a specific label."""
        client = get_loki_client()
        values = await client.get_label_values(label)
        return {"label": label, "values": values}

    return router


if __name__ == "__main__":
    import asyncio

    async def test():
        client = LokiClient()

        # Test health
        health = await client.check_health()
        print("Health:", health)

        # Test services
        services = await client.get_services()
        print("\nServices:", services)

        # Test query
        result = await client.query_logs(hours=1, limit=10)
        print(f"\nQuery result: {result.total} logs")
        for log in result.logs[:3]:
            print(f"  [{log.level}] {log.service}: {log.message[:50]}...")

        await client.close()

    asyncio.run(test())
