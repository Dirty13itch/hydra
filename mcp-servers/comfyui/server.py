#!/usr/bin/env python3
"""
ComfyUI MCP Server
Provides MCP interface to ComfyUI for image generation and queue management.
"""

import asyncio
import json
import sys
from typing import Any, Optional
import urllib.request
import urllib.error

COMFYUI_URL = "http://192.168.1.203:8188"

# MCP Protocol implementation
async def send_response(response: dict):
    """Send a JSON-RPC response to stdout."""
    message = json.dumps(response)
    sys.stdout.write(f"Content-Length: {len(message)}\r\n\r\n{message}")
    sys.stdout.flush()

async def read_message() -> Optional[dict]:
    """Read a JSON-RPC message from stdin."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if line == "\r\n" or line == "\n":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    if "content-length" not in headers:
        return None

    length = int(headers["content-length"])
    content = sys.stdin.read(length)
    return json.loads(content)


def comfyui_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make HTTP request to ComfyUI API."""
    url = f"{COMFYUI_URL}/{endpoint}"

    try:
        if method == "POST" and data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
        else:
            req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


# Tool implementations
def get_queue_status() -> dict:
    """Get current ComfyUI queue status."""
    result = comfyui_request("queue")
    if "error" in result:
        return result

    return {
        "pending": len(result.get("queue_pending", [])),
        "running": len(result.get("queue_running", [])),
        "queue_pending": [item[0] for item in result.get("queue_pending", [])[:5]],
        "queue_running": [item[0] for item in result.get("queue_running", [])]
    }


def get_history(limit: int = 10) -> dict:
    """Get recent generation history."""
    result = comfyui_request("history")
    if "error" in result:
        return result

    history = []
    for prompt_id, data in list(result.items())[:limit]:
        status = data.get("status", {})
        outputs = data.get("outputs", {})

        images = []
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    images.append(img.get("filename", "unknown"))

        history.append({
            "prompt_id": prompt_id,
            "status": status.get("status_str", "unknown"),
            "completed": status.get("completed", False),
            "images": images
        })

    return {"history": history, "total": len(result)}


def queue_prompt(workflow: dict, client_id: str = "mcp-server") -> dict:
    """Queue a workflow for execution."""
    data = {
        "prompt": workflow,
        "client_id": client_id
    }

    result = comfyui_request("prompt", "POST", data)
    return result


def get_system_stats() -> dict:
    """Get ComfyUI system statistics."""
    result = comfyui_request("system_stats")
    if "error" in result:
        return result

    devices = result.get("devices", [])
    gpu_info = []
    for device in devices:
        gpu_info.append({
            "name": device.get("name", "unknown"),
            "type": device.get("type", "unknown"),
            "vram_total": device.get("vram_total", 0),
            "vram_free": device.get("vram_free", 0),
            "torch_vram_total": device.get("torch_vram_total", 0),
            "torch_vram_free": device.get("torch_vram_free", 0)
        })

    return {
        "gpus": gpu_info,
        "cpu_count": result.get("system", {}).get("cpu_count", 0),
        "ram_total": result.get("system", {}).get("ram_total", 0),
        "ram_free": result.get("system", {}).get("ram_free", 0)
    }


def interrupt_current() -> dict:
    """Interrupt currently running generation."""
    result = comfyui_request("interrupt", "POST", {})
    return {"interrupted": True} if not result.get("error") else result


# MCP Protocol handlers
TOOLS = [
    {
        "name": "comfyui_queue_status",
        "description": "Get the current ComfyUI queue status showing pending and running jobs",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "comfyui_history",
        "description": "Get recent generation history from ComfyUI",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of history items to return",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "comfyui_system_stats",
        "description": "Get ComfyUI system statistics including GPU VRAM usage",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "comfyui_queue_prompt",
        "description": "Queue a ComfyUI workflow for execution. Requires a valid ComfyUI workflow JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "object",
                    "description": "ComfyUI workflow JSON"
                }
            },
            "required": ["workflow"]
        }
    },
    {
        "name": "comfyui_interrupt",
        "description": "Interrupt the currently running generation",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


async def handle_request(request: dict) -> dict:
    """Handle incoming MCP request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "comfyui-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        result = None
        if tool_name == "comfyui_queue_status":
            result = get_queue_status()
        elif tool_name == "comfyui_history":
            result = get_history(arguments.get("limit", 10))
        elif tool_name == "comfyui_system_stats":
            result = get_system_stats()
        elif tool_name == "comfyui_queue_prompt":
            result = queue_prompt(arguments.get("workflow", {}))
        elif tool_name == "comfyui_interrupt":
            result = interrupt_current()
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
        }


async def main():
    """Main MCP server loop."""
    while True:
        try:
            message = await read_message()
            if message is None:
                break

            response = await handle_request(message)
            if response is not None:
                await send_response(response)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    asyncio.run(main())
