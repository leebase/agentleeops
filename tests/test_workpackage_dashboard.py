"""Tests for work package dashboard generation."""

from pathlib import Path
import json

from lib.workpackage import (
    initialize_work_package,
    refresh_artifact_registry,
    refresh_dashboard,
    transition_stage,
)


def _init_package(tmp_path: Path) -> Path:
    return initialize_work_package(
        base_dir=tmp_path,
        work_package_id="task-456",
        title="Dashboard Test",
        dirname="dashboard-test",
        context_mode="NEW",
        acceptance_criteria=["dashboard works"],
    )


def _write_design(work_package_dir: Path, content: str) -> Path:
    design_file = work_package_dir / "artifacts" / "design" / "DESIGN.md"
    design_file.write_text(content, encoding="utf-8")
    return design_file


def test_refresh_dashboard_writes_json_and_html(tmp_path: Path):
    """Manual dashboard refresh should write both canonical files."""
    work_package_dir = _init_package(tmp_path)
    _write_design(work_package_dir, "# Design\n")
    refresh_artifact_registry(work_package_dir)

    data_path, html_path = refresh_dashboard(work_package_dir)
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert data_path.exists()
    assert html_path.exists()
    assert payload["work_package"]["id"] == "task-456"
    assert payload["artifacts"][0]["path"] == "artifacts/design/DESIGN.md"
    assert "Stage Status" in html_path.read_text(encoding="utf-8")


def test_transition_auto_refreshes_dashboard(tmp_path: Path):
    """Lifecycle transitions should regenerate dashboard output automatically."""
    work_package_dir = _init_package(tmp_path)
    _write_design(work_package_dir, "# Design v1\n")

    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    dashboard_data = json.loads(
        (work_package_dir / "dashboard" / "dashboard.json").read_text(encoding="utf-8")
    )
    artifact = next(
        row for row in dashboard_data["artifacts"] if row["path"] == "artifacts/design/DESIGN.md"
    )

    assert dashboard_data["work_package"]["current_stage"] == "design_approved"
    assert len(dashboard_data["approval_events"]) >= 2
    assert artifact["state"] == "approved"


def test_refresh_artifacts_updates_dashboard_freshness(tmp_path: Path):
    """Artifact refresh should update dashboard when approved files drift."""
    work_package_dir = _init_package(tmp_path)
    design_file = _write_design(work_package_dir, "# Design v1\n")

    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    design_file.write_text("# Design v2\n", encoding="utf-8")
    refresh_artifact_registry(work_package_dir)

    dashboard_data = json.loads(
        (work_package_dir / "dashboard" / "dashboard.json").read_text(encoding="utf-8")
    )
    artifact = next(
        row for row in dashboard_data["artifacts"] if row["path"] == "artifacts/design/DESIGN.md"
    )

    assert artifact["state"] == "stale"
