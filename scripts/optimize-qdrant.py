#!/usr/bin/env python3
"""
Qdrant Collection Optimization Script for Hydra Cluster

Features:
- HNSW index optimization for large collections
- Snapshot scheduling and management
- Collection health monitoring
- Memory usage analysis

Usage:
    python optimize-qdrant.py --optimize
    python optimize-qdrant.py --snapshot
    python optimize-qdrant.py --status

Generated: December 14, 2025
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.error

QDRANT_URL = "http://192.168.1.244:6333"

# Optimization thresholds
LARGE_COLLECTION_THRESHOLD = 10000  # vectors
OPTIMIZE_EF_CONSTRUCT = 200  # Higher for better recall
OPTIMIZE_M = 16  # Graph connections per layer


def api_request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Make an API request to Qdrant."""
    url = f"{QDRANT_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    request_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return {"error": str(e)}
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return {"error": str(e)}


def get_collections() -> list:
    """Get list of all collections."""
    result = api_request("/collections")
    if "result" in result:
        return result["result"]["collections"]
    return []


def get_collection_info(name: str) -> dict:
    """Get detailed info about a collection."""
    return api_request(f"/collections/{name}")


def optimize_collection(name: str, dry_run: bool = False) -> dict:
    """Optimize a collection's HNSW index."""
    info = get_collection_info(name)
    if "error" in info:
        return info

    collection = info.get("result", {})
    vectors_count = collection.get("vectors_count", 0)
    status = collection.get("status", "unknown")

    print(f"\n{'='*50}")
    print(f"Collection: {name}")
    print(f"Vectors: {vectors_count:,}")
    print(f"Status: {status}")

    # Check if optimization is needed
    if vectors_count < LARGE_COLLECTION_THRESHOLD:
        print(f"Skipping: Collection has fewer than {LARGE_COLLECTION_THRESHOLD:,} vectors")
        return {"status": "skipped", "reason": "small_collection"}

    # Get current HNSW config
    config = collection.get("config", {})
    hnsw_config = config.get("hnsw_config", {})
    current_m = hnsw_config.get("m", 0)
    current_ef = hnsw_config.get("ef_construct", 0)

    print(f"Current HNSW: m={current_m}, ef_construct={current_ef}")

    if current_m >= OPTIMIZE_M and current_ef >= OPTIMIZE_EF_CONSTRUCT:
        print("Skipping: Already optimized")
        return {"status": "skipped", "reason": "already_optimized"}

    if dry_run:
        print(f"[DRY RUN] Would optimize to: m={OPTIMIZE_M}, ef_construct={OPTIMIZE_EF_CONSTRUCT}")
        return {"status": "dry_run"}

    # Apply optimization
    print(f"Optimizing to: m={OPTIMIZE_M}, ef_construct={OPTIMIZE_EF_CONSTRUCT}")

    update_data = {
        "hnsw_config": {
            "m": OPTIMIZE_M,
            "ef_construct": OPTIMIZE_EF_CONSTRUCT
        }
    }

    result = api_request(f"/collections/{name}", method="PATCH", data=update_data)

    if "error" not in result:
        print("Optimization applied successfully!")
        # Trigger index rebuild
        api_request(f"/collections/{name}/index", method="POST")
        print("Index rebuild triggered")
        return {"status": "optimized"}

    return result


def create_snapshot(name: str) -> dict:
    """Create a snapshot of a collection."""
    print(f"Creating snapshot for: {name}")
    result = api_request(f"/collections/{name}/snapshots", method="POST")

    if "result" in result:
        snapshot_name = result["result"]["name"]
        print(f"Snapshot created: {snapshot_name}")
        return {"status": "created", "snapshot": snapshot_name}

    return result


def list_snapshots(name: str) -> list:
    """List snapshots for a collection."""
    result = api_request(f"/collections/{name}/snapshots")
    if "result" in result:
        return result["result"]
    return []


