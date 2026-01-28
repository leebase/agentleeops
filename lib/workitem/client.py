"""
WorkItem client facade.

User-facing client that wraps a provider and delegates operations.
Provides a clean API for agents to interact with work items.
"""

from typing import TYPE_CHECKING

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)
from lib.workitem.config import load_provider_config, get_provider_config
from lib.workitem.capabilities import Capability, detect_capabilities, has_capability

if TYPE_CHECKING:
    from lib.workitem.protocol import WorkItemProvider


class WorkItemClient:
    """
    User-facing client for work item operations.
    
    Wraps a WorkItemProvider and delegates all operations.
    Provides a clean, consistent API for agents.
    
    Example:
        client = WorkItemClient.from_config()
        items = client.query_work_items(WorkItemQuery(states=[WorkItemState.INBOX]))
        for item in items:
            client.add_tag(item.identity, "processing")
    """
    
    def __init__(self, provider: "WorkItemProvider"):
        """
        Initialize client with a provider.
        
        Args:
            provider: WorkItem provider instance
        """
        self._provider = provider
        self._capabilities = detect_capabilities(provider)
    
    @classmethod
    def from_config(cls, config_path: str | None = None) -> "WorkItemClient":
        """
        Create client from configuration file.
        
        Loads config and instantiates the default provider.
        
        Args:
            config_path: Optional path to config file
            
        Returns:
            Configured WorkItemClient
            
        Raises:
            ValueError: If provider not supported
        """
        config = load_provider_config(config_path)
        provider_name = config.get("default_provider", "kanboard")
        
        provider = cls._create_provider(provider_name, config)
        return cls(provider)
    
    @staticmethod
    def _create_provider(name: str, config: dict) -> "WorkItemProvider":
        """Create provider instance by name."""
        providers_config = config.get("providers", {})
        
        if name == "kanboard":
            from lib.workitem.providers.kanboard import KanboardWorkItemProvider
            provider_config = providers_config.get("kanboard", {})
            return KanboardWorkItemProvider(provider_config)
        
        # Future providers:
        # elif name == "jira":
        #     from lib.workitem.providers.jira import JiraWorkItemProvider
        #     return JiraWorkItemProvider(providers_config.get("jira", {}))
        
        raise ValueError(f"Unknown provider: {name}")
    
    @property
    def provider_name(self) -> str:
        """Name of the underlying provider."""
        return self._provider.name
    
    @property
    def capabilities(self) -> set[Capability]:
        """Set of capabilities supported by the provider."""
        return self._capabilities
    
    def has_capability(self, capability: Capability) -> bool:
        """Check if provider supports a specific capability."""
        return capability in self._capabilities
    
    # --- Read Operations ---
    
    def get_work_item(self, identity: WorkItemIdentity) -> WorkItem | None:
        """
        Fetch a single work item by identity.
        
        Args:
            identity: Work item identifier
            
        Returns:
            WorkItem if found, None otherwise
        """
        return self._provider.get_work_item(identity)
    
    def query_work_items(self, query: WorkItemQuery) -> list[WorkItem]:
        """
        Query work items with filters.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching WorkItems
        """
        return self._provider.query_work_items(query)
    
    def get_tags(self, identity: WorkItemIdentity) -> list[str]:
        """
        Get tags for a work item.
        
        Args:
            identity: Work item identifier
            
        Returns:
            List of tag names
        """
        return self._provider.get_tags(identity)
    
    # --- Write Operations ---
    
    def update_state(
        self,
        identity: WorkItemIdentity,
        new_state: WorkItemState,
    ) -> bool:
        """
        Transition work item to a new state.
        
        Args:
            identity: Work item identifier
            new_state: Target state
            
        Returns:
            True if successful
        """
        return self._provider.update_state(identity, new_state)
    
    def post_comment(
        self,
        identity: WorkItemIdentity,
        content: str,
    ) -> bool:
        """
        Add a comment to the work item.
        
        Args:
            identity: Work item identifier
            content: Comment text
            
        Returns:
            True if successful
        """
        return self._provider.post_comment(identity, content)
    
    def set_metadata(
        self,
        identity: WorkItemIdentity,
        key: str,
        value: str,
    ) -> bool:
        """
        Set a metadata field.
        
        Args:
            identity: Work item identifier
            key: Field name
            value: Field value
            
        Returns:
            True if successful
        """
        return self._provider.set_metadata(identity, key, value)
    
    def add_tag(
        self,
        identity: WorkItemIdentity,
        tag: str,
    ) -> bool:
        """
        Add a tag to the work item.
        
        Args:
            identity: Work item identifier
            tag: Tag name
            
        Returns:
            True if successful
        """
        return self._provider.add_tag(identity, tag)
    
    def remove_tag(
        self,
        identity: WorkItemIdentity,
        tag: str,
    ) -> bool:
        """
        Remove a tag from the work item.
        
        Args:
            identity: Work item identifier
            tag: Tag name
            
        Returns:
            True if successful
        """
        return self._provider.remove_tag(identity, tag)
