"""Tests for LLM trace monitoring and analytics."""

import json
import tempfile
from pathlib import Path

import pytest

from lib.llm.monitor import (
    analyze_traces,
    format_repair_report,
    format_provider_report,
)


def create_test_trace(
    trace_dir: Path,
    request_id: str,
    provider: str = "opencode_cli",
    role: str = "test",
    model: str = "gpt-4o",
    json_mode: bool = False,
    repair_applied: bool = False,
    repair_method: str | None = None,
    success: bool = True,
    elapsed_ms: int = 100,
    usage: dict | None = None,
) -> Path:
    """Create a test trace file."""
    trace_data = {
        "request_id": request_id,
        "timestamp": "2026-01-27T12:00:00",
        "role": role,
        "provider": provider,
        "model": model,
        "config_hash": "testhash",
        "request": {
            "messages": [{"role": "user", "content": "test"}],
            "json_mode": json_mode,
            "schema": None,
            "max_tokens": 1000,
            "temperature": 0.2,
            "timeout_s": 120,
        },
        "response": {
            "text": "test response",
            "usage": usage or {},
            "elapsed_ms": elapsed_ms,
            "json_repair_applied": repair_applied,
            "json_repair_method": repair_method,
            "raw": {},
        },
        "success": success,
        "metadata": {},
    }

    trace_file = trace_dir / f"{request_id}.json"
    with open(trace_file, "w") as f:
        json.dump(trace_data, f)

    return trace_file


class TestAnalyzeTraces:
    """Test trace analysis functionality."""

    def test_empty_directory(self):
        """Should handle empty trace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis = analyze_traces(workspace=Path(tmpdir))

            assert analysis.total_traces == 0
            assert analysis.repair_stats.total_requests == 0

    def test_basic_analysis(self):
        """Should analyze traces without repairs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Create test traces
            create_test_trace(trace_dir, "req-1", json_mode=False)
            create_test_trace(trace_dir, "req-2", json_mode=True, repair_applied=False)

            analysis = analyze_traces(workspace=workspace)

            assert analysis.total_traces == 2
            assert analysis.repair_stats.total_requests == 2
            assert analysis.repair_stats.json_mode_requests == 1
            assert analysis.repair_stats.repairs_applied == 0
            assert analysis.repair_stats.repair_rate == 0.0

    def test_repair_statistics(self):
        """Should track repair statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Create traces with repairs
            create_test_trace(
                trace_dir,
                "req-1",
                json_mode=True,
                repair_applied=True,
                repair_method="trailing_commas",
            )
            create_test_trace(
                trace_dir,
                "req-2",
                json_mode=True,
                repair_applied=True,
                repair_method="markdown_extraction",
            )
            create_test_trace(
                trace_dir,
                "req-3",
                json_mode=True,
                repair_applied=True,
                repair_method="trailing_commas",
            )
            create_test_trace(trace_dir, "req-4", json_mode=True, repair_applied=False)

            analysis = analyze_traces(workspace=workspace)

            assert analysis.total_traces == 4
            assert analysis.repair_stats.json_mode_requests == 4
            assert analysis.repair_stats.repairs_applied == 3
            assert analysis.repair_stats.repair_rate == 75.0  # 3/4

            # Check method counts
            assert analysis.repair_stats.methods["trailing_commas"] == 2
            assert analysis.repair_stats.methods["markdown_extraction"] == 1

    def test_by_provider_statistics(self):
        """Should track repairs by provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Provider A: 2 repairs out of 3
            create_test_trace(
                trace_dir,
                "req-1",
                provider="provider_a",
                json_mode=True,
                repair_applied=True,
                repair_method="trailing_commas",
            )
            create_test_trace(
                trace_dir,
                "req-2",
                provider="provider_a",
                json_mode=True,
                repair_applied=True,
                repair_method="trailing_commas",
            )
            create_test_trace(
                trace_dir, "req-3", provider="provider_a", json_mode=True, repair_applied=False
            )

            # Provider B: 0 repairs out of 2
            create_test_trace(
                trace_dir, "req-4", provider="provider_b", json_mode=True, repair_applied=False
            )
            create_test_trace(
                trace_dir, "req-5", provider="provider_b", json_mode=True, repair_applied=False
            )

            analysis = analyze_traces(workspace=workspace)

            # Check provider A
            assert "provider_a" in analysis.repair_stats.by_provider
            provider_a = analysis.repair_stats.by_provider["provider_a"]
            assert provider_a["total"] == 3
            assert provider_a["repairs"] == 2

            # Check provider B
            assert "provider_b" in analysis.repair_stats.by_provider
            provider_b = analysis.repair_stats.by_provider["provider_b"]
            assert provider_b["total"] == 2
            assert provider_b["repairs"] == 0

    def test_by_role_statistics(self):
        """Should track repairs by role."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Planner role: high repair rate
            create_test_trace(
                trace_dir,
                "req-1",
                role="planner",
                json_mode=True,
                repair_applied=True,
                repair_method="markdown_extraction",
            )
            create_test_trace(
                trace_dir,
                "req-2",
                role="planner",
                json_mode=True,
                repair_applied=True,
                repair_method="markdown_extraction",
            )

            # Coder role: low repair rate
            create_test_trace(
                trace_dir, "req-3", role="coder", json_mode=True, repair_applied=False
            )

            analysis = analyze_traces(workspace=workspace)

            assert "planner" in analysis.repair_stats.by_role
            assert analysis.repair_stats.by_role["planner"]["repairs"] == 2

            assert "coder" in analysis.repair_stats.by_role
            assert analysis.repair_stats.by_role["coder"]["repairs"] == 0

    def test_provider_performance_stats(self):
        """Should track provider performance metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Successful requests
            create_test_trace(
                trace_dir,
                "req-1",
                provider="test_provider",
                success=True,
                elapsed_ms=100,
                usage={"total_tokens": 50, "total_cost": 0.001},
            )
            create_test_trace(
                trace_dir,
                "req-2",
                provider="test_provider",
                success=True,
                elapsed_ms=200,
                usage={"total_tokens": 75, "total_cost": 0.0015},
            )

            # Failed request
            create_test_trace(
                trace_dir, "req-3", provider="test_provider", success=False, elapsed_ms=50
            )

            analysis = analyze_traces(workspace=workspace)

            assert "test_provider" in analysis.provider_stats
            pstats = analysis.provider_stats["test_provider"]

            assert pstats.total_requests == 3
            assert pstats.successful_requests == 2
            assert pstats.failed_requests == 1
            assert pstats.success_rate == pytest.approx(66.67, rel=0.01)
            assert pstats.avg_latency_ms == 150.0  # (100 + 200) / 2
            assert pstats.total_tokens == 125  # 50 + 75
            assert pstats.total_cost == pytest.approx(0.0025)


