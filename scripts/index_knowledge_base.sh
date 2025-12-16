#!/bin/bash
# Knowledge Base Indexer (Bash version)
#
# Indexes all knowledge/*.md files to the Hydra knowledge base.
# Uses the /ingest/document endpoint on the Hydra Tools API.
#
# Usage:
#   ./scripts/index_knowledge_base.sh
#   ./scripts/index_knowledge_base.sh --dry-run
#   ./scripts/index_knowledge_base.sh --file knowledge/automation.md

set -e

HYDRA_API_URL="http://192.168.1.244:8700"
KNOWLEDGE_DIR="$(dirname "$0")/../knowledge"
COLLECTION="hydra_knowledge"
DRY_RUN=false
SPECIFIC_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --file)
            SPECIFIC_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================================"
echo "Hydra Knowledge Base Indexer"
echo "============================================================"

# Check API health
check_api() {
    echo "Checking API health..."
    HEALTH=$(curl -s --connect-timeout 5 "$HYDRA_API_URL/health" 2>/dev/null || echo '{"status":"error"}')
    STATUS=$(echo "$HEALTH" | jq -r '.status // "error"')
    VERSION=$(echo "$HEALTH" | jq -r '.version // "unknown"')

    if [ "$STATUS" != "healthy" ]; then
        echo "[ERROR] API not healthy: $STATUS"
        return 1
    fi

    echo "API Status: $STATUS"
    echo "API Version: $VERSION"

    # Check for ingest endpoint
    ROOT=$(curl -s --connect-timeout 5 "$HYDRA_API_URL/" 2>/dev/null)
    if ! echo "$ROOT" | jq -e '.endpoints.ingest' > /dev/null 2>&1; then
        echo "[WARNING] /ingest endpoint not found - API may need restart for v1.3.0"
        return 1
    fi

    return 0
}

# Get tags for a file
get_tags() {
    local filename="$1"
    local name=$(basename "$filename" .md | tr '[:upper:]' '[:lower:]')

    case "$name" in
        automation) echo '["automation", "n8n", "agents", "crewai", "knowledge-base"]' ;;
        creative-stack) echo '["creative", "comfyui", "media", "generation", "knowledge-base"]' ;;
        databases) echo '["databases", "postgresql", "qdrant", "redis", "knowledge-base"]' ;;
        inference-stack) echo '["inference", "tabbyapi", "ollama", "litellm", "knowledge-base"]' ;;
        infrastructure) echo '["infrastructure", "hardware", "network", "nodes", "knowledge-base"]' ;;
        media-stack) echo '["media", "jellyfin", "tts", "streaming", "knowledge-base"]' ;;
        models) echo '["models", "llm", "exllama", "quantization", "knowledge-base"]' ;;
        observability) echo '["observability", "prometheus", "grafana", "monitoring", "knowledge-base"]' ;;
        troubleshooting) echo '["troubleshooting", "debugging", "fixes", "knowledge-base"]' ;;
        *) echo '["knowledge", "documentation", "knowledge-base"]' ;;
    esac
}

# Get title for a file
get_title() {
    local filename="$1"
    local name=$(basename "$filename" .md)
    # Convert kebab-case to Title Case
    echo "Knowledge: $(echo "$name" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')"
}

# Index a single file
index_file() {
    local filepath="$1"
    local filename=$(basename "$filepath")
    local title=$(get_title "$filepath")
    local tags=$(get_tags "$filepath")
    local content

    # Read content and escape for JSON
    content=$(cat "$filepath" | jq -Rs .)

    echo "Processing: $filename"
    echo "  Title: $title"
    echo "  Tags: $tags"
    echo "  Content length: $(wc -c < "$filepath") bytes"

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Would index this file"
        return 0
    fi

    # Build JSON payload
    PAYLOAD=$(cat <<EOF
{
    "content": $content,
    "title": "$title",
    "source": "file://$filepath",
    "doc_type": "knowledge-document",
    "tags": $tags,
    "collection": "$COLLECTION"
}
EOF
)

    # Send to API
    RESPONSE=$(curl -s -X POST "$HYDRA_API_URL/ingest/document" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --connect-timeout 30 \
        --max-time 120 2>&1)

    # Check response
    if echo "$RESPONSE" | jq -e '.document_id' > /dev/null 2>&1; then
        local doc_id=$(echo "$RESPONSE" | jq -r '.document_id')
        local chunks=$(echo "$RESPONSE" | jq -r '.chunks // "N/A"')
        echo "  [OK] Indexed - ID: $doc_id, Chunks: $chunks"
        return 0
    else
        local error=$(echo "$RESPONSE" | jq -r '.error // .detail // "Unknown error"')
        echo "  [ERROR] $error"
        return 1
    fi
}

# Main logic
if [ "$DRY_RUN" = false ]; then
    if ! check_api; then
        echo ""
        echo "[ERROR] API not ready. Use --dry-run to preview."
        exit 1
    fi
fi

echo ""

# Determine files to process
if [ -n "$SPECIFIC_FILE" ]; then
    if [ ! -f "$SPECIFIC_FILE" ]; then
        echo "[ERROR] File not found: $SPECIFIC_FILE"
        exit 1
    fi
    FILES=("$SPECIFIC_FILE")
else
    FILES=("$KNOWLEDGE_DIR"/*.md)
fi

SUCCESS=0
ERRORS=0

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        if index_file "$file"; then
            ((SUCCESS++)) || true
        else
            ((ERRORS++)) || true
        fi
        echo ""
    fi
done

# Summary
echo "============================================================"
echo "Summary"
echo "============================================================"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run completed: ${#FILES[@]} file(s) would be indexed"
else
    echo "Indexed: $SUCCESS file(s)"
    [ "$ERRORS" -gt 0 ] && echo "Errors: $ERRORS file(s)"
fi
