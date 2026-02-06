"""Migration utilities from legacy workspace artifacts to single-card packages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import shutil

from .artifacts import refresh_artifact_registry
from .dashboard import refresh_dashboard
from .service import initialize_work_package, initialize_work_package_from_task


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _copy_file(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def migrate_from_workspace(
    base_dir: Path,
    work_package_id: str,
    title: str,
    dirname: str,
    context_mode: str,
    acceptance_criteria: str | list[str],
    workspace_dir: Path,
    task_id: int | None = None,
    project_id: int | None = None,
    provider: str = "kanboard",
) -> dict[str, Any]:
    """Migrate known artifacts from a legacy workspace into a work package."""
    if task_id is not None:
        work_package_dir = initialize_work_package_from_task(
            base_dir=base_dir,
            task_id=task_id,
            title=title,
            dirname=dirname,
            context_mode=context_mode,
            acceptance_criteria=acceptance_criteria,
            project_id=project_id,
            provider=provider,
        )
    else:
        work_package_dir = initialize_work_package(
            base_dir=base_dir,
            work_package_id=work_package_id,
            title=title,
            dirname=dirname,
            context_mode=context_mode,
            acceptance_criteria=acceptance_criteria,
            source={"provider": provider},
        )

    mapping = {
        workspace_dir / "DESIGN.md": work_package_dir / "artifacts" / "design" / "DESIGN.md",
        workspace_dir / "prd.json": work_package_dir / "artifacts" / "planning" / "prd.json",
    }

    copied: list[str] = []
    missing: list[str] = []

    for src, dst in mapping.items():
        if _copy_file(src, dst):
            copied.append(str(dst.relative_to(work_package_dir)))
        else:
            missing.append(str(src))

    for pattern in ("TEST_PLAN_*.md", "test_*.py"):
        for source in sorted((workspace_dir / "tests").glob(pattern)):
            target = work_package_dir / "artifacts" / "tests" / source.name
            if _copy_file(source, target):
                copied.append(str(target.relative_to(work_package_dir)))

    for source in sorted((workspace_dir / "src").rglob("*")):
        if not source.is_file():
            continue
        target = work_package_dir / "artifacts" / "implementation" / "src" / source.relative_to(
            workspace_dir / "src"
        )
        if _copy_file(source, target):
            copied.append(str(target.relative_to(work_package_dir)))

    refresh_artifact_registry(work_package_dir)
    refresh_dashboard(work_package_dir)

    report = {
        "generated_at": _utc_now(),
        "work_package_dir": str(work_package_dir),
        "workspace_dir": str(workspace_dir),
        "copied_files": sorted(set(copied)),
        "missing_required": sorted(set(missing)),
    }

    report_dir = work_package_dir / "migration"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "migration-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report
