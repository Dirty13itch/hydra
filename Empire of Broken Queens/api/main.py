"""
Empire of Broken Queens - Control Plane API
FastAPI service for orchestrating generation pipeline
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import httpx
import asyncpg
import uuid
import os
import json

# =============================================================================
# Configuration (from environment variables)
# =============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://hydra:hydra@192.168.1.244:5432/empire_of_broken_queens")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://192.168.1.203:8188")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://192.168.1.244:6333")
REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.1.244:6379")

# =============================================================================
# Enums
# =============================================================================

class TaskType(str, Enum):
    portrait = "portrait"
    expression = "expression"
    pose = "pose"
    explicit = "explicit"
    background = "background"
    video_idle = "video_idle"
    voice_line = "voice_line"
    lora_training = "lora_training"

class TaskPriority(str, Enum):
    critical = "critical"
    high = "high"
    normal = "normal"
    low = "low"
    idle = "idle"

class TaskStatus(str, Enum):
    queued = "queued"
    assigned = "assigned"
    running = "running"
    quality_check = "quality_check"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class QueenTier(str, Enum):
    alpha = "Alpha"
    elite = "Elite"
    core = "Core"
    exotic = "Exotic"
    specialist = "Specialist"
    legacy = "Legacy"

# =============================================================================
# Models
# =============================================================================

class QueenBase(BaseModel):
    name: str
    codename: Optional[str] = None
    tier: QueenTier

class QueenResponse(QueenBase):
    id: int
    height: Optional[str] = None
    measurements: Optional[str] = None
    portrait_count: int = 0
    lora_path: Optional[str] = None

class QueenAssetSummary(BaseModel):
    queen_id: int
    queen_name: str
    queen_slug: str
    tier: str
    approved_portraits: int = 0
    approved_expressions: int = 0
    approved_poses: int = 0
    approved_explicit: int = 0
    pending_review: int = 0
    avg_quality_score: Optional[float] = None
    last_generated_at: Optional[datetime] = None

class GenerationRequest(BaseModel):
    queen_slug: str
    task_type: TaskType
    count: int = Field(default=10, ge=1, le=100)
    priority: TaskPriority = TaskPriority.normal
    config: Optional[dict] = None

class GenerationTaskResponse(BaseModel):
    id: str
    task_type: TaskType
    queen_slug: str
    status: TaskStatus
    priority: TaskPriority
    total_count: int
    completed_count: int
    approved_count: int
    created_at: datetime

class BatchGenerationRequest(BaseModel):
    tasks: List[GenerationRequest]

class QueueStatusResponse(BaseModel):
    queued: int
    running: int
    completed_today: int
    failed_today: int
    images_generated_today: int
    images_approved_today: int

class ClusterStatusResponse(BaseModel):
    hydra_ai: dict
    hydra_compute: dict
    comfyui_queue: int
    database_connected: bool
    qdrant_connected: bool

# =============================================================================
# Application
# =============================================================================

app = FastAPI(
    title="Empire Control Plane",
    description="Orchestration API for Empire of Broken Queens asset generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/status", response_model=ClusterStatusResponse)
async def cluster_status():
    """Get overall cluster status"""
    status = {
        "hydra_ai": {"status": "unknown"},
        "hydra_compute": {"status": "unknown"},
        "comfyui_queue": 0,
        "database_connected": False,
        "qdrant_connected": False
    }

    # Check database
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            status["database_connected"] = True
    except:
        pass

    # Check Qdrant
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{QDRANT_URL}/collections", timeout=5)
            status["qdrant_connected"] = resp.status_code == 200
    except:
        pass

    # Check ComfyUI queue
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{COMFYUI_URL}/queue", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                status["comfyui_queue"] = len(data.get("queue_running", [])) + len(data.get("queue_pending", []))
                status["hydra_compute"]["status"] = "online"
    except:
        pass

    return status

@app.get("/queue/status", response_model=QueueStatusResponse)
async def queue_status():
    """Get generation queue statistics"""
    async with db_pool.acquire() as conn:
        queued = await conn.fetchval(
            "SELECT COUNT(*) FROM generation_tasks WHERE status = 'queued'"
        )
        running = await conn.fetchval(
            "SELECT COUNT(*) FROM generation_tasks WHERE status IN ('assigned', 'running')"
        )
        completed_today = await conn.fetchval(
            "SELECT COUNT(*) FROM generation_tasks WHERE status = 'completed' AND completed_at >= CURRENT_DATE"
        )
        failed_today = await conn.fetchval(
            "SELECT COUNT(*) FROM generation_tasks WHERE status = 'failed' AND completed_at >= CURRENT_DATE"
        )
        images_today = await conn.fetchval(
            "SELECT COALESCE(SUM(completed_count), 0) FROM generation_tasks WHERE completed_at >= CURRENT_DATE"
        )
        approved_today = await conn.fetchval(
            "SELECT COALESCE(SUM(approved_count), 0) FROM generation_tasks WHERE completed_at >= CURRENT_DATE"
        )

    return QueueStatusResponse(
        queued=queued or 0,
        running=running or 0,
        completed_today=completed_today or 0,
        failed_today=failed_today or 0,
        images_generated_today=images_today or 0,
        images_approved_today=approved_today or 0
    )

# =============================================================================
# Queens Endpoints
# =============================================================================

@app.get("/queens", response_model=List[QueenResponse])
async def list_queens():
    """Get all queens"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, codename, tier, height, measurements, portrait_count, lora_path
            FROM queens
            ORDER BY
                CASE tier
                    WHEN 'Alpha' THEN 1
                    WHEN 'Elite' THEN 2
                    WHEN 'Core' THEN 3
                    WHEN 'Exotic' THEN 4
                    WHEN 'Specialist' THEN 5
                    WHEN 'Legacy' THEN 6
                END, name
        """)
    return [dict(row) for row in rows]

@app.get("/queens/{slug}", response_model=QueenResponse)
async def get_queen(slug: str):
    """Get queen by slug"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, name, codename, tier, height, measurements, portrait_count, lora_path
            FROM queens
            WHERE slug = $1
        """, slug.lower())

    if not row:
        raise HTTPException(status_code=404, detail="Queen not found")
    return dict(row)

@app.get("/queens/{slug}/assets", response_model=QueenAssetSummary)
async def get_queen_assets(slug: str):
    """Get queen asset summary"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM queen_asset_summary
            WHERE queen_slug = $1
        """, slug.lower())

    if not row:
        raise HTTPException(status_code=404, detail="Queen not found")
    return dict(row)

@app.get("/queens/{slug}/dna")
async def get_queen_dna(slug: str):
    """Get queen's full DNA configuration"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT name, codename, tier, dna, backstory
            FROM queens
            WHERE slug = $1
        """, slug.lower())

    if not row:
        raise HTTPException(status_code=404, detail="Queen not found")
    return dict(row)

# =============================================================================
# Generation Endpoints
# =============================================================================

@app.post("/generate", response_model=GenerationTaskResponse)
async def create_generation_task(request: GenerationRequest, background_tasks: BackgroundTasks):
    """Create a new generation task"""
    task_id = str(uuid.uuid4())

    async with db_pool.acquire() as conn:
        # Verify queen exists
        queen = await conn.fetchrow("""
            SELECT id, name, slug, dna FROM queens
            WHERE slug = $1
        """, request.queen_slug.lower())

        if not queen:
            raise HTTPException(status_code=404, detail="Queen not found")

        # Create task
        await conn.execute("""
            INSERT INTO generation_tasks (
                id, task_type, priority, queen_id, queen_slug,
                config, status, total_count, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'queued', $7, 'api')
        """,
            uuid.UUID(task_id),
            request.task_type.value,
            request.priority.value,
            queen["id"],
            request.queen_slug.lower(),
            json.dumps(request.config or {}),
            request.count
        )

        # Get created task
        row = await conn.fetchrow("""
            SELECT id, task_type, queen_slug, status, priority,
                   total_count, completed_count, approved_count, created_at
            FROM generation_tasks WHERE id = $1
        """, uuid.UUID(task_id))

    # Queue to ComfyUI in background
    background_tasks.add_task(queue_to_comfyui, task_id, request)

    return GenerationTaskResponse(
        id=str(row["id"]),
        task_type=row["task_type"],
        queen_slug=row["queen_slug"],
        status=row["status"],
        priority=row["priority"],
        total_count=row["total_count"],
        completed_count=row["completed_count"],
        approved_count=row["approved_count"],
        created_at=row["created_at"]
    )

@app.post("/generate/batch")
async def create_batch_generation(request: BatchGenerationRequest, background_tasks: BackgroundTasks):
    """Create multiple generation tasks"""
    results = []
    for task_request in request.tasks:
        try:
            result = await create_generation_task(task_request, background_tasks)
            results.append({"status": "created", "task": result})
        except HTTPException as e:
            results.append({"status": "error", "error": e.detail, "request": task_request.dict()})

    return {"tasks": results, "total": len(results)}

@app.get("/tasks/{task_id}", response_model=GenerationTaskResponse)
async def get_task(task_id: str):
    """Get task status"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, task_type, queen_slug, status, priority,
                   total_count, completed_count, approved_count, created_at
            FROM generation_tasks WHERE id = $1
        """, uuid.UUID(task_id))

    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    return GenerationTaskResponse(
        id=str(row["id"]),
        task_type=row["task_type"],
        queen_slug=row["queen_slug"],
        status=row["status"],
        priority=row["priority"],
        total_count=row["total_count"],
        completed_count=row["completed_count"],
        approved_count=row["approved_count"],
        created_at=row["created_at"]
    )

@app.get("/tasks")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    queen_slug: Optional[str] = None,
    limit: int = 50
):
    """List generation tasks"""
    async with db_pool.acquire() as conn:
        query = """
            SELECT id, task_type, queen_slug, status, priority,
                   total_count, completed_count, approved_count, created_at
            FROM generation_tasks
            WHERE 1=1
        """
        params = []

        if status:
            params.append(status.value)
            query += f" AND status = ${len(params)}"

        if queen_slug:
            params.append(queen_slug.lower())
            query += f" AND queen_slug = ${len(params)}"

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a queued task"""
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE generation_tasks
            SET status = 'cancelled'
            WHERE id = $1 AND status = 'queued'
        """, uuid.UUID(task_id))

    if result == "UPDATE 0":
        raise HTTPException(status_code=400, detail="Task cannot be cancelled (not queued)")

    return {"status": "cancelled", "task_id": task_id}

# =============================================================================
# Background Tasks
# =============================================================================

async def queue_to_comfyui(task_id: str, request: GenerationRequest):
    """Queue generation to ComfyUI"""
    try:
        # Get queen's DNA for prompt
        async with db_pool.acquire() as conn:
            queen = await conn.fetchrow("""
                SELECT name, dna FROM queens
                WHERE slug = $1
            """, request.queen_slug.lower())

            # Update task status
            await conn.execute("""
                UPDATE generation_tasks
                SET status = 'assigned', assigned_node = 'hydra-compute', started_at = NOW()
                WHERE id = $1
            """, uuid.UUID(task_id))

        # Build and queue ComfyUI workflow
        dna_raw = queen["dna"] if queen else "{}"
        dna = json.loads(dna_raw) if isinstance(dna_raw, str) else (dna_raw or {})
        base_prompt = dna.get("generation", {}).get("base_prompt", queen["name"])

        async with httpx.AsyncClient() as client:
            for i in range(request.count):
                workflow = build_comfyui_workflow(
                    task_type=request.task_type.value,
                    queen_name=queen["name"],
                    queen_slug=request.queen_slug,
                    base_prompt=base_prompt,
                    seed=None,  # Random
                    index=i
                )

                await client.post(
                    f"{COMFYUI_URL}/prompt",
                    json={"prompt": workflow},
                    timeout=30
                )

        # Update status
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE generation_tasks
                SET status = 'running'
                WHERE id = $1
            """, uuid.UUID(task_id))

    except Exception as e:
        # Mark as failed
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE generation_tasks
                SET status = 'failed', last_error = $2
                WHERE id = $1
            """, uuid.UUID(task_id), str(e))

def build_comfyui_workflow(
    task_type: str,
    queen_name: str,
    queen_slug: str,
    base_prompt: str,
    seed: Optional[int] = None,
    index: int = 0
) -> dict:
    """Build ComfyUI workflow JSON"""
    import random

    if seed is None:
        seed = random.randint(0, 999999999)

    # Dimensions based on task type
    dimensions = {
        "portrait": (1024, 1024),
        "expression": (768, 768),
        "pose": (768, 1152),
        "explicit": (768, 1152)
    }
    width, height = dimensions.get(task_type, (1024, 1024))

    # Build prompt
    prompts = {
        "portrait": f"professional portrait photograph of {queen_name}, {base_prompt}, photorealistic, 8k uhd, studio lighting, sharp focus",
        "expression": f"close-up portrait of {queen_name}, expressive face, {base_prompt}, photorealistic, studio lighting",
        "pose": f"full body photograph of {queen_name}, elegant pose, {base_prompt}, fashion photography",
        "explicit": f"artistic intimate photograph of {queen_name}, sensual, {base_prompt}, professional lighting"
    }
    prompt = prompts.get(task_type, prompts["portrait"])

    negative = "deformed, ugly, bad anatomy, blurry, low quality, watermark, text, anime, cartoon, 3d render"

    return {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7,
                "sampler_name": "dpmpp_2m_sde_gpu",
                "scheduler": "karras",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {"ckpt_name": "RealVisXL_V5.0.safetensors"},
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {"text": prompt, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {"text": negative, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": f"empire/{queen_slug}/{task_type}/{index:04d}",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
