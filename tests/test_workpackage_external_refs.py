"""Tests for external work item mapping import/export."""

from pathlib import Path

from lib.workpackage import (
    add_external_ref,
    export_external_refs,
    import_external_refs,
    initialize_work_package,
    list_external_refs,
)


def _init_package(tmp_path: Path, work_package_id: str) -> Path:
    return initialize_work_package(
        base_dir=tmp_path,
        work_package_id=work_package_id,
        title="External Ref Test",
        dirname=f"{work_package_id}-dirname",
        context_mode="NEW",
        acceptance_criteria=["mapping works"],
    )


def test_add_external_ref_is_idempotent(tmp_path: Path):
    """Adding the same external ref should update, not duplicate."""
    work_package_dir = _init_package(tmp_path, "task-201")
    add_external_ref(work_package_dir, provider="jira", external_id="PROJ-1", url="https://a")
    add_external_ref(work_package_dir, provider="jira", external_id="PROJ-1", url="https://b")

    refs = list_external_refs(work_package_dir)
    assert len(refs) == 1
    assert refs[0]["provider"] == "jira"
    assert refs[0]["external_id"] == "PROJ-1"
    assert refs[0]["url"] == "https://b"


def test_export_then_import_external_refs(tmp_path: Path):
    """Exported mapping payload should import into another work package."""
    source_dir = _init_package(tmp_path, "task-202")
    target_dir = _init_package(tmp_path, "task-203")

    add_external_ref(source_dir, provider="jira", external_id="PROJ-2")
    add_external_ref(source_dir, provider="ado", external_id="ADO-9", url="https://ado/9")
    payload = export_external_refs(source_dir)

    applied = import_external_refs(target_dir, payload)
    refs = list_external_refs(target_dir)

    assert applied == 2
    assert {(item["provider"], item["external_id"]) for item in refs} == {
        ("jira", "PROJ-2"),
        ("ado", "ADO-9"),
    }
