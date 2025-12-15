#!/usr/bin/env python3
"""
n8n Workflow Activation Script

Imports and activates workflows in n8n for the Hydra cluster.

Prerequisites:
    1. n8n running at http://192.168.1.244:5678
    2. API key generated (Settings -> API Settings)

Usage:
    export N8N_API_KEY="your-api-key"
    python activate-n8n-workflows.py [--import-only | --activate-only | --list]

The script will:
    1. Import workflow JSON files from config/n8n/workflows/
    2. Activate imported workflows
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

# Configuration
N8N_URL = os.getenv("N8N_URL", "http://192.168.1.244:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Workflow files to import
WORKFLOW_DIR = Path(__file__).parent.parent / "config" / "n8n" / "workflows"


def get_headers() -> dict[str, str]:
    """Get API headers."""
    if not N8N_API_KEY:
        print("Error: N8N_API_KEY environment variable required")
        print("Generate an API key in n8n: Settings -> API Settings")
        sys.exit(1)

    return {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json",
    }


def list_workflows() -> list[dict[str, Any]]:
    """List all workflows in n8n."""
    try:
        response = httpx.get(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except httpx.HTTPError as e:
        print(f"Error listing workflows: {e}")
        return []


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    """Get a specific workflow."""
    try:
        response = httpx.get(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"Error getting workflow {workflow_id}: {e}")
        return None


def import_workflow(workflow_data: dict[str, Any]) -> str | None:
    """Import a workflow into n8n."""
    try:
        # Remove fields that shouldn't be in import
        import_data = workflow_data.copy()
        import_data.pop("id", None)
        import_data.pop("versionId", None)
        import_data.pop("createdAt", None)
        import_data.pop("updatedAt", None)

        response = httpx.post(
            f"{N8N_URL}/api/v1/workflows",
            headers=get_headers(),
            json=import_data,
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("id")
    except httpx.HTTPStatusError as e:
        # Check if workflow already exists (by name)
        if e.response.status_code == 400:
            existing = find_workflow_by_name(workflow_data.get("name", ""))
            if existing:
                print(f"  Workflow already exists: {workflow_data.get('name')} (ID: {existing})")
                return existing
        print(f"Error importing workflow: {e}")
        return None
    except httpx.HTTPError as e:
        print(f"Error importing workflow: {e}")
        return None


def find_workflow_by_name(name: str) -> str | None:
    """Find a workflow by name and return its ID."""
    workflows = list_workflows()
    for wf in workflows:
        if wf.get("name", "").lower() == name.lower():
            return wf.get("id")
    return None


def activate_workflow(workflow_id: str) -> bool:
    """Activate a workflow."""
    try:
        response = httpx.patch(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_headers(),
            json={"active": True},
            timeout=30.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as e:
        print(f"Error activating workflow {workflow_id}: {e}")
        return False


def deactivate_workflow(workflow_id: str) -> bool:
    """Deactivate a workflow."""
    try:
        response = httpx.patch(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers=get_headers(),
            json={"active": False},
            timeout=30.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as e:
        print(f"Error deactivating workflow {workflow_id}: {e}")
        return False


def import_workflows_from_files() -> list[tuple[str, str]]:
    """Import all workflow JSON files and return list of (name, id) tuples."""
    if not WORKFLOW_DIR.exists():
        print(f"Workflow directory not found: {WORKFLOW_DIR}")
        return []

    imported = []
    workflow_files = list(WORKFLOW_DIR.glob("*.json"))

    if not workflow_files:
        print(f"No workflow files found in {WORKFLOW_DIR}")
        return []

    print(f"Found {len(workflow_files)} workflow files\n")

    for wf_file in workflow_files:
        print(f"Importing: {wf_file.name}")
        try:
            workflow_data = json.loads(wf_file.read_text())
            name = workflow_data.get("name", wf_file.stem)

            workflow_id = import_workflow(workflow_data)
            if workflow_id:
                imported.append((name, workflow_id))
                print(f"  Success: {name} (ID: {workflow_id})")
            else:
                print(f"  Failed: {name}")
        except json.JSONDecodeError as e:
            print(f"  Invalid JSON: {e}")
        except Exception as e:
            print(f"  Error: {e}")

    return imported


def activate_all_workflows(workflow_ids: list[str] | None = None):
    """Activate all workflows or specific ones."""
    if workflow_ids is None:
        workflows = list_workflows()
        workflow_ids = [wf["id"] for wf in workflows]

    print(f"\nActivating {len(workflow_ids)} workflows...")

    for wf_id in workflow_ids:
        wf = get_workflow(wf_id)
        name = wf.get("name", wf_id) if wf else wf_id

        if activate_workflow(wf_id):
            print(f"  Activated: {name}")
        else:
            print(f"  Failed to activate: {name}")


def display_workflows():
    """Display all workflows with their status."""
    workflows = list_workflows()

    if not workflows:
        print("No workflows found")
        return

    print(f"\n{'Name':<40} {'ID':<10} {'Active':<10}")
    print("-" * 60)

    active_count = 0
    for wf in workflows:
        name = wf.get("name", "Unknown")[:38]
        wf_id = wf.get("id", "N/A")
        active = "Yes" if wf.get("active") else "No"
        if wf.get("active"):
            active_count += 1
        print(f"{name:<40} {wf_id:<10} {active:<10}")

    print("-" * 60)
    print(f"Total: {len(workflows)} workflows ({active_count} active)")


def main():
    parser = argparse.ArgumentParser(description="n8n Workflow Manager")
    parser.add_argument("--list", action="store_true", help="List all workflows")
    parser.add_argument("--import-only", action="store_true", help="Import without activating")
    parser.add_argument("--activate-only", action="store_true", help="Activate existing workflows")
    parser.add_argument("--deactivate-all", action="store_true", help="Deactivate all workflows")
    parser.add_argument("--workflow-dir", type=str, help="Custom workflow directory")

    args = parser.parse_args()

    global WORKFLOW_DIR
    if args.workflow_dir:
        WORKFLOW_DIR = Path(args.workflow_dir)

    print(f"n8n URL: {N8N_URL}")
    print(f"Workflow directory: {WORKFLOW_DIR}")

    if args.list:
        display_workflows()
        return

    if args.deactivate_all:
        workflows = list_workflows()
        print(f"\nDeactivating {len(workflows)} workflows...")
        for wf in workflows:
            if deactivate_workflow(wf["id"]):
                print(f"  Deactivated: {wf.get('name')}")
        return

    if args.activate_only:
        activate_all_workflows()
        display_workflows()
        return

    # Default: import and activate
    print("\nImporting workflows...")
    imported = import_workflows_from_files()

    if not args.import_only and imported:
        workflow_ids = [wf_id for _, wf_id in imported]
        activate_all_workflows(workflow_ids)

    print("\n" + "=" * 60)
    display_workflows()


if __name__ == "__main__":
    main()
