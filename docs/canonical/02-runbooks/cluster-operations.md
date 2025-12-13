# Hydra Cluster Operations Runbook

This document is the comprehensive operations manual for the Hydra cluster. It covers daily operations, maintenance, troubleshooting, and emergency procedures.

## Quick Reference

### SSH Access

```bash
# NixOS nodes
ssh typhon@hydra-compute   # 192.168.1.203
ssh typhon@hydra-ai        # 192.168.1.250

# Unraid
ssh root@hydra-storage     # 192.168.1.244

# Via Tailscale (remote)
ssh typhon@100.74.73.44    # hydra-compute
ssh typhon@100.84.120.44   # hydra-ai
ssh root@100.111.54.59     # hydra-storage
```

### Critical Service Ports

| Service | URL | Health Check |
|---------|-----|--------------|
| TabbyAPI | http://192.168.1.250:5000 | `/health` |
| Ollama | http://192.168.1.203:11434 | `/api/tags` |
| LiteLLM | http://192.168.1.244:4000 | `/health` |
| Open WebUI | http://192.168.1.250:3000 | - |
| Grafana | http://192.168.1.244:3003 | `/api/health` |
| Prometheus | http://192.168.1.244:9090 | `/-/healthy` |

### Emergency Commands

```bash
# Restart TabbyAPI (inference down)
ssh typhon@hydra-ai "sudo systemctl restart tabbyapi"

# Restart all containers on Unraid
ssh root@hydra-storage "cd /mnt/user/appdata/hydra-stack && docker-compose restart"

# Check disk space cluster-wide
ssh typhon@hydra-compute "df -h /" && ssh typhon@hydra-ai "df -h /" && ssh root@hydra-storage "df -h /mnt/user"

# Kill runaway GPU process
ssh typhon@hydra-ai "nvidia-smi --query-compute-apps=pid --format=csv,noheader | xargs -I {} kill {}"
```

---

## Daily Operations

### Morning Health Check (5 minutes)

1. **Check Grafana Dashboard**
   - Open http://192.168.1.244:3003
   - Review "Hydra Overview" dashboard
   - Look for: red panels, high CPU/memory, disk warnings

2. **Verify Inference is Working**
   ```bash
   curl -s http://192.168.1.250:5000/v1/model | jq '.model_name'
   # Should return loaded model name

   curl -s http://192.168.1.203:11434/api/tags | jq '.models | length'
   # Should return number > 0
   ```

3. **Check Container Status**
   ```bash
   ssh root@hydra-storage "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -v 'Up'"
   # Should be empty (all containers up)
   ```

### Normal Operating Ranges

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| GPU Temp | <70°C | 70-80°C | >80°C |
| GPU Power (5090) | <400W | 400-450W | >450W |
| GPU Power (4090) | <280W | 280-300W | >300W |
| CPU Usage | <60% | 60-80% | >80% |
| RAM Usage | <70% | 70-85% | >85% |
| Disk Usage | <80% | 80-90% | >90% |
| Inference Latency | <2s | 2-5s | >5s |

---

## Common Tasks

### View Service Logs

```bash
# TabbyAPI logs
ssh typhon@hydra-ai "journalctl -u tabbyapi -f --no-pager -n 100"

# Docker container logs
ssh root@hydra-storage "docker logs <container_name> --tail 100 -f"

# All container logs (brief)
ssh root@hydra-storage "docker ps -q | xargs -I {} docker logs {} --tail 5 2>&1 | head -100"
```

### Restart Services

```bash
# TabbyAPI
ssh typhon@hydra-ai "sudo systemctl restart tabbyapi"

# Ollama
ssh typhon@hydra-compute "sudo systemctl restart ollama"

# Specific Docker container
ssh root@hydra-storage "docker restart <container_name>"

# All containers in stack
ssh root@hydra-storage "cd /mnt/user/appdata/hydra-stack && docker-compose restart"
```

### Check Resource Usage

```bash
# GPU status (both nodes)
ssh typhon@hydra-ai "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw --format=csv"
ssh typhon@hydra-compute "nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw --format=csv"

# Memory usage
ssh typhon@hydra-ai "free -h"
ssh typhon@hydra-compute "free -h"
ssh root@hydra-storage "free -h"

# Disk usage
ssh root@hydra-storage "df -h /mnt/user /mnt/cache"

# Docker disk usage
ssh root@hydra-storage "docker system df"
```

### Model Management

```powershell
# From Windows - use the model utility
.\scripts\hydra-models.ps1 status
.\scripts\hydra-models.ps1 list
.\scripts\hydra-models.ps1 pull llama3.2:3b
```

```bash
# From SSH - Ollama
curl -s http://192.168.1.203:11434/api/tags | jq '.models[].name'

# Pull new model
curl -X POST http://192.168.1.203:11434/api/pull -d '{"name": "gemma2:9b"}'
```

---

## Maintenance Procedures

### Weekly: Docker Cleanup

```bash
ssh root@hydra-storage << 'EOF'
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -f

# Remove unused volumes (careful!)
# docker volume prune -f

# Remove build cache
docker builder prune -f

# Show space reclaimed
docker system df
EOF
```

