#!/usr/bin/env python3
"""
Profile Report Tool - Analyze agent execution profiles.

Usage:
    python tools/profile-report.py profile.json
    python tools/profile-report.py --workspace ~/projects/myapp
    python tools/profile-report.py --all
    python tools/profile-report.py --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_profile(filepath: Path) -> dict[str, Any]:
    """Load profile data from file.

    Args:
        filepath: Path to profile file

    Returns:
        Profile data dictionary
    """
    with open(filepath) as f:
        return json.load(f)


def find_profile_files(workspace: Path | None = None) -> list[Path]:
    """Find all profile files.

    Args:
        workspace: Workspace path to search in, or None for current directory

    Returns:
        List of profile file paths
    """
    if workspace:
        profiles_dir = workspace / ".agentleeops" / "profiles"
    else:
        # Search in current directory and .agentleeops/profiles
        profiles_dir = Path(".agentleeops/profiles")

    if not profiles_dir.exists():
        return []

    return sorted(profiles_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)


def format_duration(ms: int) -> str:
    """Format duration in human-readable format.

    Args:
        ms: Duration in milliseconds

    Returns:
        Formatted duration string
    """
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms / 1000:.2f}s"
    else:
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


def print_profile_tree(entries: list[dict], indent: int = 0, max_depth: int = 10):
    """Print profile entries as a tree.

    Args:
        entries: List of profile entries
        indent: Current indentation level
        max_depth: Maximum depth to display
    """
    if indent >= max_depth:
        return

    for entry in entries:
        name = entry["name"]
        duration = entry.get("duration_ms", 0)
        metadata = entry.get("metadata", {})

        # Format metadata for display
        meta_str = ""
        if metadata:
            # Only show important metadata
            important = {}
            for key in ["role", "provider", "model", "file", "command"]:
                if key in metadata:
                    important[key] = metadata[key]
            if important:
                meta_str = " " + " ".join(
                    f"{k}={v}" for k, v in important.items()
                )

        # Print entry
        prefix = "  " * indent
        print(f"{prefix}├─ {name}: {format_duration(duration)}{meta_str}")

        # Print children
        children = entry.get("children", [])
        if children:
            print_profile_tree(children, indent + 1, max_depth)


def print_operation_stats(profile: dict[str, Any]):
    """Print operation statistics.

    Args:
        profile: Profile data dictionary
    """
    stats = profile.get("statistics", {})
    operations = stats.get("operations", {})

    if not operations:
        print("No operations recorded.")
        return

    print("\nOperation Statistics:")
    print("=" * 80)
    print(
        f"{'Operation':<40} {'Count':>8} {'Total':>12} {'Avg':>12} {'Min':>12} {'Max':>12}"
    )
    print("-" * 80)

    # Sort by total time descending
    sorted_ops = sorted(
        operations.items(), key=lambda x: x[1]["total_ms"], reverse=True
    )

    for op_name, op_stats in sorted_ops:
        count = op_stats["count"]
        total = format_duration(op_stats["total_ms"])
        avg = format_duration(op_stats["avg_ms"])
        min_ms = format_duration(op_stats["min_ms"])
        max_ms = format_duration(op_stats["max_ms"])

        # Truncate long operation names
        display_name = (
            op_name if len(op_name) <= 40 else op_name[:37] + "..."
        )

        print(
            f"{display_name:<40} {count:>8} {total:>12} {avg:>12} {min_ms:>12} {max_ms:>12}"
        )


def print_slowest_operations(profile: dict[str, Any], limit: int = 10):
    """Print slowest individual operations.

    Args:
        profile: Profile data dictionary
        limit: Number of operations to show
    """
    # Flatten all entries
    all_entries = []

    def collect_entries(entries):
        for entry in entries:
            all_entries.append(entry)
            if entry.get("children"):
                collect_entries(entry["children"])

    collect_entries(profile.get("entries", []))

    if not all_entries:
        return

    # Sort by duration descending
    sorted_entries = sorted(
        all_entries, key=lambda e: e.get("duration_ms", 0), reverse=True
    )

    print(f"\nTop {limit} Slowest Operations:")
    print("=" * 80)
    print(f"{'Operation':<50} {'Duration':>12} {'Metadata':<20}")
    print("-" * 80)

    for entry in sorted_entries[:limit]:
        name = entry["name"]
        duration = format_duration(entry.get("duration_ms", 0))
        metadata = entry.get("metadata", {})

        # Format key metadata
        meta_str = ""
        if "role" in metadata:
            meta_str = f"role={metadata['role']}"
        elif "file" in metadata:
            meta_str = f"file={Path(metadata['file']).name}"
        elif "command" in metadata:
            cmd = metadata['command']
            meta_str = cmd if len(cmd) <= 20 else cmd[:17] + "..."

        # Truncate long names
        display_name = name if len(name) <= 50 else name[:47] + "..."

        print(f"{display_name:<50} {duration:>12} {meta_str:<20}")


def print_summary(profile: dict[str, Any]):
    """Print profile summary.

    Args:
        profile: Profile data dictionary
    """
    stats = profile.get("statistics", {})
    total_duration = profile.get("total_duration_ms", 0)
    total_entries = stats.get("total_entries", 0)

    print("\nProfile Summary:")
    print("=" * 80)
    print(f"Timestamp: {profile.get('timestamp', 'N/A')}")
    print(f"Total Duration: {format_duration(total_duration)}")
    print(f"Total Operations: {total_entries}")
    print(f"Unique Operation Types: {len(stats.get('operations', {}))}")


def print_profile_report(profile: dict[str, Any], show_tree: bool = True):
    """Print full profile report.

    Args:
        profile: Profile data dictionary
        show_tree: Whether to show execution tree
    """
    # Summary
    print_summary(profile)

    # Operation statistics
    print_operation_stats(profile)

    # Slowest operations
    print_slowest_operations(profile, limit=10)

    # Execution tree
    if show_tree and profile.get("entries"):
        print("\nExecution Tree:")
        print("=" * 80)
        print_profile_tree(profile["entries"], max_depth=5)


def aggregate_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate multiple profiles.

    Args:
        profiles: List of profile dictionaries

    Returns:
        Aggregated profile data
    """
    total_duration = 0
    total_entries = 0
    operations = {}

    for profile in profiles:
        total_duration += profile.get("total_duration_ms", 0)
        stats = profile.get("statistics", {})
        total_entries += stats.get("total_entries", 0)

        # Merge operations
        for op_name, op_stats in stats.get("operations", {}).items():
            if op_name not in operations:
                operations[op_name] = {
                    "count": 0,
                    "total_ms": 0,
                    "min_ms": float("inf"),
                    "max_ms": 0,
                }

            agg_stats = operations[op_name]
            agg_stats["count"] += op_stats["count"]
            agg_stats["total_ms"] += op_stats["total_ms"]
            agg_stats["min_ms"] = min(agg_stats["min_ms"], op_stats["min_ms"])
            agg_stats["max_ms"] = max(agg_stats["max_ms"], op_stats["max_ms"])

    # Calculate averages
    for stats in operations.values():
        if stats["count"] > 0:
            stats["avg_ms"] = stats["total_ms"] // stats["count"]

    return {
        "aggregated": True,
        "profile_count": len(profiles),
        "total_duration_ms": total_duration,
        "statistics": {
            "total_entries": total_entries,
            "operations": operations,
        },
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze agent execution profiles"
    )
    parser.add_argument(
        "profile",
        nargs="?",
        help="Path to profile file",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Workspace path to analyze profiles from",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Aggregate all profiles in workspace",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Show only latest profile",
    )
    parser.add_argument(
        "--no-tree",
        action="store_true",
        help="Don't show execution tree",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    # Determine which profiles to analyze
    if args.profile:
        # Single profile specified
        profile_files = [Path(args.profile)]
    elif args.workspace or args.all or args.latest:
        # Find profiles in workspace
        profile_files = find_profile_files(args.workspace)
        if not profile_files:
            print("No profile files found.")
            sys.exit(1)

        if args.latest:
            profile_files = [profile_files[-1]]
    else:
        parser.print_help()
        sys.exit(1)

    # Load profiles
    profiles = []
    for filepath in profile_files:
        try:
            profile = load_profile(filepath)
            profiles.append(profile)
        except Exception as e:
            print(f"Error loading {filepath}: {e}", file=sys.stderr)
            continue

    if not profiles:
        print("No profiles loaded.")
        sys.exit(1)

    # Aggregate if requested
    if args.all and len(profiles) > 1:
        profile = aggregate_profiles(profiles)
        print(f"Aggregated {len(profiles)} profiles\n")
    else:
        profile = profiles[0]
        if len(profile_files) == 1:
            print(f"Profile: {profile_files[0]}\n")

    # Output
    if args.json:
        print(json.dumps(profile, indent=2))
    else:
        print_profile_report(profile, show_tree=not args.no_tree)


if __name__ == "__main__":
    main()
