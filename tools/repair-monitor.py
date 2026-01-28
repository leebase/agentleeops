#!/usr/bin/env python3
"""JSON Repair Monitoring Dashboard CLI.

Analyzes LLM trace files to identify JSON repair patterns and provide
recommendations for improving JSON mode prompts.

Usage:
    python tools/repair-monitor.py                    # Analyze current workspace
    python tools/repair-monitor.py --workspace ~/projects/myapp
    python tools/repair-monitor.py --providers        # Show provider stats
    python tools/repair-monitor.py --all              # Show all reports
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.llm.monitor import (
    analyze_traces,
    format_repair_report,
    format_provider_report,
)


def main():
    parser = argparse.ArgumentParser(
        description="JSON Repair Monitoring Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        help="Workspace directory (default: current directory)",
    )

    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)",
    )

    parser.add_argument(
        "--providers",
        "-p",
        action="store_true",
        help="Show provider performance report",
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Show all reports (repair + provider)",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output raw JSON statistics",
    )

    args = parser.parse_args()

    # Analyze traces
    print("Analyzing traces...", file=sys.stderr)
    analysis = analyze_traces(workspace=args.workspace, days=args.days)

    if analysis.total_traces == 0:
        print("\nNo trace files found.", file=sys.stderr)
        if args.workspace:
            trace_dir = args.workspace / ".agentleeops" / "traces"
        else:
            trace_dir = Path(".agentleeops") / "traces"
        print(f"Expected location: {trace_dir}", file=sys.stderr)
        sys.exit(1)

    # JSON output mode
    if args.json:
        import json
        from dataclasses import asdict

        output = {
            "repair_stats": asdict(analysis.repair_stats),
            "provider_stats": {
                k: asdict(v) for k, v in analysis.provider_stats.items()
            },
            "date_range": analysis.date_range,
            "total_traces": analysis.total_traces,
            "trace_directories": analysis.trace_directories,
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    if args.all:
        # Show both reports
        print(format_repair_report(analysis))
        print()
        print(format_provider_report(analysis))
    elif args.providers:
        # Show only provider report
        print(format_provider_report(analysis))
    else:
        # Show only repair report (default)
        print(format_repair_report(analysis))


if __name__ == "__main__":
    main()
