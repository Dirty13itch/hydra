#!/bin/bash
# PostgreSQL Backup Script for Hydra Cluster
#
# Backs up all PostgreSQL databases to MinIO/local storage
# Run via cron or n8n workflow
#
# Usage: ./backup-postgres.sh [--database <name>] [--all]
#
# Generated: December 14, 2025

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-192.168.1.244}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-hydra}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/user/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/backup_${DATE}.log"

# Databases to backup
DATABASES=("hydra" "litellm" "n8n" "letta")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log "=========================================="
log "PostgreSQL Backup Started"
log "Host: $POSTGRES_HOST"
log "Backup Dir: $BACKUP_DIR"
log "=========================================="

# Parse arguments
BACKUP_SPECIFIC=""
BACKUP_ALL=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --database)
            BACKUP_SPECIFIC="$2"
            BACKUP_ALL=false
            shift 2
            ;;
        --all)
            BACKUP_ALL=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to backup a single database
backup_database() {
    local db=$1
    local backup_file="${BACKUP_DIR}/${db}_${DATE}.sql.gz"

    log "Backing up database: $db"

    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$db" \
        --no-password \
        --format=plain \
        --verbose \
        2>> "$LOG_FILE" | gzip > "$backup_file"; then

        local size=$(du -h "$backup_file" | cut -f1)
        success "$db backup complete: $backup_file ($size)"
        return 0
    else
        error "Failed to backup $db"
        return 1
    fi
}

# Backup databases
FAILED=0
SUCCEEDED=0

if [ "$BACKUP_ALL" = true ]; then
    for db in "${DATABASES[@]}"; do
        if backup_database "$db"; then
            ((SUCCEEDED++))
        else
            ((FAILED++))
        fi
    done
elif [ -n "$BACKUP_SPECIFIC" ]; then
    if backup_database "$BACKUP_SPECIFIC"; then
        ((SUCCEEDED++))
    else
        ((FAILED++))
    fi
fi

# Cleanup old backups
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.log" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "unknown")

log "=========================================="
log "Backup Summary"
log "  Succeeded: $SUCCEEDED"
log "  Failed: $FAILED"
log "  Total Backup Size: $TOTAL_SIZE"
log "=========================================="

# Upload to MinIO if configured
if [ -n "${MINIO_ENDPOINT:-}" ] && [ -n "${MINIO_ACCESS_KEY:-}" ]; then
    log "Uploading to MinIO..."

    # Create today's folder in MinIO
    mc alias set hydra-minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null || true

    for backup_file in "${BACKUP_DIR}"/*_${DATE}.sql.gz; do
        if [ -f "$backup_file" ]; then
            mc cp "$backup_file" "hydra-minio/backups/postgres/$(basename "$backup_file")" 2>> "$LOG_FILE" && \
                log "Uploaded: $(basename "$backup_file")"
        fi
    done
fi

# Report to Hydra MCP API
if [ -n "${HYDRA_MCP_URL:-}" ]; then
    curl -sf -X POST "${HYDRA_MCP_URL}/api/activities" \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"postgres_backup\",
            \"source\": \"backup-script\",
            \"target\": \"hydra-postgres\",
            \"status\": \"$([ $FAILED -eq 0 ] && echo 'success' || echo 'partial')\",
            \"details\": \"Backed up $SUCCEEDED databases, $FAILED failed. Total size: $TOTAL_SIZE\"
        }" 2>/dev/null || true
fi

# Exit with error if any backup failed
if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0
