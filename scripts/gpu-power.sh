#!/bin/bash
# Hydra GPU Power Management Script
#
# Manages GPU power limits and monitoring for the Hydra cluster.
# Critical for staying within 2000W UPS budget.
#
# Usage:
#   ./gpu-power.sh status        - Show current power status
#   ./gpu-power.sh set <node> <watts> - Set power limit
#   ./gpu-power.sh profile <name> - Apply power profile
#   ./gpu-power.sh monitor       - Continuous monitoring

set -euo pipefail

# Configuration
HYDRA_AI_HOST="192.168.1.250"
HYDRA_COMPUTE_HOST="192.168.1.203"

# Power limits (watts)
# RTX 5090: Default TDP 575W, we limit to 450W for efficiency
# RTX 4090: Default TDP 450W, we limit to 300W for efficiency
# RTX 5070 Ti: Default TDP 300W, we limit to 250W
# RTX 3060: Default TDP 170W

declare -A GPU_DEFAULTS=(
    ["5090"]=575
    ["4090"]=450
    ["5070"]=300
    ["3060"]=170
)

declare -A GPU_LIMITS=(
    ["5090"]=450
    ["4090"]=300
    ["5070"]=250
    ["3060"]=150
)

# Power profiles
declare -A PROFILE_IDLE=(
    ["hydra-ai-0"]=200   # 5090 idle
    ["hydra-ai-1"]=150   # 4090 idle
    ["hydra-compute-0"]=100  # 5070 Ti idle
    ["hydra-compute-1"]=80   # 3060 idle
)

declare -A PROFILE_NORMAL=(
    ["hydra-ai-0"]=450   # 5090 inference
    ["hydra-ai-1"]=300   # 4090 inference
    ["hydra-compute-0"]=250  # 5070 Ti
    ["hydra-compute-1"]=150  # 3060
)

declare -A PROFILE_MAX=(
    ["hydra-ai-0"]=575   # 5090 max
    ["hydra-ai-1"]=450   # 4090 max
    ["hydra-compute-0"]=300  # 5070 Ti max
    ["hydra-compute-1"]=170  # 3060 max
)

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

# Get GPU info from a node
get_gpu_info() {
    local host="$1"
    local user="${2:-typhon}"

    ssh -o ConnectTimeout=5 "$user@$host" \
        "nvidia-smi --query-gpu=index,name,power.draw,power.limit,temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits" 2>/dev/null
}

# Set power limit on a GPU
set_power_limit() {
    local host="$1"
    local gpu_index="$2"
    local watts="$3"
    local user="${4:-typhon}"

    log_info "Setting GPU $gpu_index on $host to ${watts}W"
    ssh "$user@$host" "sudo nvidia-smi -i $gpu_index -pl $watts" 2>/dev/null
}

