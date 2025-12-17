#!/usr/bin/env python3
"""Index all knowledge/*.md files to Qdrant hydra_knowledge collection."""

import os
import json
import urllib.request
from pathlib import Path

API_URL = "http://192.168.1.244:8700/ingest/document"

def index_file(filepath: Path) -> dict:
    """Index a single knowledge file."""
    title = filepath.stem
    content = filepath.read_text()[:15000]  # Limit to 15k chars

    payload = {
        "content": content,
        "title": title,
        "source": str(filepath),
        "collection": "hydra_knowledge"
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return {"file": title, "status": "success", "result": result}
    except Exception as e:
        return {"file": title, "status": "error", "error": str(e)}

def main():
    # Support both host path and container path
    knowledge_dir = Path("/mnt/user/appdata/hydra-dev/knowledge")
    if not knowledge_dir.exists():
        knowledge_dir = Path("/app/knowledge")
    files = list(knowledge_dir.glob("*.md"))

    print(f"Found {len(files)} knowledge files to index")

    results = []
    for f in files:
        print(f"Indexing: {f.name}...")
        result = index_file(f)
        results.append(result)
        print(f"  -> {result['status']}")

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\nCompleted: {success}/{len(files)} files indexed successfully")

if __name__ == "__main__":
    main()
