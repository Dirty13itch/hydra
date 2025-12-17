"""
HYDRA Wake Word Detection

Integrates with OpenWakeWord for hands-free voice activation.

Features:
- Multiple wake word models (hey_jarvis, alexa, hey_mycroft, custom)
- Voice Activity Detection (VAD) for noise filtering
- Speex noise suppression for noisy environments
- Integration with existing voice pipeline
- Wyoming protocol support for Home Assistant

Usage:
    # Start wake word detection
    detector = WakeWordDetector()
    await detector.start()

    # Or via API
    POST /voice/wake/start
    POST /voice/wake/stop
    GET /voice/wake/status
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class WakeWord(Enum):
    """Available wake word models."""
    HEY_JARVIS = "hey_jarvis"
    ALEXA = "alexa"
    HEY_MYCROFT = "hey_mycroft"
    OK_NABU = "ok_nabu"
    CUSTOM = "custom"


@dataclass
class WakeWordConfig:
    """Wake word detection configuration."""
    model: WakeWord = WakeWord.HEY_JARVIS
    threshold: float = 0.5  # Detection threshold (0-1)
    vad_threshold: float = 0.5  # Voice activity detection threshold
    enable_noise_suppression: bool = True
    audio_device: Optional[str] = None  # Use default if None
    sample_rate: int = 16000
    chunk_size: int = 1280  # 80ms at 16kHz

    # Wyoming protocol server (for Home Assistant integration)
    wyoming_host: str = "192.168.1.244"
    wyoming_port: int = 10400

    # Callback endpoints
    on_detection_webhook: Optional[str] = None
    on_detection_action: str = "voice_chat"  # What to do when wake word detected


# =============================================================================
# Wyoming Protocol Client
# =============================================================================

class WyomingClient:
    """
    Client for Wyoming protocol servers.

    The Wyoming protocol is used by Home Assistant for voice components.
    This client communicates with wyoming-openwakeword for wake word detection.
    """

    def __init__(self, host: str = "localhost", port: int = 10400):
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Wyoming server."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
            logger.info(f"Connected to Wyoming server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Wyoming server: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Wyoming server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        logger.info("Disconnected from Wyoming server")

    async def send_audio(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Send audio data and check for detection."""
        if not self._connected:
            return None

        try:
            # Wyoming protocol: send audio chunk
            self._writer.write(audio_data)
            await self._writer.drain()

            # Check for response (non-blocking)
            try:
                response = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=0.1
                )
                if response:
                    return {"detected": True, "data": response}
            except asyncio.TimeoutError:
                pass

            return {"detected": False}

        except Exception as e:
            logger.error(f"Error sending audio to Wyoming: {e}")
            return None


# =============================================================================
# Wake Word Detector
# =============================================================================

