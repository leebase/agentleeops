"""Lifecycle transitions and approval event recording for work packages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import uuid

from .schema import STAGES, ManifestValidationError
from .artifacts import refresh_artifact_registry
from .dashboard import refresh_dashboard
from .service import load_manifest, save_manifest

APPROVAL_STAGE_PATH_KEY = {
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


@dataclass(frozen=True)
class TransitionResult:
    """Result metadata for a lifecycle transition."""

    from_stage: str
    to_stage: str
    transition_type: str
    event_file: Path
    event_id: str


def _stage_order_map() -> dict[str, int]:
    return {stage["id"]: int(stage["order"]) for stage in STAGES}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_file_path(approvals_dir: Path, event_type: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = uuid.uuid4().hex[:8]
    return approvals_dir / f"{ts}-{event_type}-{suffix}.json"


def _list_stage_artifacts(work_package_dir: Path, manifest: dict[str, Any], stage_id: str) -> list[str]:
    paths = manifest.get("paths", {})
    stage_key = APPROVAL_STAGE_PATH_KEY.get(stage_id)
    if not stage_key:
        return []

    relative_dir = paths.get(stage_key)
    if not relative_dir:
        return []

    target_dir = work_package_dir / str(relative_dir)
    if not target_dir.exists():
        return []

    files: list[str] = []
    for file_path in sorted(target_dir.rglob("*")):
        if file_path.is_file():
            files.append(str(file_path.relative_to(work_package_dir)))
    return files


def _validate_target_stage(target_stage: str) -> None:
    stage_ids = {stage["id"] for stage in STAGES}
    if target_stage not in stage_ids:
        raise ManifestValidationError(
            f"Unknown target stage '{target_stage}'. Expected one of: {sorted(stage_ids)}"
        )


def _transition_type(current_stage: str, target_stage: str) -> str:
    orders = _stage_order_map()
    current_order = orders[current_stage]
    target_order = orders[target_stage]
    if target_order == current_order:
        raise ManifestValidationError(f"Work package is already in stage '{current_stage}'")
    if target_order == current_order + 1:
        return "advance"
    if target_order < current_order:
        return "rollback"
    raise ManifestValidationError(
        f"Invalid forward jump: {current_stage} -> {target_stage}. "
        "Only one-step forward transitions are allowed."
    )


def _precondition_errors(
    work_package_dir: Path,
    manifest: dict[str, Any],
    current_stage: str,
    transition_type: str,
) -> list[str]:
    if transition_type != "advance":
        return []

    if current_stage not in {"design_draft", "planning_draft", "tests_draft"}:
        return []

    stage_files = _list_stage_artifacts(work_package_dir, manifest, current_stage)
    if stage_files:
        return []

    stage_label = current_stage.replace("_", " ")
    return [f"Cannot advance from {stage_label}: no stage artifacts found"]


def _mark_approved_state(manifest: dict[str, Any], stage_id: str, event_id: str, actor: str) -> None:
    state = manifest.setdefault("lifecycle", {})
    approvals = state.setdefault("stage_approvals", {})
    approvals[stage_id] = {
        "status": "approved",
        "event_id": event_id,
        "approved_at": _utc_now(),
        "approved_by": actor,
    }


def _mark_reopened_state(manifest: dict[str, Any], target_stage: str, event_id: str, actor: str) -> list[str]:
    orders = _stage_order_map()
    target_order = orders[target_stage]
    state = manifest.setdefault("lifecycle", {})
    approvals = state.setdefault("stage_approvals", {})
    reopened: list[str] = []

    for stage_id, stage_order in orders.items():
        if stage_order >= target_order and stage_id in approvals:
            approvals[stage_id]["status"] = "reopened"
            approvals[stage_id]["reopened_at"] = _utc_now()
            approvals[stage_id]["reopened_by"] = actor
            approvals[stage_id]["reopened_event_id"] = event_id
            reopened.append(stage_id)

    return sorted(reopened, key=lambda item: orders[item])


def transition_stage(
    work_package_dir: Path,
    to_stage: str,
    actor: str = "system",
    reason: str = "",
) -> TransitionResult:
    """
    Move a work package to a new stage and record a lifecycle event.

    Rules:
    - One-step forward transitions only.
    - Rollback/reopen transitions can jump to any prior stage.
    - Forward transitions implicitly approve the current stage.
    """
    manifest = load_manifest(work_package_dir)
    work_package = manifest["work_package"]
    from_stage = str(work_package["current_stage"])

    _validate_target_stage(to_stage)
    transition_type = _transition_type(from_stage, to_stage)

    errors = _precondition_errors(work_package_dir, manifest, from_stage, transition_type)
    if errors:
        raise ManifestValidationError("; ".join(errors))

    approvals_dir = work_package_dir / manifest["paths"]["approvals_root"]
    approvals_dir.mkdir(parents=True, exist_ok=True)

    event_id = str(uuid.uuid4())
    event_file = _event_file_path(approvals_dir, transition_type)
    event: dict[str, Any] = {
        "event_id": event_id,
        "event_type": transition_type,
        "at": _utc_now(),
        "actor": actor,
        "reason": reason,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "artifacts": [],
        "effects": {},
    }

    if transition_type == "advance":
        event["artifacts"] = _list_stage_artifacts(work_package_dir, manifest, from_stage)
        event["effects"]["approved_stage"] = from_stage
        _mark_approved_state(manifest, from_stage, event_id, actor)
    else:
        reopened = _mark_reopened_state(manifest, to_stage, event_id, actor)
        event["effects"]["reopened_stages"] = reopened

    work_package["current_stage"] = to_stage
    work_package["updated_at"] = _utc_now()
    work_package["last_transition"] = {
        "event_id": event_id,
        "event_type": transition_type,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "at": _utc_now(),
        "actor": actor,
    }

    refresh_artifact_registry(
        work_package_dir=work_package_dir,
        manifest=manifest,
        approved_stage=from_stage if transition_type == "advance" else None,
        approval_event_id=event_id if transition_type == "advance" else None,
        persist=False,
        refresh_dashboard_output=False,
        reason=f"transition:{transition_type}",
    )

    event_file.write_text(json.dumps(event, indent=2), encoding="utf-8")
    save_manifest(work_package_dir, manifest)
    refresh_dashboard(work_package_dir, manifest=manifest)

    return TransitionResult(
        from_stage=from_stage,
        to_stage=to_stage,
        transition_type=transition_type,
        event_file=event_file,
        event_id=event_id,
    )


def list_approval_events(work_package_dir: Path) -> list[dict[str, Any]]:
    """Load approval event history ordered by filename timestamp."""
    manifest = load_manifest(work_package_dir)
    approvals_root = work_package_dir / manifest["paths"]["approvals_root"]
    if not approvals_root.exists():
        return []

    events: list[dict[str, Any]] = []
    for event_file in sorted(approvals_root.glob("*.json")):
        try:
            event = json.loads(event_file.read_text(encoding="utf-8"))
            event["_file"] = str(event_file.relative_to(work_package_dir))
            events.append(event)
        except json.JSONDecodeError:
            continue
    events.sort(key=lambda item: (str(item.get("at", "")), str(item.get("_file", ""))))
    return events


def replay_summary(work_package_dir: Path) -> list[str]:
    """Return a compact, replayable transition summary."""
    manifest = load_manifest(work_package_dir)
    events = list_approval_events(work_package_dir)
    lines = [
        f"work_package:{manifest['work_package']['id']}",
        f"current_stage:{manifest['work_package']['current_stage']}",
    ]
    for event in events:
        lines.append(
            "event:"
            f"{event.get('event_type')}:{event.get('from_stage')}->{event.get('to_stage')}:"
            f"{event.get('event_id')}"
        )
    return lines
