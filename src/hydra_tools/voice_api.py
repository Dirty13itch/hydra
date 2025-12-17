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
from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


# Configuration
VOICE_SERVICE_URL = os.getenv("VOICE_SERVICE_URL", "http://192.168.1.244:8850")
STT_URL = os.getenv("STT_URL", "http://192.168.1.203:9002")
TTS_URL = os.getenv("TTS_URL", "http://192.168.1.244:8880")
LLM_URL = os.getenv("LLM_URL", "http://192.168.1.244:4000")
TABBY_URL = os.getenv("TABBY_URL", "http://192.168.1.250:5000")
LLM_API_KEY = os.getenv("LITELLM_API_KEY", "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7")


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

        # LLM health check needs longer timeout (LiteLLM checks all backends)
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{LLM_URL}/health",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"}
                )
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
                # Kokoro TTS uses OpenAI-compatible API with "input" field
                payload = {
                    "input": request.text,
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
            # TabbyAPI requires user/assistant alternation - no system role
            user_message = f"You are Hydra, a helpful AI assistant. Keep responses concise for voice interaction.\n\nUser: {request.text}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                llm_payload = {
                    "model": "midnight-miqu-70b",
                    "messages": [
                        {"role": "user", "content": user_message}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7,
                }

                resp = await client.post(
                    f"{LLM_URL}/v1/chat/completions",
                    json=llm_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {LLM_API_KEY}"
                    }
                )
                resp.raise_for_status()
                result = resp.json()

                response_text = result["choices"][0]["message"]["content"]
                model_used = result.get("model", "midnight-miqu-70b")

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
            "llm_model": "midnight-miqu-70b",
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

    @router.post("/chat/stream")
    async def voice_chat_stream(request: VoiceChatRequest):
        """
        Streaming voice chat pipeline.

        Uses LLM streaming + sentence-buffered TTS for lower perceived latency.
        Returns SSE stream with audio chunks.
        """
        from fastapi.responses import StreamingResponse
        import asyncio
        import re

        async def generate_stream():
            """Generate SSE stream with text and audio."""
            # Accumulate text for sentence detection
            accumulated_text = ""
            sentences_processed = 0

            # Build user message
            user_message = f"You are Hydra, a helpful AI assistant. Keep responses concise for voice interaction.\n\nUser: {request.text}"

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    # Start streaming LLM request
                    async with client.stream(
                        "POST",
                        f"{TABBY_URL}/v1/chat/completions",
                        json={
                            "model": "Midnight-Miqu-70B-v1.5-exl2-2.5bpw",
                            "messages": [{"role": "user", "content": user_message}],
                            "max_tokens": 200,
                            "temperature": 0.7,
                            "stream": True,
                        },
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data: "):
                                continue

                            data = line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break

                            try:
                                import json
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    accumulated_text += content

                                    # Yield text chunk event
                                    yield f"data: {json.dumps({'type': 'text', 'content': content})}\\n\\n"

                                    # Check for complete sentences
                                    sentence_end = re.search(r'[.!?]\\s*$', accumulated_text)
                                    if sentence_end and request.voice_response:
                                        # Extract sentence and synthesize
                                        sentence = accumulated_text.strip()
                                        accumulated_text = ""
                                        sentences_processed += 1

                                        # Request TTS for this sentence
                                        tts_resp = await client.post(
                                            f"{TTS_URL}/v1/audio/speech",
                                            json={
                                                "input": sentence,
                                                "voice": request.voice,
                                                "response_format": "mp3",
                                                "stream": False,
                                            }
                                        )

                                        if tts_resp.status_code == 200:
                                            audio_base64 = base64.b64encode(tts_resp.content).decode()
                                            yield f"data: {json.dumps({'type': 'audio', 'content': audio_base64, 'sentence': sentences_processed})}\\n\\n"

                            except Exception:
                                continue

                    # Handle any remaining text
                    if accumulated_text.strip() and request.voice_response:
                        async with httpx.AsyncClient(timeout=30.0) as tts_client:
                            tts_resp = await tts_client.post(
                                f"{TTS_URL}/v1/audio/speech",
                                json={
                                    "input": accumulated_text.strip(),
                                    "voice": request.voice,
                                    "response_format": "mp3",
                                    "stream": False,
                                }
                            )
                            if tts_resp.status_code == 200:
                                import json
                                audio_base64 = base64.b64encode(tts_resp.content).decode()
                                yield f"data: {json.dumps({'type': 'audio', 'content': audio_base64, 'sentence': sentences_processed + 1})}\\n\\n"

                    yield f"data: {json.dumps({'type': 'done', 'sentences': sentences_processed})}\\n\\n"

            except Exception as e:
                import json
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\\n\\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    @router.websocket("/ws")
    async def voice_websocket(websocket: WebSocket):
        """
        WebSocket endpoint for real-time voice interaction.

        Protocol:
        - Client sends JSON messages:
          {"type": "audio", "data": "<base64_audio>"}  # Audio chunk for STT
          {"type": "text", "data": "user message"}      # Text message
          {"type": "config", "voice": "af_nova"}        # Configuration

        - Server sends JSON messages:
          {"type": "transcription", "text": "..."}      # STT result
          {"type": "response_text", "text": "...", "chunk": N}  # LLM text chunk
          {"type": "response_audio", "data": "...", "format": "mp3"}  # TTS audio
          {"type": "done"}                               # Turn complete
          {"type": "error", "message": "..."}           # Error
        """
        await websocket.accept()

        # Session state
        voice = "af_nova"
        system_prompt = "You are Hydra, a helpful AI assistant. Be concise and conversational."
        accumulated_audio = b""

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "config":
                    # Update configuration
                    voice = data.get("voice", voice)
                    system_prompt = data.get("system_prompt", system_prompt)
                    await websocket.send_json({"type": "config_ack", "voice": voice})

                elif msg_type == "audio":
                    # Receive audio chunk for STT
                    audio_b64 = data.get("data", "")
                    if audio_b64:
                        accumulated_audio += base64.b64decode(audio_b64)

                elif msg_type == "audio_end":
                    # Process accumulated audio through STT
                    if accumulated_audio:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            try:
                                stt_resp = await client.post(
                                    f"{STT_URL}/inference",
                                    files={"audio_file": ("audio.wav", accumulated_audio, "audio/wav")},
                                    data={"task": "transcribe", "language": "en"}
                                )
                                if stt_resp.status_code == 200:
                                    result = stt_resp.json()
                                    text = result.get("text", "").strip()
                                    await websocket.send_json({"type": "transcription", "text": text})

                                    # Process through LLM if we got text
                                    if text:
                                        await _ws_process_llm_tts(
                                            websocket, text, voice, system_prompt
                                        )
                            except Exception as e:
                                await websocket.send_json({"type": "error", "message": f"STT error: {e}"})

                        accumulated_audio = b""

                elif msg_type == "text":
                    # Direct text input
                    text = data.get("data", "").strip()
                    if text:
                        await _ws_process_llm_tts(websocket, text, voice, system_prompt)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass

    async def _ws_process_llm_tts(
        websocket: WebSocket,
        text: str,
        voice: str,
        system_prompt: str
    ):
        """Process text through LLM and TTS, streaming results to WebSocket."""
        import json as json_module

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Stream from LLM
            accumulated_response = ""
            chunk_count = 0

            try:
                async with client.stream(
                    "POST",
                    f"{TABBY_URL}/v1/chat/completions",
                    json={
                        "messages": [
                            {"role": "user", "content": f"{system_prompt}\n\nUser: {text}"}
                        ],
                        "max_tokens": 500,
                        "stream": True,
                        "temperature": 0.7
                    },
                    timeout=60.0
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json_module.loads(data_str)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    accumulated_response += content
                                    chunk_count += 1
                                    await websocket.send_json({
                                        "type": "response_text",
                                        "text": content,
                                        "chunk": chunk_count
                                    })
                            except Exception:
                                continue

                # Generate TTS for complete response
                if accumulated_response.strip():
                    try:
                        tts_resp = await client.post(
                            f"{TTS_URL}/v1/audio/speech",
                            json={
                                "input": accumulated_response.strip(),
                                "voice": voice,
                                "response_format": "mp3",
                                "stream": False
                            },
                            timeout=30.0
                        )
                        if tts_resp.status_code == 200:
                            audio_b64 = base64.b64encode(tts_resp.content).decode()
                            await websocket.send_json({
                                "type": "response_audio",
                                "data": audio_b64,
                                "format": "mp3"
                            })
                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": f"TTS error: {e}"})

                await websocket.send_json({"type": "done"})

            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"LLM error: {e}"})

    return router
