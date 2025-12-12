#!/bin/bash
# Hydra PostgreSQL Backup Script
# Backs up all PostgreSQL databases with rotation and compression
# Designed to be run via cron on hydra-storage

set -e

# Configuration
BACKUP_ROOT="/mnt/user/backups/postgres"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
LOGFILE="/var/log/hydra-pg-backup.log"

# Database configurations
declare -A DATABASES=(
    ["letta"]="letta-db:letta:letta"
    ["hydra"]="hydra-postgres:hydra:hydra"
)

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

# Create backup directories
mkdir -p "$BACKUP_ROOT"
mkdir -p "$(dirname "$LOGFILE")"

log "=== Starting PostgreSQL backup ==="

# Backup each database
for db_name in "${!DATABASES[@]}"; do
    IFS=':' read -r container user database <<< "${DATABASES[$db_name]}"

    BACKUP_DIR="$BACKUP_ROOT/$db_name"
    BACKUP_FILE="$BACKUP_DIR/${db_name}_${DATE}.sql.gz"

    mkdir -p "$BACKUP_DIR"

    log "Backing up $db_name from container $container..."

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log "ERROR: Container $container is not running, skipping $db_name"
        continue
    fi

    # Perform backup with compression
    if docker exec "$container" pg_dump -U "$user" "$database" 2>>"$LOGFILE" | gzip > "$BACKUP_FILE"; then
        # Verify backup file exists and has content
        if [ -s "$BACKUP_FILE" ]; then
            SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log "SUCCESS: $db_name backed up to $BACKUP_FILE ($SIZE)"
        else
            log "ERROR: Backup file $BACKUP_FILE is empty"
            rm -f "$BACKUP_FILE"
        fi
    else
        log "ERROR: Failed to backup $db_name"
        rm -f "$BACKUP_FILE"
    fi
done

# Cleanup old backups
log "Cleaning up backups older than $RETENTION_DAYS days..."
for db_name in "${!DATABASES[@]}"; do
    BACKUP_DIR="$BACKUP_ROOT/$db_name"
    if [ -d "$BACKUP_DIR" ]; then
        DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
        if [ "$DELETED" -gt 0 ]; then
            log "Deleted $DELETED old backup(s) from $db_name"
        fi
    fi
done

# Summary
log "=== Backup summary ==="
for db_name in "${!DATABASES[@]}"; do
    BACKUP_DIR="$BACKUP_ROOT/$db_name"
    if [ -d "$BACKUP_DIR" ]; then
        COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f | wc -l)
        TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
        log "$db_name: $COUNT backups, total size: $TOTAL_SIZE"
    fi
done

log "=== PostgreSQL backup complete ==="
