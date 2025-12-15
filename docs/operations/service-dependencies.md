# Hydra Cluster Service Dependencies

This document maps service dependencies and defines the correct startup order for disaster recovery.

## Dependency Graph

```
                                    ┌─────────────┐
                                    │   Network   │
                                    │   (Layer 0) │
                                    └──────┬──────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
       ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
       │  hydra-ai   │              │hydra-compute│              │hydra-storage│
       │  (NixOS)    │              │  (NixOS)    │              │  (Unraid)   │
       └──────┬──────┘              └──────┬──────┘              └──────┬──────┘
              │                            │                            │
              │                            │                    ┌───────┴───────┐
              │                            │                    │               │
              │                            │                    ▼               │
              │                            │             ┌─────────────┐        │
              │                            │             │  Databases  │        │
              │                            │             │  (Layer 1)  │        │
              │                            │             │ PostgreSQL  │        │
              │                            │             │   Redis     │        │
              │                            │             │   Qdrant    │        │
              │                            │             └──────┬──────┘        │
              │                            │                    │               │
              │                            │                    ▼               │
              │                            │             ┌─────────────┐        │
              │                            │             │Observability│        │
              │                            │             │  (Layer 2)  │        │
              │                            │             │ Prometheus  │        │
              │                            │             │   Loki      │        │
              │                            │             │  Grafana    │        │
              │                            │             └──────┬──────┘        │
              │                            │                    │               │
              ▼                            ▼                    ▼               │
       ┌─────────────┐              ┌─────────────┐      ┌─────────────┐        │
       │  TabbyAPI   │              │   Ollama    │      │  LiteLLM    │        │
       │  (Layer 3)  │              │  (Layer 3)  │      │  (Layer 3)  │        │
       └──────┬──────┘              └──────┬──────┘      └──────┬──────┘        │
              │                            │                    │               │
              └────────────────────────────┼────────────────────┘               │
                                           │                                    │
                                           ▼                                    │
                                    ┌─────────────┐                             │
                                    │   UIs &     │                             │
                                    │ Automation  │                             │
                                    │  (Layer 4)  │◄────────────────────────────┘
                                    │ Open WebUI  │
                                    │    n8n      │
                                    │ SillyTavern │
                                    └─────────────┘
```

## Startup Order (Disaster Recovery)

### Layer 0: Network Foundation
**Must be running first**

| Service | Node | How to Start | Verification |
|---------|------|--------------|--------------|
| Physical Network | - | Check cables, switches | `ping 192.168.1.1` |
| Unraid | hydra-storage | Power on, wait for boot | IPMI or `ping 192.168.1.244` |
| NixOS nodes | hydra-ai, compute | Power on | `ping 192.168.1.250/203` |
| AdGuard DNS | hydra-storage | `docker start hydra-adguard` | `dig @192.168.1.244 google.com` |

### Layer 1: Databases
**Required by most services**

| Service | Node | Dependencies | Start Command | Verification |
|---------|------|--------------|---------------|--------------|
| PostgreSQL | hydra-storage | Network | `docker start hydra-postgres` | `docker exec hydra-postgres pg_isready` |
| Redis | hydra-storage | Network | `docker start hydra-redis` | `docker exec hydra-redis redis-cli ping` |
| Qdrant | hydra-storage | Network | `docker start hydra-qdrant` | `curl http://192.168.1.244:6333/health` |
| Meilisearch | hydra-storage | Network | `docker start hydra-meilisearch` | `curl http://192.168.1.244:7700/health` |

**Wait 30 seconds after starting databases before proceeding.**

### Layer 2: Observability
**Recommended but not blocking**

| Service | Node | Dependencies | Start Command | Verification |
|---------|------|--------------|---------------|--------------|
| Prometheus | hydra-storage | Network | `docker start hydra-prometheus` | `curl http://192.168.1.244:9090/-/healthy` |
| Loki | hydra-storage | Network | `docker start hydra-loki` | `curl http://192.168.1.244:3100/ready` |
| Grafana | hydra-storage | PostgreSQL | `docker start hydra-grafana` | `curl http://192.168.1.244:3003/api/health` |

### Layer 3: Inference Services
**Core AI functionality**

| Service | Node | Dependencies | Start Command | Verification |
|---------|------|--------------|---------------|--------------|
| TabbyAPI | hydra-ai | NFS mounts | `sudo systemctl start tabbyapi` | `curl http://192.168.1.250:5000/health` |
| Ollama | hydra-compute | NFS mounts | `sudo systemctl start ollama` | `curl http://192.168.1.203:11434/api/tags` |
| LiteLLM | hydra-storage | Redis, PostgreSQL | `docker start hydra-litellm` | `curl http://192.168.1.244:4000/health` |
| ComfyUI | hydra-compute | NFS mounts | `sudo systemctl start comfyui` | `curl http://192.168.1.203:8188/system_stats` |

**Note:** TabbyAPI may take 2-5 minutes to load a 70B model.

### Layer 4: Applications & UIs
**User-facing services**