# Show current status
cmd_status() {
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                    HYDRA GPU POWER STATUS                            ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo

    local total_power=0
    local total_limit=0

    # hydra-ai
    echo -e "${CYAN}▶ hydra-ai ($HYDRA_AI_HOST)${NC}"
    echo "  ┌────────────────────────────────────────────────────────────────────┐"
    if info=$(get_gpu_info "$HYDRA_AI_HOST"); then
        while IFS=, read -r idx name power limit temp mem_used mem_total util; do
            # Trim whitespace
            idx=$(echo "$idx" | xargs)
            name=$(echo "$name" | xargs)
            power=$(echo "$power" | xargs)
            limit=$(echo "$limit" | xargs)
            temp=$(echo "$temp" | xargs)
            mem_used=$(echo "$mem_used" | xargs)
            mem_total=$(echo "$mem_total" | xargs)
            util=$(echo "$util" | xargs)

            total_power=$((total_power + ${power%.*}))
            total_limit=$((total_limit + ${limit%.*}))

            # Color code power usage
            power_int=${power%.*}
            limit_int=${limit%.*}
            pct=$((power_int * 100 / limit_int))

            if [[ $pct -gt 90 ]]; then
                power_color=$RED
            elif [[ $pct -gt 70 ]]; then
                power_color=$YELLOW
            else
                power_color=$GREEN
            fi

            printf "  │ GPU %s: %-25s                                       │\n" "$idx" "$name"
            printf "  │   Power: ${power_color}%6.1fW${NC} / %6.1fW (%2d%%)  Temp: %3d°C  Util: %3d%%          │\n" \
                "$power" "$limit" "$pct" "$temp" "$util"
            printf "  │   VRAM:  %5dMB / %5dMB                                        │\n" "$mem_used" "$mem_total"
        done <<< "$info"
    else
        echo "  │ (unreachable)                                                      │"
    fi
    echo "  └────────────────────────────────────────────────────────────────────┘"
    echo

    # hydra-compute
    echo -e "${CYAN}▶ hydra-compute ($HYDRA_COMPUTE_HOST)${NC}"
    echo "  ┌────────────────────────────────────────────────────────────────────┐"
    if info=$(get_gpu_info "$HYDRA_COMPUTE_HOST"); then
        while IFS=, read -r idx name power limit temp mem_used mem_total util; do
            idx=$(echo "$idx" | xargs)
            name=$(echo "$name" | xargs)
            power=$(echo "$power" | xargs)
            limit=$(echo "$limit" | xargs)
            temp=$(echo "$temp" | xargs)
            mem_used=$(echo "$mem_used" | xargs)
            mem_total=$(echo "$mem_total" | xargs)
            util=$(echo "$util" | xargs)

            total_power=$((total_power + ${power%.*}))
            total_limit=$((total_limit + ${limit%.*}))

            power_int=${power%.*}
            limit_int=${limit%.*}
            pct=$((power_int * 100 / limit_int))

            if [[ $pct -gt 90 ]]; then
                power_color=$RED
            elif [[ $pct -gt 70 ]]; then
                power_color=$YELLOW
            else
                power_color=$GREEN
            fi

            printf "  │ GPU %s: %-25s                                       │\n" "$idx" "$name"
            printf "  │   Power: ${power_color}%6.1fW${NC} / %6.1fW (%2d%%)  Temp: %3d°C  Util: %3d%%          │\n" \
                "$power" "$limit" "$pct" "$temp" "$util"
            printf "  │   VRAM:  %5dMB / %5dMB                                        │\n" "$mem_used" "$mem_total"
        done <<< "$info"
    else
        echo "  │ (unreachable)                                                      │"
    fi
    echo "  └────────────────────────────────────────────────────────────────────┘"
    echo

    # Summary
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    printf "║  TOTAL GPU POWER: %4dW / %4dW configured                          ║\n" "$total_power" "$total_limit"
    printf "║  UPS HEADROOM:    %4dW remaining (2000W capacity)                  ║\n" "$((2000 - total_power))"
    echo "╚══════════════════════════════════════════════════════════════════════╝"

    if [[ $total_power -gt 1600 ]]; then
        log_warn "Power usage above 80% of UPS capacity!"
    fi
}

# Set power limit
cmd_set() {
    local target="$1"
    local watts="$2"

    if [[ -z "$target" || -z "$watts" ]]; then
        echo "Usage: $0 set <target> <watts>"
        echo "Target: hydra-ai-0, hydra-ai-1, hydra-compute-0, hydra-compute-1, or node name"
        exit 1
    fi

    case "$target" in
        hydra-ai-0|ai-0)
            set_power_limit "$HYDRA_AI_HOST" 0 "$watts"
            ;;
        hydra-ai-1|ai-1)
            set_power_limit "$HYDRA_AI_HOST" 1 "$watts"
            ;;
        hydra-ai|ai)
            set_power_limit "$HYDRA_AI_HOST" 0 "$watts"
            set_power_limit "$HYDRA_AI_HOST" 1 "$watts"
            ;;
        hydra-compute-0|compute-0)
            set_power_limit "$HYDRA_COMPUTE_HOST" 0 "$watts"
            ;;
        hydra-compute-1|compute-1)
            set_power_limit "$HYDRA_COMPUTE_HOST" 1 "$watts"
            ;;
        hydra-compute|compute)
            set_power_limit "$HYDRA_COMPUTE_HOST" 0 "$watts"
            set_power_limit "$HYDRA_COMPUTE_HOST" 1 "$watts"
            ;;
        *)
            log_error "Unknown target: $target"
            exit 1
            ;;
    esac

    log_success "Power limit set"
}

