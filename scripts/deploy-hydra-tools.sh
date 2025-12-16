#!/bin/bash
# Deploy Hydra Tools API to the cluster
# Usage: ./scripts/deploy-hydra-tools.sh [--build] [--dry-run]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STORAGE_HOST="192.168.1.244"
STORAGE_USER="root"
DEPLOY_PATH="/mnt/user/appdata/hydra-tools"
STACK_PATH="/mnt/user/appdata/hydra-stack"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
BUILD=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--build] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --build    Build Docker image locally before deploying"
            echo "  --dry-run  Show what would be done without executing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "  Would run: $*"
    else
        "$@"
    fi
}

ssh_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "  Would run on ${STORAGE_HOST}: $*"
    else
        ssh "${STORAGE_USER}@${STORAGE_HOST}" "$@"
    fi
}

# Main deployment
log "Hydra Tools API Deployment"
echo "----------------------------------------"
echo "Target: ${STORAGE_USER}@${STORAGE_HOST}"
echo "Path: ${DEPLOY_PATH}"
echo "Build: ${BUILD}"
echo "Dry Run: ${DRY_RUN}"
echo "----------------------------------------"

# Step 1: Create deployment directory
log "Step 1: Creating deployment directory..."
ssh_cmd "mkdir -p ${DEPLOY_PATH}/{src,data/{diagnosis,optimization,knowledge,capabilities}}"
success "Directory structure created"

# Step 2: Copy source files
log "Step 2: Copying source files..."
if [ "$DRY_RUN" = false ]; then
    scp -r "${PROJECT_ROOT}/src/hydra_tools" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/src/"
    scp "${PROJECT_ROOT}/requirements.txt" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/"
    scp "${PROJECT_ROOT}/docker/Dockerfile.hydra-tools" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/"
    scp "${PROJECT_ROOT}/docker-compose/hydra-tools-api.yml" "${STORAGE_USER}@${STORAGE_HOST}:${DEPLOY_PATH}/"
else
    echo "  Would copy: src/hydra_tools -> ${DEPLOY_PATH}/src/"
    echo "  Would copy: requirements.txt -> ${DEPLOY_PATH}/"
    echo "  Would copy: Dockerfile.hydra-tools -> ${DEPLOY_PATH}/"
    echo "  Would copy: hydra-tools-api.yml -> ${DEPLOY_PATH}/"
fi
success "Source files copied"

# Step 3: Build Docker image (if requested)
if [ "$BUILD" = true ]; then
    log "Step 3: Building Docker image..."
    ssh_cmd "cd ${DEPLOY_PATH} && docker build -f Dockerfile.hydra-tools -t hydra-tools-api:latest ."
    success "Docker image built"
else
    log "Step 3: Skipping Docker build (use --build to enable)"
fi

# Step 4: Create docker-compose override for local paths
log "Step 4: Creating compose configuration..."
ssh_cmd "cat > ${DEPLOY_PATH}/docker-compose.override.yml << 'EOF'
version: \"3.8\"

services:
  hydra-tools-api:
    volumes:
      - ${DEPLOY_PATH}/data:/data:rw
      - ${STACK_PATH}/data:/mnt/data:rw
EOF
"
success "Compose configuration created"

# Step 5: Deploy container
log "Step 5: Deploying container..."
ssh_cmd "cd ${DEPLOY_PATH} && docker-compose -f hydra-tools-api.yml -f docker-compose.override.yml up -d"
success "Container deployed"

# Step 6: Wait for health check
log "Step 6: Waiting for health check..."
if [ "$DRY_RUN" = false ]; then
    for i in {1..10}; do
        if ssh "${STORAGE_USER}@${STORAGE_HOST}" "curl -sf http://localhost:8700/health > /dev/null 2>&1"; then
            success "Health check passed!"
            break
        fi
        echo "  Waiting... (${i}/10)"
        sleep 2
    done
else
    echo "  Would wait for health check at http://localhost:8700/health"
fi

# Step 7: Show status
log "Step 7: Deployment status"
if [ "$DRY_RUN" = false ]; then
    ssh "${STORAGE_USER}@${STORAGE_HOST}" "docker ps --filter name=hydra-tools-api --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    echo ""
    echo "API Endpoints (v1.4.0):"
    echo "  Core:"
    echo "    Health:       http://${STORAGE_HOST}:8700/health"
    echo "    Docs:         http://${STORAGE_HOST}:8700/docs"
    echo "    Diagnosis:    http://${STORAGE_HOST}:8700/diagnosis"
    echo "    Optimization: http://${STORAGE_HOST}:8700/optimization"
    echo "    Knowledge:    http://${STORAGE_HOST}:8700/knowledge"
    echo "    Capabilities: http://${STORAGE_HOST}:8700/capabilities"
    echo ""
    echo "  Search & Research:"
    echo "    Search:       http://${STORAGE_HOST}:8700/search"
    echo "    Ingest:       http://${STORAGE_HOST}:8700/ingest"
    echo "    Research:     http://${STORAGE_HOST}:8700/research"
    echo ""
    echo "  Autonomous Systems:"
    echo "    Crews:        http://${STORAGE_HOST}:8700/crews"
    echo "    Alerts:       http://${STORAGE_HOST}:8700/alerts"
    echo "    Reconcile:    http://${STORAGE_HOST}:8700/reconcile"
    echo ""
    echo "  Cluster Management:"
    echo "    Health:       http://${STORAGE_HOST}:8700/health/cluster"
    echo "    Voice:        http://${STORAGE_HOST}:8700/voice"
    echo ""
    echo "Run ./scripts/test-api-endpoints.sh to verify all endpoints"
else
    echo "  Would show container status"
fi

echo ""
success "Deployment complete!"