class WakeWordDetector:
    """
    Wake word detection using OpenWakeWord.

    Can operate in two modes:
    1. Local mode: Uses OpenWakeWord Python library directly
    2. Wyoming mode: Connects to wyoming-openwakeword Docker container
    """

    def __init__(
        self,
        config: Optional[WakeWordConfig] = None,
        on_detection: Optional[Callable[[str], None]] = None,
    ):
        self.config = config or WakeWordConfig()
        self.on_detection = on_detection
        self._running = False
        self._detection_count = 0
        self._last_detection: Optional[datetime] = None
        self._wyoming_client: Optional[WyomingClient] = None

        # Detection history
        self._detection_history: List[Dict[str, Any]] = []

    async def start(self) -> bool:
        """Start wake word detection."""
        if self._running:
            return True

        # Try to connect to Wyoming server first
        self._wyoming_client = WyomingClient(
            host=self.config.wyoming_host,
            port=self.config.wyoming_port
        )

        connected = await self._wyoming_client.connect()
        if not connected:
            logger.warning("Wyoming server not available, wake word detection disabled")
            return False

        self._running = True
        logger.info(f"Wake word detection started (model={self.config.model.value})")
        return True

    async def stop(self):
        """Stop wake word detection."""
        self._running = False

        if self._wyoming_client:
            await self._wyoming_client.disconnect()
            self._wyoming_client = None

        logger.info("Wake word detection stopped")

    async def check_wyoming_status(self) -> Dict[str, Any]:
        """Check if Wyoming server is available."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # Wyoming servers typically don't have HTTP, but we can check the port
                # by trying to connect
                reader, writer = await asyncio.open_connection(
                    self.config.wyoming_host,
                    self.config.wyoming_port
                )
                writer.close()
                await writer.wait_closed()
                return {
                    "available": True,
                    "host": self.config.wyoming_host,
                    "port": self.config.wyoming_port
                }
            except Exception as e:
                return {
                    "available": False,
                    "host": self.config.wyoming_host,
                    "port": self.config.wyoming_port,
                    "error": str(e)
                }

    def _record_detection(self, wake_word: str, confidence: float):
        """Record a detection event."""
        self._detection_count += 1
        self._last_detection = datetime.utcnow()

        event = {
            "wake_word": wake_word,
            "confidence": confidence,
            "timestamp": self._last_detection.isoformat(),
        }
        self._detection_history.append(event)

        # Keep only last 100 detections
        if len(self._detection_history) > 100:
            self._detection_history = self._detection_history[-100:]

        # Trigger callback
        if self.on_detection:
            self.on_detection(wake_word)

    def get_status(self) -> Dict[str, Any]:
        """Get detector status."""
        return {
            "running": self._running,
            "model": self.config.model.value,
            "threshold": self.config.threshold,
            "vad_threshold": self.config.vad_threshold,
            "noise_suppression": self.config.enable_noise_suppression,
            "wyoming_host": self.config.wyoming_host,
            "wyoming_port": self.config.wyoming_port,
            "detection_count": self._detection_count,
            "last_detection": self._last_detection.isoformat() if self._last_detection else None,
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get detection history."""
        return self._detection_history[-limit:]


# =============================================================================
# Global Instance
# =============================================================================

_detector: Optional[WakeWordDetector] = None


def get_wake_word_detector() -> WakeWordDetector:
    """Get or create the global wake word detector."""
    global _detector
    if _detector is None:
        _detector = WakeWordDetector()
    return _detector


# =============================================================================
# FastAPI Router
# =============================================================================

