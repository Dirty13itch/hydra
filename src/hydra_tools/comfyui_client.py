"""
ComfyUI Client for Empire of Broken Queens Asset Generation

Provides utilities to:
- Load workflow templates
- Fill in template variables
- Queue generation jobs
- Monitor job status
- Retrieve generated images
"""

import json
import logging
import os
import random
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

from .config import get_config

logger = logging.getLogger(__name__)

# Template directory - check multiple possible locations
def _find_templates_dir():
    env_path = os.environ.get("COMFYUI_TEMPLATES_DIR")
    candidates = [
        Path(env_path) if env_path else None,  # Environment override
        Path("/data/comfyui/workflows"),  # Data directory (mounted in container)
        Path("/app/repo/config/comfyui/workflows"),  # Docker mounted repo
        Path(__file__).parent.parent.parent / "config" / "comfyui" / "workflows",  # Relative to source
    ]
    for p in candidates:
        if p and p.exists() and p.is_dir():
            logger.info(f"Using ComfyUI templates from: {p}")
            return p
    logger.warning(f"No ComfyUI templates found, using fallback: {candidates[1]}")
    return candidates[1]  # Default to data directory

TEMPLATES_DIR = _find_templates_dir()


class ComfyUIClient:
    """Client for interacting with ComfyUI API."""

    def __init__(self, comfyui_url: Optional[str] = None):
        config = get_config()
        self.base_url = comfyui_url or config.comfyui_url
        self.client = httpx.Client(timeout=60.0)

    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a workflow template from file."""
        template_path = TEMPLATES_DIR / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            return json.load(f)

    def fill_template(
        self,
        template: Dict[str, Any],
        variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Fill in template variables."""
        # Deep copy to avoid modifying original
        workflow = json.loads(json.dumps(template))

        # Remove metadata
        workflow.pop("_meta", None)

        # Replace variables in string values
        def replace_vars(obj):
            if isinstance(obj, str):
                for key, value in variables.items():
                    obj = obj.replace(f"{{{{{key}}}}}", str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_vars(item) for item in obj]
            return obj

        return replace_vars(workflow)

    def queue_prompt(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Queue a workflow for execution."""
        payload = {
            "prompt": workflow,
            "client_id": str(uuid.uuid4())
        }

        try:
            response = self.client.post(
                f"{self.base_url}/prompt",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id")
                logger.info(f"Queued prompt: {prompt_id}")
                return prompt_id
            else:
                logger.error(f"Failed to queue prompt: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history for a prompt."""
        try:
            response = self.client.get(f"{self.base_url}/history/{prompt_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting history: {e}")
        return {}

    def get_queue(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            response = self.client.get(f"{self.base_url}/queue")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting queue: {e}")
        return {"queue_running": [], "queue_pending": []}

    def generate_character_portrait(
        self,
        character_name: str,
        positive_prompt: str,
        negative_prompt: str = "",
        emotion: str = "neutral"
    ) -> Optional[str]:
        """Generate a character portrait using the template."""
        template = self.load_template("character_portrait_template")

        variables = {
            "CHARACTER_NAME": f"{character_name}_{emotion}",
            "POSITIVE_PROMPT": positive_prompt,
            "NEGATIVE_PROMPT": negative_prompt or "lowres, bad anatomy, bad hands",
            "SEED": str(random.randint(0, 2**32 - 1))  # Random seed for variety
        }

        workflow = self.fill_template(template, variables)
        return self.queue_prompt(workflow)

    def generate_background(
        self,
        scene_description: str,
        time_of_day: str = "day",
        scene_id: str = "scene"
    ) -> Optional[str]:
        """Generate a scene background using the template."""
        template = self.load_template("background_template")

        variables = {
            "SCENE_DESCRIPTION": scene_description,
            "TIME_OF_DAY": time_of_day,
            "OUTPUT_PATH": f"background_{scene_id}",
            "SEED": str(random.randint(0, 2**32 - 1))
        }

        workflow = self.fill_template(template, variables)
        return self.queue_prompt(workflow)


def build_portrait_prompt(character_data: Dict[str, Any], emotion: str = "neutral") -> str:
    """Build a detailed prompt from character data."""
    parts = []

    # Character basics
    display_name = character_data.get("display_name", "character")
    parts.append(f"portrait of {display_name}")

    # Appearance
    appearance = character_data.get("appearance", {})
    if appearance.get("hair_color"):
        parts.append(f"{appearance['hair_color']} hair")
    if appearance.get("hair_style"):
        parts.append(appearance["hair_style"])
    if appearance.get("eye_color"):
        parts.append(f"{appearance['eye_color']} eyes")
    if appearance.get("skin_tone"):
        parts.append(f"{appearance['skin_tone']} skin")

    # Distinguishing features
    features = appearance.get("distinguishing_features", [])
    if features:
        parts.extend(features[:3])  # Limit to 3 features

    # Emotion mapping
    emotion_prompts = {
        "neutral": "calm expression, serene",
        "happy": "smiling, joyful expression, bright eyes",
        "sad": "melancholic expression, downcast eyes, sorrowful",
        "angry": "angry expression, furrowed brow, intense gaze",
        "fearful": "frightened expression, wide eyes, tense",
        "surprised": "surprised expression, raised eyebrows, wide eyes",
        "loving": "loving gaze, soft smile, tender expression",
        "seductive": "alluring expression, half-lidded eyes, slight smirk",
        "determined": "determined expression, firm jaw, focused eyes",
        "pensive": "thoughtful expression, contemplative, distant gaze"
    }
    parts.append(emotion_prompts.get(emotion, emotion_prompts["neutral"]))

    # Wardrobe
    wardrobe = character_data.get("wardrobe", {})
    default_outfit = wardrobe.get("default", {})
    if default_outfit.get("description"):
        parts.append(default_outfit["description"])

    return ", ".join(parts)


# FastAPI router for ComfyUI endpoints
def create_comfyui_router():
    """Create FastAPI router for ComfyUI endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/comfyui", tags=["comfyui"])
    client = ComfyUIClient()

    class PortraitRequest(BaseModel):
        character_name: str
        positive_prompt: str
        negative_prompt: str = ""
        emotion: str = "neutral"

    class BackgroundRequest(BaseModel):
        scene_description: str
        time_of_day: str = "day"
        scene_id: str = "scene"

    @router.get("/queue")
    async def get_queue_status():
        """Get current ComfyUI queue status."""
        return client.get_queue()

    @router.get("/history/{prompt_id}")
    async def get_prompt_history(prompt_id: str):
        """Get execution history for a prompt."""
        return client.get_history(prompt_id)

    @router.post("/portrait")
    async def generate_portrait(request: PortraitRequest):
        """Generate a character portrait."""
        prompt_id = client.generate_character_portrait(
            character_name=request.character_name,
            positive_prompt=request.positive_prompt,
            negative_prompt=request.negative_prompt,
            emotion=request.emotion
        )

        if not prompt_id:
            raise HTTPException(status_code=500, detail="Failed to queue portrait")

        return {
            "status": "queued",
            "prompt_id": prompt_id,
            "character": request.character_name,
            "emotion": request.emotion
        }

    @router.post("/background")
    async def generate_background(request: BackgroundRequest):
        """Generate a scene background."""
        prompt_id = client.generate_background(
            scene_description=request.scene_description,
            time_of_day=request.time_of_day,
            scene_id=request.scene_id
        )

        if not prompt_id:
            raise HTTPException(status_code=500, detail="Failed to queue background")

        return {
            "status": "queued",
            "prompt_id": prompt_id,
            "scene_id": request.scene_id
        }

    @router.get("/templates")
    async def list_templates():
        """List available workflow templates."""
        templates = []
        if TEMPLATES_DIR.exists():
            for f in TEMPLATES_DIR.glob("*.json"):
                with open(f) as tf:
                    data = json.load(tf)
                    meta = data.get("_meta", {})
                    templates.append({
                        "name": f.stem,
                        "description": meta.get("description", ""),
                        "variables": list(meta.get("variables", {}).keys())
                    })
        return {"templates": templates}

    return router
