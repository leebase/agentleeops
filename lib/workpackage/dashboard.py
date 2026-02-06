"""Dashboard rendering for work package lifecycle and artifact health."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
import json

from .schema import STAGES
from .service import load_manifest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dashboard_paths(work_package_dir: Path, manifest: dict[str, Any]) -> tuple[Path, Path]:
    paths = manifest.get("paths", {})
    html_rel = str(paths.get("dashboard", "")).strip() or "dashboard/dashboard.html"
    data_rel = str(paths.get("dashboard_data", "")).strip()
    if not data_rel:
        data_rel = str(Path(html_rel).parent / "dashboard.json")

    return work_package_dir / data_rel, work_package_dir / html_rel


def _stage_status_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    current_stage = str(manifest.get("work_package", {}).get("current_stage", ""))
    approvals = manifest.get("lifecycle", {}).get("stage_approvals", {})

    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        stage_id = str(stage["id"])
        approval = approvals.get(stage_id, {})
        rows.append(
            {
                "id": stage_id,
                "label": stage["label"],
                "order": int(stage["order"]),
                "is_current": stage_id == current_stage,
                "approval_status": approval.get("status", "n/a"),
                "approval_event_id": approval.get("event_id"),
            }
        )
    return rows


def _artifact_rows(work_package_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("artifacts", {}).get("items", {})
    if not isinstance(items, dict):
        return []

    rows: list[dict[str, Any]] = []
    for rel_path in sorted(items.keys()):
        entry = items[rel_path]
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "path": rel_path,
                "full_path": str((work_package_dir / rel_path).resolve()),
                "stage_group": entry.get("stage_group"),
                "state": entry.get("state"),
                "sha256": entry.get("sha256"),
                "last_approved_hash": entry.get("last_approved_hash"),
                "exists": bool(entry.get("exists", True)),
            }
        )
    return rows


def _approval_events(work_package_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    approvals_root_rel = str(manifest.get("paths", {}).get("approvals_root", "")).strip()
    if not approvals_root_rel:
        return []
    approvals_root = work_package_dir / approvals_root_rel
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


def build_dashboard_data(
    work_package_dir: Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical dashboard data from manifest, approvals, and artifacts."""
    current_manifest = manifest if manifest is not None else load_manifest(work_package_dir)
    events = _approval_events(work_package_dir, current_manifest)
    artifact_rows = _artifact_rows(work_package_dir, current_manifest)

    return {
        "generated_at": _utc_now(),
        "work_package": current_manifest.get("work_package", {}),
        "fields": current_manifest.get("fields", {}),
        "stage_status": _stage_status_rows(current_manifest),
        "artifacts": artifact_rows,
        "artifact_counts": current_manifest.get("artifacts", {}).get("counts", {}),
        "approval_events": events,
        "links": {
            "manifest": str((work_package_dir / "manifest.yaml").resolve()),
            "approvals": str((work_package_dir / "approvals").resolve()),
            "artifacts_root": str((work_package_dir / "artifacts").resolve()),
        },
    }


def render_dashboard_html(data: dict[str, Any]) -> str:
    """Render dashboard HTML from canonical data."""
    work_package = data.get("work_package", {})
    title = escape(str(work_package.get("title", "Work Package Dashboard")))
    wp_id = escape(str(work_package.get("id", "")))
    current_stage = escape(str(work_package.get("current_stage", "")))
    generated_at = escape(str(data.get("generated_at", "")))

    stage_rows = data.get("stage_status", [])
    artifact_rows = data.get("artifacts", [])
    approval_events = data.get("approval_events", [])

    stage_table = "".join(
        (
            "<tr>"
            f"<td>{escape(str(row.get('order', '')))}</td>"
            f"<td>{escape(str(row.get('label', '')))}</td>"
            f"<td>{'yes' if row.get('is_current') else ''}</td>"
            f"<td>{escape(str(row.get('approval_status', '')))}</td>"
            "</tr>"
        )
        for row in stage_rows
    )

    artifact_table = "".join(
        (
            "<tr>"
            f"<td>{escape(str(row.get('path', '')))}</td>"
            f"<td>{escape(str(row.get('stage_group', '')))}</td>"
            f"<td>{escape(str(row.get('state', '')))}</td>"
            f"<td>{'yes' if row.get('exists') else 'no'}</td>"
            "</tr>"
        )
        for row in artifact_rows
    )

    event_table = "".join(
        (
            "<tr>"
            f"<td>{escape(str(event.get('event_type', '')))}</td>"
            f"<td>{escape(str(event.get('from_stage', '')))}</td>"
            f"<td>{escape(str(event.get('to_stage', '')))}</td>"
            f"<td>{escape(str(event.get('_file', '')))}</td>"
            "</tr>"
        )
        for event in approval_events
    )

    links = data.get("links", {})
    approvals_link = escape(str(links.get("approvals", "")))
    artifacts_link = escape(str(links.get("artifacts_root", "")))
    manifest_link = escape(str(links.get("manifest", "")))

    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        f"  <title>{title}</title>\n"
        "  <style>\n"
        "    body { font-family: Arial, sans-serif; margin: 24px; color: #1a1a1a; }\n"
        "    table { border-collapse: collapse; width: 100%; margin-bottom: 24px; }\n"
        "    th, td { border: 1px solid #d4d4d4; padding: 8px; text-align: left; }\n"
        "    th { background: #f5f5f5; }\n"
        "    code { background: #f0f0f0; padding: 1px 4px; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>{title}</h1>\n"
        f"  <p><strong>ID:</strong> <code>{wp_id}</code></p>\n"
        f"  <p><strong>Current stage:</strong> <code>{current_stage}</code></p>\n"
        f"  <p><strong>Generated:</strong> {generated_at}</p>\n"
        "  <p>\n"
        f"    <strong>Links:</strong> manifest <code>{manifest_link}</code>, "
        f"artifacts <code>{artifacts_link}</code>, approvals <code>{approvals_link}</code>\n"
        "  </p>\n"
        "  <h2>Stage Status</h2>\n"
        "  <table>\n"
        "    <thead><tr><th>Order</th><th>Stage</th><th>Current</th><th>Approval</th></tr></thead>\n"
        f"    <tbody>{stage_table}</tbody>\n"
        "  </table>\n"
        "  <h2>Artifacts</h2>\n"
        "  <table>\n"
        "    <thead><tr><th>Path</th><th>Stage</th><th>State</th><th>Exists</th></tr></thead>\n"
        f"    <tbody>{artifact_table}</tbody>\n"
        "  </table>\n"
        "  <h2>Approval History</h2>\n"
        "  <table>\n"
        "    <thead><tr><th>Type</th><th>From</th><th>To</th><th>Event File</th></tr></thead>\n"
        f"    <tbody>{event_table}</tbody>\n"
        "  </table>\n"
        "</body>\n"
        "</html>\n"
    )


def refresh_dashboard(
    work_package_dir: Path,
    manifest: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Write dashboard JSON and HTML files and return their paths."""
    current_manifest = manifest if manifest is not None else load_manifest(work_package_dir)
    data_path, html_path = _dashboard_paths(work_package_dir, current_manifest)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    dashboard_data = build_dashboard_data(work_package_dir, manifest=current_manifest)
    data_path.write_text(json.dumps(dashboard_data, indent=2), encoding="utf-8")
    html_path.write_text(render_dashboard_html(dashboard_data), encoding="utf-8")
    return data_path, html_path
