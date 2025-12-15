# Backup and Restore Runbook

Procedures for backing up and restoring Hydra cluster data.

## Backup Schedule

| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| PostgreSQL | Daily 2 AM | 7 days | `/mnt/user/backups/postgres/` |
| Qdrant | Daily 2 AM | 7 days | `/mnt/user/backups/qdrant/` |
| Redis | Daily 2 AM | 7 days | `/mnt/user/backups/redis/` |
| Docker volumes | Weekly | 4 weeks | `/mnt/user/backups/volumes/` |
| NixOS configs | On change | Git history | GitHub repo |

---

## Manual Backup

### Full Cluster Backup

```bash
ssh root@192.168.1.244

# Run backup script
/mnt/user/appdata/hydra-stack/scripts/backup-create.sh

# Or manual backup
BACKUP_DIR="/mnt/user/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
```

### PostgreSQL Backup

```bash
# Dump all databases
docker exec hydra-postgres pg_dumpall -U hydra > $BACKUP_DIR/postgres_all.sql

# Dump specific database
docker exec hydra-postgres pg_dump -U hydra -d n8n > $BACKUP_DIR/postgres_n8n.sql
docker exec hydra-postgres pg_dump -U hydra -d litellm > $BACKUP_DIR/postgres_litellm.sql
docker exec hydra-postgres pg_dump -U hydra -d miniflux > $BACKUP_DIR/postgres_miniflux.sql
docker exec hydra-postgres pg_dump -U hydra -d letta > $BACKUP_DIR/postgres_letta.sql

# Compress
gzip $BACKUP_DIR/postgres_*.sql
```

### Qdrant Backup

```bash
# Create snapshot for each collection
for collection in $(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name'); do
    curl -X POST "http://localhost:6333/collections/$collection/snapshots"
done

# Copy snapshots
mkdir -p $BACKUP_DIR/qdrant
cp -r /mnt/user/appdata/qdrant/snapshots/* $BACKUP_DIR/qdrant/
```

### Redis Backup

```bash
# Trigger RDB save
docker exec hydra-redis redis-cli -a 'PASSWORD' BGSAVE

# Wait for completion
sleep 10

# Copy RDB file
cp /mnt/user/appdata/redis/dump.rdb $BACKUP_DIR/redis_dump.rdb
```

### Docker Volume Backup

```bash
# List volumes to backup
VOLUMES="n8n_data grafana_data prometheus_data loki_data homeassistant_config"

for vol in $VOLUMES; do
    echo "Backing up $vol..."
    docker run --rm -v ${vol}:/source -v $BACKUP_DIR:/backup alpine \
        tar czf /backup/${vol}.tar.gz -C /source .
done
```

---

## Restore Procedures

### PostgreSQL Restore

**Full restore (all databases):**
```bash
# Stop services using PostgreSQL
docker stop litellm n8n miniflux letta

# Restore
gunzip -c $BACKUP_DIR/postgres_all.sql.gz | docker exec -i hydra-postgres psql -U hydra

# Restart services
docker start litellm n8n miniflux letta
```

**Single database restore:**
```bash
# Drop and recreate database
docker exec hydra-postgres psql -U hydra -c "DROP DATABASE n8n;"
docker exec hydra-postgres psql -U hydra -c "CREATE DATABASE n8n;"

# Restore
gunzip -c $BACKUP_DIR/postgres_n8n.sql.gz | docker exec -i hydra-postgres psql -U hydra -d n8n
```

### Qdrant Restore

```bash
# Stop Qdrant
docker stop qdrant

# Clear existing data
rm -rf /mnt/user/appdata/qdrant/storage/*

# Restore from snapshot
# Option 1: Copy snapshot files
cp -r $BACKUP_DIR/qdrant/* /mnt/user/appdata/qdrant/snapshots/

# Start Qdrant
docker start qdrant

# Recover collection from snapshot
for snapshot in /mnt/user/appdata/qdrant/snapshots/*; do
    collection=$(basename $snapshot | cut -d'-' -f1)
    curl -X PUT "http://localhost:6333/collections/$collection/snapshots/recover" \
        -H "Content-Type: application/json" \
        -d "{\"location\": \"file://$snapshot\"}"
done
```

