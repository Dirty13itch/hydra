#!/usr/bin/env python3
"""
Hydra MCP Proxy Server - Local stdio-based MCP server that proxies to remote Hydra MCP HTTP API.

This script runs locally and communicates with Claude Code via stdio,
then proxies requests to the remote Hydra MCP Server over HTTP.

Usage:
  Add to Claude Code MCP settings:
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
"""
import sys
import json
import os
import urllib.request
import urllib.error
from typing import Any

HYDRA_MCP_URL = os.environ.get("HYDRA_MCP_URL", "http://192.168.1.244:8600")

def http_get(path: str) -> dict:
    """Make HTTP GET request to Hydra MCP server"""
    try:
        url = f"{HYDRA_MCP_URL}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}"}

def http_post(path: str, data: dict = None) -> dict:
    """Make HTTP POST request to Hydra MCP server"""
    try:
        url = f"{HYDRA_MCP_URL}{path}"
        body = json.dumps(data or {}).encode() if data else b""
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}"}

# MCP Tool definitions
TOOLS = [
    {
        "name": "hydra_cluster_status",
        "description": "Get the current status of the Hydra cluster including all services and Prometheus targets",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_services_status",
        "description": "Check the health status of key Hydra services (Letta, CrewAI, Qdrant, LiteLLM, Prometheus)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_metrics_summary",
        "description": "Get a summary of cluster metrics: CPU, memory, disk usage averages",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_metrics_nodes",
        "description": "Get per-node metrics for all cluster nodes",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_containers_list",
        "description": "List all running Docker containers on the storage node",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_container_logs",
        "description": "Get logs from a specific container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name"},
                "tail": {"type": "integer", "description": "Number of lines (default 100)", "default": 100}
            },
            "required": ["container"]
        }
    },
    {
        "name": "hydra_container_restart",
        "description": "Restart a container. Protected containers require a confirmation token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name"},
                "confirmation_token": {"type": "string", "description": "Confirmation token for protected containers"}
            },
            "required": ["container"]
        }
    },
    {
        "name": "hydra_protected_containers",
        "description": "List containers that are protected and require confirmation to restart",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_pending_confirmations",
        "description": "List pending confirmation tokens for dangerous operations",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_audit_log",
        "description": "Get recent audit log entries",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of entries (default 50)", "default": 50}
            },
            "required": []
        }
    },
    {
        "name": "hydra_knowledge_search",
        "description": "Search the Hydra knowledge base using semantic search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Number of results (default 5)", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hydra_letta_message",
        "description": "Send a message to the Hydra Steward Letta agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["message"]
        }
    },
    {
        "name": "hydra_letta_memory",
        "description": "Get the current memory blocks from the Hydra Steward agent",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_inference_models",
        "description": "List available inference models via LiteLLM",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_gpu_status",
        "description": "Get GPU utilization metrics from cluster nodes",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_run_crew",
        "description": "Run a CrewAI crew (monitoring, research, or maintenance)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "crew": {"type": "string", "description": "Crew name: monitoring, research, or maintenance"},
                "topic": {"type": "string", "description": "Optional topic for research crew"}
            },
            "required": ["crew"]
        }
    }
]

def handle_tool_call(name: str, arguments: dict) -> dict:
    """Handle MCP tool calls by proxying to Hydra MCP HTTP API"""

    if name == "hydra_cluster_status":
        return http_get("/cluster/status")

    elif name == "hydra_services_status":
        return http_get("/services/status")

    elif name == "hydra_metrics_summary":
        return http_get("/metrics/summary")

    elif name == "hydra_metrics_nodes":
        return http_get("/metrics/nodes")

    elif name == "hydra_containers_list":
        return http_get("/containers/list")

    elif name == "hydra_container_logs":
        container = arguments.get("container", "")
        tail = arguments.get("tail", 100)
        return http_get(f"/containers/{container}/logs?tail={tail}")

    elif name == "hydra_container_restart":
        return http_post("/containers/restart", {
            "container": arguments.get("container", ""),
            "confirmation_token": arguments.get("confirmation_token")
        })

    elif name == "hydra_protected_containers":
        return http_get("/safety/protected")

    elif name == "hydra_pending_confirmations":
        return http_get("/safety/pending")

    elif name == "hydra_audit_log":
        limit = arguments.get("limit", 50)
        return http_get(f"/audit/log?limit={limit}")

    elif name == "hydra_knowledge_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        return http_get(f"/knowledge/search?query={urllib.parse.quote(query)}&limit={limit}")

    elif name == "hydra_letta_message":
        message = arguments.get("message", "")
        return http_post(f"/letta/message?message={urllib.parse.quote(message)}")

    elif name == "hydra_letta_memory":
        return http_get("/letta/memory")

    elif name == "hydra_inference_models":
        return http_get("/inference/models")

    elif name == "hydra_gpu_status":
        return http_get("/gpu/status")

    elif name == "hydra_run_crew":
        crew = arguments.get("crew", "")
        topic = arguments.get("topic")
        payload = {"topic": topic} if topic else {}
        return http_post(f"/crews/run/{crew}", payload)

    else:
        return {"error": f"Unknown tool: {name}"}

import urllib.parse

def write_response(response: dict):
    """Write JSON-RPC response to stdout"""
    output = json.dumps(response) + "\n"
    sys.stdout.write(output)
    sys.stdout.flush()

def main():
    """Main MCP server loop - reads JSON-RPC from stdin, writes to stdout"""

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            write_response({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})
            continue

        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            write_response({
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "hydra-mcp-proxy",
                        "version": "1.0.0"
                    }
                },
                "id": request_id
            })

        elif method == "notifications/initialized":
            # No response needed for notifications
            pass

        elif method == "tools/list":
            write_response({
                "jsonrpc": "2.0",
                "result": {"tools": TOOLS},
                "id": request_id
            })

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            result = handle_tool_call(tool_name, tool_args)

            write_response({
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)}
                    ]
                },
                "id": request_id
            })

        elif method == "ping":
            write_response({
                "jsonrpc": "2.0",
                "result": {},
                "id": request_id
            })

        else:
            write_response({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id
            })

if __name__ == "__main__":
    main()
