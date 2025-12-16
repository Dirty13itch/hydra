#!/bin/bash
# Quick restart of Hydra Tools API with updated source
# Usage: ./scripts/restart-hydra-tools.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STORAGE_HOST="192.168.1.244"
STORAGE_USER="root"
DEPLOY_PATH="/mnt/user/appdata/hydra-tools"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }

log "Quick restart of Hydra Tools API..."

# Step 1: Copy updated source
log "Copying updated source files..."
scp -r "${PROJECT_ROOT}/src/hydra_tools" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/src/"

# Also copy any supporting modules
for module in hydra_search hydra_crews hydra_alerts hydra_health hydra_voice hydra_reconcile; do
    if [ -d "${PROJECT_ROOT}/src/${module}" ]; then
        scp -r "${PROJECT_ROOT}/src/${module}" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/src/"
    fi
done
success "Source files copied"

# Step 2: Restart container
log "Restarting container..."
ssh "${STORAGE_USER}@${STORAGE_HOST}" "docker restart hydra-tools-api"
success "Container restarted"

# Step 3: Wait for health
log "Waiting for health check..."
for i in {1..15}; do
    if ssh "${STORAGE_USER}@${STORAGE_HOST}" "curl -sf http://localhost:8700/health > /dev/null 2>&1"; then
        success "Health check passed!"
        break
    fi
    echo "  Waiting... (${i}/15)"
    sleep 2
done

# Step 4: Show version
log "Checking API version..."
VERSION=$(ssh "${STORAGE_USER}@${STORAGE_HOST}" "curl -sf http://localhost:8700/ | jq -r '.version'" 2>/dev/null || echo "unknown")
echo "  API Version: ${VERSION}"

success "Restart complete!"
echo ""
echo "Run ./scripts/test-api-endpoints.sh to verify all endpoints"
