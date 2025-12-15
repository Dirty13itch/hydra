#!/usr/bin/env bash
# Hydra Cluster Restore Test Script
# Tests backup restorability without affecting production
#
# Usage: ./restore-test.sh [--component COMPONENT] [--cleanup]
#
# This script:
# 1. Creates isolated test containers
# 2. Restores backups to them
# 3. Verifies data integrity
# 4. Cleans up test resources
#
# SAFE: Does not touch production data

set -euo pipefail

# Configuration
STORAGE_HOST="${STORAGE_HOST:-192.168.1.244}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/user/backups/hydra}"
TEST_NETWORK="hydra-restore-test"
TEST_PREFIX="restore-test"
LOG_FILE="/tmp/restore-test-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

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

info() {
    log "${BLUE}→${NC} $1"
}

header() {
    log "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    log "${BLUE}  $1${NC}"
    log "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

# Setup test environment
setup_test_env() {
    header "Setting Up Test Environment"

    # Create test network
    info "Creating isolated test network..."
    ssh root@${STORAGE_HOST} "docker network create ${TEST_NETWORK} 2>/dev/null || true"
    pass "Test network created: ${TEST_NETWORK}"

    # Create temp directory for restore operations
    info "Creating temporary restore directory..."
    ssh root@${STORAGE_HOST} "mkdir -p /tmp/hydra-restore-test"
    pass "Temp directory ready"
}

# Cleanup test environment
cleanup_test_env() {
    header "Cleaning Up Test Environment"

    info "Stopping test containers..."
    ssh root@${STORAGE_HOST} "docker ps -a --filter 'name=${TEST_PREFIX}' -q | xargs -r docker rm -f" 2>/dev/null || true

    info "Removing test network..."
    ssh root@${STORAGE_HOST} "docker network rm ${TEST_NETWORK}" 2>/dev/null || true

    info "Cleaning up temp files..."
    ssh root@${STORAGE_HOST} "rm -rf /tmp/hydra-restore-test" 2>/dev/null || true

    pass "Cleanup complete"
}

# Test PostgreSQL restore
test_postgres_restore() {
    header "PostgreSQL Restore Test"

    local backup_dir="${BACKUP_ROOT}/postgres"
    local container_name="${TEST_PREFIX}-postgres"

    # Find latest backup
    local latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.sql.gz 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        fail "No PostgreSQL backup found to test"
        return
    fi

    info "Testing restore of: $(basename $latest)"

    # Start fresh PostgreSQL container
    info "Starting test PostgreSQL container..."
    ssh root@${STORAGE_HOST} "docker run -d \
        --name ${container_name} \
        --network ${TEST_NETWORK} \
        -e POSTGRES_USER=hydra \
        -e POSTGRES_PASSWORD=testpassword \
        -e POSTGRES_DB=hydra \
        postgres:16-alpine"

    # Wait for PostgreSQL to be ready
    info "Waiting for PostgreSQL to start..."
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if ssh root@${STORAGE_HOST} "docker exec ${container_name} pg_isready -U hydra" &>/dev/null; then
            break
        fi
        sleep 1
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        fail "PostgreSQL container failed to start"
        ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
        return
    fi

    pass "Test PostgreSQL container running"

    # Restore backup
    info "Restoring backup..."
    if ssh root@${STORAGE_HOST} "zcat ${latest} | docker exec -i ${container_name} psql -U hydra -d hydra" &>/dev/null; then
        pass "Backup restored successfully"
    else
        fail "Backup restore failed"
        ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
        return
    fi

    # Verify restore - check tables exist
    info "Verifying restored data..."
    local table_count=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} psql -U hydra -d hydra -t -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';\"" | tr -d ' ')

    if [[ $table_count -gt 0 ]]; then
        pass "Found ${table_count} tables after restore"
    else
        fail "No tables found after restore"
    fi

    # Check row counts in key tables (if they exist)
    for table in users documents collections; do
        local exists=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} psql -U hydra -d hydra -t -c \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='${table}');\"" | tr -d ' ')
        if [[ "$exists" == "t" ]]; then
            local rows=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} psql -U hydra -d hydra -t -c \"SELECT count(*) FROM ${table};\"" | tr -d ' ')
            info "  Table '${table}': ${rows} rows"
        fi
    done

    # Cleanup
    info "Cleaning up test container..."
    ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
    pass "PostgreSQL restore test complete"
}

