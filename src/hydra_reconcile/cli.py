#!/usr/bin/env python3
"""CLI for cluster state reconciliation."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from hydra_reconcile.reconciler import ClusterReconciler
from hydra_reconcile.state import DesiredState


def print_state(state: dict, format_type: str = "text") -> None:
    """Print cluster state."""
    if format_type == "json":
        print(json.dumps(state, indent=2))
        return

    print("\n=== Cluster State ===")
    print(f"Timestamp: {state['timestamp']}")
    print()

    for node in state["nodes"]:
        status_icon = {"online": "🟢", "offline": "🔴", "degraded": "🟡"}.get(
            node["status"], "⚪"
        )
        print(f"{status_icon} {node['name']} ({node['ip']}) - {node['status'].upper()}")

        if node["gpu_count"] > 0:
            temps = ", ".join(f"{t}°C" for t in node["gpu_temps"])
            print(f"   GPUs: {node['gpu_count']} ({temps})")

        if node["memory_total_gb"] > 0:
            print(
                f"   Memory: {node['memory_used_gb']:.1f}GB / {node['memory_total_gb']:.1f}GB"
            )

        print(f"   Services:")
        for svc in node["services"]:
            svc_icon = {
                "running": "✓",
                "stopped": "✗",
                "unhealthy": "!",
                "unknown": "?",
            }.get(svc["status"], "?")
            port_str = f" :{svc['port']}" if svc.get("port") else ""
            print(f"      {svc_icon} {svc['name']}{port_str}")
        print()


def print_plan(plan: dict, format_type: str = "text") -> None:
    """Print reconciliation plan."""
    if format_type == "json":
        print(json.dumps(plan, indent=2))
        return

    print("\n=== Reconciliation Plan ===")
    print(f"Drifts found: {plan['drift_count']}")
    print(f"Critical: {plan['critical_count']}")
    print(f"Auto-fixable: {plan['auto_fixable_count']}")
    print()

    if not plan["drifts"]:
        print("✓ No drift detected - cluster is in desired state")
        return

    print("Drifts:")
    for drift in plan["drifts"]:
        severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
            drift["severity"], "⚪"
        )
        fix_icon = "🔧" if drift["auto_fixable"] else ""
        print(
            f"  {severity_icon} {drift['service']} on {drift['node']}: "
            f"{drift['drift_type']} (expected: {drift['expected']}, "
            f"actual: {drift['actual']}) {fix_icon}"
        )

    if plan["actions"]:
        print("\nPlanned Actions:")
        for action in plan["actions"]:
            print(f"  → {action['type'].upper()} {action['target']} on {action['node']}")


def print_results(results: dict, format_type: str = "text") -> None:
    """Print reconciliation results."""
    if format_type == "json":
        print(json.dumps(results, indent=2))
        return

    print("\n=== Reconciliation Results ===")
    print(f"Dry run: {results['dry_run']}")
    print()

    if results["results"]["applied"]:
        print("Applied:")
        for action in results["results"]["applied"]:
            print(f"  ✓ {action['type']} {action['target']} on {action['node']}")

    if results["results"]["failed"]:
        print("Failed:")
        for item in results["results"]["failed"]:
            print(
                f"  ✗ {item['action']['type']} {item['action']['target']} "
                f"on {item['action']['node']}: {item['reason']}"
            )

    if results["results"]["skipped"]:
        print(f"Skipped: {len(results['results']['skipped'])} actions (dry run)")


async def cmd_state(args: argparse.Namespace) -> int:
    """Get current cluster state."""
    async with ClusterReconciler() as reconciler:
        state = await reconciler.get_current_state()
        print_state(state.to_dict(), args.format)
    return 0


async def cmd_diff(args: argparse.Namespace) -> int:
    """Show drift between desired and actual state."""
    if not Path(args.desired).exists():
        print(f"Error: Desired state file not found: {args.desired}", file=sys.stderr)
        return 1

    desired = DesiredState.from_yaml(args.desired)

    async with ClusterReconciler(desired_state=desired) as reconciler:
        current = await reconciler.get_current_state()
        plan = reconciler.compare_states(desired, current)
        print_plan(plan.to_dict(), args.format)

    return 1 if plan.has_critical_drifts else 0


async def cmd_reconcile(args: argparse.Namespace) -> int:
    """Reconcile cluster state."""
    if not Path(args.desired).exists():
        print(f"Error: Desired state file not found: {args.desired}", file=sys.stderr)
        return 1

    desired = DesiredState.from_yaml(args.desired)

    async with ClusterReconciler(desired_state=desired) as reconciler:
        results = await reconciler.reconcile(dry_run=not args.apply)
        print_plan(results["plan"], args.format)
        print_results(results, args.format)

    return 1 if results["results"]["failed"] else 0


async def cmd_watch(args: argparse.Namespace) -> int:
    """Watch cluster state continuously."""
    import time

    desired = None
    if args.desired and Path(args.desired).exists():
        desired = DesiredState.from_yaml(args.desired)

    try:
        while True:
            print("\033[2J\033[H")  # Clear screen

            async with ClusterReconciler(desired_state=desired) as reconciler:
                state = await reconciler.get_current_state()
                print_state(state.to_dict(), "text")

                if desired:
                    plan = reconciler.compare_states(desired, state)
                    if plan.drifts:
                        print_plan(plan.to_dict(), "text")

            print(f"\n(Refreshing every {args.interval}s, Ctrl+C to exit)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hydra cluster state reconciliation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hydra-reconcile state                     # Show current cluster state
  hydra-reconcile diff -d desired.yaml      # Show drift from desired state
  hydra-reconcile reconcile -d desired.yaml # Plan reconciliation (dry run)
  hydra-reconcile reconcile -d desired.yaml --apply  # Apply reconciliation
  hydra-reconcile watch -d desired.yaml     # Continuous monitoring
        """,
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # state command
    state_parser = subparsers.add_parser("state", help="Get current cluster state")
    state_parser.set_defaults(func=cmd_state)

    # diff command
    diff_parser = subparsers.add_parser(
        "diff", help="Show drift from desired state"
    )
    diff_parser.add_argument(
        "-d",
        "--desired",
        required=True,
        help="Path to desired state YAML file",
    )
    diff_parser.set_defaults(func=cmd_diff)

    # reconcile command
    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Reconcile cluster state"
    )
    reconcile_parser.add_argument(
        "-d",
        "--desired",
        required=True,
        help="Path to desired state YAML file",
    )
    reconcile_parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (default is dry-run)",
    )
    reconcile_parser.set_defaults(func=cmd_reconcile)

    # watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Watch cluster state continuously"
    )
    watch_parser.add_argument(
        "-d",
        "--desired",
        help="Path to desired state YAML file (optional)",
    )
    watch_parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)",
    )
    watch_parser.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
