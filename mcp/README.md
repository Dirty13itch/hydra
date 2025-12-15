# Hydra MCP (Model Context Protocol) Server

## Architecture

```
Claude Code → hydra_mcp_proxy.py (local) → mcp_server.py (container:8600)
```

## Files

| File | Purpose | Status |
|------|---------|--------|
| `hydra_mcp_proxy.py` | Local proxy for Claude Code | ACTIVE - configured in .mcp.json |
| `mcp_server.py` | Main MCP server with all tools | ACTIVE - runs as container |
| `claude_code_mcp_config.json` | Example Claude Code config | Reference |
| `gpu_endpoint_update.py` | GPU metrics endpoint patch | Utility |
| `mcp_header_fix.py` | Header fix utility | Utility |

## Configuration

Configure in `.mcp.json` at project root:

```json
{
  "mcpServers": {
    "hydra": {
      "command": "python",
      "args": ["C:/Users/shaun/projects/hydra/mcp/hydra_mcp_proxy.py"],
      "env": {
        "HYDRA_MCP_URL": "http://192.168.1.244:8600"
      }
    }
  }
}
```

## Archived Versions

Old/experimental versions are in `legacy/mcp-archive/` and `legacy/prototypes/mcp_*.py`.

---
*Consolidated December 14, 2025*
