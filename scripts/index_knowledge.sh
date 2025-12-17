#!/bin/bash
# Index all knowledge files to Qdrant

cd /mnt/user/appdata/hydra-dev

files=(
    "knowledge/automation.md:Automation"
    "knowledge/creative-stack.md:Creative Stack"
    "knowledge/databases.md:Databases"
    "knowledge/inference-stack.md:Inference Stack"
    "knowledge/infrastructure.md:Infrastructure"
    "knowledge/media-stack.md:Media Stack"
    "knowledge/models.md:Models"
    "knowledge/observability.md:Observability"
    "knowledge/troubleshooting.md:Troubleshooting"
)

for entry in "${files[@]}"; do
    file="${entry%%:*}"
    title="${entry##*:}"
    name=$(basename "$file" .md)

    if [ ! -f "$file" ]; then
        echo "File not found: $file"
        continue
    fi

    # Create JSON payload
    content=$(cat "$file" | jq -Rs '.')

    payload=$(jq -n \
        --arg content "$content" \
        --arg source "file://$file" \
        --arg title "$title" \
        --arg name "$name" \
        --arg filename "$(basename "$file")" \
        '{
          content: ($content | fromjson),
          source: $source,
          title: $title,
          doc_type: "documentation",
          tags: ["knowledge", "hydra", $name],
          metadata: {filename: $filename, category: "knowledge"}
        }')

    # Index the document
    result=$(echo "$payload" | curl -s -X POST \
        "http://192.168.1.244:8700/ingest/document?collection=hydra_knowledge&index=hydra_knowledge" \
        -H "Content-Type: application/json" \
        -d @-)

    chunks=$(echo "$result" | jq -r '.chunks // .detail // "error"')
    echo "Indexed: $title - $chunks chunks"
done

echo ""
echo "Verifying collection..."
curl -s http://192.168.1.244:6333/collections/hydra_knowledge | jq '{points_count: .result.points_count, vectors_count: .result.vectors_count}'
