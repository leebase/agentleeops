"""Tests for CLI-first local orchestration helpers."""

from pathlib import Path

from lib.workpackage import (
    evaluate_gate,
    initialize_work_package,
    load_manifest,
    refresh_artifact_registry,
    sync_to_stage,
)


def _init_package(tmp_path: Path) -> Path:
    return initialize_work_package(
        base_dir=tmp_path,
        work_package_id="task-301",
        title="Local Orchestrator Test",
        dirname="local-orchestrator-test",
        context_mode="NEW",
        acceptance_criteria=["local orchestration works"],
    )


def test_sync_to_stage_moves_forward_with_expected_event_count(tmp_path: Path):
    """sync_to_stage should execute deterministic one-step transitions."""
    work_package_dir = _init_package(tmp_path)
    (work_package_dir / "artifacts" / "design" / "DESIGN.md").write_text(
        "# Design\n",
        encoding="utf-8",
    )
    (work_package_dir / "artifacts" / "planning" / "prd.json").write_text(
        "{\"stories\": []}\n",
        encoding="utf-8",
    )

    result = sync_to_stage(work_package_dir, to_stage="plan_approved", actor="test")
    manifest = load_manifest(work_package_dir)

    assert result.from_stage == "inbox"
    assert result.to_stage == "plan_approved"
    assert len(result.event_ids) == 4
    assert manifest["work_package"]["current_stage"] == "plan_approved"


def test_evaluate_gate_blocks_when_artifact_is_stale(tmp_path: Path):
    """evaluate_gate should block actions when required artifacts are stale."""
    work_package_dir = _init_package(tmp_path)
    design_file = work_package_dir / "artifacts" / "design" / "DESIGN.md"
    design_file.write_text("# Design v1\n", encoding="utf-8")

    sync_to_stage(work_package_dir, to_stage="design_approved", actor="test")
    design_file.write_text("# Design v2\n", encoding="utf-8")
    refresh_artifact_registry(work_package_dir)

    decision = evaluate_gate(work_package_dir, "PM_AGENT")
    assert decision.allowed is False
