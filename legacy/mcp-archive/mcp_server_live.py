"""Hydra MCP Server v2 - Unified Control Plane API with Safety Layer"""
from fastapi import FastAPI, HTTPException, Request
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

# =============================================================================
# Safety Layer - Confirmation tokens and rate limiting
# =============================================================================

# Pending confirmations: {token: {action, container, expires, details}}
pending_confirmations: Dict[str, dict] = {}

# Rate limiting: {ip: {endpoint: [timestamps]}}
rate_limit_data: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
RATE_LIMITS = {
    "default": (100, 60),      # 100 requests per 60 seconds
    "dangerous": (5, 60),       # 5 dangerous ops per 60 seconds
    "inference": (20, 60),      # 20 inference requests per 60 seconds
}

# Audit log (in-memory, last 1000 entries)
audit_log: List[dict] = []
MAX_AUDIT_LOG = 1000

# Protected containers that require confirmation to restart/stop
PROTECTED_CONTAINERS = {
    "hydra-prometheus", "hydra-grafana", "hydra-letta", "hydra-litellm",
    "hydra-qdrant", "hydra-postgres", "hydra-redis", "hydra-neo4j",
    "hydra-alertmanager", "hydra-loki"
}

def safe_float(value, default=0.0):
    """Convert value to float, handling NaN/infinity"""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except:
        return default

