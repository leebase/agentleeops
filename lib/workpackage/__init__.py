"""Work package primitives for the single-card lifecycle model."""

from .schema import (
    STAGES,
    SCHEMA_VERSION,
    ManifestValidationError,
    build_manifest,
    validate_manifest,
)
from .service import (
    ARTIFACT_STAGE_DIRS,
    get_manifest_path,
    initialize_work_package,
    initialize_work_package_from_task,
    load_manifest,
    save_manifest,
)
from .artifacts import refresh_artifact_registry
from .dashboard import (
    build_dashboard_data,
    refresh_dashboard,
    render_dashboard_html,
)
from .lifecycle import (
    TransitionResult,
    list_approval_events,
    replay_summary,
    transition_stage,
)

__all__ = [
    "ARTIFACT_STAGE_DIRS",
    "ManifestValidationError",
    "SCHEMA_VERSION",
    "STAGES",
    "TransitionResult",
    "build_manifest",
    "build_dashboard_data",
    "get_manifest_path",
    "initialize_work_package",
    "initialize_work_package_from_task",
    "list_approval_events",
    "load_manifest",
    "refresh_artifact_registry",
    "refresh_dashboard",
    "replay_summary",
    "render_dashboard_html",
    "save_manifest",
    "transition_stage",
    "validate_manifest",
]
