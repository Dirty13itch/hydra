#!/usr/bin/env python3
import os
import json
import requests

ARCHIVE_ID = "archive-40324e79-7c65-4153-bb75-c5c7543c8cd2"  # hydra-steward-v2's archive
LETTA_URL = "http://192.168.1.244:8283"
KNOWLEDGE_DIR = "/app/repo/knowledge"

files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith('.md')]
print(f"Found {len(files)} knowledge files")

success = 0
for filename in files:
    filepath = os.path.join(KNOWLEDGE_DIR, filename)
    with open(filepath, 'r') as f:
        content = f.read()

    payload = {
        "text": content,
        "metadata": {"source": filename}
    }

    try:
        resp = requests.post(
            f"{LETTA_URL}/v1/archives/{ARCHIVE_ID}/passages",
            json=payload,
            timeout=60
        )

        if resp.status_code == 200:
            passage_id = resp.json().get('id', 'unknown')
            print(f"OK: {filename} -> {passage_id}")
            success += 1
        else:
            print(f"ERR: {filename} -> {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"ERR: {filename} -> {str(e)}")

print(f"\nImported {success}/{len(files)} files")
