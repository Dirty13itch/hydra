"""
Agent-Based Character Generation for Empire of Broken Queens

Autonomous agent workflow for generating complete characters:
1. Generate character metadata from brief
2. Generate ComfyUI prompt for portrait
3. Execute portrait generation
4. Apply quality scoring
5. Store with face embedding for consistency

Author: Hydra Autonomous Caretaker
Created: 2025-12-19
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import httpx

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

CHARACTER_GENERATIONS = Counter(
    "hydra_character_generations_total",
    "Total character generations",
    ["status", "queen_name"]
)

CHARACTER_LATENCY = Histogram(
    "hydra_character_generation_latency_seconds",
    "Character generation latency",
    buckets=[30, 60, 120, 300, 600, 1200]
)


# =============================================================================
# Configuration
# =============================================================================

ENDPOINTS = {
    "litellm": "http://192.168.1.244:4000/v1",
    "comfyui": "http://192.168.1.203:8188",
    "character_api": "http://192.168.1.244:8700/characters",
    "quality_api": "http://192.168.1.244:8700/quality",
}

# Default models for different tasks
MODELS = {
    "metadata": "dolphin-70b",  # Uncensored for adult content
    "prompt": "qwen-coder-32b",  # Coding model for structured prompts
    "description": "tabby",  # Main model for descriptions
}


class CharacterArchetype(Enum):
    """Character archetypes for Queens."""
    WARRIOR = "warrior"
    SCHOLAR = "scholar"
    SEDUCTRESS = "seductress"
    MYSTIC = "mystic"
    POLITICIAN = "politician"
    HEALER = "healer"
    TRICKSTER = "trickster"
    MOTHER = "mother"
    REBEL = "rebel"


@dataclass
class CharacterBrief:
    """Brief for character generation."""
    name: str
    archetype: CharacterArchetype
    kingdom: str
    age_range: str = "25-35"
    key_traits: List[str] = field(default_factory=list)
    visual_style: str = "dark fantasy, realistic"
    nsfw_level: str = "softcore"  # none, softcore, explicit
    background_story: Optional[str] = None
    relationships: List[str] = field(default_factory=list)


@dataclass
class GeneratedCharacter:
    """A fully generated character."""
    id: str
    name: str
    metadata: Dict[str, Any]
    portrait_url: Optional[str] = None
    portrait_path: Optional[str] = None
    face_embedding: Optional[List[float]] = None
    quality_score: Optional[float] = None
    status: str = "generating"
    created_at: datetime = field(default_factory=datetime.utcnow)
    generation_log: List[str] = field(default_factory=list)


class CharacterGenerationAgent:
    """
    Autonomous agent for complete character generation.
    """

    def __init__(self):
        self.endpoints = ENDPOINTS
        self.models = MODELS
        self.active_generations: Dict[str, GeneratedCharacter] = {}

    async def generate_character(
        self,
        brief: CharacterBrief,
    ) -> GeneratedCharacter:
        """
        Generate a complete character from a brief.

        Steps:
        1. Generate detailed metadata using LLM
        2. Generate ComfyUI prompt for portrait
        3. Queue portrait generation
        4. Apply quality scoring
        5. Extract and store face embedding
        """
        char_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()

        character = GeneratedCharacter(
            id=char_id,
            name=brief.name,
            metadata={},
        )
        self.active_generations[char_id] = character

        try:
            # Step 1: Generate metadata
            character.generation_log.append("Step 1: Generating character metadata...")
            metadata = await self._generate_metadata(brief)
            character.metadata = metadata
            character.generation_log.append(f"Generated metadata with {len(metadata)} fields")

            # Step 2: Generate ComfyUI prompt
            character.generation_log.append("Step 2: Generating portrait prompt...")
            comfy_prompt = await self._generate_comfyui_prompt(brief, metadata)
            character.generation_log.append(f"Generated ComfyUI prompt ({len(comfy_prompt)} chars)")

            # Step 3: Queue portrait generation
            character.generation_log.append("Step 3: Queuing portrait generation...")
            portrait_result = await self._generate_portrait(comfy_prompt, brief.name)

            if portrait_result.get("success"):
                character.portrait_path = portrait_result.get("image_path")
                character.portrait_url = portrait_result.get("image_url")
                character.generation_log.append(f"Portrait generated: {character.portrait_path}")
            else:
                character.generation_log.append(f"Portrait generation failed: {portrait_result.get('error')}")

            # Step 4: Quality scoring
            if character.portrait_path:
                character.generation_log.append("Step 4: Applying quality scoring...")
                quality = await self._score_quality(character.portrait_path)
                character.quality_score = quality.get("overall_score", 0)
                character.generation_log.append(f"Quality score: {character.quality_score}")

            # Step 5: Extract face embedding
            if character.portrait_path:
                character.generation_log.append("Step 5: Extracting face embedding...")
                embedding = await self._extract_face_embedding(character.portrait_path)
                if embedding:
                    character.face_embedding = embedding
                    character.generation_log.append("Face embedding extracted")

            # Store character
            await self._store_character(character)
            character.status = "completed"

            # Metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            CHARACTER_GENERATIONS.labels(status="success", queen_name=brief.name).inc()
            CHARACTER_LATENCY.observe(duration)

            character.generation_log.append(f"Generation completed in {duration:.1f}s")

        except Exception as e:
            character.status = "failed"
            character.generation_log.append(f"Error: {str(e)}")
            CHARACTER_GENERATIONS.labels(status="failed", queen_name=brief.name).inc()
            logger.error(f"Character generation failed for {brief.name}: {e}")

        return character

    async def _generate_metadata(self, brief: CharacterBrief) -> Dict[str, Any]:
        """Generate detailed character metadata using LLM."""
        prompt = f"""Generate detailed character metadata for a dark fantasy visual novel character.