def add_audit_entry(action: str, details: dict, result: str, ip: str = "internal"):
    """Add entry to audit log"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "result": result,
        "ip": ip
    }
    audit_log.append(entry)
    if len(audit_log) > MAX_AUDIT_LOG:
        audit_log.pop(0)

def check_rate_limit(ip: str, endpoint_type: str = "default") -> bool:
    """Check if request is within rate limits"""
    limit, window = RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])
    now = time.time()

    # Clean old entries
    rate_limit_data[ip][endpoint_type] = [
        ts for ts in rate_limit_data[ip][endpoint_type] if now - ts < window
    ]

    if len(rate_limit_data[ip][endpoint_type]) >= limit:
        return False

    rate_limit_data[ip][endpoint_type].append(now)
    return True

def generate_confirmation_token(action: str, container: str, details: str = "") -> str:
    """Generate a confirmation token for dangerous operations"""
    token = secrets.token_urlsafe(16)
    pending_confirmations[token] = {
        "action": action,
        "container": container,
        "details": details,
        "expires": time.time() + 300,  # 5 minute expiry
        "created": datetime.now().isoformat()
    }
    return token

def cleanup_expired_tokens():
    """Remove expired confirmation tokens"""
    now = time.time()
    expired = [t for t, v in pending_confirmations.items() if v["expires"] < now]
    for t in expired:
        del pending_confirmations[t]

# =============================================================================
# Startup
# =============================================================================

start_time = time.time()

@app.on_event("startup")
async def startup():
    add_audit_entry("server_start", {"version": "2.0.0"}, "success")

# =============================================================================
# Health and Status Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - start_time, 2)
    }

@app.get("/cluster/status")
async def cluster_status():
    """Get comprehensive cluster status"""
    status = {"timestamp": datetime.now().isoformat()}

    # Check Prometheus targets
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query?query=up")
        if r.status_code == 200:
            data = r.json()
            targets = data.get("data", {}).get("result", [])
            up = sum(1 for t in targets if t.get("value", [0, "0"])[1] == "1")
            status["prometheus"] = {"up": up, "total": len(targets)}
    except:
        status["prometheus"] = {"error": "unreachable"}

    # Check Letta
    try:
        headers = {"Authorization": f"Bearer {LETTA_TOKEN}"}
        r = await client.get(f"{LETTA_URL}/v1/health/", headers=headers)
        status["letta"] = r.json() if r.status_code == 200 else {"error": f"status {r.status_code}"}
    except:
        status["letta"] = {"error": "unreachable"}

    # Check CrewAI
    try:
        r = await client.get(f"{CREWAI_URL}/health")
        status["crewai"] = r.json() if r.status_code == 200 else {"error": f"status {r.status_code}"}
    except:
        status["crewai"] = {"error": "unreachable"}

    # Check Qdrant
    try:
        r = await client.get(f"{QDRANT_URL}/collections")
        if r.status_code == 200:
            data = r.json()
            status["qdrant"] = {"collections": len(data.get("result", {}).get("collections", []))}
    except:
        status["qdrant"] = {"error": "unreachable"}

    return status

@app.get("/services/status")
async def services_status():
    """Check status of key Hydra services"""
    services = {}
    checks = [
        ("letta", f"{LETTA_URL}/v1/health/", None),
        ("crewai", f"{CREWAI_URL}/health", None),
        ("qdrant", f"{QDRANT_URL}/collections", None),
        ("litellm", f"{LITELLM_URL}/health", {"Authorization": f"Bearer {LITELLM_KEY}"}),
        ("prometheus", f"{PROMETHEUS_URL}/-/ready", None),
    ]

    for name, url, headers in checks:
        try:
            r = await client.get(url, timeout=5.0, headers=headers)
            services[name] = "up" if r.status_code in [200, 204] else f"status:{r.status_code}"
        except:
            services[name] = "down"

    return services

# =============================================================================
# Metrics Endpoints
# =============================================================================

@app.get("/metrics/summary")
async def metrics_summary():
    """Get key metrics summary from Prometheus"""
    queries = {
        "cpu_avg": '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100',
        "memory_used_pct": "avg((1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes) * 100)",
        "disk_used_pct": 'avg((1 - node_filesystem_avail_bytes{fstype=~"ext4|xfs|btrfs"}/node_filesystem_size_bytes{fstype=~"ext4|xfs|btrfs"}) * 100)',
    }
    results = {}
    for name, query in queries.items():
        try:
            r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
            if r.status_code == 200:
                data = r.json()
                result = data.get("data", {}).get("result", [])
                if result:
                    raw_value = result[0].get("value", [0, "0"])[1]
                    results[name] = safe_float(raw_value)
                else:
                    results[name] = None
        except:
            results[name] = None
    return results

@app.get("/metrics/nodes")
async def metrics_nodes():
    """Get per-node metrics"""
    nodes = {}
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "node_uname_info"})
        if r.status_code == 200:
            for item in r.json().get("data", {}).get("result", []):
                instance = item.get("metric", {}).get("instance", "")
                nodename = item.get("metric", {}).get("nodename", instance)
                nodes[instance] = {"name": nodename}

        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                            params={"query": "100-avg(rate(node_cpu_seconds_total{mode='idle'}[5m]))by(instance)*100"})
        if r.status_code == 200:
            for item in r.json().get("data", {}).get("result", []):
                instance = item.get("metric", {}).get("instance", "")
                if instance in nodes:
                    nodes[instance]["cpu_pct"] = safe_float(item.get("value", [0, 0])[1])

        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                            params={"query": "(1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100"})
        if r.status_code == 200:
            for item in r.json().get("data", {}).get("result", []):
                instance = item.get("metric", {}).get("instance", "")
                if instance in nodes:
                    nodes[instance]["memory_pct"] = safe_float(item.get("value", [0, 0])[1])
    except:
        pass
    return nodes

@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-format metrics endpoint"""
    lines = []

    lines.append("# HELP hydra_mcp_info MCP Server information")
    lines.append("# TYPE hydra_mcp_info gauge")
    lines.append('hydra_mcp_info{version="2.0.0"} 1')

    uptime = time.time() - start_time
    lines.append("# HELP hydra_mcp_uptime_seconds MCP Server uptime in seconds")
    lines.append("# TYPE hydra_mcp_uptime_seconds counter")
    lines.append(f"hydra_mcp_uptime_seconds {uptime:.2f}")

    lines.append("# HELP hydra_service_up Service health status")
    lines.append("# TYPE hydra_service_up gauge")

    checks = [
        ("letta", f"{LETTA_URL}/v1/health/"),
        ("crewai", f"{CREWAI_URL}/health"),
        ("qdrant", f"{QDRANT_URL}/collections"),
        ("prometheus", f"{PROMETHEUS_URL}/-/ready"),
    ]

    for name, url in checks:
        try:
            r = await client.get(url, timeout=5.0)
            status = 1 if r.status_code in [200, 204] else 0
        except:
            status = 0
        lines.append(f'hydra_service_up{{service="{name}"}} {status}')

    try:
        r = await client.get(f"{QDRANT_URL}/collections")
        if r.status_code == 200:
            count = len(r.json().get("result", {}).get("collections", []))
            lines.append("# HELP hydra_qdrant_collections_total Number of Qdrant collections")
            lines.append("# TYPE hydra_qdrant_collections_total gauge")
            lines.append(f"hydra_qdrant_collections_total {count}")
    except:
        pass

    try:
        r = await client.get(f"{QDRANT_URL}/collections/hydra_knowledge")
        if r.status_code == 200:
            points = r.json().get("result", {}).get("points_count", 0)
            lines.append("# HELP hydra_knowledge_vectors_total Number of vectors in knowledge base")
            lines.append("# TYPE hydra_knowledge_vectors_total gauge")
            lines.append(f"hydra_knowledge_vectors_total {points}")
    except:
        pass

    # Audit log count
    lines.append("# HELP hydra_audit_log_entries_total Number of audit log entries")
    lines.append("# TYPE hydra_audit_log_entries_total gauge")
    lines.append(f"hydra_audit_log_entries_total {len(audit_log)}")

    # Pending confirmations
    cleanup_expired_tokens()
    lines.append("# HELP hydra_pending_confirmations Number of pending dangerous operation confirmations")
    lines.append("# TYPE hydra_pending_confirmations gauge")
    lines.append(f"hydra_pending_confirmations {len(pending_confirmations)}")

    return "\n".join(lines) + "\n"

