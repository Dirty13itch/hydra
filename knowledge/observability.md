# Observability Stack - Hydra Cluster

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     hydra-storage (Unraid)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Prometheus  │  │   Grafana    │  │    Loki      │          │
│  │    :9090     │  │    :3003     │  │    :3100     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│  ┌──────▼─────────────────▼──────────────────▼───────┐          │
│  │              Prometheus Data / Loki Logs           │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Uptime Kuma  │  │ AlertManager │                             │
│  │    :3001     │  │    :9093     │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │hydra-ai │          │hydra-   │          │hydra-   │
    │node-exp │          │compute  │          │storage  │
    │dcgm-exp │          │node-exp │          │cAdvisor │
    │promtail │          │dcgm-exp │          │promtail │
    └─────────┘          │promtail │          └─────────┘
                         └─────────┘
```

## Components

### Prometheus (Metrics Collection)
- **Image:** `prom/prometheus:v2.54.1`
- **Port:** 9090
- **Purpose:** Time-series metrics database, scraping all endpoints
- **Current Targets:** 10 active (all UP as of Dec 10, 2025)

### Grafana (Visualization)
- **Image:** `grafana/grafana:11.3.0`
- **Port:** 3003
- **Credentials:** admin / HydraGrafana2024!
- **Purpose:** Dashboards, alerting UI

### Loki (Log Aggregation)
- **Image:** `grafana/loki:3.2.0`
- **Port:** 3100
- **Purpose:** Log storage and querying

### Promtail (Log Shipping)
- **Image:** `grafana/promtail:2.9.2`
- **Purpose:** Ships logs from each node to Loki

### AlertManager (Alert Routing)
- **Image:** `prom/alertmanager:v0.28.1`
- **Port:** 9093
- **Purpose:** Routes alerts to webhooks (n8n integration ready)
- **Status:** Deployed and connected to Prometheus

### Uptime Kuma (Health Checks)
- **Image:** `louislam/uptime-kuma:1`
- **Port:** 3004
- **Credentials:** admin / HydraKuma2024!
- **Monitors:** 16 active (TabbyAPI, Ollama, LiteLLM, DBs, Media stack)

---

## Prometheus Configuration

Save as `/mnt/user/appdata/hydra-stack/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/alerts/*.yml

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporters (system metrics)
  - job_name: 'node'
    static_configs:
      - targets:
          - '192.168.1.250:9100'  # hydra-ai
          - '192.168.1.203:9100'  # hydra-compute
          - '192.168.1.244:9100'  # hydra-storage
        labels:
          cluster: 'hydra'

  # NVIDIA GPU Metrics (DCGM Exporter)
  - job_name: 'gpu'
    static_configs:
      - targets:
          - '192.168.1.250:9400'  # hydra-ai (5090 + 4090)
          - '192.168.1.203:9400'  # hydra-compute (5070 Ti + 3060)
        labels:
          cluster: 'hydra'

  # Docker/Container metrics (cAdvisor on Unraid)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # TabbyAPI metrics
  - job_name: 'tabbyapi'
    static_configs:
      - targets: ['192.168.1.250:5000']
    metrics_path: /metrics

  # LiteLLM metrics (after deployment)
  - job_name: 'litellm'
    static_configs:
      - targets: ['litellm:4000']
    metrics_path: /metrics
```

---

## Alert Rules

Save as `/mnt/user/appdata/hydra-stack/prometheus/alerts/hydra-alerts.yml`:

```yaml
groups:
  - name: hydra-cluster
    rules:
      # Node down
      - alert: NodeDown
        expr: up{job="node"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Node {{ $labels.instance }} is down"

      # GPU temperature high
      - alert: GPUTemperatureHigh
        expr: DCGM_FI_DEV_GPU_TEMP > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} temperature is {{ $value }}°C"

      # GPU memory near full
      - alert: GPUMemoryHigh
        expr: (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL) * 100 > 95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} memory usage is {{ $value }}%"

      # Disk space low
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disk space low on {{ $labels.instance }}: {{ $value }}% free"

      # TabbyAPI down
      - alert: TabbyAPIDown
        expr: up{job="tabbyapi"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "TabbyAPI is down"

      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}: {{ $value }}%"
```

---

## Grafana Dashboards

### Dashboard: Cluster Overview
Create after deployment with these panels:
- Node status (up/down)
- CPU usage by node
- Memory usage by node
- GPU utilization and temperature
- Network throughput
- Disk usage

### Dashboard: GPU Performance
- GPU utilization per card
- GPU memory usage
- GPU temperature
- GPU power draw
- Inference tokens/sec (if available)

### Dashboard: Inference Metrics
- TabbyAPI request rate
- Response latency (p50, p95, p99)
- Active model
- Queue depth
- Error rate

---

## NixOS Node Exporter Configuration

Add to `/etc/nixos/configuration.nix` on hydra-ai and hydra-compute:

```nix
# Prometheus Node Exporter
services.prometheus.exporters.node = {
  enable = true;
  port = 9100;
  enabledCollectors = [
    "cpu"
    "diskstats"
    "filesystem"
    "loadavg"
    "meminfo"
    "netdev"
    "stat"
    "time"
    "vmstat"
  ];
};

# Open firewall for metrics scraping
networking.firewall.allowedTCPPorts = [ 9100 9400 ];
```

---

## GPU Metrics Exporters

### DCGM Exporter (Ampere/Ada GPUs only)
**IMPORTANT:** DCGM crashes on Blackwell (RTX 5090/5070 Ti) due to sm_120 architecture.

For older GPUs (RTX 4090, 3060):
```bash
docker run -d \
  --name dcgm-exporter \
  --gpus all \
  --restart unless-stopped \
  -p 9400:9400 \
  nvidia/dcgm-exporter:3.3.0-3.2.0-ubuntu22.04
```

### nvidia-smi Script Exporter (Blackwell Compatible)
For RTX 5090/5070 Ti nodes, use the custom Python exporter:

- **Port:** 9835
- **Location:** `/opt/nvidia-metrics/exporter.py`
- **Service:** `~/.config/systemd/user/nvidia-metrics-exporter.service`
- **CRITICAL:** Requires `sudo loginctl enable-linger <username>` for persistence

Current targets:
- `192.168.1.250:9835` (hydra-ai: 5090+4090)
- `192.168.1.203:9835` (hydra-compute: 5070 Ti+3060)

---

## Loki Configuration

Save as `/mnt/user/appdata/hydra-stack/loki/loki-config.yml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 3m
  chunk_block_size: 262144
  chunk_retain_period: 1m

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

---

## Promtail Configuration (on each node)

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://192.168.1.244:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          host: ${HOSTNAME}
          __path__: /var/log/*log

  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
        host: ${HOSTNAME}
    relabel_configs:
      - source_labels: ['__journal__systemd_unit']
        target_label: 'unit'
```

---

## AlertManager Configuration

Save as `/mnt/user/appdata/hydra-stack/alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'discord'

receivers:
  - name: 'discord'
    discord_configs:
      - webhook_url: '${DISCORD_WEBHOOK_URL}'
        title: '{{ template "discord.title" . }}'
        message: '{{ template "discord.message" . }}'
```

---

## Verification Commands

```bash
# Check Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check Grafana health
curl -s http://192.168.1.244:3003/api/health | jq .

# Check Loki ready
curl -s http://192.168.1.244:3100/ready

# Check AlertManager status
curl -s http://192.168.1.244:9093/-/healthy

# Query Prometheus
curl -s 'http://192.168.1.244:9090/api/v1/query?query=up' | jq '.data.result'
```

---

## Troubleshooting

### Prometheus not scraping targets
1. Check firewall on target nodes: `sudo iptables -L`
2. Test connectivity: `curl http://<target>:9100/metrics`
3. Check Prometheus logs: `docker logs hydra-prometheus`

### Grafana can't connect to Prometheus
1. Verify Prometheus is on same Docker network
2. Check datasource URL uses container name or correct IP
3. Test from Grafana container: `docker exec hydra-grafana curl prometheus:9090/-/healthy`

### GPU metrics not appearing
1. Verify DCGM exporter is running: `docker ps | grep dcgm`
2. Check GPU access: `docker exec dcgm-exporter nvidia-smi`
3. Test metrics endpoint: `curl http://192.168.1.250:9400/metrics | head`

---

*Knowledge file: observability.md*
*Last updated: December 10, 2025*
