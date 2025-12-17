"""
Hydra Tools API - Unified FastAPI Application

Exposes all Phase 11 self-improvement tools as REST endpoints:
- /diagnosis/* - Failure analysis and pattern detection
- /optimization/* - Resource utilization and optimization
- /knowledge/* - Knowledge lifecycle management
- /capabilities/* - Feature gap tracking
- /routing/* - Intelligent model routing
- /preferences/* - User preference tracking
- /activity/* - Unified activity logging (Transparency Framework)
- /control/* - System control modes (Transparency Framework)

Run with:
    uvicorn hydra_tools.api:app --host 0.0.0.0 --port 8700

Or via Docker:
    docker run -p 8700:8700 hydra-tools-api
"""

from contextlib import asynccontextmanager
from datetime import datetime
import os
import secrets
import hashlib
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus metrics
from hydra_tools.auth_metrics import (
    record_auth_result,
    record_auth_latency,
    update_auth_status,
    record_http_request,
    metrics_endpoint,
    HTTP_REQUESTS_IN_PROGRESS,
)

# Structured logging - configure at import time before FastAPI starts
from hydra_tools.logging_config import (
    setup_logging,
    get_logger,
    generate_request_id,
    set_request_id,
    log_request,
)

# Initialize structured logging at module import
# This ensures JSON formatting is set up before uvicorn configures its loggers
_use_json = os.environ.get("HYDRA_LOG_JSON", "true").lower() == "true"
setup_logging(json_format=_use_json)

# Import router creators
from hydra_tools.self_diagnosis import create_diagnosis_router
from hydra_tools.resource_optimization import create_optimization_router
from hydra_tools.knowledge_optimization import create_knowledge_router
from hydra_tools.capability_expansion import create_capability_api as create_capabilities_router
from hydra_tools.activity import create_activity_router, create_control_router
from hydra_tools.hardware_discovery import create_hardware_router
from hydra_tools.scheduler import create_scheduler_router, get_scheduler
from hydra_tools.letta_bridge import create_letta_bridge_router
from hydra_tools.search_api import create_search_router, create_ingest_router, create_research_router
from hydra_tools.crews_api import create_crews_router
from hydra_tools.story_crew import create_story_crew_router
from hydra_tools.alerts_api import create_alerts_router
from hydra_tools.health_api import create_health_router
from hydra_tools.voice_api import create_voice_router
from hydra_tools.reconcile_api import create_reconcile_router
from hydra_tools.constitution import create_constitution_router, get_enforcer
from hydra_tools.self_improvement import create_self_improvement_router
from hydra_tools.sandbox import create_sandbox_router
from hydra_tools.memory_architecture import create_memory_router
from hydra_tools.predictive_maintenance import create_predictive_router
from hydra_tools.preference_collector import create_preference_collector_router
from hydra_tools.container_health import create_container_health_router
from hydra_tools.benchmark_suite import create_benchmark_router
from hydra_tools.presence_automation import create_presence_router
from hydra_tools.calendar_intelligence import create_calendar_router
from hydra_tools.discord_bot import create_discord_router
from hydra_tools.agent_scheduler import create_scheduler_router as create_agent_scheduler_router, get_scheduler as get_agent_scheduler
from hydra_tools.wake_word import create_wake_word_router
from hydra_tools.discovery_archive import create_discovery_router
from hydra_tools.character_consistency import create_character_router
from hydra_tools.comfyui_client import create_comfyui_router
from hydra_tools.dashboard_api import create_dashboard_router, get_dashboard_state
from hydra_tools.home_automation import create_home_automation_router
from hydra_tools.logs_api import create_logs_router
from hydra_tools.autonomous_controller import create_autonomous_router, get_controller
from hydra_tools.routers.unraid import router as unraid_router
from hydra_tools.routers.events import router as events_router
from hydra_tools.routers.services import create_services_router
from hydra_tools.clients.unraid_client import close_unraid_client
from hydra_tools.asset_quality import create_quality_router
from hydra_tools.semantic_cache import create_semantic_cache_router
from hydra_tools.face_detection import create_face_detection_router
from hydra_tools.graphiti_memory import create_graphiti_router
from hydra_tools.reranker import create_reranker_router
from hydra_tools.conversation_cache import create_conversation_cache_router

