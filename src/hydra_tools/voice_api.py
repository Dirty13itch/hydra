"""
Voice API Router

Exposes voice interaction capabilities via the Hydra Tools API.
Proxies to the hydra_voice service or provides direct integration.

Endpoints:
- /voice/status - Voice pipeline status
- /voice/transcribe - Speech-to-text
- /voice/chat - Voice chat (STT -> LLM -> TTS)
- /voice/speak - Text-to-speech
- /voice/wake - Wake word handling
- /voice/settings - Voice configuration
"""

import base64
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field


# Configuration
VOICE_SERVICE_URL = os.getenv("VOICE_SERVICE_URL", "http://192.168.1.244:8850")
STT_URL = os.getenv("STT_URL", "http://192.168.1.203:9001")
TTS_URL = os.getenv("TTS_URL", "http://192.168.1.244:8880")
LLM_URL = os.getenv("LLM_URL", "http://192.168.1.244:4000")


class PipelineStatus(str, Enum):
    READY = "ready"
    LOADING = "loading"
    ERROR = "error"
    OFFLINE = "offline"


class VoiceStatus(BaseModel):
    """Voice pipeline status."""
    stt_status: PipelineStatus
    tts_status: PipelineStatus
    llm_status: PipelineStatus
    wake_word_enabled: bool
    current_voice: str
    target_latency_ms: int
    last_interaction: Optional[str] = None


class TranscribeResponse(BaseModel):
    """Transcription response."""
    text: str
    language: str
    confidence: float
    latency_ms: float


class SpeakRequest(BaseModel):
    """Text-to-speech request."""
    text: str = Field(..., description="Text to synthesize")
    voice: str = Field("af_bella", description="Voice ID")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed")


class SpeakResponse(BaseModel):
    """Text-to-speech response."""
    audio_base64: str
    duration_ms: float
    voice: str
    latency_ms: float


class VoiceChatRequest(BaseModel):
    """Voice chat request."""
    text: str = Field(..., description="User text input")
    voice_response: bool = Field(True, description="Generate audio response")
    voice: str = Field("af_bella", description="Voice ID for response")
    context: Optional[str] = Field(None, description="Additional context")


class VoiceChatResponse(BaseModel):
    """Voice chat response."""
    text: str
    audio_base64: Optional[str] = None
    model_used: str
    latencies: Dict[str, float]


class VoiceSettingsRequest(BaseModel):
    """Voice settings update."""
    voice: Optional[str] = None
    wake_word_enabled: Optional[bool] = None
    stt_model: Optional[str] = None


