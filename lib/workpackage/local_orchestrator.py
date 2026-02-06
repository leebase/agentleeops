"""Local orchestration helpers for CLI-first lifecycle execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .adapter import GateDecision, KanboardLifecycleAdapter
from .lifecycle import transition_stage
from .schema import STAGES, ManifestValidationError
from .service import load_manifest


@dataclass
class LocalSyncResult:
    """Result metadata for local sync-stage operations."""

    from_stage: str
    to_stage: str
    event_ids: list[str] = field(default_factory=list)


def _stage_order() -> dict[str, int]:
    return {str(stage["id"]): int(stage["order"]) for stage in STAGES}


def sync_to_stage(
    work_package_dir: Path,
    to_stage: str,
    actor: str = "cli",
    reason: str = "",
) -> LocalSyncResult:
    """Sync local lifecycle to target stage deterministically."""
    manifest = load_manifest(work_package_dir)
    current_stage = str(manifest["work_package"]["current_stage"])
    if current_stage == to_stage:
        return LocalSyncResult(from_stage=current_stage, to_stage=to_stage, event_ids=[])

    order_map = _stage_order()
    if to_stage not in order_map:
        raise ManifestValidationError(f"Unknown stage: {to_stage}")

    from_stage = current_stage
    events: list[str] = []
    if order_map[to_stage] > order_map[current_stage]:
        ordered_ids = [str(stage["id"]) for stage in sorted(STAGES, key=lambda row: int(row["order"]))]
        while current_stage != to_stage:
            idx = ordered_ids.index(current_stage)
            next_stage = ordered_ids[idx + 1]
            result = transition_stage(
                work_package_dir=work_package_dir,
                to_stage=next_stage,
                actor=actor,
                reason=reason or f"sync-stage:{to_stage}",
            )
            events.append(result.event_id)
            current_stage = next_stage
    else:
        result = transition_stage(
            work_package_dir=work_package_dir,
            to_stage=to_stage,
            actor=actor,
            reason=reason or f"sync-stage:{to_stage}",
        )
        events.append(result.event_id)
        current_stage = to_stage

    return LocalSyncResult(from_stage=from_stage, to_stage=current_stage, event_ids=events)


def evaluate_gate(work_package_dir: Path, action: str) -> GateDecision:
    """Evaluate stage gate from local artifact state without board dependencies."""
    return KanboardLifecycleAdapter().gate_action(work_package_dir, action)
