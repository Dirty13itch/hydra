# Troubleshooting Guide

## Quick Diagnostics

### Check All Services Health
```bash
# From hydra-storage
curl -s "http://localhost:9090/api/v1/targets" | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"'

# Container status
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -v "^NAMES"
```

### SSH Access Patterns
```bash
# NixOS nodes - use SSH aliases (configured in ~/.ssh/config)
ssh hydra-ai
ssh hydra-compute

# hydra-storage - requires specific key
ssh -i ~/.ssh/hydra-mcp root@192.168.1.244
```

---

## Container Issues

### Container Restart Loop
**Symptoms:** Container repeatedly restarting, short uptime in `docker ps`

**Diagnosis:**
```bash
docker logs <container> --tail 50
docker inspect <container> --format '{{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}'
```

**Common Causes:**
1. **Health check too aggressive** - Increase `start_period` in healthcheck
2. **Missing dependency** - Check `depends_on` and service availability
3. **OOM killed** - Increase memory limit or reduce workload
4. **Config error** - Check logs for syntax/config issues

**Fix for health monitor causing restarts:**
- Edit `/mnt/user/appdata/hydra-stack/scripts/health-monitor.sh`
- Add grace period: `GRACE_PERIOD=120` (seconds)
- Check container uptime before health check

### Container Can't Connect to Other Services
**Symptoms:** Connection refused, DNS resolution failures

**Diagnosis:**
```bash
# Check network
docker network inspect hydra-network
docker inspect <container> --format '{{json .NetworkSettings.Networks}}' | jq .

# Test from inside container
docker exec <container> ping other-container
docker exec <container> curl http://other-container:port/health
```

**Common Causes:**
1. **Wrong network** - Container not on `hydra-network`
2. **Service name mismatch** - Use container name, not service name
3. **Port not exposed** - Check container exposes correct port

### Stale NFS File Handle
**Symptoms:** `stale NFS file handle` errors, especially after config changes

**Fix:**
```bash
# Instead of config reload (SIGHUP)
docker restart hydra-prometheus

# If persistent, remount NFS on host
sudo umount -f /mnt/models && sudo mount /mnt/models
```

---

## NixOS Issues

### Firewall Blocking Ports
**Symptoms:** Service works locally but not remotely, Prometheus scrape failures

**Diagnosis:**
```bash
# Check firewall rules
sudo iptables -L nixos-fw -n | grep <port>

# Test local vs remote
curl localhost:<port>  # works
curl <node-ip>:<port>  # fails
```

**Temporary Fix (lost on reboot):**
```bash
sudo iptables -I nixos-fw 1 -p tcp --dport <port> -j nixos-fw-accept
```

**Permanent Fix:**
```bash
# Edit configuration.nix
sudo nano /etc/nixos/configuration.nix
# Add port to: networking.firewall.allowedTCPPorts = [ ... <port> ... ];
sudo nixos-rebuild switch
```

### User Systemd Service Dies on SSH Disconnect
**Symptoms:** Service runs during SSH session, stops after disconnect

**Root Cause:** User services killed when session ends (no lingering)

**Fix:**
```bash
sudo loginctl enable-linger <username>
# For typhon user on hydra-compute:
sudo loginctl enable-linger typhon
```

**Verify:**
```bash
loginctl show-user <username> | grep Linger
# Should show: Linger=yes
```

### Python/Binary Not Found
**Symptoms:** `python3: command not found` or similar

**NixOS stores binaries in /nix/store, not /usr/bin**

**Fix for systemd services:**
```ini
# Use full path from nix store
ExecStart=/run/current-system/sw/bin/python3 /path/to/script.py
```

**Find correct path:**
```bash
which python3
# Returns: /run/current-system/sw/bin/python3
```

---

## Prometheus/Monitoring Issues

### Target Shows DOWN
**Diagnosis:**
```bash
# Check if service is running
curl -s http://<target-ip>:<port>/metrics | head -3

# Check Prometheus scrape error
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.labels.job=="<job>") | .lastError'
```

**Common Causes:**
1. **Firewall** - See firewall section above
2. **Service not running** - Start service, check logs
3. **Wrong IP** - Verify IP in prometheus.yml matches actual node IP
4. **Network unreachable** - Check routing, 10GbE vs management network

### Rules Not Loading
**Symptoms:** `/api/v1/rules` returns empty groups

**Diagnosis:**
```bash
# Check files are mounted
docker exec hydra-prometheus ls -la /etc/prometheus/

# Validate rules
docker exec hydra-prometheus promtool check rules /etc/prometheus/recording_rules.yml
```

**Fix:** Add volume mounts in docker-compose.yml:
```yaml
volumes:
  - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
  - ./prometheus/recording_rules.yml:/etc/prometheus/recording_rules.yml
  - ./prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml
```

### Alertmanager Not Receiving Alerts
**Diagnosis:**
```bash
curl -s http://localhost:9090/api/v1/alertmanagers | jq .
# Check activeAlertmanagers list

curl -s http://localhost:9093/api/v2/status | jq .
```

