"""
Hydra Speech-to-Text (STT) API

A FastAPI service wrapping faster-whisper for speech recognition.
Runs on hydra-compute for GPU acceleration.

Target: <200ms first-word latency for real-time transcription

Generated: December 14, 2025
"""

import asyncio
import base64
import io
import os
import tempfile
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ===========================================
# CONFIGURATION
# ===========================================

class Config:
    """STT configuration."""
    MODEL_SIZE = os.environ.get("WHISPER_MODEL", "large-v3")
    DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")  # cuda or cpu
    COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE", "float16")  # float16, int8, etc.
    LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "en")

    # Performance tuning
    BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "5"))
    VAD_FILTER = os.environ.get("WHISPER_VAD", "true").lower() == "true"


# ===========================================
# MODELS
# ===========================================

class TranscriptionRequest(BaseModel):
    audio_base64: str
    language: str = "en"
    task: str = "transcribe"  # transcribe or translate


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_seconds: float
    latency_ms: float
    segments: Optional[list] = None


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    timestamp: str


# ===========================================
# APPLICATION
# ===========================================

app = FastAPI(
    title="Hydra STT API",
    description="Speech-to-Text service using faster-whisper",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
_model = None
_model_loading = False


async def get_model():
    """Get or initialize the whisper model."""
    global _model, _model_loading

    if _model is not None:
        return _model

    if _model_loading:
        # Wait for model to finish loading
        while _model_loading:
            await asyncio.sleep(0.1)
        return _model

    _model_loading = True
    try:
        from faster_whisper import WhisperModel

        print(f"Loading faster-whisper model: {Config.MODEL_SIZE}")
        print(f"Device: {Config.DEVICE}, Compute type: {Config.COMPUTE_TYPE}")

        _model = WhisperModel(
            Config.MODEL_SIZE,
            device=Config.DEVICE,
            compute_type=Config.COMPUTE_TYPE,
        )
        print("Model loaded successfully")
        return _model
    except ImportError:
        print("faster-whisper not installed, using mock mode")
        return None
    finally:
        _model_loading = False


# ===========================================
# ENDPOINTS
# ===========================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model=Config.MODEL_SIZE,
        device=Config.DEVICE,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe an audio file to text.

    Accepts: wav, mp3, flac, ogg, m4a
    """
    start_time = time.time()

    model = await get_model()
    if model is None:
        # Mock mode for testing without GPU
        return TranscriptionResponse(
            text="[Mock transcription - faster-whisper not available]",
            language="en",
            confidence=0.0,
            duration_seconds=0.0,
            latency_ms=(time.time() - start_time) * 1000
        )

    try:
        # Read audio data
        audio_data = await audio.read()

        # Save to temp file (faster-whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Transcribe
            segments, info = model.transcribe(
                tmp_path,
                language=Config.LANGUAGE if Config.LANGUAGE != "auto" else None,
                beam_size=Config.BEAM_SIZE,
                vad_filter=Config.VAD_FILTER,
            )

            # Collect segments
            segment_list = []
            full_text = []
            for segment in segments:
                full_text.append(segment.text)
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                })

            text = " ".join(full_text).strip()
            latency_ms = (time.time() - start_time) * 1000

            return TranscriptionResponse(
                text=text,
                language=info.language,
                confidence=info.language_probability,
                duration_seconds=info.duration,
                latency_ms=latency_ms,
                segments=segment_list if len(segment_list) > 1 else None
            )

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/transcribe/base64", response_model=TranscriptionResponse)
async def transcribe_base64(request: TranscriptionRequest):
    """
    Transcribe base64-encoded audio.

    Useful for WebSocket and API integrations.
    """
    start_time = time.time()

    model = await get_model()
    if model is None:
        return TranscriptionResponse(
            text="[Mock transcription - faster-whisper not available]",
            language=request.language,
            confidence=0.0,
            duration_seconds=0.0,
            latency_ms=(time.time() - start_time) * 1000
        )

    try:
        # Decode base64
        audio_data = base64.b64decode(request.audio_base64)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Transcribe
            language = request.language if request.language != "auto" else None
            segments, info = model.transcribe(
                tmp_path,
                language=language,
                task=request.task,
                beam_size=Config.BEAM_SIZE,
                vad_filter=Config.VAD_FILTER,
            )

            # Collect text
            text = " ".join([s.text for s in segments]).strip()
            latency_ms = (time.time() - start_time) * 1000

            return TranscriptionResponse(
                text=text,
                language=info.language,
                confidence=info.language_probability,
                duration_seconds=info.duration,
                latency_ms=latency_ms
            )

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.websocket("/ws/stream")
async def stream_transcription(websocket: WebSocket):
    """
    WebSocket endpoint for streaming transcription.

    Send audio chunks, receive transcriptions in real-time.
    """
    await websocket.accept()

    model = await get_model()
    audio_buffer = io.BytesIO()

    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_bytes()
            audio_buffer.write(data)

            # Check if we have enough data (e.g., 1 second of audio)
            if audio_buffer.tell() >= 32000:  # ~1 second at 16kHz mono
                audio_buffer.seek(0)

                if model:
                    # Save to temp and transcribe
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_buffer.read())
                        tmp_path = tmp.name

                    try:
                        segments, info = model.transcribe(
                            tmp_path,
                            beam_size=1,  # Faster for streaming
                            vad_filter=True,
                        )
                        text = " ".join([s.text for s in segments]).strip()

                        await websocket.send_json({
                            "type": "transcript",
                            "text": text,
                            "final": False
                        })
                    finally:
                        os.unlink(tmp_path)
                else:
                    await websocket.send_json({
                        "type": "transcript",
                        "text": "[Streaming mock]",
                        "final": False
                    })

                # Reset buffer
                audio_buffer = io.BytesIO()

    except WebSocketDisconnect:
        pass


@app.get("/models")
async def list_models():
    """List available whisper models."""
    return {
        "available": [
            "tiny", "tiny.en",
            "base", "base.en",
            "small", "small.en",
            "medium", "medium.en",
            "large-v1", "large-v2", "large-v3"
        ],
        "current": Config.MODEL_SIZE,
        "device": Config.DEVICE,
        "compute_type": Config.COMPUTE_TYPE
    }


# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
