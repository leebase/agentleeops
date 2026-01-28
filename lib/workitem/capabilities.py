"""
WorkItem provider capabilities.

Capability detection for determining what operations a provider supports.
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.workitem.protocol import WorkItemProvider


class Capability(Enum):
    """
    Capabilities that a WorkItem provider may support.
    
    Used for graceful degradation when a provider doesn't support
    certain operations (e.g., a read-only provider).
    """
    READ = "read"                    # get_work_item, query_work_items
    WRITE_STATE = "write_state"      # update_state
    WRITE_COMMENT = "write_comment"  # post_comment
    WRITE_METADATA = "write_metadata"  # set_metadata
    WRITE_TAGS = "write_tags"        # add_tag, remove_tag, get_tags


# Method names for each capability
CAPABILITY_METHODS = {
    Capability.READ: ["get_work_item", "query_work_items"],
    Capability.WRITE_STATE: ["update_state"],
    Capability.WRITE_COMMENT: ["post_comment"],
    Capability.WRITE_METADATA: ["set_metadata"],
    Capability.WRITE_TAGS: ["add_tag", "remove_tag", "get_tags"],
}


def detect_capabilities(provider: "WorkItemProvider") -> set[Capability]:
    """
    Detect which capabilities a provider supports.
    
    Checks for the existence of required methods on the provider.
    
    Args:
        provider: WorkItem provider instance
        
    Returns:
        Set of supported Capability values
    """
    capabilities = set()
    
    for capability, methods in CAPABILITY_METHODS.items():
        # Check if all required methods exist and are callable
        has_all = all(
            hasattr(provider, method) and callable(getattr(provider, method))
            for method in methods
        )
        if has_all:
            capabilities.add(capability)
    
    return capabilities


def has_capability(provider: "WorkItemProvider", capability: Capability) -> bool:
    """
    Check if a provider supports a specific capability.
    
    Args:
        provider: WorkItem provider instance
        capability: Capability to check
        
    Returns:
        True if provider supports the capability
    """
    return capability in detect_capabilities(provider)