def create_wake_word_router() -> APIRouter:
    """Create FastAPI router for wake word detection endpoints."""
    router = APIRouter(prefix="/voice/wake", tags=["wake-word"])

    @router.get("/status")
    async def get_status():
        """Get wake word detector status."""
        detector = get_wake_word_detector()
        wyoming_status = await detector.check_wyoming_status()
        return {
            "detector": detector.get_status(),
            "wyoming": wyoming_status,
        }

    @router.post("/start")
    async def start_detection():
        """Start wake word detection."""
        detector = get_wake_word_detector()
        success = await detector.start()
        return {
            "status": "started" if success else "failed",
            "message": "Wake word detection active" if success else "Wyoming server not available"
        }

    @router.post("/stop")
    async def stop_detection():
        """Stop wake word detection."""
        detector = get_wake_word_detector()
        await detector.stop()
        return {"status": "stopped"}

    @router.get("/history")
    async def get_history(limit: int = 20):
        """Get detection history."""
        detector = get_wake_word_detector()
        return {
            "history": detector.get_history(limit),
            "count": detector._detection_count,
        }

    @router.post("/configure")
    async def configure(
        model: str = "hey_jarvis",
        threshold: float = 0.5,
        vad_threshold: float = 0.5,
    ):
        """Configure wake word detection."""
        detector = get_wake_word_detector()

        try:
            detector.config.model = WakeWord(model)
        except ValueError:
            detector.config.model = WakeWord.HEY_JARVIS

        detector.config.threshold = max(0.0, min(1.0, threshold))
        detector.config.vad_threshold = max(0.0, min(1.0, vad_threshold))

        return {
            "status": "configured",
            "config": detector.get_status(),
        }

    @router.post("/test")
    async def test_detection():
        """
        Test wake word detection by simulating a detection event.
        Useful for testing the pipeline without actual audio.
        """
        detector = get_wake_word_detector()
        detector._record_detection(
            wake_word=detector.config.model.value,
            confidence=1.0
        )
        return {
            "status": "test_detection_triggered",
            "wake_word": detector.config.model.value,
            "action": detector.config.on_detection_action,
        }

    @router.post("/trigger-voice-chat")
    async def trigger_voice_chat(text: str, voice: str = "af_nova"):
        """
        Trigger voice chat pipeline after wake word detection.

        This endpoint is called by the wake word detection system
        (e.g., Home Assistant, n8n workflow) with the user's spoken text.
        """
        import os

        N8N_URL = os.environ.get("N8N_URL", "http://192.168.1.244:5678")
        VOICE_API_URL = os.environ.get("VOICE_API_URL", "http://192.168.1.244:8700")

        detector = get_wake_word_detector()
        detector._record_detection(
            wake_word=detector.config.model.value,
            confidence=1.0
        )

        # Call the voice chat API directly
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{VOICE_API_URL}/voice/chat",
                    json={
                        "text": text,
                        "voice_response": True,
                        "voice": voice,
                        "system_prompt": "You are Hydra, a helpful AI assistant. Be concise and conversational."
                    }
                )
                result = response.json()

                latencies = result.get("latencies", {})
                return {
                    "status": "success",
                    "input_text": text,
                    "response_text": result.get("text", ""),
                    "audio_available": result.get("audio_base64") is not None,
                    "model": result.get("model_used", "unknown"),
                    "latency_ms": {
                        "llm": latencies.get("llm_ms", 0),
                        "tts": latencies.get("tts_ms", 0),
                        "total": latencies.get("total_ms", 0)
                    }
                }
            except Exception as e:
                logger.error(f"Voice chat error: {e}")
                return {
                    "status": "error",
                    "error": str(e)
                }

    @router.post("/callback")
    async def wake_word_callback(
        wake_word: str = "hey_jarvis",
        confidence: float = 1.0,
        audio_base64: Optional[str] = None,
        text: Optional[str] = None,
    ):
        """
        Callback endpoint for external wake word detection systems.

        Called by Home Assistant, Wyoming satellite, or other systems
        when a wake word is detected. Can optionally include audio or text.
        """
        import os

        N8N_WEBHOOK_URL = os.environ.get(
            "WAKE_WORD_N8N_WEBHOOK",
            "http://192.168.1.244:5678/webhook/wake-word-detected"
        )

        detector = get_wake_word_detector()
        detector._record_detection(wake_word=wake_word, confidence=confidence)

        # Forward to n8n workflow
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                payload = {
                    "wake_word": wake_word,
                    "confidence": confidence,
                    "audio_base64": audio_base64,
                    "text": text,
                    "source": "wake_word_callback"
                }

                response = await client.post(N8N_WEBHOOK_URL, json=payload)

                return {
                    "status": "forwarded",
                    "wake_word": wake_word,
                    "n8n_status": response.status_code,
                    "n8n_response": response.json() if response.status_code == 200 else None
                }
            except Exception as e:
                logger.warning(f"n8n webhook failed: {e}")
                return {
                    "status": "recorded_locally",
                    "wake_word": wake_word,
                    "error": f"n8n webhook failed: {e}"
                }

    return router


# =============================================================================
# Docker Compose Configuration for Wyoming-OpenWakeWord
# =============================================================================

DOCKER_COMPOSE_SNIPPET = """
# Add to docker-compose.yml for wake word detection
services:
  wyoming-openwakeword:
    image: rhasspy/wyoming-openwakeword:latest
    container_name: wyoming-openwakeword
    ports:
      - "10400:10400"
    volumes:
      - /mnt/user/appdata/openwakeword/custom:/custom
    command:
      - --preload-model
      - hey_jarvis
      - --custom-model-dir
      - /custom
    restart: unless-stopped
    environment:
      - TZ=America/Chicago
"""
