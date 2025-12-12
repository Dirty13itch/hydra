#!/usr/bin/env python3
import requests
import json

OLLAMA_URL = "http://192.168.1.203:11434"
QDRANT_URL = "http://hydra-qdrant:6333"
COLLECTION = "hydra_knowledge"

# New service documentation to add
new_docs = [
    {"text": "The Hydra MCP Server runs on port 8600 and provides REST APIs for cluster management including health checks, container management, GPU monitoring, service status, and audit logging.", "source": "mcp"},
    {"text": "MCP Server endpoints include /health, /services/status, /containers/list, /containers/restart, /gpu/status, /metrics/summary, /metrics/nodes, and /audit/log for comprehensive cluster monitoring.", "source": "mcp"},
    {"text": "The Hydra Control Plane UI runs on port 3200 and provides a real-time dashboard showing cluster nodes, services, containers, GPU metrics, and an audit log.", "source": "ui"},
    {"text": "The Control Plane dashboard displays three node cards for hydra-ai, hydra-compute, and hydra-storage, each showing CPU, memory, and GPU metrics with real-time sparklines.", "source": "ui"},
    {"text": "Users can restart containers from the Control Plane UI. Protected containers like hydra-mcp require confirmation before restart to prevent accidental service disruption.", "source": "ui"},
    {"text": "The Letta chat interface in the Control Plane allows users to interact with the hydra-steward AI agent directly from the dashboard for cluster queries and management.", "source": "ui"},
    {"text": "Prometheus runs on port 9090 and scrapes metrics from node_exporter, nvidia_gpu_exporter, and the MCP server. It stores time-series data for monitoring and alerting.", "source": "monitoring"},
    {"text": "GPU temperature alerts are configured to warn at 75C and alert critically at 85C. Alertmanager can send notifications via webhook to the MCP server or Discord.", "source": "monitoring"},
    {"text": "The hydra-steward is a Letta AI agent that can answer questions about the cluster, help with troubleshooting, and provide operational guidance. It runs on the Letta server at port 8283.", "source": "letta"},
    {"text": "Qdrant vector database runs on port 6333 and stores the hydra_knowledge collection containing cluster documentation for semantic search.", "source": "qdrant"},
    {"text": "hydra-ai hosts the RTX 5090 for primary inference and RTX 4090 for secondary workloads. TabbyAPI runs on these GPUs serving large language models.", "source": "gpu"},
    {"text": "hydra-compute hosts RTX 5070 Ti and RTX 3060 for creative workloads and overflow inference. Ollama runs here for smaller model inference.", "source": "gpu"},
    {"text": "The Hydra cluster uses the 192.168.1.0/24 network. hydra-storage is at 192.168.1.244, hydra-ai at 192.168.1.250, and hydra-compute at 192.168.1.203.", "source": "network"},
]

def get_embedding(text):
    r = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "nomic-embed-text:latest", "prompt": text})
    if r.status_code == 200:
        return r.json().get("embedding", [])
    return None

def get_next_id():
    r = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll", json={"limit": 100, "with_payload": False, "with_vector": False})
    if r.status_code == 200:
        points = r.json().get("result", {}).get("points", [])
        if points:
            # Handle both int and string IDs
            ids = [int(p["id"]) if isinstance(p["id"], (int, str)) and str(p["id"]).isdigit() else 0 for p in points]
            return max(ids) + 1 if ids else 46
    return 46

if __name__ == "__main__":
    next_id = get_next_id()
    print(f"Starting at ID {next_id}")
    added = 0

    for doc in new_docs:
        embedding = get_embedding(doc["text"])
        if embedding:
            point = {"id": next_id, "vector": embedding, "payload": {"text": doc["text"], "source": doc["source"]}}
            r = requests.put(f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true", json={"points": [point]})
            if r.status_code == 200:
                added += 1
                src = doc["source"]
                print(f"Added {next_id}: {src}")
            next_id += 1

    print(f"\nDone! Added {added}/{len(new_docs)} documents")
