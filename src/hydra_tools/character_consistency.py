"""
Character Consistency System for Empire of Broken Queens

Phase 12 module providing character reference management, style consistency,
and asset generation coordination for visual novel production.

Features:
- Character reference database (Qdrant vector storage)
- Face embedding extraction and matching
- Style guide management
- ComfyUI workflow integration
- Script parsing and scene extraction
- Voice profile management for TTS
"""

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import get_config

logger = logging.getLogger(__name__)


class EmotionTag(Enum):
    """Standard emotion tags for characters."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    CONTEMPTUOUS = "contemptuous"
    LOVING = "loving"
    SEDUCTIVE = "seductive"
    PENSIVE = "pensive"
    DETERMINED = "determined"


class PoseType(Enum):
    """Standard pose types for character art."""
    PORTRAIT = "portrait"  # Head/shoulders
    BUST = "bust"  # Upper body
    FULL = "full"  # Full body
    ACTION = "action"  # Dynamic pose
    SITTING = "sitting"
    LYING = "lying"


@dataclass
class CharacterReference:
    """A character reference with embeddings and metadata."""
    id: str
    name: str
    display_name: str
    description: str
    face_embedding: Optional[List[float]] = None
    style_embedding: Optional[List[float]] = None

    # Visual characteristics
    hair_color: str = ""
    hair_style: str = ""
    eye_color: str = ""
    skin_tone: str = ""
    distinguishing_features: List[str] = field(default_factory=list)

    # Reference images
    reference_images: List[str] = field(default_factory=list)  # paths

    # Voice profile
    voice_id: Optional[str] = None
    voice_characteristics: Dict[str, Any] = field(default_factory=dict)

    # Outfit variations
    outfits: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)

    # Metadata
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "eye_color": self.eye_color,
            "skin_tone": self.skin_tone,
            "distinguishing_features": self.distinguishing_features,
            "reference_images": self.reference_images,
            "voice_id": self.voice_id,
            "voice_characteristics": self.voice_characteristics,
            "outfits": self.outfits,
            "relationships": self.relationships,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SceneDescription:
    """A parsed scene from a visual novel script."""
    id: str
    chapter: int
    scene_number: int
    location: str
    time_of_day: str
    characters: List[str]
    character_emotions: Dict[str, EmotionTag]
    character_poses: Dict[str, PoseType]
    dialogue: List[Dict[str, str]]
    narration: str
    background_description: str
    music_cue: Optional[str] = None
    sound_effects: List[str] = field(default_factory=list)


class CharacterManager:
    """Manages character references in Qdrant."""

    FACE_COLLECTION = "empire_faces"
    IMAGE_COLLECTION = "empire_images"
    FACE_DIM = 512
    IMAGE_DIM = 768

    def __init__(self, qdrant_url: Optional[str] = None):
        config = get_config()
        self.qdrant_url = qdrant_url or config.qdrant_url
        self.client = httpx.Client(timeout=30.0)

    def _ensure_collections(self) -> None:
        """Ensure required collections exist."""
        for collection, dim in [
            (self.FACE_COLLECTION, self.FACE_DIM),
            (self.IMAGE_COLLECTION, self.IMAGE_DIM),
        ]:
            try:
                resp = self.client.get(f"{self.qdrant_url}/collections/{collection}")
                if resp.status_code == 404:
                    self._create_collection(collection, dim)
            except Exception as e:
                logger.error(f"Error checking collection {collection}: {e}")

    def _create_collection(self, name: str, dim: int) -> None:
        """Create a Qdrant collection."""
        payload = {
            "vectors": {
                "size": dim,
                "distance": "Cosine"
            }
        }
        try:
            resp = self.client.put(
                f"{self.qdrant_url}/collections/{name}",
                json=payload
            )
            if resp.status_code in (200, 201):
                logger.info(f"Created collection {name}")
            else:
                logger.error(f"Failed to create collection {name}: {resp.text}")
        except Exception as e:
            logger.error(f"Error creating collection {name}: {e}")

    def add_character(self, character: CharacterReference) -> bool:
        """Add a character reference to the database."""
        self._ensure_collections()

        timestamp = datetime.utcnow().isoformat()
        if not character.created_at:
            character.created_at = timestamp
        character.updated_at = timestamp

        # Always store character metadata (with placeholder vector if no face embedding)
        face_vector = character.face_embedding or [0.0] * self.FACE_DIM
        metadata_point = {
            "id": str(uuid.uuid4()),
            "vector": face_vector,
            "payload": {
                "character_id": character.id,
                "character_name": character.name,
                "type": "metadata" if not character.face_embedding else "face",
                "has_face_embedding": bool(character.face_embedding),
                **character.to_dict()
            }
        }
        try:
            resp = self.client.put(
                f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points",
                json={"points": [metadata_point]}
            )
            if resp.status_code not in (200, 201):
                logger.error(f"Failed to store character metadata: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error storing character metadata: {e}")
            return False

        # Store face embedding if provided (separate point for actual face matching)
        if character.face_embedding:
            face_point = {
                "id": str(uuid.uuid4()),
                "vector": character.face_embedding,
                "payload": {
                    "character_id": character.id,
                    "character_name": character.name,
                    "type": "face",
                    **character.to_dict()
                }
            }
            try:
                resp = self.client.put(
                    f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points",
                    json={"points": [face_point]}
                )
                if resp.status_code not in (200, 201):
                    logger.error(f"Failed to store face embedding: {resp.text}")
                    return False
            except Exception as e:
                logger.error(f"Error storing face embedding: {e}")
                return False

        # Store style embedding if provided
        if character.style_embedding:
            style_point = {
                "id": str(uuid.uuid4()),
                "vector": character.style_embedding,
                "payload": {
                    "character_id": character.id,
                    "character_name": character.name,
                    "type": "style",
                    **character.to_dict()
                }
            }
            try:
                resp = self.client.put(
                    f"{self.qdrant_url}/collections/{self.IMAGE_COLLECTION}/points",
                    json={"points": [style_point]}
                )
                if resp.status_code not in (200, 201):
                    logger.error(f"Failed to store style embedding: {resp.text}")
                    return False
            except Exception as e:
                logger.error(f"Error storing style embedding: {e}")
                return False

        logger.info(f"Added character {character.name} ({character.id})")
        return True

    def get_character(self, character_id: str) -> Optional[CharacterReference]:
        """Retrieve a character by ID."""
        filter_query = {
            "filter": {
                "must": [
                    {"key": "character_id", "match": {"value": character_id}}
                ]
            },
            "limit": 1,
            "with_payload": True
        }

        try:
            resp = self.client.post(
                f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points/scroll",
                json=filter_query
            )
            if resp.status_code == 200:
                data = resp.json()
                points = data.get("result", {}).get("points", [])
                if points:
                    payload = points[0].get("payload", {})
                    return self._payload_to_character(payload)
        except Exception as e:
            logger.error(f"Error retrieving character {character_id}: {e}")

        return None

    def update_character_references(
        self,
        character_id: str,
        reference_images: List[str]
    ) -> bool:
        """Update a character's reference images."""
        # Get existing character
        character = self.get_character(character_id)
        if not character:
            logger.error(f"Character {character_id} not found")
            return False

        # Delete existing points for this character
        try:
            resp = self.client.post(
                f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "character_id", "match": {"value": character_id}}
                        ]
                    }
                }
            )
            if resp.status_code not in (200, 201):
                logger.error(f"Failed to delete old character points: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error deleting character points: {e}")
            return False

        # Update reference images and re-add
        character.reference_images = reference_images
        return self.add_character(character)

    def find_similar_faces(
        self,
        face_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Tuple[CharacterReference, float]]:
        """Find characters with similar faces."""
        query = {
            "vector": face_embedding,
            "limit": limit,
            "with_payload": True,
            "score_threshold": score_threshold
        }

        results = []
        try:
            resp = self.client.post(
                f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points/search",
                json=query
            )
            if resp.status_code == 200:
                data = resp.json()
                for point in data.get("result", []):
                    payload = point.get("payload", {})
                    score = point.get("score", 0)
                    char = self._payload_to_character(payload)
                    if char:
                        results.append((char, score))
        except Exception as e:
            logger.error(f"Error searching faces: {e}")

        return results

    def list_characters(self) -> List[CharacterReference]:
        """List all characters."""
        characters = []

        try:
            resp = self.client.post(
                f"{self.qdrant_url}/collections/{self.FACE_COLLECTION}/points/scroll",
                json={"limit": 100, "with_payload": True}
            )
            if resp.status_code == 200:
                data = resp.json()
                seen_ids = set()
                for point in data.get("result", {}).get("points", []):
                    payload = point.get("payload", {})
                    char_id = payload.get("character_id")
                    if char_id and char_id not in seen_ids:
                        seen_ids.add(char_id)
                        char = self._payload_to_character(payload)
                        if char:
                            characters.append(char)
        except Exception as e:
            logger.error(f"Error listing characters: {e}")

        return characters

    def _payload_to_character(self, payload: Dict) -> Optional[CharacterReference]:
        """Convert Qdrant payload to CharacterReference."""
        try:
            return CharacterReference(
                id=payload.get("character_id", ""),
                name=payload.get("character_name", payload.get("name", "")),
                display_name=payload.get("display_name", ""),
                description=payload.get("description", ""),
                hair_color=payload.get("hair_color", ""),
                hair_style=payload.get("hair_style", ""),
                eye_color=payload.get("eye_color", ""),
                skin_tone=payload.get("skin_tone", ""),
                distinguishing_features=payload.get("distinguishing_features", []),
                reference_images=payload.get("reference_images", []),
                voice_id=payload.get("voice_id"),
                voice_characteristics=payload.get("voice_characteristics", {}),
                outfits=payload.get("outfits", {}),
                relationships=payload.get("relationships", {}),
                created_at=payload.get("created_at", ""),
                updated_at=payload.get("updated_at", ""),
            )
        except Exception as e:
            logger.error(f"Error parsing character payload: {e}")
            return None