**Fix:** Ensure `alerting` section in prometheus.yml:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - hydra-alertmanager:9093
```

---

## GPU Issues

### DCGM/nvidia_gpu_exporter Crashes on Blackwell GPUs
**Symptoms:** Exporter crashes immediately, logs show sm_120 errors

**Root Cause:** Blackwell (RTX 50xx) uses sm_120 architecture, not yet supported by DCGM

**Workaround:** Use nvidia-smi script exporter
```bash
# Check exporter running on hydra-compute
curl http://192.168.1.203:9835/metrics
```

**Exporter location:** `/opt/nvidia-metrics/exporter.py`

### Docker `--gpus all` Fails on NixOS
**Symptoms:** `docker: Error response from daemon: could not select device driver`

**Root Cause:** NixOS Docker doesn't support `--gpus` flag directly

**Fix:** Use CDI (Container Device Interface) in docker-compose:
```yaml
services:
  my-gpu-app:
    devices:
      - nvidia.com/gpu=0  # Use CDI device request
```

---

## Database Issues

### PostgreSQL Connection Refused
**Diagnosis:**
```bash
docker exec hydra-postgres pg_isready -U hydra
docker logs hydra-postgres --tail 20
```

**Common Causes:**
1. **Container not running** - `docker start hydra-postgres`
2. **Wrong credentials** - Check env vars in docker-compose
3. **Network mismatch** - Ensure client on same Docker network

### Qdrant Collection Dimension Mismatch
**Symptoms:** `Vector dimension error` when inserting

**Root Cause:** Collection created with different dimension than vectors being inserted

**Check dimension:**
```bash
curl -s http://localhost:6333/collections/hydra_knowledge | jq '.result.config.params.vectors.size'
```

**Fix:** Create collection with correct dimension (768 for nomic-embed-text):
```bash
curl -X PUT "http://localhost:6333/collections/hydra_knowledge" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
```

### pgvector Extension Missing
**Symptoms:** `ERROR: type "vector" does not exist`

**Fix:**
```bash
docker exec <postgres-container> psql -U <user> -d <db> -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Note:** Requires `pgvector/pgvector:pg16` image, not standard postgres

---

## Network Issues

### Python TCPServer Port Already in Use
**Symptoms:** `Address already in use` when starting service

**Diagnosis:**
```bash
netstat -tlnp | grep <port>
ps aux | grep <script>
```

**Root Cause:** Socket in TIME_WAIT state after previous process killed

**Fixes:**
1. **Wait 60-120 seconds** for socket timeout
2. **Use ReuseAddrTCPServer:**
```python
class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True
```
3. **Kill orphaned processes:**
```bash
pkill -9 -f <script-name>
sleep 70  # Wait for TIME_WAIT
```

### 10GbE Performance Issues
**Diagnosis:**
```bash
# Check link speed
ethtool eno1 | grep Speed

# Test throughput
iperf3 -c 192.168.1.244 -t 10

# Check NFS mount options
mount | grep models
```

**Expected:** 9.4+ Gbps on iperf3, 500+ MB/s on NFS

---

## Letta Issues

### Letta Can't Connect to Database
**Symptoms:** Migration errors, connection refused

**Diagnosis:**
```bash
docker logs hydra-letta --tail 50
docker exec letta-db pg_isready -U letta
```

**Fix:** Ensure `LETTA_PG_URI` uses container name:
```
postgresql://letta:HydraLettaDB2024!@letta-db:5432/letta
```

### Letta Returns 401 Unauthorized
**Root Cause:** `SECURE=true` requires password header

**Fix:** Include password in requests:
```bash
curl -H "Authorization: Bearer HydraLetta2024!" http://192.168.1.244:8283/v1/health
```

---

## Schema/Version Issues

### Container Downgrade Fails
**Symptoms:** Data corruption errors, migration failures when using older image

**Affected Services:** Qdrant, Portainer, AdGuard Home

**Root Cause:** Database schema created by newer version incompatible with older

**Fix:** Keep on `:latest` or current version, don't downgrade:
```yaml
# These must stay on latest due to schema issues
image: qdrant/qdrant:latest
image: portainer/portainer-ce:latest
image: adguard/adguardhome:latest
```

---

## Common Commands Reference

### Container Operations
```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker logs <container> --tail 100 -f
docker exec -it <container> sh
docker restart <container>
docker compose -f /path/to/docker-compose.yml up -d
docker compose -f /path/to/docker-compose.yml down
```

### Prometheus Queries
```bash
# All targets status
curl -s "http://localhost:9090/api/v1/targets" | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"'

# Query metric
curl -s "http://localhost:9090/api/v1/query?query=up" | jq -r '.data.result[] | "\(.metric.job): \(.value[1])"'

# Check rules
curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[].name'
```

### GPU Status
```bash
nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv
```

### NixOS
```bash
sudo nixos-rebuild switch          # Apply config changes
sudo nixos-rebuild switch --rollback  # Revert last change
journalctl -u <service> -f         # Follow service logs
systemctl status <service>         # Check service status
```

---

*Last updated: December 10, 2025*
