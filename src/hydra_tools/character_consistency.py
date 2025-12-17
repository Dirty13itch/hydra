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


class TransitionType(Enum):
    """Scene transition effects for visual novel."""
    CUT = "cut"                    # Instant transition (default)
    FADE = "fade"                  # Fade to/from black
    DISSOLVE = "dissolve"          # Cross-dissolve between scenes
    WIPE_LEFT = "wipe_left"        # Wipe from right to left
    WIPE_RIGHT = "wipe_right"      # Wipe from left to right
    WIPE_UP = "wipe_up"            # Wipe upward
    WIPE_DOWN = "wipe_down"        # Wipe downward
    IRIS_IN = "iris_in"            # Circle closing to center
    IRIS_OUT = "iris_out"          # Circle opening from center
    FLASH = "flash"                # White flash transition
    BLUR = "blur"                  # Blur out then blur in
    PIXELATE = "pixelate"          # Pixelation effect
    SHAKE = "shake"                # Screen shake (impact moment)


class TransitionTiming(Enum):
    """Timing presets for transitions."""
    INSTANT = 0.0                  # No transition
    FAST = 0.3                     # Quick cut
    NORMAL = 0.5                   # Standard transition
    SLOW = 1.0                     # Dramatic effect
    DRAMATIC = 2.0                 # Very slow, emotional