### Redis Restore

```bash
# Stop Redis
docker stop hydra-redis

# Replace RDB file
cp $BACKUP_DIR/redis_dump.rdb /mnt/user/appdata/redis/dump.rdb
chown 999:999 /mnt/user/appdata/redis/dump.rdb

# Start Redis
docker start hydra-redis
```

### Docker Volume Restore

```bash
# Stop container using the volume
docker stop n8n

# Clear and restore volume
docker run --rm -v n8n_data:/target -v $BACKUP_DIR:/backup alpine \
    sh -c "rm -rf /target/* && tar xzf /backup/n8n_data.tar.gz -C /target"

# Start container
docker start n8n
```

---

## Backup Verification

### Daily Verification

```bash
# Run verification script
/mnt/user/appdata/hydra-stack/scripts/backup-verify.sh

# Manual checks
# 1. Check backup file exists and has size
ls -lh /mnt/user/backups/latest/

# 2. Check file age (should be < 24 hours)
find /mnt/user/backups/latest/ -mtime +1 -type f

# 3. Test PostgreSQL backup integrity
gunzip -t /mnt/user/backups/latest/postgres_all.sql.gz && echo "PostgreSQL backup OK"

# 4. Check Qdrant snapshots
ls -la /mnt/user/backups/latest/qdrant/
```

### Restore Test (Monthly)

```bash
# Run restore test script
/mnt/user/appdata/hydra-stack/scripts/restore-test.sh

# This creates isolated test containers and verifies restore works
```

---

## Disaster Recovery

### Complete Data Loss (hydra-storage)

1. **Reinstall Unraid** (if needed)
   - Boot from USB
   - Configure array with existing disks
   - Re-enable Docker

2. **Restore Docker configs**
   ```bash
   # Clone repo
   cd /mnt/user/appdata
   git clone https://github.com/shaun/hydra.git hydra-stack

   # Copy docker-compose files
   cp hydra-stack/docker-compose/* .
   ```

3. **Restore from off-site backup**
   ```bash
   # Mount backup source (NAS, cloud, etc.)
   mount -t cifs //backup-server/hydra /mnt/backup

   # Restore databases
   cp -r /mnt/backup/latest/* /mnt/user/backups/

   # Run restore procedures above
   ```

4. **Start services in order**
   ```bash
   # Layer 0: Core databases
   docker-compose up -d postgres redis qdrant
   sleep 60

   # Layer 1: Run restores
   # (PostgreSQL, Qdrant, Redis restores)

   # Layer 2: Dependent services
   docker-compose up -d
   ```

### NixOS Node Recovery

1. **Boot NixOS installer USB**

2. **Mount filesystems**
   ```bash
   mount /dev/nvme0n1p2 /mnt
   mount /dev/nvme0n1p1 /mnt/boot
   ```

3. **Restore configuration**
   ```bash
   git clone https://github.com/shaun/hydra.git /mnt/etc/nixos/hydra
   cp /mnt/etc/nixos/hydra/nixos-modules/examples/hydra-ai.nix /mnt/etc/nixos/configuration.nix
   ```

4. **Rebuild**
   ```bash
   nixos-install --root /mnt
   reboot
   ```

---

## Off-site Backup (Recommended)

### Setup Restic to Backblaze B2

```bash
# Install restic
apt install restic  # or nix-env -i restic

# Initialize repository
export B2_ACCOUNT_ID="your-account-id"
export B2_ACCOUNT_KEY="your-account-key"
export RESTIC_PASSWORD="your-encryption-password"

restic -r b2:hydra-backups init

# Backup
restic -r b2:hydra-backups backup /mnt/user/backups/

# Verify
restic -r b2:hydra-backups check
restic -r b2:hydra-backups snapshots
```

### Automate with Cron

```bash
# Add to crontab
0 4 * * * /usr/local/bin/restic -r b2:hydra-backups backup /mnt/user/backups/ >> /var/log/restic-backup.log 2>&1
```
