"""
Storage Tools for Hydra Agents

Provides file read/write operations on the shared NFS storage.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain.tools import tool

from .config import get_config


@tool
def read_file(path: str, max_bytes: int = 100000) -> str:
    """
    Read a file from shared Hydra storage.

    Args:
        path: File path (relative to shared_path or absolute)
        max_bytes: Maximum bytes to read (default: 100KB)

    Returns:
        File contents as string
    """
    config = get_config()
    full_path = _resolve_path(path, config)

    try:
        if not os.path.exists(full_path):
            return f"File not found: {path}"

        if not os.path.isfile(full_path):
            return f"Not a file: {path}"

        # Check file size
        file_size = os.path.getsize(full_path)
        if file_size > max_bytes:
            return f"File too large ({file_size} bytes). Max allowed: {max_bytes} bytes"

        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return content

    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """
    Write content to a file in shared Hydra storage.

    Args:
        path: File path (relative to shared_path or absolute)
        content: Content to write
        overwrite: Whether to overwrite existing files (default: False)

    Returns:
        Success message or error
    """
    config = get_config()
    full_path = _resolve_path(path, config)

    try:
        # Safety check - don't allow writing outside shared path
        shared_path = Path(config.shared_path).resolve()
        target_path = Path(full_path).resolve()

        if not str(target_path).startswith(str(shared_path)):
            return f"Security error: Cannot write outside shared storage"

        if os.path.exists(full_path) and not overwrite:
            return f"File exists and overwrite=False: {path}"

        # Create parent directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote {len(content)} bytes to {path}"

    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def _resolve_path(path: str, config) -> str:
    """Resolve relative paths to absolute paths within shared storage."""
    if os.path.isabs(path):
        return path
    return os.path.join(config.shared_path, path)


def list_directory(path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
    """
    List contents of a directory in shared storage.

    Args:
        path: Directory path (relative to shared_path or absolute)
        recursive: Whether to list recursively (default: False)

    Returns:
        List of file/directory info dicts
    """
    config = get_config()
    full_path = _resolve_path(path, config) if path else config.shared_path

    try:
        if not os.path.exists(full_path):
            return [{"error": f"Directory not found: {path}"}]

        if not os.path.isdir(full_path):
            return [{"error": f"Not a directory: {path}"}]

        results = []

        if recursive:
            for root, dirs, files in os.walk(full_path):
                rel_root = os.path.relpath(root, full_path)
                for d in dirs:
                    rel_path = os.path.join(rel_root, d) if rel_root != "." else d
                    results.append({
                        "name": d,
                        "path": rel_path,
                        "type": "directory",
                    })
                for f in files:
                    file_path = os.path.join(root, f)
                    rel_path = os.path.join(rel_root, f) if rel_root != "." else f
                    results.append({
                        "name": f,
                        "path": rel_path,
                        "type": "file",
                        "size": os.path.getsize(file_path),
                    })
        else:
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                if os.path.isdir(entry_path):
                    results.append({
                        "name": entry,
                        "type": "directory",
                    })
                else:
                    results.append({
                        "name": entry,
                        "type": "file",
                        "size": os.path.getsize(entry_path),
                    })

        return results

    except PermissionError:
        return [{"error": f"Permission denied: {path}"}]
    except Exception as e:
        return [{"error": str(e)}]


def list_models(model_type: str = "exl2") -> List[Dict[str, Any]]:
    """
    List available AI models in the models directory.

    Args:
        model_type: Model format - exl2, gguf, embeddings, diffusion

    Returns:
        List of model info dicts
    """
    config = get_config()

    # Models are stored on NFS at /mnt/user/models on Unraid
    # Mounted at /mnt/models on NixOS nodes
    model_paths = [
        "/mnt/models",  # NixOS mount
        "/mnt/user/models",  # Unraid direct
    ]

    model_dir = None
    for base in model_paths:
        test_path = os.path.join(base, model_type)
        if os.path.exists(test_path):
            model_dir = test_path
            break

    if not model_dir:
        return [{"error": f"Model directory not found for type: {model_type}"}]

    models = []
    try:
        for entry in os.listdir(model_dir):
            entry_path = os.path.join(model_dir, entry)
            if os.path.isdir(entry_path):
                # Get model size (sum of all files)
                total_size = 0
                file_count = 0
                for root, _, files in os.walk(entry_path):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))
                        file_count += 1

                models.append({
                    "name": entry,
                    "path": entry_path,
                    "type": model_type,
                    "size_gb": round(total_size / (1024**3), 2),
                    "files": file_count,
                })

        # Sort by name
        models.sort(key=lambda x: x["name"])
        return models

    except Exception as e:
        return [{"error": str(e)}]


def save_json(path: str, data: Any, pretty: bool = True) -> str:
    """
    Save data as JSON file in shared storage.

    Args:
        path: File path (relative to shared_path)
        data: Data to serialize as JSON
        pretty: Whether to format with indentation (default: True)

    Returns:
        Success message or error
    """
    try:
        content = json.dumps(data, indent=2 if pretty else None, default=str)
        config = get_config()
        full_path = _resolve_path(path, config)

        # Safety check
        shared_path = Path(config.shared_path).resolve()
        target_path = Path(full_path).resolve()

        if not str(target_path).startswith(str(shared_path)):
            return "Security error: Cannot write outside shared storage"

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully saved JSON to {path}"

    except Exception as e:
        return f"Error saving JSON: {str(e)}"


def load_json(path: str) -> Any:
    """
    Load JSON file from shared storage.

    Args:
        path: File path (relative to shared_path)

    Returns:
        Parsed JSON data or error dict
    """
    config = get_config()
    full_path = _resolve_path(path, config)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def get_storage_stats() -> Dict[str, Any]:
    """
    Get storage usage statistics for shared storage.

    Returns:
        Dict with storage statistics
    """
    config = get_config()

    stats = {
        "shared_path": config.shared_path,
        "available": False,
    }

    try:
        if os.path.exists(config.shared_path):
            statvfs = os.statvfs(config.shared_path)
            total = statvfs.f_blocks * statvfs.f_frsize
            free = statvfs.f_bfree * statvfs.f_frsize
            used = total - free

            stats.update({
                "available": True,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 1) if total > 0 else 0,
            })
    except Exception as e:
        stats["error"] = str(e)

    return stats
