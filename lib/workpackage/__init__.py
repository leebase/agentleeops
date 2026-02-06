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
    initialize_work_package,
    initialize_work_package_from_task,
    load_manifest,
)

__all__ = [
    "ARTIFACT_STAGE_DIRS",
    "ManifestValidationError",
    "SCHEMA_VERSION",
    "STAGES",
    "build_manifest",
    "initialize_work_package",
    "initialize_work_package_from_task",
    "load_manifest",
    "validate_manifest",
]
