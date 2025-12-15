#!/bin/bash
# Hydra Cluster Bootstrap Script
#
# Automates initial setup and verification of the Hydra cluster.
# Run this after fresh deployment or to verify cluster health.
#
# Usage:
#   ./bootstrap-cluster.sh              # Full bootstrap
#   ./bootstrap-cluster.sh verify       # Verify only
#   ./bootstrap-cluster.sh deploy       # Deploy configs only

set -euo pipefail

# ===========================================
# CONFIGURATION
# ===========================================

HYDRA_AI="192.168.1.250"
HYDRA_COMPUTE="192.168.1.203"
HYDRA_STORAGE="192.168.1.244"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN} $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"; }

# ===========================================
# PREREQUISITE CHECKS
# ===========================================

check_prerequisites() {
    log_section "Checking Prerequisites"

    local missing=()

    # Check required tools
    for cmd in ssh curl jq docker; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi

    log_success "All required tools available"

    # Check SSH connectivity
    log_info "Testing SSH connectivity..."

    if ssh -o ConnectTimeout=5 -o BatchMode=yes typhon@$HYDRA_AI "true" 2>/dev/null; then
        log_success "hydra-ai: SSH OK"
    else
        log_error "hydra-ai: SSH failed"
    fi

    if ssh -o ConnectTimeout=5 -o BatchMode=yes typhon@$HYDRA_COMPUTE "true" 2>/dev/null; then
        log_success "hydra-compute: SSH OK"
    else
        log_error "hydra-compute: SSH failed"
    fi

    if ssh -o ConnectTimeout=5 -o BatchMode=yes root@$HYDRA_STORAGE "true" 2>/dev/null; then
        log_success "hydra-storage: SSH OK"
    else
        log_error "hydra-storage: SSH failed"
    fi
}

# ===========================================
# NETWORK VERIFICATION
# ===========================================

verify_network() {
    log_section "Verifying Network"

    # Check inter-node connectivity
    log_info "Testing inter-node latency..."

    for src in "typhon@$HYDRA_AI" "typhon@$HYDRA_COMPUTE" "root@$HYDRA_STORAGE"; do
        for dst in $HYDRA_AI $HYDRA_COMPUTE $HYDRA_STORAGE; do
            latency=$(ssh -o ConnectTimeout=5 "$src" "ping -c 1 -W 1 $dst 2>/dev/null | grep 'time=' | sed 's/.*time=\([0-9.]*\).*/\1/'" 2>/dev/null || echo "failed")
            if [[ "$latency" != "failed" ]]; then
                echo "  $src -> $dst: ${latency}ms"
            else
                log_warn "$src -> $dst: unreachable"
            fi
        done
    done

    # Check DNS
    log_info "Testing DNS resolution..."
    if ssh typhon@$HYDRA_AI "host google.com" &>/dev/null; then
        log_success "hydra-ai: DNS OK"
    else
        log_warn "hydra-ai: DNS issues"
    fi
}

# ===========================================
# GPU VERIFICATION
# ===========================================

verify_gpus() {
    log_section "Verifying GPUs"

    # hydra-ai GPUs
    log_info "hydra-ai GPUs:"
    if gpu_info=$(ssh typhon@$HYDRA_AI "nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader" 2>/dev/null); then
        echo "$gpu_info" | while read -r line; do
            echo "  $line"
        done
        log_success "hydra-ai: $(echo "$gpu_info" | wc -l) GPU(s) detected"
    else
        log_error "hydra-ai: GPU detection failed"
    fi

    # hydra-compute GPUs
    log_info "hydra-compute GPUs:"
    if gpu_info=$(ssh typhon@$HYDRA_COMPUTE "nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader" 2>/dev/null); then
        echo "$gpu_info" | while read -r line; do
            echo "  $line"
        done
        log_success "hydra-compute: $(echo "$gpu_info" | wc -l) GPU(s) detected"
    else
        log_error "hydra-compute: GPU detection failed"
    fi
}

# ===========================================
# STORAGE VERIFICATION
# ===========================================

verify_storage() {
    log_section "Verifying Storage"

    # NFS mounts on NixOS nodes
    log_info "Checking NFS mounts..."

    if ssh typhon@$HYDRA_AI "df -h /mnt/models 2>/dev/null | tail -1"; then
        log_success "hydra-ai: /mnt/models mounted"
    else
        log_warn "hydra-ai: /mnt/models not mounted"
    fi

    if ssh typhon@$HYDRA_COMPUTE "df -h /mnt/models 2>/dev/null | tail -1"; then
        log_success "hydra-compute: /mnt/models mounted"
    else
        log_warn "hydra-compute: /mnt/models not mounted"
    fi

    # Unraid array status
    log_info "Unraid array status..."
    if parity_status=$(ssh root@$HYDRA_STORAGE "cat /proc/mdcmd 2>/dev/null | grep -E 'mdState|sbSynced'" 2>/dev/null); then
        echo "$parity_status"
    else
        ssh root@$HYDRA_STORAGE "df -h /mnt/user 2>/dev/null | tail -1" || true
    fi
}

