#!/usr/bin/env python3
"""Import Hydra knowledge files into Letta archival memory."""

import os
import requests
import glob

LETTA_URL = "http://192.168.1.244:8283"
AGENT_ID = "agent-b3fb1747-1a5b-4c94-b713-11d6403350bf"
KNOWLEDGE_DIR = r"C:\Users\shaun\projects\hydra\knowledge"

def import_file(filepath: str) -> dict:
    """Import a single markdown file into Letta archival memory."""
    filename = os.path.basename(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add metadata header to content
    text = f"[HYDRA KNOWLEDGE FILE: {filename}]\n\n{content}"

    response = requests.post(
        f"{LETTA_URL}/v1/agents/{AGENT_ID}/archival",
        json={"text": text},
        headers={"Content-Type": "application/json"},
        timeout=60
    )

    return {
        "file": filename,
        "status": response.status_code,
        "response": response.json() if response.status_code == 200 else response.text
    }

def main():
    """Import all knowledge files."""
    # Get all markdown files
    pattern = os.path.join(KNOWLEDGE_DIR, "*.md")
    files = glob.glob(pattern)

    print(f"Found {len(files)} knowledge files to import")
    print("-" * 50)

    results = []
    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        print(f"Importing: {filename}...")

        try:
            result = import_file(filepath)
            results.append(result)

            if result["status"] == 200:
                print(f"  ✓ Success")
            else:
                print(f"  ✗ Failed: {result['status']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({"file": filename, "status": "error", "response": str(e)})

    print("-" * 50)
    success = sum(1 for r in results if r["status"] == 200)
    print(f"Imported {success}/{len(files)} files successfully")

    return results

if __name__ == "__main__":
    main()
