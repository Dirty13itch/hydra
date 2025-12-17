#!/usr/bin/env python3
"""
Ingest knowledge files to Letta archival memory.

Imports all knowledge/*.md files into the hydra-steward-v2 agent's
archival memory for cross-session retrieval.
"""

import json
import urllib.request
from pathlib import Path
from datetime import datetime

LETTA_URL = "http://192.168.1.244:8283"
AGENT_NAME = "hydra-steward-v2"

def get_agent_id() -> str:
    """Get the agent ID by name."""
    req = urllib.request.Request(f"{LETTA_URL}/v1/agents/")
    with urllib.request.urlopen(req, timeout=30) as resp:
        agents = json.loads(resp.read())
        for agent in agents:
            if agent.get("name") == AGENT_NAME:
                return agent.get("id")
    raise ValueError(f"Agent {AGENT_NAME} not found")

def insert_archival_memory(agent_id: str, content: str, source: str) -> dict:
    """Insert content into agent's archival memory."""
    payload = json.dumps({
        "text": content,
    }).encode()

    req = urllib.request.Request(
        f"{LETTA_URL}/v1/agents/{agent_id}/archival-memory",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return {"error": str(e), "detail": error_body}

def chunk_content(content: str, chunk_size: int = 4000) -> list:
    """Split content into chunks."""
    # Split by paragraphs first
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)
        if current_size + para_size > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks

def main():
    # Support both host path and container path
    knowledge_dir = Path("/mnt/user/appdata/hydra-dev/knowledge")
    if not knowledge_dir.exists():
        knowledge_dir = Path("/app/knowledge")

    print(f"Looking for knowledge files in: {knowledge_dir}")
    files = list(knowledge_dir.glob("*.md"))
    print(f"Found {len(files)} files")

    if not files:
        print("No files to ingest")
        return

    try:
        agent_id = get_agent_id()
        print(f"Found agent: {AGENT_NAME} ({agent_id})")
    except Exception as e:
        print(f"Error finding agent: {e}")
        return

    success = 0
    errors = 0

    for filepath in files:
        print(f"\nProcessing: {filepath.name}")
        content = filepath.read_text()

        # Chunk the content
        chunks = chunk_content(content)
        print(f"  Split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            source = f"file://{filepath}#chunk{i+1}"
            header = f"# Knowledge: {filepath.stem} (Part {i+1}/{len(chunks)})\n\n"

            result = insert_archival_memory(agent_id, header + chunk, source)

            if "error" in result:
                print(f"  Chunk {i+1}: ERROR - {result.get('detail', result['error'])[:100]}")
                errors += 1
            else:
                print(f"  Chunk {i+1}: OK")
                success += 1

    print(f"\n{'='*50}")
    print(f"Summary: {success} chunks ingested, {errors} errors")

if __name__ == "__main__":
    main()
