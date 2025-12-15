# Hydra Cluster MCP Server

MCP (Model Context Protocol) server that provides Claude Desktop with access to the Hydra AI cluster.

## Features

- **Cluster Health**: Check overall cluster health and individual services
- **LLM Inference**: Run queries through LiteLLM gateway to TabbyAPI/Ollama
- **Knowledge Search**: Semantic search in Qdrant vector database
- **Model Management**: List loaded models on TabbyAPI and Ollama
- **GPU Status**: Monitor GPU usage across cluster nodes

## Installation

```bash
cd mcp-servers/hydra-cluster
pip install -e .
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LITELLM_URL` | http://192.168.1.244:4000 | LiteLLM gateway URL |
| `HEALTH_URL` | http://192.168.1.244:8600 | Health aggregator URL |
| `QDRANT_URL` | http://192.168.1.244:6333 | Qdrant vector DB URL |
| `TABBY_URL` | http://192.168.1.250:5000 | TabbyAPI URL |
| `OLLAMA_URL` | http://192.168.1.203:11434 | Ollama URL |

### Claude Desktop Setup

1. Copy the configuration to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hydra-cluster": {
      "command": "python",
      "args": ["-m", "hydra_mcp_server"],
      "env": {
        "LITELLM_URL": "http://192.168.1.244:4000",
        "HEALTH_URL": "http://192.168.1.244:8600"
      }
    }
  }
}
```

2. Restart Claude Desktop

3. The Hydra tools will be available in conversations

## Available Tools

### cluster_health
Get cluster health status.

```
Arguments:
  detail: "summary" | "full" | "unhealthy"
```

### check_service
Check a specific service.

```
Arguments:
  service: string (e.g., "tabbyapi", "ollama", "qdrant")
```

### list_models
List available LLM models.

### gpu_status
Get GPU status across nodes.

```
Arguments:
  node: "all" | "hydra-ai" | "hydra-compute"
```

### query_knowledge
Search the knowledge base.

```
Arguments:
  query: string
  collection: string (default: "hydra_docs")
  limit: integer (default: 5)
```

### inference
Run LLM inference.

```
Arguments:
  prompt: string
  model: string (default: "llama-70b")
  max_tokens: integer (default: 1024)
```

### cluster_services
List all services with status.

```
Arguments:
  category: "all" | "inference" | "database" | "observability" | "automation" | "ui"
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run server directly
python server.py

# Test with MCP inspector
npx @modelcontextprotocol/inspector python server.py
```

## Network Requirements

The MCP server needs network access to the Hydra cluster:
- Port 4000 (LiteLLM)
- Port 5000 (TabbyAPI)
- Port 6333 (Qdrant)
- Port 8600 (Health Aggregator)
- Port 11434 (Ollama)

If running on hydra-dev or via Tailscale, use the appropriate IPs.
