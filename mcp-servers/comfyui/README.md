# ComfyUI MCP Server

MCP server for integrating ComfyUI image generation with Claude Code.

## Features

- **comfyui_queue_status**: Get current queue status (pending/running jobs)
- **comfyui_history**: View recent generation history
- **comfyui_system_stats**: Get GPU VRAM and system stats
- **comfyui_queue_prompt**: Queue a workflow for execution
- **comfyui_interrupt**: Stop current generation

## Configuration

Add to your Claude Code MCP settings (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "comfyui": {
      "command": "python3",
      "args": ["/mnt/user/appdata/hydra-dev/mcp-servers/comfyui/server.py"],
      "env": {}
    }
  }
}
```

## Environment Variables

- `COMFYUI_URL`: ComfyUI server URL (default: http://192.168.1.203:8188)

## Example Usage

```
"Check the ComfyUI queue status"
"Show me recent generated images"
"What's the GPU VRAM usage?"
"Interrupt the current generation"
```

## ComfyUI Endpoint

This server connects to: http://192.168.1.203:8188 (hydra-compute)
