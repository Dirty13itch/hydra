#!/usr/bin/env python3
"""Patch script to add model management endpoints to MCP server"""

# Read the server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if model endpoints already exist
if "/models/list" in content:
    print("Model endpoints already exist")
    exit(0)

# Add constants after PROMETHEUS_URL line
PROMETHEUS_LINE = "PROMETHEUS_URL = "
CONSTANTS = """
# Model service URLs
TABBY_API_URL = "http://192.168.1.250:5000"
OLLAMA_COMPUTE_URL = "http://192.168.1.175:11434"
"""
pos = content.find(PROMETHEUS_LINE)
if pos > 0:
    end_pos = content.find("\n", pos)
    content = content[:end_pos+1] + CONSTANTS + content[end_pos+1:]

# Model management endpoint code
MODEL_ENDPOINTS = '''
# =============================================================================
# Model Management Endpoints
# =============================================================================

@app.get("/models/list")
async def list_all_models():
    """List all available models across all inference services"""
    result = {
        "tabbyapi": {"status": "unknown", "models": []},
        "ollama": {"status": "unknown", "models": []},
        "total_models": 0
    }

    # Get TabbyAPI models
    try:
        r = await client.get(f"{TABBY_API_URL}/v1/models", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
            result["tabbyapi"] = {
                "status": "online",
                "node": "hydra-ai",
                "url": TABBY_API_URL,
                "models": [
                    {
                        "id": m.get("id", ""),
                        "owned_by": m.get("owned_by", "tabbyAPI"),
                        "type": "exl2" if "exl2" in m.get("id", "").lower() else "other"
                    }
                    for m in models
                ]
            }
    except Exception as e:
        result["tabbyapi"] = {"status": "error", "error": str(e), "models": []}

    # Get Ollama models
    try:
        r = await client.get(f"{OLLAMA_COMPUTE_URL}/api/tags", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            models = data.get("models", [])
            result["ollama"] = {
                "status": "online",
                "node": "hydra-compute",
                "url": OLLAMA_COMPUTE_URL,
                "models": [
                    {
                        "id": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                    }
                    for m in models
                ]
            }
    except Exception as e:
        result["ollama"] = {"status": "unreachable", "error": str(e), "models": []}

    result["total_models"] = len(result["tabbyapi"]["models"]) + len(result["ollama"]["models"])
    add_audit_entry("models_list", {"total": result["total_models"]}, "success", "models")
    return result


@app.get("/models/tabby")
async def get_tabby_models():
    """Get TabbyAPI model details including currently loaded model"""
    result = {
        "status": "unknown",
        "available_models": [],
        "loaded_model": None
    }

    try:
        r = await client.get(f"{TABBY_API_URL}/v1/models", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            result["available_models"] = data.get("data", [])
            result["status"] = "online"

        # Get currently loaded model
        try:
            r = await client.get(f"{TABBY_API_URL}/v1/model", timeout=5.0)
            if r.status_code == 200:
                result["loaded_model"] = r.json()
        except:
            pass

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


class ModelLoadRequest(BaseModel):
    model_name: str
    max_seq_len: Optional[int] = None


@app.post("/models/tabby/load")
async def load_tabby_model(request: ModelLoadRequest):
    """Load a model in TabbyAPI"""
    try:
        payload = {"name": request.model_name}
        if request.max_seq_len:
            payload["max_seq_len"] = request.max_seq_len

        r = await client.post(
            f"{TABBY_API_URL}/v1/model/load",
            json=payload,
            timeout=300.0
        )

        if r.status_code == 200:
            add_audit_entry("model_load", {"model": request.model_name}, "success", "models")
            return {"status": "success", "message": f"Model {request.model_name} loaded", "data": r.json()}
        else:
            return {"status": "error", "message": r.text}

    except Exception as e:
        add_audit_entry("model_load", {"model": request.model_name, "error": str(e)}, "error", "models")
        return {"status": "error", "message": str(e)}


@app.post("/models/tabby/unload")
async def unload_tabby_model():
    """Unload the current model from TabbyAPI"""
    try:
        r = await client.post(f"{TABBY_API_URL}/v1/model/unload", timeout=60.0)
        if r.status_code == 200:
            add_audit_entry("model_unload", {}, "success", "models")
            return {"status": "success", "message": "Model unloaded"}
        else:
            return {"status": "error", "message": r.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}


'''

# Find where to insert (before WebSocket endpoints section)
insert_marker = "# =============================================================================\n# WebSocket Endpoint"
insert_pos = content.find(insert_marker)
if insert_pos < 0:
    insert_marker = 'if __name__ == "__main__":'
    insert_pos = content.find(insert_marker)

if insert_pos > 0:
    content = content[:insert_pos] + MODEL_ENDPOINTS + "\n" + content[insert_pos:]

    # Write the updated file
    with open("/app/mcp_server.py", "w") as f:
        f.write(content)
    print("Model management endpoints added successfully")
    print(f"File size: {len(content)} bytes")
else:
    print("Could not find insertion point")
    exit(1)
