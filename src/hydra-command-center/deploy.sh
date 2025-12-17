#!/bin/bash
# Hydra Command Center Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Hydra Command Center ==="

# Check if hydra-apps network exists
if ! docker network inspect hydra-apps >/dev/null 2>&1; then
    echo "Creating hydra-apps network..."
    docker network create hydra-apps
fi

# Build and start the container
echo "Building and starting container..."
docker-compose up -d --build

echo ""
echo "=== Deployment Complete ==="
echo "Command Center available at: http://192.168.1.244:3100"
echo ""
docker-compose ps