### Weekly: Log Rotation

```bash
ssh root@hydra-storage << 'EOF'
# Truncate large log files
find /mnt/user/appdata -name "*.log" -size +100M -exec truncate -s 0 {} \;

# Clean old rotated logs
find /mnt/user/appdata -name "*.log.*" -mtime +7 -delete
find /mnt/user/appdata -name "*.log.gz" -mtime +7 -delete
EOF
```

### Monthly: NixOS Updates

```bash
# On each NixOS node
ssh typhon@hydra-compute << 'EOF'
# Check for updates
sudo nix-channel --update

# Build without switching (test)
sudo nixos-rebuild dry-build

# If successful, apply
sudo nixos-rebuild switch

# Verify services
systemctl status ollama
systemctl status prometheus-node-exporter
EOF
```

### Monthly: Docker Image Updates

```bash
ssh root@hydra-storage << 'EOF'
cd /mnt/user/appdata/hydra-stack

# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d

# Remove old images
docker image prune -f
EOF
```

### Monthly: Backup Verification

See `backup-restore-plan.md` for the restore test checklist.

---

## Emergency Procedures

### Node Down

**Symptoms:** Cannot SSH, services unreachable, Prometheus shows target down

**Diagnosis:**
1. Ping the node: `ping 192.168.1.xxx`
2. Check from another node: `ssh typhon@hydra-compute "ping -c 3 192.168.1.250"`
3. Check IPMI (hydra-storage only): `ipmitool -I lanplus -H 192.168.1.216 -U admin power status`

**Resolution:**

| Cause | Action |
|-------|--------|
| Network issue | Check cables, switch, router |
| OS frozen | Physical power cycle or IPMI reset |
| Kernel panic | Check serial console, reboot |
| Full disk | Boot recovery, clear space |

**For hydra-storage (IPMI available):**
```bash
# Check power status
ipmitool -I lanplus -H 192.168.1.216 -U admin -P <password> power status

# Force power cycle
ipmitool -I lanplus -H 192.168.1.216 -U admin -P <password> power cycle
```

### Disk Full

**Symptoms:** Services crashing, "No space left on device" errors

**Immediate Actions:**
```bash
# Find large files
ssh root@hydra-storage "du -sh /mnt/user/*/ | sort -rh | head -10"

# Quick cleanup
ssh root@hydra-storage << 'EOF'
# Docker cleanup
docker system prune -af

# Clear logs
find /mnt/user/appdata -name "*.log" -size +50M -exec truncate -s 0 {} \;

# Find large files
find /mnt/user -type f -size +1G -exec ls -lh {} \;
EOF
```

**Common space consumers:**
- Docker images: `docker image prune -a`
- Build cache: `docker builder prune -a`
- Container logs: Truncate in `/var/lib/docker/containers/*/`
- Old snapshots: Archive to external storage

### GPU Overheating

**Symptoms:** GPU temp >85°C, thermal throttling, slow inference

**Immediate Actions:**
```bash
# Check current temp
ssh typhon@hydra-ai "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"

# Reduce power limit temporarily
ssh typhon@hydra-ai "sudo nvidia-smi -pl 350"  # 5090: reduce from 450W
ssh typhon@hydra-compute "sudo nvidia-smi -pl 180"  # 5070 Ti: reduce from 250W

# Stop inference temporarily
ssh typhon@hydra-ai "sudo systemctl stop tabbyapi"
```

**Investigation:**
- Check case fans running
- Check GPU fans (nvidia-smi shows fan speed)
- Check ambient temperature
- Check for dust buildup

### Service Crash Loop

**Symptoms:** Container constantly restarting, "Restarting (1)" in docker ps

**Diagnosis:**
```bash
# Check container status
ssh root@hydra-storage "docker ps -a | grep <container>"

# View crash logs
ssh root@hydra-storage "docker logs <container> --tail 200"

# Check resource limits
ssh root@hydra-storage "docker inspect <container> | jq '.[0].HostConfig.Memory'"
```

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Config error | Fix config file, restart |
| Missing dependency | Check depends_on, start dependencies first |
| Port conflict | Check `docker ps`, resolve conflicts |
| OOM killed | Increase memory limit or reduce load |
| Corrupt data | Restore from backup or reset |

**Recovery:**
```bash
# Stop the container
ssh root@hydra-storage "docker stop <container>"

# Fix the issue (edit config, etc.)

# Start with fresh state if needed
ssh root@hydra-storage "docker rm <container> && docker-compose up -d <service>"
```

### Network Issues

**Symptoms:** Services unreachable, high latency, packet loss

**Diagnosis:**
```bash
# Test inter-node connectivity
ssh typhon@hydra-compute "ping -c 5 192.168.1.244"
ssh typhon@hydra-compute "ping -c 5 192.168.1.250"

# Check for packet loss
ssh typhon@hydra-compute "mtr -r -c 10 192.168.1.244"

# Check NFS mounts
ssh typhon@hydra-compute "df -h /mnt/models && ls /mnt/models | head"
```

**Common Issues:**