class TestFormatReports:
    """Test report formatting."""

    def test_format_repair_report(self):
        """Should format repair report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            create_test_trace(
                trace_dir,
                "req-1",
                json_mode=True,
                repair_applied=True,
                repair_method="trailing_commas",
            )

            analysis = analyze_traces(workspace=workspace)
            report = format_repair_report(analysis)

            assert "JSON REPAIR MONITORING DASHBOARD" in report
            assert "Total Traces: 1" in report
            assert "Repair Rate:" in report
            assert "trailing_commas" in report

    def test_format_provider_report(self):
        """Should format provider report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            create_test_trace(trace_dir, "req-1", provider="test_provider", elapsed_ms=100)

            analysis = analyze_traces(workspace=workspace)
            report = format_provider_report(analysis)

            assert "PROVIDER PERFORMANCE DASHBOARD" in report
            assert "TEST_PROVIDER" in report  # Provider names are uppercased in report
            assert "Total Requests:" in report
            assert "Avg Latency:" in report

    def test_high_repair_rate_warning(self):
        """Should show warning for high repair rates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            trace_dir = workspace / ".agentleeops" / "traces" / "20260127"
            trace_dir.mkdir(parents=True)

            # Create 6 repairs out of 10 (60% rate)
            for i in range(6):
                create_test_trace(
                    trace_dir,
                    f"req-repair-{i}",
                    json_mode=True,
                    repair_applied=True,
                    repair_method="trailing_commas",
                )
            for i in range(4):
                create_test_trace(
                    trace_dir, f"req-ok-{i}", json_mode=True, repair_applied=False
                )

            analysis = analyze_traces(workspace=workspace)
            report = format_repair_report(analysis)

            assert "HIGH REPAIR RATE DETECTED" in report
            assert "improving JSON mode prompts" in report
