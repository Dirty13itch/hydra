# Hydra Cluster Monitoring Overview

This document describes the complete observability stack for the Hydra cluster.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HYDRA OBSERVABILITY                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │hydra-compute│    │  hydra-ai   │    │hydra-storage│             │
│  │   NixOS     │    │   NixOS     │    │   Unraid    │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         ▼                  ▼                  ▼                     │
│  ┌─────────────────────────────────────────────────────┐           │
│  │              Node Exporter (9100)                   │           │
│  │              NVIDIA GPU Exporter (9835)             │           │
│  │              cAdvisor (where applicable)            │           │
│  └─────────────────────────┬───────────────────────────┘           │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────┐           │
│  │              Prometheus (9090)                       │           │
│  │              hydra-storage                           │           │
│  │              - Scrapes all exporters                 │           │
│  │              - Stores 15 days of metrics             │           │
│  │              - Evaluates alert rules                 │           │
│  └─────────────────────────┬───────────────────────────┘           │
│                            │                                        │
│              ┌─────────────┼─────────────┐                         │
│              ▼             ▼             ▼                         │
│  ┌───────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │   Grafana     │ │    Loki     │ │ Alertmanager│                │
│  │   (3003)      │ │   (3100)    │ │   (9093)    │                │
│  │ - Dashboards  │ │ - Log agg   │ │ - Routing   │                │
│  │ - Alerting    │ │ - Query     │ │ - Silencing │                │
│  └───────────────┘ └─────────────┘ └─────────────┘                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### Metrics Collection

| Component | Port | Location | Metrics |
|-----------|------|----------|---------|
| Node Exporter | 9100 | all nodes | CPU, RAM, disk, network |
| NVIDIA GPU Exporter | 9835 | compute, ai | GPU temp, power, VRAM, utilization |
| cAdvisor | 8080 | storage | Container metrics |
| Prometheus | 9090 | storage | Central metrics store |

### Visualization & Alerting

| Component | Port | Location | Purpose |
|-----------|------|----------|---------|
| Grafana | 3003 | storage | Dashboards, alert UI |
| Loki | 3100 | storage | Log aggregation |
| Alertmanager | 9093 | storage | Alert routing (optional) |

### Application Metrics

| Service | Endpoint | Metrics |
|---------|----------|---------|
| TabbyAPI | `:5000/metrics` | Inference latency, tokens/sec |
| Ollama | `:11434/api/tags` | Model list, health |
| LiteLLM | `:4000/health` | Proxy health, request counts |
| Qdrant | `:6333/metrics` | Vector operations, memory |
| PostgreSQL | via exporter | Query performance, connections |
| Redis | via exporter | Memory, ops/sec |

## Prometheus Configuration

Location: `/mnt/user/appdata/prometheus/prometheus.yml`

### Scrape Targets

```yaml
scrape_configs:
  # Node exporters
  - job_name: 'node'
    static_configs:
      - targets:
        - '192.168.1.244:9100'  # hydra-storage
        - '192.168.1.203:9100'  # hydra-compute
        - '192.168.1.250:9100'  # hydra-ai

  # GPU exporters
  - job_name: 'nvidia-gpu'
    static_configs:
      - targets:
        - '192.168.1.203:9835'  # hydra-compute
        - '192.168.1.250:9835'  # hydra-ai

  # Application endpoints
  - job_name: 'tabbyapi'
    static_configs:
      - targets: ['192.168.1.250:5000']
    metrics_path: /metrics

  - job_name: 'qdrant'
    static_configs:
      - targets: ['192.168.1.244:6333']
    metrics_path: /metrics
```

### Alert Rules

Location: `/mnt/user/appdata/prometheus/rules/hydra-alerts.yml`

See `alerts-slo-plan.md` for the 10 essential alerts.

## Grafana Dashboards

### Installed Dashboards

| Dashboard | ID | Purpose |
|-----------|-----|---------|
| Node Exporter Full | 1860 | System metrics |
| NVIDIA DCGM | 12239 | GPU metrics |
| Docker Containers | 893 | Container stats |
| Hydra AI Control Plane | custom | Inference metrics |

### Creating Custom Dashboards

1. Open Grafana: `http://192.168.1.244:3003`
2. Navigate to Dashboards → New → Import
3. Enter dashboard ID or upload JSON
4. Select Prometheus as data source

### Key Panels for Hydra

**GPU Overview:**
```promql
# GPU Temperature
nvidia_gpu_temperature_celsius

# GPU Power Draw
nvidia_gpu_power_draw_watts

# GPU Memory Used
nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes * 100

# GPU Utilization
nvidia_gpu_utilization_percent
```

**Inference Performance:**
```promql
# TabbyAPI tokens per second
rate(tabby_tokens_generated_total[5m])

# Inference latency p99
histogram_quantile(0.99, rate(tabby_inference_duration_seconds_bucket[5m]))
```

**Cluster Health:**
```promql
# Node up status
up{job="node"}

# Disk space remaining
node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100

# Memory available
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100
```

## Loki Log Aggregation

### Log Sources

| Source | Method | Labels |
|--------|--------|--------|
| Docker containers | Loki Docker driver | container, compose_project |
| System logs | Promtail | host, job |
| Application logs | Direct push | app, level |

### Querying Logs

```logql
# All TabbyAPI logs
{container="tabbyapi"}

# Error logs from any container
{job="docker"} |= "error" | level="error"

# Inference requests
{container="tabbyapi"} |~ "POST /v1/completions"
```

## Health Check Endpoints

Quick validation of monitoring stack:

```bash
# Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Grafana health
curl -s http://192.168.1.244:3003/api/health

# Loki ready
curl -s http://192.168.1.244:3100/ready

# Qdrant metrics
curl -s http://192.168.1.244:6333/metrics | head -20
```

## Troubleshooting

### Prometheus Target Down

1. Check if exporter is running:
   ```bash
   ssh typhon@hydra-compute "systemctl status prometheus-node-exporter"
   ```

2. Check firewall:
   ```bash
   ssh typhon@hydra-compute "sudo iptables -L -n | grep 9100"
   ```

3. Test connectivity:
   ```bash
   curl http://192.168.1.203:9100/metrics | head -5
   ```

### Grafana Dashboard Empty

1. Verify data source connection in Grafana → Configuration → Data Sources
2. Check Prometheus has data: run query in Prometheus UI
3. Verify time range in Grafana (top right)

### Loki Not Receiving Logs

1. Check Loki container:
   ```bash
   docker logs loki --tail 50
   ```

2. Verify Docker logging driver:
   ```bash
   docker inspect <container> | jq '.[0].HostConfig.LogConfig'
   ```

## Maintenance

### Prometheus Data Retention

Default: 15 days. Adjust in prometheus.yml:
```yaml
global:
  scrape_interval: 15s

storage:
  tsdb:
    retention.time: 15d
    retention.size: 10GB
```

### Backup Grafana Dashboards

```bash
# Export all dashboards
curl -s "http://admin:admin@192.168.1.244:3003/api/search?query=&" | \
  jq -r '.[].uid' | \
  xargs -I {} curl -s "http://admin:admin@192.168.1.244:3003/api/dashboards/uid/{}" \
  > /mnt/user/backups/grafana/dashboards-$(date +%Y%m%d).json
```

### Cleanup Old Metrics

Prometheus automatically prunes based on retention settings. Force compaction:
```bash
curl -X POST http://192.168.1.244:9090/api/v1/admin/tsdb/compact
```

---

*Last updated: 2025-12-13*
