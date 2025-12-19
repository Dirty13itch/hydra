#!/bin/bash
# ComfyUI Quality Scoring Callback
# Call this after image generation to auto-score and queue for review
#
# Usage: comfyui-quality-callback.sh /path/to/generated/image.png [character_name]

IMAGE_PATH="$1"
CHARACTER_NAME="${2:-}"
API_URL="http://192.168.1.244:8700/quality/auto-score"

if [ -z "$IMAGE_PATH" ]; then
    echo "Usage: $0 <image_path> [character_name]"
    exit 1
fi

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image not found: $IMAGE_PATH"
    exit 1
fi

# Call the auto-score API
RESPONSE=$(curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{
        \"image_path\": \"$IMAGE_PATH\",
        \"character_name\": \"$CHARACTER_NAME\",
        \"model_used\": \"ComfyUI-NoobAI-XL\"
    }")

# Parse response
SCORE=$(echo "$RESPONSE" | jq -r '.overall_score // "N/A"')
TIER=$(echo "$RESPONSE" | jq -r '.tier // "unknown"')
ACTION=$(echo "$RESPONSE" | jq -r '.action // "error"')
ASSET_ID=$(echo "$RESPONSE" | jq -r '.asset_id // ""')

echo "=== Quality Score Result ==="
echo "Image: $IMAGE_PATH"
echo "Score: $SCORE"
echo "Tier: $TIER"
echo "Action: $ACTION"
echo "Asset ID: $ASSET_ID"

# Return appropriate exit code
if [ "$ACTION" = "approve" ]; then
    echo "✓ Auto-approved"
    exit 0
elif [ "$ACTION" = "review" ]; then
    echo "⚠ Needs human review - check Command Center Feedback tab"
    exit 0
elif [ "$ACTION" = "reject" ]; then
    echo "✗ Auto-rejected - consider regenerating"
    exit 1
else
    echo "Error processing image"
    exit 2
fi
