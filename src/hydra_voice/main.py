"""
Hydra Voice Interface API

A FastAPI service providing voice interaction capabilities for the Hydra cluster.
Coordinates wake word detection, STT, LLM routing, and TTS synthesis.

Target: <500ms end-to-end latency for simple queries

Generated: December 14, 2025
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ===========================================
# CONFIGURATION
# ===========================================

class Config:
    """Voice pipeline configuration."""
    STT_URL = "http://192.168.1.203:9001"  # Faster-whisper on hydra-compute (GPU accelerated)
    LLM_URL = "http://192.168.1.244:4000"  # LiteLLM gateway
    TTS_URL = "http://192.168.1.244:8880"  # Kokoro TTS
    LETTA_URL = "http://192.168.1.244:8283"  # Letta agent

    # Target latencies (ms)
    TARGET_STT_LATENCY = 200
    TARGET_LLM_LATENCY = 250
    TARGET_TTS_LATENCY = 100
    TARGET_TOTAL_LATENCY = 500

    # Default voice
    DEFAULT_VOICE = "af_bella"
    DEFAULT_MODEL = "Mistral-Nemo-12B"


# ===========================================
# MODELS
# ===========================================

class PipelineStatus(str, Enum):
    READY = "ready"
    LOADING = "loading"
    ERROR = "error"
    OFFLINE = "offline"


class WakeWordConfig(BaseModel):
    enabled: bool = False
    model: str = "porcupine-hydra"
    sensitivity: float = 0.5
    last_activation: Optional[datetime] = None


class STTStatus(BaseModel):
    engine: str = "faster-whisper"
    status: PipelineStatus = PipelineStatus.OFFLINE
    model: str = "large-v3"
    latency_ms: Optional[float] = None


class LLMStatus(BaseModel):
    router: str = "RouteLLM"
    status: PipelineStatus = PipelineStatus.READY
    active_model: Optional[str] = None
    latency_ms: Optional[float] = None


class TTSStatus(BaseModel):
    engine: str = "Kokoro"
    status: PipelineStatus = PipelineStatus.READY
    voice: str = Config.DEFAULT_VOICE
    latency_ms: Optional[float] = None


class VoicePipelineStatus(BaseModel):
    wake_word: WakeWordConfig
    stt: STTStatus
    llm: LLMStatus
    tts: TTSStatus
    overall_latency_ms: Optional[float] = None
    target_latency_ms: int = Config.TARGET_TOTAL_LATENCY


class TranscriptionRequest(BaseModel):
    audio_base64: str
    language: str = "en"


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    latency_ms: float


class ChatRequest(BaseModel):
    text: str
    context: Optional[str] = None
    voice_response: bool = True
    voice: str = Config.DEFAULT_VOICE


class ChatResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    model_used: str
    latencies: dict


class VoiceCommand(BaseModel):
    command: str
    intent: Optional[str] = None
    entities: dict = {}
    confidence: float = 0.0


class WakeEvent(BaseModel):
    """Wake word detection event from wakeword service."""
    timestamp: datetime
    confidence: float
    model: str


# ===========================================
# APPLICATION
# ===========================================

app = FastAPI(
    title="Hydra Voice Interface",
    description="Voice interaction API for the Hydra cluster",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
pipeline_status = VoicePipelineStatus(
    wake_word=WakeWordConfig(),
    stt=STTStatus(),
    llm=LLMStatus(),
    tts=TTSStatus()
)


# ===========================================
# HEALTH & STATUS ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hydra-voice"}


@app.get("/status", response_model=VoicePipelineStatus)
async def get_pipeline_status():
    """Get current voice pipeline status."""
    # Update component statuses
    await update_component_statuses()
    return pipeline_status


async def update_component_statuses():
    """Update status of all pipeline components."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check STT
        try:
            resp = await client.get(f"{Config.STT_URL}/health")
            pipeline_status.stt.status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
        except Exception:
            pipeline_status.stt.status = PipelineStatus.OFFLINE

        # Check LLM
        try:
            resp = await client.get(f"{Config.LLM_URL}/health")
            pipeline_status.llm.status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
        except Exception:
            pipeline_status.llm.status = PipelineStatus.OFFLINE

        # Check TTS
        try:
            resp = await client.get(f"{Config.TTS_URL}/health")
            pipeline_status.tts.status = PipelineStatus.READY if resp.status_code == 200 else PipelineStatus.ERROR
        except Exception:
            pipeline_status.tts.status = PipelineStatus.OFFLINE


