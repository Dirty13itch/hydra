# Backup & Restore Plan for Hydra Cluster

This document defines the backup strategy, implementation, and monthly restore test procedures.

## 3-2-1 Backup Strategy

| Rule | Implementation |
|------|----------------|
| **3 copies** | Primary (Unraid array) + Parity + Offsite/Cloud |
| **2 media types** | HDDs (array) + SSDs (cache) + Cloud storage |
| **1 offsite** | Cloud backup (Backblaze B2 or similar) |

## Data Classification

### Tier 1: Critical (Daily Backup)

| Data | Location | Size Est. | Notes |
|------|----------|-----------|-------|
| Docker appdata | `/mnt/user/appdata/` | ~50GB | All container configs |
| Databases | `/mnt/user/databases/` | ~10GB | PostgreSQL, Qdrant |
| NixOS configs | `/etc/nixos/` | <1MB | On compute + ai nodes |
| Hydra repo | `C:\Users\shaun\projects\hydra` | <100MB | Git, canonical docs |
| Vaultwarden | `/mnt/user/appdata/vaultwarden/` | <1GB | Password vault |

### Tier 2: Important (Weekly Backup)

| Data | Location | Size Est. | Notes |
|------|----------|-----------|-------|
| Home Assistant | `/mnt/user/appdata/homeassistant/` | ~2GB | Automations, history |
| n8n workflows | `/mnt/user/appdata/n8n/` | <1GB | Automation workflows |
| Grafana dashboards | `/mnt/user/appdata/grafana/` | <500MB | Custom dashboards |

### Tier 3: Replaceable (Monthly/No Backup)

| Data | Location | Size Est. | Notes |
|------|----------|-----------|-------|
| AI Models | `/mnt/user/models/` | ~500GB | Re-downloadable from HF |
| Media | `/mnt/user/media/` | ~100TB | Can be re-acquired |
| Docker images | - | ~20GB | Pulled from registries |

## Backup Implementation

### Unraid Built-in: Appdata Backup

1. Install "Appdata Backup" plugin from Community Applications
2. Configure:
   - Source: `/mnt/user/appdata/`
   - Destination: `/mnt/user/backups/appdata/`
   - Schedule: Daily at 4:00 AM (after snapshot script)
   - Retention: 7 daily, 4 weekly
   - Compression: Yes (tar.gz)

### NixOS Configs: Git + Sync

On each NixOS node, configs are version controlled:

```bash
# Already tracked in /etc/nixos (git init if not)
cd /etc/nixos
git add -A && git commit -m "config: $(date +%Y-%m-%d)"

# Sync to hydra-storage
rsync -avz /etc/nixos/ root@hydra-storage:/mnt/user/backups/nixos/$(hostname)/
```

Add to cron on each NixOS node:
```bash
0 4 * * * cd /etc/nixos && git add -A && git commit -m "auto: $(date +\%Y-\%m-\%d)" 2>/dev/null; rsync -avz /etc/nixos/ root@hydra-storage:/mnt/user/backups/nixos/$(hostname)/
```

### Database Backups

#### PostgreSQL Daily Dump

```bash
# Add to hydra-storage cron
0 3 * * * docker exec hydra-postgres pg_dumpall -U hydra | gzip > /mnt/user/backups/postgres/pg_dump_$(date +\%Y\%m\%d).sql.gz

# Retention: keep 7 days
7 3 * * * find /mnt/user/backups/postgres/ -name "pg_dump_*.sql.gz" -mtime +7 -delete
```

#### Qdrant Snapshot

```bash
# Weekly Qdrant snapshot
0 3 * * 0 curl -X POST "http://localhost:6333/snapshots" && \
  cp /mnt/user/appdata/qdrant/snapshots/*.snapshot /mnt/user/backups/qdrant/
```

### Offsite: Backblaze B2

Install `rclone` and configure B2 bucket:

```bash
# One-time setup
rclone config
# Select: New remote → Backblaze B2 → Enter credentials

# Daily sync of critical data
0 5 * * * rclone sync /mnt/user/backups/ b2:hydra-backups/$(date +\%Y\%m\%d)/ --transfers 4
```

**Estimated monthly cost:** ~$5-10 for 100GB

### Hydra Repo: Git Remote

```powershell
# Push to GitHub/GitLab as second backup
cd C:\Users\shaun\projects\hydra
git push origin main
```

