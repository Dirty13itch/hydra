#!/usr/bin/env python3
"""
Hydra Cluster MCP Server

Provides Claude Desktop with access to the Hydra cluster via MCP protocol.
Exposes tools for:
- Cluster health monitoring
- Service status checks
- LLM inference
- Knowledge search
- SSH command execution

Install: pip install mcp httpx
Run: python server.py
"""

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# Configuration
LITELLM_URL = os.getenv("LITELLM_URL", "http://192.168.1.244:4000")
HEALTH_URL = os.getenv("HEALTH_URL", "http://192.168.1.244:8600")
QDRANT_URL = os.getenv("QDRANT_URL", "http://192.168.1.244:6333")
TABBY_URL = os.getenv("TABBY_URL", "http://192.168.1.250:5000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.203:11434")

# Create server
server = Server("hydra-cluster")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="cluster_health",
            description="Get Hydra cluster health status including all services, nodes, and any issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["summary", "full", "unhealthy"],
                        "description": "Level of detail to return",
                        "default": "summary",
                    }
                },
            },
        ),
        Tool(
            name="check_service",
            description="Check health of a specific cluster service",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name (e.g., tabbyapi, ollama, litellm, qdrant)",
                    }
                },
                "required": ["service"],
            },
        ),
        Tool(
            name="list_models",
            description="List available LLM models on TabbyAPI and Ollama",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="gpu_status",
            description="Get GPU status across cluster nodes (VRAM, power, temperature)",
            inputSchema={
                "type": "object",
                "properties": {
                    "node": {
                        "type": "string",
                        "enum": ["all", "hydra-ai", "hydra-compute"],
                        "default": "all",
                    }
                },
            },
        ),
        Tool(
            name="query_knowledge",
            description="Search the Hydra knowledge base using semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection to search",
                        "default": "hydra_docs",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="inference",
            description="Run LLM inference through LiteLLM gateway",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (llama-70b, llama-8b, qwen-7b)",
                        "default": "llama-70b",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                        "default": 1024,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="cluster_services",
            description="List all cluster services with their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "inference", "database", "observability", "automation", "ui"],
                        "default": "all",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""

    async with httpx.AsyncClient(timeout=30.0) as client:

        if name == "cluster_health":
            detail = arguments.get("detail", "summary")

            if detail == "summary":
                response = await client.get(f"{HEALTH_URL}/health/summary")
            elif detail == "unhealthy":
                response = await client.get(f"{HEALTH_URL}/health/services?status=unhealthy")
            else:
                response = await client.get(f"{HEALTH_URL}/health")

            if response.status_code == 200:
                data = response.json()
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(data, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {response.status_code}")]
                )

        elif name == "check_service":
            service = arguments["service"]
            response = await client.get(f"{HEALTH_URL}/health/service/{service}")

            if response.status_code == 200:
                data = response.json()
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(data, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Service not found: {service}")]
                )

        elif name == "list_models":
            results = {"tabbyapi": None, "ollama": None}

            # TabbyAPI
            try:
                response = await client.get(f"{TABBY_URL}/v1/model")
                if response.status_code == 200:
                    results["tabbyapi"] = response.json()
            except Exception as e:
                results["tabbyapi"] = {"error": str(e)}

            # Ollama
            try:
                response = await client.get(f"{OLLAMA_URL}/api/tags")
                if response.status_code == 200:
                    results["ollama"] = response.json()
            except Exception as e:
                results["ollama"] = {"error": str(e)}

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(results, indent=2))]
            )

        elif name == "gpu_status":
            # This would need SSH access or a dedicated metrics endpoint
            # For now, return a placeholder
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="GPU status requires SSH access. Use hydra CLI: hydra gpu"
                )]
            )

        elif name == "query_knowledge":
            query = arguments["query"]
            collection = arguments.get("collection", "hydra_docs")
            limit = arguments.get("limit", 5)

            # Generate embedding via Ollama
            embed_response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": query}
            )

            if embed_response.status_code != 200:
                return CallToolResult(
                    content=[TextContent(type="text", text="Failed to generate embedding")]
                )

            embedding = embed_response.json()["embedding"]

            # Search Qdrant
            search_response = await client.post(
                f"{QDRANT_URL}/collections/{collection}/points/search",
                json={
                    "vector": embedding,
                    "limit": limit,
                    "with_payload": True,
                }
            )

            if search_response.status_code == 200:
                results = search_response.json()
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(results, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Search error: {search_response.status_code}")]
                )

        elif name == "inference":
            prompt = arguments["prompt"]
            model = arguments.get("model", "llama-70b")
            max_tokens = arguments.get("max_tokens", 1024)

            response = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                timeout=120.0,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                result = {
                    "response": content,
                    "model": data.get("model"),
                    "tokens": usage,
                }
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Inference error: {response.text}")]
                )

        elif name == "cluster_services":
            category = arguments.get("category", "all")

            if category == "all":
                response = await client.get(f"{HEALTH_URL}/health/services")
            else:
                response = await client.get(f"{HEALTH_URL}/health/services?category={category}")

            if response.status_code == 200:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response.json(), indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {response.status_code}")]
                )

        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