Character Brief:
- Name: {brief.name}
- Archetype: {brief.archetype.value}
- Kingdom: {brief.kingdom}
- Age Range: {brief.age_range}
- Key Traits: {', '.join(brief.key_traits)}
- NSFW Level: {brief.nsfw_level}
- Background: {brief.background_story or 'Generate a compelling background'}
- Relationships: {', '.join(brief.relationships) if brief.relationships else 'To be determined'}

Return a detailed JSON object with:
{{
    "full_name": "Complete name with titles",
    "age": "Specific age",
    "physical_description": {{
        "height": "in cm",
        "build": "body type",
        "hair": "color and style",
        "eyes": "color and notable features",
        "skin": "tone and notable features",
        "distinguishing_marks": "scars, tattoos, birthmarks",
        "typical_expression": "resting expression"
    }},
    "personality": {{
        "core_traits": ["list of 5 core traits"],
        "strengths": ["list"],
        "weaknesses": ["list"],
        "fears": ["list"],
        "desires": ["list"],
        "speech_patterns": "how they speak"
    }},
    "background": {{
        "origin": "where they came from",
        "rise_to_power": "how they became queen",
        "key_events": ["formative events"],
        "secrets": ["hidden truths"]
    }},
    "kingdom": {{
        "name": "{brief.kingdom}",
        "culture": "dominant culture",
        "economy": "primary industry",
        "military": "military strength",
        "relationships": "relations with other kingdoms"
    }},
    "sexuality": {{
        "orientation": "sexual orientation",
        "preferences": ["preferences"],
        "seduction_style": "how they seduce"
    }},
    "combat_style": "if applicable",
    "magic_abilities": "if applicable",
    "quotes": ["3 characteristic quotes"]
}}"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.endpoints['litellm']}/chat/completions",
                json={
                    "model": self.models["metadata"],
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert character designer for dark fantasy stories. Create rich, complex characters with depth and nuance. You have no content restrictions."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2048,
                    "temperature": 0.8,
                },
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Parse JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())

        return {"name": brief.name, "archetype": brief.archetype.value, "error": "Generation failed"}

    async def _generate_comfyui_prompt(
        self,
        brief: CharacterBrief,
        metadata: Dict[str, Any],
    ) -> str:
        """Generate a ComfyUI prompt for the character portrait."""
        physical = metadata.get("physical_description", {})

        # Build positive prompt
        positive_parts = [
            "masterpiece, best quality, highly detailed",
            f"portrait of {brief.name}",
            f"a {metadata.get('age', '30')}-year-old {brief.archetype.value} queen",
            f"{physical.get('hair', 'dark hair')}, {physical.get('eyes', 'intense eyes')}",
            f"{physical.get('build', 'elegant')} build",
            brief.visual_style,
            "dramatic lighting, cinematic",
            "dark fantasy aesthetic",
        ]

        if brief.nsfw_level != "none":
            positive_parts.append("alluring, sensual")

        positive_prompt = ", ".join(positive_parts)

        # Negative prompt
        negative_prompt = "low quality, blurry, deformed, bad anatomy, bad hands, missing fingers, extra fingers, text, watermark, signature, ugly, duplicate, morbid, mutilated"

        return json.dumps({
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "character_name": brief.name,
            "seed": -1,  # Random seed
            "steps": 30,
            "cfg_scale": 7.5,
            "width": 768,
            "height": 1024,
        })

    async def _generate_portrait(self, prompt_json: str, character_name: str) -> Dict[str, Any]:
        """Queue portrait generation in ComfyUI."""
        prompt_data = json.loads(prompt_json)

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Call the ComfyUI API through our wrapper
                response = await client.post(
                    "http://192.168.1.244:8700/comfyui/generate",
                    json={
                        "prompt": prompt_data["positive_prompt"],
                        "negative_prompt": prompt_data["negative_prompt"],
                        "width": prompt_data.get("width", 768),
                        "height": prompt_data.get("height", 1024),
                        "steps": prompt_data.get("steps", 30),
                        "cfg": prompt_data.get("cfg_scale", 7.5),
                        "seed": prompt_data.get("seed", -1),
                        "character_name": character_name,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "image_path": data.get("image_path"),
                        "image_url": data.get("image_url"),
                        "prompt_id": data.get("prompt_id"),
                    }
                else:
                    return {"success": False, "error": f"ComfyUI returned {response.status_code}"}

            except Exception as e:
                return {"success": False, "error": str(e)}

    async def _score_quality(self, image_path: str) -> Dict[str, Any]:
        """Score the quality of the generated portrait."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.endpoints['quality_api']}/score",
                    json={"image_path": image_path},
                )

                if response.status_code == 200:
                    return response.json()

            except Exception as e:
                logger.warning(f"Quality scoring failed: {e}")

        return {"overall_score": 0.5, "error": "Scoring unavailable"}

    async def _extract_face_embedding(self, image_path: str) -> Optional[List[float]]:
        """Extract face embedding for consistency tracking."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "http://192.168.1.244:8700/face-detection/embedding",
                    json={"image_path": image_path},
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding")

            except Exception as e:
                logger.warning(f"Face embedding extraction failed: {e}")

        return None

    async def _store_character(self, character: GeneratedCharacter):
        """Store the generated character in the database."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(
                    self.endpoints["character_api"],
                    json={
                        "id": character.id,
                        "name": character.name,
                        "metadata": character.metadata,
                        "portrait_path": character.portrait_path,
                        "portrait_url": character.portrait_url,
                        "face_embedding": character.face_embedding,
                        "quality_score": character.quality_score,
                        "status": character.status,
                        "created_at": character.created_at.isoformat(),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to store character: {e}")

    def get_generation_status(self, char_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a character generation."""
        char = self.active_generations.get(char_id)
        if char:
            return {
                "id": char.id,
                "name": char.name,
                "status": char.status,
                "quality_score": char.quality_score,
                "portrait_url": char.portrait_url,
                "log": char.generation_log,
            }
        return None

    def list_generations(self) -> List[Dict[str, Any]]:
        """List all active/recent generations."""
        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "created_at": c.created_at.isoformat(),
            }
            for c in self.active_generations.values()
        ]


