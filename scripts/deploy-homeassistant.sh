#!/bin/bash
# Home Assistant Integration Deployment Script
#
# Deploys Hydra cluster integration configs to the live Home Assistant instance.
#
# Usage:
#   ./deploy-homeassistant.sh [--dry-run]
#
# This script:
#   1. Validates YAML syntax
#   2. Backs up existing configs
#   3. Deploys new configs
#   4. Restarts Home Assistant
#   5. Verifies deployment

set -euo pipefail

# Configuration
HA_HOST="${HA_HOST:-192.168.1.244}"
HA_PORT="${HA_PORT:-8123}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/mnt/user/appdata/homeassistant}"
LOCAL_CONFIG_DIR="$(dirname "$0")/../homeassistant"
DRY_RUN="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${CYAN}=== $1 ===${NC}\n"; }

# Check if running in dry-run mode
if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log_warn "DRY RUN MODE - No changes will be made"
    DRY_RUN=true
else
    DRY_RUN=false
fi

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"

    # Check if local config files exist
    if [[ ! -d "$LOCAL_CONFIG_DIR" ]]; then
        log_error "Local config directory not found: $LOCAL_CONFIG_DIR"
        exit 1
    fi

    # Check for required files
    local required_files=(
        "automations.yaml"
        "configuration.yaml"
        "shell_commands.yaml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$LOCAL_CONFIG_DIR/$file" ]]; then
            log_warn "Missing config file: $file"
        else
            log_info "Found: $file"
        fi
    done

    # Check if yq is available for YAML validation
    if command -v yq &> /dev/null; then
        log_info "YAML validator (yq) available"
    else
        log_warn "yq not found - YAML validation will be skipped"
    fi

    # Check Home Assistant connectivity
    if curl -sf "http://${HA_HOST}:${HA_PORT}/api/" &>/dev/null; then
        log_info "Home Assistant reachable at ${HA_HOST}:${HA_PORT}"
    else
        log_warn "Cannot reach Home Assistant at ${HA_HOST}:${HA_PORT}"
        log_info "Deployment will proceed but verification may fail"
    fi
}

