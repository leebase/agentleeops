"""External work item mapping helpers for work packages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .service import load_manifest, save_manifest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_external_refs(work_package_dir: Path) -> list[dict[str, Any]]:
    """Return configured external work item references."""
    manifest = load_manifest(work_package_dir)
    refs = manifest.get("external_refs", {}).get("items", [])
    if not isinstance(refs, list):
        return []
    return [item for item in refs if isinstance(item, dict)]


def add_external_ref(
    work_package_dir: Path,
    provider: str,
    external_id: str,
    url: str | None = None,
) -> dict[str, Any]:
    """Add or update an external provider mapping entry."""
    manifest = load_manifest(work_package_dir)
    external_refs = manifest.setdefault("external_refs", {})
    items = external_refs.setdefault("items", [])
    if not isinstance(items, list):
        items = []
        external_refs["items"] = items

    normalized_provider = provider.strip().lower()
    normalized_id = external_id.strip()
    if not normalized_provider or not normalized_id:
        raise ValueError("provider and external_id are required")

    existing = None
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("provider") == normalized_provider
            and item.get("external_id") == normalized_id
        ):
            existing = item
            break

    now = _utc_now()
    if existing is None:
        existing = {
            "provider": normalized_provider,
            "external_id": normalized_id,
            "url": url or "",
            "added_at": now,
            "updated_at": now,
        }
        items.append(existing)
    else:
        if url is not None:
            existing["url"] = url
        existing["updated_at"] = now

    external_refs["updated_at"] = now
    save_manifest(work_package_dir, manifest)
    return existing


def export_external_refs(work_package_dir: Path) -> dict[str, Any]:
    """Export external mapping payload for backup or migration."""
    manifest = load_manifest(work_package_dir)
    refs = list_external_refs(work_package_dir)
    return {
        "work_package_id": manifest.get("work_package", {}).get("id"),
        "exported_at": _utc_now(),
        "refs": refs,
    }


def import_external_refs(
    work_package_dir: Path,
    payload: dict[str, Any],
) -> int:
    """Import external mapping payload and return number of refs applied."""
    refs = payload.get("refs", [])
    if not isinstance(refs, list):
        raise ValueError("payload.refs must be a list")

    applied = 0
    for item in refs:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider", "")).strip()
        external_id = str(item.get("external_id", "")).strip()
        url = str(item.get("url", "")).strip() or None
        if not provider or not external_id:
            continue
        add_external_ref(
            work_package_dir=work_package_dir,
            provider=provider,
            external_id=external_id,
            url=url,
        )
        applied += 1
    return applied
