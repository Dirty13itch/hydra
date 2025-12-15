# Hydra STT Service - faster-whisper
#
# Build: docker build -t hydra-stt:latest .
# Run: docker run --gpus all -p 9001:9001 hydra-stt:latest
#
# GPU-accelerated speech-to-text using faster-whisper

FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

LABEL maintainer="Hydra Cluster"
LABEL description="Speech-to-Text API using faster-whisper"

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    python3.11-venv \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    python-multipart==0.0.6 \
    faster-whisper==1.0.1 \
    pydantic==2.5.3

# Copy application code
COPY main.py .
COPY __init__.py .

# Create non-root user
RUN useradd -m -u 1000 hydra && chown -R hydra:hydra /app
USER hydra

# Environment variables
ENV WHISPER_MODEL=large-v3
ENV WHISPER_DEVICE=cuda
ENV WHISPER_COMPUTE=float16
ENV WHISPER_LANGUAGE=en
ENV WHISPER_BEAM_SIZE=5
ENV WHISPER_VAD=true

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"]
