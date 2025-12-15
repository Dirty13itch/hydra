"""
Hydra Wake Word Detection Service

Continuously listens for "Hey Hydra" wake word and triggers voice pipeline.
Uses openWakeWord for efficient CPU-based detection.

API Endpoints:
    GET  /health          - Health check
    GET  /status          - Detection status
    POST /start           - Start listening
    POST /stop            - Stop listening
    WS   /ws/events       - WebSocket for wake events

Configuration via environment:
    WAKE_WORD_MODEL: Wake word model name (default: "hey_jarvis")
    DETECTION_THRESHOLD: Confidence threshold 0-1 (default: 0.5)
    VOICE_API_URL: Voice interface URL to notify (default: http://192.168.1.244:8850)
    AUDIO_DEVICE: Audio input device index (default: -1 for default)
"""

import os
import asyncio
import logging
from typing import Optional, Set
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("hydra-wakeword")


class Config:
    """Service configuration from environment."""
    WAKE_WORD_MODEL = os.environ.get("WAKE_WORD_MODEL", "hey_jarvis")  # Close to "hey hydra"
    DETECTION_THRESHOLD = float(os.environ.get("DETECTION_THRESHOLD", "0.5"))
    VOICE_API_URL = os.environ.get("VOICE_API_URL", "http://192.168.1.244:8850")
    AUDIO_DEVICE = int(os.environ.get("AUDIO_DEVICE", "-1"))
    COOLDOWN_SECONDS = float(os.environ.get("COOLDOWN_SECONDS", "2.0"))


class DetectionStatus(BaseModel):
    """Wake word detection status."""
    listening: bool
    model: str
    threshold: float
    last_detection: Optional[datetime] = None
    total_detections: int = 0


class WakeEvent(BaseModel):
    """Wake word detection event."""
    timestamp: datetime
    confidence: float
    model: str


# Global state
detection_status = DetectionStatus(
    listening=False,
    model=Config.WAKE_WORD_MODEL,
    threshold=Config.DETECTION_THRESHOLD
)
websocket_clients: Set[WebSocket] = set()
detection_task: Optional[asyncio.Task] = None
last_detection_time: Optional[datetime] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - start/stop detection loop."""
    logger.info("Hydra Wake Word Service starting...")
    logger.info(f"Model: {Config.WAKE_WORD_MODEL}")
    logger.info(f"Threshold: {Config.DETECTION_THRESHOLD}")
    logger.info(f"Voice API: {Config.VOICE_API_URL}")

    # Auto-start detection on startup
    await start_detection()

    yield

    # Stop detection on shutdown
    await stop_detection()
    logger.info("Hydra Wake Word Service stopped")


app = FastAPI(
    title="Hydra Wake Word Service",
    description="Wake word detection for Hydra voice interface",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def notify_voice_api(event: WakeEvent):
    """Notify voice interface of wake word detection."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.VOICE_API_URL}/wake",
                json=event.model_dump(mode='json'),
                timeout=5.0
            )
            if response.status_code == 200:
                logger.info("Voice API notified successfully")
            else:
                logger.warning(f"Voice API returned {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to notify Voice API: {e}")


async def broadcast_event(event: WakeEvent):
    """Broadcast wake event to all WebSocket clients."""
    if not websocket_clients:
        return

    message = event.model_dump(mode='json')
    disconnected = set()

    for client in websocket_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    websocket_clients.difference_update(disconnected)


async def detection_loop():
    """
    Main wake word detection loop.

    Uses openWakeWord for detection. Falls back to simulated
    detection if audio dependencies not available.
    """
    global detection_status, last_detection_time

    try:
        # Try to import audio dependencies
        import numpy as np

        try:
            from openwakeword import Model
            import pyaudio

            # Initialize PyAudio
            audio = pyaudio.PyAudio()

            # Get audio device
            device_index = Config.AUDIO_DEVICE if Config.AUDIO_DEVICE >= 0 else None

            # Initialize wake word model
            oww_model = Model(
                wakeword_models=[Config.WAKE_WORD_MODEL],
                inference_framework='onnx'
            )

            # Audio stream parameters
            CHUNK = 1280  # 80ms at 16kHz
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000

            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=device_index
            )

            logger.info("Audio stream opened, listening for wake word...")

            while detection_status.listening:
                # Read audio chunk
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Run wake word detection
                predictions = oww_model.predict(audio_array)

                # Check for wake word
                for model_name, confidence in predictions.items():
                    if confidence >= Config.DETECTION_THRESHOLD:
                        # Check cooldown
                        now = datetime.now()
                        if last_detection_time:
                            elapsed = (now - last_detection_time).total_seconds()
                            if elapsed < Config.COOLDOWN_SECONDS:
                                continue

                        # Wake word detected!
                        last_detection_time = now
                        detection_status.last_detection = now
                        detection_status.total_detections += 1

                        logger.info(f"Wake word detected! Confidence: {confidence:.3f}")

                        event = WakeEvent(
                            timestamp=now,
                            confidence=confidence,
                            model=model_name
                        )

                        # Notify voice API and broadcast to clients
                        await notify_voice_api(event)
                        await broadcast_event(event)

                await asyncio.sleep(0.01)  # Small yield

            # Cleanup
            stream.stop_stream()
            stream.close()
            audio.terminate()

        except ImportError as e:
            logger.warning(f"Audio dependencies not available: {e}")
            logger.info("Running in simulation mode (no actual detection)")

            # Simulation mode - just keep running
            while detection_status.listening:
                await asyncio.sleep(1.0)

    except Exception as e:
        logger.error(f"Detection loop error: {e}")
        detection_status.listening = False
        raise


async def start_detection():
    """Start wake word detection."""
    global detection_task, detection_status

    if detection_status.listening:
        return

    detection_status.listening = True
    detection_task = asyncio.create_task(detection_loop())
    logger.info("Wake word detection started")


async def stop_detection():
    """Stop wake word detection."""
    global detection_task, detection_status

    if not detection_status.listening:
        return

    detection_status.listening = False

    if detection_task:
        detection_task.cancel()
        try:
            await detection_task
        except asyncio.CancelledError:
            pass
        detection_task = None

    logger.info("Wake word detection stopped")


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "hydra-wakeword",
        "version": "1.0.0",
        "listening": detection_status.listening
    }


@app.get("/status", response_model=DetectionStatus)
async def get_status():
    """Get detection status."""
    return detection_status


@app.post("/start")
async def start():
    """Start wake word detection."""
    await start_detection()
    return {"status": "started"}


@app.post("/stop")
async def stop():
    """Stop wake word detection."""
    await stop_detection()
    return {"status": "stopped"}


@app.post("/test")
async def test_detection():
    """Simulate a wake word detection for testing."""
    now = datetime.now()
    event = WakeEvent(
        timestamp=now,
        confidence=0.95,
        model="test"
    )

    detection_status.last_detection = now
    detection_status.total_detections += 1

    await notify_voice_api(event)
    await broadcast_event(event)

    return {"status": "test event sent", "event": event}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for wake word events."""
    await websocket.accept()
    websocket_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(websocket_clients)}")

    try:
        # Send current status
        await websocket.send_json({
            "type": "status",
            "data": detection_status.model_dump(mode='json')
        })

        # Keep connection alive
        while True:
            try:
                # Wait for ping/pong or close
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text("ping")

    except WebSocketDisconnect:
        pass
    finally:
        websocket_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(websocket_clients)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8860)