# Import core classes for direct endpoints
from hydra_tools.routellm import RouteClassifier, ModelTier
from hydra_tools.preference_learning import PreferenceLearner, FeedbackType, TaskType


# =============================================================================
# API Key Authentication
# =============================================================================

# Security scheme definitions
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

# Paths that don't require authentication
EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",  # Prometheus scrape endpoint
    "/api/v1/events/stream",  # SSE stream needs to work without auth header
    "/auth/status",  # Allow checking auth status without auth
    "/auth/generate-key",  # Allow generating keys without auth
}

# Path prefixes that don't require authentication
EXEMPT_PREFIXES = (
    "/docs",
    "/redoc",
)


def get_api_keys() -> set:
    """Get valid API keys from environment."""
    keys = set()

    # Primary API key
    primary_key = os.environ.get("HYDRA_API_KEY", "")
    if primary_key:
        keys.add(primary_key)

    # Additional keys (comma-separated)
    additional = os.environ.get("HYDRA_API_KEYS", "")
    if additional:
        for key in additional.split(","):
            key = key.strip()
            if key:
                keys.add(key)

    return keys


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    # Auth is enabled if any API keys are configured
    return bool(get_api_keys())


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key authentication."""

    async def dispatch(self, request: Request, call_next):
        auth_start = time.perf_counter()
        path = request.url.path

        # Skip auth if not enabled
        if not is_auth_enabled():
            record_auth_result("disabled", path)
            record_auth_latency(time.perf_counter() - auth_start)
            return await call_next(request)

        # Check if path is exempt
        if path in EXEMPT_PATHS:
            record_auth_result("exempt", path)
            record_auth_latency(time.perf_counter() - auth_start)
            return await call_next(request)

        # Check if path starts with exempt prefix
        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                record_auth_result("exempt", path)
                record_auth_latency(time.perf_counter() - auth_start)
                return await call_next(request)

        # Get API key from header or query parameter
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        if not api_key:
            record_auth_result("missing_key", path)
            record_auth_latency(time.perf_counter() - auth_start)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Missing API key",
                    "detail": "Provide API key via X-API-Key header or api_key query parameter",
                },
            )

        # Validate API key
        valid_keys = get_api_keys()
        if api_key not in valid_keys:
            record_auth_result("invalid_key", path)
            record_auth_latency(time.perf_counter() - auth_start)
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Invalid API key",
                    "detail": "The provided API key is not valid",
                },
            )

        # Key is valid, proceed
        record_auth_result("success", path)
        record_auth_latency(time.perf_counter() - auth_start)
        return await call_next(request)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics (latency, count, status codes)."""

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # Generate and set request ID for tracing
        request_id = generate_request_id()
        set_request_id(request_id)

        # Track in-progress requests
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        request_start = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Record metrics
            duration = time.perf_counter() - request_start
            duration_ms = duration * 1000
            record_http_request(method, path, status_code, duration)
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()

            # Log request (skip noisy endpoints)
            if path not in ("/health", "/metrics"):
                logger = get_logger("hydra_tools.api")
                log_request(logger, method, path, status_code, duration_ms)

        return response


