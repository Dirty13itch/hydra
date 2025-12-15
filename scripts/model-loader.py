#!/usr/bin/env python3
"""
TabbyAPI Model Loader

Manages model loading for TabbyAPI with preset configurations.
Supports loading models via API, reloading, and preset management.

Usage:
    python model-loader.py load <model_name>
    python model-loader.py preset <preset_name>
    python model-loader.py unload
    python model-loader.py status
    python model-loader.py list
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# Configuration
TABBY_URL = os.getenv("TABBY_URL", "http://192.168.1.250:5000")
MODELS_DIR = os.getenv("MODELS_DIR", "/mnt/models/exl2")
CONFIG_FILE = Path(__file__).parent / "model-presets.yaml"


@dataclass
class ModelPreset:
    """Model loading preset configuration."""
    name: str
    model_name: str
    max_seq_len: int = 8192
    cache_size: int = 8192
    tensor_parallel: bool = False
    gpu_split: Optional[List[float]] = None
    draft_model: Optional[str] = None
    draft_ratio: float = 0.0
    description: str = ""


# Default presets
DEFAULT_PRESETS = {
    "llama-70b-default": ModelPreset(
        name="llama-70b-default",
        model_name="Llama-3.1-70B-Instruct-exl2-4.0bpw",
        max_seq_len=8192,
        cache_size=8192,
        gpu_split=[0.6, 0.4],  # 5090: 60%, 4090: 40%
        description="Llama 3.1 70B at 4bpw for general use",
    ),
    "llama-70b-long": ModelPreset(
        name="llama-70b-long",
        model_name="Llama-3.1-70B-Instruct-exl2-4.0bpw",
        max_seq_len=32768,
        cache_size=32768,
        gpu_split=[0.6, 0.4],
        description="Llama 3.1 70B with extended context",
    ),
    "llama-8b-fast": ModelPreset(
        name="llama-8b-fast",
        model_name="Llama-3.1-8B-Instruct-exl2-6.0bpw",
        max_seq_len=8192,
        cache_size=8192,
        description="Llama 3.1 8B for fast inference",
    ),
    "deepseek-coder": ModelPreset(
        name="deepseek-coder",
        model_name="DeepSeek-Coder-V2-Instruct-exl2-4.0bpw",
        max_seq_len=16384,
        cache_size=16384,
        gpu_split=[0.6, 0.4],
        description="DeepSeek Coder V2 for code generation",
    ),
    "qwen-72b": ModelPreset(
        name="qwen-72b",
        model_name="Qwen2.5-72B-Instruct-exl2-4.0bpw",
        max_seq_len=8192,
        cache_size=8192,
        gpu_split=[0.6, 0.4],
        description="Qwen 2.5 72B for multilingual tasks",
    ),
    "creative": ModelPreset(
        name="creative",
        model_name="Fimbulvetr-11B-v2-exl2-6.0bpw",
        max_seq_len=8192,
        cache_size=8192,
        description="Uncensored creative writing model",
    ),
}


def load_presets() -> Dict[str, ModelPreset]:
    """Load presets from file, falling back to defaults."""
    presets = DEFAULT_PRESETS.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                custom = yaml.safe_load(f)
                if custom and "presets" in custom:
                    for name, cfg in custom["presets"].items():
                        presets[name] = ModelPreset(name=name, **cfg)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load custom presets: {e}[/yellow]")

    return presets


def get_current_model() -> Optional[Dict[str, Any]]:
    """Get currently loaded model info."""
    try:
        response = httpx.get(f"{TABBY_URL}/v1/model", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def list_available_models() -> List[str]:
    """List available models in the models directory."""
    models_path = Path(MODELS_DIR)

    if not models_path.exists():
        console.print(f"[red]Models directory not found: {MODELS_DIR}[/red]")
        return []

    models = []
    for item in models_path.iterdir():
        if item.is_dir():
            # Check if it looks like a model directory
            config = item / "config.json"
            if config.exists():
                models.append(item.name)

    return sorted(models)


def load_model(preset: ModelPreset) -> bool:
    """Load a model into TabbyAPI."""
    console.print(f"\n[cyan]Loading model: {preset.model_name}[/cyan]")
    console.print(f"Max sequence length: {preset.max_seq_len}")
    console.print(f"Cache size: {preset.cache_size}")

    if preset.gpu_split:
        console.print(f"GPU split: {preset.gpu_split}")

    # Build request payload
    payload = {
        "model_name": preset.model_name,
        "max_seq_len": preset.max_seq_len,
        "cache_size": preset.cache_size,
    }

    if preset.gpu_split:
        payload["gpu_split"] = preset.gpu_split

    if preset.draft_model and preset.draft_ratio > 0:
        payload["draft"] = {
            "draft_model_name": preset.draft_model,
            "draft_rope_alpha": 1.0,
        }

    try:
        console.print("\n[yellow]Sending load request...[/yellow]")

        response = httpx.post(
            f"{TABBY_URL}/v1/model/load",
            json=payload,
            timeout=300,  # 5 minute timeout for large models
        )

        if response.status_code == 200:
            console.print("[green]✓ Model load initiated[/green]")

            # Wait for model to be ready
            console.print("[yellow]Waiting for model to load...[/yellow]")

            for _ in range(120):  # 2 minutes max wait
                time.sleep(1)
                model_info = get_current_model()

                if model_info and model_info.get("model_name") == preset.model_name:
                    console.print("[green]✓ Model loaded successfully![/green]")
                    return True

            console.print("[yellow]Model loading in progress (check status)[/yellow]")
            return True

        else:
            error = response.json() if response.content else {}
            console.print(f"[red]✗ Load failed: {response.status_code}[/red]")
            console.print(f"[red]{error}[/red]")
            return False

    except httpx.TimeoutException:
        console.print("[yellow]Request timed out - model may still be loading[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


def unload_model() -> bool:
    """Unload the current model."""
    console.print("[yellow]Unloading current model...[/yellow]")

    try:
        response = httpx.post(f"{TABBY_URL}/v1/model/unload", timeout=30)

        if response.status_code == 200:
            console.print("[green]✓ Model unloaded[/green]")
            return True
        else:
            console.print(f"[red]✗ Unload failed: {response.status_code}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


def show_status():
    """Show current model status."""
    console.print(Panel.fit("[bold blue]TabbyAPI Model Status[/bold blue]"))

    model = get_current_model()

    if model:
        table = Table(box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Model Name", model.get("model_name", "N/A"))
        table.add_row("Max Seq Length", str(model.get("max_seq_len", "N/A")))
        table.add_row("Cache Size", str(model.get("cache_size", "N/A")))

        if "loras" in model and model["loras"]:
            table.add_row("LoRAs", ", ".join(l.get("name", "") for l in model["loras"]))
        else:
            table.add_row("LoRAs", "None")

        console.print(table)
    else:
        console.print("[yellow]No model currently loaded[/yellow]")

    # Check TabbyAPI health
    try:
        response = httpx.get(f"{TABBY_URL}/health", timeout=5)
        if response.status_code == 200:
            console.print(f"\n[green]TabbyAPI is healthy at {TABBY_URL}[/green]")
        else:
            console.print(f"\n[red]TabbyAPI unhealthy: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"\n[red]Cannot reach TabbyAPI: {e}[/red]")


def list_presets():
    """List available presets and models."""
    presets = load_presets()

    # Presets table
    console.print(Panel.fit("[bold blue]Available Presets[/bold blue]"))

    table = Table(box=box.ROUNDED)
    table.add_column("Preset", style="cyan")
    table.add_column("Model")
    table.add_column("Context")
    table.add_column("Description")

    for name, preset in sorted(presets.items()):
        table.add_row(
            name,
            preset.model_name,
            str(preset.max_seq_len),
            preset.description or "-",
        )

    console.print(table)

    # Available models
    console.print(Panel.fit("[bold blue]Available Models[/bold blue]"))

    models = list_available_models()
    if models:
        for model in models:
            console.print(f"  • {model}")
    else:
        console.print("[yellow]No models found[/yellow]")


def cmd_load(args):
    """Handle load command."""
    model_name = args.model

    # Check if it's a preset
    presets = load_presets()
    if model_name in presets:
        preset = presets[model_name]
    else:
        # Treat as direct model name
        preset = ModelPreset(
            name="custom",
            model_name=model_name,
            max_seq_len=args.context or 8192,
            cache_size=args.context or 8192,
        )

    # Optionally unload first
    if args.unload_first:
        unload_model()
        time.sleep(2)

    load_model(preset)


def cmd_preset(args):
    """Handle preset command."""
    preset_name = args.preset
    presets = load_presets()

    if preset_name not in presets:
        console.print(f"[red]Unknown preset: {preset_name}[/red]")
        console.print(f"Available: {', '.join(presets.keys())}")
        return

    preset = presets[preset_name]

    # Unload current model first
    current = get_current_model()
    if current:
        unload_model()
        time.sleep(2)

    load_model(preset)


def main():
    parser = argparse.ArgumentParser(
        description="TabbyAPI Model Loader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # load command
    p_load = subparsers.add_parser("load", help="Load a model by name")
    p_load.add_argument("model", help="Model name or preset name")
    p_load.add_argument("--context", "-c", type=int, help="Context length")
    p_load.add_argument("--unload-first", "-u", action="store_true", help="Unload current model first")
    p_load.set_defaults(func=cmd_load)

    # preset command
    p_preset = subparsers.add_parser("preset", help="Load a preset configuration")
    p_preset.add_argument("preset", help="Preset name")
    p_preset.set_defaults(func=cmd_preset)

    # unload command
    p_unload = subparsers.add_parser("unload", help="Unload current model")
    p_unload.set_defaults(func=lambda _: unload_model())

    # status command
    p_status = subparsers.add_parser("status", help="Show current model status")
    p_status.set_defaults(func=lambda _: show_status())

    # list command
    p_list = subparsers.add_parser("list", help="List presets and available models")
    p_list.set_defaults(func=lambda _: list_presets())

    args = parser.parse_args()

    if not args.command:
        # Default to status
        show_status()
    elif hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