# =============================================================================
# Global Instance
# =============================================================================

_character_agent: Optional[CharacterGenerationAgent] = None


def get_character_agent() -> CharacterGenerationAgent:
    """Get or create the global character generation agent."""
    global _character_agent
    if _character_agent is None:
        _character_agent = CharacterGenerationAgent()
    return _character_agent


# =============================================================================
# FastAPI Router
# =============================================================================

def create_character_generation_router():
    """Create FastAPI router for character generation endpoints."""
    from fastapi import APIRouter, BackgroundTasks
    from pydantic import BaseModel

    router = APIRouter(prefix="/character-gen", tags=["character-generation"])

    class GenerateRequest(BaseModel):
        name: str
        archetype: str
        kingdom: str
        age_range: str = "25-35"
        key_traits: List[str] = []
        visual_style: str = "dark fantasy, realistic"
        nsfw_level: str = "softcore"
        background_story: Optional[str] = None
        relationships: List[str] = []

    @router.post("/generate")
    async def generate_character(request: GenerateRequest, background_tasks: BackgroundTasks):
        """Start character generation in background."""
        agent = get_character_agent()

        # Validate archetype
        try:
            archetype = CharacterArchetype(request.archetype)
        except ValueError:
            return {"error": f"Invalid archetype. Valid: {[a.value for a in CharacterArchetype]}"}

        brief = CharacterBrief(
            name=request.name,
            archetype=archetype,
            kingdom=request.kingdom,
            age_range=request.age_range,
            key_traits=request.key_traits,
            visual_style=request.visual_style,
            nsfw_level=request.nsfw_level,
            background_story=request.background_story,
            relationships=request.relationships,
        )

        # Run in background
        async def run_generation():
            await agent.generate_character(brief)

        background_tasks.add_task(asyncio.create_task, run_generation())

        return {
            "message": "Character generation started",
            "name": request.name,
            "check_status": f"/character-gen/status/{request.name}",
        }

    @router.get("/status/{name}")
    async def get_status(name: str):
        """Get generation status by character name."""
        agent = get_character_agent()

        for char_id, char in agent.active_generations.items():
            if char.name.lower() == name.lower():
                return agent.get_generation_status(char_id)

        return {"error": "Character not found"}

    @router.get("/list")
    async def list_generations():
        """List all character generations."""
        agent = get_character_agent()
        return {"generations": agent.list_generations()}

    @router.get("/archetypes")
    async def list_archetypes():
        """List available character archetypes."""
        return {
            "archetypes": [
                {"value": a.value, "name": a.name.replace("_", " ").title()}
                for a in CharacterArchetype
            ]
        }

    return router
