#!/usr/bin/env bash
# Hydra Cluster Backup Creation Script
# Creates consistent backups of all critical cluster data
#
# Usage: ./backup-create.sh [--component COMPONENT] [--retain DAYS]
#
# This script should be run on hydra-storage (Unraid) or via SSH.
# Recommended: Run via cron or n8n workflow.

set -euo pipefail

# Configuration
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/user/backups/hydra}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
DATE_STAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="${BACKUP_ROOT}/logs/backup-${DATE_STAMP}.log"

# Database credentials (should use SOPS in production)
PG_HOST="${PG_HOST:-localhost}"
PG_USER="${PG_USER:-hydra}"
PG_PASSWORD="${PG_PASSWORD:-g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6}"
REDIS_PASSWORD="${REDIS_PASSWORD:-ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUCCESS=0
FAILED=0

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

success() {
    ((SUCCESS++))
    log "${GREEN}✓${NC} $1"
}

fail() {
    ((FAILED++))
    log "${RED}✗${NC} $1"
}

info() {
    log "${BLUE}→${NC} $1"
}

header() {
    log ""
    log "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    log "${BLUE}  $1${NC}"
    log "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    log ""
}

# Ensure backup directories exist
setup_directories() {
    header "Setting Up Backup Directories"

    local dirs=(
        "${BACKUP_ROOT}"
        "${BACKUP_ROOT}/postgres"
        "${BACKUP_ROOT}/qdrant"
        "${BACKUP_ROOT}/redis"
        "${BACKUP_ROOT}/volumes"
        "${BACKUP_ROOT}/configs"
        "${BACKUP_ROOT}/logs"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        info "Created: $dir"
    done

    success "Backup directories ready"
}

# Backup PostgreSQL
backup_postgres() {
    header "PostgreSQL Backup"

    local backup_file="${BACKUP_ROOT}/postgres/hydra-${DATE_STAMP}.sql.gz"

    info "Connecting to PostgreSQL..."

    # Get list of databases
    local databases=$(docker exec hydra-postgres psql -U ${PG_USER} -t -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';" 2>/dev/null | tr -d ' ' | grep -v '^$')

    if [[ -z "$databases" ]]; then
        fail "Could not list databases"
        return 1
    fi

    info "Found databases: $(echo $databases | tr '\n' ' ')"

    # Full cluster dump
    info "Creating full database dump..."
    if docker exec hydra-postgres pg_dumpall -U ${PG_USER} | gzip > "$backup_file"; then
        local size=$(du -h "$backup_file" | cut -f1)
        success "PostgreSQL backup complete: ${size}"

        # Also create per-database dumps for easier selective restore
        for db in $databases; do
            local db_file="${BACKUP_ROOT}/postgres/${db}-${DATE_STAMP}.sql.gz"
            if docker exec hydra-postgres pg_dump -U ${PG_USER} "$db" | gzip > "$db_file"; then
                info "  Backed up database: $db"
            fi
        done
    else
        fail "PostgreSQL backup failed"
        return 1
    fi
}

# Backup Qdrant collections
backup_qdrant() {
    header "Qdrant Backup"

    local snapshot_dir="${BACKUP_ROOT}/qdrant/${DATE_STAMP}"
    mkdir -p "$snapshot_dir"

    info "Fetching collection list..."

    # Get collections
    local collections=$(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name' 2>/dev/null)

    if [[ -z "$collections" ]]; then
        info "No collections found to backup"
        return 0
    fi

    for collection in $collections; do
        info "Creating snapshot for: $collection"

        # Create snapshot
        local snapshot_response=$(curl -s -X POST "http://localhost:6333/collections/${collection}/snapshots")
        local snapshot_name=$(echo "$snapshot_response" | jq -r '.result.name' 2>/dev/null)

        if [[ -n "$snapshot_name" && "$snapshot_name" != "null" ]]; then
            # Download snapshot
            local snapshot_url="http://localhost:6333/collections/${collection}/snapshots/${snapshot_name}"
            if curl -s -o "${snapshot_dir}/${collection}-${snapshot_name}" "$snapshot_url"; then
                success "Snapshot created: ${collection}"
            else
                fail "Failed to download snapshot: ${collection}"
            fi
        else
            fail "Failed to create snapshot: ${collection}"
        fi
    done
}

# Backup Redis
backup_redis() {
    header "Redis Backup"

    local backup_file="${BACKUP_ROOT}/redis/redis-${DATE_STAMP}.rdb"

    info "Triggering Redis BGSAVE..."

    # Trigger background save
    if docker exec hydra-redis redis-cli -a "${REDIS_PASSWORD}" BGSAVE 2>/dev/null | grep -q "Background"; then
        # Wait for save to complete
        sleep 2

        local wait_count=0
        while docker exec hydra-redis redis-cli -a "${REDIS_PASSWORD}" LASTSAVE 2>/dev/null; do
            local saving=$(docker exec hydra-redis redis-cli -a "${REDIS_PASSWORD}" INFO persistence 2>/dev/null | grep "rdb_bgsave_in_progress:1" || true)
            if [[ -z "$saving" ]]; then
                break
            fi
            sleep 1
            ((wait_count++))
            if [[ $wait_count -gt 60 ]]; then
                fail "Redis save timeout"
                return 1
            fi
        done

        # Copy RDB file
        info "Copying RDB file..."
        if docker cp hydra-redis:/data/dump.rdb "$backup_file" 2>/dev/null; then
            local size=$(du -h "$backup_file" | cut -f1)
            success "Redis backup complete: ${size}"
        else
            fail "Failed to copy Redis dump"
        fi
    else
        fail "Failed to trigger Redis save"
    fi
}

# Backup Docker volumes
backup_volumes() {
    header "Docker Volume Backup"

    local volumes_to_backup=(
        "grafana-data"
        "prometheus-data"
        "n8n-data"
        "loki-data"
        "uptime-kuma-data"
        "open-webui-data"
        "homeassistant-data"
    )

    for volume in "${volumes_to_backup[@]}"; do
        local backup_file="${BACKUP_ROOT}/volumes/${volume}-${DATE_STAMP}.tar.gz"

        info "Backing up volume: $volume"

        # Check if volume exists
        if docker volume inspect "$volume" &>/dev/null; then
            # Create backup using alpine container
            if docker run --rm \
                -v "${volume}:/data:ro" \
                -v "${BACKUP_ROOT}/volumes:/backup" \
                alpine tar czf "/backup/${volume}-${DATE_STAMP}.tar.gz" -C /data . 2>/dev/null; then
                local size=$(du -h "$backup_file" | cut -f1)
                success "${volume}: ${size}"
            else
                fail "Failed to backup: ${volume}"
            fi
        else
            info "Volume not found, skipping: ${volume}"
        fi
    done
}

# Backup configuration files
backup_configs() {
    header "Configuration Backup"

    local config_dir="${BACKUP_ROOT}/configs/${DATE_STAMP}"
    mkdir -p "$config_dir"

    # Docker compose files
    local compose_dirs=(
        "/mnt/user/appdata/hydra-stack"
        "/mnt/user/appdata/media-stack"
        "/mnt/user/appdata/download-stack"
    )

    for dir in "${compose_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            local name=$(basename "$dir")
            cp -r "$dir"/*.{yml,yaml,env} "$config_dir/${name}/" 2>/dev/null || true
            info "Backed up: $name configs"
        fi
    done

    # LiteLLM config
    if [[ -f "/mnt/user/appdata/hydra-stack/litellm-config.yaml" ]]; then
        cp "/mnt/user/appdata/hydra-stack/litellm-config.yaml" "$config_dir/"
        success "LiteLLM config backed up"
    fi

    # Prometheus config
    if [[ -f "/mnt/user/appdata/prometheus/prometheus.yml" ]]; then
        cp "/mnt/user/appdata/prometheus/prometheus.yml" "$config_dir/"
        success "Prometheus config backed up"
    fi

    # Grafana dashboards
    if [[ -d "/mnt/user/appdata/grafana/dashboards" ]]; then
        cp -r "/mnt/user/appdata/grafana/dashboards" "$config_dir/"
        success "Grafana dashboards backed up"
    fi

    # Create tarball of all configs
    tar czf "${BACKUP_ROOT}/configs/configs-${DATE_STAMP}.tar.gz" -C "$config_dir" .
    rm -rf "$config_dir"

    success "All configurations archived"
}

# Cleanup old backups
cleanup_old_backups() {
    header "Cleaning Up Old Backups"

    info "Retention period: ${RETAIN_DAYS} days"

    local cleaned=0

    # PostgreSQL
    for f in $(find "${BACKUP_ROOT}/postgres" -name "*.sql.gz" -mtime +${RETAIN_DAYS} 2>/dev/null); do
        rm "$f"
        ((cleaned++))
    done

    # Qdrant snapshots
    for d in $(find "${BACKUP_ROOT}/qdrant" -maxdepth 1 -type d -mtime +${RETAIN_DAYS} 2>/dev/null | grep -v "^${BACKUP_ROOT}/qdrant$"); do
        rm -rf "$d"
        ((cleaned++))
    done

    # Redis
    for f in $(find "${BACKUP_ROOT}/redis" -name "*.rdb" -mtime +${RETAIN_DAYS} 2>/dev/null); do
        rm "$f"
        ((cleaned++))
    done

    # Volumes
    for f in $(find "${BACKUP_ROOT}/volumes" -name "*.tar.gz" -mtime +${RETAIN_DAYS} 2>/dev/null); do
        rm "$f"
        ((cleaned++))
    done

    # Configs
    for f in $(find "${BACKUP_ROOT}/configs" -name "*.tar.gz" -mtime +${RETAIN_DAYS} 2>/dev/null); do
        rm "$f"
        ((cleaned++))
    done

    # Logs
    for f in $(find "${BACKUP_ROOT}/logs" -name "*.log" -mtime +${RETAIN_DAYS} 2>/dev/null); do
        rm "$f"
        ((cleaned++))
    done

    success "Removed ${cleaned} old backup files"
}

# Calculate backup sizes
report_sizes() {
    header "Backup Size Report"

    local total_size=$(du -sh "${BACKUP_ROOT}" | cut -f1)
    info "Total backup size: ${total_size}"

    echo ""
    info "By component:"
    for dir in postgres qdrant redis volumes configs; do
        if [[ -d "${BACKUP_ROOT}/${dir}" ]]; then
            local size=$(du -sh "${BACKUP_ROOT}/${dir}" | cut -f1)
            info "  ${dir}: ${size}"
        fi
    done
}

# Generate summary
generate_summary() {
    header "Backup Summary"

    local total=$((SUCCESS + FAILED))
    log "Completed: ${SUCCESS} successful, ${FAILED} failed"

    if [[ $FAILED -eq 0 ]]; then
        log "${GREEN}All backups completed successfully!${NC}"
    else
        log "${RED}Some backups failed. Check log for details.${NC}"
    fi

    log ""
    log "Backup location: ${BACKUP_ROOT}"
    log "Log file: ${LOG_FILE}"

    return $FAILED
}

# Main
main() {
    local component=""
    local retain=${RETAIN_DAYS}

    while [[ $# -gt 0 ]]; do
        case $1 in
            --component)
                component="$2"
                shift 2
                ;;
            --retain)
                retain="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    RETAIN_DAYS=$retain

    header "Hydra Cluster Backup"
    info "Started at $(date)"
    info "Timestamp: ${DATE_STAMP}"

    setup_directories

    if [[ -n "$component" ]]; then
        case $component in
            postgres) backup_postgres ;;
            qdrant) backup_qdrant ;;
            redis) backup_redis ;;
            volumes) backup_volumes ;;
            configs) backup_configs ;;
            *) echo "Unknown component: $component"; exit 1 ;;
        esac
    else
        backup_postgres
        backup_qdrant
        backup_redis
        backup_volumes
        backup_configs
    fi

    cleanup_old_backups
    report_sizes
    generate_summary
}

main "$@"
