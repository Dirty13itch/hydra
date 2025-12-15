# Service Recovery Runbook

Step-by-step procedures for recovering failed services on the Hydra cluster.

## Quick Service Status Check

```bash
# Full cluster health
curl -s http://192.168.1.244:8600/health/summary | jq .

# Node-by-node status
ssh typhon@192.168.1.250 "systemctl status tabbyapi open-webui --no-pager"
ssh typhon@192.168.1.203 "systemctl status ollama comfyui --no-pager"
ssh root@192.168.1.244 "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20"
```

---

## Docker Service Recovery (hydra-storage)

### Single Container Restart

```bash
ssh root@192.168.1.244

# Restart single container
docker restart litellm

# Check logs
docker logs -f litellm --tail=50
```

### Container Won't Start

1. **Check container status**
   ```bash
   docker inspect litellm | jq '.[0].State'
   ```

2. **View error logs**
   ```bash
   docker logs litellm 2>&1 | tail -100
   ```

3. **Common fixes**
   ```bash
   # Port conflict
   docker ps -a | grep -E ":[PORT]"
   docker stop <conflicting_container>

   # Volume permission issue
   docker run --rm -v litellm_data:/data alpine chown -R 1000:1000 /data

   # Corrupted container
   docker rm litellm
   docker-compose up -d litellm
   ```

4. **Full stack restart (last resort)**
   ```bash
   cd /mnt/user/appdata/hydra-stack
   docker-compose down
   docker-compose up -d
   ```

---

## NixOS Service Recovery (hydra-ai / hydra-compute)

### Single Service Restart

```bash
# On hydra-ai
ssh typhon@192.168.1.250 "sudo systemctl restart tabbyapi"

# Check status
ssh typhon@192.168.1.250 "systemctl status tabbyapi"

# View logs
ssh typhon@192.168.1.250 "journalctl -u tabbyapi -f"
```

### Service Won't Start

1. **Check journal for errors**
   ```bash
   journalctl -u tabbyapi -b --no-pager | tail -100
   ```

2. **Common issues**

   **Port already in use:**
   ```bash
   sudo ss -tlnp | grep :5000
   sudo kill $(sudo ss -tlnp | grep :5000 | awk '{print $7}' | cut -d= -f2 | cut -d, -f1)
   sudo systemctl start tabbyapi
   ```

   **Configuration error:**
   ```bash
   # Validate config
   cat /opt/tabbyapi/config.yml
   # Fix and restart
   sudo systemctl restart tabbyapi
   ```

   **Missing dependencies:**
   ```bash
   # Check Python environment
   /opt/tabbyapi/.venv/bin/python --version
   # Reinstall if needed
   cd /opt/tabbyapi && ./install.sh
   ```

3. **View full service definition**
   ```bash
   systemctl cat tabbyapi
   ```

---

## Database Recovery

### PostgreSQL

```bash
ssh root@192.168.1.244

# Check if running
docker exec hydra-postgres pg_isready -U hydra

# Restart
docker restart hydra-postgres

# Connect and check
docker exec -it hydra-postgres psql -U hydra -c "\l"

# If corrupted, restore from backup
docker stop hydra-postgres
cp -r /mnt/user/databases/postgres /mnt/user/databases/postgres.bak
docker start hydra-postgres
```

### Qdrant

```bash
# Check health
curl http://192.168.1.244:6333/health

# Restart
docker restart qdrant

# Check collections
curl http://192.168.1.244:6333/collections | jq '.result.collections[].name'

# If corrupted, restore from snapshot
docker stop qdrant
rm -rf /mnt/user/appdata/qdrant/storage/*
# Copy from backup
cp -r /mnt/user/backups/qdrant/latest/* /mnt/user/appdata/qdrant/storage/
docker start qdrant
```

### Redis

```bash
# Check if responding
docker exec hydra-redis redis-cli -a 'PASSWORD' ping

# Restart
docker restart hydra-redis

# Check memory
docker exec hydra-redis redis-cli -a 'PASSWORD' info memory | grep used_memory_human

# Clear cache if needed (careful!)
docker exec hydra-redis redis-cli -a 'PASSWORD' flushall
```

