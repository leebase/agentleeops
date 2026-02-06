"""Tests for work package artifact indexing and integrity state."""

from pathlib import Path

from lib.workpackage import (
    initialize_work_package,
    load_manifest,
    refresh_artifact_registry,
    transition_stage,
)


def _init_package(tmp_path: Path) -> Path:
    return initialize_work_package(
        base_dir=tmp_path,
        work_package_id="task-123",
        title="Artifact Registry Test",
        dirname="artifact-registry-test",
        context_mode="NEW",
        acceptance_criteria=["registry works"],
    )


def _write_design(work_package_dir: Path, content: str) -> Path:
    design_file = work_package_dir / "artifacts" / "design" / "DESIGN.md"
    design_file.write_text(content, encoding="utf-8")
    return design_file


def test_refresh_indexes_stage_artifacts_as_draft(tmp_path: Path):
    """Refresh should index artifacts and mark new files as draft."""
    work_package_dir = _init_package(tmp_path)
    _write_design(work_package_dir, "# Design\n")

    state = refresh_artifact_registry(work_package_dir)
    manifest = load_manifest(work_package_dir)
    item = manifest["artifacts"]["items"]["artifacts/design/DESIGN.md"]

    assert state["counts"]["draft"] == 1
    assert item["stage_group"] == "design"
    assert item["state"] == "draft"
    assert item["exists"] is True
    assert len(item["sha256"]) == 64


def test_approved_artifact_becomes_stale_after_modification(tmp_path: Path):
    """An approved artifact should be marked stale when hash changes."""
    work_package_dir = _init_package(tmp_path)
    design_file = _write_design(work_package_dir, "# Design v1\n")

    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    approved_manifest = load_manifest(work_package_dir)
    approved_item = approved_manifest["artifacts"]["items"]["artifacts/design/DESIGN.md"]
    assert approved_item["state"] == "approved"

    design_file.write_text("# Design v2\n", encoding="utf-8")
    refreshed = refresh_artifact_registry(work_package_dir)
    stale_manifest = load_manifest(work_package_dir)
    stale_item = stale_manifest["artifacts"]["items"]["artifacts/design/DESIGN.md"]

    assert refreshed["counts"]["stale"] == 1
    assert stale_item["state"] == "stale"


def test_deleted_approved_artifact_is_superseded(tmp_path: Path):
    """An approved artifact should become superseded when deleted."""
    work_package_dir = _init_package(tmp_path)
    design_file = _write_design(work_package_dir, "# Design v1\n")

    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    design_file.unlink()
    state = refresh_artifact_registry(work_package_dir)
    manifest = load_manifest(work_package_dir)
    item = manifest["artifacts"]["items"]["artifacts/design/DESIGN.md"]

    assert state["counts"]["superseded"] == 1
    assert item["state"] == "superseded"
    assert item["exists"] is False
    assert item["superseded_at"]


def test_rollback_recomputes_approved_artifact_to_draft(tmp_path: Path):
    """Rollback should reopen prior approvals and recalculate artifact freshness."""
    work_package_dir = _init_package(tmp_path)
    _write_design(work_package_dir, "# Design v1\n")

    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")
    transition_stage(work_package_dir, to_stage="planning_draft", actor="test")

    manifest_before = load_manifest(work_package_dir)
    assert manifest_before["artifacts"]["items"]["artifacts/design/DESIGN.md"]["state"] == "approved"

    transition_stage(work_package_dir, to_stage="design_draft", actor="test", reason="reopen")

    manifest_after = load_manifest(work_package_dir)
    item = manifest_after["artifacts"]["items"]["artifacts/design/DESIGN.md"]

    assert item["state"] == "draft"
    assert manifest_after["lifecycle"]["stage_approvals"]["design_draft"]["status"] == "reopened"