class ScriptParser:
    """Parses visual novel scripts into structured scenes."""

    # Pattern for scene headers: ## Scene 1: Location - Time
    SCENE_PATTERN = re.compile(
        r'^##\s*Scene\s*(\d+):\s*(.+?)(?:\s*-\s*(.+))?$',
        re.MULTILINE
    )

    # Pattern for dialogue: **Character** (emotion): "dialogue"
    DIALOGUE_PATTERN = re.compile(
        r'\*\*([^*]+)\*\*(?:\s*\(([^)]+)\))?\s*:\s*"([^"]+)"'
    )

    # Pattern for narration blocks
    NARRATION_PATTERN = re.compile(r'^\*([^*]+)\*$', re.MULTILINE)

    # Pattern for character entrance: [Enter CHARACTER]
    ENTRANCE_PATTERN = re.compile(r'\[Enter\s+([^\]]+)\]', re.IGNORECASE)

    # Pattern for background: [Background: description]
    BACKGROUND_PATTERN = re.compile(r'\[Background:\s*([^\]]+)\]', re.IGNORECASE)

    # Pattern for music: [Music: cue]
    MUSIC_PATTERN = re.compile(r'\[Music:\s*([^\]]+)\]', re.IGNORECASE)

    def __init__(self, character_manager: Optional[CharacterManager] = None):
        self.character_manager = character_manager or CharacterManager()
        self.known_characters = {
            c.name.lower(): c for c in self.character_manager.list_characters()
        }

    def parse_script(self, script_text: str, chapter: int = 1) -> List[SceneDescription]:
        """Parse a script into scenes."""
        scenes = []

        # Split by scene headers
        scene_splits = self.SCENE_PATTERN.split(script_text)

        # First element is prologue/intro text before first scene
        if scene_splits and not scene_splits[0].strip():
            scene_splits = scene_splits[1:]

        # Process scenes in groups of 4: (number, location, time, content)
        i = 0
        while i < len(scene_splits) - 3:
            scene_num = int(scene_splits[i])
            location = scene_splits[i + 1].strip()
            time_of_day = scene_splits[i + 2].strip() if scene_splits[i + 2] else "day"
            content = scene_splits[i + 3] if i + 3 < len(scene_splits) else ""

            scene = self._parse_scene_content(
                content, chapter, scene_num, location, time_of_day
            )
            scenes.append(scene)
            i += 4

        return scenes

    def _parse_scene_content(
        self,
        content: str,
        chapter: int,
        scene_num: int,
        location: str,
        time_of_day: str
    ) -> SceneDescription:
        """Parse scene content into structured data."""
        characters = set()
        character_emotions = {}
        character_poses = {}
        dialogue = []
        narration_parts = []
        background = ""
        music = None
        sfx = []

        # Extract background
        bg_match = self.BACKGROUND_PATTERN.search(content)
        if bg_match:
            background = bg_match.group(1)

        # Extract music
        music_match = self.MUSIC_PATTERN.search(content)
        if music_match:
            music = music_match.group(1)

        # Extract character entrances
        for entrance in self.ENTRANCE_PATTERN.finditer(content):
            char_name = entrance.group(1).strip()
            characters.add(char_name)

        # Extract dialogue
        for dial_match in self.DIALOGUE_PATTERN.finditer(content):
            char_name = dial_match.group(1).strip()
            emotion_str = dial_match.group(2) or "neutral"
            text = dial_match.group(3)

            characters.add(char_name)

            # Parse emotion
            try:
                emotion = EmotionTag(emotion_str.lower())
            except ValueError:
                emotion = EmotionTag.NEUTRAL
            character_emotions[char_name] = emotion

            dialogue.append({
                "character": char_name,
                "emotion": emotion.value,
                "text": text
            })

        # Extract narration
        for narr_match in self.NARRATION_PATTERN.finditer(content):
            narration_parts.append(narr_match.group(1).strip())

        # Default poses
        for char in characters:
            character_poses[char] = PoseType.BUST

        scene_id = f"ch{chapter:02d}_sc{scene_num:03d}"

        return SceneDescription(
            id=scene_id,
            chapter=chapter,
            scene_number=scene_num,
            location=location,
            time_of_day=time_of_day,
            characters=list(characters),
            character_emotions=character_emotions,
            character_poses=character_poses,
            dialogue=dialogue,
            narration=" ".join(narration_parts),
            background_description=background,
            music_cue=music,
            sound_effects=sfx
        )


