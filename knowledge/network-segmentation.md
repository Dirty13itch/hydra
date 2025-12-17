# Hydra Network Segmentation

## Overview

Docker network segmentation provides isolation between service tiers, improving security and reducing blast radius of potential issues.

## Network Architecture

| Network | Subnet | Purpose | Services |
|---------|--------|---------|----------|
| hydra-infra | 172.30.0.0/24 | Infrastructure & monitoring | prometheus, grafana, alertmanager, loki, promtail |
| hydra-ai-services | 172.30.1.0/24 | AI/inference services | litellm, letta, crewai, docling, hydra-tools-api |
| hydra-apps | 172.30.2.0/24 | User-facing applications | open-webui, sillytavern, perplexica, homepage |
| hydra-databases | 172.30.3.0/24 | Data stores | postgres, qdrant, neo4j, redis |
| hydra-network | default | Legacy/migration | Existing services during migration |
| download-stack_default | default | Media automation | sonarr, radarr, prowlarr, etc. |

## Inter-Network Communication

Services that need cross-network access should be connected to multiple networks:

### Gateway Services (multi-network)
- **hydra-litellm**: hydra-ai-services + hydra-apps (API gateway)
- **hydra-postgres**: hydra-databases + hydra-ai-services (shared DB)
- **hydra-grafana**: hydra-infra + hydra-apps (dashboards)

## Migration Plan

### Phase 1: Infrastructure Services
```bash
# Move monitoring stack to hydra-infra
docker network connect hydra-infra hydra-prometheus
docker network connect hydra-infra hydra-grafana
docker network connect hydra-infra hydra-alertmanager
docker network connect hydra-infra hydra-loki
docker network connect hydra-infra hydra-promtail
```

### Phase 2: Database Layer
```bash
# Move databases to hydra-databases
docker network connect hydra-databases hydra-postgres
docker network connect hydra-databases hydra-qdrant
docker network connect hydra-databases hydra-neo4j
docker network connect hydra-databases hydra-redis
```

### Phase 3: AI Services
```bash
# Move AI services to hydra-ai-services
docker network connect hydra-ai-services hydra-litellm
docker network connect hydra-ai-services hydra-letta
docker network connect hydra-ai-services hydra-tools-api
docker network connect hydra-ai-services hydra-crewai
docker network connect hydra-ai-services hydra-docling
```

### Phase 4: User Apps
```bash
# Move user-facing apps to hydra-apps
docker network connect hydra-apps open-webui
docker network connect hydra-apps sillytavern
docker network connect hydra-apps homepage
```

## Firewall Rules (Future)

For additional isolation, consider iptables rules between networks:
- hydra-databases: Only accept connections from hydra-ai-services and hydra-infra
- hydra-ai-services: Accept from hydra-apps, hydra-infra
- hydra-apps: Accept from external (user traffic)
- hydra-infra: Accept from all internal networks

## Verification

Check network connectivity:
```bash
# List networks
docker network ls --filter "name=hydra-"

# Inspect network
docker network inspect hydra-ai-services

# Check container networks
docker inspect --format '{{.NetworkSettings.Networks}}' hydra-litellm
```