# =============================================================================
# Application metadata
# =============================================================================
APP_TITLE = "Hydra Tools API"
APP_DESCRIPTION = """
Self-improvement and optimization toolkit for the Hydra cluster.

## Core Features

* **Self-Diagnosis** - Failure analysis, pattern detection, auto-remediation
* **Resource Optimization** - GPU/CPU/RAM analysis, model placement suggestions
* **Knowledge Optimization** - Stale detection, redundancy consolidation
* **Capability Tracking** - Feature gaps, priority scoring, roadmap generation
* **Intelligent Routing** - Route prompts to optimal models
* **Preference Learning** - Track user preferences and model performance

## Transparency Framework

* **Activity Logging** - Unified activity log for all autonomous actions
* **System Control** - Control modes, emergency stop, workflow toggles
* **Constitution** - Safety constraints and audit trail

## Search & Knowledge

* **Hybrid Search** - Combined semantic + keyword search (Qdrant + Meilisearch)
* **Document Ingestion** - Index documents and URLs to knowledge base
* **Web Research** - Search web and crawl pages (SearXNG + Firecrawl)
* **Memory Architecture** - MIRIX 6-tier memory system

## Orchestration & Agents

* **CrewAI Orchestration** - Multi-agent crews for research, monitoring, maintenance
* **Agent Scheduler** - AIOS-style agent task scheduling
* **Autonomous Controller** - Proactive task spawning and execution

## Infrastructure

* **Cluster Health** - Unified health monitoring across all nodes
* **Predictive Maintenance** - Trend analysis and failure prediction
* **Container Health** - External healthchecks for containers
* **State Reconciliation** - Drift detection and auto-remediation
* **Unraid Integration** - Storage management and monitoring

## Creative Pipeline (Phase 12)

* **Character Consistency** - Face embedding and style reference management
* **Asset Quality Scoring** - Automated quality assessment for generated images
* **Batch Portrait Generation** - Queue multiple character portraits
* **Voice Pipeline** - STT, LLM, TTS voice interaction

## Notifications & Dashboards

* **Alert Routing** - Notification routing to Discord, Slack
* **Discovery Archive** - Cross-session learning and improvement tracking
* **Dashboard API** - Real-time SSE streaming for Command Center
"""
APP_VERSION = "2.6.0"  # Prometheus auth/request metrics, API key auth, chapter automation


# Startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler."""
    # Logging already configured at module import time
    logger = get_logger("hydra_tools.api")

    # Startup
    logger.info("Hydra Tools API starting", extra={
        "version": APP_VERSION,
        "data_dir": os.environ.get('HYDRA_DATA_DIR', '/mnt/user/appdata/hydra-stack/data'),
    })

    # Initialize auth status metrics
    auth_keys = get_api_keys()
    update_auth_status(bool(auth_keys), len(auth_keys))
    print(f"  Auth enabled: {bool(auth_keys)}, Keys configured: {len(auth_keys)}")

    # Initialize shared instances
    app.state.route_classifier = RouteClassifier()
    app.state.preference_learner = PreferenceLearner(user_id="hydra-default")

    # Start the crew scheduler
    scheduler = get_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    print(f"[{datetime.utcnow().isoformat()}] Crew scheduler started")

    # Start the agent scheduler (AIOS-style)
    agent_scheduler = get_agent_scheduler()
    await agent_scheduler.start()
    app.state.agent_scheduler = agent_scheduler
    print(f"[{datetime.utcnow().isoformat()}] Agent scheduler started")

    # Register agent handlers
    from hydra_tools.character_consistency import CharacterManager

    async def character_generation_handler(task):
        """Handle character generation agent tasks."""
        import httpx
        manager = CharacterManager()
        action = task.payload.get("action", "generate_portrait")
        results = []

        if action == "generate_missing_portraits":
            characters = task.payload.get("characters", [])
            for char_name in characters:
                try:
                    # Find character by name
                    char = next((c for c in manager.list_characters() if c.name == char_name), None)
                    if char and not char.reference_images:
                        # Generate portrait via API
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(
                                "http://localhost:8700/characters/generate-portrait",
                                json={
                                    "character_id": str(char.id),
                                    "emotion": task.payload.get("emotion", "neutral"),
                                    "style": task.payload.get("style", "visual_novel")
                                },
                                timeout=60
                            )
                            results.append({"character": char_name, "status": "queued", "response": resp.json()})
                except Exception as e:
                    results.append({"character": char_name, "status": "error", "error": str(e)})

        return {"action": action, "results": results, "count": len(results)}

    agent_scheduler.register_handler("character_generation", character_generation_handler)
    print(f"[{datetime.utcnow().isoformat()}] Registered character_generation handler")

    # Start the autonomous controller (proactive task spawning)
    autonomous_controller = get_controller()
    await autonomous_controller.start()
    app.state.autonomous_controller = autonomous_controller
    print(f"[{datetime.utcnow().isoformat()}] Autonomous controller started")

    # Start background container health checker
    import asyncio
    from hydra_tools.container_health import _monitor

    async def container_health_background_task():
        """Background task to periodically check container health."""
        while True:
            try:
                await _monitor.check_all()
            except Exception as e:
                print(f"[{datetime.utcnow().isoformat()}] Container health check error: {e}")
            await asyncio.sleep(60)  # Check every 60 seconds

    container_health_task = asyncio.create_task(container_health_background_task())
    app.state.container_health_task = container_health_task
    print(f"[{datetime.utcnow().isoformat()}] Background container health checker started (60s interval)")

    yield

    # Shutdown
    print(f"[{datetime.utcnow().isoformat()}] Hydra Tools API shutting down...")
    scheduler.stop()
    await agent_scheduler.stop()
    await autonomous_controller.stop()
    container_health_task.cancel()
    try:
        await container_health_task
    except asyncio.CancelledError:
        pass
    await close_unraid_client()
    print(f"[{datetime.utcnow().isoformat()}] Schedulers, autonomous controller, and clients stopped")


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3200",
        "http://localhost:3210",
        "http://localhost:5173",  # Vite dev server for Command Center
        "http://192.168.1.244:3200",
        "http://192.168.1.244:3210",
        "http://192.168.1.244:3333",
        "http://192.168.1.244:5173",  # Vite on Unraid
        "*",  # Allow all origins for SSE streaming
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Authentication middleware (only active when HYDRA_API_KEY is set)
app.add_middleware(APIKeyAuthMiddleware)

# Request metrics middleware (must be added after auth to capture accurate status codes)
app.add_middleware(RequestMetricsMiddleware)


# Include Phase 11 routers
app.include_router(create_diagnosis_router())
app.include_router(create_optimization_router())
app.include_router(create_knowledge_router())
app.include_router(create_capabilities_router())

# Include Transparency Framework routers
app.include_router(create_activity_router())
app.include_router(create_control_router())

# Include Hardware Discovery router
app.include_router(create_hardware_router())

# Include Scheduler router
app.include_router(create_scheduler_router())

# Include Letta-OpenAI Bridge router
app.include_router(create_letta_bridge_router())

# Include Search, Ingest, and Research routers
app.include_router(create_search_router())
app.include_router(create_ingest_router())
app.include_router(create_research_router())

# Include Crews API router (CrewAI multi-agent orchestration)
app.include_router(create_crews_router())

# Include Story Crew router (story generation)
app.include_router(create_story_crew_router())

# Include Alerts API router (notification routing)
app.include_router(create_alerts_router())

# Include Health API router (cluster health aggregation)
app.include_router(create_health_router())

# Include Voice API router (voice interaction pipeline)
app.include_router(create_voice_router())

# Include Reconcile API router (state management)
app.include_router(create_reconcile_router())

# Include Constitution router (safety constraints and audit)
app.include_router(create_constitution_router())

# Include Self-Improvement router (DGM-inspired self-modification)
app.include_router(create_self_improvement_router())

# Include Sandbox router (secure code execution)
app.include_router(create_sandbox_router())

# Include Memory Architecture router (MIRIX 6-tier memory)
app.include_router(create_memory_router())

# Include Predictive Maintenance router (trend analysis, failure prediction)
app.include_router(create_predictive_router())

