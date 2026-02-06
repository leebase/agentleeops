"""Artifact indexing and integrity tracking for work packages."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .schema import STAGES
from .service import load_manifest, save_manifest

_STAGE_GROUP_TO_PATH_KEY = {
    "design": "design",
    "planning": "planning",
    "tests": "tests",
    "implementation": "implementation",
}

_STAGE_GROUP_APPROVALS = {
    "design": {"design_draft", "design_approved"},
    "planning": {"planning_draft", "plan_approved"},
    "tests": {"tests_draft", "tests_approved"},
    "implementation": {"ralph_loop", "code_review", "final_review", "done"},
}

_ARTIFACT_STATES = {"draft", "approved", "stale", "superseded"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage_order_map() -> dict[str, int]:
    return {stage["id"]: int(stage["order"]) for stage in STAGES}


def _stage_group_is_approved(manifest: dict[str, Any], stage_group: str) -> bool:
    approvals = (
        manifest.get("lifecycle", {})
        .get("stage_approvals", {})
    )
    group_stages = _STAGE_GROUP_APPROVALS.get(stage_group, set())
    if not approvals or not group_stages:
        return False

    orders = _stage_order_map()
    approved_stages = [
        stage_id
        for stage_id in group_stages
        if approvals.get(stage_id, {}).get("status") == "approved"
    ]
    if not approved_stages:
        return False

    latest = max(approved_stages, key=lambda stage_id: orders.get(stage_id, 0))
    return approvals.get(latest, {}).get("status") == "approved"


def _scan_artifact_files(work_package_dir: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    paths = manifest.get("paths", {})
    indexed: dict[str, dict[str, Any]] = {}

    for stage_group, path_key in _STAGE_GROUP_TO_PATH_KEY.items():
        relative = str(paths.get(path_key, "")).strip()
        if not relative:
            continue
        target_dir = work_package_dir / relative
        if not target_dir.exists():
            continue

        for file_path in sorted(target_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative_path = str(file_path.relative_to(work_package_dir))
            stat_result = file_path.stat()
            indexed[relative_path] = {
                "path": relative_path,
                "stage_group": stage_group,
                "sha256": _sha256_file(file_path),
                "size_bytes": int(stat_result.st_size),
                "mtime_ns": int(stat_result.st_mtime_ns),
            }

    return indexed


def refresh_artifact_registry(
    work_package_dir: Path,
    manifest: dict[str, Any] | None = None,
    approved_stage: str | None = None,
    approval_event_id: str | None = None,
    persist: bool = True,
    refresh_dashboard_output: bool = True,
    reason: str = "manual",
) -> dict[str, Any]:
    """
    Re-index artifact files and recompute integrity states.

    States:
    - draft: file exists but does not match an approved snapshot
    - approved: file hash matches last approved hash and stage remains approved
    - stale: file hash drifted from last approved hash
    - superseded: previously approved file no longer exists
    """
    current_manifest = manifest if manifest is not None else load_manifest(work_package_dir)
    snapshot = _scan_artifact_files(work_package_dir, current_manifest)

    artifacts_state = current_manifest.setdefault("artifacts", {})
    previous_items = artifacts_state.get("items", {})
    if not isinstance(previous_items, dict):
        previous_items = {}

    now = _utc_now()
    updated_items: dict[str, dict[str, Any]] = {}

    for relative_path, entry in snapshot.items():
        previous = previous_items.get(relative_path, {})
        if not isinstance(previous, dict):
            previous = {}

        record = dict(previous)
        record.update(entry)
        record["exists"] = True

        if approved_stage and approval_event_id:
            approved_group = _stage_for_lifecycle_stage(approved_stage)
            if approved_group and approved_group == record.get("stage_group"):
                record["last_approved_hash"] = record["sha256"]
                record["last_approved_at"] = now
                record["last_approved_event_id"] = approval_event_id
                record["approval_stage"] = approved_stage

        approved_hash = str(record.get("last_approved_hash", "")).strip()
        if approved_hash and approved_hash != record["sha256"]:
            record["state"] = "stale"
        elif approved_hash and _stage_group_is_approved(current_manifest, str(record["stage_group"])):
            record["state"] = "approved"
        else:
            record["state"] = "draft"

        record["updated_at"] = now
        record.pop("superseded_at", None)
        updated_items[relative_path] = record

    for relative_path, previous in previous_items.items():
        if relative_path in updated_items:
            continue
        if not isinstance(previous, dict):
            continue

        if not str(previous.get("last_approved_hash", "")).strip():
            # Keep registry small: dropped draft-only files are removed.
            continue

        record = dict(previous)
        record["exists"] = False
        record["state"] = "superseded"
        record["superseded_at"] = now
        record["updated_at"] = now
        updated_items[relative_path] = record

    artifacts_state["items"] = updated_items
    artifacts_state["updated_at"] = now
    artifacts_state["reason"] = reason
    artifacts_state["counts"] = _count_states(updated_items)

    if persist:
        save_manifest(work_package_dir, current_manifest)
        if refresh_dashboard_output:
            from .dashboard import refresh_dashboard

            refresh_dashboard(work_package_dir, manifest=current_manifest)
    return artifacts_state


def _stage_for_lifecycle_stage(stage_id: str) -> str | None:
    stage_map = {
        "design_draft": "design",
        "design_approved": "design",
        "planning_draft": "planning",
        "plan_approved": "planning",
        "tests_draft": "tests",
        "tests_approved": "tests",
        "ralph_loop": "implementation",
        "code_review": "implementation",
        "final_review": "implementation",
        "done": "implementation",
    }
    return stage_map.get(stage_id)


def _count_states(items: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {state: 0 for state in _ARTIFACT_STATES}
    for entry in items.values():
        state = str(entry.get("state", "")).strip()
        if state in counts:
            counts[state] += 1
    return counts
