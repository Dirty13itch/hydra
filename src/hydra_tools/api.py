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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import router creators
from hydra_tools.self_diagnosis import create_diagnosis_router
from hydra_tools.resource_optimization import create_optimization_router
from hydra_tools.knowledge_optimization import create_knowledge_router
from hydra_tools.capability_expansion import create_capability_api as create_capabilities_router
from hydra_tools.activity import create_activity_router, create_control_router
from hydra_tools.hardware_discovery import create_hardware_router
from hydra_tools.scheduler import create_scheduler_router, get_scheduler

# Import core classes for direct endpoints
from hydra_tools.routellm import RouteClassifier, ModelTier
from hydra_tools.preference_learning import PreferenceLearner, FeedbackType, TaskType


# Application metadata
APP_TITLE = "Hydra Tools API"
APP_DESCRIPTION = """
Self-improvement and optimization toolkit for the Hydra cluster.

## Features

* **Self-Diagnosis** - Failure analysis, pattern detection, auto-remediation
* **Resource Optimization** - GPU/CPU/RAM analysis, model placement suggestions
* **Knowledge Optimization** - Stale detection, redundancy consolidation
* **Capability Tracking** - Feature gaps, priority scoring, roadmap generation
* **Intelligent Routing** - Route prompts to optimal models
* **Preference Learning** - Track user preferences and model performance
* **Activity Logging** - Unified activity log for all autonomous actions
* **System Control** - Control modes, emergency stop, workflow toggles
"""
APP_VERSION = "1.2.0"


# Startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler."""
    # Startup
    print(f"[{datetime.utcnow().isoformat()}] Hydra Tools API starting...")
    print(f"  Data directory: {os.environ.get('HYDRA_DATA_DIR', '/mnt/user/appdata/hydra-stack/data')}")

    # Initialize shared instances
    app.state.route_classifier = RouteClassifier()
    app.state.preference_learner = PreferenceLearner(user_id="hydra-default")

    # Start the crew scheduler
    scheduler = get_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    print(f"[{datetime.utcnow().isoformat()}] Crew scheduler started")

    yield

    # Shutdown
    print(f"[{datetime.utcnow().isoformat()}] Hydra Tools API shutting down...")
    scheduler.stop()
    print(f"[{datetime.utcnow().isoformat()}] Crew scheduler stopped")


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
        "http://192.168.1.244:3200",
        "http://192.168.1.244:3333",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        },
    }


@app.get("/health", tags=["info"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
    }


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

    host = os.environ.get("HYDRA_API_HOST", "0.0.0.0")
    port = int(os.environ.get("HYDRA_API_PORT", "8700"))

    uvicorn.run(
        "hydra_tools.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
