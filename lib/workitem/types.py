"""
WorkItem types and data structures.

This module defines provider-agnostic data classes for work items,
decoupling the orchestration layer from specific backends like Kanboard.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorkItemState(Enum):
    """
    Logical pipeline states for work items.
    
    These map to the 10-column AgentLeeOps workflow but are decoupled
    from provider-specific column names. Providers translate their
    native states to these logical states.
    """
    INBOX = "inbox"
    DESIGN_DRAFT = "design_draft"
    DESIGN_APPROVED = "design_approved"
    PLANNING_DRAFT = "planning_draft"
    PLAN_APPROVED = "plan_approved"
    TESTS_DRAFT = "tests_draft"
    TESTS_APPROVED = "tests_approved"
    IMPLEMENTATION = "implementation"
    FINAL_REVIEW = "final_review"
    DONE = "done"
    UNKNOWN = "unknown"  # Fallback for unmapped states


@dataclass(frozen=True)
class WorkItemIdentity:
    """
    Unique identifier for a work item across providers.
    
    Frozen (immutable) so it can be used as dict key or in sets.
    
    Attributes:
        provider: Provider name (e.g., "kanboard", "jira", "ado")
        external_id: Provider's native ID as string (e.g., "123", "PROJ-456")
        url: Optional direct link to the work item in the provider's UI
    """
    provider: str
    external_id: str
    url: str | None = None
    
    def __str__(self) -> str:
        return f"{self.provider}:{self.external_id}"


@dataclass
class WorkItem:
    """
    Complete work item representation.
    
    Contains all fields needed by the orchestration layer, independent
    of which provider the item came from.
    
    Attributes:
        identity: Unique identifier (provider, external_id, url)
        title: Work item title/summary
        description: Full description text
        state: Current logical pipeline state
        
        dirname: Project directory name (task-specific)
        context_mode: "NEW" or "FEATURE" (task-specific)
        acceptance_criteria: Acceptance criteria text
        complexity: Size estimate ("S", "M", "L", "XL")
        
        agent_status: Current agent execution status
        current_phase: Current workflow phase
        tags: List of tags/labels
        
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        
        metadata: Provider-specific extra fields
    """
    identity: WorkItemIdentity
    title: str
    description: str = ""
    state: WorkItemState = WorkItemState.UNKNOWN
    
    # Task-specific fields (from card metadata/description)
    dirname: str | None = None
    context_mode: str | None = None
    acceptance_criteria: str | None = None
    complexity: str | None = None
    
    # Status tracking
    agent_status: str | None = None
    current_phase: str | None = None
    tags: list[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    # Provider-specific extras (flexibility for enterprise)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def has_tag(self, tag: str) -> bool:
        """Check if work item has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "identity": {
                "provider": self.identity.provider,
                "external_id": self.identity.external_id,
                "url": self.identity.url,
            },
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "dirname": self.dirname,
            "context_mode": self.context_mode,
            "acceptance_criteria": self.acceptance_criteria,
            "complexity": self.complexity,
            "agent_status": self.agent_status,
            "current_phase": self.current_phase,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkItem":
        """Create WorkItem from dictionary."""
        identity_data = data.get("identity", {})
        identity = WorkItemIdentity(
            provider=identity_data.get("provider", "unknown"),
            external_id=identity_data.get("external_id", ""),
            url=identity_data.get("url"),
        )
        
        state_value = data.get("state", "unknown")
        try:
            state = WorkItemState(state_value)
        except ValueError:
            state = WorkItemState.UNKNOWN
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        
        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            identity=identity,
            title=data.get("title", ""),
            description=data.get("description", ""),
            state=state,
            dirname=data.get("dirname"),
            context_mode=data.get("context_mode"),
            acceptance_criteria=data.get("acceptance_criteria"),
            complexity=data.get("complexity"),
            agent_status=data.get("agent_status"),
            current_phase=data.get("current_phase"),
            tags=data.get("tags", []),
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkItemQuery:
    """
    Query parameters for filtering work items.
    
    Used by providers to implement filtered fetching.
    All fields are optional - None means "no filter".
    
    Attributes:
        project_id: Filter by project (provider-specific format)
        states: Filter by one or more logical states
        tags: Filter by tags (items must have ALL specified tags)
        assignee: Filter by assignee identifier
        limit: Maximum number of items to return
    """
    project_id: str | None = None
    states: list[WorkItemState] | None = None
    tags: list[str] | None = None
    assignee: str | None = None
    limit: int = 100
