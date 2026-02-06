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
from .adapter import (
    AdapterSyncResult,
    GateDecision,
    KanboardLifecycleAdapter,
    WorkItemLifecycleAdapter,
    normalize_column_title,
    stage_for_column,
)
from .dashboard import (
    build_dashboard_data,
    refresh_dashboard,
    render_dashboard_html,
)
from .external_refs import (
    add_external_ref,
    export_external_refs,
    import_external_refs,
    list_external_refs,
)
from .local_orchestrator import LocalSyncResult, evaluate_gate, sync_to_stage
from .lifecycle import (
    TransitionResult,
    list_approval_events,
    replay_summary,
    transition_stage,
)

__all__ = [
    "ARTIFACT_STAGE_DIRS",
    "AdapterSyncResult",
    "GateDecision",
    "KanboardLifecycleAdapter",
    "LocalSyncResult",
    "ManifestValidationError",
    "SCHEMA_VERSION",
    "STAGES",
    "TransitionResult",
    "WorkItemLifecycleAdapter",
    "add_external_ref",
    "build_manifest",
    "build_dashboard_data",
    "export_external_refs",
    "get_manifest_path",
    "evaluate_gate",
    "import_external_refs",
    "initialize_work_package",
    "initialize_work_package_from_task",
    "list_external_refs",
    "list_approval_events",
    "load_manifest",
    "refresh_artifact_registry",
    "refresh_dashboard",
    "replay_summary",
    "render_dashboard_html",
    "save_manifest",
    "sync_to_stage",
    "normalize_column_title",
    "stage_for_column",
    "transition_stage",
    "validate_manifest",
]
