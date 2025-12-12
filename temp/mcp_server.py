"""Hydra MCP Server - Unified Control Plane API for Claude Code"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os
from datetime import datetime
from typing import Optional
import json
import math

app = FastAPI(title="Hydra MCP Server", version="1.0.0")

# Configuration from environment
LETTA_URL = os.getenv("LETTA_URL", "http://hydra-letta:8283")
LETTA_TOKEN = os.getenv("LETTA_TOKEN", "")
LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://hydra-prometheus:9090")
CREWAI_URL = os.getenv("CREWAI_URL", "http://hydra-crewai:8500")
LITELLM_URL = os.getenv("LITELLM_URL", "http://hydra-litellm:4000")
LITELLM_KEY = os.getenv("LITELLM_KEY", "")
NEO4J_URI = os.getenv("NEO4J_URI", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://hydra-qdrant:6333")

client = httpx.AsyncClient(timeout=30.0)

def safe_float(value, default=0.0):
    """Convert value to float, handling NaN/infinity"""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except:
        return default

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}

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

@app.get("/metrics/summary")
async def metrics_summary():
    """Get key metrics summary from Prometheus"""
    queries = {
        "cpu_avg": '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100',
        "memory_used_pct": "avg((1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes) * 100)",
        "disk_used_pct": 'avg((1 - node_filesystem_avail_bytes{fstype=~"ext4|xfs|btrfs"}/node_filesystem_size_bytes{fstype=~"ext4|xfs|btrfs"}) * 100)',
        "containers_running": 'count(container_last_seen{name!=""})',
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
        except Exception as e:
            results[name] = None
    return results

@app.get("/metrics/nodes")
async def metrics_nodes():
    """Get per-node metrics"""
    nodes = {}
    try:
        # Get node names
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": "node_uname_info"})
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", {}).get("result", []):
                instance = item.get("metric", {}).get("instance", "")
                nodename = item.get("metric", {}).get("nodename", instance)
                nodes[instance] = {"name": nodename}

        # Get CPU per node
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                            params={"query": "100-avg(rate(node_cpu_seconds_total{mode='idle'}[5m]))by(instance)*100"})
        if r.status_code == 200:
            for item in r.json().get("data", {}).get("result", []):
                instance = item.get("metric", {}).get("instance", "")
                if instance in nodes:
                    nodes[instance]["cpu_pct"] = safe_float(item.get("value", [0, 0])[1])

        # Get memory per node
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

@app.post("/letta/message")
async def send_letta_message(message: str):
    """Send message to Letta agent"""
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
            agent = r.json()
            return agent.get("memory", {})
        return {"error": f"status {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/crews/run/{crew_name}")
async def run_crew(crew_name: str, topic: Optional[str] = None):
    """Trigger a CrewAI crew execution"""
    if crew_name not in ["monitoring", "research", "maintenance"]:
        raise HTTPException(status_code=400, detail="Unknown crew")

    try:
        payload = {"topic": topic} if topic else {}
        r = await client.post(f"{CREWAI_URL}/run/{crew_name}", json=payload, timeout=600.0)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

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
async def complete(prompt: str, model: str = "hydra-70b", max_tokens: int = 500):
    """Generate completion via LiteLLM"""
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

@app.get("/containers/list")
async def list_containers():
    """List running containers (via cAdvisor metrics)"""
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query",
                            params={"query": 'container_last_seen{name!=""}'})
        if r.status_code == 200:
            data = r.json()
            containers = []
            for item in data.get("data", {}).get("result", []):
                name = item.get("metric", {}).get("name", "")
                if name and not name.startswith("/"):
                    containers.append(name)
            return {"containers": sorted(set(containers)), "count": len(set(containers))}
        return {"error": "prometheus unavailable"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/services/status")
async def services_status():
    """Check status of key Hydra services"""
    services = {}
    checks = [
        ("letta", f"{LETTA_URL}/v1/health/"),
        ("crewai", f"{CREWAI_URL}/health"),
        ("qdrant", f"{QDRANT_URL}/collections"),
        ("litellm", f"{LITELLM_URL}/health"),
        ("prometheus", f"{PROMETHEUS_URL}/-/ready"),
    ]

    for name, url in checks:
        try:
            r = await client.get(url, timeout=5.0)
            services[name] = "up" if r.status_code in [200, 204] else f"status:{r.status_code}"
        except:
            services[name] = "down"

    return services

@app.get("/gpu/status")
async def gpu_status():
    """Get GPU metrics from Prometheus"""
    gpus = []
    try:
        # Query GPU utilization
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

from fastapi.responses import PlainTextResponse
import time

# Track request counts and latencies
request_counts = {}
start_time = time.time()

@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-format metrics endpoint"""
    lines = []

    # MCP Server info
    lines.append("# HELP hydra_mcp_info MCP Server information")
    lines.append("# TYPE hydra_mcp_info gauge")
    lines.append('hydra_mcp_info{version="1.0.0"} 1')

    # Uptime
    uptime = time.time() - start_time
    lines.append("# HELP hydra_mcp_uptime_seconds MCP Server uptime in seconds")
    lines.append("# TYPE hydra_mcp_uptime_seconds counter")
    lines.append(f"hydra_mcp_uptime_seconds {uptime:.2f}")

    # Service health checks (1 = up, 0 = down)
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

    # Qdrant collections count
    try:
        r = await client.get(f"{QDRANT_URL}/collections")
        if r.status_code == 200:
            count = len(r.json().get("result", {}).get("collections", []))
            lines.append("# HELP hydra_qdrant_collections_total Number of Qdrant collections")
            lines.append("# TYPE hydra_qdrant_collections_total gauge")
            lines.append(f"hydra_qdrant_collections_total {count}")
    except:
        pass

    # Knowledge base vectors
    try:
        r = await client.get(f"{QDRANT_URL}/collections/hydra_knowledge")
        if r.status_code == 200:
            points = r.json().get("result", {}).get("points_count", 0)
            lines.append("# HELP hydra_knowledge_vectors_total Number of vectors in knowledge base")
            lines.append("# TYPE hydra_knowledge_vectors_total gauge")
            lines.append(f"hydra_knowledge_vectors_total {points}")
    except:
        pass

    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
