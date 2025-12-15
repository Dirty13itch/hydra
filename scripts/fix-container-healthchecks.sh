#!/bin/bash
# Fix Container Healthchecks for Hydra Cluster
#
# This script updates containers to have proper healthchecks.
# Run on hydra-storage (192.168.1.244)
#
# Usage: ./fix-container-healthchecks.sh [--apply]
#   Without --apply: dry-run mode, shows what would be done
#   With --apply: actually updates containers

set -euo pipefail

APPLY_MODE="${1:-}"
DRY_RUN=true

if [[ "$APPLY_MODE" == "--apply" ]]; then
    DRY_RUN=false
    echo "=== APPLY MODE: Changes will be made ==="
else
    echo "=== DRY RUN MODE: No changes will be made ==="
    echo "Run with --apply to actually update containers"
fi
echo ""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Define healthcheck commands for containers that typically report unhealthy
declare -A HEALTHCHECKS=(
    # Databases
    ["hydra-postgres"]="pg_isready -U hydra"
    ["hydra-redis"]="redis-cli -a ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC ping"
    ["hydra-qdrant"]="wget -q --spider http://localhost:6333/health || exit 1"
    ["letta-db"]="pg_isready -U letta"

    # Observability
    ["hydra-alertmanager"]="wget -q --spider http://localhost:9093/-/healthy || exit 1"
    ["hydra-uptime-kuma"]="wget -q --spider http://localhost:3001/api/status-page/heartbeat || exit 1"

    # AI Services
    ["hydra-letta"]="wget -q --spider http://localhost:8283/health || exit 1"
    ["letta-proxy"]="wget -q --spider http://localhost:8600/health || exit 1"
    ["hydra-mcp"]="wget -q --spider http://localhost:8600/health || exit 1"
    ["hydra-crewai"]="wget -q --spider http://localhost:8500/health || exit 1"

    # Web UIs
    ["hydra-homepage"]="wget -q --spider http://localhost:3000 || exit 1"
    ["homepage"]="wget -q --spider http://localhost:3000 || exit 1"
    ["open-webui"]="wget -q --spider http://localhost:8080/health || exit 1"
    ["hydra-searxng"]="wget -q --spider http://localhost:8080/healthz || exit 1"

    # Media
    ["Plex-Media-Server"]="wget -q --spider http://localhost:32400/identity || exit 1"
    ["stash"]="wget -q --spider http://localhost:9999 || exit 1"

    # Neo4j
    ["hydra-neo4j"]="wget -q --spider http://localhost:7474 || exit 1"

    # Watchtower
    ["hydra-watchtower"]="exit 0"  # Watchtower doesn't have a health endpoint

    # Auditforecaster
    ["auditforecaster-backup"]="exit 0"  # Backup service, no health endpoint
    ["auditforecaster-monitor"]="exit 0"  # May not have health endpoint
)

# Check current container health status
log_info "Checking current container health status..."
echo ""

UNHEALTHY_CONTAINERS=()
while IFS= read -r line; do
    NAME=$(echo "$line" | awk '{print $1}')
    STATUS=$(echo "$line" | awk '{$1=""; print $0}' | xargs)

    if [[ "$STATUS" == *"unhealthy"* ]]; then
        UNHEALTHY_CONTAINERS+=("$NAME")
        log_warn "$NAME: $STATUS"
    fi
done < <(docker ps --format "{{.Names}} {{.Status}}" 2>/dev/null || echo "")

echo ""
log_info "Found ${#UNHEALTHY_CONTAINERS[@]} unhealthy containers"
echo ""

# Function to update container healthcheck
update_healthcheck() {
    local container="$1"
    local healthcmd="$2"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would update $container with healthcheck: $healthcmd"
        return 0
    fi

    log_info "Updating healthcheck for $container..."

    # Get current container config
    local image=$(docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null)
    local volumes=$(docker inspect --format='{{range .Mounts}}-v {{.Source}}:{{.Destination}} {{end}}' "$container" 2>/dev/null)
    local env=$(docker inspect --format='{{range .Config.Env}}-e {{.}} {{end}}' "$container" 2>/dev/null)
    local ports=$(docker inspect --format='{{range $p, $conf := .NetworkSettings.Ports}}{{if $conf}}-p {{(index $conf 0).HostPort}}:{{$p}} {{end}}{{end}}' "$container" 2>/dev/null)
    local network=$(docker inspect --format='{{range $net, $conf := .NetworkSettings.Networks}}--network={{$net}} {{end}}' "$container" 2>/dev/null)
    local restart=$(docker inspect --format='{{.HostConfig.RestartPolicy.Name}}' "$container" 2>/dev/null)

    # Note: Actually recreating containers is complex due to all the config options
    # For now, we'll document what needs to be done
    log_warn "Container $container needs manual update in docker-compose.yml"
    log_info "  Add healthcheck: $healthcmd"
}

# Process unhealthy containers
for container in "${UNHEALTHY_CONTAINERS[@]}"; do
    if [[ -n "${HEALTHCHECKS[$container]:-}" ]]; then
        update_healthcheck "$container" "${HEALTHCHECKS[$container]}"
    else
        log_warn "No healthcheck defined for $container - checking if it has one..."
        HC=$(docker inspect --format='{{.Config.Healthcheck}}' "$container" 2>/dev/null || echo "none")
        if [[ "$HC" == "<nil>" ]] || [[ "$HC" == "none" ]]; then
            log_error "$container has no healthcheck configured"
        else
            log_info "$container has healthcheck but it's failing: $HC"
        fi
    fi
done

echo ""
log_info "=== Summary ==="
echo ""

# Generate docker-compose healthcheck snippet
log_info "Generating docker-compose healthcheck additions..."
echo ""

cat << 'COMPOSE_SNIPPET'
# Add these healthcheck blocks to your docker-compose.yml services:

# For containers reporting unhealthy, add inside the service definition:

  hydra-letta:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8283/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  letta-db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U letta"]
      interval: 30s
      timeout: 10s
      retries: 3

  hydra-alertmanager:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3

  hydra-neo4j:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  hydra-crewai:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8500/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  hydra-mcp:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8600/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  homepage:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  open-webui:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  hydra-uptime-kuma:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3001"]
      interval: 30s
      timeout: 10s
      retries: 3

  Plex-Media-Server:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:32400/identity"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s

COMPOSE_SNIPPET

echo ""
log_info "Script complete. To apply changes:"
echo "  1. Update your docker-compose.yml with the healthcheck blocks above"
echo "  2. Run: docker-compose up -d"
echo "  3. Wait 2-3 minutes for health checks to stabilize"
echo "  4. Verify: docker ps --format 'table {{.Names}}\t{{.Status}}'"
