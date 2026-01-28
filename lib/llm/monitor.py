"""LLM trace monitoring and analytics.

Provides analysis of trace files including JSON repair patterns,
provider performance, and usage statistics.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RepairStats:
    """Statistics for JSON repair operations."""

    total_requests: int = 0
    json_mode_requests: int = 0
    repairs_applied: int = 0
    repair_rate: float = 0.0
    methods: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_provider: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_role: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_model: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ProviderStats:
    """Statistics for provider performance."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class TraceAnalysis:
    """Complete analysis of trace files."""

    repair_stats: RepairStats
    provider_stats: dict[str, ProviderStats]
    date_range: tuple[str, str] | None = None
    total_traces: int = 0
    trace_directories: list[str] = field(default_factory=list)


def analyze_traces(workspace: Path | None = None, days: int = 7) -> TraceAnalysis:
    """Analyze trace files for repair patterns and provider performance.

    Args:
        workspace: Optional workspace path (defaults to current directory)
        days: Number of days to analyze (default: 7)

    Returns:
        TraceAnalysis with comprehensive statistics
    """
    # Determine trace directory
    if workspace:
        trace_base = Path(workspace) / ".agentleeops" / "traces"
    else:
        trace_base = Path(".agentleeops") / "traces"

    if not trace_base.exists():
        return TraceAnalysis(
            repair_stats=RepairStats(),
            provider_stats={},
            total_traces=0,
        )

    # Collect trace files
    trace_files = []
    trace_dirs = []

    for date_dir in sorted(trace_base.iterdir()):
        if date_dir.is_dir() and date_dir.name.isdigit():
            trace_dirs.append(date_dir.name)
            for trace_file in date_dir.glob("*.json"):
                trace_files.append(trace_file)

    # Initialize stats
    repair_stats = RepairStats()
    provider_stats_dict = defaultdict(
        lambda: ProviderStats()
    )

    # Track date range
    min_date = None
    max_date = None

    # Analyze each trace
    for trace_file in trace_files:
        try:
            with open(trace_file) as f:
                trace = json.load(f)

            # Track date range
            timestamp = trace.get("timestamp", "")
            if timestamp:
                if not min_date or timestamp < min_date:
                    min_date = timestamp
                if not max_date or timestamp > max_date:
                    max_date = timestamp

            # Extract basic info
            success = trace.get("success", True)
            provider = trace.get("provider", "unknown")
            role = trace.get("role", "unknown")
            model = trace.get("model", "unknown")

            # Update provider stats
            pstats = provider_stats_dict[provider]
            pstats.total_requests += 1

            if success:
                pstats.successful_requests += 1

                # Extract performance data
                response = trace.get("response", {})
                elapsed_ms = response.get("elapsed_ms", 0)
                pstats.avg_latency_ms = (
                    (pstats.avg_latency_ms * (pstats.successful_requests - 1) + elapsed_ms)
                    / pstats.successful_requests
                )

                # Extract usage data
                usage = response.get("usage", {})
                if usage:
                    total = usage.get("total_tokens", 0)
                    pstats.total_tokens += total

                    # Calculate cost if available
                    cost = usage.get("total_cost", 0)
                    pstats.total_cost += cost
            else:
                pstats.failed_requests += 1

            # Analyze repair stats
            request = trace.get("request", {})
            json_mode = request.get("json_mode", False)

            repair_stats.total_requests += 1

            if json_mode:
                repair_stats.json_mode_requests += 1

                # Check if repair was applied
                response = trace.get("response", {})
                repair_applied = response.get("json_repair_applied", False)
                repair_method = response.get("json_repair_method")

                if repair_applied and repair_method:
                    repair_stats.repairs_applied += 1
                    repair_stats.methods[repair_method] += 1

                    # Track by provider
                    if provider not in repair_stats.by_provider:
                        repair_stats.by_provider[provider] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_provider[provider]["total"] += 1
                    repair_stats.by_provider[provider]["repairs"] += 1
                    repair_stats.by_provider[provider]["methods"][repair_method] += 1

                    # Track by role
                    if role not in repair_stats.by_role:
                        repair_stats.by_role[role] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_role[role]["total"] += 1
                    repair_stats.by_role[role]["repairs"] += 1
                    repair_stats.by_role[role]["methods"][repair_method] += 1

                    # Track by model
                    if model not in repair_stats.by_model:
                        repair_stats.by_model[model] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_model[model]["total"] += 1
                    repair_stats.by_model[model]["repairs"] += 1
                    repair_stats.by_model[model]["methods"][repair_method] += 1
                else:
                    # Track non-repaired JSON mode requests
                    if provider not in repair_stats.by_provider:
                        repair_stats.by_provider[provider] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_provider[provider]["total"] += 1

                    if role not in repair_stats.by_role:
                        repair_stats.by_role[role] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_role[role]["total"] += 1

                    if model not in repair_stats.by_model:
                        repair_stats.by_model[model] = {
                            "total": 0,
                            "repairs": 0,
                            "methods": defaultdict(int),
                        }
                    repair_stats.by_model[model]["total"] += 1

        except (json.JSONDecodeError, IOError) as e:
            # Skip malformed or unreadable traces
            continue

    # Calculate derived stats
    if repair_stats.json_mode_requests > 0:
        repair_stats.repair_rate = (
            repair_stats.repairs_applied / repair_stats.json_mode_requests * 100
        )

    for pstats in provider_stats_dict.values():
        if pstats.total_requests > 0:
            pstats.success_rate = (
                pstats.successful_requests / pstats.total_requests * 100
            )

    # Build date range tuple
    date_range = None
    if min_date and max_date:
        date_range = (min_date, max_date)

    return TraceAnalysis(
        repair_stats=repair_stats,
        provider_stats=dict(provider_stats_dict),
        date_range=date_range,
        total_traces=len(trace_files),
        trace_directories=trace_dirs,
    )


