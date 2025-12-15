#!/bin/bash
#
# Hydra Intelligence Layer Deployment
#
# Deploys Phase 11 Tools API, Voice Interface, STT, Wake Word, and CrewAI
# Plus imports n8n workflows and Prometheus recording rules
#
# Usage: ./deploy-intelligence-layer.sh [component]
# Components: all, tools, voice, stt, wakeword, crews, workflows, rules
#
# Generated: December 14, 2025

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HYDRA_STORAGE="192.168.1.244"
HYDRA_COMPUTE="192.168.1.203"
PROJECT_DIR="/c/Users/shaun/projects/hydra"
COMPOSE_DIR="${PROJECT_DIR}/docker-compose"
CONFIG_DIR="${PROJECT_DIR}/config"
N8N_WORKFLOWS="${CONFIG_DIR}/n8n/workflows"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Deploy Phase 11 Tools API
deploy_tools() {
    log_info "Deploying Phase 11 Tools API..."

    # Check if directory exists on hydra-storage
    ssh root@${HYDRA_STORAGE} "mkdir -p /mnt/user/appdata/hydra-tools/data"

    # Copy compose file
    scp ${COMPOSE_DIR}/hydra-tools-api.yml root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/

    # Copy source code
    ssh root@${HYDRA_STORAGE} "mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_tools"
    scp -r ${PROJECT_DIR}/src/hydra_tools/* root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/src/hydra_tools/

    # Copy Dockerfile
    scp ${PROJECT_DIR}/docker/Dockerfile.hydra-tools root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/docker/

    # Build and deploy
    ssh root@${HYDRA_STORAGE} "cd /mnt/user/appdata/hydra-stack && docker-compose -f hydra-tools-api.yml build && docker-compose -f hydra-tools-api.yml up -d"

    log_success "Phase 11 Tools API deployed on port 8700"
}

# Deploy STT Service (on hydra-compute for GPU)
deploy_stt() {
    log_info "Deploying STT Service on hydra-compute..."

    # Copy source to hydra-compute
    ssh typhon@${HYDRA_COMPUTE} "mkdir -p ~/hydra-stt"
    scp -r ${PROJECT_DIR}/src/hydra_stt/* typhon@${HYDRA_COMPUTE}:~/hydra-stt/

    # Build Docker image on hydra-compute
    ssh typhon@${HYDRA_COMPUTE} "cd ~/hydra-stt && docker build -t hydra-stt:latest ."

    # Run the container
    ssh typhon@${HYDRA_COMPUTE} "docker stop hydra-stt 2>/dev/null || true && docker rm hydra-stt 2>/dev/null || true"
    ssh typhon@${HYDRA_COMPUTE} "docker run -d --name hydra-stt --gpus '\"device=1\"' -p 9001:9001 --restart unless-stopped hydra-stt:latest"

    log_success "STT Service deployed on hydra-compute:9001"
}

# Deploy Voice Interface
deploy_voice() {
    log_info "Deploying Voice Interface..."

    # Copy compose file and source
    scp ${COMPOSE_DIR}/voice-interface.yml root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/
    ssh root@${HYDRA_STORAGE} "mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_voice"
    scp -r ${PROJECT_DIR}/src/hydra_voice/* root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/src/hydra_voice/

    # Build and deploy
    ssh root@${HYDRA_STORAGE} "cd /mnt/user/appdata/hydra-stack && docker-compose -f voice-interface.yml build && docker-compose -f voice-interface.yml up -d"

    log_success "Voice Interface deployed on port 8850"
}

# Deploy Wake Word Service
# Note: This typically runs on a device with a microphone (RPi, mini PC)
# The compose file is provided for reference; actual deployment may vary
deploy_wakeword() {
    log_info "Deploying Wake Word Service..."
    log_warning "Note: Wake word service requires audio device access"

    # Copy compose file and source to hydra-storage (or edge device)
    scp ${COMPOSE_DIR}/wakeword-service.yml root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/
    ssh root@${HYDRA_STORAGE} "mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_wakeword"
    scp -r ${PROJECT_DIR}/src/hydra_wakeword/* root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/src/hydra_wakeword/

    log_info "Wake word service files copied. Deploy to device with: docker-compose -f wakeword-service.yml up -d"
    log_success "Wake Word Service ready for deployment on port 8860"
}

# Deploy CrewAI Crews
deploy_crews() {
    log_info "Deploying CrewAI Crews..."

    # Copy crews module to hydra-storage
    ssh root@${HYDRA_STORAGE} "mkdir -p /mnt/user/appdata/hydra-stack/src/hydra_crews"
    scp -r ${PROJECT_DIR}/src/hydra_crews/* root@${HYDRA_STORAGE}:/mnt/user/appdata/hydra-stack/src/hydra_crews/

    log_success "CrewAI Crews deployed (ResearchCrew, MonitoringCrew, MaintenanceCrew)"
}

# Import n8n workflows
import_workflows() {
    log_info "Importing n8n workflows..."

    # List of workflows to import
    # Priority: Critical monitoring and automation workflows first
    WORKFLOWS=(
        # Core monitoring & alerting
        "health-digest-clean.json"
        "alertmanager-handler-v2.json"
        "resource-monitor.json"
        "container-restart-ratelimit.json"
        "gpu-thermal-handler.json"
        "disk-cleanup-automation.json"
        # Database operations
        "postgres-backup.json"
        "scheduled-database-backup.json"
        "qdrant-maintenance.json"
        # Intelligence layer
        "model-performance-tracker.json"
        "activity-logger.json"
        "morning-briefing.json"
        # Voice & CrewAI
        "voice-command-processor.json"
        "crewai-task-dispatcher.json"
        # Knowledge management
        "knowledge-refresh-clean.json"
        "learnings-capture-clean.json"
        "letta-memory-update-clean.json"
        # Research automation
        "autonomous-research-clean.json"
        # Integration workflows
        "github-webhook-handler.json"
        "email-digest-sender.json"
        "discord-notification-bridge.json"
        "rss-feed-processor.json"
        # Advanced automation
        "model-benchmark-automation.json"
        "service-dependency-restart.json"
        "usage-tracking-aggregator.json"
        "uptime-kuma-alert-handler.json"
    )

    for workflow in "${WORKFLOWS[@]}"; do
        if [ -f "${N8N_WORKFLOWS}/${workflow}" ]; then
            log_info "  Importing ${workflow}..."
            # n8n API import (adjust URL and credentials as needed)
            curl -s -X POST "http://${HYDRA_STORAGE}:5678/api/v1/workflows" \
                -H "Content-Type: application/json" \
                -d @"${N8N_WORKFLOWS}/${workflow}" > /dev/null 2>&1 || log_warning "  Could not import ${workflow} via API"
        else
            log_warning "  Workflow not found: ${workflow}"
        fi
    done

    log_success "Workflow import complete (verify in n8n UI)"
}

# Deploy Prometheus recording rules
deploy_rules() {
    log_info "Deploying Prometheus recording rules..."

    # Copy recording rules
    scp ${CONFIG_DIR}/prometheus/rules/recording-rules.yml root@${HYDRA_STORAGE}:/mnt/user/appdata/prometheus/rules/

    # Reload Prometheus
    curl -s -X POST "http://${HYDRA_STORAGE}:9090/-/reload" > /dev/null 2>&1 || log_warning "Could not reload Prometheus (may need manual restart)"

    log_success "Recording rules deployed"
}

# Verify deployments
verify() {
    log_info "Verifying deployments..."

    echo ""
    echo "Phase 11 Tools API:"
    curl -s "http://${HYDRA_STORAGE}:8700/health" | jq . 2>/dev/null || echo "  Not responding"

    echo ""
    echo "STT Service:"
    curl -s "http://${HYDRA_COMPUTE}:9001/health" | jq . 2>/dev/null || echo "  Not responding"

    echo ""
    echo "Voice Interface:"
    curl -s "http://${HYDRA_STORAGE}:8850/health" | jq . 2>/dev/null || echo "  Not responding"

    echo ""
    echo "Voice Pipeline Status:"
    curl -s "http://${HYDRA_STORAGE}:8850/status" | jq . 2>/dev/null || echo "  Not responding"

    echo ""
    echo "Prometheus Rules:"
    curl -s "http://${HYDRA_STORAGE}:9090/api/v1/rules" | jq '.data.groups | length' 2>/dev/null || echo "  Could not query"

    echo ""
    echo "Letta Agent:"
    curl -s "http://${HYDRA_STORAGE}:8283/v1/agents" | jq '.[0].name' 2>/dev/null || echo "  Not responding"
}

# Main
main() {
    local component="${1:-all}"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       HYDRA INTELLIGENCE LAYER DEPLOYMENT                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    case "$component" in
        tools)
            deploy_tools
            ;;
        stt)
            deploy_stt
            ;;
        voice)
            deploy_voice
            ;;
        wakeword)
            deploy_wakeword
            ;;
        crews)
            deploy_crews
            ;;
        workflows)
            import_workflows
            ;;
        rules)
            deploy_rules
            ;;
        verify)
            verify
            ;;
        all)
            deploy_tools
            deploy_stt
            deploy_voice
            deploy_wakeword
            deploy_crews
            deploy_rules
            import_workflows
            echo ""
            verify
            ;;
        *)
            echo "Usage: $0 [all|tools|stt|voice|wakeword|crews|workflows|rules|verify]"
            exit 1
            ;;
    esac

    echo ""
    log_success "Deployment complete!"
    echo ""
    echo "Endpoints:"
    echo "  - Phase 11 Tools API: http://${HYDRA_STORAGE}:8700/docs"
    echo "  - STT Service:        http://${HYDRA_COMPUTE}:9001/docs"
    echo "  - Voice Interface:    http://${HYDRA_STORAGE}:8850/docs"
    echo "  - Wake Word Service:  http://<device>:8860/docs"
    echo "  - n8n Workflows:      http://${HYDRA_STORAGE}:5678"
    echo ""
    echo "CrewAI Crews available:"
    echo "  - ResearchCrew:    Autonomous web research and synthesis"
    echo "  - MonitoringCrew:  Cluster health surveillance"
    echo "  - MaintenanceCrew: Automated maintenance tasks"
    echo ""
}

main "$@"
