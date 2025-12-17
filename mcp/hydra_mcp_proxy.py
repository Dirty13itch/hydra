#!/usr/bin/env python3
"""
Hydra MCP Proxy Server v2.0 - MCP server that proxies to Hydra Tools API.

This script runs locally and communicates with Claude Code via stdio,
then proxies requests to the Hydra Tools API over HTTP.

Supports Phase 11 features:
- Memory (MIRIX 6-tier with Qdrant)
- Sandbox (secure code execution)
- Constitution (safety constraints)
- Self-improvement (DGM workflow)
- Voice (STT/TTS pipeline)
- Benchmarks
- And all original cluster management features

Usage:
  Add to Claude Code MCP settings:
  {
    "mcpServers": {
      "hydra": {
        "command": "python",
        "args": ["path/to/hydra_mcp_proxy.py"],
        "env": {
          "HYDRA_API_URL": "http://192.168.1.244:8700"
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
import urllib.parse
from typing import Any

# Updated to use hydra-tools-api (8700) instead of hydra-mcp (8600)
HYDRA_API_URL = os.environ.get("HYDRA_API_URL", os.environ.get("HYDRA_MCP_URL", "http://192.168.1.244:8700"))

def http_get(path: str, timeout: int = 30) -> dict:
    """Make HTTP GET request to Hydra API"""
    try:
        url = f"{HYDRA_API_URL}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}"}

def http_post(path: str, data: dict = None, timeout: int = 120) -> dict:
    """Make HTTP POST request to Hydra API"""
    try:
        url = f"{HYDRA_API_URL}{path}"
        body = json.dumps(data or {}).encode() if data else b""
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
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
    },
    # ========================
    # Phase 11 Tools
    # ========================
    {
        "name": "hydra_memory_search",
        "description": "Semantic search across Hydra's MIRIX 6-tier memory system using embeddings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hydra_memory_store",
        "description": "Store a new fact in semantic memory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The fact/knowledge to store"},
                "domain": {"type": "string", "description": "Domain category (infrastructure, inference, etc.)"},
                "confidence": {"type": "number", "description": "Confidence score 0-1", "default": 1.0}
            },
            "required": ["content", "domain"]
        }
    },
    {
        "name": "hydra_memory_status",
        "description": "Get memory system status including Qdrant backend info",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_sandbox_execute",
        "description": "Execute code in a secure sandboxed container (Python, Bash, or JavaScript)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to execute"},
                "language": {"type": "string", "description": "Language: python, bash, or javascript", "default": "python"},
                "timeout_seconds": {"type": "integer", "description": "Timeout in seconds", "default": 30}
            },
            "required": ["code"]
        }
    },
    {
        "name": "hydra_sandbox_status",
        "description": "Get sandbox system status and configuration",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_constitution_check",
        "description": "Check if an operation is allowed by constitutional constraints",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation_type": {"type": "string", "description": "Type of operation"},
                "target_resource": {"type": "string", "description": "Resource being operated on"}
            },
            "required": ["operation_type", "target_resource"]
        }
    },
    {
        "name": "hydra_constitution_status",
        "description": "Get constitutional enforcer status and integrity check",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_benchmark_run",
        "description": "Run the DGM-inspired capability benchmark suite",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_benchmark_results",
        "description": "Get the latest benchmark results",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_self_improvement_analyze",
        "description": "Analyze system and propose improvements based on benchmarks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_voice_chat",
        "description": "Send a message through the voice chat pipeline (LLM with optional TTS)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to process"},
                "voice_response": {"type": "boolean", "description": "Generate audio response", "default": False}
            },
            "required": ["text"]
        }
    },
    {
        "name": "hydra_voice_status",
        "description": "Get voice pipeline status (STT, TTS, LLM)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_diagnosis_health",
        "description": "Get self-diagnosis health report with failure analysis",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_aggregate_health",
        "description": "Get aggregate health from all subsystems",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # ========================
    # Agent Scheduler Tools
    # ========================
    {
        "name": "hydra_agent_schedule",
        "description": "Schedule an LLM agent task for execution (supports Ollama, TabbyAPI, LiteLLM backends)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt/task for the LLM agent"},
                "model": {"type": "string", "description": "Model to use (default: qwen2.5:7b)", "default": "qwen2.5:7b"},
                "backend": {"type": "string", "description": "Backend: ollama, tabby, or litellm", "default": "ollama"},
                "include_memory": {"type": "boolean", "description": "Include memory context", "default": True},
                "priority": {"type": "string", "description": "Priority: low, normal, high", "default": "normal"}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "hydra_agent_status",
        "description": "Get the status of a scheduled agent task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to check"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "hydra_agent_queue",
        "description": "List all pending and running agent tasks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # ========================
    # Discovery Archive Tools
    # ========================
    {
        "name": "hydra_discovery_log",
        "description": "Log a discovery, learning, or improvement for cross-session persistence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Type: discovery, failure, pattern, improvement, session"},
                "title": {"type": "string", "description": "Short title for the entry"},
                "description": {"type": "string", "description": "Detailed description"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"}
            },
            "required": ["type", "title", "description"]
        }
    },
    {
        "name": "hydra_discovery_search",
        "description": "Search the discovery archive for past learnings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "type": {"type": "string", "description": "Filter by type (optional)"},
                "limit": {"type": "integer", "description": "Max results", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hydra_discovery_recent",
        "description": "Get recent discoveries and learnings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of entries", "default": 20}
            },
            "required": []
        }
    },
    # ========================
    # Memory Lifecycle Tools
    # ========================
    {
        "name": "hydra_memory_health",
        "description": "Get memory system health including decay status and recommendations",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_memory_decay_run",
        "description": "Run memory decay to reduce confidence of old memories",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_memory_conflicts",
        "description": "Detect conflicting information in memory",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_memory_consolidate",
        "description": "Consolidate and archive stale memories",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # ========================
    # Research & Search Tools
    # ========================
    {
        "name": "hydra_research_web",
        "description": "Search the web using SearXNG and synthesize results",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research query"},
                "max_results": {"type": "integer", "description": "Max results to process", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hydra_search_hybrid",
        "description": "Hybrid search across knowledge base (semantic + keyword)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hydra_ingest_url",
        "description": "Ingest a URL into the knowledge base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to ingest"},
                "collection": {"type": "string", "description": "Collection name", "default": "knowledge"}
            },
            "required": ["url"]
        }
    },
    # ========================
    # Predictive Maintenance
    # ========================
    {
        "name": "hydra_predictive_analysis",
        "description": "Get predictive maintenance analysis for the cluster",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # ========================
    # Presence Automation
    # ========================
    {
        "name": "hydra_presence_status",
        "description": "Get current presence state and automation status",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # ========================
    # ComfyUI / Image Generation
    # ========================
    {
        "name": "hydra_comfyui_status",
        "description": "Get ComfyUI server status and queue info",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_comfyui_queue_prompt",
        "description": "Queue a ComfyUI workflow for execution",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow": {"type": "object", "description": "ComfyUI workflow JSON"},
                "client_id": {"type": "string", "description": "Optional client ID"}
            },
            "required": ["workflow"]
        }
    },
    {
        "name": "hydra_comfyui_history",
        "description": "Get ComfyUI execution history",
        "inputSchema": {
            "type": "object",
            "properties": {"prompt_id": {"type": "string", "description": "Optional prompt ID to filter"}},
            "required": []
        }
    },
    # ========================
    # Character System (Phase 12)
    # ========================
    {
        "name": "hydra_characters_list",
        "description": "List all Empire of Broken Queens characters",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_character_get",
        "description": "Get a specific character by ID",
        "inputSchema": {
            "type": "object",
            "properties": {"character_id": {"type": "string", "description": "Character ID"}},
            "required": ["character_id"]
        }
    },
    {
        "name": "hydra_character_create",
        "description": "Create a new character for Empire of Broken Queens",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "display_name": {"type": "string"},
                "description": {"type": "string"},
                "hair_color": {"type": "string"},
                "eye_color": {"type": "string"},
                "voice_id": {"type": "string"}
            },
            "required": ["name", "display_name", "description"]
        }
    },
    # ========================
    # n8n Workflow Triggers
    # ========================
    {
        "name": "hydra_n8n_trigger_research",
        "description": "Trigger the research crew to investigate a topic overnight",
        "inputSchema": {
            "type": "object",
            "properties": {"topic": {"type": "string", "description": "Research topic"}},
            "required": ["topic"]
        }
    },
    {
        "name": "hydra_n8n_trigger_monitoring",
        "description": "Trigger the monitoring crew to run a health check",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_n8n_trigger_maintenance",
        "description": "Trigger the maintenance crew to run optimization tasks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    # Agent Scheduler tools
    {
        "name": "hydra_agent_schedule",
        "description": "Schedule an agent task for execution (research, monitoring, maintenance, llm, character_creation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {"type": "string", "description": "Agent type: research, monitoring, maintenance, llm, character_creation"},
                "description": {"type": "string", "description": "Task description"},
                "payload": {"type": "object", "description": "Task-specific payload"},
                "priority": {"type": "string", "description": "Priority: critical, high, normal, low, idle"}
            },
            "required": ["agent_type", "description"]
        }
    },
    {
        "name": "hydra_agent_status",
        "description": "Get agent scheduler status and statistics",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_agent_create_character",
        "description": "Schedule autonomous character creation for Empire of Broken Queens",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Character name"},
                "archetype": {"type": "string", "description": "Character archetype (queen, advisor, villain, etc)"},
                "traits": {"type": "array", "items": {"type": "string"}, "description": "Personality traits"},
                "backstory_hint": {"type": "string", "description": "Brief backstory direction"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "hydra_agent_deep_research",
        "description": "Schedule autonomous deep research on a topic with web search, content synthesis, and knowledge storage",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Research topic"},
                "depth": {"type": "string", "description": "Research depth: shallow, medium, deep"},
                "store_results": {"type": "boolean", "description": "Store results in knowledge base"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "hydra_memory_extract_skill",
        "description": "Extract a reusable skill from a completed task for procedural memory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "What the task was"},
                "task_steps": {"type": "array", "items": {"type": "string"}, "description": "Steps taken"},
                "outcome": {"type": "string", "description": "Success/failure and result"},
                "context": {"type": "string", "description": "Additional context"}
            },
            "required": ["task_description", "task_steps", "outcome"]
        }
    },
    # Container remediation tools
    {
        "name": "hydra_container_unhealthy",
        "description": "Get list of currently unhealthy containers that may need remediation",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_container_restart",
        "description": "Restart a specific container. Respects constitutional protections (databases, critical infrastructure).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_name": {"type": "string", "description": "Name of container to restart"},
                "reason": {"type": "string", "description": "Reason for restart"}
            },
            "required": ["container_name"]
        }
    },
    {
        "name": "hydra_container_remediate",
        "description": "Execute a remediation action on a container (restart, stop, start, logs)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_name": {"type": "string", "description": "Name of container"},
                "action": {"type": "string", "enum": ["restart", "stop", "start", "logs"], "description": "Action to take"},
                "reason": {"type": "string", "description": "Reason for action"}
            },
            "required": ["container_name", "action"]
        }
    },
    # Sandboxed code execution tools
    {
        "name": "hydra_sandbox_execute",
        "description": "Execute code in a secure sandboxed container. Supports Python, Bash, and JavaScript. Network isolated, memory limited, read-only filesystem. Constitutional constraints enforced.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to execute"},
                "language": {"type": "string", "enum": ["python", "bash", "javascript"], "description": "Programming language (default: python)"},
                "timeout_seconds": {"type": "integer", "description": "Execution timeout (default: 30, max: 300)"},
                "memory_limit": {"type": "string", "description": "Memory limit (default: 256m)"},
                "network_enabled": {"type": "boolean", "description": "Enable network access (default: false for security)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "hydra_sandbox_status",
        "description": "Get sandbox manager status including supported languages and configuration",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_sandbox_test_isolation",
        "description": "Run security isolation tests on the sandbox (network, memory, filesystem, user)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "hydra_sandbox_history",
        "description": "Get recent sandbox execution history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results to return (default: 50)"},
                "status": {"type": "string", "enum": ["success", "failed", "timeout", "error"], "description": "Filter by status"}
            },
            "required": []
        }
    }
]

def handle_tool_call(name: str, arguments: dict) -> dict:
    """Handle MCP tool calls by proxying to Hydra MCP HTTP API"""

    if name == "hydra_cluster_status":
        return http_get("/health/cluster")

    elif name == "hydra_services_status":
        return http_get("/health/services")

    elif name == "hydra_metrics_summary":
        return http_get("/health/summary")

    elif name == "hydra_metrics_nodes":
        return http_get("/health/nodes")

    elif name == "hydra_containers_list":
        # Use container-health API which has container info
        return http_get("/container-health/status")

    elif name == "hydra_container_logs":
        container = arguments.get("container", "")
        # Check container health status (logs require direct docker access)
        return http_get(f"/container-health/check/{container}")

    elif name == "hydra_container_restart":
        # Container restart requires activity approval system
        return http_post("/activity", {
            "operation": "container_restart",
            "resource": arguments.get("container", ""),
            "parameters": {"confirmation_token": arguments.get("confirmation_token")}
        })

    elif name == "hydra_protected_containers":
        # Use constitution constraints for protected resources
        return http_get("/constitution/constraints")

    elif name == "hydra_pending_confirmations":
        return http_get("/activity/pending")

    elif name == "hydra_audit_log":
        limit = arguments.get("limit", 50)
        return http_get(f"/constitution/audit?limit={limit}")

    elif name == "hydra_knowledge_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        return http_post("/search/semantic", {"query": query, "limit": limit})

    elif name == "hydra_letta_message":
        message = arguments.get("message", "")
        # Use letta-bridge OpenAI-compatible endpoint
        return http_post("/letta-bridge/v1/chat/completions", {
            "model": "letta-agent",
            "messages": [{"role": "user", "content": message}]
        }, timeout=60)

    elif name == "hydra_letta_memory":
        # Letta bridge health includes memory info
        return http_get("/letta-bridge/health")

    elif name == "hydra_inference_models":
        # Get models from letta-bridge
        return http_get("/letta-bridge/v1/models")

    elif name == "hydra_gpu_status":
        return http_get("/health/gpu")

    elif name == "hydra_run_crew":
        crew = arguments.get("crew", "")
        topic = arguments.get("topic")
        # Map crew types to correct endpoints
        if crew == "monitoring":
            return http_get("/crews/monitoring/quick")
        elif crew == "research" and topic:
            return http_post(f"/crews/research/topic?topic={urllib.parse.quote(topic)}")
        elif crew == "maintenance":
            return http_post("/crews/maintenance/run")
        else:
            return http_get("/crews/list")

    # ========================
    # Phase 11 Tool Handlers
    # ========================

    elif name == "hydra_memory_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        return http_post(f"/memory/semantic-search?query={urllib.parse.quote(query)}&limit={limit}")

    elif name == "hydra_memory_store":
        content = arguments.get("content", "")
        domain = arguments.get("domain", "general")
        confidence = arguments.get("confidence", 1.0)
        return http_post(f"/memory/semantic?content={urllib.parse.quote(content)}&domain={domain}&confidence={confidence}")

    elif name == "hydra_memory_status":
        return http_get("/memory/stats")

    elif name == "hydra_sandbox_execute":
        return http_post("/sandbox/execute", {
            "code": arguments.get("code", ""),
            "language": arguments.get("language", "python"),
            "timeout_seconds": arguments.get("timeout_seconds", 30)
        })

    elif name == "hydra_sandbox_status":
        return http_get("/sandbox/status")

    elif name == "hydra_constitution_check":
        return http_post("/constitution/check", {
            "operation_type": arguments.get("operation_type", ""),
            "target_resource": arguments.get("target_resource", "")
        })

    elif name == "hydra_constitution_status":
        return http_get("/constitution/status")

    elif name == "hydra_benchmark_run":
        return http_post("/benchmark/run", timeout=300)

    elif name == "hydra_benchmark_results":
        return http_get("/benchmark/latest")

    elif name == "hydra_self_improvement_analyze":
        return http_post("/self-improvement/analyze-and-propose", timeout=180)

    elif name == "hydra_voice_chat":
        return http_post("/voice/chat", {
            "text": arguments.get("text", ""),
            "voice_response": arguments.get("voice_response", False)
        }, timeout=60)

    elif name == "hydra_voice_status":
        return http_get("/voice/status")

    elif name == "hydra_diagnosis_health":
        return http_get("/diagnosis/health")

    elif name == "hydra_aggregate_health":
        return http_get("/aggregate/health")

    # ========================
    # Agent Scheduler Handlers
    # ========================

    elif name == "hydra_agent_schedule":
        prompt = arguments.get("prompt", "")
        model = arguments.get("model", "qwen2.5:7b")
        backend = arguments.get("backend", "ollama")
        include_memory = arguments.get("include_memory", True)
        priority = arguments.get("priority", "normal")
        return http_post("/agent-scheduler/schedule", {
            "agent_type": "llm",
            "description": prompt[:50] if prompt else "LLM Task",
            "payload": {
                "prompt": prompt,
                "model": model,
                "backend": backend,
                "include_memory": include_memory,
                "max_tokens": 2048
            },
            "priority": priority
        })

    elif name == "hydra_agent_status":
        task_id = arguments.get("task_id", "")
        return http_get(f"/agent-scheduler/task/{task_id}")

    elif name == "hydra_agent_queue":
        return http_get("/agent-scheduler/queue")

    # ========================
    # Discovery Archive Handlers
    # ========================

    elif name == "hydra_discovery_log":
        return http_post("/discoveries/archive", {
            "type": arguments.get("type", "discovery"),
            "title": arguments.get("title", ""),
            "description": arguments.get("description", ""),
            "tags": arguments.get("tags", [])
        })

    elif name == "hydra_discovery_search":
        query = arguments.get("query", "")
        entry_type = arguments.get("type")
        limit = arguments.get("limit", 10)
        payload = {"query": query, "limit": limit}
        if entry_type:
            payload["type"] = entry_type
        return http_post("/discoveries/search", payload)

    elif name == "hydra_discovery_recent":
        limit = arguments.get("limit", 20)
        entry_type = arguments.get("type")
        url = f"/discoveries/list?limit={limit}"
        if entry_type:
            url += f"&type={entry_type}"
        return http_get(url)

    # ========================
    # Memory Lifecycle Handlers
    # ========================

    elif name == "hydra_memory_health":
        return http_get("/memory/health/memory")

    elif name == "hydra_memory_decay_run":
        return http_post("/memory/decay/run")

    elif name == "hydra_memory_conflicts":
        return http_get("/memory/conflicts/detect")

    elif name == "hydra_memory_consolidate":
        return http_post("/memory/consolidate")

    # ========================
    # Research & Search Handlers
    # ========================

    elif name == "hydra_research_web":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        return http_post(f"/research/web?query={urllib.parse.quote(query)}&max_results={max_results}", timeout=180)

    elif name == "hydra_search_hybrid":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        # Use search/query which supports multiple modes
        return http_post("/search/query", {
            "query": query,
            "limit": limit,
            "mode": "hybrid"
        })

    elif name == "hydra_ingest_url":
        url = arguments.get("url", "")
        collection = arguments.get("collection", "knowledge")
        return http_post("/ingest/url", {
            "url": url,
            "collection": collection
        }, timeout=120)

    # ========================
    # Predictive Maintenance Handler
    # ========================

    elif name == "hydra_predictive_analysis":
        return http_get("/predictive/health")

    # ========================
    # Presence Automation Handler
    # ========================

    elif name == "hydra_presence_status":
        return http_get("/presence/status")

    # ========================
    # ComfyUI / Image Generation Handlers
    # ========================

    elif name == "hydra_comfyui_status":
        # Direct call to ComfyUI on hydra-compute
        try:
            req = urllib.request.Request("http://192.168.1.203:8188/system_stats", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                stats = json.loads(response.read().decode())
            queue_req = urllib.request.Request("http://192.168.1.203:8188/queue", headers={"Accept": "application/json"})
            with urllib.request.urlopen(queue_req, timeout=10) as response:
                queue = json.loads(response.read().decode())
            return {"system": stats, "queue": queue}
        except Exception as e:
            return {"error": str(e)}

    elif name == "hydra_comfyui_queue_prompt":
        workflow = arguments.get("workflow", {})
        client_id = arguments.get("client_id", "hydra-mcp")
        try:
            payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
            req = urllib.request.Request(
                "http://192.168.1.203:8188/prompt",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"error": str(e)}

    elif name == "hydra_comfyui_history":
        prompt_id = arguments.get("prompt_id", "")
        url = f"http://192.168.1.203:8188/history/{prompt_id}" if prompt_id else "http://192.168.1.203:8188/history"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"error": str(e)}

    # ========================
    # Character System Handlers (Phase 12)
    # ========================

    elif name == "hydra_characters_list":
        return http_get("/characters/")

    elif name == "hydra_character_get":
        char_id = arguments.get("character_id", "")
        return http_get(f"/characters/{char_id}")

    elif name == "hydra_character_create":
        return http_post("/characters/", {
            "name": arguments.get("name", ""),
            "display_name": arguments.get("display_name", ""),
            "description": arguments.get("description", ""),
            "hair_color": arguments.get("hair_color", ""),
            "eye_color": arguments.get("eye_color", ""),
            "voice_id": arguments.get("voice_id")
        })

    # ========================
    # n8n Workflow Trigger Handlers
    # ========================

    elif name == "hydra_n8n_trigger_research":
        topic = arguments.get("topic", "")
        # Trigger research crew via API
        return http_post("/scheduler/trigger/research", {"topic": topic})

    elif name == "hydra_n8n_trigger_monitoring":
        # Trigger monitoring crew via API
        return http_post("/scheduler/trigger/monitoring")

    elif name == "hydra_n8n_trigger_maintenance":
        # Trigger maintenance crew via API
        return http_post("/scheduler/trigger/maintenance")

    # Agent Scheduler tools
    elif name == "hydra_agent_schedule":
        agent_type = arguments.get("agent_type", "llm")
        description = arguments.get("description", "")
        payload = arguments.get("payload", {})
        priority = arguments.get("priority", "normal")
        return http_post("/agent-scheduler/schedule", {
            "agent_type": agent_type,
            "description": description,
            "payload": payload,
            "priority": priority
        })

    elif name == "hydra_agent_status":
        return http_get("/agent-scheduler/status")

    elif name == "hydra_agent_create_character":
        name_arg = arguments.get("name", "Unknown")
        archetype = arguments.get("archetype", "queen")
        traits = arguments.get("traits", [])
        backstory_hint = arguments.get("backstory_hint", "")
        return http_post("/agent-scheduler/schedule", {
            "agent_type": "character_creation",
            "description": f"Create character: {name_arg}",
            "payload": {
                "name": name_arg,
                "archetype": archetype,
                "traits": traits,
                "backstory_hint": backstory_hint
            },
            "priority": "normal"
        })

    elif name == "hydra_agent_deep_research":
        topic = arguments.get("topic", "")
        depth = arguments.get("depth", "medium")
        store_results = arguments.get("store_results", True)
        return http_post("/agent-scheduler/schedule", {
            "agent_type": "deep_research",
            "description": f"Research: {topic}",
            "payload": {
                "topic": topic,
                "depth": depth,
                "store_results": store_results
            },
            "priority": "normal",
            "timeout_seconds": 300
        })

    elif name == "hydra_memory_extract_skill":
        return http_post("/memory/procedural/extract", {
            "task_description": arguments.get("task_description", ""),
            "task_steps": arguments.get("task_steps", []),
            "outcome": arguments.get("outcome", ""),
            "context": arguments.get("context", "")
        })

    # Container remediation tools
    elif name == "hydra_container_unhealthy":
        return http_get("/container-health/unhealthy")

    elif name == "hydra_container_restart":
        container = arguments.get("container_name", "")
        reason = arguments.get("reason", "manual")
        return http_post(f"/container-health/restart/{container}?reason={reason}")

    elif name == "hydra_container_remediate":
        return http_post("/container-health/remediate", {
            "container_name": arguments.get("container_name", ""),
            "action": arguments.get("action", "restart"),
            "reason": arguments.get("reason", "manual")
        })

    # Sandboxed code execution tools
    elif name == "hydra_sandbox_execute":
        return http_post("/sandbox/execute", {
            "code": arguments.get("code", ""),
            "language": arguments.get("language", "python"),
            "timeout_seconds": arguments.get("timeout_seconds", 30),
            "memory_limit": arguments.get("memory_limit", "256m"),
            "network_enabled": arguments.get("network_enabled", False)
        }, timeout=180)

    elif name == "hydra_sandbox_status":
        return http_get("/sandbox/status")

    elif name == "hydra_sandbox_test_isolation":
        return http_post("/sandbox/test-isolation", timeout=180)

    elif name == "hydra_sandbox_history":
        limit = arguments.get("limit", 50)
        status = arguments.get("status", "")
        params = f"?limit={limit}"
        if status:
            params += f"&status={status}"
        return http_get(f"/sandbox/history{params}")

    else:
        return {"error": f"Unknown tool: {name}"}


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
                        "version": "2.2.0"
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
