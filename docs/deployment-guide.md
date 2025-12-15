# Hydra Cluster Deployment Guide

This guide covers deploying the Phase 11 infrastructure components to the Hydra cluster.

## Prerequisites

- SSH access to all three nodes:
  - hydra-ai (192.168.1.250)
  - hydra-compute (192.168.1.203)
  - hydra-storage (192.168.1.244)
- Docker and docker-compose on hydra-storage
- Python 3.10+ on all nodes

## Quick Start

```bash
# Clone the repo to your local machine
cd /path/to/hydra

# Copy deployment files to hydra-storage
scp -r scripts/ config/ docker-compose/ root@192.168.1.244:/tmp/hydra-deploy/

# Run the main deployment script
ssh root@192.168.1.244 "cd /tmp/hydra-deploy && chmod +x scripts/*.sh && ./scripts/deploy-tier1-infrastructure.sh"
```

---

## Component Deployment

### 1. Container Healthchecks

Fixes unhealthy container status for 18+ containers.

```bash
# Deploy healthcheck additions
cd /mnt/user/appdata/hydra-stack
cp /tmp/hydra-deploy/docker-compose/healthchecks-additions.yml .

# Merge with main compose and restart
docker-compose -f docker-compose.yml -f healthchecks-additions.yml up -d
```

Affected services:
- Databases: hydra-postgres, hydra-redis, hydra-qdrant, letta-db
- AI: hydra-letta, hydra-mcp, hydra-crewai
- Observability: hydra-alertmanager, hydra-uptime-kuma
- Web UIs: homepage, open-webui, hydra-searxng
- Media: Plex-Media-Server, stash

### 2. Grafana Dashboards

Three new dashboards for cluster monitoring.

```bash
# Copy dashboard files
mkdir -p /mnt/user/appdata/grafana/dashboards/hydra
cp /tmp/hydra-deploy/config/grafana/dashboards/*.json /mnt/user/appdata/grafana/dashboards/hydra/

# Copy provisioning config
cp /tmp/hydra-deploy/config/grafana/provisioning/dashboards/hydra-dashboards.yaml \
   /mnt/user/appdata/grafana/provisioning/dashboards/

# Restart Grafana
docker restart hydra-grafana
```

Dashboards:
- **Cluster Overview** - Node status, health percentage, GPU temps
- **Inference Metrics** - LLM latency, throughput, model stats
- **Services Health** - Container resources, database stats

### 3. hydra-health Service

Health aggregation API for unified monitoring.

```bash
# Copy source files
mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_health
cp -r /tmp/hydra-deploy/src/hydra_health/* /mnt/user/appdata/hydra-stack/src/hydra_health/

# Deploy container (already in deploy script)
docker-compose -f docker-compose.services.yml up -d hydra-health

# Verify
curl http://192.168.1.244:8600/health
```

Endpoints:
- `GET /health` - Full cluster health
- `GET /health/summary` - Health summary
- `GET /health/services` - Individual service health
- `GET /live` - Liveness probe
- `GET /ready` - Readiness probe

### 4. hydra-alerts Service

Webhook receiver for Alertmanager notifications.

```bash
# Copy source files
mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_alerts
cp -r /tmp/hydra-deploy/src/hydra_alerts/* /mnt/user/appdata/hydra-stack/src/hydra_alerts/

# Deploy container
docker-compose -f docker-compose.services.yml up -d hydra-alerts

# Verify
curl http://192.168.1.244:9095/health
```

Configure Alertmanager to send to these endpoints:
- `/webhook` - Default (logging only)
- `/critical` - All notification channels
- `/gpu` - GPU-specific alerts
- `/infra` - Infrastructure alerts

### 5. NixOS Configuration

Deploy DNS and firewall configs to NixOS nodes.

```bash
# Copy to hydra-ai
scp /tmp/hydra-deploy/config/nixos/*.nix typhon@192.168.1.250:/tmp/
ssh typhon@192.168.1.250 "sudo cp /tmp/*.nix /etc/nixos/ && sudo nixos-rebuild switch"

# Copy to hydra-compute
scp /tmp/hydra-deploy/config/nixos/*.nix typhon@192.168.1.203:/tmp/
ssh typhon@192.168.1.203 "sudo cp /tmp/*.nix /etc/nixos/ && sudo nixos-rebuild switch"
```

Modules:
- `dns-adguard.nix` - Points DNS to AdGuard on hydra-storage
- `firewall-hydra.nix` - Opens ports 9100 (node_exporter), 9835 (GPU metrics)

### 6. STATE.json Auto-Update

Automated cluster state collection.

```bash
# Copy files
cp /tmp/hydra-deploy/scripts/update-state.py /mnt/user/appdata/hydra-stack/scripts/
cp /tmp/hydra-deploy/config/systemd/hydra-state-collector.* /etc/systemd/system/

# Enable timer
systemctl daemon-reload
systemctl enable --now hydra-state-collector.timer

# Test manually
python3 /mnt/user/appdata/hydra-stack/scripts/update-state.py --output /mnt/user/appdata/hydra-stack/STATE.json
```

