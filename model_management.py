# =============================================================================
# Model Management Endpoints for Hydra MCP Server
# =============================================================================
"""
Add these endpoints to mcp_server.py after the imports section.

Provides model management across inference services:
- TabbyAPI (hydra-ai)
- Ollama (hydra-compute)
"""

# Add these constants near the top with other URLs
TABBY_API_URL = "http://192.168.1.250:5000"
OLLAMA_COMPUTE_URL = "http://192.168.1.175:11434"

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

    # Get Ollama models (try direct and via hydra-ai proxy)
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
                        "digest": m.get("digest", "")[:12] if m.get("digest") else ""
                    }
                    for m in models
                ]
            }
    except:
        # Try via localhost if MCP runs on the same network
        try:
            r = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                models = data.get("models", [])
                result["ollama"] = {
                    "status": "online",
                    "node": "local",
                    "models": [
                        {"id": m.get("name", ""), "size": m.get("size", 0)}
                        for m in models
                    ]
                }
        except:
            result["ollama"] = {"status": "unreachable", "models": []}

    # Calculate totals
    result["total_models"] = len(result["tabbyapi"]["models"]) + len(result["ollama"]["models"])

    add_audit_entry("models_list", {"total": result["total_models"]}, "success", "models")
    return result


@app.get("/models/tabby")
async def get_tabby_models():
    """Get TabbyAPI model details including currently loaded model"""
    result = {
        "status": "unknown",
        "available_models": [],
        "loaded_model": None,
        "draft_model": None
    }

    try:
        # Get available models
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

        # Get draft model status
        try:
            r = await client.get(f"{TABBY_API_URL}/v1/model/draft", timeout=5.0)
            if r.status_code == 200:
                result["draft_model"] = r.json()
        except:
            pass

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


@app.get("/models/ollama")
async def get_ollama_models():
    """Get Ollama model details"""
    result = {
        "status": "unknown",
        "models": [],
        "running": []
    }

    try:
        # Get available models
        r = await client.get(f"{OLLAMA_COMPUTE_URL}/api/tags", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            result["models"] = data.get("models", [])
            result["status"] = "online"

        # Get running models
        try:
            r = await client.get(f"{OLLAMA_COMPUTE_URL}/api/ps", timeout=5.0)
            if r.status_code == 200:
                result["running"] = r.json().get("models", [])
        except:
            pass

    except Exception as e:
        result["status"] = "unreachable"
        result["error"] = str(e)

    return result


class ModelLoadRequest(BaseModel):
    model_name: str
    max_seq_len: Optional[int] = None
    gpu_split: Optional[str] = None
    draft_model: Optional[str] = None


@app.post("/models/tabby/load")
async def load_tabby_model(request: ModelLoadRequest):
    """Load a model in TabbyAPI"""
    try:
        payload = {"name": request.model_name}
        if request.max_seq_len:
            payload["max_seq_len"] = request.max_seq_len
        if request.gpu_split:
            payload["gpu_split"] = request.gpu_split

        r = await client.post(
            f"{TABBY_API_URL}/v1/model/load",
            json=payload,
            timeout=300.0  # 5 minute timeout for model loading
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


class OllamaPullRequest(BaseModel):
    model_name: str


@app.post("/models/ollama/pull")
async def pull_ollama_model(request: OllamaPullRequest):
    """Pull a model to Ollama"""
    try:
        r = await client.post(
            f"{OLLAMA_COMPUTE_URL}/api/pull",
            json={"name": request.model_name, "stream": False},
            timeout=600.0  # 10 minute timeout for downloading
        )

        if r.status_code == 200:
            add_audit_entry("ollama_pull", {"model": request.model_name}, "success", "models")
            return {"status": "success", "message": f"Model {request.model_name} pulled"}
        else:
            return {"status": "error", "message": r.text}

    except Exception as e:
        add_audit_entry("ollama_pull", {"model": request.model_name, "error": str(e)}, "error", "models")
        return {"status": "error", "message": str(e)}


@app.delete("/models/ollama/{model_name}")
async def delete_ollama_model(model_name: str):
    """Delete a model from Ollama"""
    try:
        r = await client.delete(
            f"{OLLAMA_COMPUTE_URL}/api/delete",
            json={"name": model_name},
            timeout=60.0
        )

        if r.status_code == 200:
            add_audit_entry("ollama_delete", {"model": model_name}, "success", "models")
            return {"status": "success", "message": f"Model {model_name} deleted"}
        else:
            return {"status": "error", "message": r.text}

    except Exception as e:
        return {"status": "error", "message": str(e)}
