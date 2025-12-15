# Phase 11 Production Deployment Checklist

> **Purpose:** Step-by-step checklist to deploy all Phase 11 components to production
> **Estimated Time:** 2-3 hours
> **Prerequisites:** SSH access to all nodes, hydra project files

---

## Pre-Deployment Verification

### Verify Current State
```bash
# Check cluster is reachable
ssh typhon@192.168.1.250 "echo 'hydra-ai OK'"
ssh typhon@192.168.1.203 "echo 'hydra-compute OK'"
ssh root@192.168.1.244 "echo 'hydra-storage OK'"
```

- [ ] All three nodes reachable via SSH
- [ ] No active workloads that would be disrupted

### Verify Phase 11 Files Exist
```bash
# Run from project root
ls -la src/hydra_tools/api.py
ls -la docker/Dockerfile.hydra-tools
ls -la docker-compose/hydra-tools-api.yml
ls -la scripts/deploy-hydra-tools.sh
```

- [ ] `api.py` exists
- [ ] `Dockerfile.hydra-tools` exists
- [ ] `hydra-tools-api.yml` exists
- [ ] `deploy-hydra-tools.sh` exists

---

## Step 1: Deploy Hydra Tools API

### 1.1 Deploy Container
```bash
# Make script executable and run
chmod +x scripts/deploy-hydra-tools.sh

# Dry run first
./scripts/deploy-hydra-tools.sh --dry-run

# If dry run looks good, deploy with build
./scripts/deploy-hydra-tools.sh --build
```

- [ ] Dry run completed successfully
- [ ] Deployment completed without errors

### 1.2 Verify API Health
```bash
# Wait 30 seconds for container to start
sleep 30

# Check health endpoint
curl -s http://192.168.1.244:8700/health | jq .

# Check OpenAPI docs accessible
curl -s http://192.168.1.244:8700/docs | head -20
```

- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] OpenAPI docs page loads

### 1.3 Test Individual Endpoints
```bash
# Diagnosis endpoint
curl -s http://192.168.1.244:8700/diagnosis/report | jq .

# Optimization endpoint
curl -s http://192.168.1.244:8700/optimization/suggestions | jq .

# Knowledge endpoint
curl -s http://192.168.1.244:8700/knowledge/metrics | jq .

# Capabilities endpoint
curl -s http://192.168.1.244:8700/capabilities/backlog | jq .
```

- [ ] Diagnosis report returns valid JSON
- [ ] Optimization suggestions return valid JSON
- [ ] Knowledge metrics return valid JSON
- [ ] Capabilities backlog returns valid JSON

---

## Step 2: Fix Container Healthchecks

### 2.1 Apply Healthcheck Fixes
```bash
ssh root@192.168.1.244 << 'EOF'
cd /mnt/user/appdata/hydra-stack

# Copy healthchecks additions file (if not already present)
# Create or verify healthchecks-additions.yml exists

# Apply the compose override
docker-compose -f docker-compose.yml -f healthchecks-additions.yml up -d
EOF
```

- [ ] Compose command completed without errors

### 2.2 Verify Containers Now Healthy
```bash
# Wait for healthchecks to run (up to 2 minutes)
sleep 120

# Check container status
ssh root@192.168.1.244 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'unhealthy|healthy'"

# Count unhealthy
ssh root@192.168.1.244 "docker ps | grep -c unhealthy || echo 0"
```

- [ ] Unhealthy count reduced (target: 0)
- [ ] Core services (postgres, redis, qdrant, letta) showing healthy

---

## Step 3: Activate n8n Workflows

### 3.1 Import Workflows
```bash
# Run workflow activation script
python scripts/activate-n8n-workflows.py

# Or manually via n8n API
curl -X GET http://192.168.1.244:5678/api/v1/workflows | jq '.data | length'
```

- [ ] Workflows imported successfully
- [ ] Workflow count matches expected (14+)

### 3.2 Activate Critical Workflows
Access n8n UI at http://192.168.1.244:5678 and activate:

| Workflow | Priority | Verify Active |
|----------|----------|---------------|
| letta-memory-update | HIGH | [ ] |
| cluster-health-digest | HIGH | [ ] |
| container-auto-restart | HIGH | [ ] |
| learnings-capture | MEDIUM | [ ] |
| knowledge-refresh | MEDIUM | [ ] |
| autonomous-research | MEDIUM | [ ] |
| disk-cleanup | LOW | [ ] |

### 3.3 Test Webhook Endpoints
```bash
# Test health digest webhook (should trigger workflow)
curl -X POST http://192.168.1.244:5678/webhook/health-digest

# Test learnings webhook
curl -X POST http://192.168.1.244:5678/webhook/learnings \
  -H "Content-Type: application/json" \
  -d '{"learning": "Test learning entry", "category": "test"}'
```

- [ ] Health digest webhook responds
- [ ] Learnings webhook responds

---

## Step 4: Apply NixOS Configurations

