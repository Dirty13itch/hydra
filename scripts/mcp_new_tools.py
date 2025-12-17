"""
New MCP Tools - Home Assistant, n8n, Scheduler Integration
Apply to mcp_server.py with patch command
"""

# ============================================================================
# Home Assistant Integration Tools
# ============================================================================

@app.get("/homeassistant/states")
async def ha_get_states():
    """Get all Home Assistant entity states"""
    import httpx
    ha_url = os.getenv("HA_URL", "http://192.168.1.244:8123")
    ha_token = os.getenv("HA_TOKEN", "")

    if not ha_token:
        return {"error": "HA_TOKEN not configured"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ha_url}/api/states",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=10
        )
        return response.json()


@app.get("/homeassistant/state/{entity_id}")
async def ha_get_state(entity_id: str):
    """Get specific Home Assistant entity state"""
    import httpx
    ha_url = os.getenv("HA_URL", "http://192.168.1.244:8123")
    ha_token = os.getenv("HA_TOKEN", "")

    if not ha_token:
        return {"error": "HA_TOKEN not configured"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ha_url}/api/states/{entity_id}",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=10
        )
        return response.json()


@app.post("/homeassistant/service/{domain}/{service}")
async def ha_call_service(domain: str, service: str, entity_id: str = None, data: dict = None):
    """Call Home Assistant service"""
    import httpx
    ha_url = os.getenv("HA_URL", "http://192.168.1.244:8123")
    ha_token = os.getenv("HA_TOKEN", "")

    if not ha_token:
        return {"error": "HA_TOKEN not configured"}

    payload = data or {}
    if entity_id:
        payload["entity_id"] = entity_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ha_url}/api/services/{domain}/{service}",
            headers={"Authorization": f"Bearer {ha_token}"},
            json=payload,
            timeout=10
        )
        return {"status": "ok", "response": response.json() if response.content else None}


# ============================================================================
# n8n Workflow Integration Tools
# ============================================================================

@app.get("/n8n/workflows")
async def n8n_list_workflows():
    """List all n8n workflows"""
    import httpx
    n8n_url = os.getenv("N8N_URL", "http://192.168.1.244:5678")
    n8n_api_key = os.getenv("N8N_API_KEY", "")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{n8n_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": n8n_api_key} if n8n_api_key else {},
            timeout=10
        )
        return response.json()


@app.post("/n8n/workflow/{workflow_id}/activate")
async def n8n_activate_workflow(workflow_id: str):
    """Activate a workflow"""
    import httpx
    n8n_url = os.getenv("N8N_URL", "http://192.168.1.244:5678")
    n8n_api_key = os.getenv("N8N_API_KEY", "")

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": n8n_api_key} if n8n_api_key else {},
            json={"active": True},
            timeout=10
        )
        return response.json()


@app.post("/n8n/webhook/{webhook_path:path}")
async def n8n_trigger_webhook(webhook_path: str, data: dict = None):
    """Trigger n8n webhook"""
    import httpx
    n8n_url = os.getenv("N8N_URL", "http://192.168.1.244:5678")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{n8n_url}/webhook/{webhook_path}",
            json=data or {},
            timeout=30
        )
        return {"status_code": response.status_code, "response": response.text}


# ============================================================================
# Scheduler Integration Tools
# ============================================================================

@app.get("/scheduler/status")
async def scheduler_status():
    """Get crew scheduler status"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://192.168.1.244:8700/scheduler/status", timeout=10)
        return response.json()


@app.get("/scheduler/jobs")
async def scheduler_list_jobs():
    """List scheduled jobs"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://192.168.1.244:8700/scheduler/jobs", timeout=10)
        return response.json()


@app.post("/scheduler/job")
async def scheduler_add_job(name: str, cron: str, crew_type: str):
    """Add a scheduled job"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://192.168.1.244:8700/scheduler/job",
            json={"name": name, "cron": cron, "crew_type": crew_type},
            timeout=10
        )
        return response.json()


@app.delete("/scheduler/job/{job_id}")
async def scheduler_remove_job(job_id: str):
    """Remove a scheduled job"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://192.168.1.244:8700/scheduler/job/{job_id}", timeout=10)
        return response.json()


# ============================================================================
# Predictive Maintenance Integration
# ============================================================================

@app.get("/predictive/health")
async def predictive_health():
    """Get predictive maintenance health overview"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://192.168.1.244:8700/predictive/health", timeout=30)
        return response.json()


@app.get("/predictive/score")
async def predictive_score():
    """Get overall predictive health score"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://192.168.1.244:8700/predictive/score", timeout=10)
        return response.json()