def _get_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_voice_router() -> APIRouter:
    """Create and configure the voice API router."""
    router = APIRouter(prefix="/voice", tags=["voice"])

    @router.get("/status", response_model=VoiceStatus)
    async def get_voice_status():
        """
        Get voice pipeline status.

        Returns status of all voice pipeline components.
        """
        stt_status = PipelineStatus.OFFLINE
        tts_status = PipelineStatus.OFFLINE
        llm_status = PipelineStatus.OFFLINE

        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check STT
            try:
                resp = await client.get(f"{STT_URL}/health")
                stt_status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
            except Exception:
                pass

            # Check TTS
            try:
                resp = await client.get(f"{TTS_URL}/health")
                tts_status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
            except Exception:
                pass

            # Check LLM
            try:
                resp = await client.get(f"{LLM_URL}/health")
                llm_status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
            except Exception:
                pass

        return VoiceStatus(
            stt_status=stt_status,
            tts_status=tts_status,
            llm_status=llm_status,
            wake_word_enabled=False,  # Would read from state
            current_voice="af_bella",
            target_latency_ms=500,
            last_interaction=None,
        )

    @router.post("/transcribe", response_model=TranscribeResponse)
    async def transcribe_audio(audio: UploadFile = File(...)):
        """
        Transcribe audio to text.

        Uses faster-whisper for GPU-accelerated speech recognition.
        """
        start = time.time()

        try:
            audio_data = await audio.read()

            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"audio": (audio.filename or "audio.wav", audio_data)}
                resp = await client.post(f"{STT_URL}/transcribe", files=files)

                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=f"STT service error: {resp.status_code}"
                    )

                result = resp.json()
                latency = (time.time() - start) * 1000

                return TranscribeResponse(
                    text=result.get("text", ""),
                    language=result.get("language", "en"),
                    confidence=result.get("confidence", 0.9),
                    latency_ms=latency,
                )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"STT error: {str(e)}")

    @router.post("/speak", response_model=SpeakResponse)
    async def text_to_speech(request: SpeakRequest):
        """
        Convert text to speech.

        Uses Kokoro TTS for natural voice synthesis.
        """
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "text": request.text,
                    "voice": request.voice,
                    "speed": request.speed,
                }
                resp = await client.post(
                    f"{TTS_URL}/v1/audio/speech",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=f"TTS service error: {resp.status_code}"
                    )

                # Handle different response formats
                content_type = resp.headers.get("content-type", "")

                if "audio" in content_type:
                    # Raw audio response
                    audio_bytes = resp.content
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    duration = len(audio_bytes) / 44100 * 1000  # Rough estimate
                else:
                    # JSON with base64 audio
                    result = resp.json()
                    audio_base64 = result.get("audio", result.get("audio_base64", ""))
                    duration = result.get("duration_ms", 0)

                latency = (time.time() - start) * 1000

                return SpeakResponse(
                    audio_base64=audio_base64,
                    duration_ms=duration,
                    voice=request.voice,
                    latency_ms=latency,
                )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"TTS error: {str(e)}")

    @router.post("/chat", response_model=VoiceChatResponse)
    async def voice_chat(request: VoiceChatRequest):
        """
        Full voice chat pipeline.

        Processes text through LLM and optionally generates speech response.
        Target latency: <500ms for simple queries.
        """
        latencies = {}
        total_start = time.time()

        # Step 1: LLM inference
        llm_start = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                llm_payload = {
                    "model": "hydra-70b",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Hydra, a helpful AI assistant. Keep responses concise for voice interaction."
                        },
                        {"role": "user", "content": request.text}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7,
                }

                resp = await client.post(
                    f"{LLM_URL}/v1/chat/completions",
                    json=llm_payload,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()
                result = resp.json()

                response_text = result["choices"][0]["message"]["content"]
                model_used = result.get("model", "hydra-70b")

            latencies["llm_ms"] = (time.time() - llm_start) * 1000

        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

        # Step 2: TTS if requested
        audio_base64 = None
        if request.voice_response:
            tts_start = time.time()
            try:
                speak_req = SpeakRequest(text=response_text, voice=request.voice)
                speak_resp = await text_to_speech(speak_req)
                audio_base64 = speak_resp.audio_base64
                latencies["tts_ms"] = (time.time() - tts_start) * 1000
            except Exception as e:
                latencies["tts_error"] = str(e)

        latencies["total_ms"] = (time.time() - total_start) * 1000

        return VoiceChatResponse(
            text=response_text,
            audio_base64=audio_base64,
            model_used=model_used,
            latencies=latencies,
        )

    @router.post("/wake")
    async def handle_wake_event(
        confidence: float = 0.0,
        model: str = "porcupine-hydra",
    ):
        """
        Handle wake word detection.

        Called when "Hey Hydra" is detected by the wakeword service.
        Prepares the voice pipeline for incoming audio.
        """
        timestamp = _get_timestamp()

        # Log wake event
        import logging
        logging.info(f"Wake word detected! Confidence: {confidence:.3f}, Model: {model}")

        return {
            "acknowledged": True,
            "timestamp": timestamp,
            "confidence": confidence,
            "ready_for_audio": True,
            "pipeline_status": "ready",
        }

    @router.get("/settings")
    async def get_voice_settings():
        """
        Get current voice settings.

        Returns voice, model, and feature configuration.
        """
        return {
            "voice": "af_bella",
            "stt_model": "large-v3",
            "llm_model": "hydra-70b",
            "wake_word_enabled": False,
            "target_latency_ms": 500,
            "available_voices": [
                "af_bella",
                "af_sarah",
                "am_michael",
                "bf_emma",
                "bm_george",
            ],
        }

    @router.post("/settings")
    async def update_voice_settings(request: VoiceSettingsRequest):
        """
        Update voice settings.

        Modifies voice, model, or feature configuration.
        """
        # Would persist to state/config
        updated = {}
        if request.voice:
            updated["voice"] = request.voice
        if request.wake_word_enabled is not None:
            updated["wake_word_enabled"] = request.wake_word_enabled
        if request.stt_model:
            updated["stt_model"] = request.stt_model

        return {
            "status": "updated",
            "changes": updated,
            "timestamp": _get_timestamp(),
        }

    @router.get("/voices")
    async def list_voices():
        """
        List available TTS voices.

        Returns all voices available in Kokoro TTS.
        """
        # These are the Kokoro TTS voices
        voices = [
            {"id": "af_bella", "name": "Bella (American Female)", "language": "en-US"},
            {"id": "af_sarah", "name": "Sarah (American Female)", "language": "en-US"},
            {"id": "af_nicole", "name": "Nicole (American Female)", "language": "en-US"},
            {"id": "af_sky", "name": "Sky (American Female)", "language": "en-US"},
            {"id": "am_michael", "name": "Michael (American Male)", "language": "en-US"},
            {"id": "am_adam", "name": "Adam (American Male)", "language": "en-US"},
            {"id": "bf_emma", "name": "Emma (British Female)", "language": "en-GB"},
            {"id": "bf_isabella", "name": "Isabella (British Female)", "language": "en-GB"},
            {"id": "bm_george", "name": "George (British Male)", "language": "en-GB"},
            {"id": "bm_lewis", "name": "Lewis (British Male)", "language": "en-GB"},
        ]

        return {"voices": voices, "default": "af_bella"}

    return router
