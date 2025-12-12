# Deploy Phase 1: Foundation Layer

Execute the complete Phase 1 deployment for the Hydra cluster. This includes databases, observability, and the LiteLLM API gateway.

## Prerequisites Check
First, verify:
1. hydra-storage (192.168.1.244) is accessible via SSH
2. Docker is running on Unraid
3. /mnt/user/appdata directory exists

## Step 1: Create Directory Structure
```bash
ssh root@192.168.1.244 "mkdir -p /mnt/user/appdata/hydra-stack/{prometheus/alerts,grafana/provisioning/datasources,loki,alertmanager} /mnt/user/databases/{postgres,redis,qdrant,minio}"
```

## Step 2: Create Environment File
Create `/mnt/user/appdata/hydra-stack/.env` with secure passwords:
- POSTGRES_PASSWORD (generate random 32 char)
- MINIO_USER: admin
- MINIO_PASSWORD (generate random 32 char)
- LITELLM_KEY: sk-hydra-local
- GRAFANA_PASSWORD (generate random 16 char)
- N8N_ENCRYPTION_KEY (generate random 32 char)
- UNRAID_IP: 192.168.1.244
- HYDRA_AI_IP: 192.168.1.250
- HYDRA_COMPUTE_IP: 192.168.1.203

## Step 3: Create Docker Compose
Create `/mnt/user/appdata/hydra-stack/docker-compose.yml` with:
- PostgreSQL 16 on port 5432
- Redis 7 on port 6379
- Qdrant on ports 6333/6334
- MinIO on ports 9000/9001
- Prometheus on port 9090
- Grafana on port 3003
- Loki on port 3100
- Uptime Kuma on port 3001
- AlertManager on port 9093
- LiteLLM on port 4000

Use the configs from @knowledge/databases.md and @knowledge/observability.md

## Step 4: Create Prometheus Config
Create `/mnt/user/appdata/hydra-stack/prometheus/prometheus.yml` with scrape configs for:
- Prometheus self
- Node exporters (all 3 nodes on :9100)
- GPU metrics (hydra-ai and hydra-compute on :9400)
- TabbyAPI (hydra-ai:5000)
- LiteLLM (localhost:4000)

## Step 5: Create Grafana Datasource
Create `/mnt/user/appdata/hydra-stack/grafana/provisioning/datasources/datasources.yml`:
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
```

## Step 6: Create LiteLLM Config
Create `/mnt/user/appdata/hydra-stack/litellm/config.yaml`:
```yaml
model_list:
  - model_name: hydra-70b
    litellm_params:
      model: openai/default
      api_base: http://192.168.1.250:5000/v1
      api_key: none
  - model_name: hydra-fast
    litellm_params:
      model: ollama/qwen2.5:14b
      api_base: http://192.168.1.203:11434
  - model_name: hydra-embed
    litellm_params:
      model: ollama/nomic-embed-text
      api_base: http://192.168.1.203:11434

general_settings:
  master_key: sk-hydra-local
```

## Step 7: Deploy Services
```bash
ssh root@192.168.1.244 "cd /mnt/user/appdata/hydra-stack && docker-compose up -d"
```

## Step 8: Wait for Services
Wait 30 seconds for containers to initialize, then verify.

## Step 9: Create Databases
```bash
ssh root@192.168.1.244 "docker exec hydra-postgres psql -U hydra -c 'CREATE DATABASE n8n;' && docker exec hydra-postgres psql -U hydra -c 'CREATE DATABASE litellm;' && docker exec hydra-postgres psql -U hydra -c 'CREATE DATABASE grafana;'"
```

## Step 10: Verify Each Service
Run health checks:
```bash
# PostgreSQL
docker exec hydra-postgres pg_isready -U hydra

# Redis
docker exec hydra-redis redis-cli ping

# Qdrant
curl -s http://192.168.1.244:6333/health

# Prometheus
curl -s http://192.168.1.244:9090/-/healthy

# Grafana
curl -s http://192.168.1.244:3003/api/health

# LiteLLM
curl -s http://192.168.1.244:4000/health

# Uptime Kuma
curl -s http://192.168.1.244:3001
```

## Step 11: Test LiteLLM Routing
```bash
curl -X POST http://192.168.1.244:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-hydra-local" \
  -d '{"model": "hydra-70b", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 20}'
```

## Step 12: Report Status
Report which services are healthy and which failed. Include:
- Container status (running/stopped)
- Health check results
- Any error messages from logs
- Suggested fixes for failures

## Rollback Procedure
If deployment fails:
```bash
ssh root@192.168.1.244 "cd /mnt/user/appdata/hydra-stack && docker-compose down && docker-compose logs > /tmp/deploy-failure.log"
```

## Success Criteria
Phase 1 is complete when:
- [ ] All containers show "healthy" or "running"
- [ ] PostgreSQL accepts connections
- [ ] Redis responds to PING
- [ ] Qdrant health endpoint returns OK
- [ ] Prometheus shows all targets UP
- [ ] Grafana is accessible
- [ ] LiteLLM routes to TabbyAPI successfully

## Next Phase
After Phase 1 completion, proceed to Phase 2: Automation & Knowledge
- Deploy n8n
- Deploy SearXNG
- Deploy Firecrawl
- Set up embedding pipeline