class ComfyUIWorkflowGenerator:
    """Generates ComfyUI workflows for consistent character art."""

    def __init__(self, comfyui_url: Optional[str] = None):
        config = get_config()
        self.comfyui_url = comfyui_url or config.comfyui_url
        self.client = httpx.Client(timeout=60.0)

    def generate_character_portrait(
        self,
        character: CharacterReference,
        emotion: EmotionTag = EmotionTag.NEUTRAL,
        pose: PoseType = PoseType.BUST,
        outfit_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a ComfyUI workflow for character portrait."""

        # Build prompt from character details
        prompt_parts = [character.display_name or character.name]

        if character.hair_color:
            prompt_parts.append(f"{character.hair_color} hair")
        if character.hair_style:
            prompt_parts.append(f"{character.hair_style}")
        if character.eye_color:
            prompt_parts.append(f"{character.eye_color} eyes")
        if character.skin_tone:
            prompt_parts.append(f"{character.skin_tone} skin")

        # Add outfit
        if outfit_name and outfit_name in character.outfits:
            outfit = character.outfits[outfit_name]
            prompt_parts.append(outfit.get("description", ""))

        # Add emotion
        emotion_prompts = {
            EmotionTag.HAPPY: "smiling, happy expression",
            EmotionTag.SAD: "sad expression, downcast eyes",
            EmotionTag.ANGRY: "angry expression, furrowed brow",
            EmotionTag.SURPRISED: "surprised expression, wide eyes",
            EmotionTag.LOVING: "loving gaze, soft smile",
            EmotionTag.SEDUCTIVE: "seductive expression, half-lidded eyes",
            EmotionTag.DETERMINED: "determined expression, confident",
            EmotionTag.PENSIVE: "thoughtful expression, distant gaze",
        }
        if emotion in emotion_prompts:
            prompt_parts.append(emotion_prompts[emotion])

        # Add pose framing
        pose_prompts = {
            PoseType.PORTRAIT: "portrait, head and shoulders, close-up",
            PoseType.BUST: "upper body, bust shot",
            PoseType.FULL: "full body",
            PoseType.ACTION: "dynamic pose, action shot",
        }
        if pose in pose_prompts:
            prompt_parts.append(pose_prompts[pose])

        # Add distinguishing features
        prompt_parts.extend(character.distinguishing_features)

        # Quality tags
        prompt_parts.extend([
            "high quality", "detailed", "visual novel style",
            "anime illustration", "clean lines"
        ])

        prompt = ", ".join(filter(None, prompt_parts))

        # Build workflow
        workflow = {
            "prompt": prompt,
            "negative_prompt": "low quality, blurry, deformed, ugly, bad anatomy",
            "character_id": character.id,
            "character_name": character.name,
            "emotion": emotion.value,
            "pose": pose.value,
            "reference_images": character.reference_images[:3],  # Use up to 3 refs
            "workflow_type": "character_portrait",
            "use_instantid": len(character.reference_images) > 0,
            "use_ipadapter": True,
        }

        return workflow

    def queue_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Queue a workflow in ComfyUI."""
        try:
            # Load the portrait template - try multiple paths
            template_paths = [
                Path(__file__).parent.parent.parent / "config/comfyui/workflows/character_portrait_template.json",
                Path("/app/repo/config/comfyui/workflows/character_portrait_template.json"),  # Docker mount
                Path("/mnt/user/appdata/hydra-dev/config/comfyui/workflows/character_portrait_template.json"),  # Host path
            ]

            template_path = None
            for path in template_paths:
                if path.exists():
                    template_path = path
                    break

            if template_path is None:
                logger.error(f"Character portrait template not found in any of: {template_paths}")
                return None

            with open(template_path) as f:
                template = json.load(f)

            # Remove metadata before sending
            if "_meta" in template:
                del template["_meta"]

            # Substitute variables in template
            positive_prompt = workflow.get("prompt", "")
            negative_prompt = workflow.get("negative_prompt", "low quality, blurry, deformed")
            character_name = workflow.get("character_name", "unknown")

            # Generate a random seed (0 to 2^63-1)
            import random
            random_seed = random.randint(0, 2**63 - 1)

            # Walk through template and substitute variables
            template_str = json.dumps(template)
            template_str = template_str.replace("{{POSITIVE_PROMPT}}", positive_prompt.replace('"', '\\"'))
            template_str = template_str.replace("{{NEGATIVE_PROMPT}}", negative_prompt.replace('"', '\\"'))
            template_str = template_str.replace("{{CHARACTER_NAME}}", character_name)
            template_str = template_str.replace("{{REFERENCE_IMAGE}}", "")
            template_str = template_str.replace("{{OUTPUT_PATH}}", f"empire/{character_name}")
            # Replace SEED placeholder - it's quoted in template so we need to replace with unquoted number
            template_str = template_str.replace('"{{SEED}}"', str(random_seed))

            comfyui_workflow = json.loads(template_str)

            # Submit to ComfyUI /prompt endpoint
            payload = {
                "prompt": comfyui_workflow,
                "client_id": "hydra-tools-api"
            }

            resp = self.client.post(
                f"{self.comfyui_url}/prompt",
                json=payload,
                timeout=30.0
            )

            if resp.status_code == 200:
                result = resp.json()
                prompt_id = result.get("prompt_id")
                logger.info(f"Queued ComfyUI workflow {prompt_id} for {character_name}")
                return prompt_id
            else:
                logger.error(f"ComfyUI returned {resp.status_code}: {resp.text}")
                return None

        except Exception as e:
            logger.error(f"Error queuing ComfyUI workflow: {e}")
            # Return a mock ID for tracking purposes
            job_id = hashlib.md5(json.dumps(workflow).encode()).hexdigest()[:12]
            logger.warning(f"Returning mock job ID {job_id} due to ComfyUI error")
            return job_id

    def get_workflow_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a queued workflow."""
        try:
            resp = self.client.get(f"{self.comfyui_url}/history/{job_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
        return {"status": "unknown"}


class VoiceSynthesizer:
    """Manages voice synthesis with character profiles."""

    DEFAULT_KOKORO_URL = "http://192.168.1.244:8880"

    def __init__(self, kokoro_url: Optional[str] = None):
        self.kokoro_url = kokoro_url or self.DEFAULT_KOKORO_URL
        self.client = httpx.Client(timeout=30.0)

    def synthesize_dialogue(
        self,
        text: str,
        character: CharacterReference,
        emotion: EmotionTag = EmotionTag.NEUTRAL
    ) -> Optional[bytes]:
        """Synthesize dialogue for a character."""

        # Get voice settings
        voice_id = character.voice_id or "af_sarah"  # default voice
        voice_chars = character.voice_characteristics or {}

        # Adjust speed/pitch based on emotion
        emotion_adjustments = {
            EmotionTag.HAPPY: {"speed": 1.1, "pitch": 1.05},
            EmotionTag.SAD: {"speed": 0.9, "pitch": 0.95},
            EmotionTag.ANGRY: {"speed": 1.15, "pitch": 1.1},
            EmotionTag.SEDUCTIVE: {"speed": 0.85, "pitch": 0.98},
            EmotionTag.DETERMINED: {"speed": 1.0, "pitch": 1.02},
        }

        adjustments = emotion_adjustments.get(emotion, {"speed": 1.0, "pitch": 1.0})

        payload = {
            "text": text,
            "voice": voice_id,
            "speed": voice_chars.get("base_speed", 1.0) * adjustments["speed"],
        }

        try:
            resp = self.client.post(f"{self.kokoro_url}/v1/audio/speech", json=payload)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            logger.error(f"Error synthesizing voice: {e}")

        return None


# FastAPI router for character consistency endpoints
def create_character_router():
    """Create FastAPI router for character consistency endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/characters", tags=["characters"])
    manager = CharacterManager()
    parser = ScriptParser(manager)
    workflow_gen = ComfyUIWorkflowGenerator()
    voice_synth = VoiceSynthesizer()

    class CharacterCreate(BaseModel):
        name: str
        display_name: str
        description: str
        hair_color: str = ""
        hair_style: str = ""
        eye_color: str = ""
        skin_tone: str = ""
        distinguishing_features: List[str] = []
        voice_id: Optional[str] = None

    class ScriptParseRequest(BaseModel):
        script_text: str
        chapter: int = 1

    class GeneratePortraitRequest(BaseModel):
        character_id: str
        emotion: str = "neutral"
        pose: str = "bust"
        outfit_name: Optional[str] = None

    @router.get("/")
    async def list_characters():
        """List all characters."""
        characters = manager.list_characters()
        return {"characters": [c.to_dict() for c in characters]}

    @router.post("/")
    async def create_character(char: CharacterCreate):
        """Create a new character."""
        character = CharacterReference(
            id=str(uuid.uuid4()),
            name=char.name,
            display_name=char.display_name,
            description=char.description,
            hair_color=char.hair_color,
            hair_style=char.hair_style,
            eye_color=char.eye_color,
            skin_tone=char.skin_tone,
            distinguishing_features=char.distinguishing_features,
            voice_id=char.voice_id,
        )

        success = manager.add_character(character)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create character")

        return {"character": character.to_dict()}

    class UpdateReferencesRequest(BaseModel):
        reference_images: List[str]

    class UpdateVoiceRequest(BaseModel):
        voice_id: Optional[str] = None
        voice_characteristics: Optional[Dict[str, Any]] = None

    @router.patch("/{character_id}/voice")
    async def update_character_voice(character_id: str, request: UpdateVoiceRequest):
        """Update a character's voice profile."""
        character = manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Update voice settings
        if request.voice_id is not None:
            character.voice_id = request.voice_id
        if request.voice_characteristics is not None:
            character.voice_characteristics = request.voice_characteristics

        # Delete old character data first (like update_character_references does)
        try:
            import httpx
            resp = httpx.post(
                f"{manager.qdrant_url}/collections/{manager.FACE_COLLECTION}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "character_id", "match": {"value": character_id}}
                        ]
                    }
                }
            )
            if resp.status_code not in (200, 201):
                raise HTTPException(status_code=500, detail=f"Failed to delete old character: {resp.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting old character: {e}")

        # Re-add character with updated data
        success = manager.add_character(character)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update voice profile")

        updated = manager.get_character(character_id)
        return {
            "status": "updated",
            "character_id": character_id,
            "voice_id": updated.voice_id if updated else None,
            "voice_characteristics": updated.voice_characteristics if updated else {},
        }

    @router.patch("/{character_id}/references")
    async def update_character_references(character_id: str, request: UpdateReferencesRequest):
        """Update a character's reference images."""
        character = manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        success = manager.update_character_references(character_id, request.reference_images)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update references")

        updated = manager.get_character(character_id)
        return {
            "status": "updated",
            "character_id": character_id,
            "reference_count": len(request.reference_images),
            "character": updated.to_dict() if updated else None
        }

    @router.post("/parse-script")
    async def parse_script(request: ScriptParseRequest):
        """Parse a visual novel script into scenes."""
        scenes = parser.parse_script(request.script_text, request.chapter)
        return {
            "scenes": [
                {
                    "id": s.id,
                    "chapter": s.chapter,
                    "scene_number": s.scene_number,
                    "location": s.location,
                    "time_of_day": s.time_of_day,
                    "characters": s.characters,
                    "dialogue_count": len(s.dialogue),
                    "background": s.background_description,
                }
                for s in scenes
            ]
        }

    @router.post("/generate-portrait")
    async def generate_portrait(request: GeneratePortraitRequest):
        """Generate a character portrait workflow."""
        character = manager.get_character(request.character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        try:
            emotion = EmotionTag(request.emotion)
        except ValueError:
            emotion = EmotionTag.NEUTRAL

        try:
            pose = PoseType(request.pose)
        except ValueError:
            pose = PoseType.BUST

        workflow = workflow_gen.generate_character_portrait(
            character, emotion, pose, request.outfit_name
        )

        job_id = workflow_gen.queue_workflow(workflow)

        return {
            "job_id": job_id,
            "workflow": workflow,
            "status": "queued"
        }

    # Batch generation models and endpoint
    class BatchPortraitRequest(BaseModel):
        """Request for batch portrait generation."""
        character_ids: List[str] = []  # Empty means all characters
        emotions: List[str] = ["neutral"]  # Emotions to generate for each character
        poses: List[str] = ["bust"]  # Poses to generate for each character
        skip_existing: bool = True  # Skip if character already has reference images
        priority: str = "normal"  # Priority: low, normal, high
        max_concurrent: int = 4  # Max concurrent generations

    class BatchPortraitItem(BaseModel):
        """Single item in batch generation."""
        character_id: str
        character_name: str
        emotion: str
        pose: str
        job_id: Optional[str] = None
        status: str = "pending"
        error: Optional[str] = None

    @router.post("/batch-generate")
    async def batch_generate_portraits(request: BatchPortraitRequest):
        """
        Generate portraits for multiple characters in batch.

        If character_ids is empty, generates for all characters.
        Generates all combinations of emotions x poses for each character.
        """
        # Get characters to process
        if request.character_ids:
            characters = []
            for char_id in request.character_ids:
                char = manager.get_character(char_id)
                if char:
                    characters.append(char)
        else:
            characters = manager.list_characters()

        if not characters:
            return {
                "status": "error",
                "message": "No characters found",
                "jobs": []
            }

        # Filter out characters with existing references if skip_existing
        if request.skip_existing:
            characters = [c for c in characters if not c.reference_images]

        if not characters:
            return {
                "status": "completed",
                "message": "All characters already have reference images",
                "jobs": []
            }

        # Generate jobs for all combinations
        jobs = []
        for character in characters:
            for emotion_str in request.emotions:
                for pose_str in request.poses:
                    try:
                        emotion = EmotionTag(emotion_str)
                    except ValueError:
                        emotion = EmotionTag.NEUTRAL

                    try:
                        pose = PoseType(pose_str)
                    except ValueError:
                        pose = PoseType.BUST

                    workflow = workflow_gen.generate_character_portrait(
                        character, emotion, pose
                    )
                    job_id = workflow_gen.queue_workflow(workflow)

                    jobs.append(BatchPortraitItem(
                        character_id=character.id,
                        character_name=character.name,
                        emotion=emotion.value,
                        pose=pose.value,
                        job_id=job_id,
                        status="queued"
                    ))

        return {
            "status": "queued",
            "message": f"Queued {len(jobs)} portrait generations",
            "total_characters": len(characters),
            "emotions": request.emotions,
            "poses": request.poses,
            "combinations_per_character": len(request.emotions) * len(request.poses),
            "jobs": [j.model_dump() for j in jobs]
        }

    @router.get("/batch-status/{batch_id}")
    async def get_batch_status(batch_id: str):
        """Get status of a batch generation job."""
        # In a real implementation, this would track batch status in a database
        # For now, return a placeholder
        return {
            "batch_id": batch_id,
            "status": "unknown",
            "message": "Batch tracking not yet implemented - check individual job IDs"
        }

    @router.get("/coverage")
    async def get_portrait_coverage():
        """
        Get portrait coverage statistics for all characters.

        Returns how many characters have reference images and which emotions are covered.
        """
        characters = manager.list_characters()

        with_references = [c for c in characters if c.reference_images]
        without_references = [c for c in characters if not c.reference_images]

        coverage_details = []
        for char in characters:
            coverage_details.append({
                "id": char.id,
                "name": char.name,
                "display_name": char.display_name,
                "has_reference": bool(char.reference_images),
                "reference_count": len(char.reference_images),
            })

        return {
            "total_characters": len(characters),
            "with_references": len(with_references),
            "without_references": len(without_references),
            "coverage_percentage": (len(with_references) / len(characters) * 100) if characters else 0,
            "characters_needing_portraits": [c.name for c in without_references],
            "details": coverage_details
        }

    @router.post("/generate-missing")
    async def generate_missing_portraits(
        emotions: List[str] = ["neutral", "happy", "sad"],
        poses: List[str] = ["bust"]
    ):
        """
        Generate portraits for all characters missing reference images.

        Convenience endpoint that wraps batch-generate with skip_existing=True.
        """
        batch_request = BatchPortraitRequest(
            character_ids=[],  # All characters
            emotions=emotions,
            poses=poses,
            skip_existing=True,
            priority="normal"
        )

        return await batch_generate_portraits(batch_request)

    # NOTE: Using Path parameter with regex to only match UUIDs, preventing
    # matches against "/coverage", "/batch-status", etc.
    from fastapi import Path as FastAPIPath
    import re
    UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    @router.get("/by-id/{character_id}")
    async def get_character(
        character_id: str = FastAPIPath(..., regex=UUID_PATTERN, description="Character UUID")
    ):
        """Get a character by ID. Use /by-id/{uuid} to avoid route conflicts."""
        character = manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        return {"character": character.to_dict()}

    return router