---

## GPU-Related Issues

### GPU Not Detected

```bash
# Check driver
nvidia-smi

# If fails, reload driver
sudo rmmod nvidia_uvm nvidia_drm nvidia_modeset nvidia
sudo modprobe nvidia

# If still fails, reboot
sudo reboot
```

### GPU Temperature Critical

```bash
# Check temperatures
nvidia-smi --query-gpu=temperature.gpu --format=csv

# Set power limit to reduce heat
sudo nvidia-smi -i 0 -pl 350  # Reduce 5090 power
sudo nvidia-smi -i 1 -pl 250  # Reduce 4090 power

# If still critical
# 1. Stop inference workloads
curl -X POST http://192.168.1.250:5000/v1/model/unload
# 2. Check physical cooling (fans, airflow)
# 3. Wait for cooldown before resuming
```

### CUDA Out of Memory

```bash
# Check VRAM usage
nvidia-smi

# Find processes using VRAM
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv

# Kill orphaned processes
sudo kill -9 <pid>

# Clear CUDA cache
python -c "import torch; torch.cuda.empty_cache()"
```

---

## Network Issues

### Node Unreachable

1. **Check from storage node**
   ```bash
   ssh root@192.168.1.244
   ping -c 3 192.168.1.250  # hydra-ai
   ping -c 3 192.168.1.203  # hydra-compute
   ```

2. **Check via IPMI (hydra-storage only)**
   ```bash
   # Access IPMI web interface
   # http://192.168.1.216
   # Check power state, restart if needed
   ```

3. **Check Tailscale (for remote access)**
   ```bash
   tailscale status
   tailscale ping hydra-ai
   ```

### DNS Issues

```bash
# Test DNS resolution
dig @192.168.1.244 hydra-ai.local

# Check AdGuard
curl http://192.168.1.244:3053/control/status

# Restart AdGuard
docker restart adguardhome
```

---

## Full Node Recovery

### hydra-ai (Critical - Primary Inference)

1. **Verify network connectivity**
   ```bash
   ping -c 3 192.168.1.250
   ```

2. **SSH and check status**
   ```bash
   ssh typhon@192.168.1.250
   systemctl status tabbyapi open-webui
   nvidia-smi
   ```

3. **Restart critical services**
   ```bash
   sudo systemctl restart tabbyapi
   # Wait 2 minutes for model load
   sudo systemctl restart open-webui
   ```

4. **Verify inference working**
   ```bash
   curl -s http://192.168.1.250:5000/v1/model | jq .model_name
   ```

### hydra-storage (Critical - All Docker Services)

1. **Check Unraid Web UI**
   - http://192.168.1.244/Main
   - Check array status, disk health

2. **Verify Docker daemon**
   ```bash
   ssh root@192.168.1.244 "docker info"
   ```

3. **Restart Docker daemon (careful!)**
   ```bash
   ssh root@192.168.1.244 "/etc/rc.d/rc.docker restart"
   ```

4. **Start critical containers first**
   ```bash
   cd /mnt/user/appdata/hydra-stack
   docker-compose up -d postgres redis qdrant
   sleep 30
   docker-compose up -d litellm prometheus grafana
   sleep 30
   docker-compose up -d
   ```

---

## Escalation

If standard recovery fails:

1. **Capture diagnostics**
   ```bash
   # System logs
   journalctl -b > /tmp/journal.log

   # Docker logs
   docker logs --tail=500 <container> > /tmp/container.log

   # GPU state
   nvidia-smi -q > /tmp/gpu.log
   ```

2. **Check recent changes**
   - Git log for config changes
   - Docker image updates
   - NixOS generation rollback available?

3. **Consider rollback**
   ```bash
   # NixOS rollback
   sudo nixos-rebuild switch --rollback

   # Docker image rollback
   docker-compose pull --ignore-pull-failures
   docker-compose up -d
   ```