| Service | Node | Dependencies | Start Command | Verification |
|---------|------|--------------|---------------|--------------|
| Open WebUI | hydra-ai | LiteLLM, PostgreSQL | `docker start hydra-open-webui` | `curl http://192.168.1.250:3000` |
| n8n | hydra-storage | PostgreSQL, Redis | `docker start hydra-n8n` | `curl http://192.168.1.244:5678/healthz` |
| SillyTavern | hydra-storage | TabbyAPI or Ollama | `docker start hydra-sillytavern` | `curl http://192.168.1.244:8000` |
| SearXNG | hydra-storage | Network | `docker start hydra-searxng` | `curl http://192.168.1.244:8888/healthz` |
| Perplexica | hydra-storage | SearXNG, LiteLLM | `docker start hydra-perplexica` | `curl http://192.168.1.244:3030` |

### Layer 5: Optional/Media
**Non-critical services**

| Service | Dependencies | Start Command |
|---------|--------------|---------------|
| Sonarr/Radarr/Prowlarr | PostgreSQL | `docker-compose -f media-stack.yml up -d` |
| Home Assistant | Network | `docker start homeassistant` |
| Plex | Storage | `docker start plex` |

## Dependency Details

### PostgreSQL (Critical)
**Depends on:** Nothing (self-contained)
**Required by:**
- Grafana (dashboards, users)
- n8n (workflow storage)
- Open WebUI (chat history)
- LiteLLM (spend tracking)
- Letta (agent memory)
- Sonarr/Radarr (media database)

### Redis (Critical)
**Depends on:** Nothing
**Required by:**
- LiteLLM (caching, rate limiting)
- n8n (queue, sessions)
- Open WebUI (sessions)
- Celery workers

### Qdrant (Important)
**Depends on:** Nothing
**Required by:**
- Knowledge search
- RAG pipelines
- Letta (vector memory)
- Perplexica (search embeddings)

### LiteLLM (Important)
**Depends on:** Redis, PostgreSQL
**Required by:**
- Open WebUI (default backend)
- n8n workflows
- Perplexica
- Any OpenAI-compatible client

### TabbyAPI (Critical)
**Depends on:** NFS mounts for models
**Required by:**
- LiteLLM (as backend)
- Direct API users
- 70B+ model inference

### NFS Mounts (Critical for inference)
**Location:** hydra-storage exports
**Mounted on:** hydra-ai, hydra-compute
**Contains:** Model files, shared data
**Check:** `df -h /mnt/models`

## Recovery Scripts

### Full Cluster Restart
```bash
#!/bin/bash
# full-restart.sh - Execute from any machine with SSH access

echo "=== Layer 0: Network ==="
ping -c 1 192.168.1.244 || { echo "hydra-storage not reachable"; exit 1; }
ping -c 1 192.168.1.250 || echo "hydra-ai not reachable"
ping -c 1 192.168.1.203 || echo "hydra-compute not reachable"

echo "=== Layer 1: Databases ==="
ssh root@192.168.1.244 "docker start hydra-postgres hydra-redis hydra-qdrant"
sleep 30

echo "=== Layer 2: Observability ==="
ssh root@192.168.1.244 "docker start hydra-prometheus hydra-loki hydra-grafana"
sleep 10

echo "=== Layer 3: Inference ==="
ssh typhon@192.168.1.250 "sudo systemctl start tabbyapi"
ssh typhon@192.168.1.203 "sudo systemctl start ollama comfyui"
ssh root@192.168.1.244 "docker start hydra-litellm"
sleep 60  # Wait for model loading

echo "=== Layer 4: Applications ==="
ssh root@192.168.1.244 "docker start hydra-n8n hydra-searxng hydra-open-webui hydra-sillytavern"

echo "=== Verification ==="
curl -s http://192.168.1.244:8600/health/summary | jq .
```

### Emergency: Databases Only
```bash
ssh root@192.168.1.244 "
  docker start hydra-postgres hydra-redis hydra-qdrant &&
  sleep 10 &&
  docker exec hydra-postgres pg_isready &&
  docker exec hydra-redis redis-cli ping &&
  curl -s http://localhost:6333/health
"
```

### Emergency: Inference Only
```bash
# When you just need LLM running fast
ssh typhon@192.168.1.250 "sudo systemctl restart tabbyapi"
# Or use Ollama as fallback
ssh typhon@192.168.1.203 "sudo systemctl restart ollama"
```

## Troubleshooting

### Service Won't Start

1. **Check dependencies first**
   ```bash
   docker logs <container> 2>&1 | tail -20
   ```

2. **Database connection issues**
   ```bash
   docker exec hydra-postgres pg_isready
   docker exec hydra-redis redis-cli -a $REDIS_PASS ping
   ```

3. **NFS mount issues**
   ```bash
   ssh typhon@192.168.1.250 "df -h /mnt/models && ls /mnt/models"
   ```

### Circular Dependency Warning

Some services have soft circular dependencies:
- Grafana → Prometheus (for datasource) → Node Exporter (on Grafana host)

**Resolution:** Start in dependency order, ignore initial datasource errors in Grafana.

## Contact for Emergencies

- **IPMI Access (hydra-storage):** http://192.168.1.216
- **Unraid Web UI:** http://192.168.1.244
- **Portainer:** http://192.168.1.244:9000