# Include Preference Collector router (LiteLLM callback, feedback collection)
app.include_router(create_preference_collector_router())

# Include Container Health router (external healthchecks for containers)
app.include_router(create_container_health_router())

# Include Benchmark Suite router (DGM-inspired capability metrics)
app.include_router(create_benchmark_router())

# Include Presence Automation router (Home Assistant integration)
app.include_router(create_presence_router())

# Include Calendar Intelligence router (schedule-aware operations)
app.include_router(create_calendar_router())

# Include Discord Bot router (system control via Discord)
app.include_router(create_discord_router())

# Include Agent Scheduler router (AIOS-style agent orchestration)
app.include_router(create_agent_scheduler_router())

# Include Wake Word router (voice activation)
app.include_router(create_wake_word_router())

# Include Discovery Archive router (cross-session learning)
app.include_router(create_discovery_router())

# Include Character Consistency router (Phase 12: Empire of Broken Queens)
app.include_router(create_character_router())

# Include ComfyUI router (Phase 12: image generation orchestration)
app.include_router(create_comfyui_router())

# Include Dashboard router (Command Center UI backend)
app.include_router(create_dashboard_router())

# Include Home Automation router (Home Assistant integration for Command Center)
app.include_router(create_home_automation_router())

# Include Logs router (Loki integration for cluster logs)
app.include_router(create_logs_router())

# Include Autonomous Controller router (proactive task spawning)
app.include_router(create_autonomous_router())

# Include Unraid router (Unified Control Plane - storage management)
app.include_router(unraid_router)

# Include SSE Events router (Unified Control Plane - real-time streaming)
app.include_router(events_router)

# Include Asset Quality router (Phase 12: automated quality scoring for generated assets)
app.include_router(create_quality_router())

# Include Unified Services router (Homepage integration - single pane of glass)
app.include_router(create_services_router())

# Include Semantic Cache router (LLM response caching with semantic similarity)
app.include_router(create_semantic_cache_router())

# Include Face Detection router (Phase 12: face analysis for quality scoring)
app.include_router(create_face_detection_router())

# Include Graphiti Memory router (Hybrid graph + vector + keyword search)
app.include_router(create_graphiti_router())

# Include Reranker router (Cross-encoder reranking for improved relevance)
app.include_router(create_reranker_router())

# Include Conversation Cache router (High-performance context caching)
app.include_router(create_conversation_cache_router())