## Backup Schedule Summary

| Time | Action | Data |
|------|--------|------|
| 3:00 AM | Hydra snapshot | System state |
| 3:15 AM | PostgreSQL dump | Databases |
| 4:00 AM | Appdata backup | Container configs |
| 5:00 AM | Offsite sync | All backups |
| Sunday 3:00 AM | Qdrant snapshot | Vector DB |

## Monthly Restore Test Checklist

Perform on the **first Saturday of each month**.

### Pre-Test

- [ ] Verify backup files exist and are recent
- [ ] Check backup sizes are reasonable (not 0 bytes)
- [ ] Ensure test environment is isolated (don't overwrite production)

### Test 1: Appdata Restore

```bash
# Create test directory
mkdir -p /mnt/user/restore-test

# Extract latest appdata backup
tar -xzf /mnt/user/backups/appdata/latest.tar.gz -C /mnt/user/restore-test/

# Verify key files exist
ls /mnt/user/restore-test/appdata/hydra-stack/docker-compose.yml
ls /mnt/user/restore-test/appdata/vaultwarden/
```

- [ ] docker-compose.yml present and valid
- [ ] Vaultwarden data directory intact
- [ ] Config files readable (not corrupted)

### Test 2: PostgreSQL Restore

```bash
# Create test database
docker exec -it hydra-postgres psql -U hydra -c "CREATE DATABASE restore_test;"

# Restore from backup
gunzip -c /mnt/user/backups/postgres/pg_dump_latest.sql.gz | \
  docker exec -i hydra-postgres psql -U hydra -d restore_test

# Verify tables exist
docker exec -it hydra-postgres psql -U hydra -d restore_test -c "\dt"

# Cleanup
docker exec -it hydra-postgres psql -U hydra -c "DROP DATABASE restore_test;"
```

- [ ] Restore completes without errors
- [ ] Tables and data present
- [ ] Cleanup successful

### Test 3: NixOS Config Restore

```bash
# On a NixOS node, verify backup
ls /mnt/user/backups/nixos/$(hostname)/configuration.nix

# Diff current vs backup
diff /etc/nixos/configuration.nix /mnt/user/backups/nixos/$(hostname)/configuration.nix
```

- [ ] Backup file exists
- [ ] Diff shows expected differences (or identical)

### Test 4: Offsite Download

```bash
# List remote backups
rclone ls b2:hydra-backups/ | head -20

# Download a test file
rclone copy b2:hydra-backups/latest/appdata/test-file.txt /tmp/
```

- [ ] Remote files accessible
- [ ] Download completes successfully

### Post-Test

- [ ] Clean up test files: `rm -rf /mnt/user/restore-test`
- [ ] Document any issues found
- [ ] Update this document if procedures changed

### Test Log

| Date | Tester | Result | Notes |
|------|--------|--------|-------|
| 2025-01-04 | | | |
| 2025-02-01 | | | |
| 2025-03-01 | | | |

## Disaster Recovery Runbook

### Scenario: Complete hydra-storage Failure

1. **Acquire replacement hardware**
2. **Install Unraid** from USB
3. **Restore array configuration** from backup
4. **Restore appdata** from offsite:
   ```bash
   rclone sync b2:hydra-backups/latest/appdata/ /mnt/user/appdata/
   ```
5. **Restore databases**:
   ```bash
   rclone copy b2:hydra-backups/latest/postgres/pg_dump_latest.sql.gz /tmp/
   # Start postgres container, then restore
   ```
6. **Verify critical services**:
   - [ ] Vaultwarden accessible
   - [ ] PostgreSQL healthy
   - [ ] Docker containers running

### Scenario: NixOS Node Failure

1. **Install NixOS** from USB
2. **Restore configuration**:
   ```bash
   scp root@hydra-storage:/mnt/user/backups/nixos/$(hostname)/* /etc/nixos/
   nixos-rebuild switch
   ```
3. **Verify services**:
   - [ ] TabbyAPI/Ollama running
   - [ ] NFS mounts working
   - [ ] GPU detected

## Backup Monitoring

Add to Uptime Kuma or Prometheus:

- Alert if backup file age > 48 hours
- Alert if backup size < expected minimum
- Alert if offsite sync fails

---

*Last updated: 2025-12-13*