### 4.1 Copy Configuration Files
```bash
# Copy DNS module to hydra-ai
scp config/nixos/dns-adguard.nix typhon@192.168.1.250:/tmp/
ssh typhon@192.168.1.250 "sudo cp /tmp/dns-adguard.nix /etc/nixos/modules/"

# Copy firewall module to hydra-ai
scp config/nixos/firewall-hydra.nix typhon@192.168.1.250:/tmp/
ssh typhon@192.168.1.250 "sudo cp /tmp/firewall-hydra.nix /etc/nixos/modules/"

# Repeat for hydra-compute
scp config/nixos/dns-adguard.nix typhon@192.168.1.203:/tmp/
ssh typhon@192.168.1.203 "sudo cp /tmp/dns-adguard.nix /etc/nixos/modules/"
scp config/nixos/firewall-hydra.nix typhon@192.168.1.203:/tmp/
ssh typhon@192.168.1.203 "sudo cp /tmp/firewall-hydra.nix /etc/nixos/modules/"
```

- [ ] Modules copied to hydra-ai
- [ ] Modules copied to hydra-compute

### 4.2 Update configuration.nix to Import Modules
```bash
# Add imports to configuration.nix on each node
ssh typhon@192.168.1.250 "grep -q 'dns-adguard' /etc/nixos/configuration.nix && echo 'Already imported' || echo 'Need to add import'"

# If needed, add these lines to imports section:
# ./modules/dns-adguard.nix
# ./modules/firewall-hydra.nix
```

- [ ] hydra-ai imports updated
- [ ] hydra-compute imports updated

### 4.3 Apply NixOS Configuration
```bash
# Dry build first
ssh typhon@192.168.1.250 "sudo nixos-rebuild dry-build"
ssh typhon@192.168.1.203 "sudo nixos-rebuild dry-build"

# If successful, apply
ssh typhon@192.168.1.250 "sudo nixos-rebuild switch"
ssh typhon@192.168.1.203 "sudo nixos-rebuild switch"
```

- [ ] hydra-ai dry-build successful
- [ ] hydra-compute dry-build successful
- [ ] hydra-ai rebuild switch successful
- [ ] hydra-compute rebuild switch successful

### 4.4 Verify DNS Configuration
```bash
# Check DNS resolver on each node
ssh typhon@192.168.1.250 "cat /etc/resolv.conf"
ssh typhon@192.168.1.203 "cat /etc/resolv.conf"

# Test DNS resolution
ssh typhon@192.168.1.250 "nslookup hydra-storage"
```

- [ ] Nodes using 192.168.1.244 for DNS
- [ ] Hostname resolution working

---

## Step 5: Prometheus Integration

### 5.1 Add Hydra Tools API to Prometheus
```bash
ssh root@192.168.1.244 << 'EOF'
# Add scrape config for hydra-tools-api
cat >> /mnt/user/appdata/prometheus/prometheus.yml << 'YAML'

  - job_name: 'hydra-tools-api'
    static_configs:
      - targets: ['hydra-storage:8700']
    metrics_path: '/metrics'
YAML

# Reload Prometheus
docker exec hydra-prometheus kill -HUP 1
EOF
```

- [ ] Prometheus config updated
- [ ] Prometheus reloaded

### 5.2 Verify Prometheus Target
```bash
# Check targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="hydra-tools-api")'
```

- [ ] hydra-tools-api target showing UP

---

## Step 6: Update STATE.json

### 6.1 Trigger State Update
```bash
# Run state collector manually
ssh root@192.168.1.244 "python3 /mnt/user/projects/hydra/scripts/update-state.py"

# Or via systemd timer (if installed)
ssh root@192.168.1.244 "systemctl start hydra-state-collector"
```

- [ ] STATE.json updated

### 6.2 Verify State Accuracy
```bash
# Check STATE.json reflects healthy status
cat STATE.json | jq '.summary'
```

- [ ] Status shows improved health
- [ ] Container counts accurate

---

## Post-Deployment Verification

### Final Health Checks
```bash
# All-in-one cluster health check
curl -s http://192.168.1.244:8600/cluster/status | jq .

# Phase 11 API health
curl -s http://192.168.1.244:8700/health | jq .

# n8n workflows
curl -s http://192.168.1.244:5678/api/v1/workflows | jq '.data | map(select(.active==true)) | length'

# Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets | map(select(.health=="up")) | length'
```

### Summary Checklist
- [ ] **Hydra Tools API:** Running on port 8700, all endpoints responding
- [ ] **Container Health:** All containers healthy (or known exceptions)
- [ ] **n8n Workflows:** Critical workflows activated and responding
- [ ] **NixOS Configs:** DNS and firewall applied on both nodes
- [ ] **Prometheus:** New target added and scraping
- [ ] **STATE.json:** Updated to reflect current state

---

## Rollback Procedures

### If Tools API Fails
```bash
ssh root@192.168.1.244 "cd /mnt/user/appdata/hydra-tools && docker-compose down"
```

### If NixOS Fails
```bash
ssh typhon@192.168.1.250 "sudo nixos-rebuild switch --rollback"
ssh typhon@192.168.1.203 "sudo nixos-rebuild switch --rollback"
```

### If n8n Workflows Cause Issues
```bash
# Deactivate all workflows via API
curl -X PATCH http://192.168.1.244:5678/api/v1/workflows/bulk \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

---

## Next Steps After Successful Deployment

1. **Monitor for 24 hours:** Watch for any issues in Grafana/Prometheus
2. **Run validation tests:** Execute self-improvement loop test scenarios
3. **Begin SOPS migration:** Encrypt plaintext secrets
4. **Setup Uptime Kuma monitors:** Configure 40+ endpoint monitors
5. **Start Phase 12 planning:** Character reference system design

---

*Checklist Version: 1.0*
*Created: 2025-12-13*
*For: Phase 11 Production Deployment*
