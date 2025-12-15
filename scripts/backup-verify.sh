#!/usr/bin/env bash
# Hydra Cluster Backup Verification Script
# Verifies backup integrity across all critical services
#
# Usage: ./backup-verify.sh [--full] [--component COMPONENT]
#
# Components: postgres, qdrant, redis, volumes, models, configs

set -euo pipefail

# Configuration
STORAGE_HOST="${STORAGE_HOST:-192.168.1.244}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/user/backups/hydra}"
LOG_FILE="/tmp/backup-verify-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASS=0
FAIL=0
WARN=0

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

pass() {
    ((PASS++))
    log "${GREEN}✓${NC} $1"
}

fail() {
    ((FAIL++))
    log "${RED}✗${NC} $1"
}

warn() {
    ((WARN++))
    log "${YELLOW}!${NC} $1"
}

info() {
    log "${BLUE}→${NC} $1"
}

header() {
    log "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    log "${BLUE}  $1${NC}"
    log "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

# Check if we can connect to storage
check_storage_connection() {
    header "Storage Connection Check"

    if ssh -o ConnectTimeout=5 root@${STORAGE_HOST} "echo 'connected'" &>/dev/null; then
        pass "SSH connection to hydra-storage"
    else
        fail "Cannot connect to hydra-storage"
        exit 1
    fi

    if ssh root@${STORAGE_HOST} "test -d ${BACKUP_ROOT}"; then
        pass "Backup root directory exists: ${BACKUP_ROOT}"
    else
        fail "Backup root directory not found: ${BACKUP_ROOT}"
        exit 1
    fi
}

# Verify PostgreSQL backups
verify_postgres() {
    header "PostgreSQL Backup Verification"

    local backup_dir="${BACKUP_ROOT}/postgres"

    # Check backup directory
    if ! ssh root@${STORAGE_HOST} "test -d ${backup_dir}"; then
        warn "PostgreSQL backup directory not found"
        return
    fi

    # Find latest backup
    local latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.sql.gz 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        fail "No PostgreSQL backups found"
        return
    fi

    local backup_name=$(basename "$latest")
    local backup_age=$(ssh root@${STORAGE_HOST} "stat -c %Y ${latest}")
    local now=$(date +%s)
    local age_hours=$(( (now - backup_age) / 3600 ))

    info "Latest backup: ${backup_name}"
    info "Backup age: ${age_hours} hours"

    if [[ $age_hours -lt 24 ]]; then
        pass "Backup is recent (< 24 hours)"
    elif [[ $age_hours -lt 72 ]]; then
        warn "Backup is stale (${age_hours} hours old)"
    else
        fail "Backup is too old (${age_hours} hours)"
    fi

    # Verify backup integrity (gzip test)
    if ssh root@${STORAGE_HOST} "gzip -t ${latest}" 2>/dev/null; then
        pass "Backup file integrity verified (gzip ok)"
    else
        fail "Backup file corrupted (gzip test failed)"
    fi

    # Check backup size
    local size=$(ssh root@${STORAGE_HOST} "stat -c %s ${latest}")
    local size_mb=$((size / 1024 / 1024))

    if [[ $size -gt 1000 ]]; then
        pass "Backup size reasonable: ${size_mb}MB"
    else
        fail "Backup suspiciously small: ${size_mb}MB"
    fi

    # List databases in backup
    info "Checking databases in backup..."
    local dbs=$(ssh root@${STORAGE_HOST} "zcat ${latest} | grep -oP '(?<=\\\\connect )\w+' | sort -u | head -10")
    for db in $dbs; do
        info "  Found database: ${db}"
    done
}

# Verify Qdrant backups
verify_qdrant() {
    header "Qdrant Backup Verification"

    local backup_dir="${BACKUP_ROOT}/qdrant"

    if ! ssh root@${STORAGE_HOST} "test -d ${backup_dir}"; then
        warn "Qdrant backup directory not found"
        return
    fi

    # Find latest snapshot directory
    local latest=$(ssh root@${STORAGE_HOST} "ls -td ${backup_dir}/*/ 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        fail "No Qdrant snapshots found"
        return
    fi

    local snapshot_name=$(basename "$latest")
    info "Latest snapshot: ${snapshot_name}"

    # Check for collection snapshots
    local collections=$(ssh root@${STORAGE_HOST} "ls -d ${latest}*/ 2>/dev/null | wc -l")

    if [[ $collections -gt 0 ]]; then
        pass "Found ${collections} collection snapshot(s)"

        # List collections
        for col in $(ssh root@${STORAGE_HOST} "ls ${latest}"); do
            local col_size=$(ssh root@${STORAGE_HOST} "du -sh ${latest}${col} 2>/dev/null | cut -f1")
            info "  Collection: ${col} (${col_size})"
        done
    else
        fail "No collection snapshots found"
    fi

    # Check snapshot age
    local backup_age=$(ssh root@${STORAGE_HOST} "stat -c %Y ${latest}")
    local now=$(date +%s)
    local age_hours=$(( (now - backup_age) / 3600 ))

    if [[ $age_hours -lt 24 ]]; then
        pass "Snapshot is recent (< 24 hours)"
    elif [[ $age_hours -lt 168 ]]; then
        warn "Snapshot is stale (${age_hours} hours old)"
    else
        fail "Snapshot is too old (${age_hours} hours)"
    fi
}

# Verify Redis backups
verify_redis() {
    header "Redis Backup Verification"

    local backup_dir="${BACKUP_ROOT}/redis"

    if ! ssh root@${STORAGE_HOST} "test -d ${backup_dir}"; then
        warn "Redis backup directory not found"
        return
    fi

    # Find latest RDB file
    local latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.rdb 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        # Check for compressed backups
        latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.rdb.gz 2>/dev/null | head -1")
    fi

    if [[ -z "$latest" ]]; then
        fail "No Redis backups found"
        return
    fi

    local backup_name=$(basename "$latest")
    info "Latest backup: ${backup_name}"

    # Check file integrity
    local size=$(ssh root@${STORAGE_HOST} "stat -c %s ${latest}")

    if [[ $size -gt 100 ]]; then
        pass "Backup file exists and has content: ${size} bytes"
    else
        fail "Backup file empty or too small"
    fi

    # Check RDB header magic bytes
    local magic=$(ssh root@${STORAGE_HOST} "head -c 5 ${latest} 2>/dev/null | cat")
    if [[ "$magic" == "REDIS" ]]; then
        pass "Valid Redis RDB file header"
    else
        warn "Cannot verify RDB header (may be compressed)"
    fi
}

# Verify Docker volume backups
verify_volumes() {
    header "Docker Volume Backup Verification"

    local backup_dir="${BACKUP_ROOT}/volumes"

    if ! ssh root@${STORAGE_HOST} "test -d ${backup_dir}"; then
        warn "Volume backup directory not found"
        return
    fi

    # List volume backups
    local count=$(ssh root@${STORAGE_HOST} "ls ${backup_dir}/*.tar.gz 2>/dev/null | wc -l")

    if [[ $count -eq 0 ]]; then
        warn "No volume backups found"
        return
    fi

    info "Found ${count} volume backup(s)"

    # Check critical volumes
    local critical_volumes=("grafana" "prometheus" "n8n" "loki" "open-webui")

    for vol in "${critical_volumes[@]}"; do
        local vol_backup=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*${vol}*.tar.gz 2>/dev/null | head -1")

        if [[ -n "$vol_backup" ]]; then
            # Verify tar integrity
            if ssh root@${STORAGE_HOST} "gzip -t ${vol_backup}" 2>/dev/null; then
                local size=$(ssh root@${STORAGE_HOST} "stat -c %s ${vol_backup}")
                pass "${vol}: $(numfmt --to=iec $size)"
            else
                fail "${vol}: backup corrupted"
            fi
        else
            warn "${vol}: no backup found"
        fi
    done
}

# Verify model configs (not models themselves - too large)
verify_model_configs() {
    header "Model Configuration Backup Verification"

    local backup_dir="${BACKUP_ROOT}/configs"

    if ! ssh root@${STORAGE_HOST} "test -d ${backup_dir}"; then
        warn "Config backup directory not found"
        return
    fi

    # Check for TabbyAPI config
    if ssh root@${STORAGE_HOST} "test -f ${backup_dir}/tabbyapi-config.yml"; then
        pass "TabbyAPI config backed up"
    else
        warn "TabbyAPI config not in backup"
    fi

    # Check for LiteLLM config
    if ssh root@${STORAGE_HOST} "test -f ${backup_dir}/litellm-config.yaml"; then
        pass "LiteLLM config backed up"
    else
        warn "LiteLLM config not in backup"
    fi

    # Check for docker-compose files
    local compose_count=$(ssh root@${STORAGE_HOST} "ls ${backup_dir}/*.yml ${backup_dir}/*.yaml 2>/dev/null | wc -l")
    if [[ $compose_count -gt 0 ]]; then
        pass "Found ${compose_count} compose/config files"
    else
        warn "No compose files in backup"
    fi
}

# Verify service configs (appdata)
verify_appdata() {
    header "Application Data Verification"

    local appdata_dir="/mnt/user/appdata"

    # Check critical app directories exist and have content
    local apps=("hydra-stack" "grafana" "prometheus" "n8n" "homeassistant")

    for app in "${apps[@]}"; do
        local app_path="${appdata_dir}/${app}"
        if ssh root@${STORAGE_HOST} "test -d ${app_path}"; then
            local file_count=$(ssh root@${STORAGE_HOST} "find ${app_path} -type f 2>/dev/null | wc -l")
            if [[ $file_count -gt 0 ]]; then
                pass "${app}: ${file_count} files"
            else
                warn "${app}: directory empty"
            fi
        else
            warn "${app}: directory not found"
        fi
    done
}

# Generate backup report
generate_report() {
    header "Backup Verification Summary"

    local total=$((PASS + FAIL + WARN))

    log "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
    log ""

    if [[ $FAIL -eq 0 ]]; then
        if [[ $WARN -eq 0 ]]; then
            log "${GREEN}All backup verifications passed!${NC}"
        else
            log "${YELLOW}Backups verified with warnings.${NC}"
        fi
    else
        log "${RED}Backup verification failed. Review issues above.${NC}"
    fi

    log ""
    log "Full log saved to: ${LOG_FILE}"

    # Return exit code
    if [[ $FAIL -gt 0 ]]; then
        return 1
    elif [[ $WARN -gt 0 ]]; then
        return 2
    else
        return 0
    fi
}

# Main
main() {
    local full=false
    local component=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                full=true
                shift
                ;;
            --component)
                component="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    header "Hydra Cluster Backup Verification"
    info "Started at $(date)"
    info "Log file: ${LOG_FILE}"

    check_storage_connection

    if [[ -n "$component" ]]; then
        case $component in
            postgres) verify_postgres ;;
            qdrant) verify_qdrant ;;
            redis) verify_redis ;;
            volumes) verify_volumes ;;
            models) verify_model_configs ;;
            configs) verify_appdata ;;
            *) echo "Unknown component: $component"; exit 1 ;;
        esac
    else
        verify_postgres
        verify_qdrant
        verify_redis
        verify_volumes
        verify_model_configs

        if $full; then
            verify_appdata
        fi
    fi

    generate_report
}

main "$@"