| Issue | Check | Solution |
|-------|-------|----------|
| NFS stale | `mount | grep nfs` | Remount: `sudo umount -l /mnt/models && sudo mount -a` |
| DNS failure | `nslookup hydra-storage` | Check AdGuard, use IPs temporarily |
| Switch issue | Check link lights | Power cycle switch |
| Cable fault | Try different port | Replace cable |

---

## Troubleshooting Guides

### SSH Connection Refused

```bash
# Check if SSH is running
ping 192.168.1.250
nc -zv 192.168.1.250 22

# If reachable but SSH refused, may need console access
# Check from another node
ssh typhon@hydra-compute "ssh -v typhon@192.168.1.250"
```

### TabbyAPI Not Loading Model

```bash
# Check service status
ssh typhon@hydra-ai "systemctl status tabbyapi"

# Check logs for errors
ssh typhon@hydra-ai "journalctl -u tabbyapi -n 100 --no-pager"

# Check GPU memory
ssh typhon@hydra-ai "nvidia-smi"

# Check model path exists
ssh typhon@hydra-ai "ls -la /mnt/models/exl2/"

# Verify NFS mount
ssh typhon@hydra-ai "df -h /mnt/models"
```

**Common causes:**
- Insufficient VRAM: Use smaller quantization
- Corrupt model files: Re-download
- NFS mount stale: Remount
- Config syntax error: Check YAML

### Container Won't Start

```bash
# Check why it exited
ssh root@hydra-storage "docker logs <container> 2>&1 | tail -50"

# Check for port conflicts
ssh root@hydra-storage "docker ps -a --format 'table {{.Names}}\t{{.Ports}}' | grep <port>"
ssh root@hydra-storage "ss -tlnp | grep <port>"

# Check volume mounts
ssh root@hydra-storage "docker inspect <container> | jq '.[0].Mounts'"

# Try interactive start
ssh root@hydra-storage "docker run -it --rm <image> /bin/sh"
```

### High Memory Usage

```bash
# Find memory hogs
ssh typhon@hydra-ai "ps aux --sort=-%mem | head -10"

# Check for memory leaks in containers
ssh root@hydra-storage "docker stats --no-stream"

# Clear system caches (safe)
ssh typhon@hydra-ai "sync && echo 3 | sudo tee /proc/sys/vm/drop_caches"
```

### Slow Inference

**Diagnosis:**
```bash
# Check GPU utilization
ssh typhon@hydra-ai "nvidia-smi dmon -s u -d 1 -c 5"

# Check if swapping to disk
ssh typhon@hydra-ai "vmstat 1 5"

# Check model context length (longer = slower)
curl -s http://192.168.1.250:5000/v1/model | jq '.max_seq_len'
```

**Optimization:**
- Reduce max_tokens in requests
- Use smaller model or higher quantization
- Check for competing GPU processes
- Verify power limits are set correctly

---

## Service Dependencies

```
                    ┌─────────────┐
                    │   AdGuard   │
                    │    (DNS)    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   NFS/SMB    │  │  PostgreSQL  │  │    Redis     │
│  (storage)   │  │   (state)    │  │   (cache)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────────────────────────────────────────┐
│                   LiteLLM                        │
│               (API Gateway)                      │
└──────────────────────┬───────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   TabbyAPI   │ │  Ollama  │ │   Qdrant     │
│  (primary)   │ │ (second) │ │  (vectors)   │
└──────────────┘ └──────────┘ └──────────────┘
        │              │
        ▼              ▼
┌──────────────────────────────────────────────────┐
│              User Interfaces                     │
│   Open WebUI, SillyTavern, API Clients          │
└──────────────────────────────────────────────────┘
```

**Startup Order:**
1. Network/DNS (AdGuard)
2. Storage (NFS exports)
3. Databases (PostgreSQL, Redis, Qdrant)
4. Inference (TabbyAPI, Ollama)
5. Routing (LiteLLM)
6. Frontends (Open WebUI, etc.)

---

## Appendix: Command Cheat Sheet

### One-Liners

```bash
# Cluster health summary
for h in hydra-compute hydra-ai hydra-storage; do echo "=== $h ==="; ssh $([ $h = hydra-storage ] && echo root || echo typhon)@$h "uptime; df -h / | tail -1"; done

# GPU status all nodes
ssh typhon@hydra-compute "nvidia-smi --query-gpu=name,memory.used,temperature.gpu --format=csv" && ssh typhon@hydra-ai "nvidia-smi --query-gpu=name,memory.used,temperature.gpu --format=csv"

# Container status
ssh root@hydra-storage "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20"

# Quick inference test
curl -s http://192.168.1.244:4000/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7" -d '{"model":"gpt-4","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' | jq -r '.choices[0].message.content'
```

### PowerShell Shortcuts

```powershell
# Add to PowerShell profile for quick access
function hydra-status { ssh typhon@hydra-ai "nvidia-smi --query-gpu=name,memory.used,temperature.gpu --format=csv"; ssh root@hydra-storage "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10" }
function hydra-logs { param($container) ssh root@hydra-storage "docker logs $container --tail 50 -f" }
function hydra-restart { param($service) ssh root@hydra-storage "docker restart $service" }
```

---

*Last updated: 2025-12-13*