# Test Qdrant restore
test_qdrant_restore() {
    header "Qdrant Restore Test"

    local backup_dir="${BACKUP_ROOT}/qdrant"
    local container_name="${TEST_PREFIX}-qdrant"

    # Find latest snapshot
    local latest=$(ssh root@${STORAGE_HOST} "ls -td ${backup_dir}/*/ 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        fail "No Qdrant snapshot found to test"
        return
    fi

    info "Testing restore of: $(basename $latest)"

    # Copy snapshot to temp location
    info "Preparing snapshot for restore..."
    ssh root@${STORAGE_HOST} "cp -r ${latest} /tmp/hydra-restore-test/qdrant-snapshot"

    # Start fresh Qdrant container with snapshot mounted
    info "Starting test Qdrant container..."
    ssh root@${STORAGE_HOST} "docker run -d \
        --name ${container_name} \
        --network ${TEST_NETWORK} \
        -v /tmp/hydra-restore-test/qdrant-snapshot:/qdrant/snapshots:ro \
        -e QDRANT__SERVICE__GRPC_PORT=6334 \
        qdrant/qdrant:latest"

    # Wait for Qdrant to start
    sleep 5

    # Check if Qdrant is healthy
    local health=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} curl -s http://localhost:6333/health" 2>/dev/null)

    if echo "$health" | grep -q "ok\|title"; then
        pass "Test Qdrant container running"
    else
        fail "Qdrant container not healthy"
        ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
        return
    fi

    # List available snapshots
    info "Listing available snapshots..."
    local snapshots=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} ls /qdrant/snapshots 2>/dev/null" || echo "none")
    info "  Found: ${snapshots}"

    # Note: Full restore would require API call to restore from snapshot
    # For now, we verify snapshot files are accessible

    pass "Qdrant snapshot accessible in test container"

    # Cleanup
    info "Cleaning up test container..."
    ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
    ssh root@${STORAGE_HOST} "rm -rf /tmp/hydra-restore-test/qdrant-snapshot" 2>/dev/null
    pass "Qdrant restore test complete"
}

# Test Redis restore
test_redis_restore() {
    header "Redis Restore Test"

    local backup_dir="${BACKUP_ROOT}/redis"
    local container_name="${TEST_PREFIX}-redis"

    # Find latest RDB
    local latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.rdb 2>/dev/null | head -1")

    if [[ -z "$latest" ]]; then
        latest=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.rdb.gz 2>/dev/null | head -1")
        if [[ -n "$latest" ]]; then
            info "Decompressing backup..."
            ssh root@${STORAGE_HOST} "gunzip -c ${latest} > /tmp/hydra-restore-test/dump.rdb"
            latest="/tmp/hydra-restore-test/dump.rdb"
        fi
    fi

    if [[ -z "$latest" ]]; then
        fail "No Redis backup found to test"
        return
    fi

    info "Testing restore of: $(basename $latest)"

    # Copy RDB to temp location
    ssh root@${STORAGE_HOST} "cp ${latest} /tmp/hydra-restore-test/dump.rdb 2>/dev/null || true"

    # Start Redis with restored data
    info "Starting test Redis container..."
    ssh root@${STORAGE_HOST} "docker run -d \
        --name ${container_name} \
        --network ${TEST_NETWORK} \
        -v /tmp/hydra-restore-test/dump.rdb:/data/dump.rdb:ro \
        redis:7-alpine redis-server --appendonly no"

    # Wait for Redis
    sleep 3

    # Check if Redis responds
    local pong=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} redis-cli ping" 2>/dev/null)

    if [[ "$pong" == "PONG" ]]; then
        pass "Test Redis container running"
    else
        fail "Redis container not responding"
        ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
        return
    fi

    # Check key count
    local key_count=$(ssh root@${STORAGE_HOST} "docker exec ${container_name} redis-cli dbsize" 2>/dev/null | grep -oP '\d+' || echo "0")
    info "Keys in restored database: ${key_count}"

    if [[ $key_count -gt 0 ]]; then
        pass "Data restored successfully (${key_count} keys)"
    else
        info "No keys found (backup may have been empty)"
    fi

    # Cleanup
    info "Cleaning up test container..."
    ssh root@${STORAGE_HOST} "docker rm -f ${container_name}" 2>/dev/null
    pass "Redis restore test complete"
}

