"""
WorkItem Abstraction Package

Provider-agnostic work item handling for AgentLeeOps.
Supports Kanboard out of the box, with extensibility for Jira, ADO, etc.
"""

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)
from lib.workitem.protocol import WorkItemProvider
from lib.workitem.config import load_provider_config, get_provider_config

__all__ = [
    "WorkItem",
    "WorkItemIdentity",
    "WorkItemQuery",
    "WorkItemState",
    "WorkItemProvider",
    "load_provider_config",
    "get_provider_config",
]