def cleanup_old_snapshots(name: str, keep: int = 7) -> int:
    """Remove old snapshots, keeping the most recent ones."""
    snapshots = list_snapshots(name)
    if len(snapshots) <= keep:
        return 0

    # Sort by creation time and delete oldest
    sorted_snapshots = sorted(snapshots, key=lambda x: x.get("creation_time", ""), reverse=True)
    to_delete = sorted_snapshots[keep:]

    deleted = 0
    for snap in to_delete:
        snap_name = snap.get("name", "")
        if snap_name:
            result = api_request(f"/collections/{name}/snapshots/{snap_name}", method="DELETE")
            if "error" not in result:
                print(f"Deleted old snapshot: {snap_name}")
                deleted += 1

    return deleted


def get_cluster_status() -> dict:
    """Get overall cluster status."""
    return api_request("/cluster")


def print_status():
    """Print detailed status of all collections."""
    print("\n" + "=" * 60)
    print("QDRANT COLLECTION STATUS")
    print("=" * 60)

    # Cluster info
    cluster = get_cluster_status()
    if "result" in cluster:
        peer_id = cluster["result"].get("peer_id", "unknown")
        status = cluster["result"].get("status", "unknown")
        print(f"\nCluster: peer_id={peer_id}, status={status}")

    # Collections
    collections = get_collections()
    print(f"\nCollections: {len(collections)}")

    total_vectors = 0
    total_size = 0

    for coll in collections:
        name = coll.get("name", "unknown")
        info = get_collection_info(name)

        if "result" in info:
            result = info["result"]
            vectors = result.get("vectors_count", 0)
            points = result.get("points_count", 0)
            status = result.get("status", "unknown")

            # Get indexed vectors
            indexed = result.get("indexed_vectors_count", vectors)
            pct_indexed = (indexed / vectors * 100) if vectors > 0 else 100

            # Get HNSW config
            config = result.get("config", {})
            hnsw = config.get("hnsw_config", {})
            m = hnsw.get("m", 0)
            ef = hnsw.get("ef_construct", 0)

            # Snapshots
            snapshots = list_snapshots(name)

            print(f"\n  {name}:")
            print(f"    Vectors: {vectors:,} ({pct_indexed:.1f}% indexed)")
            print(f"    Points: {points:,}")
            print(f"    Status: {status}")
            print(f"    HNSW: m={m}, ef_construct={ef}")
            print(f"    Snapshots: {len(snapshots)}")

            total_vectors += vectors

    print(f"\n{'='*60}")
    print(f"Total Vectors: {total_vectors:,}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Qdrant Collection Optimizer")
    parser.add_argument("--optimize", action="store_true", help="Optimize all large collections")
    parser.add_argument("--snapshot", action="store_true", help="Create snapshots of all collections")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old snapshots")
    parser.add_argument("--status", action="store_true", help="Show detailed status")
    parser.add_argument("--collection", type=str, help="Target specific collection")
    parser.add_argument("--dry-run", action="store_true", help="Don't apply changes")
    parser.add_argument("--keep-snapshots", type=int, default=7, help="Snapshots to keep per collection")

    args = parser.parse_args()

    # Default to status if no action specified
    if not any([args.optimize, args.snapshot, args.cleanup, args.status]):
        args.status = True

    collections = get_collections()
    if args.collection:
        collections = [{"name": args.collection}]

    if args.status:
        print_status()

    if args.optimize:
        print("\n" + "=" * 60)
        print("OPTIMIZING COLLECTIONS")
        print("=" * 60)

        for coll in collections:
            name = coll.get("name", "")
            if name:
                optimize_collection(name, dry_run=args.dry_run)

    if args.snapshot:
        print("\n" + "=" * 60)
        print("CREATING SNAPSHOTS")
        print("=" * 60)

        for coll in collections:
            name = coll.get("name", "")
            if name:
                create_snapshot(name)

    if args.cleanup:
        print("\n" + "=" * 60)
        print("CLEANING UP OLD SNAPSHOTS")
        print("=" * 60)

        total_deleted = 0
        for coll in collections:
            name = coll.get("name", "")
            if name:
                deleted = cleanup_old_snapshots(name, keep=args.keep_snapshots)
                total_deleted += deleted

        print(f"\nTotal snapshots deleted: {total_deleted}")


if __name__ == "__main__":
    main()
