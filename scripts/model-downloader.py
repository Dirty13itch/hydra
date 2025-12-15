#!/usr/bin/env python3
"""
Hydra Model Downloader

Automates downloading models from Hugging Face for the Hydra cluster.
Supports EXL2, GGUF, and diffusion models with integrity verification.

Usage:
    python model-downloader.py download bartowski/Llama-3.1-70B-Instruct-exl2 --quantization 4.0bpw
    python model-downloader.py list --type exl2
    python model-downloader.py verify Llama-3.1-70B-Instruct-exl2-4.0bpw
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from tqdm import tqdm

# Model storage paths
MODEL_PATHS = {
    "exl2": Path("/mnt/user/models/exl2"),
    "gguf": Path("/mnt/user/models/gguf"),
    "embeddings": Path("/mnt/user/models/embeddings"),
    "diffusion": Path("/mnt/user/models/diffusion"),
}

# Hugging Face base URL
HF_BASE_URL = "https://huggingface.co"

# Known model repositories for common models
KNOWN_MODELS = {
    # 70B+ Models (for hydra-ai)
    "llama-3.1-70b-instruct": {
        "repo": "bartowski/Llama-3.1-70B-Instruct-exl2",
        "type": "exl2",
        "recommended_quant": "4.0bpw",
        "vram_gb": {"4.0bpw": 42, "3.5bpw": 38, "4.5bpw": 48},
    },
    "llama-3.3-70b-instruct": {
        "repo": "bartowski/Llama-3.3-70B-Instruct-exl2",
        "type": "exl2",
        "recommended_quant": "4.0bpw",
        "vram_gb": {"4.0bpw": 42, "3.5bpw": 38},
    },
    "qwen-2.5-72b-instruct": {
        "repo": "bartowski/Qwen2.5-72B-Instruct-exl2",
        "type": "exl2",
        "recommended_quant": "4.0bpw",
        "vram_gb": {"4.0bpw": 44, "3.5bpw": 40},
    },
    "deepseek-r1-70b": {
        "repo": "bartowski/DeepSeek-R1-Distill-Llama-70B-exl2",
        "type": "exl2",
        "recommended_quant": "4.0bpw",
        "vram_gb": {"4.0bpw": 42},
    },

    # Medium Models (for hydra-compute or fast inference)
    "llama-3.1-8b-instruct": {
        "repo": "bartowski/Llama-3.1-8B-Instruct-exl2",
        "type": "exl2",
        "recommended_quant": "6.0bpw",
        "vram_gb": {"6.0bpw": 10, "8.0bpw": 12},
    },
    "qwen-2.5-14b-instruct": {
        "repo": "bartowski/Qwen2.5-14B-Instruct-exl2",
        "type": "exl2",
        "recommended_quant": "6.0bpw",
        "vram_gb": {"6.0bpw": 14, "8.0bpw": 18},
    },

    # Embedding Models
    "nomic-embed-text": {
        "repo": "nomic-ai/nomic-embed-text-v1.5",
        "type": "embeddings",
        "recommended_quant": None,
        "vram_gb": {"default": 1},
    },

    # Diffusion Models
    "flux-dev": {
        "repo": "black-forest-labs/FLUX.1-dev",
        "type": "diffusion",
        "recommended_quant": None,
        "vram_gb": {"default": 24},
    },
    "sdxl-base": {
        "repo": "stabilityai/stable-diffusion-xl-base-1.0",
        "type": "diffusion",
        "recommended_quant": None,
        "vram_gb": {"default": 8},
    },
}


@dataclass
class DownloadTask:
    """Download task configuration."""
    repo_id: str
    revision: Optional[str]
    files: List[str]
    output_dir: Path
    expected_size: int
    checksums: Dict[str, str]


class ModelDownloader:
    """Handles model downloads from Hugging Face."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "hydra-models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hf_token = os.environ.get("HF_TOKEN")

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for HF API."""
        headers = {"User-Agent": "hydra-model-downloader/1.0"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers

    def list_repo_files(self, repo_id: str, revision: str = "main") -> List[Dict]:
        """List files in a Hugging Face repository."""
        url = f"{HF_BASE_URL}/api/models/{repo_id}/tree/{revision}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def get_file_info(self, repo_id: str, filename: str, revision: str = "main") -> Dict:
        """Get information about a specific file."""
        url = f"{HF_BASE_URL}/api/models/{repo_id}/blob/{revision}/{filename}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def download_file(
        self,
        repo_id: str,
        filename: str,
        output_path: Path,
        revision: str = "main",
        resume: bool = True,
    ) -> bool:
        """Download a single file with resume support."""
        url = f"{HF_BASE_URL}/{repo_id}/resolve/{revision}/{filename}"

        # Check for existing partial download
        temp_path = output_path.with_suffix(output_path.suffix + ".part")
        existing_size = temp_path.stat().st_size if temp_path.exists() else 0

        headers = self.get_headers()
        if resume and existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)

            # Handle resume
            if response.status_code == 416:  # Range not satisfiable = complete
                temp_path.rename(output_path)
                return True

            response.raise_for_status()

            # Get total size
            total_size = int(response.headers.get("content-length", 0))
            if existing_size > 0:
                total_size += existing_size

            # Download with progress bar
            mode = "ab" if existing_size > 0 else "wb"
            with open(temp_path, mode) as f:
                with tqdm(
                    total=total_size,
                    initial=existing_size,
                    unit="B",
                    unit_scale=True,
                    desc=filename,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))

            # Rename completed download
            temp_path.rename(output_path)
            return True

        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            return False

    def download_model(
        self,
        repo_id: str,
        model_type: str,
        quantization: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Download a complete model from Hugging Face.

        Args:
            repo_id: HuggingFace repo (e.g., "bartowski/Llama-3.1-70B-Instruct-exl2")
            model_type: Model type (exl2, gguf, embeddings, diffusion)
            quantization: Quantization level (e.g., "4.0bpw" for EXL2)
            output_name: Custom output directory name

        Returns:
            Tuple of (success, output_path)
        """
        base_path = MODEL_PATHS.get(model_type)
        if not base_path:
            return False, f"Unknown model type: {model_type}"

        # Determine output directory
        if output_name:
            output_dir = base_path / output_name
        else:
            # Extract model name from repo
            model_name = repo_id.split("/")[-1]
            if quantization:
                model_name = f"{model_name}-{quantization}"
            output_dir = base_path / model_name

        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Downloading {repo_id} to {output_dir}")

        # Get file list
        revision = quantization if quantization else "main"

        try:
            files = self.list_repo_files(repo_id, revision)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Try main branch for GGUF/other types
                revision = "main"
                files = self.list_repo_files(repo_id, revision)
            else:
                raise

        # Filter relevant files
        download_files = []
        for file_info in files:
            filename = file_info.get("path", "")
            # Skip non-model files
            if any(skip in filename for skip in [".md", ".txt", ".gitattributes", "README"]):
                continue
            download_files.append(filename)

        if not download_files:
            return False, "No model files found in repository"

        print(f"Found {len(download_files)} files to download")

        # Download each file
        success = True
        for filename in download_files:
            file_path = output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.exists():
                print(f"Skipping {filename} (already exists)")
                continue

            if not self.download_file(repo_id, filename, file_path, revision):
                success = False
                print(f"Failed to download: {filename}")

        return success, str(output_dir)

    def verify_model(self, model_path: Path) -> Tuple[bool, List[str]]:
        """
        Verify model integrity using checksums if available.

        Returns:
            Tuple of (all_valid, list_of_issues)
        """
        issues = []

        if not model_path.exists():
            return False, [f"Model path does not exist: {model_path}"]

        # Check for required files based on type
        if model_path.parent.name == "exl2":
            required_patterns = ["*.safetensors", "config.json", "tokenizer*"]
        elif model_path.parent.name == "gguf":
            required_patterns = ["*.gguf"]
        else:
            required_patterns = []

        for pattern in required_patterns:
            matches = list(model_path.glob(pattern))
            if not matches:
                issues.append(f"Missing required file pattern: {pattern}")

        # Check for SHA256 checksum file
        checksum_file = model_path / "checksums.sha256"
        if checksum_file.exists():
            with open(checksum_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        expected_hash, filename = parts[0], parts[1]
                        file_path = model_path / filename

                        if not file_path.exists():
                            issues.append(f"Missing file: {filename}")
                            continue

                        actual_hash = self._compute_sha256(file_path)
                        if actual_hash != expected_hash:
                            issues.append(f"Checksum mismatch: {filename}")

        return len(issues) == 0, issues

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def list_local_models(model_type: Optional[str] = None) -> Dict[str, List[Dict]]:
    """List locally installed models."""
    results = {}

    paths_to_check = (
        {model_type: MODEL_PATHS[model_type]} if model_type else MODEL_PATHS
    )

    for mtype, path in paths_to_check.items():
        if not path.exists():
            results[mtype] = []
            continue

        models = []
        for item in path.iterdir():
            if item.is_dir():
                # Get size
                total_size = sum(
                    f.stat().st_size for f in item.rglob("*") if f.is_file()
                )

                models.append({
                    "name": item.name,
                    "path": str(item),
                    "size_gb": round(total_size / (1024**3), 2),
                    "files": len(list(item.rglob("*"))),
                })

        results[mtype] = sorted(models, key=lambda x: x["name"])

    return results


def list_known_models() -> None:
    """Print list of known/recommended models."""
    print("\n=== Recommended Models for Hydra Cluster ===\n")

    print("70B+ Models (hydra-ai - 56GB VRAM):")
    print("-" * 50)
    for name, info in KNOWN_MODELS.items():
        if info.get("vram_gb", {}).get(info.get("recommended_quant", "default"), 0) >= 30:
            quant = info.get("recommended_quant") or "default"
            vram = info["vram_gb"].get(quant, "?")
            print(f"  {name}")
            print(f"    Repo: {info['repo']}")
            print(f"    Recommended: {quant} (~{vram}GB VRAM)")
            print()

    print("\nMedium Models (hydra-compute - 16GB VRAM):")
    print("-" * 50)
    for name, info in KNOWN_MODELS.items():
        vram = info.get("vram_gb", {}).get(info.get("recommended_quant", "default"), 100)
        if 5 <= vram < 30:
            quant = info.get("recommended_quant") or "default"
            print(f"  {name}")
            print(f"    Repo: {info['repo']}")
            print(f"    Recommended: {quant} (~{vram}GB VRAM)")
            print()

    print("\nEmbedding & Diffusion Models:")
    print("-" * 50)
    for name, info in KNOWN_MODELS.items():
        if info["type"] in ["embeddings", "diffusion"]:
            print(f"  {name}")
            print(f"    Repo: {info['repo']}")
            print(f"    Type: {info['type']}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Hydra Model Downloader")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("repo", help="HuggingFace repo ID or known model name")
    download_parser.add_argument("--type", "-t", choices=["exl2", "gguf", "embeddings", "diffusion"],
                                 default="exl2", help="Model type")
    download_parser.add_argument("--quantization", "-q", help="Quantization (e.g., 4.0bpw)")
    download_parser.add_argument("--output", "-o", help="Custom output directory name")

    # List command
    list_parser = subparsers.add_parser("list", help="List models")
    list_parser.add_argument("--type", "-t", choices=["exl2", "gguf", "embeddings", "diffusion"],
                            help="Filter by model type")
    list_parser.add_argument("--known", "-k", action="store_true",
                            help="Show known/recommended models")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify model integrity")
    verify_parser.add_argument("model", help="Model name or path")
    verify_parser.add_argument("--type", "-t", choices=["exl2", "gguf", "embeddings", "diffusion"],
                              default="exl2", help="Model type")

    args = parser.parse_args()

    if args.command == "download":
        downloader = ModelDownloader()

        # Check if it's a known model name
        if args.repo in KNOWN_MODELS:
            model_info = KNOWN_MODELS[args.repo]
            repo = model_info["repo"]
            model_type = model_info["type"]
            quant = args.quantization or model_info.get("recommended_quant")
        else:
            repo = args.repo
            model_type = args.type
            quant = args.quantization

        success, result = downloader.download_model(
            repo, model_type, quant, args.output
        )

        if success:
            print(f"\n✅ Download complete: {result}")
        else:
            print(f"\n❌ Download failed: {result}")
            sys.exit(1)

    elif args.command == "list":
        if args.known:
            list_known_models()
        else:
            models = list_local_models(args.type)
            print("\n=== Installed Models ===\n")
            for mtype, model_list in models.items():
                print(f"{mtype.upper()}:")
                if model_list:
                    for m in model_list:
                        print(f"  - {m['name']} ({m['size_gb']}GB, {m['files']} files)")
                else:
                    print("  (none)")
                print()

    elif args.command == "verify":
        downloader = ModelDownloader()
        model_path = Path(args.model)

        # If just a name, resolve to full path
        if not model_path.exists():
            model_path = MODEL_PATHS[args.type] / args.model

        valid, issues = downloader.verify_model(model_path)

        if valid:
            print(f"✅ Model verified: {model_path}")
        else:
            print(f"❌ Model verification failed: {model_path}")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
