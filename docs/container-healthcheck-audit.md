# Container Health Check Audit

Generated: December 14, 2025
Auditor: Hydra Autonomous Steward

## Executive Summary

This audit reviews health check configurations across all Hydra cluster containers. The goal is to ensure proper monitoring, automatic recovery, and early detection of issues.

## Current State

### Containers with Health Checks (Verified)

| Container | Check Type | Endpoint/Command | Interval | Notes |
|-----------|------------|------------------|----------|-------|
| hydra-postgres | pg_isready | `pg_isready -U hydra` | 30s | Correct |
| hydra-redis | redis-cli ping | `redis-cli -a <pass> ping` | 30s | Correct |
| hydra-qdrant | HTTP | `/health` | 30s | Correct |
| hydra-meilisearch | HTTP | `/health` | 30s | Correct |
| hydra-prometheus | HTTP | `/-/healthy` | 30s | Correct |
| hydra-grafana | HTTP | `/api/health` | 30s | Correct |
| hydra-loki | HTTP | `/ready` | 30s | Correct |
| hydra-litellm | HTTP | `/health` | 30s | Correct |
| hydra-n8n | HTTP | `/healthz` | 30s | Correct |

### Containers Requiring Health Check Addition

These containers are defined in `healthchecks-additions.yml`:

| Container | Recommended Check | Status |
|-----------|-------------------|--------|
| hydra-letta | HTTP `/health` | Pending deployment |
| letta-db | `pg_isready -U letta` | Pending deployment |
| letta-proxy | Python urllib | Pending deployment |
| hydra-alertmanager | HTTP `/-/healthy` | Pending deployment |
| hydra-uptime-kuma | HTTP `/` | Pending deployment |
| hydra-crewai | HTTP `/health` | Pending deployment |
| hydra-mcp | HTTP `/health` | Pending deployment |
| hydra-neo4j | HTTP port 7474 | Pending deployment |
| homepage | HTTP `/` | Pending deployment |
| open-webui | HTTP `/health` | Pending deployment |
| hydra-searxng | HTTP `/healthz` | Pending deployment |
| Plex-Media-Server | HTTP `/identity` | Pending deployment |
| stash | HTTP `/` | Pending deployment |
| hydra-watchtower | Process check | Pending deployment |

### Media Stack Containers

| Container | Current Check | Recommendation |
|-----------|---------------|----------------|
| radarr | None | Add HTTP `/api/health` |
| sonarr | None | Add HTTP `/api/health` |
| lidarr | None | Add HTTP `/api/health` |
| prowlarr | None | Add HTTP `/ping` |
| bazarr | None | Add HTTP `/api/systemstatus` |
| qbittorrent | None | Add HTTP `/api/v2/app/version` |
| sabnzbd | None | Add HTTP `/api?mode=version` |

## Health Check Best Practices

### Timing Guidelines

```yaml
# Fast services (databases, caches)
interval: 30s
timeout: 10s
retries: 3
start_period: 30s

# Slow services (AI models, complex apps)
interval: 60s
timeout: 15s
retries: 3
start_period: 120s

# Very slow services (Plex, large models)
interval: 120s
timeout: 30s
retries: 5
start_period: 300s
```

### Check Types by Service Category

1. **Databases**: Use native CLI tools (`pg_isready`, `redis-cli ping`, `mongosh --eval`)
2. **HTTP Services**: Use `wget -q --spider` or `curl -sf` to health endpoints
3. **Background Processes**: Use `ps aux | grep -q <process>` or pidfile checks
4. **AI Services**: Allow longer start periods (120-300s) for model loading

## Recommended Actions

### Immediate (Apply Today)

1. Deploy `healthchecks-additions.yml`:
   ```bash
   docker-compose -f hydra-stack.yml -f healthchecks-additions.yml up -d
   ```

2. Verify all containers show healthy status:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

### Short-term (This Week)

1. Add health checks to media stack containers
2. Configure Uptime Kuma monitors for all containers
3. Set up alerting for container health failures

### Medium-term (This Month)

1. Implement container restart rate limiting (n8n workflow ready)
2. Create auto-healing playbooks for common failures
3. Add health check latency tracking to Prometheus

## Health Check Monitoring Integration

### Prometheus Metrics

Add container health scraping:

```yaml
# prometheus.yml scrape config
- job_name: 'docker'
  static_configs:
    - targets: ['192.168.1.244:9323']
  metrics_path: /metrics
```

### Alertmanager Rules

```yaml
- alert: ContainerUnhealthy
  expr: container_health_status{status!="healthy"} == 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Container {{ $labels.name }} is unhealthy"
```

### n8n Integration

The `container-restart-ratelimit.json` workflow provides:
- Webhook endpoint: `POST /webhook/container-failed`
- Rate limiting: 3 restarts per hour per container
- Activity logging to Hydra MCP

## Container-Specific Notes

### GPU-Dependent Containers (hydra-ai, hydra-compute)

TabbyAPI and Ollama health checks should:
- Wait for GPU initialization (start_period: 180s)
- Check model loading status, not just HTTP
- Consider VRAM availability in health logic

### Network-Dependent Containers

Services depending on external APIs should have:
- Fallback behavior when external services are down
- Separate health check for local vs external dependencies

## Verification Script

Create `/opt/scripts/check-container-health.sh`:

```bash
#!/bin/bash
# Quick health audit of all containers

echo "=== Container Health Audit ==="
echo ""

# Get all containers with health status
docker ps --format "{{.Names}}\t{{.Status}}" | while read name status; do
  if echo "$status" | grep -q "healthy"; then
    echo -e "\033[32m$name: healthy\033[0m"
  elif echo "$status" | grep -q "unhealthy"; then
    echo -e "\033[31m$name: UNHEALTHY\033[0m"
  elif echo "$status" | grep -q "starting"; then
    echo -e "\033[33m$name: starting\033[0m"
  else
    echo -e "\033[36m$name: no healthcheck\033[0m"
  fi
done

echo ""
echo "=== Summary ==="
echo "Healthy: $(docker ps --filter health=healthy --format '{{.Names}}' | wc -l)"
echo "Unhealthy: $(docker ps --filter health=unhealthy --format '{{.Names}}' | wc -l)"
echo "Starting: $(docker ps --filter health=starting --format '{{.Names}}' | wc -l)"
echo "No check: $(docker ps --filter health=none --format '{{.Names}}' | wc -l)"
```

## Conclusion

The Hydra cluster has good health check coverage for core services. Key improvements needed:

1. **Deploy `healthchecks-additions.yml`** for AI and utility containers
2. **Add health checks to media stack** (*Arr apps, download clients)
3. **Enable container health alerting** via Prometheus/Alertmanager
4. **Activate rate-limited auto-restart** workflow in n8n

Following these recommendations will achieve 100% health check coverage and enable autonomous container recovery with appropriate guardrails.

---

*Audit completed by Hydra Autonomous Steward*
