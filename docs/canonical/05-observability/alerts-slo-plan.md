# Alerts & SLO Plan for Hydra Cluster

This document defines the 10 essential alerts for the Hydra cluster. Focus is on actionable alerts only—no noise.

## Alert Philosophy

- **Alert on symptoms, not causes** - Alert when user experience is degraded
- **Every alert must be actionable** - If you can't do anything about it at 3 AM, don't wake up
- **Prefer fewer, better alerts** - 10 focused alerts beat 50 ignored ones

## The 10 Must-Have Alerts

### 1. Node Down

**What:** A cluster node is unreachable
**Why:** Complete service outage for that node
**Threshold:** No response for 2 minutes

```yaml
- alert: NodeDown
  expr: up{job="node"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Node {{ $labels.instance }} is down"
    description: "Node has been unreachable for over 2 minutes"
```

### 2. GPU Temperature Critical

**What:** GPU temperature exceeds safe operating range
**Why:** Risk of thermal throttling or hardware damage
**Threshold:** >85°C for 5 minutes

```yaml
- alert: GPUTemperatureCritical
  expr: nvidia_gpu_temperature_celsius > 85
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU {{ $labels.gpu }} on {{ $labels.instance }} is overheating"
    description: "Temperature is {{ $value }}°C (threshold: 85°C)"
```

### 3. Disk Space Low

**What:** Disk usage exceeds 85%
**Why:** Services will fail when disk is full
**Threshold:** >85% used

```yaml
- alert: DiskSpaceLow
  expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 15
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Low disk space on {{ $labels.instance }}"
    description: "{{ $labels.mountpoint }} has {{ $value | humanize }}% free"
```

### 4. Disk Space Critical

**What:** Disk usage exceeds 95%
**Why:** Imminent service failure
**Threshold:** >95% used

```yaml
- alert: DiskSpaceCritical
  expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 5
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Critical disk space on {{ $labels.instance }}"
    description: "{{ $labels.mountpoint }} has only {{ $value | humanize }}% free"
```

### 5. TabbyAPI Down

**What:** Primary inference engine is unavailable
**Why:** All LLM inference stops
**Threshold:** No response for 2 minutes

```yaml
- alert: TabbyAPIDown
  expr: up{job="tabbyapi"} == 0 or probe_success{job="blackbox", target="http://192.168.1.250:5000/health"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "TabbyAPI is down"
    description: "Primary inference engine has been unreachable for 2 minutes"
```

### 6. Container Restart Loop

**What:** A container is restarting repeatedly
**Why:** Service is crashing and likely misconfigured
**Threshold:** >3 restarts in 10 minutes

```yaml
- alert: ContainerRestartLoop
  expr: increase(container_restarts_total[10m]) > 3
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Container {{ $labels.name }} is in a restart loop"
    description: "Container has restarted {{ $value }} times in the last 10 minutes"
```

### 7. High Memory Usage

**What:** System memory is nearly exhausted
**Why:** OOM killer may start terminating processes
**Threshold:** >90% RAM used for 5 minutes

```yaml
- alert: HighMemoryUsage
  expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High memory usage on {{ $labels.instance }}"
    description: "Memory usage is {{ $value | humanize }}%"
```

### 8. NFS Mount Stale

**What:** NFS mount is unavailable or stale
**Why:** Models and shared storage become inaccessible
**Threshold:** Mount check fails for 2 minutes

```yaml
- alert: NFSMountStale
  expr: node_filesystem_readonly{fstype="nfs4"} == 1 or node_filesystem_avail_bytes{fstype="nfs4"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "NFS mount issue on {{ $labels.instance }}"
    description: "{{ $labels.mountpoint }} is read-only or unavailable"
```

### 9. Parity Check Running (Unraid)

**What:** Unraid is performing a parity check
**Why:** Performance degradation expected; don't schedule other heavy tasks
**Threshold:** Parity check detected

```yaml
- alert: ParityCheckRunning
  expr: unraid_parity_check_running == 1
  for: 1m
  labels:
    severity: info
  annotations:
    summary: "Unraid parity check in progress"
    description: "Performance may be degraded on hydra-storage"
```

### 10. Prometheus Target Down

**What:** A Prometheus scrape target is failing
**Why:** Monitoring blind spot
**Threshold:** Target down for 5 minutes

```yaml
- alert: PrometheusTargetDown
  expr: up == 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Prometheus target {{ $labels.job }} is down"
    description: "Cannot scrape {{ $labels.instance }}"
```

## Implementation

### Step 1: Create Alert Rules File

SSH to hydra-storage and create the rules file:

```bash
ssh root@hydra-storage
cat > /mnt/user/appdata/prometheus/rules/hydra-alerts.yml << 'EOF'
groups:
  - name: hydra-alerts
    rules:
      # Paste all 10 alert rules here
EOF
```

### Step 2: Update Prometheus Config

Ensure `/mnt/user/appdata/prometheus/prometheus.yml` includes:

```yaml
rule_files:
  - /etc/prometheus/rules/*.yml
```

### Step 3: Reload Prometheus

```bash
curl -X POST http://192.168.1.244:9090/-/reload
```

### Step 4: Verify in Grafana

1. Open Grafana at `http://192.168.1.244:3003`
2. Navigate to Alerting → Alert rules
3. Confirm all 10 rules appear

## Notification Channels (Future)

| Channel | Use Case |
|---------|----------|
| Discord webhook | All warnings/critical |
| Email | Critical only |
| Pushover | Critical (mobile push) |

Configure in Grafana → Alerting → Contact points

## SLO Targets

| Service | Target | Measurement |
|---------|--------|-------------|
| TabbyAPI | 99% uptime | Weekly |
| Plex | 99% uptime | Weekly |
| NFS mounts | 99.9% availability | Weekly |
| GPU temp | <80°C avg | Daily |

## Alert Escalation

| Severity | Response Time | Action |
|----------|---------------|--------|
| info | Next business day | Review when convenient |
| warning | Same day | Investigate, plan fix |
| critical | Immediate | Stop and fix now |

---

*Last updated: 2025-12-13*
