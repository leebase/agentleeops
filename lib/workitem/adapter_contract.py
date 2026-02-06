"""External adapter contract for future Jira/ADO integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .types import WorkItem, WorkItemIdentity, WorkItemState


@dataclass(frozen=True)
class StateMapping:
    """Mapping between provider-native state keys and logical work item states."""

    native_state: str
    logical_state: WorkItemState


@runtime_checkable
class ExternalWorkItemAdapter(Protocol):
    """
    Contract for future external providers (for example Jira or Azure DevOps).

    Implementations should be deterministic, idempotent, and retry-safe.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""

    def to_work_item(self, payload: dict[str, Any]) -> WorkItem:
        """Convert provider payload into canonical WorkItem model."""

    def to_identity(self, payload: dict[str, Any]) -> WorkItemIdentity:
        """Extract canonical identity from provider payload."""

    def resolve_state(self, native_state: str) -> WorkItemState:
        """Map provider state key to canonical logical state."""

    def supported_state_mappings(self) -> list[StateMapping]:
        """Return explicit state mapping table for introspection and docs."""
