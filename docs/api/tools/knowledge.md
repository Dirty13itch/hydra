# Knowledge Tools

Tools for semantic search and knowledge retrieval from Qdrant and Meilisearch.

## query_knowledge

Semantic search using Qdrant vector database.

```python
from hydra_tools.knowledge import query_knowledge

# Basic search
results = query_knowledge("How does the inference pipeline work?")

# With parameters
results = query_knowledge(
    query="GPU configuration",
    collection="hydra_docs",
    limit=10,
    score_threshold=0.8
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | required | Search query |
| `collection` | str | `"hydra_docs"` | Qdrant collection name |
| `limit` | int | 5 | Maximum results |
| `score_threshold` | float | 0.7 | Minimum similarity score |

### Collections

| Collection | Description |
|------------|-------------|
| `hydra_docs` | Cluster documentation |
| `knowledge_base` | General knowledge |
| `code_snippets` | Code examples |

## keyword_search

Full-text search using Meilisearch.

```python
from hydra_tools.knowledge import keyword_search

# Basic search
results = keyword_search("docker compose")

# With filters
results = keyword_search(
    query="TabbyAPI config",
    index="hydra_docs",
    limit=20,
    filter="category = 'inference'"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | required | Search query |
| `index` | str | `"hydra_docs"` | Meilisearch index |
| `limit` | int | 10 | Maximum results |
| `filter` | str | None | Meilisearch filter expression |

## hybrid_search

Combined semantic and keyword search with reciprocal rank fusion.

```python
from hydra_tools.knowledge import hybrid_search

# Basic hybrid search
results = hybrid_search("GPU power management")

# With weights
results = hybrid_search(
    query="NixOS module configuration",
    collection="hydra_docs",
    index="hydra_docs",
    limit=10,
    semantic_weight=0.7  # 70% semantic, 30% keyword
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | required | Search query |
| `collection` | str | `"hydra_docs"` | Qdrant collection |
| `index` | str | `"hydra_docs"` | Meilisearch index |
| `limit` | int | 5 | Maximum results |
| `semantic_weight` | float | 0.7 | Weight for semantic results (0-1) |

### How It Works

1. Query is embedded using Ollama's nomic-embed-text
2. Parallel search: Qdrant (semantic) + Meilisearch (keyword)
3. Results combined using Reciprocal Rank Fusion (RRF)
4. Deduplicated and sorted by combined score

## get_document

Retrieve a specific document by ID.

```python
from hydra_tools.knowledge import get_document

doc = get_document(
    doc_id="doc_12345",
    collection="hydra_docs"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `doc_id` | str | required | Document ID |
| `collection` | str | `"hydra_docs"` | Collection name |

## Response Format

All search functions return JSON with this structure:

```json
{
  "results": [
    {
      "id": "doc_123",
      "content": "Document text...",
      "score": 0.95,
      "metadata": {
        "source": "docs/inference.md",
        "category": "inference"
      }
    }
  ],
  "query": "original query",
  "total": 5
}
```

## Error Handling

```python
from hydra_tools import ToolError

try:
    results = query_knowledge("test query")
except ToolError as e:
    if "connection" in str(e).lower():
        print("Qdrant unavailable")
    else:
        raise
```

## Best Practices

1. **Use hybrid search for best results** - Combines semantic understanding with exact matching
2. **Adjust score threshold** - Lower for recall, higher for precision
3. **Use filters when possible** - Reduces search space
4. **Cache frequent queries** - Results are deterministic for same query