# Root endpoints
@app.get("/", tags=["info"])
async def root():
    """API root - basic info."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "diagnosis": "/diagnosis",
            "optimization": "/optimization",
            "knowledge": "/knowledge",
            "capabilities": "/capabilities",
            "routing": "/routing",
            "preferences": "/preferences",
            "activity": "/activity",
            "control": "/control",
            "hardware": "/hardware",
            "scheduler": "/scheduler",
            "letta-bridge": "/letta-bridge",
            "search": "/search",
            "ingest": "/ingest",
            "research": "/research",
            "crews": "/crews",
            "alerts": "/alerts",
            "cluster-health": "/health",
            "voice": "/voice",
            "reconcile": "/reconcile",
            "constitution": "/constitution",
            "self-improvement": "/self-improvement",
            "sandbox": "/sandbox",
            "memory": "/memory",
            "predictive": "/predictive",
            "preference-collector": "/preference-collector",
            "container-health": "/container-health",
            "dashboard": "/dashboard",
            "unraid": "/api/v1/unraid",
            "events": "/api/v1/events",
            "quality": "/quality",
            "comfyui": "/comfyui",
            "cache": "/cache",
            "faces": "/faces",
            "graphiti": "/graphiti",
            "rerank": "/rerank",
            "conversation-cache": "/conversation-cache",
        },
    }


@app.get("/health", tags=["info"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
        "auth_enabled": is_auth_enabled(),
    }


@app.get("/auth/status", tags=["auth"])
async def auth_status(request: Request):
    """
    Check authentication status.

    Returns whether auth is enabled and if the provided key is valid.
    This endpoint works both with and without authentication.
    """
    auth_enabled = is_auth_enabled()
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

    if not auth_enabled:
        return {
            "auth_enabled": False,
            "message": "Authentication is disabled. Set HYDRA_API_KEY to enable.",
            "key_provided": bool(api_key),
        }

    if not api_key:
        return {
            "auth_enabled": True,
            "authenticated": False,
            "message": "No API key provided",
        }

    valid_keys = get_api_keys()
    is_valid = api_key in valid_keys

    return {
        "auth_enabled": True,
        "authenticated": is_valid,
        "message": "API key is valid" if is_valid else "API key is invalid",
    }


@app.post("/auth/generate-key", tags=["auth"])
async def generate_api_key():
    """
    Generate a new random API key.

    Note: This just generates a key - you must add it to your environment
    variables (HYDRA_API_KEY or HYDRA_API_KEYS) to use it.
    """
    # Generate a secure random key
    key = secrets.token_urlsafe(32)

    return {
        "api_key": key,
        "instructions": [
            "Add this key to your environment configuration:",
            "  HYDRA_API_KEY=<key>  (for single key)",
            "  HYDRA_API_KEYS=key1,key2,key3  (for multiple keys)",
            "",
            "Then restart the API container to apply changes.",
        ],
    }


# Prometheus metrics endpoint
@app.get("/metrics", tags=["monitoring"], include_in_schema=False)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Exposes:
    - hydra_api_auth_requests_total: Auth request counts by result
    - hydra_api_auth_latency_seconds: Auth check latency histogram
    - hydra_api_http_requests_total: HTTP request counts
    - hydra_api_http_request_latency_seconds: Request latency histogram
    """
    return await metrics_endpoint()


# Routing endpoints
@app.post("/routing/classify", tags=["routing"])
async def classify_prompt(
    prompt: str,
    system_prompt: str = None,
    prefer_quality: bool = False,
    prefer_speed: bool = False,
):
    """
    Classify a prompt and recommend optimal model.

    Returns model recommendation based on complexity analysis.
    """
    classifier: RouteClassifier = app.state.route_classifier

    result = classifier.route(
        prompt=prompt,
        system_prompt=system_prompt,
        prefer_quality=prefer_quality,
        prefer_speed=prefer_speed,
    )

    return {
        "model": result.model,
        "tier": result.tier.value,
        "confidence": result.confidence,
        "reason": result.reason,
    }


@app.get("/routing/tiers", tags=["routing"])
async def get_model_tiers():
    """Get available model tiers and their characteristics."""
    return {
        "tiers": {
            ModelTier.FAST.value: {
                "description": "7B class models for simple tasks (local inference)",
                "primary": "qwen2.5-7b",
                "models": ["qwen2.5-7b", "llama-3.1-8b", "mistral-7b", "llama-3.2-3b"],
                "backend": "Ollama on hydra-compute",
                "use_cases": ["greetings", "simple questions", "translations"],
            },
            ModelTier.QUALITY.value: {
                "description": "70B class models for complex tasks (local inference)",
                "primary": "midnight-miqu-70b",
                "models": ["midnight-miqu-70b", "tabby-primary"],
                "backend": "TabbyAPI on hydra-ai (RTX 5090 + 4090)",
                "use_cases": ["analysis", "reasoning", "long-form content"],
            },
            ModelTier.CODE.value: {
                "description": "Code-optimized models (local inference)",
                "primary": "qwen2.5-coder-7b",
                "models": ["qwen2.5-coder-7b", "codellama-13b"],
                "backend": "Ollama on hydra-compute",
                "use_cases": ["code generation", "debugging", "code review"],
            },
        }
    }


