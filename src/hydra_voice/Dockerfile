# Hydra Voice Interface Dockerfile
#
# Build: docker build -t hydra-voice:latest .
# Run: docker run -p 8850:8850 hydra-voice:latest

FROM python:3.11-slim

LABEL maintainer="Hydra Cluster"
LABEL description="Voice Interface API for the Hydra cluster"

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    httpx==0.26.0 \
    python-multipart==0.0.6 \
    websockets==12.0

# Copy application code
COPY main.py .
COPY __init__.py .

# Create non-root user
RUN useradd -m -u 1000 hydra && chown -R hydra:hydra /app
USER hydra

# Expose port
EXPOSE 8850

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8850/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8850"]