# ===========================================
# SERVICE VERIFICATION
# ===========================================

verify_services() {
    log_section "Verifying Services"

    local services=(
        "TabbyAPI:http://$HYDRA_AI:5000/v1/model"
        "Ollama:http://$HYDRA_COMPUTE:11434/api/tags"
        "LiteLLM:http://$HYDRA_STORAGE:4000/health"
        "Qdrant:http://$HYDRA_STORAGE:6333/health"
        "PostgreSQL:tcp://$HYDRA_STORAGE:5432"
        "Redis:tcp://$HYDRA_STORAGE:6379"
        "Prometheus:http://$HYDRA_STORAGE:9090/-/healthy"
        "Grafana:http://$HYDRA_STORAGE:3003/api/health"
        "n8n:http://$HYDRA_STORAGE:5678/healthz"
        "SearXNG:http://$HYDRA_STORAGE:8888/healthz"
        "ComfyUI:http://$HYDRA_COMPUTE:8188/system_stats"
    )

    local up=0
    local down=0

    for service_info in "${services[@]}"; do
        IFS=: read -r name proto rest <<< "$service_info"
        url="${proto}:${rest}"

        if [[ "$proto" == "tcp" ]]; then
            host_port="${rest#//}"
            host="${host_port%:*}"
            port="${host_port#*:}"
            if timeout 2 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
                log_success "$name"
                ((up++))
            else
                log_error "$name (DOWN)"
                ((down++))
            fi
        else
            if curl -sf --connect-timeout 5 "$url" &>/dev/null; then
                log_success "$name"
                ((up++))
            else
                log_error "$name (DOWN)"
                ((down++))
            fi
        fi
    done

    echo
    log_info "Services: $up UP, $down DOWN"
}

# ===========================================
# DATABASE VERIFICATION
# ===========================================

verify_databases() {
    log_section "Verifying Databases"

    # PostgreSQL
    log_info "PostgreSQL databases..."
    if dbs=$(ssh root@$HYDRA_STORAGE "docker exec hydra-postgres psql -U hydra -c '\l' --no-align -t 2>/dev/null | cut -d'|' -f1 | grep -v template | grep -v postgres"); then
        echo "$dbs" | while read -r db; do
            if [[ -n "$db" ]]; then
                echo "  - $db"
            fi
        done
    else
        log_warn "Could not list PostgreSQL databases"
    fi

    # Qdrant collections
    log_info "Qdrant collections..."
    if collections=$(curl -sf "http://$HYDRA_STORAGE:6333/collections" | jq -r '.result.collections[].name' 2>/dev/null); then
        if [[ -n "$collections" ]]; then
            echo "$collections" | while read -r col; do
                echo "  - $col"
            done
        else
            log_info "No collections found"
        fi
    else
        log_warn "Could not list Qdrant collections"
    fi

    # Redis
    log_info "Redis info..."
    if redis_info=$(ssh root@$HYDRA_STORAGE "docker exec hydra-redis redis-cli -a ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC INFO keyspace 2>/dev/null | grep -v '#'"); then
        echo "$redis_info"
    else
        log_warn "Could not get Redis info"
    fi
}

# ===========================================
# CONFIG DEPLOYMENT
# ===========================================

deploy_configs() {
    log_section "Deploying Configurations"

    # Deploy Prometheus config
    log_info "Deploying Prometheus configuration..."
    if [[ -f "$REPO_ROOT/config/prometheus/prometheus.yml" ]]; then
        scp "$REPO_ROOT/config/prometheus/prometheus.yml" \
            "root@$HYDRA_STORAGE:/mnt/user/appdata/hydra-stack/prometheus/prometheus.yml"
        log_success "Prometheus config deployed"

        # Reload Prometheus
        curl -X POST "http://$HYDRA_STORAGE:9090/-/reload" 2>/dev/null && \
            log_success "Prometheus reloaded" || \
            log_warn "Could not reload Prometheus"
    fi

    # Deploy alert rules
    if [[ -f "$REPO_ROOT/config/prometheus/rules/hydra-alerts.yml" ]]; then
        scp "$REPO_ROOT/config/prometheus/rules/hydra-alerts.yml" \
            "root@$HYDRA_STORAGE:/mnt/user/appdata/hydra-stack/prometheus/rules/hydra-alerts.yml"
        log_success "Alert rules deployed"
    fi

    # Deploy Grafana dashboards
    log_info "Deploying Grafana dashboards..."
    if [[ -d "$REPO_ROOT/config/grafana/dashboards" ]]; then
        scp -r "$REPO_ROOT/config/grafana/dashboards/"*.json \
            "root@$HYDRA_STORAGE:/mnt/user/appdata/hydra-stack/grafana/provisioning/dashboards/" 2>/dev/null || true
        log_success "Grafana dashboards deployed"
    fi
}

