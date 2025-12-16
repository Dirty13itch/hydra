#!/usr/bin/env python3
"""
Knowledge Base Indexer

Indexes all knowledge/*.md files to the Hydra knowledge base.
Uses the /ingest/document endpoint on the Hydra Tools API.

Usage:
    python scripts/index_knowledge_base.py
    python scripts/index_knowledge_base.py --dry-run
    python scripts/index_knowledge_base.py --file knowledge/automation.md
"""

import argparse
import json
import sys
from pathlib import Path
import requests

# Configuration
HYDRA_API_URL = "http://192.168.1.244:8700"
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
COLLECTION = "hydra_knowledge"


def get_file_metadata(filepath: Path) -> dict:
    """Extract metadata from a knowledge file."""
    # Determine doc type from filename
    name = filepath.stem.lower()

    # Tag mapping
    tag_mapping = {
        "automation": ["automation", "n8n", "agents", "crewai"],
        "creative-stack": ["creative", "comfyui", "media", "generation"],
        "databases": ["databases", "postgresql", "qdrant", "redis"],
        "inference-stack": ["inference", "tabbyapi", "ollama", "litellm"],
        "infrastructure": ["infrastructure", "hardware", "network", "nodes"],
        "media-stack": ["media", "jellyfin", "tts", "streaming"],
        "models": ["models", "llm", "exllama", "quantization"],
        "observability": ["observability", "prometheus", "grafana", "monitoring"],
        "troubleshooting": ["troubleshooting", "debugging", "fixes"],
    }

    tags = tag_mapping.get(name, ["knowledge", "documentation"])
    tags.append("knowledge-base")

    return {
        "title": f"Knowledge: {filepath.stem.replace('-', ' ').title()}",
        "source": f"file://{filepath}",
        "doc_type": "knowledge-document",
        "tags": tags,
        "collection": COLLECTION,
    }


def read_file_content(filepath: Path) -> str:
    """Read the content of a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def index_document(content: str, metadata: dict, dry_run: bool = False) -> dict:
    """Index a document to the knowledge base."""
    payload = {
        "content": content,
        **metadata,
    }

    if dry_run:
        print(f"[DRY-RUN] Would index: {metadata['title']}")
        print(f"  Source: {metadata['source']}")
        print(f"  Tags: {metadata['tags']}")
        print(f"  Content length: {len(content)} chars")
        return {"dry_run": True, "title": metadata["title"]}

    try:
        response = requests.post(
            f"{HYDRA_API_URL}/ingest/document",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        print(f"[OK] Indexed: {metadata['title']}")
        print(f"  Chunks: {result.get('chunks', 'N/A')}")
        print(f"  Document ID: {result.get('document_id', 'N/A')}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to index {metadata['title']}: {e}")
        return {"error": str(e), "title": metadata["title"]}


def check_api_health() -> bool:
    """Check if the Hydra API is healthy and has the ingest endpoint."""
    try:
        response = requests.get(f"{HYDRA_API_URL}/health", timeout=10)
        health = response.json()
        print(f"API Status: {health.get('status', 'unknown')}")
        print(f"API Version: {health.get('version', 'unknown')}")

        # Check if ingest endpoint exists
        root = requests.get(f"{HYDRA_API_URL}/", timeout=10).json()
        endpoints = root.get("endpoints", {})

        if "ingest" not in endpoints:
            print("[WARNING] /ingest endpoint not found - API may need restart for v1.3.0")
            return False

        return True
    except Exception as e:
        print(f"[ERROR] API health check failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Index knowledge files to Hydra knowledge base")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be indexed without indexing")
    parser.add_argument("--file", type=str, help="Index a specific file instead of all")
    parser.add_argument("--force", action="store_true", help="Skip API health check")
    args = parser.parse_args()

    print("=" * 60)
    print("Hydra Knowledge Base Indexer")
    print("=" * 60)

    # Check API health unless forced
    if not args.force and not args.dry_run:
        if not check_api_health():
            print("\n[ERROR] API not ready. Use --force to skip check or --dry-run for preview.")
            sys.exit(1)

    # Determine files to index
    if args.file:
        files = [Path(args.file)]
        if not files[0].exists():
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)
    else:
        files = sorted(KNOWLEDGE_DIR.glob("*.md"))

    if not files:
        print("[WARNING] No files to index")
        sys.exit(0)

    print(f"\nIndexing {len(files)} file(s)...\n")

    results = []
    for filepath in files:
        print(f"Processing: {filepath.name}")
        content = read_file_content(filepath)
        metadata = get_file_metadata(filepath)
        result = index_document(content, metadata, dry_run=args.dry_run)
        results.append(result)
        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    success = sum(1 for r in results if "error" not in r and not r.get("dry_run"))
    errors = sum(1 for r in results if "error" in r)
    dry_runs = sum(1 for r in results if r.get("dry_run"))

    if dry_runs > 0:
        print(f"Dry run completed: {dry_runs} file(s) would be indexed")
    else:
        print(f"Indexed: {success} file(s)")
        if errors > 0:
            print(f"Errors: {errors} file(s)")


if __name__ == "__main__":
    main()