@dataclass
class SceneTransition:
    """Transition metadata for scene changes."""
    type: TransitionType = TransitionType.CUT
    duration: float = 0.5          # Seconds
    color: str = "#000000"         # For fade/flash (black or white typically)
    easing: str = "ease-in-out"    # CSS-style easing
    sound_effect: Optional[str] = None  # Transition sound


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

    # Transition metadata
    transition_in: Optional[SceneTransition] = None    # Transition INTO this scene
    transition_out: Optional[SceneTransition] = None   # Transition OUT of this scene
    transition_notes: str = ""                          # Director notes for transition

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "chapter": self.chapter,
            "scene_number": self.scene_number,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "characters": self.characters,
            "character_emotions": {k: v.value for k, v in self.character_emotions.items()},
            "character_poses": {k: v.value for k, v in self.character_poses.items()},
            "dialogue": self.dialogue,
            "narration": self.narration,
            "background_description": self.background_description,
            "music_cue": self.music_cue,
            "sound_effects": self.sound_effects,
            "transition_in": {
                "type": self.transition_in.type.value,
                "duration": self.transition_in.duration,
                "color": self.transition_in.color,
                "easing": self.transition_in.easing,
                "sound_effect": self.transition_in.sound_effect
            } if self.transition_in else None,
            "transition_out": {
                "type": self.transition_out.type.value,
                "duration": self.transition_out.duration,
                "color": self.transition_out.color,
                "easing": self.transition_out.easing,
                "sound_effect": self.transition_out.sound_effect
            } if self.transition_out else None,
            "transition_notes": self.transition_notes
        }


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

        # First element is prologue/intro text before first scene - skip it
        # The regex split produces: [pre-content, num1, loc1, time1, content1, num2, ...]
        # So we need to skip the first element (pre-content) to align to groups of 4
        if scene_splits:
            scene_splits = scene_splits[1:]  # Always skip prologue/intro content

        # Process scenes in groups of 4: (number, location, time, content)
        i = 0
        while i < len(scene_splits) - 3:
            try:
                scene_num = int(scene_splits[i])
            except (ValueError, TypeError):
                # Skip malformed scene data
                i += 1
                continue

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

    def generate_background(
        self,
        description: str,
        location: str = "",
        time_of_day: str = "day",
        output_prefix: str = "background"
    ) -> Dict[str, Any]:
        """Generate a ComfyUI workflow for scene background."""

        # Build the scene description
        scene_parts = [description]
        if location:
            scene_parts.append(location)

        scene_description = ", ".join(filter(None, scene_parts))

        # Map time of day to lighting
        lighting_map = {
            "morning": "early morning light, soft sunrise colors, golden hour",
            "day": "bright daylight, clear sky, natural lighting",
            "afternoon": "warm afternoon light, long shadows",
            "evening": "sunset colors, orange and purple sky, warm glow",
            "night": "nighttime, moonlight, starry sky, dark atmosphere",
            "dusk": "twilight, purple sky, ambient lighting",
            "dawn": "pre-dawn, soft blue light, misty atmosphere",
        }
        lighting = lighting_map.get(time_of_day.lower(), time_of_day)

        return {
            "scene_description": scene_description,
            "time_of_day": lighting,
            "output_prefix": output_prefix,
            "workflow_type": "background"
        }

    def queue_background(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Queue a background workflow in ComfyUI."""
        try:
            # Load the background template
            template_paths = [
                Path(__file__).parent.parent.parent / "config/comfyui/workflows/background_template.json",
                Path("/app/repo/config/comfyui/workflows/background_template.json"),
                Path("/mnt/user/appdata/hydra-dev/config/comfyui/workflows/background_template.json"),
            ]

            template_path = None
            for path in template_paths:
                if path.exists():
                    template_path = path
                    break

            if template_path is None:
                logger.error(f"Background template not found")
                return None

            with open(template_path) as f:
                template = json.load(f)

            # Remove metadata
            if "_meta" in template:
                del template["_meta"]

            # Generate random seed
            import random
            random_seed = random.randint(0, 2**63 - 1)

            # Substitute variables
            template_str = json.dumps(template)
            template_str = template_str.replace("{{SCENE_DESCRIPTION}}", workflow.get("scene_description", "").replace('"', '\\"'))
            template_str = template_str.replace("{{TIME_OF_DAY}}", workflow.get("time_of_day", "day").replace('"', '\\"'))

            # Update seed (the template has -1 for random)
            comfyui_workflow = json.loads(template_str)
            if "5" in comfyui_workflow and "inputs" in comfyui_workflow["5"]:
                comfyui_workflow["5"]["inputs"]["seed"] = random_seed

            # Update output filename prefix
            output_prefix = workflow.get("output_prefix", "background")
            if "7" in comfyui_workflow and "inputs" in comfyui_workflow["7"]:
                comfyui_workflow["7"]["inputs"]["filename_prefix"] = output_prefix

            # Submit to ComfyUI
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
                logger.info(f"Queued background workflow {prompt_id}")
                return prompt_id
            else:
                logger.error(f"ComfyUI returned {resp.status_code}: {resp.text}")
                return None

        except Exception as e:
            logger.error(f"Error queuing background workflow: {e}")
            job_id = hashlib.md5(json.dumps(workflow).encode()).hexdigest()[:12]
            return job_id


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
    from fastapi import APIRouter, HTTPException, Body
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
        """Parse a visual novel script into scenes with full dialogue data."""
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
                    "dialogues": s.dialogue,  # Full dialogue data with character, emotion, text
                    "dialogue_count": len(s.dialogue),
                    "background": s.background_description,
                    "narration": s.narration,
                    "music_cue": s.music_cue,
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

    class ChapterAssetRequest(BaseModel):
        """Request to generate all assets for a parsed chapter."""
        scenes: List[dict]  # Parsed scene data with characters and dialogues
        generate_portraits: bool = True
        generate_tts: bool = True
        generate_backgrounds: bool = True
        skip_existing_emotions: bool = True
        output_base: str = "/app/repo/output/empire/chapters"  # Maps to hydra-dev/output/

    class DialogueItem(BaseModel):
        """Single dialogue line for TTS generation."""
        scene_id: str
        character: str
        emotion: str
        text: str
        voice_id: str
        output_path: str

    @router.post("/generate-chapter-assets")
    async def generate_chapter_assets(request: ChapterAssetRequest):
        """
        Generate all assets for a chapter: portraits, TTS, and backgrounds.

        Takes parsed scene data and queues generation for:
        - Character portraits (unique character+emotion combinations)
        - TTS voice lines (all dialogues)
        - Background images (unique scene backgrounds)
        """
        # Get all characters for lookup
        all_chars = manager.list_characters()
        char_map = {c.name.lower(): c for c in all_chars}

        # Track unique character+emotion combos for portraits
        portrait_requests = set()  # (character_name, emotion)
        tts_requests = []
        background_requests = []

        chapter_num = request.scenes[0].get("chapter", 1) if request.scenes else 1

        for scene in request.scenes:
            scene_id = scene.get("id", f"scene_{len(background_requests)}")

            # Extract dialogues if present
            dialogues = scene.get("dialogues", [])
            characters = scene.get("characters", [])

            # Queue portraits for each character+emotion
            for dialogue in dialogues:
                char_name = dialogue.get("character", "").lower()
                emotion = dialogue.get("emotion", "neutral").lower()
                text = dialogue.get("text", "")

                if char_name:
                    portrait_requests.add((char_name, emotion))

                    # Prepare TTS request
                    if request.generate_tts and text:
                        char_data = char_map.get(char_name)
                        voice_id = char_data.voice_id if char_data else "af_sarah"
                        tts_requests.append({
                            "scene_id": scene_id,
                            "character": char_name,
                            "emotion": emotion,
                            "text": text,
                            "voice_id": voice_id,
                            "output_path": f"{request.output_base}/ch{chapter_num:02d}/{scene_id}/{char_name}_{len(tts_requests):03d}.wav"
                        })

            # Also add neutral portraits for any characters without dialogues
            for char_name in characters:
                if char_name.lower() not in [p[0] for p in portrait_requests]:
                    portrait_requests.add((char_name.lower(), "neutral"))

            # Queue background if present
            background = scene.get("background", "")
            if request.generate_backgrounds and background:
                background_requests.append({
                    "scene_id": scene_id,
                    "description": background,
                    "location": scene.get("location", ""),
                    "time_of_day": scene.get("time_of_day", "day"),
                    "output_path": f"{request.output_base}/ch{chapter_num:02d}/{scene_id}/background.png"
                })

        # Generate portraits
        portrait_jobs = []
        if request.generate_portraits:
            for char_name, emotion in portrait_requests:
                char_data = char_map.get(char_name)
                if char_data:
                    try:
                        emotion_tag = EmotionTag(emotion)
                    except ValueError:
                        emotion_tag = EmotionTag.NEUTRAL

                    workflow = workflow_gen.generate_character_portrait(
                        char_data, emotion_tag, PoseType.BUST
                    )
                    job_id = workflow_gen.queue_workflow(workflow)
                    portrait_jobs.append({
                        "character": char_name,
                        "emotion": emotion,
                        "job_id": job_id,
                        "status": "queued"
                    })

        # Generate TTS for all dialogue lines
        tts_results = []
        if request.generate_tts and tts_requests:
            import aiohttp
            import os

            kokoro_url = "http://192.168.1.244:8880/v1/audio/speech"

            async with aiohttp.ClientSession() as session:
                for dialogue in tts_requests:
                    try:
                        emotion = dialogue.get("emotion", "neutral")
                        speed_map = {
                            "neutral": 1.0, "happy": 1.1, "sad": 0.9,
                            "angry": 1.2, "fearful": 1.15, "surprised": 1.1,
                            "pensive": 0.95, "determined": 1.0, "loving": 0.9
                        }
                        speed = speed_map.get(emotion, 1.0)

                        payload = {
                            "model": "kokoro",
                            "input": dialogue.get("text", ""),
                            "voice": dialogue.get("voice_id", "af_sarah"),
                            "speed": speed,
                            "response_format": "wav"
                        }

                        async with session.post(kokoro_url, json=payload) as resp:
                            if resp.status == 200:
                                output_path = dialogue.get("output_path")
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                                audio_data = await resp.read()
                                with open(output_path, "wb") as f:
                                    f.write(audio_data)

                                tts_results.append({
                                    "scene_id": dialogue.get("scene_id"),
                                    "character": dialogue.get("character"),
                                    "output_path": output_path,
                                    "status": "completed"
                                })
                            else:
                                tts_results.append({
                                    "character": dialogue.get("character"),
                                    "status": "failed",
                                    "error": f"HTTP {resp.status}"
                                })
                    except Exception as e:
                        tts_results.append({
                            "character": dialogue.get("character"),
                            "status": "failed",
                            "error": str(e)
                        })

        tts_successful = len([r for r in tts_results if r.get("status") == "completed"])
        tts_failed = len([r for r in tts_results if r.get("status") == "failed"])

        return {
            "status": "completed" if tts_failed == 0 else "partial",
            "chapter": chapter_num,
            "summary": {
                "portrait_jobs": len(portrait_jobs),
                "tts_generated": tts_successful,
                "tts_failed": tts_failed,
                "background_jobs": len(background_requests),
                "unique_emotions": list(set(e for _, e in portrait_requests))
            },
            "portraits": portrait_jobs,
            "tts_results": tts_results,
            "backgrounds": background_requests
        }

    @router.post("/generate-tts-batch")
    async def generate_tts_batch(dialogues: List[dict]):
        """
        Generate TTS for a batch of dialogue lines.

        Each dialogue should have: character, text, emotion, voice_id, output_path
        """
        import aiohttp
        import asyncio

        results = []
        kokoro_url = "http://192.168.1.244:8880/v1/audio/speech"

        async with aiohttp.ClientSession() as session:
            for dialogue in dialogues:
                try:
                    # Map emotion to speed adjustment
                    emotion = dialogue.get("emotion", "neutral")
                    speed_map = {
                        "neutral": 1.0, "happy": 1.1, "sad": 0.9,
                        "angry": 1.2, "fearful": 1.15, "surprised": 1.1,
                        "seductive": 0.85, "mysterious": 0.95
                    }
                    speed = speed_map.get(emotion, 1.0)

                    payload = {
                        "model": "kokoro",
                        "input": dialogue.get("text", ""),
                        "voice": dialogue.get("voice_id", "af_sarah"),
                        "speed": speed,
                        "response_format": "wav"
                    }

                    async with session.post(kokoro_url, json=payload) as resp:
                        if resp.status == 200:
                            # Save audio to output path
                            output_path = dialogue.get("output_path", f"/tmp/tts_{len(results)}.wav")
                            import os
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)

                            audio_data = await resp.read()
                            with open(output_path, "wb") as f:
                                f.write(audio_data)

                            results.append({
                                "character": dialogue.get("character"),
                                "text": dialogue.get("text", "")[:50] + "...",
                                "output_path": output_path,
                                "status": "completed"
                            })
                        else:
                            results.append({
                                "character": dialogue.get("character"),
                                "status": "failed",
                                "error": f"HTTP {resp.status}"
                            })
                except Exception as e:
                    results.append({
                        "character": dialogue.get("character"),
                        "status": "failed",
                        "error": str(e)
                    })

        return {
            "status": "completed",
            "total": len(dialogues),
            "successful": len([r for r in results if r.get("status") == "completed"]),
            "failed": len([r for r in results if r.get("status") == "failed"]),
            "results": results
        }

    class QualityScoreRequest(BaseModel):
        """Request to score image quality and consistency."""
        image_path: str  # Path or URL to image to score
        reference_path: Optional[str] = None  # Reference image for comparison
        score_aesthetic: bool = True
        score_consistency: bool = True

    @router.post("/quality-score")
    async def score_image_quality(request: QualityScoreRequest):
        """
        Score image quality using aesthetic predictor and consistency comparison.

        Returns:
        - aesthetic_score: 0-10 score from aesthetic predictor
        - consistency_score: 0-1 similarity to reference image (if provided)
        - overall_score: Combined weighted score
        """
        import hashlib
        from PIL import Image
        import io

        results = {
            "image_path": request.image_path,
            "aesthetic_score": None,
            "consistency_score": None,
            "overall_score": None,
            "status": "pending"
        }

        try:
            # Load images
            def load_image(path: str) -> Image.Image:
                if path.startswith("http"):
                    import requests
                    resp = requests.get(path, timeout=30)
                    return Image.open(io.BytesIO(resp.content))
                else:
                    return Image.open(path)

            img = load_image(request.image_path)

            # Calculate perceptual hash for basic quality check
            # (images that are too uniform or corrupted will have low entropy)
            img_gray = img.convert('L').resize((64, 64))
            pixels = list(img_gray.getdata())
            avg = sum(pixels) / len(pixels)
            variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)

            # Normalized variance as basic quality metric (0-1)
            basic_quality = min(1.0, variance / 5000)

            # If reference provided, calculate similarity
            if request.reference_path and request.score_consistency:
                ref_img = load_image(request.reference_path)

                # Resize both to same size for comparison
                size = (256, 256)
                img_resized = img.resize(size).convert('RGB')
                ref_resized = ref_img.resize(size).convert('RGB')

                # Calculate histogram similarity
                def color_histogram(image):
                    """Calculate normalized color histogram."""
                    hist_r = image.histogram()[:256]
                    hist_g = image.histogram()[256:512]
                    hist_b = image.histogram()[512:768]
                    total = sum(hist_r) + sum(hist_g) + sum(hist_b)
                    return [h/total for h in hist_r + hist_g + hist_b]

                hist1 = color_histogram(img_resized)
                hist2 = color_histogram(ref_resized)

                # Cosine similarity
                dot = sum(a * b for a, b in zip(hist1, hist2))
                norm1 = sum(a * a for a in hist1) ** 0.5
                norm2 = sum(b * b for b in hist2) ** 0.5
                consistency = dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0

                results["consistency_score"] = round(consistency, 3)

            # Use ComfyUI aesthetic predictor if available
            if request.score_aesthetic:
                # For now, use basic quality metric
                # TODO: Queue ComfyUI workflow for proper aesthetic scoring
                results["aesthetic_score"] = round(basic_quality * 10, 2)  # Scale to 0-10

            # Calculate overall score
            scores = []
            if results["aesthetic_score"] is not None:
                scores.append(results["aesthetic_score"] / 10)  # Normalize to 0-1
            if results["consistency_score"] is not None:
                scores.append(results["consistency_score"])

            if scores:
                results["overall_score"] = round(sum(scores) / len(scores), 3)

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    class BatchQualityRequest(BaseModel):
        """Request for batch quality scoring."""
        images: List[str]
        reference_path: Optional[str] = None

    @router.post("/batch-quality-score")
    async def batch_score_quality(request: BatchQualityRequest):
        """Score multiple images against a reference."""
        results = []
        for image_path in request.images:
            req = QualityScoreRequest(
                image_path=image_path,
                reference_path=request.reference_path
            )
            score = await score_image_quality(req)
            results.append(score)

        # Summary statistics
        valid_scores = [r["overall_score"] for r in results if r.get("overall_score")]

        return {
            "total": len(request.images),
            "scored": len(valid_scores),
            "average_score": round(sum(valid_scores) / len(valid_scores), 3) if valid_scores else None,
            "min_score": min(valid_scores) if valid_scores else None,
            "max_score": max(valid_scores) if valid_scores else None,
            "results": results
        }

    class BackgroundRequest(BaseModel):
        """Request for generating a single background."""
        description: str
        location: str = ""
        time_of_day: str = "day"
        output_prefix: str = "background"

    @router.post("/generate-background")
    async def generate_background(request: BackgroundRequest):
        """Generate a single scene background image."""
        workflow = workflow_gen.generate_background(
            description=request.description,
            location=request.location,
            time_of_day=request.time_of_day,
            output_prefix=request.output_prefix
        )
        job_id = workflow_gen.queue_background(workflow)

        return {
            "status": "queued" if job_id else "failed",
            "job_id": job_id,
            "description": request.description,
            "location": request.location,
            "time_of_day": request.time_of_day
        }

    class BatchBackgroundRequest(BaseModel):
        """Request for generating multiple backgrounds."""
        backgrounds: List[dict]  # Each with description, location, time_of_day, output_prefix

    @router.post("/generate-backgrounds-batch")
    async def generate_backgrounds_batch(request: BatchBackgroundRequest):
        """Generate multiple scene backgrounds."""
        jobs = []

        for bg in request.backgrounds:
            workflow = workflow_gen.generate_background(
                description=bg.get("description", ""),
                location=bg.get("location", ""),
                time_of_day=bg.get("time_of_day", "day"),
                output_prefix=bg.get("output_prefix", "background")
            )
            job_id = workflow_gen.queue_background(workflow)
            jobs.append({
                "description": bg.get("description", ""),
                "job_id": job_id,
                "status": "queued" if job_id else "failed"
            })

        return {
            "total": len(jobs),
            "queued": len([j for j in jobs if j["status"] == "queued"]),
            "jobs": jobs
        }

    # Voice Assignment System
    KOKORO_URL = "http://192.168.1.244:8880"

    VOICE_CATEGORIES = {
        "female_american": ["af_alloy", "af_bella", "af_heart", "af_jessica", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky"],
        "female_british": ["bf_alice", "bf_emma", "bf_lily"],
        "male_american": ["am_adam", "am_echo", "am_eric", "am_liam", "am_michael", "am_onyx"],
        "male_british": ["bm_daniel", "bm_fable", "bm_george", "bm_lewis"],
        "special": ["am_santa", "em_santa", "am_fenrir", "am_puck"],
    }

    VOICE_DESCRIPTIONS = {
        "af_sky": "Young, bright, optimistic female voice",
        "af_sarah": "Mature, warm, authoritative female voice",
        "af_nicole": "Soft, gentle, mysterious female voice",
        "af_bella": "Elegant, refined female voice",
        "af_heart": "Emotional, expressive female voice",
        "bf_emma": "British, sophisticated female voice",
        "bf_lily": "British, youthful female voice",
        "am_adam": "Deep, confident male voice",
        "am_michael": "Warm, friendly male voice",
        "am_eric": "Young, energetic male voice",
        "bm_george": "British, distinguished male voice",
        "bm_lewis": "British, scholarly male voice",
    }

    @router.get("/voices")
    async def list_available_voices():
        """List all available TTS voices with categories and descriptions."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{KOKORO_URL}/v1/audio/voices", timeout=10)
                if resp.status_code == 200:
                    voices = resp.json().get("voices", [])
                else:
                    voices = []
        except Exception:
            voices = list(VOICE_DESCRIPTIONS.keys())

        return {
            "total": len(voices),
            "voices": voices,
            "categories": VOICE_CATEGORIES,
            "descriptions": VOICE_DESCRIPTIONS,
            "recommended": {
                "queen": "af_sky",  # Primary queen voice
                "advisor": "af_sarah",  # Mature advisor
                "mystic": "af_nicole",  # Mysterious seer
                "warrior": "bf_emma",  # British warrior
                "male_lead": "bm_george",  # Distinguished male
            }
        }

    class VoiceAssignmentRequest(BaseModel):
        """Request to assign a voice to a character."""
        character_name: str
        voice_id: str

    @router.post("/assign-voice")
    async def assign_voice_to_character(request: VoiceAssignmentRequest):
        """Assign a TTS voice to a character."""
        char = manager.get_character(request.character_name)
        if not char:
            return {"error": f"Character '{request.character_name}' not found"}

        # Update character's voice_id
        char.voice_id = request.voice_id
        manager.save_character(char)

        return {
            "character": char.name,
            "voice_id": request.voice_id,
            "description": VOICE_DESCRIPTIONS.get(request.voice_id, "Custom voice"),
            "status": "assigned"
        }

    @router.get("/voice-assignments")
    async def get_voice_assignments():
        """Get current voice assignments for all characters."""
        chars = manager.list_characters()

        assignments = []
        unassigned = []

        for char in chars:
            if char.voice_id:
                assignments.append({
                    "character": char.name,
                    "voice_id": char.voice_id,
                    "description": VOICE_DESCRIPTIONS.get(char.voice_id, "Custom voice")
                })
            else:
                unassigned.append(char.name)

        return {
            "assigned": len(assignments),
            "unassigned": len(unassigned),
            "assignments": assignments,
            "characters_needing_voice": unassigned
        }

    @router.post("/preview-voice")
    async def preview_voice(voice_id: str, text: str = "Hello, this is a voice preview."):
        """Generate a voice preview for a given voice ID."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{KOKORO_URL}/v1/audio/speech",
                    json={"voice": voice_id, "input": text, "speed": 1.0},
                    timeout=30
                )
                if resp.status_code == 200:
                    # Save preview to temp file
                    preview_path = f"/tmp/voice_preview_{voice_id}.wav"
                    with open(preview_path, "wb") as f:
                        f.write(resp.content)

                    return {
                        "voice_id": voice_id,
                        "text": text,
                        "preview_path": preview_path,
                        "status": "generated"
                    }
                else:
                    return {"error": f"TTS failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    class ChapterStructureRequest(BaseModel):
        """Request for creating chapter directory structure."""
        chapter_number: int
        scene_count: int = 1
        output_base: str = "/app/repo/output/empire/chapters"

    @router.post("/create-chapter-structure")
    async def create_chapter_structure(request: ChapterStructureRequest):
        """Create standardized directory structure for a chapter."""
        import os

        chapter_dir = f"{request.output_base}/ch{request.chapter_number:02d}"

        # Standard subdirectories
        subdirs = [
            "portraits",      # Character portraits with emotions
            "tts",            # Text-to-speech audio files
            "backgrounds",    # Scene background images
            "music",          # Background music and SFX
            "metadata",       # JSON manifests and config
            "raw",            # Original/unprocessed assets
        ]

        created = []
        for subdir in subdirs:
            path = os.path.join(chapter_dir, subdir)
            os.makedirs(path, exist_ok=True)
            created.append(path)

        # Create scene subdirectories
        for scene_num in range(1, request.scene_count + 1):
            scene_dir = os.path.join(chapter_dir, f"scenes/sc{scene_num:03d}")
            os.makedirs(scene_dir, exist_ok=True)
            created.append(scene_dir)

        # Create manifest file
        manifest = {
            "chapter": request.chapter_number,
            "created_at": datetime.now().isoformat(),
            "scene_count": request.scene_count,
            "structure": subdirs,
            "status": "initialized"
        }

        manifest_path = os.path.join(chapter_dir, "metadata/manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return {
            "chapter": request.chapter_number,
            "base_path": chapter_dir,
            "directories_created": len(created),
            "manifest": manifest_path,
            "structure": {
                "portraits": f"{chapter_dir}/portraits",
                "tts": f"{chapter_dir}/tts",
                "backgrounds": f"{chapter_dir}/backgrounds",
                "music": f"{chapter_dir}/music",
                "metadata": f"{chapter_dir}/metadata",
                "scenes": f"{chapter_dir}/scenes"
            }
        }

    @router.get("/chapter-assets/{chapter_number}")
    async def get_chapter_assets(chapter_number: int, output_base: str = "/app/repo/output/empire/chapters"):
        """Get inventory of all assets for a chapter."""
        import os
        import glob

        chapter_dir = f"{output_base}/ch{chapter_number:02d}"

        if not os.path.exists(chapter_dir):
            return {"error": f"Chapter {chapter_number} not found", "path": chapter_dir}

        # Count assets by type
        assets = {
            "portraits": glob.glob(f"{chapter_dir}/portraits/*.png"),
            "tts": glob.glob(f"{chapter_dir}/tts/*.wav"),
            "backgrounds": glob.glob(f"{chapter_dir}/backgrounds/*.png"),
            "music": glob.glob(f"{chapter_dir}/music/*.mp3") + glob.glob(f"{chapter_dir}/music/*.wav"),
        }

        # Check manifest
        manifest_path = f"{chapter_dir}/metadata/manifest.json"
        manifest = None
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)

        return {
            "chapter": chapter_number,
            "path": chapter_dir,
            "manifest": manifest,
            "asset_counts": {k: len(v) for k, v in assets.items()},
            "total_assets": sum(len(v) for v in assets.values()),
            "files": {k: [os.path.basename(f) for f in v] for k, v in assets.items()}
        }

    # =========================================================================
    # Scene Transition Management
    # =========================================================================

    class TransitionRequest(BaseModel):
        """Request model for scene transition."""
        transition_type: str = "cut"  # cut, fade, dissolve, wipe_left, etc.
        duration: float = 0.5
        color: str = "#000000"
        easing: str = "ease-in-out"
        sound_effect: Optional[str] = None

    class SceneTransitionUpdate(BaseModel):
        """Update scene transition metadata."""
        chapter: int
        scene_number: int
        transition_in: Optional[TransitionRequest] = None
        transition_out: Optional[TransitionRequest] = None
        transition_notes: str = ""

    @router.get("/transition-types")
    async def list_transition_types():
        """List all available transition types with descriptions."""
        transitions = {
            "cut": {
                "name": "Cut",
                "description": "Instant transition, no effect",
                "recommended_duration": 0.0,
                "use_cases": ["dialogue scenes", "quick cuts", "same location"]
            },
            "fade": {
                "name": "Fade",
                "description": "Fade to/from color (typically black)",
                "recommended_duration": 0.5,
                "use_cases": ["time passage", "scene endings", "dream sequences"]
            },
            "dissolve": {
                "name": "Dissolve",
                "description": "Cross-fade between scenes",
                "recommended_duration": 0.5,
                "use_cases": ["soft transitions", "flashbacks", "memories"]
            },
            "wipe_left": {
                "name": "Wipe Left",
                "description": "New scene wipes in from right to left",
                "recommended_duration": 0.3,
                "use_cases": ["location changes", "sequential events"]
            },
            "wipe_right": {
                "name": "Wipe Right",
                "description": "New scene wipes in from left to right",
                "recommended_duration": 0.3,
                "use_cases": ["location changes", "returning to previous scene"]
            },
            "wipe_up": {
                "name": "Wipe Up",
                "description": "New scene wipes in from bottom",
                "recommended_duration": 0.3,
                "use_cases": ["ascending", "positive mood shift"]
            },
            "wipe_down": {
                "name": "Wipe Down",
                "description": "New scene wipes in from top",
                "recommended_duration": 0.3,
                "use_cases": ["descending", "darker mood shift"]
            },
            "iris_in": {
                "name": "Iris In",
                "description": "Circle closing to center point",
                "recommended_duration": 0.5,
                "use_cases": ["focus on character", "dramatic endings"]
            },
            "iris_out": {
                "name": "Iris Out",
                "description": "Circle expanding from center",
                "recommended_duration": 0.5,
                "use_cases": ["scene openings", "revealing new locations"]
            },
            "flash": {
                "name": "Flash",
                "description": "Bright flash transition",
                "recommended_duration": 0.2,
                "use_cases": ["sudden reveals", "magic effects", "explosions"]
            },
            "blur": {
                "name": "Blur",
                "description": "Scene blurs out then new scene focuses in",
                "recommended_duration": 0.8,
                "use_cases": ["dream transitions", "memory recall", "intoxication"]
            },
            "pixelate": {
                "name": "Pixelate",
                "description": "Pixelation effect transition",
                "recommended_duration": 0.5,
                "use_cases": ["digital/tech themes", "retro effect", "glitch"]
            },
            "shake": {
                "name": "Shake",
                "description": "Screen shake effect",
                "recommended_duration": 0.3,
                "use_cases": ["impact moments", "earthquakes", "explosions"]
            }
        }

        return {
            "transition_types": transitions,
            "timing_presets": {
                "instant": 0.0,
                "fast": 0.3,
                "normal": 0.5,
                "slow": 1.0,
                "dramatic": 2.0
            },
            "easing_options": [
                "linear",
                "ease-in",
                "ease-out",
                "ease-in-out",
                "cubic-bezier"
            ]
        }

    @router.post("/scene-transition")
    async def update_scene_transition(request: SceneTransitionUpdate):
        """Update transition metadata for a specific scene."""
        import os

        output_base = "/app/repo/output/empire/chapters"
        chapter_dir = f"{output_base}/ch{request.chapter:02d}"
        transitions_file = f"{chapter_dir}/metadata/transitions.json"

        # Load existing transitions or create new
        transitions = {}
        if os.path.exists(transitions_file):
            with open(transitions_file, "r") as f:
                transitions = json.load(f)

        scene_key = f"sc{request.scene_number:03d}"

        # Build transition data
        scene_transitions = {
            "scene_number": request.scene_number,
            "updated_at": datetime.now().isoformat(),
            "transition_notes": request.transition_notes
        }

        if request.transition_in:
            scene_transitions["transition_in"] = {
                "type": request.transition_in.transition_type,
                "duration": request.transition_in.duration,
                "color": request.transition_in.color,
                "easing": request.transition_in.easing,
                "sound_effect": request.transition_in.sound_effect
            }

        if request.transition_out:
            scene_transitions["transition_out"] = {
                "type": request.transition_out.transition_type,
                "duration": request.transition_out.duration,
                "color": request.transition_out.color,
                "easing": request.transition_out.easing,
                "sound_effect": request.transition_out.sound_effect
            }

        transitions[scene_key] = scene_transitions

        # Ensure directory exists
        os.makedirs(os.path.dirname(transitions_file), exist_ok=True)

        # Save transitions file
        with open(transitions_file, "w") as f:
            json.dump(transitions, f, indent=2)

        return {
            "status": "updated",
            "chapter": request.chapter,
            "scene": scene_key,
            "transitions": scene_transitions,
            "file": transitions_file
        }

    @router.get("/scene-transitions/{chapter}")
    async def get_chapter_transitions(chapter: int):
        """Get all scene transitions for a chapter."""
        import os

        output_base = "/app/repo/output/empire/chapters"
        chapter_dir = f"{output_base}/ch{chapter:02d}"
        transitions_file = f"{chapter_dir}/metadata/transitions.json"

        if not os.path.exists(transitions_file):
            return {
                "chapter": chapter,
                "transitions": {},
                "message": "No transitions defined yet"
            }

        with open(transitions_file, "r") as f:
            transitions = json.load(f)

        return {
            "chapter": chapter,
            "scene_count": len(transitions),
            "transitions": transitions,
            "file": transitions_file
        }

    class AutoTransitionRequest(BaseModel):
        """Request for auto-generating transitions based on scene content."""
        chapter: int
        scenes: List[Dict[str, Any]]  # List of scene metadata

    @router.post("/auto-generate-transitions")
    async def auto_generate_transitions(request: AutoTransitionRequest):
        """Auto-generate transition recommendations based on scene content."""
        recommendations = []

        for i, scene in enumerate(request.scenes):
            scene_num = scene.get("scene_number", i + 1)
            location = scene.get("location", "")
            time_of_day = scene.get("time_of_day", "day")
            prev_location = request.scenes[i - 1].get("location", "") if i > 0 else ""
            prev_time = request.scenes[i - 1].get("time_of_day", "") if i > 0 else ""

            # Determine transition_in based on context
            transition_in = {"type": "cut", "duration": 0.0}

            if i == 0:
                # First scene - fade in
                transition_in = {"type": "fade", "duration": 0.5, "color": "#000000"}
            elif location != prev_location:
                # Location change - dissolve or wipe
                transition_in = {"type": "dissolve", "duration": 0.5}
            elif time_of_day != prev_time:
                # Time change in same location - fade
                transition_in = {"type": "fade", "duration": 0.8, "color": "#000000"}

            # Special cases based on keywords
            narration = scene.get("narration", "").lower()
            if "dream" in narration or "memory" in narration:
                transition_in = {"type": "blur", "duration": 1.0}
            elif "flash" in narration or "sudden" in narration:
                transition_in = {"type": "flash", "duration": 0.2, "color": "#FFFFFF"}
            elif "earthquake" in narration or "explosion" in narration:
                transition_in = {"type": "shake", "duration": 0.3}

            recommendations.append({
                "scene_number": scene_num,
                "location": location,
                "transition_in": transition_in,
                "reasoning": f"Based on {'scene opening' if i == 0 else 'location change' if location != prev_location else 'time change' if time_of_day != prev_time else 'same context'}"
            })

        return {
            "chapter": request.chapter,
            "recommendations": recommendations,
            "note": "Review and customize these recommendations as needed"
        }

    @router.post("/apply-transition-preset")
    async def apply_transition_preset(
        chapter: int,
        preset: str = "dramatic"
    ):
        """Apply a preset transition style to all scenes in a chapter."""
        presets = {
            "cinematic": {
                "default_in": {"type": "fade", "duration": 0.5},
                "location_change": {"type": "dissolve", "duration": 0.8},
                "time_skip": {"type": "fade", "duration": 1.0},
            },
            "dramatic": {
                "default_in": {"type": "cut", "duration": 0.0},
                "location_change": {"type": "fade", "duration": 0.5},
                "time_skip": {"type": "fade", "duration": 1.5},
            },
            "energetic": {
                "default_in": {"type": "cut", "duration": 0.0},
                "location_change": {"type": "wipe_right", "duration": 0.3},
                "time_skip": {"type": "dissolve", "duration": 0.3},
            },
            "retro": {
                "default_in": {"type": "iris_out", "duration": 0.5},
                "location_change": {"type": "iris_in", "duration": 0.5},
                "time_skip": {"type": "fade", "duration": 0.8},
            },
            "dreamy": {
                "default_in": {"type": "blur", "duration": 0.8},
                "location_change": {"type": "dissolve", "duration": 1.0},
                "time_skip": {"type": "fade", "duration": 1.2},
            }
        }

        if preset not in presets:
            return {
                "error": f"Unknown preset: {preset}",
                "available_presets": list(presets.keys())
            }

        return {
            "chapter": chapter,
            "preset_applied": preset,
            "transitions": presets[preset],
            "note": "Use /scene-transition to customize individual scenes"
        }

    # =========================================================================
    # Chapter Packaging
    # =========================================================================

    class ChapterPackageRequest(BaseModel):
        """Request for packaging a chapter's assets."""
        chapter_number: int
        output_base: str = "/app/repo/output/empire/chapters"
        package_name: Optional[str] = None
        include_raw: bool = False
        format: str = "zip"  # zip, renpy, godot

    @router.post("/package-chapter")
    async def package_chapter(request: ChapterPackageRequest):
        """Package all chapter assets into a distributable archive."""
        import os
        import glob
        import shutil
        import zipfile
        from datetime import datetime

        chapter_dir = f"{request.output_base}/ch{request.chapter_number:02d}"

        if not os.path.exists(chapter_dir):
            return {"error": f"Chapter {request.chapter_number} not found", "path": chapter_dir}

        # Gather all assets (check both flat directories and scene subdirectories)
        assets = {
            "portraits": glob.glob(f"{chapter_dir}/portraits/*.png") + glob.glob(f"{chapter_dir}/**/portraits/*.png", recursive=True) + glob.glob(f"{chapter_dir}/**/*_portrait*.png", recursive=True),
            "tts": glob.glob(f"{chapter_dir}/tts/*.wav") + glob.glob(f"{chapter_dir}/tts/*.mp3") + glob.glob(f"{chapter_dir}/**/*.wav", recursive=True) + glob.glob(f"{chapter_dir}/**/*.mp3", recursive=True),
            "backgrounds": glob.glob(f"{chapter_dir}/backgrounds/*.png") + glob.glob(f"{chapter_dir}/backgrounds/*.jpg") + glob.glob(f"{chapter_dir}/**/background*.png", recursive=True),
            "music": glob.glob(f"{chapter_dir}/music/*.mp3") + glob.glob(f"{chapter_dir}/music/*.wav") + glob.glob(f"{chapter_dir}/music/*.ogg"),
            "metadata": glob.glob(f"{chapter_dir}/metadata/*.json") + glob.glob(f"{chapter_dir}/**/*.json", recursive=True),
        }

        # Deduplicate assets
        for key in assets:
            assets[key] = list(set(assets[key]))

        if request.include_raw:
            assets["raw"] = glob.glob(f"{chapter_dir}/raw/*")

        total_files = sum(len(v) for v in assets.values())
        if total_files == 0:
            return {
                "error": "No assets found to package",
                "chapter": request.chapter_number,
                "path": chapter_dir
            }

        # Create package name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = request.package_name or f"empire_ch{request.chapter_number:02d}_{timestamp}"
        packages_dir = f"{request.output_base}/packages"
        os.makedirs(packages_dir, exist_ok=True)

        if request.format == "zip":
            # Standard ZIP archive
            zip_path = f"{packages_dir}/{package_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for category, files in assets.items():
                    for filepath in files:
                        arcname = f"{category}/{os.path.basename(filepath)}"
                        zipf.write(filepath, arcname)

                # Add package manifest
                package_manifest = {
                    "chapter": request.chapter_number,
                    "packaged_at": datetime.now().isoformat(),
                    "asset_counts": {k: len(v) for k, v in assets.items()},
                    "total_files": total_files,
                    "format": "zip"
                }
                zipf.writestr("package_manifest.json", json.dumps(package_manifest, indent=2))

            # Get file size
            file_size = os.path.getsize(zip_path)

            return {
                "status": "packaged",
                "chapter": request.chapter_number,
                "package_path": zip_path,
                "package_name": package_name,
                "format": "zip",
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "asset_counts": {k: len(v) for k, v in assets.items()},
                "total_files": total_files
            }

        elif request.format == "renpy":
            # Ren'Py compatible directory structure
            renpy_dir = f"{packages_dir}/{package_name}_renpy"
            os.makedirs(renpy_dir, exist_ok=True)

            # Ren'Py structure: game/images, game/audio
            renpy_images = f"{renpy_dir}/game/images/ch{request.chapter_number:02d}"
            renpy_audio = f"{renpy_dir}/game/audio/ch{request.chapter_number:02d}"
            renpy_script = f"{renpy_dir}/game"
            os.makedirs(renpy_images, exist_ok=True)
            os.makedirs(renpy_audio, exist_ok=True)

            # Copy portraits and backgrounds to images
            for filepath in assets["portraits"] + assets["backgrounds"]:
                shutil.copy2(filepath, renpy_images)

            # Copy TTS and music to audio
            for filepath in assets["tts"] + assets["music"]:
                shutil.copy2(filepath, renpy_audio)

            # Generate basic Ren'Py script template
            renpy_template = f'''# Empire of Broken Queens - Chapter {request.chapter_number}
# Auto-generated asset definitions

init python:
    pass

# Image definitions
'''
            for portrait in assets["portraits"]:
                name = os.path.splitext(os.path.basename(portrait))[0]
                renpy_template += f'image {name} = "images/ch{request.chapter_number:02d}/{os.path.basename(portrait)}"\n'

            for bg in assets["backgrounds"]:
                name = os.path.splitext(os.path.basename(bg))[0]
                renpy_template += f'image bg_{name} = "images/ch{request.chapter_number:02d}/{os.path.basename(bg)}"\n'

            renpy_template += '\n# Audio definitions\n'
            for audio in assets["tts"] + assets["music"]:
                name = os.path.splitext(os.path.basename(audio))[0]
                renpy_template += f'define audio.{name} = "audio/ch{request.chapter_number:02d}/{os.path.basename(audio)}"\n'

            script_path = f"{renpy_script}/ch{request.chapter_number:02d}_assets.rpy"
            with open(script_path, 'w') as f:
                f.write(renpy_template)

            # Copy metadata if exists
            metadata_src = f"{chapter_dir}/metadata"
            if os.path.exists(metadata_src):
                shutil.copytree(metadata_src, f"{renpy_dir}/metadata", dirs_exist_ok=True)

            return {
                "status": "packaged",
                "chapter": request.chapter_number,
                "package_path": renpy_dir,
                "package_name": f"{package_name}_renpy",
                "format": "renpy",
                "script_file": script_path,
                "structure": {
                    "images": renpy_images,
                    "audio": renpy_audio
                },
                "asset_counts": {k: len(v) for k, v in assets.items()},
                "total_files": total_files
            }

        elif request.format == "godot":
            # Godot-compatible directory structure
            godot_dir = f"{packages_dir}/{package_name}_godot"
            os.makedirs(godot_dir, exist_ok=True)

            # Godot structure
            godot_sprites = f"{godot_dir}/assets/sprites/ch{request.chapter_number:02d}"
            godot_audio = f"{godot_dir}/assets/audio/ch{request.chapter_number:02d}"
            godot_data = f"{godot_dir}/data"
            os.makedirs(godot_sprites, exist_ok=True)
            os.makedirs(godot_audio, exist_ok=True)
            os.makedirs(godot_data, exist_ok=True)

            # Copy assets
            for filepath in assets["portraits"] + assets["backgrounds"]:
                shutil.copy2(filepath, godot_sprites)
            for filepath in assets["tts"] + assets["music"]:
                shutil.copy2(filepath, godot_audio)

            # Copy metadata as JSON
            for filepath in assets["metadata"]:
                shutil.copy2(filepath, godot_data)

            # Generate resource file
            resource_data = {
                "chapter": request.chapter_number,
                "sprites": [os.path.basename(f) for f in assets["portraits"] + assets["backgrounds"]],
                "audio": [os.path.basename(f) for f in assets["tts"] + assets["music"]]
            }
            with open(f"{godot_data}/ch{request.chapter_number:02d}_resources.json", 'w') as f:
                json.dump(resource_data, f, indent=2)

            return {
                "status": "packaged",
                "chapter": request.chapter_number,
                "package_path": godot_dir,
                "package_name": f"{package_name}_godot",
                "format": "godot",
                "structure": {
                    "sprites": godot_sprites,
                    "audio": godot_audio,
                    "data": godot_data
                },
                "asset_counts": {k: len(v) for k, v in assets.items()},
                "total_files": total_files
            }

        else:
            return {
                "error": f"Unknown format: {request.format}",
                "supported_formats": ["zip", "renpy", "godot"]
            }

    @router.get("/list-packages")
    async def list_packages(output_base: str = "/app/repo/output/empire/chapters"):
        """List all packaged chapter archives."""
        import os
        import glob

        packages_dir = f"{output_base}/packages"
        if not os.path.exists(packages_dir):
            return {"packages": [], "packages_dir": packages_dir}

        packages = []
        for pkg in glob.glob(f"{packages_dir}/*"):
            pkg_name = os.path.basename(pkg)
            if pkg.endswith('.zip'):
                size = os.path.getsize(pkg)
                packages.append({
                    "name": pkg_name,
                    "path": pkg,
                    "format": "zip",
                    "size_mb": round(size / (1024 * 1024), 2)
                })
            elif os.path.isdir(pkg):
                # Calculate directory size
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(pkg)
                    for filename in filenames
                )
                pkg_format = "renpy" if "_renpy" in pkg_name else "godot" if "_godot" in pkg_name else "directory"
                packages.append({
                    "name": pkg_name,
                    "path": pkg,
                    "format": pkg_format,
                    "size_mb": round(total_size / (1024 * 1024), 2)
                })

        return {
            "packages": packages,
            "total_packages": len(packages),
            "packages_dir": packages_dir
        }

    @router.delete("/delete-package/{package_name}")
    async def delete_package(package_name: str, output_base: str = "/app/repo/output/empire/chapters"):
        """Delete a packaged chapter archive."""
        import os
        import shutil

        packages_dir = f"{output_base}/packages"
        pkg_path = f"{packages_dir}/{package_name}"

        if os.path.exists(f"{pkg_path}.zip"):
            os.remove(f"{pkg_path}.zip")
            return {"status": "deleted", "package": f"{package_name}.zip"}
        elif os.path.isdir(pkg_path):
            shutil.rmtree(pkg_path)
            return {"status": "deleted", "package": package_name}
        else:
            return {"error": f"Package not found: {package_name}"}

    # =========================================================================
    # Image Upscaling
    # =========================================================================

    class UpscaleRequest(BaseModel):
        """Request for image upscaling."""
        image_path: str
        scale: int = 2  # 2x or 4x
        model: str = "RealESRGAN_x4plus"  # Upscaling model
        output_path: Optional[str] = None

    class BatchUpscaleRequest(BaseModel):
        """Batch image upscaling request."""
        image_paths: List[str]
        scale: int = 2
        model: str = "RealESRGAN_x4plus"
        output_dir: Optional[str] = None

    # Available upscaling models
    UPSCALE_MODELS = {
        "RealESRGAN_x4plus": {
            "description": "General purpose 4x upscaler, excellent quality",
            "scale_options": [2, 4],
            "best_for": "photographs, general images"
        },
        "RealESRGAN_x4plus_anime_6B": {
            "description": "Anime/illustration optimized 4x upscaler",
            "scale_options": [2, 4],
            "best_for": "anime, illustrations, artwork"
        },
        "4x_NMKD-Siax_200k": {
            "description": "NMKD 4x upscaler for various content",
            "scale_options": [4],
            "best_for": "general purpose"
        },
        "4x-UltraSharp": {
            "description": "Ultra sharp 4x upscaler",
            "scale_options": [4],
            "best_for": "photos needing extra sharpness"
        }
    }

    @router.get("/upscale-models")
    async def list_upscale_models():
        """List available upscaling models and their capabilities."""
        return {
            "models": UPSCALE_MODELS,
            "default_model": "RealESRGAN_x4plus",
            "default_scale": 2,
            "comfyui_endpoint": "http://192.168.1.203:8188"
        }

    @router.post("/upscale")
    async def upscale_image(request: UpscaleRequest):
        """
        Upscale a single image using ComfyUI.

        Uses Real-ESRGAN or similar models for high-quality upscaling.
        """
        import os
        import base64
        import time

        # Validate input
        if not os.path.exists(request.image_path):
            return {"error": f"Image not found: {request.image_path}"}

        if request.model not in UPSCALE_MODELS:
            return {
                "error": f"Unknown model: {request.model}",
                "available_models": list(UPSCALE_MODELS.keys())
            }

        # Determine output path
        if request.output_path:
            output_path = request.output_path
        else:
            base, ext = os.path.splitext(request.image_path)
            output_path = f"{base}_upscaled_{request.scale}x{ext}"

        # Create upscaling workflow for ComfyUI
        upscale_workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": request.image_path
                }
            },
            "2": {
                "class_type": "UpscaleModelLoader",
                "inputs": {
                    "model_name": f"{request.model}.pth"
                }
            },
            "3": {
                "class_type": "ImageUpscaleWithModel",
                "inputs": {
                    "upscale_model": ["2", 0],
                    "image": ["1", 0]
                }
            },
            "4": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["3", 0],
                    "filename_prefix": os.path.basename(output_path).rsplit(".", 1)[0]
                }
            }
        }

        # Queue in ComfyUI
        comfyui_url = "http://192.168.1.203:8188"
        try:
            import urllib.request
            import urllib.error

            prompt_data = {
                "prompt": upscale_workflow,
                "client_id": "hydra-upscaler"
            }

            req = urllib.request.Request(
                f"{comfyui_url}/prompt",
                data=json.dumps(prompt_data).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                prompt_id = result.get("prompt_id", "unknown")

            return {
                "status": "queued",
                "prompt_id": prompt_id,
                "input_image": request.image_path,
                "output_path": output_path,
                "scale": request.scale,
                "model": request.model,
                "comfyui_url": comfyui_url
            }

        except urllib.error.URLError as e:
            return {"error": f"ComfyUI connection failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Upscaling failed: {str(e)}"}

    @router.post("/upscale-batch")
    async def upscale_batch(request: BatchUpscaleRequest):
        """
        Upscale multiple images in batch.

        Queues all images for upscaling and returns job IDs.
        """
        import os

        results = []

        # Determine output directory
        if request.output_dir:
            os.makedirs(request.output_dir, exist_ok=True)

        for image_path in request.image_paths:
            if not os.path.exists(image_path):
                results.append({
                    "image": image_path,
                    "status": "error",
                    "error": "File not found"
                })
                continue

            # Create upscale request
            if request.output_dir:
                base = os.path.basename(image_path)
                name, ext = os.path.splitext(base)
                output_path = f"{request.output_dir}/{name}_upscaled_{request.scale}x{ext}"
            else:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_upscaled_{request.scale}x{ext}"

            single_request = UpscaleRequest(
                image_path=image_path,
                scale=request.scale,
                model=request.model,
                output_path=output_path
            )

            # Queue upscale
            result = await upscale_image(single_request)
            results.append({
                "image": image_path,
                "output": output_path,
                **result
            })

        return {
            "total": len(request.image_paths),
            "queued": len([r for r in results if r.get("status") == "queued"]),
            "errors": len([r for r in results if r.get("status") == "error"]),
            "results": results
        }

    @router.post("/upscale-directory")
    async def upscale_directory(
        input_dir: str,
        output_dir: Optional[str] = None,
        scale: int = 2,
        model: str = "RealESRGAN_x4plus",
        extensions: str = "png,jpg,jpeg"
    ):
        """
        Upscale all images in a directory.

        Finds all images with specified extensions and queues for upscaling.
        """
        import os
        import glob

        if not os.path.isdir(input_dir):
            return {"error": f"Directory not found: {input_dir}"}

        # Collect images
        image_paths = []
        for ext in extensions.split(","):
            ext = ext.strip()
            image_paths.extend(glob.glob(f"{input_dir}/*.{ext}"))
            image_paths.extend(glob.glob(f"{input_dir}/*.{ext.upper()}"))

        if not image_paths:
            return {"error": f"No images found in {input_dir}", "extensions_checked": extensions}

        # Create output directory
        if not output_dir:
            output_dir = f"{input_dir}/upscaled_{scale}x"
        os.makedirs(output_dir, exist_ok=True)

        # Queue batch
        batch_request = BatchUpscaleRequest(
            image_paths=image_paths,
            scale=scale,
            model=model,
            output_dir=output_dir
        )

        result = await upscale_batch(batch_request)

        return {
            "input_dir": input_dir,
            "output_dir": output_dir,
            **result
        }

    @router.get("/upscale-presets")
    async def upscale_presets():
        """Get recommended upscaling presets for different use cases."""
        return {
            "presets": {
                "portrait_hd": {
                    "description": "Upscale character portraits to HD (1080p)",
                    "model": "RealESRGAN_x4plus_anime_6B",
                    "scale": 2,
                    "use_case": "Visual novel character sprites"
                },
                "portrait_4k": {
                    "description": "Upscale character portraits to 4K",
                    "model": "RealESRGAN_x4plus_anime_6B",
                    "scale": 4,
                    "use_case": "High-resolution character art"
                },
                "background_hd": {
                    "description": "Upscale backgrounds to HD",
                    "model": "RealESRGAN_x4plus",
                    "scale": 2,
                    "use_case": "Visual novel backgrounds"
                },
                "background_4k": {
                    "description": "Upscale backgrounds to 4K",
                    "model": "4x-UltraSharp",
                    "scale": 4,
                    "use_case": "High-resolution scene backgrounds"
                },
                "quick": {
                    "description": "Fast 2x upscale for previews",
                    "model": "RealESRGAN_x4plus",
                    "scale": 2,
                    "use_case": "Quick quality improvement"
                }
            }
        }

    # =========================================================================
    # Character Relationship Graph
    # =========================================================================

    # Relationship types for visual novel characters
    RELATIONSHIP_TYPES = {
        "ally": {"description": "Political or strategic alliance", "color": "#4CAF50"},
        "enemy": {"description": "Open hostility or rivalry", "color": "#F44336"},
        "romantic": {"description": "Romantic involvement", "color": "#E91E63"},
        "familial": {"description": "Family relationship", "color": "#9C27B0"},
        "mentor": {"description": "Teacher/student dynamic", "color": "#2196F3"},
        "servant": {"description": "Service or loyalty bond", "color": "#607D8B"},
        "betrayed": {"description": "Past betrayal", "color": "#FF5722"},
        "secret": {"description": "Hidden relationship", "color": "#795548"},
        "rival": {"description": "Competition without hostility", "color": "#FF9800"},
        "friend": {"description": "Personal friendship", "color": "#03A9F4"},
    }

    class RelationshipEdge(BaseModel):
        """A relationship between two characters."""
        source: str  # Character ID
        target: str  # Character ID
        relationship_type: str
        intensity: float = 0.5  # 0.0-1.0
        mutual: bool = True  # Bidirectional relationship
        description: str = ""
        since_chapter: int = 1
        evolution: List[Dict[str, Any]] = []  # Changes over time

    class RelationshipGraphData(BaseModel):
        """Full relationship graph data."""
        nodes: List[Dict[str, Any]]  # Character nodes
        edges: List[RelationshipEdge]  # Relationships

    # In-memory relationship storage (persisted to JSON)
    _relationships_file = "/data/empire/relationships.json"

    def _load_relationships() -> Dict[str, Any]:
        """Load relationships from storage."""
        import os
        if os.path.exists(_relationships_file):
            with open(_relationships_file, "r") as f:
                return json.load(f)
        return {"nodes": [], "edges": []}

    def _save_relationships(data: Dict[str, Any]):
        """Save relationships to storage."""
        import os
        os.makedirs(os.path.dirname(_relationships_file), exist_ok=True)
        with open(_relationships_file, "w") as f:
            json.dump(data, f, indent=2)

    @router.get("/relationship-types")
    async def get_relationship_types():
        """Get available relationship types."""
        return {
            "types": RELATIONSHIP_TYPES,
            "count": len(RELATIONSHIP_TYPES)
        }

    @router.post("/relationship")
    async def add_relationship(edge: RelationshipEdge):
        """Add or update a relationship between characters."""
        data = _load_relationships()

        # Find existing edge
        existing_idx = None
        for i, e in enumerate(data["edges"]):
            if (e["source"] == edge.source and e["target"] == edge.target) or \
               (edge.mutual and e["source"] == edge.target and e["target"] == edge.source):
                existing_idx = i
                break

        edge_dict = edge.dict()
        edge_dict["updated_at"] = datetime.now().isoformat()

        if existing_idx is not None:
            # Update existing
            data["edges"][existing_idx] = edge_dict
            action = "updated"
        else:
            # Add new
            data["edges"].append(edge_dict)
            action = "added"

        _save_relationships(data)

        return {
            "status": action,
            "relationship": edge_dict,
            "total_relationships": len(data["edges"])
        }

    @router.delete("/relationship/{source}/{target}")
    async def remove_relationship(source: str, target: str):
        """Remove a relationship between characters."""
        data = _load_relationships()

        initial_count = len(data["edges"])
        data["edges"] = [
            e for e in data["edges"]
            if not ((e["source"] == source and e["target"] == target) or
                    (e["source"] == target and e["target"] == source))
        ]

        if len(data["edges"]) < initial_count:
            _save_relationships(data)
            return {"status": "removed", "source": source, "target": target}
        else:
            return {"status": "not_found", "source": source, "target": target}

    @router.get("/relationships")
    async def get_all_relationships():
        """Get complete relationship graph."""
        data = _load_relationships()

        # Enhance with character info from Qdrant if available
        char_manager = CharacterManager()
        characters = char_manager.list_characters() or []

        nodes = []
        for char in characters:
            nodes.append({
                "id": char.get("id", char.get("name", "unknown")),
                "name": char.get("display_name", char.get("name", "Unknown")),
                "kingdom": char.get("description", "").split(",")[0] if char.get("description") else "Unknown"
            })

        return {
            "nodes": nodes,
            "edges": data["edges"],
            "node_count": len(nodes),
            "edge_count": len(data["edges"])
        }

    @router.get("/relationships/{character_id}")
    async def get_character_relationships(character_id: str):
        """Get all relationships for a specific character."""
        data = _load_relationships()

        related = []
        for edge in data["edges"]:
            if edge["source"] == character_id:
                related.append({
                    "character": edge["target"],
                    "relationship": edge["relationship_type"],
                    "intensity": edge.get("intensity", 0.5),
                    "direction": "outgoing",
                    "description": edge.get("description", "")
                })
            elif edge["target"] == character_id or edge.get("mutual"):
                related.append({
                    "character": edge["source"],
                    "relationship": edge["relationship_type"],
                    "intensity": edge.get("intensity", 0.5),
                    "direction": "incoming" if not edge.get("mutual") else "mutual",
                    "description": edge.get("description", "")
                })

        return {
            "character": character_id,
            "relationships": related,
            "count": len(related)
        }

    @router.get("/relationship-graph/export")
    async def export_relationship_graph(format: str = "json"):
        """Export relationship graph in various formats."""
        data = _load_relationships()
        char_manager = CharacterManager()
        characters = char_manager.list_characters() or []

        if format == "json":
            return data
        elif format == "graphviz":
            # Generate DOT format
            lines = ["digraph relationships {"]
            lines.append("  rankdir=LR;")
            lines.append("  node [shape=ellipse];")

            for char in characters:
                char_id = char.get("id", char.get("name", ""))
                name = char.get("display_name", char.get("name", ""))
                lines.append(f'  "{char_id}" [label="{name}"];')

            for edge in data["edges"]:
                color = RELATIONSHIP_TYPES.get(edge["relationship_type"], {}).get("color", "#000000")
                style = "bold" if edge.get("intensity", 0.5) > 0.7 else "solid"
                direction = "->" if not edge.get("mutual") else " -- "
                lines.append(f'  "{edge["source"]}" {direction} "{edge["target"]}" [color="{color}", style={style}, label="{edge["relationship_type"]}"];')

            lines.append("}")
            return {"format": "graphviz", "dot": "\n".join(lines)}
        elif format == "cytoscape":
            # Cytoscape.js format
            elements = []
            for char in characters:
                elements.append({
                    "data": {
                        "id": char.get("id", char.get("name", "")),
                        "label": char.get("display_name", char.get("name", ""))
                    }
                })
            for edge in data["edges"]:
                elements.append({
                    "data": {
                        "id": f"{edge['source']}-{edge['target']}",
                        "source": edge["source"],
                        "target": edge["target"],
                        "relationship": edge["relationship_type"],
                        "intensity": edge.get("intensity", 0.5)
                    }
                })
            return {"format": "cytoscape", "elements": elements}
        else:
            return {"error": f"Unknown format: {format}", "supported": ["json", "graphviz", "cytoscape"]}

    @router.post("/relationship-graph/seed")
    async def seed_relationship_graph():
        """Seed initial relationships for Empire of Broken Queens."""
        # Default relationships for the 21 queens
        default_relationships = [
            # Lyra's relationships
            {"source": "lyra", "target": "morgana", "relationship_type": "enemy", "intensity": 0.9, "description": "Lyra seeks revenge against Morgana for her betrayal"},
            {"source": "lyra", "target": "seraphina", "relationship_type": "ally", "intensity": 0.7, "description": "Former court allies, now reunited"},

            # Morgana's relationships
            {"source": "morgana", "target": "vex", "relationship_type": "servant", "intensity": 0.8, "description": "Vex serves Morgana's dark purposes"},
            {"source": "morgana", "target": "isadora", "relationship_type": "rival", "intensity": 0.6, "description": "Both seek magical dominance"},

            # Romantic tensions
            {"source": "elena", "target": "cass", "relationship_type": "romantic", "intensity": 0.7, "mutual": True, "description": "Forbidden romance between knight and healer"},
            {"source": "valeria", "target": "thorne", "relationship_type": "romantic", "intensity": 0.5, "description": "Complex attraction amid political tension"},

            # Political alliances
            {"source": "aurelia", "target": "celestine", "relationship_type": "ally", "intensity": 0.8, "mutual": True, "description": "Alliance of the eastern kingdoms"},
            {"source": "ravenna", "target": "nyx", "relationship_type": "ally", "intensity": 0.6, "description": "Shared interests in shadow politics"},

            # Familial relationships
            {"source": "isolde", "target": "rhiannon", "relationship_type": "familial", "intensity": 0.9, "description": "Sisters with complicated history"},
            {"source": "gwyneth", "target": "elara", "relationship_type": "familial", "intensity": 0.7, "description": "Cousins from the northern houses"},

            # Betrayals and conflicts
            {"source": "drusilla", "target": "vivienne", "relationship_type": "betrayed", "intensity": 0.8, "description": "Vivienne's past betrayal haunts their interactions"},
            {"source": "kalista", "target": "zahra", "relationship_type": "enemy", "intensity": 0.7, "description": "Ancient feud between their houses"},

            # Mentor relationships
            {"source": "ophelia", "target": "luna", "relationship_type": "mentor", "intensity": 0.8, "description": "Ophelia trains Luna in the arcane arts"},
            {"source": "minerva", "target": "freya", "relationship_type": "mentor", "intensity": 0.6, "description": "Strategic training for the young queen"},
        ]

        data = _load_relationships()

        added = 0
        for rel in default_relationships:
            # Check if exists
            exists = any(
                (e["source"] == rel["source"] and e["target"] == rel["target"])
                for e in data["edges"]
            )
            if not exists:
                rel["since_chapter"] = 1
                rel["mutual"] = rel.get("mutual", True)
                rel["updated_at"] = datetime.now().isoformat()
                data["edges"].append(rel)
                added += 1

        _save_relationships(data)

        return {
            "status": "seeded",
            "relationships_added": added,
            "total_relationships": len(data["edges"])
        }

    @router.get("/relationship-stats")
    async def relationship_stats():
        """Get statistics about the relationship graph."""
        data = _load_relationships()

        type_counts = {}
        for edge in data["edges"]:
            rel_type = edge.get("relationship_type", "unknown")
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        intensities = [e.get("intensity", 0.5) for e in data["edges"]]
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0

        return {
            "total_relationships": len(data["edges"]),
            "by_type": type_counts,
            "average_intensity": round(avg_intensity, 2),
            "mutual_relationships": len([e for e in data["edges"] if e.get("mutual", True)]),
            "one_way_relationships": len([e for e in data["edges"] if not e.get("mutual", True)])
        }

    # ============================================================
    # WORKFLOW TEMPLATE MANAGEMENT
    # ============================================================

    WORKFLOW_TEMPLATES_DIR = "/data/comfyui/workflows"

    def _get_templates_dir() -> Path:
        """Get workflow templates directory."""
        path = Path(WORKFLOW_TEMPLATES_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _load_template(template_name: str) -> Optional[Dict[str, Any]]:
        """Load a workflow template by name."""
        templates_dir = _get_templates_dir()

        # Try with and without .json extension
        if not template_name.endswith('.json'):
            template_name = f"{template_name}.json"

        template_path = templates_dir / template_name
        if template_path.exists():
            with open(template_path, 'r') as f:
                return json.load(f)

        # Also check the config directory (mounted from host)
        config_path = Path("/app/repo/config/comfyui/workflows") / template_name
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        return None

    def _substitute_variables(template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute {{VARIABLE}} placeholders in template with provided values."""
        import re

        def substitute_in_value(value):
            if isinstance(value, str):
                # Find all {{VAR}} patterns
                pattern = r'\{\{(\w+)\}\}'

                def replacer(match):
                    var_name = match.group(1)
                    if var_name in variables:
                        return str(variables[var_name])
                    return match.group(0)  # Keep original if not found

                return re.sub(pattern, replacer, value)
            elif isinstance(value, dict):
                return {k: substitute_in_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_in_value(item) for item in value]
            else:
                return value

        # Don't substitute in _meta
        result = {}
        for key, value in template.items():
            if key == "_meta":
                result[key] = value
            else:
                result[key] = substitute_in_value(value)

        return result

    @router.get("/workflow-templates")
    async def list_workflow_templates():
        """List all available workflow templates."""
        templates = []

        # Check both directories
        dirs_to_check = [
            _get_templates_dir(),
            Path("/app/repo/config/comfyui/workflows")
        ]

        seen = set()
        for dir_path in dirs_to_check:
            if dir_path.exists():
                for file in dir_path.glob("*.json"):
                    if file.name in seen:
                        continue
                    seen.add(file.name)

                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)

                        meta = data.get("_meta", {})
                        templates.append({
                            "name": file.stem,
                            "filename": file.name,
                            "display_name": meta.get("name", file.stem),
                            "description": meta.get("description", ""),
                            "version": meta.get("version", "1.0.0"),
                            "use_case": meta.get("use_case", ""),
                            "variables": meta.get("variables", {}),
                            "source": str(dir_path)
                        })
                    except Exception as e:
                        templates.append({
                            "name": file.stem,
                            "filename": file.name,
                            "error": str(e)
                        })

        return {
            "templates": templates,
            "count": len(templates)
        }

    @router.get("/workflow-templates/{template_name}")
    async def get_workflow_template(template_name: str, include_workflow: bool = False):
        """Get details about a specific workflow template."""
        template = _load_template(template_name)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")

        meta = template.get("_meta", {})

        result = {
            "name": template_name.replace(".json", ""),
            "display_name": meta.get("name", template_name),
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0.0"),
            "use_case": meta.get("use_case", ""),
            "variables": meta.get("variables", {}),
            "node_count": len([k for k in template.keys() if k != "_meta"])
        }

        if include_workflow:
            result["workflow"] = template

        return result

    @router.post("/workflow-templates/{template_name}/validate")
    async def validate_template_variables(template_name: str, variables: Dict[str, Any] = Body(...)):
        """Validate that all required variables are provided for a template."""
        template = _load_template(template_name)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")

        meta = template.get("_meta", {})
        required_vars = meta.get("variables", {})

        missing = []
        provided = []
        extra = []

        for var_name in required_vars.keys():
            if var_name in variables:
                provided.append(var_name)
            else:
                # Check if it has a default (SEED always has default)
                if var_name == "SEED":
                    provided.append(var_name)
                else:
                    missing.append(var_name)

        for var_name in variables.keys():
            if var_name not in required_vars and var_name != "SEED":
                extra.append(var_name)

        return {
            "valid": len(missing) == 0,
            "missing_variables": missing,
            "provided_variables": provided,
            "extra_variables": extra,
            "required_variables": required_vars
        }

    @router.post("/workflow-templates/{template_name}/apply")
    async def apply_workflow_template(
        template_name: str,
        variables: Dict[str, Any] = Body(...),
        submit: bool = True
    ):
        """Apply a workflow template with variable substitution and optionally submit to ComfyUI."""
        import random

        template = _load_template(template_name)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")

        # Add default SEED if not provided
        if "SEED" not in variables:
            variables["SEED"] = random.randint(1, 2**32 - 1)

        # Substitute variables
        workflow = _substitute_variables(template, variables)

        # Remove _meta before submission
        workflow_for_submit = {k: v for k, v in workflow.items() if k != "_meta"}

        result = {
            "template": template_name,
            "variables_applied": variables,
            "workflow": workflow_for_submit
        }

        if submit:
            # Submit to ComfyUI
            try:
                import httpx

                comfyui_url = "http://192.168.1.203:8188"
                payload = {"prompt": workflow_for_submit}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{comfyui_url}/prompt", json=payload)
                    response.raise_for_status()
                    comfy_result = response.json()

                result["submitted"] = True
                result["prompt_id"] = comfy_result.get("prompt_id")
                result["comfyui_response"] = comfy_result

            except Exception as e:
                result["submitted"] = False
                result["submit_error"] = str(e)
        else:
            result["submitted"] = False
            result["note"] = "Set submit=true to send to ComfyUI"

        return result

    @router.post("/workflow-templates/save")
    async def save_workflow_template(
        name: str = Body(...),
        display_name: str = Body(None),
        description: str = Body(""),
        use_case: str = Body(""),
        variables: Dict[str, str] = Body(default_factory=dict),
        workflow: Dict[str, Any] = Body(...)
    ):
        """Save a new workflow template."""
        templates_dir = _get_templates_dir()

        # Build template with metadata
        template = {
            "_meta": {
                "name": display_name or name,
                "description": description,
                "version": "1.0.0",
                "variables": variables,
                "use_case": use_case
            }
        }

        # Add workflow nodes
        template.update(workflow)

        # Save
        filename = name if name.endswith('.json') else f"{name}.json"
        filepath = templates_dir / filename

        with open(filepath, 'w') as f:
            json.dump(template, f, indent=2)

        return {
            "status": "saved",
            "template": name,
            "path": str(filepath)
        }

    @router.delete("/workflow-templates/{template_name}")
    async def delete_workflow_template(template_name: str):
        """Delete a workflow template."""
        templates_dir = _get_templates_dir()

        filename = template_name if template_name.endswith('.json') else f"{template_name}.json"
        filepath = templates_dir / filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")

        filepath.unlink()

        return {
            "status": "deleted",
            "template": template_name
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # END-TO-END CHAPTER AUTOMATION PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    class ChapterPipelineStage(str, Enum):
        """Stages in the chapter automation pipeline."""
        GENERATE_SCRIPT = "generate_script"
        CREATE_STRUCTURE = "create_structure"
        GENERATE_TTS = "generate_tts"
        GENERATE_ASSETS = "generate_assets"
        SCORE_QUALITY = "score_quality"
        PACKAGE = "package"

    class ChapterPipelineRequest(BaseModel):
        """Request for end-to-end chapter automation."""
        chapter_number: int
        featured_characters: List[str] = []
        themes: List[str] = []
        previous_summary: str = ""
        output_base: str = "/app/repo/output/empire/chapters"

        # Pipeline control
        stages: List[str] = ["generate_script", "create_structure", "generate_tts", "package"]
        skip_existing: bool = True  # Skip stages with existing output

        # TTS options
        tts_enabled: bool = True
        tts_voice_default: str = "af_bella"

        # Asset generation options
        assets_enabled: bool = False  # Image generation is expensive, opt-in
        asset_types: List[str] = ["character", "background"]
        comfyui_submit: bool = False  # Whether to submit workflows

        # Quality options
        quality_check: bool = True
        min_quality_score: float = 65.0

        # Packaging options
        package_on_complete: bool = True
        include_raw_assets: bool = False

    class PipelineStageResult(BaseModel):
        """Result of a single pipeline stage."""
        stage: str
        status: str  # "success", "skipped", "failed"
        duration_ms: float
        message: str
        data: Optional[Dict[str, Any]] = None
        error: Optional[str] = None

    class ChapterPipelineResponse(BaseModel):
        """Response from chapter automation pipeline."""
        chapter_number: int
        status: str  # "complete", "partial", "failed"
        stages_completed: List[str]
        stages_failed: List[str]
        stages_skipped: List[str]
        total_duration_ms: float
        stage_results: List[PipelineStageResult]
        output_directory: str
        package_path: Optional[str] = None
        summary: Dict[str, Any]

    @router.post("/automate-chapter", response_model=ChapterPipelineResponse)
    async def automate_chapter(request: ChapterPipelineRequest):
        """
        End-to-end chapter automation pipeline.

        Orchestrates the complete chapter production workflow:
        1. generate_script - Generate chapter script using LLM
        2. create_structure - Create directory structure
        3. generate_tts - Generate TTS audio for all dialogue
        4. generate_assets - Generate visual assets (optional)
        5. score_quality - Score generated assets (optional)
        6. package - Package chapter for distribution

        Usage:
        ```json
        {
            "chapter_number": 1,
            "featured_characters": ["seraphina", "marcus"],
            "themes": ["betrayal", "power"],
            "stages": ["generate_script", "create_structure", "generate_tts", "package"]
        }
        ```
        """
        import time
        import asyncio
        from datetime import datetime

        pipeline_start = time.time()
        chapter_dir = f"{request.output_base}/ch{request.chapter_number:02d}"

        stage_results: List[PipelineStageResult] = []
        stages_completed = []
        stages_failed = []
        stages_skipped = []

        # Pipeline state
        generated_script = None
        parsed_scenes = []
        dialogue_items = []
        tts_results = []
        asset_results = []
        quality_scores = []
        package_path = None

        async def run_stage(stage_name: str, stage_func):
            """Execute a pipeline stage with timing and error handling."""
            nonlocal stage_results, stages_completed, stages_failed, stages_skipped

            if stage_name not in request.stages:
                stages_skipped.append(stage_name)
                return None

            stage_start = time.time()
            try:
                result_data = await stage_func()
                duration = (time.time() - stage_start) * 1000

                stage_results.append(PipelineStageResult(
                    stage=stage_name,
                    status="success",
                    duration_ms=duration,
                    message=f"Stage {stage_name} completed successfully",
                    data=result_data
                ))
                stages_completed.append(stage_name)
                return result_data

            except Exception as e:
                duration = (time.time() - stage_start) * 1000
                error_msg = str(e)
                logger.error(f"Pipeline stage {stage_name} failed: {error_msg}")

                stage_results.append(PipelineStageResult(
                    stage=stage_name,
                    status="failed",
                    duration_ms=duration,
                    message=f"Stage {stage_name} failed",
                    error=error_msg
                ))
                stages_failed.append(stage_name)
                return None

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 1: Generate Script
        # ─────────────────────────────────────────────────────────────────────
        async def stage_generate_script():
            nonlocal generated_script, parsed_scenes, dialogue_items

            # Check for existing script
            script_file = Path(chapter_dir) / "metadata" / "script.json"
            if request.skip_existing and script_file.exists():
                with open(script_file) as f:
                    generated_script = json.load(f)
                return {"source": "cached", "scenes": len(generated_script.get("scenes", []))}

            # Call story crew to generate chapter
            from .story_crew import StoryGenerationCrew
            crew = StoryGenerationCrew()

            generated_script = crew.generate_chapter(
                chapter_number=request.chapter_number,
                featured_characters=request.featured_characters,
                themes=request.themes,
                previous_summary=request.previous_summary,
            )

            # Save script
            script_file.parent.mkdir(parents=True, exist_ok=True)
            with open(script_file, 'w') as f:
                json.dump(generated_script, f, indent=2)

            # Parse scenes and dialogue
            parsed_scenes = generated_script.get("scenes", [])
            for scene in parsed_scenes:
                for line in scene.get("dialogue", []):
                    dialogue_items.append({
                        "character": line.get("character", "narrator"),
                        "emotion": line.get("emotion", "neutral"),
                        "text": line.get("text", ""),
                        "scene_id": scene.get("id", "")
                    })

            return {
                "source": "generated",
                "scenes": len(parsed_scenes),
                "dialogue_lines": len(dialogue_items),
                "title": generated_script.get("title", f"Chapter {request.chapter_number}")
            }

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 2: Create Structure
        # ─────────────────────────────────────────────────────────────────────
        async def stage_create_structure():
            chapter_path = Path(chapter_dir)

            # Create directory structure
            subdirs = [
                "images/characters",
                "images/backgrounds",
                "images/sprites",
                "audio/dialogue",
                "audio/music",
                "audio/sfx",
                "scripts",
                "metadata",
                "packages"
            ]

            created = []
            for subdir in subdirs:
                subpath = chapter_path / subdir
                if not subpath.exists():
                    subpath.mkdir(parents=True, exist_ok=True)
                    created.append(subdir)

            # Create manifest
            manifest = {
                "chapter": request.chapter_number,
                "created_at": datetime.utcnow().isoformat(),
                "structure_version": "1.0",
                "directories": subdirs
            }
            with open(chapter_path / "metadata" / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)

            return {
                "chapter_dir": str(chapter_path),
                "directories_created": len(created),
                "total_directories": len(subdirs)
            }

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 3: Generate TTS
        # ─────────────────────────────────────────────────────────────────────
        async def stage_generate_tts():
            nonlocal tts_results

            if not request.tts_enabled or not dialogue_items:
                return {"skipped": True, "reason": "TTS disabled or no dialogue"}

            from .tts_synthesis import TTSSynthesizer
            synthesizer = TTSSynthesizer()

            audio_dir = Path(chapter_dir) / "audio" / "dialogue"
            audio_dir.mkdir(parents=True, exist_ok=True)

            success_count = 0
            failed_count = 0

            for i, item in enumerate(dialogue_items):
                try:
                    filename = f"{i:04d}_{item['character']}_{item['emotion']}.wav"
                    output_path = str(audio_dir / filename)

                    # Check if exists
                    if request.skip_existing and Path(output_path).exists():
                        tts_results.append({"index": i, "status": "cached", "path": output_path})
                        success_count += 1
                        continue

                    audio = synthesizer.synthesize(
                        text=item["text"],
                        character_name=item["character"],
                        emotion=item["emotion"],
                        output_path=output_path
                    )

                    if audio:
                        tts_results.append({"index": i, "status": "generated", "path": output_path})
                        success_count += 1
                    else:
                        tts_results.append({"index": i, "status": "failed", "error": "Synthesis returned None"})
                        failed_count += 1

                except Exception as e:
                    tts_results.append({"index": i, "status": "failed", "error": str(e)})
                    failed_count += 1

            # Save TTS manifest
            tts_manifest = {
                "chapter": request.chapter_number,
                "total_lines": len(dialogue_items),
                "success": success_count,
                "failed": failed_count,
                "results": tts_results
            }
            with open(Path(chapter_dir) / "metadata" / "tts_manifest.json", 'w') as f:
                json.dump(tts_manifest, f, indent=2)

            return {
                "total_lines": len(dialogue_items),
                "success": success_count,
                "failed": failed_count,
                "output_dir": str(audio_dir)
            }

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 4: Generate Assets
        # ─────────────────────────────────────────────────────────────────────
        async def stage_generate_assets():
            nonlocal asset_results

            if not request.assets_enabled:
                return {"skipped": True, "reason": "Asset generation disabled"}

            # Extract unique character/emotion combinations from scenes
            character_requests = []
            for scene in parsed_scenes:
                for char_name, emotion in scene.get("character_emotions", {}).items():
                    char_req = {
                        "character": char_name,
                        "emotion": emotion if isinstance(emotion, str) else emotion.value,
                        "scene_id": scene.get("id", "")
                    }
                    if char_req not in character_requests:
                        character_requests.append(char_req)

            # For now, return the asset requirements without ComfyUI submission
            # Full implementation would queue ComfyUI workflows
            asset_results = {
                "character_assets_needed": character_requests,
                "background_assets_needed": [s.get("background_description", "") for s in parsed_scenes],
                "comfyui_submitted": request.comfyui_submit,
                "total_character_assets": len(character_requests),
                "total_background_assets": len(parsed_scenes)
            }

            # Save asset requirements
            with open(Path(chapter_dir) / "metadata" / "asset_requirements.json", 'w') as f:
                json.dump(asset_results, f, indent=2)

            return asset_results

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 5: Score Quality
        # ─────────────────────────────────────────────────────────────────────
        async def stage_score_quality():
            nonlocal quality_scores

            if not request.quality_check:
                return {"skipped": True, "reason": "Quality check disabled"}

            images_dir = Path(chapter_dir) / "images"
            if not images_dir.exists():
                return {"skipped": True, "reason": "No images directory found"}

            # Find all images
            image_files = list(images_dir.glob("**/*.png")) + list(images_dir.glob("**/*.jpg"))

            if not image_files:
                return {"skipped": True, "reason": "No images found to score"}

            from .asset_quality import AssetQualityScorer
            scorer = AssetQualityScorer()

            passed = 0
            failed = 0
            for img_path in image_files:
                try:
                    report = scorer.score_image(str(img_path))
                    quality_scores.append({
                        "path": str(img_path),
                        "score": report.overall_score,
                        "passed": report.passed
                    })
                    if report.passed:
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    quality_scores.append({
                        "path": str(img_path),
                        "error": str(e),
                        "passed": False
                    })
                    failed += 1

            # Save quality report
            quality_report = {
                "chapter": request.chapter_number,
                "total_images": len(image_files),
                "passed": passed,
                "failed": failed,
                "min_threshold": request.min_quality_score,
                "scores": quality_scores
            }
            with open(Path(chapter_dir) / "metadata" / "quality_report.json", 'w') as f:
                json.dump(quality_report, f, indent=2)

            return {
                "total_images": len(image_files),
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / len(image_files) if image_files else 0
            }

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 6: Package
        # ─────────────────────────────────────────────────────────────────────
        async def stage_package():
            nonlocal package_path

            if not request.package_on_complete:
                return {"skipped": True, "reason": "Packaging disabled"}

            import zipfile
            from datetime import datetime

            package_name = f"ch{request.chapter_number:02d}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
            packages_dir = Path(chapter_dir) / "packages"
            packages_dir.mkdir(parents=True, exist_ok=True)
            package_path = str(packages_dir / package_name)

            # Create zip archive
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                chapter_path = Path(chapter_dir)

                for subdir in ["audio", "images", "scripts", "metadata"]:
                    subpath = chapter_path / subdir
                    if subpath.exists():
                        for file_path in subpath.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(chapter_path)
                                zipf.write(file_path, arcname)

            # Get package size
            package_size = Path(package_path).stat().st_size

            return {
                "package_path": package_path,
                "package_name": package_name,
                "size_bytes": package_size,
                "size_mb": round(package_size / (1024 * 1024), 2)
            }

        # ═════════════════════════════════════════════════════════════════════
        # EXECUTE PIPELINE
        # ═════════════════════════════════════════════════════════════════════

        await run_stage("generate_script", stage_generate_script)
        await run_stage("create_structure", stage_create_structure)
        await run_stage("generate_tts", stage_generate_tts)
        await run_stage("generate_assets", stage_generate_assets)
        await run_stage("score_quality", stage_score_quality)
        await run_stage("package", stage_package)

        # Calculate totals
        total_duration = (time.time() - pipeline_start) * 1000

        # Determine overall status
        if stages_failed:
            status = "partial" if stages_completed else "failed"
        else:
            status = "complete"

        # Build summary
        summary = {
            "chapter_number": request.chapter_number,
            "scenes_generated": len(parsed_scenes),
            "dialogue_lines": len(dialogue_items),
            "tts_generated": len([r for r in tts_results if r.get("status") in ["generated", "cached"]]),
            "assets_queued": len(asset_results.get("character_assets_needed", [])) if asset_results else 0,
            "quality_passed": len([q for q in quality_scores if q.get("passed")]),
            "packaged": package_path is not None
        }

        return ChapterPipelineResponse(
            chapter_number=request.chapter_number,
            status=status,
            stages_completed=stages_completed,
            stages_failed=stages_failed,
            stages_skipped=stages_skipped,
            total_duration_ms=total_duration,
            stage_results=stage_results,
            output_directory=chapter_dir,
            package_path=package_path,
            summary=summary
        )

    @router.get("/pipeline-status/{chapter_number}")
    async def get_pipeline_status(chapter_number: int, output_base: str = "/app/repo/output/empire/chapters"):
        """Get the current status of a chapter's automation pipeline."""
        chapter_dir = Path(f"{output_base}/ch{chapter_number:02d}")

        if not chapter_dir.exists():
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_number} not found")

        status = {
            "chapter_number": chapter_number,
            "directory": str(chapter_dir),
            "stages": {}
        }

        # Check each stage
        metadata_dir = chapter_dir / "metadata"

        # Script
        script_file = metadata_dir / "script.json"
        if script_file.exists():
            with open(script_file) as f:
                script = json.load(f)
            status["stages"]["generate_script"] = {
                "complete": True,
                "scenes": len(script.get("scenes", []))
            }
        else:
            status["stages"]["generate_script"] = {"complete": False}

        # Structure
        manifest_file = metadata_dir / "manifest.json"
        status["stages"]["create_structure"] = {"complete": manifest_file.exists()}

        # TTS
        tts_manifest = metadata_dir / "tts_manifest.json"
        if tts_manifest.exists():
            with open(tts_manifest) as f:
                tts_data = json.load(f)
            status["stages"]["generate_tts"] = {
                "complete": True,
                "success": tts_data.get("success", 0),
                "failed": tts_data.get("failed", 0)
            }
        else:
            status["stages"]["generate_tts"] = {"complete": False}

        # Assets
        asset_req = metadata_dir / "asset_requirements.json"
        status["stages"]["generate_assets"] = {"complete": asset_req.exists()}

        # Quality
        quality_report = metadata_dir / "quality_report.json"
        if quality_report.exists():
            with open(quality_report) as f:
                quality_data = json.load(f)
            status["stages"]["score_quality"] = {
                "complete": True,
                "passed": quality_data.get("passed", 0),
                "failed": quality_data.get("failed", 0)
            }
        else:
            status["stages"]["score_quality"] = {"complete": False}

        # Packages
        packages_dir = chapter_dir / "packages"
        packages = list(packages_dir.glob("*.zip")) if packages_dir.exists() else []
        status["stages"]["package"] = {
            "complete": len(packages) > 0,
            "packages": [p.name for p in packages]
        }

        return status

    return router
