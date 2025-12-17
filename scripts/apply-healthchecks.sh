#!/bin/bash
# Apply Healthchecks to Containers
#
# This script recreates containers with healthchecks.
# Run with caution - it will restart containers.
#
# Usage: ./apply-healthchecks.sh [container-name]
#        ./apply-healthchecks.sh --all

set -e

apply_healthcheck() {
    local container=$1
    local healthcheck=$2
    local interval=${3:-30s}
    local timeout=${4:-10s}
    local retries=${5:-3}
    local start_period=${6:-60s}

    echo "Applying healthcheck to $container..."

    # Get current container config
    local image=$(docker inspect --format='{{.Config.Image}}' $container 2>/dev/null)
    if [ -z "$image" ]; then
        echo "  Container $container not found, skipping"
        return
    fi

    # Check if already has healthcheck
    local current=$(docker inspect --format='{{if .State.Health}}yes{{else}}no{{end}}' $container 2>/dev/null)
    if [ "$current" = "yes" ]; then
        echo "  $container already has healthcheck, skipping"
        return
    fi

    echo "  Image: $image"
    echo "  Healthcheck: $healthcheck"
    echo "  To apply, add to container template or recreate container"
    echo ""
}

# Define healthchecks for each container
declare -A HEALTHCHECKS=(
    ["hydra-litellm"]="curl -sf http://localhost:4000/health || exit 1"
    ["hydra-n8n"]="wget -q --spider http://localhost:5678/healthz || exit 1"
    ["hydra-prometheus"]="wget -q --spider http://localhost:9090/-/healthy || exit 1"
    ["hydra-grafana"]="wget -q --spider http://localhost:3000/api/health || exit 1"
    ["hydra-promtail"]="wget -q --spider http://localhost:9080/ready || exit 1"
    ["hydra-loki"]="wget -q --spider http://localhost:3100/ready || exit 1"
    ["hydra-miniflux"]="wget -q --spider http://localhost:8080/healthcheck || exit 1"
    ["hydra-control-plane-ui"]="wget -q --spider http://localhost:3200 || exit 1"
    ["adguard"]="wget -q --spider http://localhost:3000 || exit 1"
    ["gpu-metrics-api"]="wget -q --spider http://localhost:8000/health || exit 1"
    ["wyoming-openwakeword"]="nc -z localhost 10400 || exit 1"
    ["hydra-neo4j"]="wget -q --spider http://localhost:7474 || exit 1"
)

if [ "$1" = "--all" ]; then
    echo "=== Healthcheck Status Report ==="
    echo ""
    for container in "${!HEALTHCHECKS[@]}"; do
        apply_healthcheck "$container" "${HEALTHCHECKS[$container]}"
    done
elif [ -n "$1" ]; then
    if [ -n "${HEALTHCHECKS[$1]}" ]; then
        apply_healthcheck "$1" "${HEALTHCHECKS[$1]}"
    else
        echo "Unknown container: $1"
        echo "Available containers:"
        for c in "${!HEALTHCHECKS[@]}"; do echo "  - $c"; done
    fi
else
    echo "Usage: $0 [container-name | --all]"
    echo ""
    echo "Available containers:"
    for c in "${!HEALTHCHECKS[@]}"; do echo "  - $c"; done
fi
