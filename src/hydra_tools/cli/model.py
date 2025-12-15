"""
Model Management CLI

Command-line interface for managing LLM models on the Hydra cluster.
"""

import argparse
import sys
from typing import Optional

import requests
from rich.console import Console
from rich.table import Table

from ..config import get_config

console = Console()


def list_models(model_type: Optional[str] = None):
    """List installed models."""
    config = get_config()

    table = Table(title="Hydra Models")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Size", style="yellow")
    table.add_column("Status", style="magenta")

    # TabbyAPI current model
    if model_type in (None, "tabby", "exl2"):
        try:
            resp = requests.get(f"{config.tabbyapi_url}/v1/model", timeout=5)
            if resp.ok:
                data = resp.json()
                model_name = data.get("model_name", "none")
                table.add_row("TabbyAPI", model_name, "-", "✅ Loaded")
        except requests.RequestException:
            table.add_row("TabbyAPI", "-", "-", "❌ Unreachable")

    # Ollama models
    if model_type in (None, "ollama", "gguf"):
        try:
            resp = requests.get(f"{config.ollama_url}/api/tags", timeout=5)
            if resp.ok:
                data = resp.json()
                for model in data.get("models", []):
                    name = model.get("name", "unknown")
                    size_gb = round(model.get("size", 0) / 1024**3, 1)
                    table.add_row("Ollama", name, f"{size_gb}GB", "✅ Available")
        except requests.RequestException:
            table.add_row("Ollama", "-", "-", "❌ Unreachable")

    console.print(table)


def load_model(model_name: str):
    """Load a model in TabbyAPI."""
    config = get_config()

    console.print(f"[blue]Loading model: {model_name}[/blue]")

    try:
        # Unload current model first
        requests.post(f"{config.tabbyapi_url}/v1/model/unload", timeout=30)

        # Load new model
        resp = requests.post(
            f"{config.tabbyapi_url}/v1/model/load",
            json={"model_name": model_name},
            timeout=300,  # Models can take a while to load
        )

        if resp.ok:
            console.print(f"[green]✅ Model loaded: {model_name}[/green]")
        else:
            console.print(f"[red]❌ Failed to load model: {resp.text}[/red]")
            sys.exit(1)

    except requests.RequestException as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)


def unload_model():
    """Unload current model from TabbyAPI."""
    config = get_config()

    try:
        resp = requests.post(f"{config.tabbyapi_url}/v1/model/unload", timeout=30)
        if resp.ok:
            console.print("[green]✅ Model unloaded[/green]")
        else:
            console.print(f"[red]❌ Failed to unload: {resp.text}[/red]")
    except requests.RequestException as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)


def status():
    """Show current model status."""
    config = get_config()

    console.print("\n[bold]Model Status[/bold]\n")

    # TabbyAPI
    try:
        resp = requests.get(f"{config.tabbyapi_url}/v1/model", timeout=5)
        if resp.ok:
            data = resp.json()
            model = data.get("model_name", "none")
            context = data.get("max_seq_len", "?")
            console.print(f"[cyan]TabbyAPI:[/cyan] {model} (context: {context})")
        else:
            console.print("[cyan]TabbyAPI:[/cyan] [yellow]No model loaded[/yellow]")
    except requests.RequestException:
        console.print("[cyan]TabbyAPI:[/cyan] [red]Unreachable[/red]")

    # Ollama
    try:
        resp = requests.get(f"{config.ollama_url}/api/ps", timeout=5)
        if resp.ok:
            data = resp.json()
            models = data.get("models", [])
            if models:
                for m in models:
                    console.print(f"[cyan]Ollama:[/cyan] {m.get('name', 'unknown')} [green]running[/green]")
            else:
                console.print("[cyan]Ollama:[/cyan] [yellow]No models loaded[/yellow]")
    except requests.RequestException:
        console.print("[cyan]Ollama:[/cyan] [red]Unreachable[/red]")

    console.print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Hydra Model Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List models")
    list_parser.add_argument("--type", "-t", choices=["tabby", "ollama", "exl2", "gguf"])

    # Load command
    load_parser = subparsers.add_parser("load", help="Load a model")
    load_parser.add_argument("model", help="Model name to load")

    # Unload command
    subparsers.add_parser("unload", help="Unload current model")

    # Status command
    subparsers.add_parser("status", help="Show status")

    args = parser.parse_args()

    if args.command == "list":
        list_models(args.type)
    elif args.command == "load":
        load_model(args.model)
    elif args.command == "unload":
        unload_model()
    elif args.command == "status":
        status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