### 7. n8n Workflows

Import and activate automation workflows.

```bash
# Set API key
export N8N_API_KEY="your-n8n-api-key"

# Run activation script
python3 /tmp/hydra-deploy/scripts/activate-n8n-workflows.py

# Or manually import via UI at http://192.168.1.244:5678
```

Workflows:
- **Learnings Capture** - Auto-appends to LEARNINGS.md
- **Knowledge Refresh** - Daily state summary generation
- **Autonomous Research** - Overnight research agent (2 AM)

### 8. Uptime Kuma Monitors

Set up 40+ service monitors.

```bash
# Set credentials
export UPTIME_KUMA_PASSWORD="your-password"

# Run setup script
python3 /tmp/hydra-deploy/scripts/setup-uptime-kuma.py

# Or view list first
python3 /tmp/hydra-deploy/scripts/setup-uptime-kuma.py --list
```

### 9. LiteLLM Router

Deploy intelligent model routing.

```bash
# Copy router config
cp /tmp/hydra-deploy/config/litellm/router-config.yaml /mnt/user/appdata/litellm/

# Restart LiteLLM
docker restart litellm
```

Routing tiers:
- **Fast** (gpt-3.5-turbo): Simple tasks, greetings, translations
- **Quality** (gpt-4): Complex analysis, reasoning, long-form
- **Code** (codestral): Programming, debugging, code review

### 10. Home Assistant Integration

Deploy cluster control to Home Assistant.

```bash
# Dry run first
./scripts/deploy-homeassistant.sh --dry-run

# Deploy
./scripts/deploy-homeassistant.sh
```

Then add to `configuration.yaml`:
```yaml
shell_command: !include shell_commands.yaml
automation: !include automations.yaml
```

---

## Verification

### Quick Health Check

```bash
# Check all services
curl -s http://192.168.1.244:8600/health/summary | jq .

# Expected output:
# {
#   "status": "healthy",
#   "healthy": 40,
#   "unhealthy": 0,
#   "total": 40,
#   ...
# }
```

### Full Cluster Verification

```bash
# Run full verification
ssh typhon@192.168.1.250 "nvidia-smi --query-gpu=name,memory.used --format=csv" && \
ssh typhon@192.168.1.203 "nvidia-smi --query-gpu=name,memory.used --format=csv" && \
ssh root@192.168.1.244 "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20"
```

### Service-Specific Checks

```bash
# TabbyAPI
curl -s http://192.168.1.250:5000/v1/model | jq .model_name

# LiteLLM
curl -s http://192.168.1.244:4000/health

# Grafana dashboards
curl -s http://192.168.1.244:3003/api/dashboards/uid/hydra-overview

# Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets | length'
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs hydra-health --tail 50

# Check compose file syntax
docker-compose -f docker-compose.services.yml config
```

### NixOS rebuild fails

```bash
# Check syntax
nix-instantiate --parse /etc/nixos/configuration.nix

# Rollback
sudo nixos-rebuild switch --rollback
```

### n8n workflow not activating

1. Check workflow syntax in n8n UI
2. Verify API key permissions
3. Check n8n logs: `docker logs hydra-n8n`

### Grafana dashboard missing

1. Check provisioning config path
2. Verify JSON syntax: `jq . dashboard.json`
3. Restart Grafana: `docker restart hydra-grafana`

---

## Post-Deployment Tasks

1. [ ] Verify Grafana dashboards at http://192.168.1.244:3003
2. [ ] Check Uptime Kuma monitors at http://192.168.1.244:3001
3. [ ] Activate n8n workflows at http://192.168.1.244:5678
4. [ ] Test Home Assistant automations
5. [ ] Verify STATE.json updates every 15 minutes
6. [ ] Configure Discord webhook (optional)

---

## File Locations Summary

| Component | Local Path | Deployed Path |
|-----------|-----------|---------------|
| Healthchecks | `docker-compose/healthchecks-additions.yml` | `/mnt/user/appdata/hydra-stack/` |
| Grafana | `config/grafana/dashboards/*.json` | `/mnt/user/appdata/grafana/dashboards/hydra/` |
| hydra-health | `src/hydra_health/` | `/mnt/user/appdata/hydra-stack/src/hydra_health/` |
| hydra-alerts | `src/hydra_alerts/` | `/mnt/user/appdata/hydra-stack/src/hydra_alerts/` |
| NixOS | `config/nixos/*.nix` | `/etc/nixos/` |
| STATE updater | `scripts/update-state.py` | `/mnt/user/appdata/hydra-stack/scripts/` |
| n8n workflows | `config/n8n/workflows/*.json` | Imported via API |
| LiteLLM router | `config/litellm/router-config.yaml` | `/mnt/user/appdata/litellm/` |

---

*Last updated: December 2025*