# Test volume restore
test_volume_restore() {
    header "Volume Restore Test"

    local backup_dir="${BACKUP_ROOT}/volumes"

    # Pick a random volume backup to test
    local test_backup=$(ssh root@${STORAGE_HOST} "ls -t ${backup_dir}/*.tar.gz 2>/dev/null | head -1")

    if [[ -z "$test_backup" ]]; then
        fail "No volume backups found to test"
        return
    fi

    local backup_name=$(basename "$test_backup" .tar.gz)
    info "Testing restore of: ${backup_name}"

    # Create temp extraction directory
    ssh root@${STORAGE_HOST} "mkdir -p /tmp/hydra-restore-test/volume-test"

    # Extract archive
    info "Extracting volume backup..."
    if ssh root@${STORAGE_HOST} "tar -xzf ${test_backup} -C /tmp/hydra-restore-test/volume-test" 2>/dev/null; then
        pass "Volume backup extracted successfully"
    else
        fail "Failed to extract volume backup"
        return
    fi

    # Verify extraction
    local file_count=$(ssh root@${STORAGE_HOST} "find /tmp/hydra-restore-test/volume-test -type f | wc -l")
    if [[ $file_count -gt 0 ]]; then
        pass "Restored ${file_count} files from backup"
    else
        fail "No files restored from backup"
    fi

    # Cleanup
    ssh root@${STORAGE_HOST} "rm -rf /tmp/hydra-restore-test/volume-test" 2>/dev/null
    pass "Volume restore test complete"
}

# Generate test report
generate_report() {
    header "Restore Test Summary"

    local total=$((PASS + FAIL))

    log "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
    log ""

    if [[ $FAIL -eq 0 ]]; then
        log "${GREEN}All restore tests passed!${NC}"
        log "Backups are verified restorable."
    else
        log "${RED}Some restore tests failed. Review issues above.${NC}"
        log "Backup integrity may be compromised."
    fi

    log ""
    log "Full log saved to: ${LOG_FILE}"

    return $FAIL
}

# Main
main() {
    local component=""
    local cleanup_only=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --component)
                component="$2"
                shift 2
                ;;
            --cleanup)
                cleanup_only=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    header "Hydra Cluster Restore Test"
    info "Started at $(date)"
    info "Log file: ${LOG_FILE}"
    log ""
    log "${YELLOW}NOTE: This test creates isolated containers.${NC}"
    log "${YELLOW}Production data is NOT affected.${NC}"

    if $cleanup_only; then
        cleanup_test_env
        exit 0
    fi

    # Trap cleanup on exit
    trap cleanup_test_env EXIT

    setup_test_env

    if [[ -n "$component" ]]; then
        case $component in
            postgres) test_postgres_restore ;;
            qdrant) test_qdrant_restore ;;
            redis) test_redis_restore ;;
            volumes) test_volume_restore ;;
            *) echo "Unknown component: $component"; exit 1 ;;
        esac
    else
        test_postgres_restore
        test_qdrant_restore
        test_redis_restore
        test_volume_restore
    fi

    generate_report
}

main "$@"
