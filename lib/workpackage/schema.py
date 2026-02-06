"""Schema helpers for single-card work package manifests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import re

from lib.workspace import validate_dirname

SCHEMA_VERSION = 1

STAGES: tuple[dict[str, Any], ...] = (
    {"id": "inbox", "label": "1. Inbox", "order": 1},
    {"id": "design_draft", "label": "2. Design Draft", "order": 2},
    {"id": "design_approved", "label": "3. Design Approved", "order": 3},
    {"id": "planning_draft", "label": "4. Planning Draft", "order": 4},
    {"id": "plan_approved", "label": "5. Plan Approved", "order": 5},
    {"id": "tests_draft", "label": "6. Tests Draft", "order": 6},
    {"id": "tests_approved", "label": "7. Tests Approved", "order": 7},
    {"id": "ralph_loop", "label": "8. Ralph Loop", "order": 8},
    {"id": "code_review", "label": "9. Code Review", "order": 9},
    {"id": "final_review", "label": "10. Final Review", "order": 10},
    {"id": "done", "label": "11. Done", "order": 11},
)


class ManifestValidationError(ValueError):
    """Raised when a work package manifest fails validation."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_acceptance_criteria(criteria: str | list[str]) -> list[str]:
    if isinstance(criteria, list):
        return [item.strip() for item in criteria if item and item.strip()]
    return [line.strip("- ").strip() for line in criteria.splitlines() if line.strip()]


def _validate_work_package_id(value: str) -> bool:
    return bool(re.match(r"^[a-z0-9-]+$", value))


def build_manifest(
    work_package_id: str,
    title: str,
    dirname: str,
    context_mode: str,
    acceptance_criteria: str | list[str],
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a v1 manifest dictionary."""
    now = _utc_now()
    source_data = source or {}

    return {
        "schema_version": SCHEMA_VERSION,
        "work_package": {
            "id": work_package_id,
            "title": title,
            "current_stage": "inbox",
            "created_at": now,
            "updated_at": now,
            "source": source_data,
        },
        "fields": {
            "dirname": dirname,
            "context_mode": context_mode,
            "acceptance_criteria": _normalize_acceptance_criteria(acceptance_criteria),
        },
        "paths": {
            "artifacts_root": "artifacts",
            "design": "artifacts/design",
            "planning": "artifacts/planning",
            "tests": "artifacts/tests",
            "implementation": "artifacts/implementation",
            "dashboard": "artifacts/dashboard.html",
            "approvals_root": "approvals",
        },
        "stages": list(STAGES),
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for a manifest."""
    errors: list[str] = []

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    work_package = manifest.get("work_package")
    if not isinstance(work_package, dict):
        errors.append("work_package must be an object")
        return errors

    wp_id = str(work_package.get("id", ""))
    if not wp_id or not _validate_work_package_id(wp_id):
        errors.append("work_package.id must match ^[a-z0-9-]+$")

    title = str(work_package.get("title", "")).strip()
    if not title:
        errors.append("work_package.title is required")

    current_stage = str(work_package.get("current_stage", ""))
    stage_ids = {stage["id"] for stage in STAGES}
    if current_stage not in stage_ids:
        errors.append("work_package.current_stage must be a known stage id")

    fields = manifest.get("fields")
    if not isinstance(fields, dict):
        errors.append("fields must be an object")
        return errors

    dirname = str(fields.get("dirname", ""))
    if not validate_dirname(dirname):
        errors.append("fields.dirname must contain lowercase letters, digits, or dashes")

    context_mode = str(fields.get("context_mode", ""))
    if context_mode not in {"NEW", "FEATURE"}:
        errors.append("fields.context_mode must be NEW or FEATURE")

    criteria = fields.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append("fields.acceptance_criteria must be a non-empty list")

    paths = manifest.get("paths")
    if not isinstance(paths, dict):
        errors.append("paths must be an object")
    else:
        required_paths = (
            "artifacts_root",
            "design",
            "planning",
            "tests",
            "implementation",
            "dashboard",
            "approvals_root",
        )
        for path_key in required_paths:
            if not str(paths.get(path_key, "")).strip():
                errors.append(f"paths.{path_key} is required")

    return errors
