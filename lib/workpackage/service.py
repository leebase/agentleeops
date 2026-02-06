"""Filesystem services for single-card work package bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import build_manifest, validate_manifest, ManifestValidationError

ARTIFACT_STAGE_DIRS = ("design", "planning", "tests", "implementation")


def _ensure_layout(work_package_dir: Path) -> None:
    artifacts_dir = work_package_dir / "artifacts"
    for stage_dir in ARTIFACT_STAGE_DIRS:
        (artifacts_dir / stage_dir).mkdir(parents=True, exist_ok=True)

    (work_package_dir / "approvals").mkdir(parents=True, exist_ok=True)

    dashboard_path = artifacts_dir / "dashboard.html"
    if not dashboard_path.exists():
        dashboard_path.write_text(
            "<!doctype html><html><body><h1>Dashboard pending generation</h1></body></html>\n",
            encoding="utf-8",
        )


def _manifest_path(work_package_dir: Path) -> Path:
    return work_package_dir / "manifest.yaml"


def load_manifest(work_package_dir: Path) -> dict[str, Any]:
    """Load and validate a work package manifest."""
    manifest_file = _manifest_path(work_package_dir)
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_file}")

    data = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
    errors = validate_manifest(data)
    if errors:
        raise ManifestValidationError("; ".join(errors))
    return data


def initialize_work_package(
    base_dir: Path,
    work_package_id: str,
    title: str,
    dirname: str,
    context_mode: str,
    acceptance_criteria: str | list[str],
    source: dict[str, Any] | None = None,
) -> Path:
    """
    Create a work package directory with a v1 manifest.

    Idempotent behavior:
    - If the manifest already exists and validates, layout is reconciled and path is returned.
    - If the manifest exists but is invalid, raises ManifestValidationError.
    """
    work_package_dir = base_dir / work_package_id
    work_package_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = _manifest_path(work_package_dir)
    if manifest_file.exists():
        load_manifest(work_package_dir)
        _ensure_layout(work_package_dir)
        return work_package_dir

    manifest = build_manifest(
        work_package_id=work_package_id,
        title=title,
        dirname=dirname,
        context_mode=context_mode,
        acceptance_criteria=acceptance_criteria,
        source=source,
    )
    errors = validate_manifest(manifest)
    if errors:
        raise ManifestValidationError("; ".join(errors))

    manifest_file.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    _ensure_layout(work_package_dir)
    return work_package_dir


def initialize_work_package_from_task(
    base_dir: Path,
    task_id: int,
    title: str,
    dirname: str,
    context_mode: str,
    acceptance_criteria: str | list[str],
    project_id: int | None = None,
    provider: str = "kanboard",
) -> Path:
    """Bootstrap work package data from task fields."""
    work_package_id = f"task-{task_id}"
    source: dict[str, Any] = {"provider": provider, "task_id": task_id}
    if project_id is not None:
        source["project_id"] = project_id

    return initialize_work_package(
        base_dir=base_dir,
        work_package_id=work_package_id,
        title=title,
        dirname=dirname,
        context_mode=context_mode,
        acceptance_criteria=acceptance_criteria,
        source=source,
    )
