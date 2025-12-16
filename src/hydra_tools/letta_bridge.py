"""
Letta-to-OpenAI Bridge - Makes Letta accessible via OpenAI-compatible API.

Exposes /v1/chat/completions that translates to Letta's agent API.
This allows Open WebUI and other OpenAI-compatible clients to use Letta.

Run standalone:
    uvicorn hydra_tools.letta_bridge:app --host 0.0.0.0 --port 8284

Or integrate into existing API.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

LETTA_URL = os.environ.get("LETTA_URL", "http://192.168.1.244:8283")
DEFAULT_AGENT_ID = os.environ.get("LETTA_DEFAULT_AGENT", None)

app = FastAPI(
    title="Letta-OpenAI Bridge",
    description="Translates OpenAI chat completions to Letta agent API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "letta"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage


# Cache for agent discovery
_agent_cache: Dict[str, str] = {}


async def get_agent_id(model_hint: str = None) -> str:
    """Get Letta agent ID, using cache or discovering from API."""
    global _agent_cache

    # If model hint looks like an agent ID, use it directly
    if model_hint and model_hint.startswith("agent-"):
        return model_hint

    # Check cache
    cache_key = model_hint or "default"
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]

    # Check environment for default
    if DEFAULT_AGENT_ID:
        _agent_cache[cache_key] = DEFAULT_AGENT_ID
        return DEFAULT_AGENT_ID

    # Discover agents from Letta
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{LETTA_URL}/v1/agents/")
            agents = response.json()

            if not agents:
                raise HTTPException(status_code=500, detail="No Letta agents available")

            # Look for agent matching model hint, or use first one
            for agent in agents:
                agent_name = agent.get("name", "").lower()
                if model_hint and model_hint.lower() in agent_name:
                    _agent_cache[cache_key] = agent["id"]
                    return agent["id"]

            # Default to first agent (usually hydra-steward)
            _agent_cache[cache_key] = agents[0]["id"]
            logger.info(f"Using default agent: {agents[0].get('name')} ({agents[0]['id']})")
            return agents[0]["id"]

        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Cannot reach Letta: {e}")


async def send_to_letta(agent_id: str, message: str) -> str:
    """Send a message to Letta agent and get response."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{LETTA_URL}/v1/agents/{agent_id}/messages",
                json={"messages": [{"role": "user", "content": message}]}
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Letta error: {response.status_code} - {error_text}")

                # Handle specific Letta errors gracefully
                if "No tool calls found" in error_text or response.status_code == 502:
                    return "I apologize, but I'm having trouble processing your request. The underlying model isn't generating the expected responses. Please try again or contact the administrator."

                raise HTTPException(status_code=response.status_code, detail="Letta API error")

            data = response.json()

            # Extract assistant message from Letta response
            # Letta returns array of messages with different types
            for msg in data.get("messages", []):
                if msg.get("message_type") == "assistant_message":
                    return msg.get("content", "")

            # Fallback: concatenate all assistant-like messages
            assistant_content = []
            for msg in data.get("messages", []):
                msg_type = msg.get("message_type", "")
                if msg_type in ["assistant_message", "function_return"]:
                    content = msg.get("content", "")
                    if content:
                        assistant_content.append(content)

            return "\n".join(assistant_content) or "I processed your message but have no response."

        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Cannot reach Letta: {e}")


@app.get("/v1/models")
async def list_models():
    """List available models (Letta agents)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{LETTA_URL}/v1/agents/")
            agents = response.json()

            models = []
            for agent in agents:
                models.append({
                    "id": f"letta-{agent.get('name', agent['id'])}",
                    "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "owned_by": "letta",
                })

            # Add a default model entry
            models.insert(0, {
                "id": "letta",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "letta",
            })

            return {"object": "list", "data": models}

        except httpx.RequestError:
            return {"object": "list", "data": [{"id": "letta", "object": "model", "owned_by": "letta"}]}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""

    # Get the agent ID
    agent_id = await get_agent_id(request.model)

    # Extract the user message (last user message in the conversation)
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Send to Letta
    response_content = await send_to_letta(agent_id, user_message)

    # Build OpenAI-compatible response
    return ChatCompletionResponse(
        id=f"chatcmpl-letta-{int(datetime.now().timestamp())}",
        created=int(datetime.now().timestamp()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_content),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=len(user_message.split()),
            completion_tokens=len(response_content.split()),
            total_tokens=len(user_message.split()) + len(response_content.split()),
        ),
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    # Check Letta connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Letta requires trailing slash on health endpoint
            response = await client.get(f"{LETTA_URL}/v1/health/")
            letta_ok = response.status_code == 200
    except:
        letta_ok = False

    return {
        "status": "healthy" if letta_ok else "degraded",
        "letta_connected": letta_ok,
        "letta_url": LETTA_URL,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def create_letta_bridge_router():
    """Create FastAPI router for embedding in larger app."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/letta-bridge", tags=["letta-bridge"])

    router.add_api_route("/v1/models", list_models, methods=["GET"])
    router.add_api_route("/v1/chat/completions", chat_completions, methods=["POST"])
    router.add_api_route("/health", health, methods=["GET"])

    return router


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8284)
