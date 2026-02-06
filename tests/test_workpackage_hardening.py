"""Hardening tests for transition persistence and idempotency."""

from pathlib import Path

import pytest

from lib.workpackage import initialize_work_package, load_manifest, transition_stage


def _init_package(tmp_path: Path) -> Path:
    return initialize_work_package(
        base_dir=tmp_path,
        work_package_id="task-701",
        title="Hardening Test",
        dirname="hardening-test",
        context_mode="NEW",
        acceptance_criteria=["hardening works"],
    )


def test_transition_failure_cleans_pending_event_and_preserves_manifest(tmp_path: Path, monkeypatch):
    """Failed save should not leave partial event files or stage updates behind."""
    work_package_dir = _init_package(tmp_path)

    from lib.workpackage import lifecycle as lifecycle_module

    def _fail_save(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(lifecycle_module, "save_manifest", _fail_save)

    with pytest.raises(RuntimeError, match="simulated failure"):
        transition_stage(work_package_dir, to_stage="design_draft", actor="test")

    manifest = load_manifest(work_package_dir)
    approvals_dir = work_package_dir / "approvals"
    assert manifest["work_package"]["current_stage"] == "inbox"
    assert list(approvals_dir.glob("*.json")) == []
    assert list(approvals_dir.glob("*.tmp")) == []


def test_transition_retry_to_same_stage_is_idempotent(tmp_path: Path):
    """Re-running transition to current stage should return prior transition metadata."""
    work_package_dir = _init_package(tmp_path)
    first = transition_stage(work_package_dir, to_stage="design_draft", actor="test")
    second = transition_stage(work_package_dir, to_stage="design_draft", actor="test")

    approvals = list((work_package_dir / "approvals").glob("*.json"))
    assert len(approvals) == 1
    assert second.event_id == first.event_id
    assert second.to_stage == "design_draft"
