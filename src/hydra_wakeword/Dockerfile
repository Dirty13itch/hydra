# Hydra Wake Word Detection Service
# Listens for "Hey Hydra" and triggers voice pipeline
# Runs on CPU - can be deployed anywhere

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.109.0 \
    uvicorn[standard]>=0.27.0 \
    httpx>=0.25.0 \
    pydantic>=2.0 \
    numpy>=1.24.0 \
    pyaudio>=0.2.14 \
    openwakeword>=0.6.0 \
    onnxruntime>=1.16.0

# Copy application code
COPY main.py .
COPY __init__.py .

# Environment configuration
ENV WAKE_WORD_MODEL=hey_jarvis
ENV DETECTION_THRESHOLD=0.5
ENV VOICE_API_URL=http://192.168.1.244:8850
ENV AUDIO_DEVICE=-1
ENV COOLDOWN_SECONDS=2.0

# Expose API port
EXPOSE 8860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8860/health')" || exit 1

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8860"]
