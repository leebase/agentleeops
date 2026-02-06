"""Tests for single-card work package adapter behavior."""

from pathlib import Path

from lib.workpackage import (
    KanboardLifecycleAdapter,
    load_manifest,
    refresh_artifact_registry,
    stage_for_column,
    transition_stage,
)


def test_stage_for_column_normalizes_numeric_prefix():
    """Kanboard column titles should map to lifecycle stage IDs."""
    assert stage_for_column("2. Design Draft") == "design_draft"
    assert stage_for_column("  11. Done") == "done"
    assert stage_for_column("Unknown") is None


def test_adapter_sync_moves_forward_one_stage_at_a_time(tmp_path: Path):
    """Sync should perform deterministic stepwise transitions when moving forward."""
    adapter = KanboardLifecycleAdapter(base_dir=tmp_path)
    work_package_dir = adapter.ensure_work_package(
        task_id=10,
        title="Adapter Sync",
        project_id=1,
        fields={
            "dirname": "adapter-sync",
            "context_mode": "NEW",
            "acceptance_criteria": "first criterion",
        },
    )
    (work_package_dir / "artifacts" / "design" / "DESIGN.md").write_text(
        "# Design\n",
        encoding="utf-8",
    )

    result = adapter.sync_to_column(work_package_dir, "4. Planning Draft", actor="test")
    manifest = load_manifest(work_package_dir)

    assert result.from_stage == "inbox"
    assert result.to_stage == "planning_draft"
    assert len(result.transition_event_ids) == 3
    assert manifest["work_package"]["current_stage"] == "planning_draft"


def test_adapter_gate_blocks_pm_when_design_is_stale(tmp_path: Path):
    """Planning should be blocked when approved design artifacts drift."""
    adapter = KanboardLifecycleAdapter(base_dir=tmp_path)
    work_package_dir = adapter.ensure_work_package(
        task_id=11,
        title="Adapter Gate",
        project_id=1,
        fields={
            "dirname": "adapter-gate",
            "context_mode": "NEW",
            "acceptance_criteria": "criterion",
        },
    )
    design_file = work_package_dir / "artifacts" / "design" / "DESIGN.md"
    design_file.write_text("# Design v1\n", encoding="utf-8")
    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    design_file.write_text("# Design v2\n", encoding="utf-8")
    refresh_artifact_registry(work_package_dir)
    decision = adapter.gate_action(work_package_dir, "PM_AGENT")

    assert decision.allowed is False
    assert "Stale" in decision.reason


def test_adapter_gate_allows_pm_when_design_is_approved(tmp_path: Path):
    """Planning should pass gate when design artifacts are approved and fresh."""
    adapter = KanboardLifecycleAdapter(base_dir=tmp_path)
    work_package_dir = adapter.ensure_work_package(
        task_id=12,
        title="Adapter Gate Pass",
        project_id=1,
        fields={
            "dirname": "adapter-gate-pass",
            "context_mode": "NEW",
            "acceptance_criteria": "criterion",
        },
    )
    design_file = work_package_dir / "artifacts" / "design" / "DESIGN.md"
    design_file.write_text("# Design v1\n", encoding="utf-8")
    transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    transition_stage(work_package_dir, to_stage="design_approved", actor="test")

    decision = adapter.gate_action(work_package_dir, "PM_AGENT")
    assert decision.allowed is True
