#!/usr/bin/env bash
# Docker Container Health Check Script
#
# Checks the health status of all Docker containers on hydra-storage.
# Reports unhealthy containers and optionally restarts them.
#
# Usage:
#   ./docker-health-check.sh                    # Report only
#   ./docker-health-check.sh --restart          # Restart unhealthy containers
#   ./docker-health-check.sh --json             # JSON output for automation

set -euo pipefail

# Configuration
RESTART_UNHEALTHY=${RESTART_UNHEALTHY:-false}
JSON_OUTPUT=${JSON_OUTPUT:-false}
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN=300  # 5 minutes between restarts of same container

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Track restarts to avoid loops
RESTART_HISTORY_FILE="/tmp/docker-restart-history.json"

declare -A container_status
declare -a unhealthy_containers
declare -a no_healthcheck

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART_UNHEALTHY=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "$1"
    fi
}

# Initialize restart history
init_restart_history() {
    if [[ ! -f "$RESTART_HISTORY_FILE" ]]; then
        echo "{}" > "$RESTART_HISTORY_FILE"
    fi
}

# Check if container can be restarted (rate limiting)
can_restart() {
    local container=$1
    local now=$(date +%s)

    if [[ ! -f "$RESTART_HISTORY_FILE" ]]; then
        return 0
    fi

    local last_restart=$(jq -r ".[\"$container\"].last_restart // 0" "$RESTART_HISTORY_FILE" 2>/dev/null || echo 0)
    local restart_count=$(jq -r ".[\"$container\"].count // 0" "$RESTART_HISTORY_FILE" 2>/dev/null || echo 0)

    # Check cooldown
    if [[ $((now - last_restart)) -lt $RESTART_COOLDOWN ]]; then
        return 1
    fi

    # Check max attempts
    if [[ $restart_count -ge $MAX_RESTART_ATTEMPTS ]]; then
        # Reset after cooldown
        if [[ $((now - last_restart)) -gt $((RESTART_COOLDOWN * 3)) ]]; then
            return 0
        fi
        return 1
    fi

    return 0
}

# Record restart
record_restart() {
    local container=$1
    local now=$(date +%s)

    local count=$(jq -r ".[\"$container\"].count // 0" "$RESTART_HISTORY_FILE" 2>/dev/null || echo 0)
    ((count++))

    jq ".[\"$container\"] = {\"last_restart\": $now, \"count\": $count}" "$RESTART_HISTORY_FILE" > "${RESTART_HISTORY_FILE}.tmp"
    mv "${RESTART_HISTORY_FILE}.tmp" "$RESTART_HISTORY_FILE"
}

# Get container health status
check_containers() {
    log "${BLUE}Checking Docker container health...${NC}"
    log ""

    # Get all containers with health info
    local containers=$(docker ps --format '{{.Names}}\t{{.Status}}' --no-trunc)

    local healthy=0
    local unhealthy=0
    local no_check=0
    local total=0

    while IFS=$'\t' read -r name status; do
        ((total++))

        if [[ "$status" == *"(healthy)"* ]]; then
            container_status["$name"]="healthy"
            ((healthy++))
        elif [[ "$status" == *"(unhealthy)"* ]]; then
            container_status["$name"]="unhealthy"
            unhealthy_containers+=("$name")
            ((unhealthy++))
        elif [[ "$status" == *"(starting)"* ]]; then
            container_status["$name"]="starting"
        else
            # No healthcheck configured
            container_status["$name"]="no_healthcheck"
            no_healthcheck+=("$name")
            ((no_check++))
        fi
    done <<< "$containers"

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json "$healthy" "$unhealthy" "$no_check" "$total"
    else
        output_text "$healthy" "$unhealthy" "$no_check" "$total"
    fi
}

output_text() {
    local healthy=$1
    local unhealthy=$2
    local no_check=$3
    local total=$4

    log "${BLUE}═══════════════════════════════════════════════${NC}"
    log "${BLUE}  Docker Container Health Summary${NC}"
    log "${BLUE}═══════════════════════════════════════════════${NC}"
    log ""
    log "Total containers: $total"
    log "${GREEN}Healthy: $healthy${NC}"
    log "${RED}Unhealthy: $unhealthy${NC}"
    log "${YELLOW}No healthcheck: $no_check${NC}"
    log ""

    if [[ ${#unhealthy_containers[@]} -gt 0 ]]; then
        log "${RED}Unhealthy Containers:${NC}"
        for container in "${unhealthy_containers[@]}"; do
            log "  ${RED}●${NC} $container"

            # Get health check logs
            local health_log=$(docker inspect --format='{{json .State.Health.Log}}' "$container" 2>/dev/null | jq -r '.[-1].Output // "No output"' 2>/dev/null | head -c 200)
            if [[ -n "$health_log" ]]; then
                log "    Last check: ${health_log}"
            fi
        done
        log ""
    fi

    if [[ ${#no_healthcheck[@]} -gt 0 && ${#no_healthcheck[@]} -le 20 ]]; then
        log "${YELLOW}Containers without healthcheck:${NC}"
        for container in "${no_healthcheck[@]}"; do
            log "  ${YELLOW}○${NC} $container"
        done
        log ""
    fi
}

output_json() {
    local healthy=$1
    local unhealthy=$2
    local no_check=$3
    local total=$4

    local unhealthy_json="[]"
    if [[ ${#unhealthy_containers[@]} -gt 0 ]]; then
        unhealthy_json=$(printf '%s\n' "${unhealthy_containers[@]}" | jq -R . | jq -s .)
    fi

    local no_check_json="[]"
    if [[ ${#no_healthcheck[@]} -gt 0 ]]; then
        no_check_json=$(printf '%s\n' "${no_healthcheck[@]}" | jq -R . | jq -s .)
    fi

    jq -n \
        --argjson healthy "$healthy" \
        --argjson unhealthy "$unhealthy" \
        --argjson no_check "$no_check" \
        --argjson total "$total" \
        --argjson unhealthy_list "$unhealthy_json" \
        --argjson no_check_list "$no_check_json" \
        '{
            summary: {
                total: $total,
                healthy: $healthy,
                unhealthy: $unhealthy,
                no_healthcheck: $no_check
            },
            unhealthy_containers: $unhealthy_list,
            no_healthcheck_containers: $no_check_list,
            timestamp: now | todate
        }'
}

restart_unhealthy() {
    if [[ ${#unhealthy_containers[@]} -eq 0 ]]; then
        log "${GREEN}No unhealthy containers to restart.${NC}"
        return 0
    fi

    log "${YELLOW}Attempting to restart unhealthy containers...${NC}"
    log ""

    for container in "${unhealthy_containers[@]}"; do
        if can_restart "$container"; then
            log "Restarting: $container"

            if docker restart "$container" 2>/dev/null; then
                record_restart "$container"
                log "${GREEN}  ✓ Restart initiated${NC}"
            else
                log "${RED}  ✗ Restart failed${NC}"
            fi
        else
            log "${YELLOW}  ○ Skipping $container (rate limited)${NC}"
        fi
    done
}

# Main
main() {
    init_restart_history
    check_containers

    if [[ "$RESTART_UNHEALTHY" == "true" && "$JSON_OUTPUT" != "true" ]]; then
        restart_unhealthy
    fi

    # Exit with error code if unhealthy containers exist
    if [[ ${#unhealthy_containers[@]} -gt 0 ]]; then
        exit 1
    fi
}

main