# Validate YAML files
validate_yaml() {
    log_section "Validating YAML Files"

    local valid=true

    for file in "$LOCAL_CONFIG_DIR"/*.yaml; do
        if [[ -f "$file" ]]; then
            filename=$(basename "$file")
            if command -v yq &> /dev/null; then
                if yq eval '.' "$file" > /dev/null 2>&1; then
                    log_info "Valid: $filename"
                else
                    log_error "Invalid YAML: $filename"
                    valid=false
                fi
            else
                # Basic check - ensure file is not empty
                if [[ -s "$file" ]]; then
                    log_info "Exists: $filename (validation skipped)"
                else
                    log_warn "Empty file: $filename"
                fi
            fi
        fi
    done

    if [[ "$valid" == false ]]; then
        log_error "YAML validation failed. Please fix errors before deploying."
        exit 1
    fi
}

# Create backup of existing configs
backup_configs() {
    log_section "Creating Backup"

    local backup_dir="${HA_CONFIG_DIR}/backups/hydra-$(date +%Y%m%d-%H%M%S)"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would create backup at: $backup_dir"
        return
    fi

    ssh root@${HA_HOST} "mkdir -p '$backup_dir'"

    # Backup existing files
    local files_to_backup=(
        "automations.yaml"
        "configuration.yaml"
        "shell_commands.yaml"
        "lovelace-dashboards.yaml"
    )

    for file in "${files_to_backup[@]}"; do
        if ssh root@${HA_HOST} "[[ -f '${HA_CONFIG_DIR}/$file' ]]"; then
            ssh root@${HA_HOST} "cp '${HA_CONFIG_DIR}/$file' '$backup_dir/'"
            log_info "Backed up: $file"
        fi
    done

    log_info "Backup created at: $backup_dir"
}

# Deploy configuration files
deploy_configs() {
    log_section "Deploying Configuration Files"

    # Files to deploy
    local deploy_files=(
        "automations.yaml:automations.yaml"
        "shell_commands.yaml:shell_commands.yaml"
        "lovelace-dashboard.yaml:lovelace-dashboards.yaml"
    )

    for mapping in "${deploy_files[@]}"; do
        local source_file="${mapping%%:*}"
        local dest_file="${mapping##*:}"

        if [[ -f "$LOCAL_CONFIG_DIR/$source_file" ]]; then
            if $DRY_RUN; then
                log_info "[DRY RUN] Would deploy: $source_file -> $dest_file"
            else
                scp "$LOCAL_CONFIG_DIR/$source_file" "root@${HA_HOST}:${HA_CONFIG_DIR}/$dest_file"
                log_info "Deployed: $source_file -> $dest_file"
            fi
        else
            log_warn "Source file not found: $source_file"
        fi
    done

    # Handle configuration.yaml specially - merge rather than replace
    if [[ -f "$LOCAL_CONFIG_DIR/configuration.yaml" ]]; then
        log_info "configuration.yaml requires manual merge"
        log_info "Please add the following to your Home Assistant configuration.yaml:"
        echo ""
        echo "  # Hydra Cluster Integration"
        echo "  shell_command: !include shell_commands.yaml"
        echo "  automation: !include automations.yaml"
        echo ""
    fi
}

# Restart Home Assistant
restart_ha() {
    log_section "Restarting Home Assistant"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would restart Home Assistant"
        return
    fi

    # Try API restart first
    local ha_token="${HA_LONG_LIVED_TOKEN:-}"
    if [[ -n "$ha_token" ]]; then
        log_info "Restarting via API..."
        curl -sf -X POST \
            -H "Authorization: Bearer $ha_token" \
            "http://${HA_HOST}:${HA_PORT}/api/services/homeassistant/restart" || {
            log_warn "API restart failed, trying Docker restart..."
            ssh root@${HA_HOST} "docker restart homeassistant"
        }
    else
        log_info "Restarting via Docker..."
        ssh root@${HA_HOST} "docker restart homeassistant"
    fi

    log_info "Waiting for Home Assistant to restart..."
    sleep 30

    # Wait for HA to come back up
    local attempts=0
    while [[ $attempts -lt 12 ]]; do
        if curl -sf "http://${HA_HOST}:${HA_PORT}/api/" &>/dev/null; then
            log_info "Home Assistant is back online"
            return 0
        fi
        ((attempts++))
        sleep 10
    done

    log_error "Home Assistant did not come back online within 2 minutes"
    return 1
}

# Verify deployment
verify_deployment() {
    log_section "Verifying Deployment"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would verify deployment"
        return
    fi

    # Check HA health
    local health_response
    health_response=$(curl -sf "http://${HA_HOST}:${HA_PORT}/api/" 2>/dev/null || echo "")

    if [[ -n "$health_response" ]]; then
        log_info "Home Assistant API responding"
    else
        log_warn "Home Assistant API not responding"
    fi

    # Check if shell commands are loaded (requires auth)
    local ha_token="${HA_LONG_LIVED_TOKEN:-}"
    if [[ -n "$ha_token" ]]; then
        local services_response
        services_response=$(curl -sf \
            -H "Authorization: Bearer $ha_token" \
            "http://${HA_HOST}:${HA_PORT}/api/services" 2>/dev/null || echo "")

        if echo "$services_response" | grep -q "shell_command"; then
            log_info "Shell commands loaded successfully"
        else
            log_warn "Shell commands may not be loaded - check Home Assistant logs"
        fi
    else
        log_info "Set HA_LONG_LIVED_TOKEN to verify shell commands"
    fi

    log_info "Deployment verification complete"
}

# Main
main() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        Home Assistant Integration Deployment               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    validate_yaml
    backup_configs
    deploy_configs
    restart_ha
    verify_deployment

    log_section "Deployment Complete"

    if $DRY_RUN; then
        log_info "DRY RUN completed - no changes were made"
        log_info "Run without --dry-run to deploy"
    else
        log_info "Home Assistant integration deployed successfully"
        log_info ""
        log_info "Next steps:"
        log_info "  1. Open Home Assistant: http://${HA_HOST}:${HA_PORT}"
        log_info "  2. Check Configuration -> Server Controls -> Check Configuration"
        log_info "  3. Add Lovelace dashboard: Configuration -> Dashboards -> Add Dashboard"
        log_info "  4. Test automations and shell commands"
    fi
}

main "$@"
