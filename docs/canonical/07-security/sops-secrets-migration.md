# SOPS Secrets Migration Plan

## Overview

This document outlines the migration of Hydra cluster secrets from plaintext in docker-compose files to encrypted secrets using SOPS (Secrets OPerationS) with age encryption.

## Current State

Secrets are currently stored in plaintext in:
- `docker-compose.yml` files on hydra-storage
- Environment variables in container configs
- NixOS configuration.nix on hydra-ai and hydra-compute
- `.env` files (gitignored but still plaintext on disk)

### Secrets Inventory

| Secret | Current Location | Service |
|--------|-----------------|---------|
| PostgreSQL password | docker-compose.yml | hydra-postgres |
| Redis password | docker-compose.yml | hydra-redis |
| LiteLLM master key | docker-compose.yml | hydra-litellm |
| LiteLLM salt key | docker-compose.yml | hydra-litellm |
| Meilisearch key | docker-compose.yml | hydra-meilisearch |
| Grafana admin password | docker-compose.yml | hydra-grafana |
| Miniflux credentials | docker-compose.yml | hydra-miniflux |
| Vaultwarden admin token | docker-compose.yml | hydra-vaultwarden |
| VPN credentials | docker-compose.yml | hydra-gluetun |
| Discord webhook URL | docker-compose.yml | n8n workflows |
| SSH keys | ~/.ssh/ | All nodes |

## Target State

All secrets encrypted at rest using SOPS with age encryption:
- Secrets stored in `secrets.yaml` files
- Encrypted in git repository
- Decrypted only at runtime on authorized hosts
- Host-specific keys derived from SSH host keys

## Prerequisites

✅ **Already Installed:**
- SOPS on hydra-ai and hydra-compute (via NixOS)
- age on hydra-ai and hydra-compute (via NixOS)
- SSH keys on all nodes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Secret Distribution                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Git Repository                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  secrets/                                                 │  │
│   │  ├── .sops.yaml              # SOPS config (plaintext)   │  │
│   │  ├── secrets.yaml            # Encrypted secrets          │  │
│   │  ├── hydra-ai.yaml           # Node-specific secrets      │  │
│   │  ├── hydra-compute.yaml      # Node-specific secrets      │  │
│   │  └── hydra-storage.yaml      # Node-specific secrets      │  │
│   └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│   │  hydra-ai   │   │hydra-compute│   │hydra-storage│          │
│   │             │   │             │   │             │          │
│   │ age key from│   │ age key from│   │ age key from│          │
│   │ SSH host key│   │ SSH host key│   │ SSH host key│          │
│   │             │   │             │   │             │          │
│   │ Decrypts:   │   │ Decrypts:   │   │ Decrypts:   │          │
│   │ - common    │   │ - common    │   │ - common    │          │
│   │ - hydra-ai  │   │ - compute   │   │ - storage   │          │
│   └─────────────┘   └─────────────┘   └─────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Migration Steps

### Phase 1: Key Setup (Day 1)

#### 1.1 Generate age keys from SSH host keys

```bash
# On each NixOS node (hydra-ai, hydra-compute)
ssh-to-age -i /etc/ssh/ssh_host_ed25519_key.pub

# For hydra-storage (Unraid), generate a new age key
# On hydra-storage:
mkdir -p /mnt/user/appdata/sops
age-keygen -o /mnt/user/appdata/sops/age.key

# Note the public keys for .sops.yaml
```

#### 1.2 Create .sops.yaml configuration

```yaml
# secrets/.sops.yaml
creation_rules:
  # Common secrets - encrypted for all nodes
  - path_regex: secrets\.yaml$
    key_groups:
      - age:
          - age1hydra_ai_public_key_here
          - age1hydra_compute_public_key_here
          - age1hydra_storage_public_key_here

  # Node-specific secrets
  - path_regex: hydra-ai\.yaml$
    key_groups:
      - age:
          - age1hydra_ai_public_key_here

  - path_regex: hydra-compute\.yaml$
    key_groups:
      - age:
          - age1hydra_compute_public_key_here

  - path_regex: hydra-storage\.yaml$
    key_groups:
      - age:
          - age1hydra_storage_public_key_here
```

### Phase 2: Create Encrypted Secrets (Day 1-2)

#### 2.1 Create secrets template

```yaml
# secrets/secrets.yaml (before encryption)
databases:
  postgres:
    user: hydra
    password: GENERATE_NEW_PASSWORD
    databases:
      - hydra
      - litellm
      - n8n
      - miniflux

  redis:
    password: GENERATE_NEW_PASSWORD

  meilisearch:
    api_key: GENERATE_NEW_KEY

ai_services:
  litellm:
    master_key: GENERATE_NEW_KEY
    salt_key: GENERATE_NEW_KEY

observability:
  grafana:
    admin_password: GENERATE_NEW_PASSWORD

content:
  miniflux:
    admin_user: admin
    admin_password: GENERATE_NEW_PASSWORD

security:
  vaultwarden:
    admin_token: GENERATE_NEW_TOKEN

notifications:
  discord:
    webhook_url: ""  # Optional, set when needed

vpn:
  provider: mullvad
  wireguard_private_key: ""
  wireguard_addresses: ""
```

#### 2.2 Generate new secrets

```bash
# Generate cryptographically secure passwords
openssl rand -base64 32  # For passwords
openssl rand -hex 32      # For API keys
```

#### 2.3 Encrypt secrets file

```bash
cd secrets/
sops --encrypt --in-place secrets.yaml
```

### Phase 3: Update Docker Compose (Day 2-3)

#### 3.1 Create docker-compose secrets integration

