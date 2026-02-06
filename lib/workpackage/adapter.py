"""Work item adapter for single-card lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
import re

from .artifacts import refresh_artifact_registry
from .dashboard import refresh_dashboard
from .lifecycle import transition_stage
from .schema import STAGES
from .service import initialize_work_package_from_task, load_manifest

KANBOARD_STAGE_MAP = {
    "inbox": "inbox",
    "design draft": "design_draft",
    "design approved": "design_approved",
    "planning draft": "planning_draft",
    "plan approved": "plan_approved",
    "tests draft": "tests_draft",
    "tests approved": "tests_approved",
    "ralph loop": "ralph_loop",
    "code review": "code_review",
    "final review": "final_review",
    "done": "done",
}


@dataclass(frozen=True)
class GateDecision:
    """Result of artifact gate evaluation for an orchestration action."""

    allowed: bool
    reason: str = ""


@dataclass
class AdapterSyncResult:
    """Lifecycle sync result for a work item update."""

    work_package_dir: Path
    from_stage: str
    to_stage: str
    transition_event_ids: list[str] = field(default_factory=list)


class WorkItemLifecycleAdapter(Protocol):
    """Provider-agnostic lifecycle adapter contract."""

    def ensure_work_package(
        self,
        task_id: int,
        title: str,
        project_id: int,
        fields: dict[str, Any],
    ) -> Path:
        """Create or reconcile local work package for external work item."""

    def sync_to_column(
        self,
        work_package_dir: Path,
        column_title: str,
        actor: str = "system",
    ) -> AdapterSyncResult:
        """Sync local lifecycle stage from external board column."""

    def gate_action(self, work_package_dir: Path, action: str) -> GateDecision:
        """Evaluate whether agent action may execute based on artifact health."""


def normalize_column_title(column_title: str) -> str:
    """Normalize Kanboard column labels by stripping numeric prefixes."""
    cleaned = re.sub(r"^\s*\d+\.\s*", "", column_title or "")
    return cleaned.strip().lower()


def stage_for_column(column_title: str) -> str | None:
    """Resolve lifecycle stage ID from Kanboard column title."""
    return KANBOARD_STAGE_MAP.get(normalize_column_title(column_title))


def _normalize_acceptance(value: str | list[str] | None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return ["Acceptance criteria pending"]
    lines = [line.strip("- ").strip() for line in str(value).splitlines() if line.strip()]
    return lines or ["Acceptance criteria pending"]


def _stage_order() -> dict[str, int]:
    return {str(stage["id"]): int(stage["order"]) for stage in STAGES}


class KanboardLifecycleAdapter:
    """Map Kanboard card movement to local single-card lifecycle transitions."""

    def __init__(self, base_dir: Path = Path("work-packages")):
        self._base_dir = base_dir

    def ensure_work_package(
        self,
        task_id: int,
        title: str,
        project_id: int,
        fields: dict[str, Any],
    ) -> Path:
        work_package_dir = initialize_work_package_from_task(
            base_dir=self._base_dir,
            task_id=task_id,
            title=title,
            dirname=str(fields.get("dirname", "")).strip(),
            context_mode=str(fields.get("context_mode", "NEW")).upper(),
            acceptance_criteria=_normalize_acceptance(fields.get("acceptance_criteria")),
            project_id=project_id,
            provider="kanboard",
        )
        refresh_artifact_registry(work_package_dir)
        refresh_dashboard(work_package_dir)
        return work_package_dir

    def sync_to_column(
        self,
        work_package_dir: Path,
        column_title: str,
        actor: str = "kanboard",
    ) -> AdapterSyncResult:
        target_stage = stage_for_column(column_title)
        if not target_stage:
            raise ValueError(f"No lifecycle stage mapping for column '{column_title}'")

        manifest = load_manifest(work_package_dir)
        current_stage = str(manifest["work_package"]["current_stage"])
        if current_stage == target_stage:
            return AdapterSyncResult(
                work_package_dir=work_package_dir,
                from_stage=current_stage,
                to_stage=target_stage,
                transition_event_ids=[],
            )

        orders = _stage_order()
        from_stage = current_stage
        events: list[str] = []

        if orders[target_stage] > orders[current_stage]:
            ordered_ids = [str(stage["id"]) for stage in sorted(STAGES, key=lambda row: int(row["order"]))]
            while current_stage != target_stage:
                idx = ordered_ids.index(current_stage)
                next_stage = ordered_ids[idx + 1]
                result = transition_stage(
                    work_package_dir=work_package_dir,
                    to_stage=next_stage,
                    actor=actor,
                    reason=f"sync-column:{column_title}",
                )
                events.append(result.event_id)
                current_stage = next_stage
        else:
            result = transition_stage(
                work_package_dir=work_package_dir,
                to_stage=target_stage,
                actor=actor,
                reason=f"sync-column:{column_title}",
            )
            events.append(result.event_id)
            current_stage = target_stage

        return AdapterSyncResult(
            work_package_dir=work_package_dir,
            from_stage=from_stage,
            to_stage=current_stage,
            transition_event_ids=events,
        )

    def gate_action(self, work_package_dir: Path, action: str) -> GateDecision:
        refresh_artifact_registry(work_package_dir)
        manifest = load_manifest(work_package_dir)
        items = manifest.get("artifacts", {}).get("items", {})
        if not isinstance(items, dict):
            items = {}

        if action == "PM_AGENT":
            return _gate_stage(items, stage_group="design", require_approved=True)
        if action in {"SPAWNER_AGENT", "TEST_AGENT"}:
            return _gate_stage(items, stage_group="planning", require_approved=True)
        if action == "TEST_CODE_AGENT":
            return _gate_stage(items, stage_group="tests", require_any=True)
        if action == "RALPH_CODER":
            return _gate_stage(items, stage_group="tests", require_approved=True)
        if action == "CODE_REVIEW_AGENT":
            return _gate_stage(items, stage_group="implementation", require_any=True)
        return GateDecision(allowed=True)


def _gate_stage(
    items: dict[str, Any],
    stage_group: str,
    require_approved: bool = False,
    require_any: bool = False,
) -> GateDecision:
    stage_items = [
        entry
        for entry in items.values()
        if isinstance(entry, dict) and entry.get("stage_group") == stage_group and entry.get("exists", True)
    ]
    if require_any and not stage_items:
        return GateDecision(False, f"Missing {stage_group} artifacts")
    if require_approved and not stage_items:
        return GateDecision(False, f"Missing {stage_group} artifacts for approval gate")
    if any(entry.get("state") == "stale" for entry in stage_items):
        return GateDecision(False, f"Stale {stage_group} artifacts must be refreshed")
    if require_approved and not any(entry.get("state") == "approved" for entry in stage_items):
        return GateDecision(False, f"No approved {stage_group} artifacts available")
    return GateDecision(True)
