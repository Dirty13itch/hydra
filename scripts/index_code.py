#!/usr/bin/env python3
"""Index key Python modules to Qdrant code collection."""

import json
import urllib.request
from pathlib import Path

API_URL = "http://192.168.1.244:8700/ingest/document"

# Key modules to index (most important for retrieval)
KEY_MODULES = [
    "api.py",
    "self_diagnosis.py",
    "resource_optimization.py",
    "knowledge_optimization.py",
    "capability_expansion.py",
    "routellm.py",
    "preference_learning.py",
    "activity.py",
    "hardware_discovery.py",
    "scheduler.py",
    "letta_bridge.py",
    "search_api.py",
    "health_api.py",
    "voice_api.py",
    "reconcile_api.py",
    "constitution.py",
    "self_improvement.py",
    "sandbox.py",
    "memory_architecture.py",
    "predictive_maintenance.py",
    "character_consistency.py",
    "asset_quality.py",
    "autonomous_controller.py",
]

def index_file(filepath: Path) -> dict:
    """Index a single code file."""
    title = f"Code: {filepath.name}"
    content = filepath.read_text()[:30000]  # Limit to 30k chars

    payload = {
        "content": content,
        "title": title,
        "source": str(filepath),
        "doc_type": "python-code",
        "tags": ["code", "python", "hydra-tools", filepath.stem],
        "collection": "code"
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return {"file": filepath.name, "status": "success", "chunks": result.get("chunks", "N/A")}
    except Exception as e:
        return {"file": filepath.name, "status": "error", "error": str(e)}

def main():
    # Support both host path and container path
    code_dir = Path("/mnt/user/appdata/hydra-dev/src/hydra_tools")
    if not code_dir.exists():
        code_dir = Path("/app/src/hydra_tools")

    print(f"Looking for key modules in: {code_dir}")

    indexed = 0
    errors = 0

    for module_name in KEY_MODULES:
        filepath = code_dir / module_name
        if filepath.exists():
            print(f"Indexing: {module_name}...")
            result = index_file(filepath)
            if result["status"] == "success":
                print(f"  -> success ({result.get('chunks', 'N/A')} chunks)")
                indexed += 1
            else:
                print(f"  -> error: {result.get('error', 'unknown')}")
                errors += 1
        else:
            print(f"Skipping: {module_name} (not found)")

    print(f"\nCompleted: {indexed} files indexed, {errors} errors")

if __name__ == "__main__":
    main()
