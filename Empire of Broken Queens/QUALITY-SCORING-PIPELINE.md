# Empire of Broken Queens - Quality Scoring Pipeline

## Overview

Automated quality assessment and approval pipeline for generated assets using multiple AI scoring models.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        QUALITY SCORING PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │   ComfyUI    │────▶│  Generated   │────▶│   Quality    │               │
│   │  Generation  │     │    Image     │     │   Scorer     │               │
│   └──────────────┘     └──────────────┘     └──────┬───────┘               │
│                                                     │                        │
│                        ┌────────────────────────────┼────────────────────┐  │
│                        │                            ▼                    │  │
│                        │    ┌─────────────────────────────────────────┐ │  │
│                        │    │           SCORING MODELS                │ │  │
│                        │    ├─────────────────────────────────────────┤ │  │
│                        │    │ 1. Aesthetic Score (LAION)    [0-1]     │ │  │
│                        │    │ 2. Technical Score (MUSIQ)    [0-1]     │ │  │
│                        │    │ 3. Face Match Score (ArcFace) [0-1]     │ │  │
│                        │    │ 4. NSFW Detection (clip)      [safe/nsfw]│ │  │
│                        │    └─────────────────────────────────────────┘ │  │
│                        │                            │                    │  │
│                        └────────────────────────────┼────────────────────┘  │
│                                                     │                        │
│                                                     ▼                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                        COMPOSITE SCORE                                │  │
│   │   = (aesthetic × 0.4) + (technical × 0.3) + (face_match × 0.3)       │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                     │                        │
│                                                     ▼                        │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                     APPROVAL DECISION                                 │  │
│   │   composite >= 0.80  →  AUTO_APPROVE                                 │  │
│   │   composite >= 0.65  →  PENDING_REVIEW                               │  │
│   │   composite <  0.65  →  AUTO_REJECT                                  │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Scoring Models

### 1. Aesthetic Score (LAION Aesthetics Predictor)

**Model:** `LAION-Aesthetics-Predictor-V2`
**Input:** Image
**Output:** Score 0-10 (normalized to 0-1)

Evaluates overall visual appeal based on:
- Composition
- Color harmony
- Lighting
- Professional quality

```python
from transformers import pipeline

aesthetic_predictor = pipeline(
    "image-classification",
    model="cafeai/cafe_aesthetic",
    device=0
)

def score_aesthetic(image_path: str) -> float:
    result = aesthetic_predictor(image_path)
    # Returns score normalized to 0-1
    return result[0]['score']
```

### 2. Technical Score (MUSIQ - Multi-Scale Image Quality)

**Model:** `google/musiq-paq2piq`
**Input:** Image
**Output:** Score 0-100 (normalized to 0-1)

Evaluates technical quality:
- Sharpness/blur detection
- Noise levels
- Compression artifacts
- Resolution quality

```python
import torch
from PIL import Image
import timm

musiq_model = timm.create_model('musiq-paq2piq', pretrained=True)

def score_technical(image_path: str) -> float:
    image = Image.open(image_path)
    # Process and score
    with torch.no_grad():
        score = musiq_model(preprocess(image))
    return score.item() / 100  # Normalize to 0-1
```

### 3. Face Match Score (ArcFace/InsightFace)

**Model:** `buffalo_l` from InsightFace
**Input:** Generated image + Reference image
**Output:** Cosine similarity 0-1

Ensures generated face matches reference queen:
- Face detection
- Embedding extraction
- Cosine similarity comparison

```python
import insightface
from insightface.app import FaceAnalysis

face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
face_app.prepare(ctx_id=0)

def score_face_match(generated_path: str, reference_embedding: np.ndarray) -> float:
    img = cv2.imread(generated_path)
    faces = face_app.get(img)

    if len(faces) == 0:
        return 0.0  # No face detected

    # Get embedding of largest face
    face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3])
    generated_embedding = face.embedding

    # Cosine similarity
    similarity = np.dot(generated_embedding, reference_embedding) / (
        np.linalg.norm(generated_embedding) * np.linalg.norm(reference_embedding)
    )
    return float(similarity)
```

### 4. NSFW Detection (Optional - for content categorization)

**Model:** `Falconsai/nsfw_image_detection`
**Input:** Image
**Output:** Classification (safe/nsfw/explicit)

Used for proper asset categorization, not rejection.

## Implementation

### Quality Scoring Service

