FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY scheduler.py .

CMD ["python", "-u", "scheduler.py"]
