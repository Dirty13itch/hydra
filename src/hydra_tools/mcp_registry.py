"""
MCP Registry - Model Context Protocol Tool Management

Provides a registry for all MCP tools available in Hydra:
- Tool discovery and categorization
- Official MCP server mapping
- Tool usage statistics
- Dynamic tool registration

This follows the Linux Foundation MCP standard and provides
infrastructure for migrating custom tools to official MCP servers.

Official MCP Servers to Integrate:
- @modelcontextprotocol/server-filesystem - File operations
- @mcp-servers/git-mcp-server - Git operations
- @mcp-servers/postgres - Database queries
- @mcp-servers/docker-mcp - Container management
- qdrant-mcp - Vector search (community)
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp-registry", tags=["mcp-registry"])

# Database path
DB_PATH = Path(os.environ.get("HYDRA_DATA_DIR", "/data")) / "mcp_registry.db"


# =============================================================================
# DATA MODELS
# =============================================================================

class ToolCategory(str, Enum):
    """Categories for MCP tools."""
    CLUSTER = "cluster"           # Cluster status and metrics
    CONTAINERS = "containers"     # Container management
    KNOWLEDGE = "knowledge"       # Knowledge and memory
    INFERENCE = "inference"       # LLM inference
    AGENTS = "agents"             # Agent management
    SANDBOX = "sandbox"           # Code execution
    CONSTITUTION = "constitution" # Safety and governance
    VOICE = "voice"               # Voice synthesis
    COMFYUI = "comfyui"          # Image generation
    CHARACTERS = "characters"     # Character management
    N8N = "n8n"                   # Workflow automation
    DISCOVERY = "discovery"       # Cross-session learning
    RESEARCH = "research"         # Research and search
    HEALTH = "health"             # Health monitoring
    OTHER = "other"


class ToolStatus(str, Enum):
    """Tool implementation status."""
    ACTIVE = "active"             # Working and available
    DEPRECATED = "deprecated"     # Still works, migration planned
    MIGRATING = "migrating"       # Being migrated to official MCP
    DISABLED = "disabled"         # Temporarily disabled


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    category: ToolCategory
    status: ToolStatus = ToolStatus.ACTIVE

    # Schema
    input_schema: Dict[str, Any] = field(default_factory=dict)

    # Implementation details
    endpoint: Optional[str] = None
    method: str = "GET"

    # Migration info
    official_replacement: Optional[str] = None
    migration_notes: Optional[str] = None

    # Stats
    call_count: int = 0
    last_called: Optional[str] = None
    avg_latency_ms: float = 0


class ToolDefinition(BaseModel):
    """API model for tool definition."""
    name: str
    description: str
    category: str
    status: str = "active"
    endpoint: Optional[str] = None
    method: str = "GET"
    official_replacement: Optional[str] = None


# =============================================================================
# TOOL REGISTRY
# =============================================================================

# Complete mapping of Hydra MCP tools to categories and endpoints
HYDRA_TOOLS: List[MCPTool] = [
    # Cluster Management
    MCPTool("hydra_cluster_status", "Get cluster status including all services", ToolCategory.CLUSTER, endpoint="/health/cluster"),
    MCPTool("hydra_services_status", "Check health of key services", ToolCategory.CLUSTER, endpoint="/services/status"),
    MCPTool("hydra_metrics_summary", "Get cluster metrics summary", ToolCategory.CLUSTER, endpoint="/metrics/summary"),
    MCPTool("hydra_metrics_nodes", "Get per-node metrics", ToolCategory.CLUSTER, endpoint="/metrics/nodes"),
    MCPTool("hydra_gpu_status", "Get GPU status across cluster", ToolCategory.CLUSTER, endpoint="/hardware/gpus"),
    MCPTool("hydra_aggregate_health", "Get aggregate system health score", ToolCategory.HEALTH, endpoint="/health/aggregate"),

    # Container Management - Could migrate to official docker-mcp
    MCPTool("hydra_containers_list", "List running Docker containers", ToolCategory.CONTAINERS, endpoint="/containers/list", official_replacement="docker-mcp"),
    MCPTool("hydra_container_logs", "Get container logs", ToolCategory.CONTAINERS, endpoint="/containers/{name}/logs", method="GET", official_replacement="docker-mcp"),
    MCPTool("hydra_container_restart", "Restart a container", ToolCategory.CONTAINERS, endpoint="/containers/{name}/restart", method="POST", official_replacement="docker-mcp"),
    MCPTool("hydra_container_unhealthy", "List unhealthy containers", ToolCategory.CONTAINERS, endpoint="/container-health/unhealthy"),
    MCPTool("hydra_container_remediate", "Auto-remediate container issues", ToolCategory.CONTAINERS, endpoint="/container-health/remediate", method="POST"),
    MCPTool("hydra_protected_containers", "List protected containers", ToolCategory.CONTAINERS, endpoint="/safety/protected"),

    # Knowledge & Memory
    MCPTool("hydra_knowledge_search", "Search knowledge base", ToolCategory.KNOWLEDGE, endpoint="/search/query", method="POST"),
    MCPTool("hydra_memory_search", "Search memory store", ToolCategory.KNOWLEDGE, endpoint="/memory/search", method="POST"),
    MCPTool("hydra_memory_store", "Store new memory", ToolCategory.KNOWLEDGE, endpoint="/memory/store", method="POST"),
    MCPTool("hydra_memory_status", "Get memory system status", ToolCategory.KNOWLEDGE, endpoint="/memory/status"),
    MCPTool("hydra_memory_health", "Get memory health metrics", ToolCategory.KNOWLEDGE, endpoint="/memory/health"),
    MCPTool("hydra_memory_decay_run", "Run memory decay process", ToolCategory.KNOWLEDGE, endpoint="/memory/decay", method="POST"),
    MCPTool("hydra_memory_conflicts", "Get memory conflicts", ToolCategory.KNOWLEDGE, endpoint="/memory/conflicts"),
    MCPTool("hydra_memory_consolidate", "Consolidate redundant memories", ToolCategory.KNOWLEDGE, endpoint="/memory/consolidate", method="POST"),
    MCPTool("hydra_memory_extract_skill", "Extract skill from conversation", ToolCategory.KNOWLEDGE, endpoint="/memory/extract-skill", method="POST"),

    # Inference
    MCPTool("hydra_inference_models", "List available models", ToolCategory.INFERENCE, endpoint="/models/loaded"),
    MCPTool("hydra_letta_message", "Send message to Letta agent", ToolCategory.INFERENCE, endpoint="/letta-bridge/message", method="POST"),
    MCPTool("hydra_letta_memory", "Query Letta memory", ToolCategory.INFERENCE, endpoint="/letta-bridge/memory"),

    # Agents
    MCPTool("hydra_run_crew", "Run a CrewAI crew", ToolCategory.AGENTS, endpoint="/crews/run/{name}", method="POST"),
    MCPTool("hydra_agent_schedule", "Schedule an agent task", ToolCategory.AGENTS, endpoint="/agent-scheduler/schedule", method="POST"),
    MCPTool("hydra_agent_status", "Get agent scheduler status", ToolCategory.AGENTS, endpoint="/agent-scheduler/status"),
    MCPTool("hydra_agent_queue", "Get agent task queue", ToolCategory.AGENTS, endpoint="/agent-scheduler/queue"),
    MCPTool("hydra_agent_create_character", "Create character via agent", ToolCategory.AGENTS, endpoint="/agent-scheduler/create-character", method="POST"),
    MCPTool("hydra_agent_deep_research", "Run deep research agent", ToolCategory.AGENTS, endpoint="/agent-scheduler/deep-research", method="POST"),

    # Sandbox (Code Execution)
    MCPTool("hydra_sandbox_execute", "Execute code in sandbox", ToolCategory.SANDBOX, endpoint="/sandbox/execute", method="POST"),
    MCPTool("hydra_sandbox_status", "Get sandbox status", ToolCategory.SANDBOX, endpoint="/sandbox/status"),
    MCPTool("hydra_sandbox_test_isolation", "Test sandbox isolation", ToolCategory.SANDBOX, endpoint="/sandbox/test-isolation", method="POST"),
    MCPTool("hydra_sandbox_history", "Get sandbox execution history", ToolCategory.SANDBOX, endpoint="/sandbox/history"),

    # Constitution (Safety)
    MCPTool("hydra_constitution_check", "Check if operation is allowed", ToolCategory.CONSTITUTION, endpoint="/constitution/check", method="POST"),
    MCPTool("hydra_constitution_status", "Get constitution status", ToolCategory.CONSTITUTION, endpoint="/constitution/status"),
    MCPTool("hydra_audit_log", "Get audit log", ToolCategory.CONSTITUTION, endpoint="/constitution/audit"),
    MCPTool("hydra_pending_confirmations", "Get pending confirmations", ToolCategory.CONSTITUTION, endpoint="/safety/pending"),

    # Voice
    MCPTool("hydra_voice_chat", "Send voice chat message", ToolCategory.VOICE, endpoint="/voice/chat", method="POST"),
    MCPTool("hydra_voice_status", "Get voice system status", ToolCategory.VOICE, endpoint="/voice/status"),

    # ComfyUI (Image Generation)
    MCPTool("hydra_comfyui_status", "Get ComfyUI queue status", ToolCategory.COMFYUI, endpoint="/comfyui/queue"),
    MCPTool("hydra_comfyui_queue_prompt", "Queue ComfyUI workflow", ToolCategory.COMFYUI, endpoint="/comfyui/portrait", method="POST"),
    MCPTool("hydra_comfyui_history", "Get ComfyUI prompt history", ToolCategory.COMFYUI, endpoint="/comfyui/history/{prompt_id}"),

    # Characters
    MCPTool("hydra_characters_list", "List all characters", ToolCategory.CHARACTERS, endpoint="/characters"),
    MCPTool("hydra_character_get", "Get character by ID", ToolCategory.CHARACTERS, endpoint="/characters/{id}"),
    MCPTool("hydra_character_create", "Create new character", ToolCategory.CHARACTERS, endpoint="/characters", method="POST"),

    # n8n Workflows
    MCPTool("hydra_n8n_trigger_research", "Trigger research workflow", ToolCategory.N8N, endpoint="/crews/trigger/research", method="POST"),
    MCPTool("hydra_n8n_trigger_monitoring", "Trigger monitoring workflow", ToolCategory.N8N, endpoint="/crews/trigger/monitoring", method="POST"),
    MCPTool("hydra_n8n_trigger_maintenance", "Trigger maintenance workflow", ToolCategory.N8N, endpoint="/crews/trigger/maintenance", method="POST"),

    # Discovery (Cross-session Learning)
    MCPTool("hydra_discovery_log", "Log a discovery", ToolCategory.DISCOVERY, endpoint="/discoveries", method="POST"),
    MCPTool("hydra_discovery_search", "Search discoveries", ToolCategory.DISCOVERY, endpoint="/discoveries/search", method="POST"),
    MCPTool("hydra_discovery_recent", "Get recent discoveries", ToolCategory.DISCOVERY, endpoint="/discoveries/recent"),

    # Research
    MCPTool("hydra_research_web", "Web research query", ToolCategory.RESEARCH, endpoint="/research/web", method="POST"),
    MCPTool("hydra_search_hybrid", "Hybrid search (web + knowledge)", ToolCategory.RESEARCH, endpoint="/search/hybrid", method="POST"),
    MCPTool("hydra_ingest_url", "Ingest URL into knowledge base", ToolCategory.RESEARCH, endpoint="/ingest/url", method="POST"),

    # Health & Diagnostics
    MCPTool("hydra_diagnosis_health", "Get diagnosis system health", ToolCategory.HEALTH, endpoint="/diagnosis/health"),
    MCPTool("hydra_benchmark_run", "Run benchmark suite", ToolCategory.HEALTH, endpoint="/benchmark/run", method="POST"),
    MCPTool("hydra_benchmark_results", "Get benchmark results", ToolCategory.HEALTH, endpoint="/self-improvement/benchmarks/latest"),
    MCPTool("hydra_self_improvement_analyze", "Analyze self-improvement opportunities", ToolCategory.HEALTH, endpoint="/self-improvement/analyze", method="POST"),
    MCPTool("hydra_predictive_analysis", "Get predictive maintenance analysis", ToolCategory.HEALTH, endpoint="/predictive/analysis"),
    MCPTool("hydra_presence_status", "Get presence automation status", ToolCategory.HEALTH, endpoint="/presence/status"),
]

# Official MCP servers that Hydra tools could migrate to
OFFICIAL_MCP_SERVERS = {
    "filesystem": {
        "package": "@modelcontextprotocol/server-filesystem",
        "description": "File system operations with access controls",
        "tools": ["read_file", "write_file", "list_directory", "create_directory", "move_file", "search_files", "get_file_info"],
        "hydra_equivalents": [],  # Hydra doesn't expose file operations via MCP currently
    },
    "git": {
        "package": "@mcp-servers/git-mcp-server",
        "description": "Git operations including commits, branches, diffs",
        "tools": ["git_status", "git_diff", "git_commit", "git_log", "git_branch"],
        "hydra_equivalents": [],  # Hydra doesn't have Git MCP tools
    },
    "postgres": {
        "package": "@mcp-servers/postgres",
        "description": "PostgreSQL database queries",
        "tools": ["query"],
        "hydra_equivalents": ["hydra_knowledge_search"],  # Could use postgres directly
    },
    "docker": {
        "package": "@mcp-servers/docker-mcp",
        "description": "Docker container management",
        "tools": ["list_containers", "get_logs", "start_container", "stop_container", "restart_container"],
        "hydra_equivalents": ["hydra_containers_list", "hydra_container_logs", "hydra_container_restart"],
    },
    "qdrant": {
        "package": "qdrant-mcp",
        "description": "Qdrant vector search",
        "tools": ["search", "upsert", "delete"],
        "hydra_equivalents": ["hydra_memory_search", "hydra_memory_store"],
    },
}


# =============================================================================
# DATABASE
# =============================================================================

def init_db():
    """Initialize the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_stats (
            tool_name TEXT PRIMARY KEY,
            call_count INTEGER DEFAULT 0,
            last_called TEXT,
            total_latency_ms REAL DEFAULT 0,
            error_count INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            called_at TEXT NOT NULL,
            latency_ms REAL,
            success INTEGER,
            error_message TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(tool_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_time ON tool_calls(called_at)")

    conn.commit()
    conn.close()


init_db()


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# REGISTRY FUNCTIONS
# =============================================================================

def get_tool(name: str) -> Optional[MCPTool]:
    """Get a tool by name."""
    for tool in HYDRA_TOOLS:
        if tool.name == name:
            return tool
    return None


def get_tools_by_category(category: ToolCategory) -> List[MCPTool]:
    """Get all tools in a category."""
    return [t for t in HYDRA_TOOLS if t.category == category]


def record_tool_call(tool_name: str, latency_ms: float, success: bool, error: Optional[str] = None):
    """Record a tool call for statistics."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    try:
        # Update stats
        conn.execute("""
            INSERT INTO tool_stats (tool_name, call_count, last_called, total_latency_ms, error_count)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(tool_name) DO UPDATE SET
                call_count = call_count + 1,
                last_called = ?,
                total_latency_ms = total_latency_ms + ?,
                error_count = error_count + ?
        """, (tool_name, now, latency_ms, 0 if success else 1, now, latency_ms, 0 if success else 1))

        # Record call
        conn.execute("""
            INSERT INTO tool_calls (tool_name, called_at, latency_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (tool_name, now, latency_ms, 1 if success else 0, error))

        conn.commit()
    finally:
        conn.close()


def get_tool_stats(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get statistics for a tool."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM tool_stats WHERE tool_name = ?", (tool_name,)
        ).fetchone()
        if row:
            avg_latency = row["total_latency_ms"] / row["call_count"] if row["call_count"] > 0 else 0
            return {
                "tool_name": row["tool_name"],
                "call_count": row["call_count"],
                "last_called": row["last_called"],
                "avg_latency_ms": round(avg_latency, 2),
                "error_count": row["error_count"],
                "success_rate": round((row["call_count"] - row["error_count"]) / row["call_count"] * 100, 1) if row["call_count"] > 0 else 100,
            }
        return None
    finally:
        conn.close()


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/tools")
async def list_tools(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all registered MCP tools."""
    tools = HYDRA_TOOLS

    if category:
        try:
            cat = ToolCategory(category)
            tools = [t for t in tools if t.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    if status:
        try:
            st = ToolStatus(status)
            tools = [t for t in tools if t.status == st]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    return {
        "tools": [asdict(t) for t in tools],
        "count": len(tools),
        "categories": [c.value for c in ToolCategory],
    }


@router.get("/tools/{name}")
async def get_tool_details(name: str):
    """Get details for a specific tool."""
    tool = get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {name}")

    stats = get_tool_stats(name)

    return {
        "tool": asdict(tool),
        "stats": stats,
    }


@router.get("/categories")
async def list_categories():
    """List all tool categories with counts."""
    counts = {}
    for cat in ToolCategory:
        count = len([t for t in HYDRA_TOOLS if t.category == cat])
        if count > 0:
            counts[cat.value] = count

    return {
        "categories": counts,
        "total_tools": len(HYDRA_TOOLS),
    }


@router.get("/official-servers")
async def list_official_servers():
    """List official MCP servers and their Hydra equivalents."""
    return {
        "servers": OFFICIAL_MCP_SERVERS,
        "migration_status": {
            "total_hydra_tools": len(HYDRA_TOOLS),
            "with_official_equivalent": sum(
                len(s["hydra_equivalents"]) for s in OFFICIAL_MCP_SERVERS.values()
            ),
        },
    }


@router.get("/stats")
async def get_registry_stats():
    """Get overall registry statistics."""
    conn = get_db()
    try:
        total_calls = conn.execute(
            "SELECT SUM(call_count) as total FROM tool_stats"
        ).fetchone()["total"] or 0

        top_tools = conn.execute("""
            SELECT tool_name, call_count, last_called
            FROM tool_stats
            ORDER BY call_count DESC
            LIMIT 10
        """).fetchall()

        return {
            "total_tools": len(HYDRA_TOOLS),
            "total_calls": total_calls,
            "categories": len(ToolCategory),
            "top_tools": [dict(row) for row in top_tools],
        }
    finally:
        conn.close()


@router.post("/record-call")
async def api_record_call(
    tool_name: str,
    latency_ms: float,
    success: bool = True,
    error: Optional[str] = None,
):
    """Record a tool call for statistics (internal use)."""
    record_tool_call(tool_name, latency_ms, success, error)
    return {"status": "recorded", "tool": tool_name}


@router.get("/export")
async def export_tools():
    """Export all tools in MCP-compatible format."""
    tools = []
    for t in HYDRA_TOOLS:
        tools.append({
            "name": t.name,
            "description": t.description,
            "inputSchema": t.input_schema or {"type": "object", "properties": {}, "required": []},
        })

    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": "hydra-mcp-server",
            "version": "2.0.0",
        },
        "tools": tools,
    }


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def create_mcp_registry_router() -> APIRouter:
    """Create and return the MCP registry router."""
    return router
