"""
TTS Synthesis Module for Empire of Broken Queens

Provides voice synthesis using Kokoro TTS with character-specific profiles.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

# Config paths
CONFIG_DIR = Path(__file__).parent.parent.parent / "config" / "kokoro"
VOICE_PROFILES_PATH = CONFIG_DIR / "empire_voice_profiles.json"

# Default Kokoro URL
DEFAULT_KOKORO_URL = "http://192.168.1.244:8880"


class VoiceProfileManager:
    """Manages voice profiles for characters."""

    def __init__(self, profiles_path: Optional[Path] = None):
        self.profiles_path = profiles_path or VOICE_PROFILES_PATH
        self._profiles = None
        self._load_profiles()

    def _load_profiles(self) -> None:
        """Load voice profiles from file."""
        if self.profiles_path.exists():
            with open(self.profiles_path) as f:
                self._profiles = json.load(f)
        else:
            logger.warning(f"Voice profiles not found at {self.profiles_path}")
            self._profiles = {"characters": {}, "default_settings": {}}

    def get_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Get voice profile for a character."""
        characters = self._profiles.get("characters", {})
        return characters.get(character_name.lower(), {})

    def get_voice_settings(
        self,
        character_name: str,
        emotion: str = "neutral"
    ) -> Dict[str, Any]:
        """Get voice settings for a character with emotion modifiers."""
        profile = self.get_character_profile(character_name)
        defaults = self._profiles.get("default_settings", {})

        # Resolve emotion aliases
        emotion_aliases = self._profiles.get("emotion_aliases", {})
        emotion = emotion_aliases.get(emotion.lower(), emotion.lower())

        # Get base settings
        voice_id = profile.get("voice_id", defaults.get("default_voice", "af_sarah"))
        base_speed = profile.get("base_speed", defaults.get("default_speed", 1.0))

        # Apply emotion modifiers
        emotion_mods = profile.get("emotion_modifiers", {})
        modifiers = emotion_mods.get(emotion, emotion_mods.get("neutral", {}))

        speed = base_speed * modifiers.get("speed", 1.0)

        return {
            "voice_id": voice_id,
            "speed": speed,
            "character_name": character_name,
            "emotion": emotion,
            "display_name": profile.get("display_name", character_name)
        }

    def list_characters(self) -> list[str]:
        """List all configured characters."""
        return list(self._profiles.get("characters", {}).keys())


class TTSSynthesizer:
    """Synthesizes speech using Kokoro TTS."""

    def __init__(
        self,
        kokoro_url: Optional[str] = None,
        profile_manager: Optional[VoiceProfileManager] = None
    ):
        self.kokoro_url = kokoro_url or DEFAULT_KOKORO_URL
        self.profile_manager = profile_manager or VoiceProfileManager()
        self.client = httpx.Client(timeout=60.0)

    def synthesize(
        self,
        text: str,
        character_name: str,
        emotion: str = "neutral",
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """Synthesize speech for a character.

        Args:
            text: The dialogue text to synthesize
            character_name: Character name for voice selection
            emotion: Emotion to apply to voice
            output_path: Optional path to save audio file

        Returns:
            Audio bytes if successful, None otherwise
        """
        # Get voice settings
        settings = self.profile_manager.get_voice_settings(character_name, emotion)

        payload = {
            "input": text,
            "voice": settings["voice_id"],
            "speed": settings["speed"]
        }

        try:
            response = self.client.post(
                f"{self.kokoro_url}/v1/audio/speech",
                json=payload
            )

            if response.status_code == 200:
                audio_data = response.content
                logger.info(
                    f"Synthesized {len(audio_data)} bytes for "
                    f"{settings['display_name']} ({emotion})"
                )

                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"Saved audio to {output_path}")

                return audio_data
            else:
                logger.error(f"TTS failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    def synthesize_dialogue(
        self,
        dialogue: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """Synthesize a dialogue entry.

        Args:
            dialogue: Dict with 'character', 'emotion', 'text' keys
            output_dir: Directory to save audio files

        Returns:
            Output path if successful, None otherwise
        """
        character = dialogue.get("character", "narrator")
        emotion = dialogue.get("emotion", "neutral")
        text = dialogue.get("text", "")

        if not text:
            return None

        output_path = None
        if output_dir:
            import time
            filename = f"{character}_{emotion}_{int(time.time() * 1000)}.wav"
            output_path = str(Path(output_dir) / filename)

        audio = self.synthesize(text, character, emotion, output_path)
        return output_path if audio else None

    def get_available_voices(self) -> list[str]:
        """Get list of available Kokoro voices."""
        try:
            response = self.client.get(f"{self.kokoro_url}/v1/audio/voices")
            if response.status_code == 200:
                data = response.json()
                return data.get("voices", [])
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
        return []


# FastAPI router
def create_tts_router():
    """Create FastAPI router for TTS endpoints."""
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import Response
    from pydantic import BaseModel

    router = APIRouter(prefix="/tts", tags=["tts"])
    synthesizer = TTSSynthesizer()

    class SynthesizeRequest(BaseModel):
        text: str
        character: str = "narrator"
        emotion: str = "neutral"

    class DialogueBatchRequest(BaseModel):
        dialogues: list[Dict[str, str]]
        output_dir: str = "/data/empire/tts"

    @router.get("/voices")
    async def list_voices():
        """List available Kokoro voices."""
        voices = synthesizer.get_available_voices()
        return {"voices": voices}

    @router.get("/characters")
    async def list_characters():
        """List configured character voice profiles."""
        characters = synthesizer.profile_manager.list_characters()
        profiles = []
        for char in characters:
            profile = synthesizer.profile_manager.get_character_profile(char)
            profiles.append({
                "name": char,
                "display_name": profile.get("display_name", char),
                "voice_id": profile.get("voice_id"),
                "description": profile.get("description", "")
            })
        return {"characters": profiles}

    @router.post("/synthesize")
    async def synthesize_speech(request: SynthesizeRequest):
        """Synthesize speech and return audio."""
        audio = synthesizer.synthesize(
            text=request.text,
            character_name=request.character,
            emotion=request.emotion
        )

        if not audio:
            raise HTTPException(status_code=500, detail="Synthesis failed")

        return Response(
            content=audio,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="{request.character}_{request.emotion}.wav"'
            }
        )

    @router.post("/batch")
    async def synthesize_batch(request: DialogueBatchRequest):
        """Synthesize a batch of dialogues."""
        results = []
        for dialogue in request.dialogues:
            output_path = synthesizer.synthesize_dialogue(
                dialogue,
                request.output_dir
            )
            results.append({
                "character": dialogue.get("character"),
                "emotion": dialogue.get("emotion"),
                "success": output_path is not None,
                "output_path": output_path
            })

        success_count = sum(1 for r in results if r["success"])
        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "results": results
        }

    return router