# =============================================================================
# Container Management with Safety Layer
# =============================================================================

@app.get("/containers/list")
async def list_containers(request: Request):
    """List all running containers via Docker API"""
    add_audit_entry("containers_list", {}, "success", request.client.host if request.client else "unknown")

    try:
        # Use docker socket via httpx with async transport
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(transport=transport) as docker:
            r = await docker.get("http://localhost/containers/json")
            if r.status_code == 200:
                containers = []
                for c in r.json():
                    containers.append({
                        "id": c.get("Id", "")[:12],
                        "name": c.get("Names", ["/unknown"])[0].lstrip("/"),
                        "image": c.get("Image", ""),
                        "status": c.get("Status", ""),
                        "state": c.get("State", ""),
                        "protected": c.get("Names", ["/unknown"])[0].lstrip("/") in PROTECTED_CONTAINERS
                    })
                return {"containers": containers, "count": len(containers)}
    except Exception as e:
        # Fallback to Prometheus metrics if Docker socket unavailable
        try:
            r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                                params={"query": 'container_last_seen{name!=""}'})
            if r.status_code == 200:
                containers = []
                for item in r.json().get("data", {}).get("result", []):
                    name = item.get("metric", {}).get("name", "")
                    if name and not name.startswith("/"):
                        containers.append({
                            "name": name,
                            "protected": name in PROTECTED_CONTAINERS
                        })
                return {"containers": containers, "count": len(containers), "source": "prometheus"}
        except:
            pass
        return {"error": str(e), "note": "Docker socket unavailable, using Prometheus fallback"}

class ContainerAction(BaseModel):
    container: str
    confirmation_token: Optional[str] = None

@app.post("/containers/restart")
async def restart_container(action: ContainerAction, request: Request):
    """Restart a container (requires confirmation for protected containers)"""
    container = action.container
    ip = request.client.host if request.client else "unknown"

    # Rate limit dangerous operations
    if not check_rate_limit(ip, "dangerous"):
        add_audit_entry("container_restart", {"container": container}, "rate_limited", ip)
        raise HTTPException(status_code=429, detail="Rate limit exceeded for dangerous operations")

    # Check if protected and needs confirmation
    if container in PROTECTED_CONTAINERS:
        if not action.confirmation_token:
            # Generate confirmation token
            token = generate_confirmation_token("restart", container)
            add_audit_entry("container_restart_requested", {"container": container, "token": token}, "pending", ip)
            return {
                "status": "confirmation_required",
                "message": f"Container '{container}' is protected. Confirm restart by calling this endpoint again with the confirmation token.",
                "confirmation_token": token,
                "expires_in_seconds": 300,
                "warning": "This action will restart a critical service!"
            }

        # Verify confirmation token
        cleanup_expired_tokens()
        if action.confirmation_token not in pending_confirmations:
            add_audit_entry("container_restart", {"container": container}, "invalid_token", ip)
            raise HTTPException(status_code=400, detail="Invalid or expired confirmation token")

        conf = pending_confirmations[action.confirmation_token]
        if conf["action"] != "restart" or conf["container"] != container:
            raise HTTPException(status_code=400, detail="Token does not match this action")

        del pending_confirmations[action.confirmation_token]

    # Execute restart
    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(transport=transport) as docker:
            r = await docker.post(f"http://localhost/containers/{container}/restart", timeout=30.0)
            if r.status_code in [200, 204]:
                add_audit_entry("container_restart", {"container": container}, "success", ip)
                return {"status": "success", "message": f"Container '{container}' restarted"}
            else:
                add_audit_entry("container_restart", {"container": container}, f"failed:{r.status_code}", ip)
                return {"status": "error", "message": f"Failed to restart: {r.text}"}
    except Exception as e:
        add_audit_entry("container_restart", {"container": container}, f"error:{str(e)}", ip)
        return {"status": "error", "message": str(e)}