# ===========================================
# WAKE WORD ENDPOINTS
# ===========================================

@app.post("/wake-word/enable")
async def enable_wake_word():
    """Enable wake word detection."""
    pipeline_status.wake_word.enabled = True
    return {"status": "enabled", "model": pipeline_status.wake_word.model}


@app.post("/wake-word/disable")
async def disable_wake_word():
    """Disable wake word detection."""
    pipeline_status.wake_word.enabled = False
    return {"status": "disabled"}


@app.post("/wake-word/detected")
async def wake_word_detected():
    """Called when wake word is detected (webhook from edge device)."""
    pipeline_status.wake_word.last_activation = datetime.now()
    return {"acknowledged": True, "timestamp": pipeline_status.wake_word.last_activation}


@app.post("/wake")
async def handle_wake_event(event: WakeEvent):
    """
    Handle wake word detection from hydra-wakeword service.

    This endpoint is called when the wake word service detects "Hey Hydra".
    It prepares the voice pipeline for incoming audio.
    """
    pipeline_status.wake_word.last_activation = event.timestamp
    pipeline_status.wake_word.enabled = True

    # Log the wake event
    import logging
    logging.info(f"Wake word detected! Confidence: {event.confidence:.3f}, Model: {event.model}")

    # Could trigger audio recording here, send notification to UI, etc.
    return {
        "acknowledged": True,
        "timestamp": event.timestamp,
        "confidence": event.confidence,
        "ready_for_audio": True
    }


