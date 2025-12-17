#!/usr/bin/env python3
"""
Ingest knowledge files into Hydra semantic search.
"""
import os
import json
import glob
import urllib.request
import urllib.error

HYDRA_API = "http://192.168.1.244:8700"
KNOWLEDGE_DIR = "/mnt/user/appdata/hydra-dev/knowledge"

def ingest_file(filepath):
    """Ingest a single knowledge file."""
    filename = os.path.basename(filepath)
    title = filename.replace('.md', '').replace('-', ' ').title()

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Prepare request
    data = {
        "content": content,
        "source": f"knowledge/{filename}",
        "title": title,
        "doc_type": "knowledge",
        "tags": ["hydra", "knowledge", "documentation"],
        "collection": "hydra_knowledge"
    }

    try:
        req = urllib.request.Request(
            f"{HYDRA_API}/ingest/document",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return True, result
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:100]}"
    except Exception as e:
        return False, str(e)

def main():
    print("=== Ingesting Knowledge Files ===\n")

    files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md"))
    success_count = 0

    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        success, result = ingest_file(filepath)

        if success:
            doc_id = result.get('document_id', 'unknown')[:8]
            print(f"  ✓ {filename} (id: {doc_id}...)")
            success_count += 1
        else:
            print(f"  ✗ {filename}: {result}")

    print(f"\nIngested {success_count}/{len(files)} files")

if __name__ == "__main__":
    main()
