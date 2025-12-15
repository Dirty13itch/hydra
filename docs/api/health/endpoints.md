# Health API Endpoints

The Hydra Health Aggregator provides unified health monitoring for all cluster services.

## Base URL

```
http://192.168.1.244:8600
```

## Endpoints

### GET /health

Complete cluster health status.

**Response:**

```json
{
  "summary": {
    "status": "healthy",
    "healthy": 18,
    "unhealthy": 0,
    "degraded": 1,
    "unknown": 0,
    "total": 19,
    "critical_down": [],
    "timestamp": "2025-12-13T10:30:00Z"
  },
  "services": [
    {
      "service": "TabbyAPI",
      "status": "healthy",
      "latency_ms": 12.5,
      "message": null,
      "node": "hydra-ai",
      "category": "inference",
      "critical": true,
      "timestamp": "2025-12-13T10:30:00Z"
    }
  ],
  "nodes": {
    "hydra-ai": {"healthy": 2, "unhealthy": 0, "total": 2},
    "hydra-compute": {"healthy": 2, "unhealthy": 0, "total": 2},
    "hydra-storage": {"healthy": 14, "unhealthy": 0, "total": 15}
  },
  "categories": {
    "inference": {"healthy": 4, "unhealthy": 0, "total": 4},
    "database": {"healthy": 4, "unhealthy": 0, "total": 4}
  }
}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh` | bool | false | Force cache refresh |

### GET /health/summary

Health summary only (smaller response).

**Response:**

```json
{
  "status": "healthy",
  "healthy": 18,
  "unhealthy": 0,
  "degraded": 1,
  "unknown": 0,
  "total": 19,
  "critical_down": [],
  "timestamp": "2025-12-13T10:30:00Z"
}
```

### GET /health/services

List individual service health.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | str | null | Filter by category |
| `node` | str | null | Filter by node |
| `status` | str | null | Filter by status |
| `refresh` | bool | false | Force cache refresh |

**Example:**

```bash
# Get unhealthy services only
curl "http://192.168.1.244:8600/health/services?status=unhealthy"

# Get inference services
curl "http://192.168.1.244:8600/health/services?category=inference"
```

### GET /health/service/{name}

Health for a specific service.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Service name (case-insensitive) |

**Example:**

```bash
curl "http://192.168.1.244:8600/health/service/tabbyapi"
```

**Response:**

```json
{
  "service": "TabbyAPI",
  "status": "healthy",
  "latency_ms": 12.5,
  "message": null,
  "node": "hydra-ai",
  "category": "inference",
  "critical": true,
  "timestamp": "2025-12-13T10:30:00Z"
}
```

### GET /health/nodes

Health grouped by node.

**Response:**

```json
{
  "hydra-ai": {
    "healthy": 2,
    "unhealthy": 0,
    "total": 2
  },
  "hydra-compute": {
    "healthy": 2,
    "unhealthy": 0,
    "total": 2
  },
  "hydra-storage": {
    "healthy": 14,
    "unhealthy": 1,
    "total": 15
  }
}
```

### GET /health/categories

Health grouped by category.

**Response:**

```json
{
  "inference": {"healthy": 4, "unhealthy": 0, "total": 4},
  "database": {"healthy": 4, "unhealthy": 0, "total": 4},
  "observability": {"healthy": 3, "unhealthy": 0, "total": 3},
  "automation": {"healthy": 3, "unhealthy": 0, "total": 3},
  "ui": {"healthy": 3, "unhealthy": 0, "total": 3},
  "media": {"healthy": 3, "unhealthy": 0, "total": 3}
}
```

### GET /ready

Kubernetes-style readiness probe.

**Response (200):**

```json
{"status": "ready"}
```

**Response (503):**

```json
{"detail": "Cluster unhealthy"}
```

### GET /live

Kubernetes-style liveness probe.

**Response:**

```json
{"status": "alive"}
```

## Status Values

| Status | Description |
|--------|-------------|
| `healthy` | Service responding normally |
| `degraded` | Service responding but with issues |
| `unhealthy` | Service not responding or errors |
| `unknown` | Cannot determine status |

## Categories

| Category | Services |
|----------|----------|
| `inference` | TabbyAPI, Ollama, LiteLLM, ComfyUI |
| `database` | PostgreSQL, Qdrant, Redis, Meilisearch |
| `observability` | Prometheus, Grafana, Loki |
| `automation` | n8n, SearXNG, Firecrawl |
| `ui` | Open WebUI, Perplexica, SillyTavern |
| `media` | Sonarr, Radarr, Prowlarr |

## Caching

- Results are cached for 30 seconds
- Use `?refresh=true` to force fresh check
- Cache is per-endpoint

## Usage Examples

### Python

```python
import httpx

# Get cluster health
response = httpx.get("http://192.168.1.244:8600/health")
health = response.json()

if health["summary"]["status"] != "healthy":
    print(f"Critical services down: {health['summary']['critical_down']}")
```

### Bash

```bash
# Quick health check
curl -s http://192.168.1.244:8600/health/summary | jq '.status'

# Check specific service
curl -s http://192.168.1.244:8600/health/service/tabbyapi | jq '.latency_ms'
```

### Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hydra-health'
    metrics_path: /health
    static_configs:
      - targets: ['192.168.1.244:8600']
```
