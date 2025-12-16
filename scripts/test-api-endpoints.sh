#!/bin/bash
# Test Hydra Tools API Endpoints
# Usage: ./scripts/test-api-endpoints.sh [--verbose]

set -euo pipefail

API_URL="${HYDRA_API_URL:-http://192.168.1.244:8700}"
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose) VERBOSE=true; shift ;;
        -h|--help)
            echo "Usage: $0 [-v|--verbose] [-h|--help]"
            echo "Tests all Hydra Tools API endpoints"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

log() { echo -e "${BLUE}[TEST]${NC} $1"; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASSED++)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAILED++)); }
skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; ((SKIPPED++)); }

test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="${4:-}"

    local url="${API_URL}${endpoint}"
    local response
    local status

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\n000")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo -e "\n000")
    fi

    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$status" -ge 200 ] && [ "$status" -lt 300 ]; then
        pass "$description ($method $endpoint) - HTTP $status"
        if [ "$VERBOSE" = true ] && [ -n "$body" ]; then
            echo "    Response: $(echo "$body" | head -c 200)..."
        fi
    elif [ "$status" = "000" ]; then
        fail "$description ($method $endpoint) - Connection failed"
    else
        fail "$description ($method $endpoint) - HTTP $status"
        if [ "$VERBOSE" = true ]; then
            echo "    Response: $body"
        fi
    fi
}

echo ""
echo "=========================================="
echo "  Hydra Tools API Endpoint Tests"
echo "  Target: $API_URL"
echo "=========================================="
echo ""

# Core Endpoints
log "Testing Core Endpoints..."
test_endpoint "GET" "/" "Root endpoint"
test_endpoint "GET" "/health" "Health check"
test_endpoint "GET" "/docs" "API documentation"

# Diagnosis Endpoints
log "Testing Diagnosis Endpoints..."
test_endpoint "GET" "/diagnosis" "System diagnosis"

# Optimization Endpoints
log "Testing Optimization Endpoints..."
test_endpoint "GET" "/optimization" "Optimization status"

# Knowledge Endpoints
log "Testing Knowledge Endpoints..."
test_endpoint "GET" "/knowledge" "Knowledge base stats"

# Capabilities Endpoints
log "Testing Capabilities Endpoints..."
test_endpoint "GET" "/capabilities" "System capabilities"

# Routing Endpoints
log "Testing Routing Endpoints..."
test_endpoint "GET" "/routing/models" "Available models"
test_endpoint "POST" "/routing/classify" "Classify prompt" '{"prompt": "Hello, world!"}'

# Preferences Endpoints
log "Testing Preferences Endpoints..."
test_endpoint "GET" "/preferences/stats" "Preference stats"

# Activity Endpoints
log "Testing Activity Endpoints..."
test_endpoint "GET" "/activity/recent" "Recent activities"
test_endpoint "GET" "/activity/pending" "Pending approvals"

# Control Endpoints
log "Testing Control Endpoints..."
test_endpoint "GET" "/control/status" "Control status"

# Hardware Endpoints
log "Testing Hardware Endpoints..."
test_endpoint "GET" "/hardware/status" "Hardware status"

# Scheduler Endpoints
log "Testing Scheduler Endpoints..."
test_endpoint "GET" "/scheduler/status" "Scheduler status"

# Letta Bridge Endpoints
log "Testing Letta Bridge Endpoints..."
test_endpoint "GET" "/letta-bridge/models" "Letta models"

# Search Endpoints (v1.3.0+)
log "Testing Search Endpoints..."
test_endpoint "POST" "/search/query" "Hybrid search" '{"query": "test", "limit": 5}'
test_endpoint "POST" "/search/semantic" "Semantic search" '{"query": "test", "limit": 5}'

# Ingest Endpoints (v1.3.0+)
log "Testing Ingest Endpoints..."
test_endpoint "GET" "/ingest/status" "Ingest status"

# Research Endpoints (v1.3.0+)
log "Testing Research Endpoints..."
test_endpoint "POST" "/research/web" "Web search" '{"query": "AI news", "num_results": 3}'

# Crews Endpoints (v1.4.0+)
log "Testing Crews Endpoints..."
test_endpoint "GET" "/crews/list" "List crews"
test_endpoint "GET" "/crews/status" "Crews status"

# Alerts Endpoints (v1.4.0+)
log "Testing Alerts Endpoints..."
test_endpoint "GET" "/alerts/status" "Alerts status"
test_endpoint "GET" "/alerts/channels" "Alert channels"

# Cluster Health Endpoints (v1.4.0+)
log "Testing Cluster Health Endpoints..."
test_endpoint "GET" "/health/cluster" "Cluster health"
test_endpoint "GET" "/health/summary" "Health summary"
test_endpoint "GET" "/health/nodes" "Nodes health"
test_endpoint "GET" "/health/categories" "Categories health"
test_endpoint "GET" "/health/gpu" "GPU health"

# Voice Endpoints (v1.4.0+)
log "Testing Voice Endpoints..."
test_endpoint "GET" "/voice/status" "Voice pipeline status"
test_endpoint "GET" "/voice/settings" "Voice settings"
test_endpoint "GET" "/voice/voices" "Available voices"

# Reconcile Endpoints (v1.4.0+)
log "Testing Reconcile Endpoints..."
test_endpoint "GET" "/reconcile/state" "Cluster state"
test_endpoint "GET" "/reconcile/drift" "Detect drift"
test_endpoint "GET" "/reconcile/desired" "Desired state"

echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "  ${GREEN}Passed:${NC}  $PASSED"
echo -e "  ${RED}Failed:${NC}  $FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $SKIPPED"
echo "  Total:   $((PASSED + FAILED + SKIPPED))"
echo "=========================================="

if [ "$FAILED" -gt 0 ]; then
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
fi
