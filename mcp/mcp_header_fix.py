"""Hydra MCP Server v2 - Unified Control Plane API with Safety Layer"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import httpx
import os
from datetime import datetime
from typing import Optional, List, Dict
import json
import math
import time
import secrets
import asyncio
from collections import defaultdict

app = FastAPI(title="Hydra MCP Server", version="2.0.0")

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
LETTA_URL = os.getenv("LETTA_URL", "http://hydra-letta:8283")
LETTA_TOKEN = os.getenv("LETTA_TOKEN", "")
LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://hydra-prometheus:9090")
CREWAI_URL = os.getenv("CREWAI_URL", "http://hydra-crewai:8500")
LITELLM_URL = os.getenv("LITELLM_URL", "http://hydra-litellm:4000")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://hydra-qdrant:6333")

# Docker socket for container operations
DOCKER_SOCKET = "/var/run/docker.sock"

client = httpx.AsyncClient(timeout=30.0)
