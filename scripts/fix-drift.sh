#!/bin/bash
# Hydra Drift Fix Script
#
# Applies fixes for known drift issues identified in the reconciliation matrix.
#
# Usage:
#   ./fix-drift.sh check    - Check for drift issues
#   ./fix-drift.sh fix      - Apply fixes
#   ./fix-drift.sh verify   - Verify fixes were applied

set -euo pipefail

# Configuration
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo '.')}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Issue 1: Check for wrong Ollama IP
check_ollama_ip() {
    log_info "Checking for hardcoded Ollama IP 192.168.1.251..."

    local wrong_ip_count=0

    # Search for wrong IP in source files
    if grep -r "192\.168\.1\.251" "$REPO_ROOT" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" 2>/dev/null; then
        wrong_ip_count=$((wrong_ip_count + 1))
    fi

    if [[ $wrong_ip_count -gt 0 ]]; then
        log_warn "Found hardcoded IP 192.168.1.251 (should be 192.168.1.203)"
        return 1
    else
        log_success "No wrong Ollama IP found"
        return 0
    fi
}

fix_ollama_ip() {
    log_info "Fixing Ollama IP references..."

    # Find and replace in TypeScript/JavaScript files
    find "$REPO_ROOT" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" \) \
        -exec grep -l "192\.168\.1\.251" {} \; 2>/dev/null | while read -r file; do
        log_info "Fixing: $file"
        sed -i 's/192\.168\.1\.251/192.168.1.203/g' "$file"
    done

    log_success "Ollama IP references fixed"
}

# Issue 2: Check LiteLLM documentation
check_litellm_docs() {
    log_info "Checking LiteLLM location in documentation..."

    # Check if any doc incorrectly says LiteLLM is on hydra-ai
    if grep -r "hydra-ai.*LiteLLM\|LiteLLM.*hydra-ai" "$REPO_ROOT/docs" 2>/dev/null; then
        log_warn "Found incorrect LiteLLM location reference"
        return 1
    fi

    log_success "LiteLLM documentation correct"
    return 0
}

# Issue 3: Check alert rules for GPU metrics
check_alert_rules() {
    log_info "Checking Prometheus alert rules for GPU metric compatibility..."

    local issues=0

    # Check if rules only use DCGM metrics (not nvidia_smi)
    if [[ -f "$REPO_ROOT/config/prometheus/rules/hydra-alerts.yml" ]]; then
        if grep -q "DCGM_FI" "$REPO_ROOT/config/prometheus/rules/hydra-alerts.yml" && \
           ! grep -q "nvidia_smi" "$REPO_ROOT/config/prometheus/rules/hydra-alerts.yml"; then
            log_warn "Alert rules only use DCGM metrics, missing nvidia_smi support"
            issues=$((issues + 1))
        fi
    fi

    if [[ $issues -gt 0 ]]; then
        return 1
    fi

    log_success "Alert rules support both metric sources"
    return 0
}

# Issue 4: Check config consistency
check_config_consistency() {
    log_info "Checking configuration consistency..."

    local issues=0

    # Check for IP consistency in config files
    local hydra_ai_ip="192.168.1.250"
    local hydra_compute_ip="192.168.1.203"
    local hydra_storage_ip="192.168.1.244"

    # Find any references to old/wrong IPs
    if grep -r "192\.168\.1\.100" "$REPO_ROOT" --include="*.yml" --include="*.yaml" --include="*.json" 2>/dev/null; then
        log_warn "Found reference to old storage IP 192.168.1.100"
        issues=$((issues + 1))
    fi

    if [[ $issues -gt 0 ]]; then
        return 1
    fi

    log_success "Configuration IPs are consistent"
    return 0
}

# Check service reachability
check_services() {
    log_info "Checking service reachability..."

    local services=(
        "TabbyAPI:192.168.1.250:5000:/v1/model"
        "LiteLLM:192.168.1.244:4000:/health"
        "Ollama:192.168.1.203:11434:/api/tags"
        "Qdrant:192.168.1.244:6333:/health"
        "Prometheus:192.168.1.244:9090/-/healthy"
    )

    for service_info in "${services[@]}"; do
        IFS=: read -r name host port path <<< "$service_info"
        if curl -sf "http://$host:$port$path" >/dev/null 2>&1; then
            log_success "$name ($host:$port) - reachable"
        else
            log_warn "$name ($host:$port) - not reachable"
        fi
    done
}

# Main commands
cmd_check() {
    echo "=== Hydra Drift Check ==="
    echo

    local issues=0

    check_ollama_ip || issues=$((issues + 1))
    check_litellm_docs || issues=$((issues + 1))
    check_alert_rules || issues=$((issues + 1))
    check_config_consistency || issues=$((issues + 1))

    echo
    if [[ $issues -gt 0 ]]; then
        log_warn "Found $issues drift issue(s)"
        echo "Run '$0 fix' to apply fixes"
        return 1
    else
        log_success "No drift issues found"
        return 0
    fi
}

cmd_fix() {
    echo "=== Applying Drift Fixes ==="
    echo

    # Fix 1: Ollama IP
    fix_ollama_ip

    # Other fixes could be added here

    echo
    log_success "Fixes applied. Run '$0 verify' to confirm."
}

cmd_verify() {
    echo "=== Verifying Fixes ==="
    echo

    # Run all checks
    cmd_check

    echo
    echo "=== Service Reachability ==="
    echo
    check_services
}

cmd_help() {
    echo "Hydra Drift Fix Script"
    echo
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  check   - Check for drift issues (read-only)"
    echo "  fix     - Apply fixes for known issues"
    echo "  verify  - Verify fixes and check service reachability"
    echo
    echo "Known drift issues:"
    echo "  1. UI hardcodes wrong Ollama IP (251 -> 203)"
    echo "  2. Documentation may have incorrect service locations"
    echo "  3. Alert rules may not support all GPU metric sources"
    echo "  4. Old IP references in config files"
}

# Main
main() {
    local cmd="${1:-check}"

    case "$cmd" in
        check|c)
            cmd_check
            ;;
        fix|f)
            cmd_fix
            ;;
        verify|v)
            cmd_verify
            ;;
        help|-h|--help)
            cmd_help
            ;;
        *)
            log_error "Unknown command: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
