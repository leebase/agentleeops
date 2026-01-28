"""
WorkItem Provider Protocol.

Defines the interface that all work item providers must implement.
Uses Python's Protocol for structural typing - providers don't need
to explicitly inherit from this class.
"""

from typing import Protocol, runtime_checkable

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)


@runtime_checkable
class WorkItemProvider(Protocol):
    """
    Provider-agnostic interface for work item backends.
    
    Implementations include:
    - KanboardWorkItemProvider (reference implementation)
    - JiraWorkItemProvider (future)
    - ADOWorkItemProvider (future)
    - MockWorkItemProvider (for testing)
    
    All methods should be idempotent and safe to retry per AGENTS.md.
    """
    
    @property
    def name(self) -> str:
        """
        Provider identifier.
        
        Returns:
            Provider name (e.g., "kanboard", "jira", "ado")
        """
        ...
    
    # --- Read Operations ---
    
    def get_work_item(self, identity: WorkItemIdentity) -> WorkItem | None:
        """
        Fetch a single work item by identity.
        
        Args:
            identity: Work item identifier
            
        Returns:
            WorkItem if found, None otherwise
        """
        ...
    
    def query_work_items(self, query: WorkItemQuery) -> list[WorkItem]:
        """
        Query work items with optional filters.
        
        Args:
            query: Query parameters (project, states, tags, etc.)
            
        Returns:
            List of matching work items (may be empty)
        """
        ...
    
    # --- State Transitions ---
    
    def update_state(
        self,
        identity: WorkItemIdentity,
        new_state: WorkItemState,
    ) -> bool:
        """
        Transition work item to a new state.
        
        This translates the logical state to the provider's native
        representation (e.g., moving to a Kanboard column).
        
        Args:
            identity: Work item identifier
            new_state: Target logical state
            
        Returns:
            True if successful, False otherwise
        """
        ...
    
    # --- Metadata & Comments ---
    
    def post_comment(
        self,
        identity: WorkItemIdentity,
        content: str,
    ) -> bool:
        """
        Add a comment to the work item.
        
        Args:
            identity: Work item identifier
            content: Comment text (markdown supported where available)
            
        Returns:
            True if successful, False otherwise
        """
        ...
    
    def set_metadata(
        self,
        identity: WorkItemIdentity,
        key: str,
        value: str,
    ) -> bool:
        """
        Set a metadata field on the work item.
        
        Metadata is provider-specific. For Kanboard, this maps to
        the MetaMagik custom fields API.
        
        Args:
            identity: Work item identifier
            key: Metadata field name
            value: Field value
            
        Returns:
            True if successful, False otherwise
        """
        ...
    
    # --- Tags ---
    
    def add_tag(
        self,
        identity: WorkItemIdentity,
        tag: str,
    ) -> bool:
        """
        Add a tag to the work item.
        
        Tags are used for idempotency tracking (e.g., "design-started").
        
        Args:
            identity: Work item identifier
            tag: Tag name
            
        Returns:
            True if successful, False otherwise
        """
        ...
    
    def get_tags(self, identity: WorkItemIdentity) -> list[str]:
        """
        Get all tags for a work item.
        
        Args:
            identity: Work item identifier
            
        Returns:
            List of tag names (may be empty)
        """
        ...
    
    def remove_tag(
        self,
        identity: WorkItemIdentity,
        tag: str,
    ) -> bool:
        """
        Remove a tag from the work item.
        
        Args:
            identity: Work item identifier
            tag: Tag name to remove
            
        Returns:
            True if successful (or tag didn't exist), False on error
        """
        ...