```python
# quality_service.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import numpy as np
from typing import Optional

app = FastAPI(title="Empire Quality Scoring Service")

# Model instances (loaded on startup)
aesthetic_model = None
technical_model = None
face_app = None

class ScoreRequest(BaseModel):
    image_path: str
    queen_slug: str
    reference_embedding_id: Optional[str] = None

class ScoreResponse(BaseModel):
    aesthetic_score: float
    technical_score: float
    face_match_score: float
    composite_score: float
    approved: bool
    approval_method: str
    rejection_reason: Optional[str] = None

# Thresholds from database config
THRESHOLDS = {
    "aesthetic_min": 0.6,
    "technical_min": 0.7,
    "face_match_min": 0.75,
    "composite_min": 0.65,
    "auto_approve": 0.80
}

@app.post("/score", response_model=ScoreResponse)
async def score_image(request: ScoreRequest):
    # Run scoring models in parallel
    aesthetic, technical, face_match = await asyncio.gather(
        run_aesthetic_score(request.image_path),
        run_technical_score(request.image_path),
        run_face_match_score(request.image_path, request.queen_slug)
    )

    # Calculate composite score
    composite = (aesthetic * 0.4) + (technical * 0.3) + (face_match * 0.3)

    # Determine approval
    approved = False
    approval_method = "auto"
    rejection_reason = None

    if composite >= THRESHOLDS["auto_approve"]:
        approved = True
        approval_method = "auto"
    elif composite >= THRESHOLDS["composite_min"]:
        approval_method = "pending"  # Needs manual review
    else:
        approval_method = "auto"
        # Determine rejection reason
        if aesthetic < THRESHOLDS["aesthetic_min"]:
            rejection_reason = "Low aesthetic quality"
        elif technical < THRESHOLDS["technical_min"]:
            rejection_reason = "Technical issues (blur/noise)"
        elif face_match < THRESHOLDS["face_match_min"]:
            rejection_reason = "Face mismatch"
        else:
            rejection_reason = "Below quality threshold"

    return ScoreResponse(
        aesthetic_score=aesthetic,
        technical_score=technical,
        face_match_score=face_match,
        composite_score=composite,
        approved=approved,
        approval_method=approval_method,
        rejection_reason=rejection_reason
    )

async def run_aesthetic_score(image_path: str) -> float:
    # Run in thread pool to not block async
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, score_aesthetic, image_path)

async def run_technical_score(image_path: str) -> float:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, score_technical, image_path)

async def run_face_match_score(image_path: str, queen_slug: str) -> float:
    # Get reference embedding from Qdrant
    reference = await get_queen_reference_embedding(queen_slug)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, score_face_match, image_path, reference)

async def get_queen_reference_embedding(queen_slug: str) -> np.ndarray:
    # Fetch from Qdrant empire_faces collection
    from qdrant_client import QdrantClient

    client = QdrantClient(host="192.168.1.244", port=6333)
    results = client.scroll(
        collection_name="empire_faces",
        scroll_filter={"must": [{"key": "queen_slug", "match": {"value": queen_slug}}]},
        limit=1,
        with_vectors=True
    )

    if results[0]:
        return np.array(results[0][0].vector)

    raise HTTPException(status_code=404, detail=f"No reference embedding for {queen_slug}")
```

### Batch Scoring Endpoint

```python
@app.post("/score/batch")
async def score_batch(requests: list[ScoreRequest]):
    """Score multiple images in parallel"""
    tasks = [score_image(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "results": [r if not isinstance(r, Exception) else {"error": str(r)} for r in results],
        "summary": {
            "total": len(results),
            "approved": sum(1 for r in results if hasattr(r, 'approved') and r.approved),
            "pending": sum(1 for r in results if hasattr(r, 'approval_method') and r.approval_method == 'pending'),
            "rejected": sum(1 for r in results if hasattr(r, 'approved') and not r.approved and r.approval_method == 'auto')
        }
    }
```

## Integration with Generation Pipeline

### n8n Workflow Integration

```javascript
// In n8n Code node after generation completes
const scoringServiceUrl = "http://192.168.1.244:8090";

const imageFiles = $input.all().map(item => item.json.output_path);

// Score all images
const scoreResults = await Promise.all(
  imageFiles.map(async (path) => {
    const response = await fetch(`${scoringServiceUrl}/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_path: path,
        queen_slug: $('Split for Dual GPU').first().json.queen_slug
      })
    });
    return response.json();
  })
);

// Update database with scores
// Approved images -> move to approved folder
// Rejected images -> move to rejected folder with reason
```

### ComfyUI Post-Processing Node (Optional)

Custom ComfyUI node that auto-scores output before saving:

```python
class EmpireQualityGate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "queen_slug": ("STRING", {"default": ""}),
                "min_score": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("image", "quality_score", "approved")
    FUNCTION = "quality_gate"
    CATEGORY = "Empire"

    def quality_gate(self, image, queen_slug, min_score):
        # Call quality service
        score = self.get_quality_score(image, queen_slug)
        approved = score >= min_score
        return (image, score, approved)