# ===========================================
# STT ENDPOINTS
# ===========================================

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio to text using faster-whisper."""
    start_time = time.time()

    if pipeline_status.stt.status != PipelineStatus.READY:
        raise HTTPException(status_code=503, detail="STT service unavailable")

    try:
        audio_data = await audio.read()

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"audio": (audio.filename or "audio.wav", audio_data)}
            resp = await client.post(f"{Config.STT_URL}/transcribe", files=files)
            resp.raise_for_status()
            result = resp.json()

        latency_ms = (time.time() - start_time) * 1000
        pipeline_status.stt.latency_ms = latency_ms

        return TranscriptionResponse(
            text=result.get("text", ""),
            language=result.get("language", "en"),
            confidence=result.get("confidence", 0.9),
            latency_ms=latency_ms
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"STT service error: {str(e)}")


# ===========================================
# CHAT/LLM ENDPOINTS
# ===========================================

@app.post("/chat", response_model=ChatResponse)
async def voice_chat(request: ChatRequest):
    """Process a voice chat request through the full pipeline."""
    latencies = {}
    total_start = time.time()

    # Step 1: Send to LLM (via Letta for context or direct to LiteLLM)
    llm_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Use Letta for stateful conversation
            letta_payload = {
                "role": "user",
                "content": request.text
            }
            resp = await client.post(
                f"{Config.LETTA_URL}/v1/agents/hydra-steward/messages",
                json=letta_payload,
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code == 200:
                result = resp.json()
                response_text = result.get("content", result.get("message", str(result)))
                model_used = "letta-agent"
            else:
                # Fallback to direct LiteLLM
                llm_payload = {
                    "model": Config.DEFAULT_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are Hydra, a helpful AI assistant. Keep responses concise for voice."},
                        {"role": "user", "content": request.text}
                    ],
                    "max_tokens": 150
                }
                resp = await client.post(
                    f"{Config.LLM_URL}/v1/chat/completions",
                    json=llm_payload,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()
                result = resp.json()
                response_text = result["choices"][0]["message"]["content"]
                model_used = result.get("model", Config.DEFAULT_MODEL)

        latencies["llm_ms"] = (time.time() - llm_start) * 1000
        pipeline_status.llm.latency_ms = latencies["llm_ms"]
        pipeline_status.llm.active_model = model_used

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {str(e)}")

    # Step 2: Generate TTS if requested
    audio_base64 = None
    if request.voice_response:
        tts_start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                tts_payload = {
                    "text": response_text,
                    "voice": request.voice
                }
                resp = await client.post(
                    f"{Config.TTS_URL}/v1/audio/speech",
                    json=tts_payload,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()

                # Assuming TTS returns base64 audio
                result = resp.json()
                audio_base64 = result.get("audio", result.get("audio_base64"))

            latencies["tts_ms"] = (time.time() - tts_start) * 1000
            pipeline_status.tts.latency_ms = latencies["tts_ms"]

        except httpx.HTTPError as e:
            # TTS failure is non-fatal, return text without audio
            latencies["tts_ms"] = None
            latencies["tts_error"] = str(e)

    latencies["total_ms"] = (time.time() - total_start) * 1000
    pipeline_status.overall_latency_ms = latencies["total_ms"]

    return ChatResponse(
        text=response_text,
        audio_base64=audio_base64,
        model_used=model_used,
        latencies=latencies
    )


# ===========================================
# INTENT/COMMAND PROCESSING
# ===========================================

INTENT_PATTERNS = {
    "lights_on": ["turn on", "lights on", "enable lights"],
    "lights_off": ["turn off", "lights off", "disable lights"],
    "temperature": ["temperature", "how hot", "how cold", "what's the temp"],
    "model_switch": ["switch model", "load model", "change model"],
    "status": ["status", "how are you", "system status"],
    "weather": ["weather", "forecast", "outside"],
}


@app.post("/intent", response_model=VoiceCommand)
async def classify_intent(text: str):
    """Classify the intent of a voice command."""
    text_lower = text.lower()

    best_intent = None
    best_confidence = 0.0

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                confidence = len(pattern) / len(text_lower)
                if confidence > best_confidence:
                    best_intent = intent
                    best_confidence = min(confidence * 1.5, 0.95)

    return VoiceCommand(
        command=text,
        intent=best_intent,
        entities={},
        confidence=best_confidence
    )


# ===========================================
# WEBSOCKET FOR STREAMING
# ===========================================

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time voice interaction."""
    await websocket.accept()

    try:
        while True:
            # Receive audio chunks
            data = await websocket.receive_bytes()

            # Process audio (simplified - real implementation would buffer)
            # For now, echo back status
            await websocket.send_json({
                "type": "status",
                "pipeline": pipeline_status.dict()
            })

    except WebSocketDisconnect:
        pass


# ===========================================
# SETTINGS
# ===========================================

@app.get("/settings/voice")
async def get_voice_settings():
    """Get current voice settings."""
    return {
        "voice": pipeline_status.tts.voice,
        "stt_model": pipeline_status.stt.model,
        "llm_model": pipeline_status.llm.active_model or Config.DEFAULT_MODEL,
        "wake_word_enabled": pipeline_status.wake_word.enabled,
        "target_latency_ms": Config.TARGET_TOTAL_LATENCY
    }


@app.post("/settings/voice")
async def update_voice_settings(
    voice: Optional[str] = None,
    wake_word_enabled: Optional[bool] = None
):
    """Update voice settings."""
    if voice:
        pipeline_status.tts.voice = voice
    if wake_word_enabled is not None:
        pipeline_status.wake_word.enabled = wake_word_enabled

    return await get_voice_settings()


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8850)
