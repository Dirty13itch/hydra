# Hydra Cluster API Reference

This documentation covers the Python libraries and tools for the Hydra AI cluster.

## Libraries

### hydra_tools

Agent tools for LangChain/LangGraph integration with cluster services.

- [Inference Tools](tools/inference.md) - Chat completion, image generation
- [Knowledge Tools](tools/knowledge.md) - Semantic and hybrid search
- [Storage Tools](tools/storage.md) - File operations
- [Cluster Tools](tools/cluster.md) - SSH execution, status

### hydra_search

Hybrid search library combining vector (Qdrant) and keyword (Meilisearch) search.

- [Configuration](search/config.md) - Setup and configuration
- [Indexing](search/indexing.md) - Document ingestion
- [Searching](search/searching.md) - Query execution

### hydra_health

Unified health aggregation API for all cluster services.

- [Endpoints](health/endpoints.md) - API reference
- [Checks](health/checks.md) - Service definitions

### hydra_cli

Command-line interface for cluster management.

- [Commands](cli/commands.md) - Available commands
- [Usage](cli/usage.md) - Common workflows

## Quick Start

```python
# Install the package
pip install hydra-cluster

# Or with all dependencies
pip install hydra-cluster[all]
```

## Service Endpoints

| Service | Port | URL |
|---------|------|-----|
| TabbyAPI | 5000 | http://192.168.1.250:5000 |
| LiteLLM | 4000 | http://192.168.1.244:4000 |
| Ollama | 11434 | http://192.168.1.203:11434 |
| Qdrant | 6333 | http://192.168.1.244:6333 |
| Meilisearch | 7700 | http://192.168.1.244:7700 |
| ComfyUI | 8188 | http://192.168.1.203:8188 |

## Environment Variables

```bash
# Inference
LITELLM_URL=http://192.168.1.244:4000
LITELLM_API_KEY=sk-...
TABBY_URL=http://192.168.1.250:5000
OLLAMA_URL=http://192.168.1.203:11434

# Search
QDRANT_URL=http://192.168.1.244:6333
MEILISEARCH_URL=http://192.168.1.244:7700
EMBEDDING_MODEL=nomic-embed-text

# Cluster
SSH_KEY_PATH=~/.ssh/id_ed25519
```