```

## Database Integration

### Store Scores with Assets

```sql
-- When asset is scored
UPDATE generated_assets
SET
    aesthetic_score = $1,
    technical_score = $2,
    face_match_score = $3,
    composite_score = $4,
    approved = $5,
    approval_method = $6,
    rejection_reason = $7,
    reviewed_at = NOW()
WHERE id = $8;
```

### Quality Metrics Aggregation

```sql
-- Aggregate quality metrics for reporting
INSERT INTO quality_metrics (
    period_start, period_end, granularity,
    queen_id, queen_slug, task_type,
    total_generated, total_approved, total_rejected,
    approval_rate,
    aesthetic_scores, technical_scores, face_match_scores,
    rejection_breakdown
)
SELECT
    date_trunc('hour', generated_at) as period_start,
    date_trunc('hour', generated_at) + interval '1 hour' as period_end,
    'hourly' as granularity,
    queen_id, queen_slug, asset_type,
    COUNT(*) as total_generated,
    COUNT(*) FILTER (WHERE approved) as total_approved,
    COUNT(*) FILTER (WHERE NOT approved) as total_rejected,
    COUNT(*) FILTER (WHERE approved)::numeric / COUNT(*)::numeric as approval_rate,
    jsonb_build_object(
        'min', MIN(aesthetic_score),
        'max', MAX(aesthetic_score),
        'avg', AVG(aesthetic_score)
    ) as aesthetic_scores,
    jsonb_build_object(
        'min', MIN(technical_score),
        'max', MAX(technical_score),
        'avg', AVG(technical_score)
    ) as technical_scores,
    jsonb_build_object(
        'min', MIN(face_match_score),
        'max', MAX(face_match_score),
        'avg', AVG(face_match_score)
    ) as face_match_scores,
    jsonb_object_agg(
        COALESCE(rejection_reason, 'approved'),
        count
    ) as rejection_breakdown
FROM generated_assets
WHERE generated_at >= NOW() - interval '1 hour'
GROUP BY
    date_trunc('hour', generated_at),
    queen_id, queen_slug, asset_type;
```

## Reference Embedding Management

### Creating Queen Reference Embeddings

```python
async def create_queen_reference(queen_slug: str, reference_images: list[str]):
    """
    Create reference embedding from multiple images of a queen.
    Average embeddings from best reference photos.
    """
    embeddings = []

    for image_path in reference_images:
        img = cv2.imread(image_path)
        faces = face_app.get(img)

        if faces:
            # Get largest face
            face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3])
            embeddings.append(face.embedding)

    if not embeddings:
        raise ValueError("No faces detected in reference images")

    # Average all embeddings
    reference_embedding = np.mean(embeddings, axis=0)

    # Store in Qdrant
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    client = QdrantClient(host="192.168.1.244", port=6333)

    client.upsert(
        collection_name="empire_faces",
        points=[
            PointStruct(
                id=queen_slug,
                vector=reference_embedding.tolist(),
                payload={"queen_slug": queen_slug, "source_images": reference_images}
            )
        ]
    )

    return {"queen_slug": queen_slug, "embedding_created": True}
```

## Deployment

### Docker Compose

```yaml
services:
  empire-quality:
    build:
      context: ./quality
      dockerfile: Dockerfile
    container_name: empire-quality-service
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - QDRANT_URL=http://192.168.1.244:6333
      - DATABASE_URL=postgresql://hydra:hydra@192.168.1.244:5432/empire_of_broken_queens
    volumes:
      - /mnt/models:/models:ro
      - /mnt/user/hydra_shared/comfyui_output:/output:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - hydra-network
```

### Resource Requirements

| Model | VRAM | Notes |
|-------|------|-------|
| Aesthetic (LAION) | ~500MB | Lightweight |
| Technical (MUSIQ) | ~200MB | Lightweight |
| Face (InsightFace) | ~1.5GB | buffalo_l model |
| **Total** | **~2.5GB** | Can run on any GPU |

**Recommended deployment:** Run on hydra-compute alongside ComfyUI - plenty of VRAM headroom.

## Thresholds Configuration

Stored in `generation_config` table:

```sql
UPDATE generation_config
SET value = '{
    "aesthetic_min": 0.6,
    "technical_min": 0.7,
    "face_match_min": 0.75,
    "composite_min": 0.65,
    "auto_approve_threshold": 0.8
}'
WHERE key = 'quality_thresholds';
```

Adjustable per-queen if needed by storing in queen's `generation_config` JSON.

---

*Quality Scoring Pipeline v1.0*
*Generated: December 12, 2025*