# Apply power profile
cmd_profile() {
    local profile="$1"

    case "$profile" in
        idle)
            log_info "Applying IDLE power profile"
            for key in "${!PROFILE_IDLE[@]}"; do
                cmd_set "$key" "${PROFILE_IDLE[$key]}"
            done
            ;;
        normal|default)
            log_info "Applying NORMAL power profile"
            for key in "${!PROFILE_NORMAL[@]}"; do
                cmd_set "$key" "${PROFILE_NORMAL[$key]}"
            done
            ;;
        max|full)
            log_warn "Applying MAX power profile - ensure adequate cooling!"
            for key in "${!PROFILE_MAX[@]}"; do
                cmd_set "$key" "${PROFILE_MAX[$key]}"
            done
            ;;
        *)
            echo "Available profiles:"
            echo "  idle   - Minimum power for idle/light workloads (~530W total)"
            echo "  normal - Standard inference workloads (~1150W total)"
            echo "  max    - Maximum performance (~1495W total)"
            exit 1
            ;;
    esac

    log_success "Profile applied"
}

# Continuous monitoring
cmd_monitor() {
    local interval="${1:-5}"

    log_info "Starting continuous monitoring (Ctrl+C to stop)"
    echo

    while true; do
        clear
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Refreshing every ${interval}s"
        echo
        cmd_status
        sleep "$interval"
    done
}

# Temperature monitoring with alerts
cmd_temps() {
    echo "GPU Temperatures:"
    echo

    # hydra-ai
    echo "hydra-ai:"
    if info=$(ssh -o ConnectTimeout=5 typhon@$HYDRA_AI_HOST \
        "nvidia-smi --query-gpu=index,name,temperature.gpu --format=csv,noheader" 2>/dev/null); then
        while IFS=, read -r idx name temp; do
            temp=$(echo "$temp" | xargs)
            if [[ $temp -gt 85 ]]; then
                echo -e "  GPU $idx: ${RED}${temp}°C${NC} (CRITICAL!)"
            elif [[ $temp -gt 75 ]]; then
                echo -e "  GPU $idx: ${YELLOW}${temp}°C${NC} (warm)"
            else
                echo -e "  GPU $idx: ${GREEN}${temp}°C${NC}"
            fi
        done <<< "$info"
    fi

    echo
    echo "hydra-compute:"
    if info=$(ssh -o ConnectTimeout=5 typhon@$HYDRA_COMPUTE_HOST \
        "nvidia-smi --query-gpu=index,name,temperature.gpu --format=csv,noheader" 2>/dev/null); then
        while IFS=, read -r idx name temp; do
            temp=$(echo "$temp" | xargs)
            if [[ $temp -gt 85 ]]; then
                echo -e "  GPU $idx: ${RED}${temp}°C${NC} (CRITICAL!)"
            elif [[ $temp -gt 75 ]]; then
                echo -e "  GPU $idx: ${YELLOW}${temp}°C${NC} (warm)"
            else
                echo -e "  GPU $idx: ${GREEN}${temp}°C${NC}"
            fi
        done <<< "$info"
    fi
}

# Main
main() {
    local cmd="${1:-status}"
    shift || true

    case "$cmd" in
        status|st)
            cmd_status
            ;;
        set)
            cmd_set "$@"
            ;;
        profile|p)
            cmd_profile "$@"
            ;;
        monitor|mon)
            cmd_monitor "$@"
            ;;
        temps|temp|t)
            cmd_temps
            ;;
        help|-h|--help)
            echo "Hydra GPU Power Manager"
            echo
            echo "Usage: $0 <command> [args]"
            echo
            echo "Commands:"
            echo "  status          Show current GPU power status"
            echo "  set <gpu> <W>   Set power limit for a GPU"
            echo "  profile <name>  Apply power profile (idle, normal, max)"
            echo "  monitor [sec]   Continuous monitoring (default: 5s)"
            echo "  temps           Show GPU temperatures"
            echo
            echo "GPU Targets:"
            echo "  hydra-ai-0     RTX 5090 (32GB)"
            echo "  hydra-ai-1     RTX 4090 (24GB)"
            echo "  hydra-compute-0 RTX 5070 Ti (16GB)"
            echo "  hydra-compute-1 RTX 3060 (12GB)"
            echo
            echo "Power Profiles:"
            echo "  idle   - 200/150/100/80W  (~530W total)"
            echo "  normal - 450/300/250/150W (~1150W total)"
            echo "  max    - 575/450/300/170W (~1495W total)"
            echo
            echo "Examples:"
            echo "  $0 status"
            echo "  $0 set ai-0 400"
            echo "  $0 profile normal"
            echo "  $0 monitor 10"
            ;;
        *)
            log_error "Unknown command: $cmd"
            main help
            exit 1
            ;;
    esac
}

main "$@"