# Preference endpoints
@app.post("/preferences/interaction", tags=["preferences"])
async def record_interaction(
    prompt: str,
    model: str,
    response: str,
    latency_ms: int = None,
    feedback: str = None,
):
    """
    Record a user interaction for preference learning.

    Feedback can be: positive, negative, regenerate, or null.
    """
    learner: PreferenceLearner = app.state.preference_learner

    feedback_type = None
    if feedback:
        try:
            feedback_type = FeedbackType(feedback)
        except ValueError:
            pass

    interaction = learner.record_interaction(
        prompt=prompt,
        model=model,
        response=response,
        latency_ms=latency_ms,
        feedback=feedback_type,
    )

    return {
        "interaction_id": interaction.id,
        "task_type": interaction.task_type,
        "model": interaction.model,
    }


@app.get("/preferences/recommend", tags=["preferences"])
async def get_recommendation(
    prompt: str = None,
    task_type: str = None,
):
    """
    Get model recommendation based on learned preferences.

    Either provide a prompt (for auto-detection) or task_type.
    """
    learner: PreferenceLearner = app.state.preference_learner

    tt = None
    if task_type:
        try:
            tt = TaskType(task_type)
        except ValueError:
            pass

    model = learner.get_preferred_model(
        prompt=prompt,
        task_type=tt,
    )

    return {
        "recommended_model": model,
        "based_on": "prompt_analysis" if prompt else "task_type",
    }


@app.get("/preferences/stats", tags=["preferences"])
async def get_preference_stats():
    """Get current preference statistics."""
    learner: PreferenceLearner = app.state.preference_learner
    prefs = learner.export_preferences()

    return {
        "model_stats": prefs.get("model_stats", {}),
        "style_preferences": learner.get_style_preferences(),
    }


# Aggregate health endpoint
@app.get("/aggregate/health", tags=["aggregate"])
async def aggregate_health():
    """
    Aggregate health status from all subsystems.

    Provides a single endpoint for overall system health.
    """
    from hydra_tools.self_diagnosis import SelfDiagnosisEngine
    from hydra_tools.resource_optimization import ResourceOptimizer
    from hydra_tools.knowledge_optimization import KnowledgeOptimizer

    diagnosis = SelfDiagnosisEngine()
    optimization = ResourceOptimizer()
    knowledge = KnowledgeOptimizer()

    diag_report = diagnosis.analyze(hours=1)
    cluster_health = optimization._calculate_cluster_health()
    knowledge_metrics = knowledge.compute_metrics()

    # Calculate overall score
    overall_score = (
        diag_report.health_score * 0.4 +
        cluster_health["score"] * 0.4 +
        (100 - knowledge_metrics.stale_entries) * 0.2
    )

    return {
        "overall_health": {
            "score": min(100, max(0, overall_score)),
            "status": "healthy" if overall_score >= 80 else "degraded" if overall_score >= 50 else "critical",
        },
        "subsystems": {
            "diagnosis": {
                "score": diag_report.health_score,
                "recent_failures": diag_report.total_failures,
                "trend": diag_report.trend,
            },
            "resources": cluster_health,
            "knowledge": {
                "total_entries": knowledge_metrics.total_entries,
                "stale": knowledge_metrics.stale_entries,
                "redundant": knowledge_metrics.redundant_entries,
            },
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "path": str(request.url.path),
        },
    )


# CLI entry point
def main():
    """Run the API server."""
    import uvicorn
    from hydra_tools.logging_config import get_uvicorn_log_config

    host = os.environ.get("HYDRA_API_HOST", "0.0.0.0")
    port = int(os.environ.get("HYDRA_API_PORT", "8700"))
    use_json = os.environ.get("HYDRA_LOG_JSON", "true").lower() == "true"

    # Get uvicorn log config that matches our structured logging
    log_config = get_uvicorn_log_config(json_format=use_json)

    uvicorn.run(
        "hydra_tools.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        log_config=log_config,
        access_log=False,  # Disable uvicorn access log, use our middleware instead
    )


if __name__ == "__main__":
    main()
