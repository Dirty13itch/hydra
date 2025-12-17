# Native MCP Server Deployment

## Overview

This document describes the deployment of official MCP servers alongside Hydra's REST-to-MCP proxy.

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │        Claude Desktop/Code          │
                    │          (MCP Client)               │
                    └─────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────────┐
                    │                │                    │
           ┌────────▼────────┐ ┌─────▼──────┐ ┌──────────▼──────────┐
           │ hydra-mcp-proxy │ │ filesystem │ │    postgres-mcp     │
           │   (30 tools)    │ │   (npx)    │ │      (docker)       │
           │  stdio→REST     │ │            │ │                     │
           └────────┬────────┘ └────────────┘ └──────────┬──────────┘
                    │                                     │
           ┌────────▼────────┐               ┌───────────▼───────────┐
           │ Hydra Tools API │               │   hydra-postgres      │
           │    :8700        │               │      :5432            │
           └─────────────────┘               └───────────────────────┘
```

## Server Configurations

### 1. Hydra MCP Proxy (Existing)

Our custom proxy that exposes Hydra Tools API via MCP protocol.

**Config (.mcp.json):**
```json
{
  "mcpServers": {
    "hydra": {
      "command": "python",
      "args": ["mcp/hydra_mcp_proxy.py"],
      "env": {
        "HYDRA_API_URL": "http://192.168.1.244:8700"
      }
    }
  }
}
```

### 2. Filesystem Server (Official)

Secure file access with path restrictions.

**Config:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/user/appdata/hydra-dev",
        "/mnt/user/appdata/hydra-tools"
      ]
    }
  }
}
```

**Tools Provided:**
- `read_file` - Read file contents
- `read_multiple_files` - Read multiple files at once
- `write_file` - Write to a file
- `create_directory` - Create a directory
- `list_directory` - List directory contents
- `move_file` - Move or rename a file
- `search_files` - Search for files by pattern
- `get_file_info` - Get file metadata

### 3. PostgreSQL Server (Docker)

Direct database access for queries.

**Config:**
```json
{
  "mcpServers": {
    "postgres": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--network", "host",
        "mcp/postgres",
        "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra"
      ]
    }
  }
}
```

**Tools Provided:**
- `query` - Execute SQL query (read-only by default)
- `list_tables` - List all tables
- `describe_table` - Get table schema

## Complete .mcp.json Configuration

```json
{
  "mcpServers": {
    "hydra": {
      "command": "python",
      "args": ["mcp/hydra_mcp_proxy.py"],
      "env": {
        "HYDRA_API_URL": "http://192.168.1.244:8700"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/user/appdata/hydra-dev",
        "/mnt/user/appdata/hydra-tools",
        "/mnt/user/appdata/hydra-stack"
      ]
    },
    "postgres": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--network", "host",
        "mcp/postgres",
        "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra"
      ]
    }
  }
}
```

## Security Notes

1. **Filesystem paths are restricted** - Only specified directories are accessible
2. **Database uses app user** - Not root, limited permissions
3. **Docker runs with --rm** - Containers are ephemeral
4. **Network host mode** - Required for localhost database access

## Tool Count Summary

| Server | Tools | Purpose |
|--------|-------|---------|
| hydra-mcp-proxy | 30 | Hydra-specific operations |
| filesystem | 15 | File operations (read, write, edit, search, tree) |
| postgres | 1 | Read-only SQL queries |
| **Total** | **46** | |

## Installation

### Prerequisites

```bash
# Install Node.js (for npx)
# On NixOS nodes, Node.js is available
# On Unraid, install via user scripts or nerd pack

# Pull postgres MCP image
docker pull mcp/postgres
```

### Testing

```bash
# Test filesystem server
npx -y @modelcontextprotocol/server-filesystem /tmp --help

# Test postgres server
docker run -i --rm --network host mcp/postgres \
  "postgresql://hydra:g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6@192.168.1.244:5432/hydra"
```