# ===========================================
# GPU POWER SETUP
# ===========================================

setup_gpu_power() {
    log_section "Setting GPU Power Limits"

    # hydra-ai: 5090 (450W) + 4090 (300W)
    log_info "Setting hydra-ai GPU power limits..."
    ssh typhon@$HYDRA_AI "sudo nvidia-smi -i 0 -pl 450 && sudo nvidia-smi -i 1 -pl 300" 2>/dev/null && \
        log_success "hydra-ai power limits set" || \
        log_warn "Could not set hydra-ai power limits"

    # hydra-compute: 5070 Ti (250W) + 3060 (150W)
    log_info "Setting hydra-compute GPU power limits..."
    ssh typhon@$HYDRA_COMPUTE "sudo nvidia-smi -i 0 -pl 250 && sudo nvidia-smi -i 1 -pl 150" 2>/dev/null && \
        log_success "hydra-compute power limits set" || \
        log_warn "Could not set hydra-compute power limits"
}

# ===========================================
# DOCKER STATUS
# ===========================================

check_docker() {
    log_section "Docker Container Status"

    log_info "Running containers on hydra-storage..."
    container_count=$(ssh root@$HYDRA_STORAGE "docker ps --format '{{.Names}}' | wc -l" 2>/dev/null || echo "0")
    log_info "Total running containers: $container_count"

    # Show any unhealthy containers
    unhealthy=$(ssh root@$HYDRA_STORAGE "docker ps --filter 'health=unhealthy' --format '{{.Names}}'" 2>/dev/null || echo "")
    if [[ -n "$unhealthy" ]]; then
        log_warn "Unhealthy containers:"
        echo "$unhealthy" | while read -r c; do
            echo "  - $c"
        done
    fi

    # Show recently restarted
    restarting=$(ssh root@$HYDRA_STORAGE "docker ps --filter 'status=restarting' --format '{{.Names}}'" 2>/dev/null || echo "")
    if [[ -n "$restarting" ]]; then
        log_warn "Restarting containers:"
        echo "$restarting"
    fi
}

# ===========================================
# SUMMARY
# ===========================================

print_summary() {
    log_section "Bootstrap Summary"

    echo "Hydra Cluster Status:"
    echo "  hydra-ai:      $HYDRA_AI (NixOS, TabbyAPI, 5090+4090)"
    echo "  hydra-compute: $HYDRA_COMPUTE (NixOS, Ollama, ComfyUI, 5070Ti+3060)"
    echo "  hydra-storage: $HYDRA_STORAGE (Unraid, Docker services)"
    echo
    echo "Key URLs:"
    echo "  TabbyAPI:  http://$HYDRA_AI:5000"
    echo "  LiteLLM:   http://$HYDRA_STORAGE:4000"
    echo "  Grafana:   http://$HYDRA_STORAGE:3003"
    echo "  Prometheus: http://$HYDRA_STORAGE:9090"
    echo "  n8n:       http://$HYDRA_STORAGE:5678"
    echo "  Open WebUI: http://$HYDRA_AI:3000"
    echo
    log_success "Bootstrap complete!"
}

# ===========================================
# MAIN
# ===========================================

cmd_full() {
    check_prerequisites
    verify_network
    verify_gpus
    verify_storage
    verify_services
    verify_databases
    check_docker
    setup_gpu_power
    deploy_configs
    print_summary
}

cmd_verify() {
    check_prerequisites
    verify_network
    verify_gpus
    verify_storage
    verify_services
    verify_databases
    check_docker
    print_summary
}

cmd_deploy() {
    check_prerequisites
    deploy_configs
    log_success "Deployment complete"
}

main() {
    local cmd="${1:-full}"

    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                    HYDRA CLUSTER BOOTSTRAP                           ║"
    echo "║                         $(date '+%Y-%m-%d %H:%M:%S')                            ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"

    case "$cmd" in
        full|bootstrap)
            cmd_full
            ;;
        verify|check)
            cmd_verify
            ;;
        deploy)
            cmd_deploy
            ;;
        help|-h|--help)
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  full     - Full bootstrap (verify + deploy + setup)"
            echo "  verify   - Verify cluster health only"
            echo "  deploy   - Deploy configurations only"
            ;;
        *)
            log_error "Unknown command: $cmd"
            exit 1
            ;;
    esac
}

main "$@"