@app.get("/containers/{container}/logs")
async def container_logs(container: str, tail: int = 100, request: Request = None):
    """Get container logs"""
    ip = request.client.host if request and request.client else "unknown"
    add_audit_entry("container_logs", {"container": container, "tail": tail}, "success", ip)

    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
        async with httpx.AsyncClient(transport=transport) as docker:
            r = await docker.get(f"http://localhost/containers/{container}/logs",
                                params={"tail": tail, "stdout": True, "stderr": True})
            if r.status_code == 200:
                return {"container": container, "logs": r.text[-5000:]}  # Last 5000 chars
            return {"error": f"Failed to get logs: {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# Letta Integration
# =============================================================================

@app.post("/letta/message")
async def send_letta_message(message: str, request: Request):
    """Send message to Letta agent"""
    ip = request.client.host if request and request.client else "unknown"
    add_audit_entry("letta_message", {"message_length": len(message)}, "sent", ip)

    headers = {
        "Authorization": f"Bearer {LETTA_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        r = await client.post(
            f"{LETTA_URL}/v1/agents/{LETTA_AGENT_ID}/messages/",
            headers=headers,
            json={"messages": [{"role": "user", "content": message}]},
            timeout=120.0
        )
        return r.json() if r.status_code == 200 else {"error": f"status {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/letta/memory")
async def get_letta_memory():
    """Get Letta agent memory blocks"""
    headers = {"Authorization": f"Bearer {LETTA_TOKEN}"}
    try:
        r = await client.get(f"{LETTA_URL}/v1/agents/{LETTA_AGENT_ID}/", headers=headers)
        if r.status_code == 200:
            return r.json().get("memory", {})
        return {"error": f"status {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# CrewAI Integration
# =============================================================================

@app.post("/crews/run/{crew_name}")
async def run_crew(crew_name: str, topic: Optional[str] = None, request: Request = None):
    """Trigger a CrewAI crew execution"""
    if crew_name not in ["monitoring", "research", "maintenance"]:
        raise HTTPException(status_code=400, detail="Unknown crew")

    ip = request.client.host if request and request.client else "unknown"
    add_audit_entry("crew_run", {"crew": crew_name, "topic": topic}, "started", ip)

    try:
        payload = {"topic": topic} if topic else {}
        r = await client.post(f"{CREWAI_URL}/run/{crew_name}", json=payload, timeout=600.0)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# Knowledge Base
# =============================================================================

@app.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 5):
    """Search Qdrant knowledge base"""
    try:
        embed_r = await client.post(
            "http://192.168.1.203:11434/api/embeddings",
            json={"model": "nomic-embed-text:latest", "prompt": query},
            timeout=30.0
        )
        if embed_r.status_code != 200:
            return {"error": "embedding failed"}
        embedding = embed_r.json().get("embedding", [])

        search_r = await client.post(
            f"{QDRANT_URL}/collections/hydra_knowledge/points/search",
            json={"vector": embedding, "limit": limit, "with_payload": True}
        )
        if search_r.status_code == 200:
            results = search_r.json().get("result", [])
            return {"results": [{"text": r.get("payload", {}).get("text", ""), "score": safe_float(r.get("score", 0))} for r in results]}
        return {"error": "search failed"}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# Inference
# =============================================================================

@app.get("/inference/models")
async def list_models():
    """List available models via LiteLLM"""
    try:
        headers = {"Authorization": f"Bearer {LITELLM_KEY}"}
        r = await client.get(f"{LITELLM_URL}/v1/models", headers=headers)
        return r.json() if r.status_code == 200 else {"error": f"status {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/inference/complete")
async def complete(prompt: str, model: str = "hydra-70b", max_tokens: int = 500, request: Request = None):
    """Generate completion via LiteLLM"""
    ip = request.client.host if request and request.client else "unknown"

    if not check_rate_limit(ip, "inference"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for inference")

    add_audit_entry("inference", {"model": model, "prompt_length": len(prompt)}, "started", ip)

    try:
        headers = {
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json"
        }
        r = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=120.0
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# Audit and Admin
# =============================================================================

# =============================================================================
# Alertmanager Webhook
# =============================================================================

# Store recent alerts for UI display
recent_alerts: List[dict] = []
MAX_ALERTS = 100

class AlertmanagerPayload(BaseModel):
    receiver: Optional[str] = None
    status: Optional[str] = None
    alerts: Optional[List[dict]] = []
    groupLabels: Optional[dict] = {}
    commonLabels: Optional[dict] = {}
    commonAnnotations: Optional[dict] = {}
    externalURL: Optional[str] = None

@app.post("/webhooks/alertmanager")
async def alertmanager_webhook(payload: AlertmanagerPayload, request: Request):
    """Receive alerts from Prometheus Alertmanager"""
    ip = request.client.host if request and request.client else "unknown"

    processed_alerts = []
    for alert in payload.alerts or []:
        alert_status = alert.get("status", "unknown")
        alertname = alert.get("labels", {}).get("alertname", "Unknown")
        severity = alert.get("labels", {}).get("severity", "info")
        instance = alert.get("labels", {}).get("instance", "unknown")
        description = alert.get("annotations", {}).get("description",
                      alert.get("annotations", {}).get("summary", "No description"))

        # Add to audit log
        add_audit_entry(
            f"alert_{alert_status}",
            {
                "alertname": alertname,
                "severity": severity,
                "instance": instance,
                "description": description[:200]
            },
            alert_status,
            "alertmanager"
        )

        # Store in recent alerts
        alert_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": alert_status,
            "alertname": alertname,
            "severity": severity,
            "instance": instance,
            "description": description,
            "labels": alert.get("labels", {}),
            "startsAt": alert.get("startsAt"),
            "endsAt": alert.get("endsAt")
        }
        recent_alerts.append(alert_entry)
        processed_alerts.append(alert_entry)

    # Keep only recent alerts
    while len(recent_alerts) > MAX_ALERTS:
        recent_alerts.pop(0)

    return {
        "status": "received",
        "processed": len(processed_alerts),
        "alerts": processed_alerts
    }

@app.get("/alerts/recent")
async def get_recent_alerts(limit: int = 50):
    """Get recent alerts received from Alertmanager"""
    return {
        "alerts": recent_alerts[-limit:],
        "total": len(recent_alerts)
    }

@app.get("/audit/log")
async def get_audit_log(limit: int = 100):
    """Get recent audit log entries"""
    return {"entries": audit_log[-limit:], "total": len(audit_log)}

@app.get("/safety/pending")
async def get_pending_confirmations():
    """Get pending confirmation tokens (for admin visibility)"""
    cleanup_expired_tokens()
    return {
        "pending": [
            {
                "action": v["action"],
                "container": v["container"],
                "created": v["created"],
                "expires_in_seconds": max(0, int(v["expires"] - time.time()))
            }
            for v in pending_confirmations.values()
        ]
    }

@app.get("/safety/protected")
async def get_protected_containers():
    """List protected containers"""
    return {"protected_containers": list(PROTECTED_CONTAINERS)}

# =============================================================================
# GPU Status
# =============================================================================

@app.get("/gpu/status")
async def gpu_status():
    """Get GPU metrics from Prometheus"""
    gpus = []
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                            params={"query": "nvidia_gpu_utilization"})
        if r.status_code == 200:
            for item in r.json().get("data", {}).get("result", []):
                gpu = {
                    "index": item.get("metric", {}).get("gpu", ""),
                    "name": item.get("metric", {}).get("name", ""),
                    "utilization": safe_float(item.get("value", [0, 0])[1])
                }
                gpus.append(gpu)
    except:
        pass
    return {"gpus": gpus}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
