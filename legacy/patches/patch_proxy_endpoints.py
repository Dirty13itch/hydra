#!/usr/bin/env python3
"""Patch script to add proxy endpoints to MCP server for CORS-blocked services.

This adds proxy endpoints for services that don't support CORS:
- Alertmanager: /proxy/alertmanager/*
- Ollama: /proxy/ollama/*
- Letta: /proxy/letta/*

The UI can then call MCP (which has CORS enabled) instead of direct service calls.
"""

PROXY_CODE = '''
# =============================================================================
# Proxy Endpoints (for CORS-blocked services)
# =============================================================================

# Service URLs for proxying
ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL", "http://192.168.1.244:9093")
OLLAMA_AI_URL = os.getenv("OLLAMA_AI_URL", "http://192.168.1.203:11434")

# --- Alertmanager Proxy ---

@app.get("/proxy/alertmanager/alerts")
async def proxy_alertmanager_alerts():
    """Proxy Alertmanager alerts API"""
    try:
        r = await client.get(f"{ALERTMANAGER_URL}/api/v2/alerts", timeout=10.0)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/proxy/alertmanager/silences")
async def proxy_alertmanager_silences():
    """Proxy Alertmanager silences API"""
    try:
        r = await client.get(f"{ALERTMANAGER_URL}/api/v2/silences", timeout=10.0)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/proxy/alertmanager/silences")
async def proxy_alertmanager_create_silence(request: Request):
    """Proxy Alertmanager create silence API"""
    try:
        body = await request.json()
        r = await client.post(
            f"{ALERTMANAGER_URL}/api/v2/silences",
            json=body,
            timeout=10.0
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.delete("/proxy/alertmanager/silence/{silence_id}")
async def proxy_alertmanager_delete_silence(silence_id: str):
    """Proxy Alertmanager delete silence API"""
    try:
        r = await client.delete(
            f"{ALERTMANAGER_URL}/api/v2/silence/{silence_id}",
            timeout=10.0
        )
        if r.status_code == 200:
            return JSONResponse(content={"status": "deleted"}, status_code=200)
        return JSONResponse(content={"error": r.text}, status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# --- Ollama Proxy ---

@app.get("/proxy/ollama/tags")
async def proxy_ollama_tags():
    """Proxy Ollama models list API"""
    try:
        r = await client.get(f"{OLLAMA_AI_URL}/api/tags", timeout=30.0)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/proxy/ollama/ps")
async def proxy_ollama_ps():
    """Proxy Ollama running models API"""
    try:
        r = await client.get(f"{OLLAMA_AI_URL}/api/ps", timeout=10.0)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/proxy/ollama/generate")
async def proxy_ollama_generate(request: Request):
    """Proxy Ollama generate API (for loading/unloading models)"""
    try:
        body = await request.json()
        r = await client.post(
            f"{OLLAMA_AI_URL}/api/generate",
            json=body,
            timeout=120.0
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# --- Letta Proxy ---

@app.get("/proxy/letta/agents")
async def proxy_letta_agents():
    """Proxy Letta agents list API"""
    try:
        headers = {}
        if LETTA_TOKEN:
            headers["Authorization"] = f"Bearer {LETTA_TOKEN}"
        r = await client.get(f"{LETTA_URL}/v1/agents/", headers=headers, timeout=10.0)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/proxy/letta/agents/{agent_id}/messages")
async def proxy_letta_messages(agent_id: str):
    """Proxy Letta agent messages API"""
    try:
        headers = {}
        if LETTA_TOKEN:
            headers["Authorization"] = f"Bearer {LETTA_TOKEN}"
        r = await client.get(
            f"{LETTA_URL}/v1/agents/{agent_id}/messages",
            headers=headers,
            timeout=30.0
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/proxy/letta/agents/{agent_id}/messages")
async def proxy_letta_send_message(agent_id: str, request: Request):
    """Proxy Letta send message API"""
    try:
        body = await request.json()
        headers = {"Content-Type": "application/json"}
        if LETTA_TOKEN:
            headers["Authorization"] = f"Bearer {LETTA_TOKEN}"
        r = await client.post(
            f"{LETTA_URL}/v1/agents/{agent_id}/messages",
            headers=headers,
            json=body,
            timeout=120.0  # Letta can be slow
        )
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
'''

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "/proxy/alertmanager" in content:
    print("Proxy endpoints already exist - no patch needed")
    exit(0)

# Find insertion point - before WebSocket section or RAG section or main
insert_markers = [
    "# =============================================================================\n# RAG Pipeline",
    "# =============================================================================\n# WebSocket",
    "# =============================================================================\n# Inference",
    'if __name__ == "__main__":'
]

inserted = False
for marker in insert_markers:
    pos = content.find(marker)
    if pos > 0:
        content = content[:pos] + PROXY_CODE + "\n\n" + content[pos:]
        print(f"Inserted proxy endpoints before: {marker[:50]}...")
        inserted = True
        break

if not inserted:
    # Fallback: insert before __main__
    main_pos = content.find('if __name__')
    if main_pos > 0:
        content = content[:main_pos] + PROXY_CODE + "\n\n" + content[main_pos:]
        print("Inserted proxy endpoints before __main__")
        inserted = True

if not inserted:
    print("Could not find insertion point for proxy endpoints")
    exit(1)

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("Proxy endpoints patch applied successfully")
print(f"File size: {len(content)} bytes")
print("\nNew endpoints added:")
print("  GET  /proxy/alertmanager/alerts")
print("  GET  /proxy/alertmanager/silences")
print("  POST /proxy/alertmanager/silences")
print("  DELETE /proxy/alertmanager/silence/{id}")
print("  GET  /proxy/ollama/tags")
print("  GET  /proxy/ollama/ps")
print("  POST /proxy/ollama/generate")
print("  GET  /proxy/letta/agents")
print("  GET  /proxy/letta/agents/{id}/messages")
print("  POST /proxy/letta/agents/{id}/messages")