def format_repair_report(analysis: TraceAnalysis) -> str:
    """Format repair analysis as a human-readable report.

    Args:
        analysis: TraceAnalysis object

    Returns:
        Formatted report string
    """
    lines = []
    stats = analysis.repair_stats

    lines.append("=" * 70)
    lines.append("JSON REPAIR MONITORING DASHBOARD")
    lines.append("=" * 70)
    lines.append("")

    # Date range
    if analysis.date_range:
        start, end = analysis.date_range
        lines.append(f"Date Range: {start[:10]} to {end[:10]}")
    lines.append(f"Total Traces: {analysis.total_traces}")
    lines.append("")

    # Overall stats
    lines.append("OVERALL STATISTICS")
    lines.append("-" * 70)
    lines.append(f"Total Requests:      {stats.total_requests:,}")
    lines.append(f"JSON Mode Requests:  {stats.json_mode_requests:,}")
    lines.append(f"Repairs Applied:     {stats.repairs_applied:,}")
    lines.append(f"Repair Rate:         {stats.repair_rate:.1f}%")
    lines.append("")

    # Repair methods
    if stats.methods:
        lines.append("REPAIR METHODS")
        lines.append("-" * 70)
        sorted_methods = sorted(
            stats.methods.items(), key=lambda x: x[1], reverse=True
        )
        for method, count in sorted_methods:
            pct = (count / stats.repairs_applied * 100) if stats.repairs_applied > 0 else 0
            lines.append(f"  {method:30s}  {count:4d}  ({pct:5.1f}%)")
        lines.append("")

    # By provider
    if stats.by_provider:
        lines.append("BY PROVIDER")
        lines.append("-" * 70)
        for provider, data in sorted(stats.by_provider.items()):
            total = data["total"]
            repairs = data["repairs"]
            rate = (repairs / total * 100) if total > 0 else 0
            lines.append(f"\n{provider}:")
            lines.append(f"  Total JSON requests: {total}")
            lines.append(f"  Repairs needed:      {repairs} ({rate:.1f}%)")
            if data["methods"]:
                lines.append("  Top methods:")
                sorted_methods = sorted(
                    data["methods"].items(), key=lambda x: x[1], reverse=True
                )[:3]
                for method, count in sorted_methods:
                    lines.append(f"    - {method}: {count}")
        lines.append("")

    # By role
    if stats.by_role:
        lines.append("BY ROLE")
        lines.append("-" * 70)
        for role, data in sorted(stats.by_role.items()):
            total = data["total"]
            repairs = data["repairs"]
            rate = (repairs / total * 100) if total > 0 else 0
            lines.append(f"\n{role}:")
            lines.append(f"  Total JSON requests: {total}")
            lines.append(f"  Repairs needed:      {repairs} ({rate:.1f}%)")
            if data["methods"]:
                lines.append("  Top methods:")
                sorted_methods = sorted(
                    data["methods"].items(), key=lambda x: x[1], reverse=True
                )[:3]
                for method, count in sorted_methods:
                    lines.append(f"    - {method}: {count}")
        lines.append("")

    # Recommendations
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 70)

    if stats.repair_rate > 50:
        lines.append("⚠️  HIGH REPAIR RATE DETECTED (>50%)")
        lines.append("    - Consider improving JSON mode prompts")
        lines.append("    - Add explicit JSON formatting instructions")
        lines.append("    - Use schema validation where possible")
    elif stats.repair_rate > 20:
        lines.append("⚠️  MODERATE REPAIR RATE (20-50%)")
        lines.append("    - Monitor repair patterns for optimization opportunities")
    elif stats.repairs_applied > 0:
        lines.append("✓ Low repair rate - JSON mode working well")
    else:
        lines.append("✓ No repairs needed - excellent JSON conformance")

    if "markdown_extraction" in stats.methods:
        count = stats.methods["markdown_extraction"]
        if count > stats.repairs_applied * 0.3:  # >30% of repairs
            lines.append("")
            lines.append("⚠️  MARKDOWN WRAPPING DETECTED")
            lines.append("    - Providers frequently wrapping JSON in markdown")
            lines.append("    - Add 'Return raw JSON without markdown' to prompts")

    if "trailing_commas" in stats.methods:
        count = stats.methods["trailing_commas"]
        if count > stats.repairs_applied * 0.2:  # >20% of repairs
            lines.append("")
            lines.append("⚠️  TRAILING COMMA ISSUES")
            lines.append("    - Consider using a provider with better JSON support")
            lines.append("    - Or add post-processing in the application layer")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_provider_report(analysis: TraceAnalysis) -> str:
    """Format provider performance analysis as a human-readable report.

    Args:
        analysis: TraceAnalysis object

    Returns:
        Formatted report string
    """
    lines = []

    lines.append("=" * 70)
    lines.append("PROVIDER PERFORMANCE DASHBOARD")
    lines.append("=" * 70)
    lines.append("")

    if not analysis.provider_stats:
        lines.append("No provider statistics available.")
        return "\n".join(lines)

    for provider, stats in sorted(analysis.provider_stats.items()):
        lines.append(f"{provider.upper()}")
        lines.append("-" * 70)
        lines.append(f"Total Requests:      {stats.total_requests:,}")
        lines.append(f"Successful:          {stats.successful_requests:,} ({stats.success_rate:.1f}%)")
        lines.append(f"Failed:              {stats.failed_requests:,}")
        lines.append(f"Avg Latency:         {stats.avg_latency_ms:.0f} ms")

        if stats.total_tokens > 0:
            lines.append(f"Total Tokens:        {stats.total_tokens:,}")

        if stats.total_cost > 0:
            lines.append(f"Total Cost:          ${stats.total_cost:.4f}")

        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)