```yaml
# docker-compose/secrets-loader.yml
# Use with: docker-compose -f hydra-stack.yml -f secrets-loader.yml up -d

version: "3.9"

secrets:
  postgres_password:
    file: /mnt/user/appdata/sops/decrypted/postgres_password
  redis_password:
    file: /mnt/user/appdata/sops/decrypted/redis_password
  litellm_master_key:
    file: /mnt/user/appdata/sops/decrypted/litellm_master_key

services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password

  redis:
    command: >
      sh -c 'redis-server --requirepass "$$(cat /run/secrets/redis_password)"'
    secrets:
      - redis_password
```

#### 3.2 Create decryption script for hydra-storage

```bash
#!/bin/bash
# /mnt/user/appdata/sops/decrypt-secrets.sh

SOPS_AGE_KEY_FILE=/mnt/user/appdata/sops/age.key
SECRETS_DIR=/mnt/user/appdata/sops
DECRYPTED_DIR=/mnt/user/appdata/sops/decrypted

mkdir -p "$DECRYPTED_DIR"
chmod 700 "$DECRYPTED_DIR"

# Decrypt and extract individual secrets
sops -d "$SECRETS_DIR/secrets.yaml" | yq -r '.databases.postgres.password' > "$DECRYPTED_DIR/postgres_password"
sops -d "$SECRETS_DIR/secrets.yaml" | yq -r '.databases.redis.password' > "$DECRYPTED_DIR/redis_password"
sops -d "$SECRETS_DIR/secrets.yaml" | yq -r '.ai_services.litellm.master_key' > "$DECRYPTED_DIR/litellm_master_key"
# ... add more as needed

chmod 600 "$DECRYPTED_DIR"/*
```

### Phase 4: NixOS Integration (Day 3-4)

#### 4.1 Update NixOS configuration

```nix
# /etc/nixos/sops.nix
{ config, pkgs, ... }:

{
  sops = {
    defaultSopsFile = ./secrets/hydra-ai.yaml;
    age = {
      sshKeyPaths = [ "/etc/ssh/ssh_host_ed25519_key" ];
      keyFile = "/var/lib/sops-nix/key.txt";
      generateKey = true;
    };

    secrets = {
      "tabbyapi/admin_key" = {
        owner = "tabbyapi";
      };
    };
  };

  # Use secret in service
  systemd.services.tabbyapi = {
    environment = {
      ADMIN_KEY_FILE = config.sops.secrets."tabbyapi/admin_key".path;
    };
  };
}
```

### Phase 5: Rotate Secrets (Day 4-5)

#### 5.1 Secret rotation procedure

```bash
# 1. Generate new secret
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Edit encrypted file
sops secrets/secrets.yaml
# Update the password

# 3. Re-decrypt on target hosts
./decrypt-secrets.sh

# 4. Update service
# For PostgreSQL:
docker exec hydra-postgres psql -U hydra -c "ALTER USER hydra PASSWORD 'new_password';"

# 5. Restart dependent services
docker-compose restart litellm n8n
```

### Phase 6: Verification (Day 5)

#### 6.1 Verify encryption

```bash
# Ensure secrets.yaml is encrypted
cat secrets/secrets.yaml
# Should show SOPS metadata and encrypted values

# Verify git doesn't contain plaintext
git log -p -- '*.yml' '*.yaml' | grep -i password
# Should return nothing sensitive
```

#### 6.2 Verify decryption works

```bash
# On each node
sops -d secrets/secrets.yaml | head -20
# Should show decrypted values
```

#### 6.3 Verify services work

```bash
# Test database connections
docker exec hydra-postgres pg_isready -U hydra
docker exec hydra-redis redis-cli -a "$(cat /mnt/user/appdata/sops/decrypted/redis_password)" ping
curl -H "Authorization: Bearer $(cat /mnt/user/appdata/sops/decrypted/litellm_master_key)" http://192.168.1.244:4000/health
```

## Rollback Plan

If issues occur during migration:

1. **Keep backup of current .env files** before migration
2. **Git revert** if encrypted secrets cause issues
3. **Restore from backup** container configs from `/mnt/user/appdata/` backups

```bash
# Emergency rollback
docker-compose down
cp .env.backup .env
docker-compose up -d
```

## Security Considerations

1. **age key protection**: The age private key on hydra-storage must be protected
   - Stored in `/mnt/user/appdata/sops/` (not backed up off-site without encryption)
   - Permission 600
   - Consider hardware key in future

2. **Git history**: Old commits may contain plaintext secrets
   - Consider repository with fresh history after migration
   - Or use git-filter-branch to remove sensitive history

3. **Memory exposure**: Decrypted secrets exist in memory/tmpfs
   - Use Docker secrets with `/run/secrets/` when possible
   - Avoid logging secrets

4. **Backup encryption**: Ensure database backups are encrypted
   - Use SOPS for backup encryption keys
   - Store backup keys separately from data

## Timeline

| Day | Task | Duration |
|-----|------|----------|
| 1 | Key setup, .sops.yaml | 2 hours |
| 1-2 | Create and encrypt secrets | 2 hours |
| 2-3 | Update docker-compose | 3 hours |
| 3-4 | NixOS integration | 2 hours |
| 4-5 | Secret rotation | 2 hours |
| 5 | Verification | 1 hour |

**Total estimated time: ~12 hours**

## Monitoring

After migration, monitor for:
- Service startup failures (authentication errors)
- Database connection issues
- API authentication failures
- n8n workflow failures

Add Prometheus alerts for authentication failures:
```yaml
- alert: ServiceAuthFailure
  expr: increase(http_requests_total{status="401"}[5m]) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High authentication failure rate"
```

## References

- [SOPS Documentation](https://github.com/getsops/sops)
- [age Encryption](https://github.com/FiloSottile/age)
- [sops-nix](https://github.com/Mic92/sops-nix)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
