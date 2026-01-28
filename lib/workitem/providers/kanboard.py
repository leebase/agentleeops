"""
Kanboard WorkItem Provider.

Implements WorkItemProvider protocol for Kanboard backend.
"""

from datetime import datetime
from typing import Any

from kanboard import Client

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)
from lib.workitem.config import get_provider_config, load_provider_config


# Default column-to-state mapping (matches AgentLeeOps 10-column workflow)
DEFAULT_COLUMN_MAP = {
    "1. Inbox": WorkItemState.INBOX,
    "2. Design Draft": WorkItemState.DESIGN_DRAFT,
    "3. Design Approved": WorkItemState.DESIGN_APPROVED,
    "4. Planning Draft": WorkItemState.PLANNING_DRAFT,
    "5. Plan Approved": WorkItemState.PLAN_APPROVED,
    "6. Tests Draft": WorkItemState.TESTS_DRAFT,
    "7. Tests Approved": WorkItemState.TESTS_APPROVED,
    "8. Ralph Loop": WorkItemState.IMPLEMENTATION,
    "9. Final Review": WorkItemState.FINAL_REVIEW,
    "10. Done": WorkItemState.DONE,
}


class KanboardWorkItemProvider:
    """
    WorkItemProvider implementation for Kanboard.
    
    Wraps the kanboard Python client and translates between
    Kanboard's task/column model and the WorkItem abstraction.
    """
    
    def __init__(self, config: dict | None = None):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider config dict. If None, loads from config file.
                    Expected keys: url, user, token, project_id, column_mapping
        """
        if config is None:
            config = get_provider_config("kanboard")
        
        self._config = config
        self._url = config.get("url", "http://localhost:188/jsonrpc.php")
        self._user = config.get("user", "jsonrpc")
        self._token = config.get("token", "")
        self._default_project_id = config.get("project_id", 1)
        
        # Build column mapping
        self._column_map = self._build_column_map(
            config.get("column_mapping", {})
        )
        
        # Lazy client initialization
        self._client: Client | None = None
        
        # Cache for column lookups
        self._column_cache: dict[int, dict] = {}
    
    def _build_column_map(self, config_mapping: dict) -> dict[str, WorkItemState]:
        """Build column-to-state map from config or defaults."""
        if not config_mapping:
            return DEFAULT_COLUMN_MAP.copy()
        
        result = {}
        for col_name, state_value in config_mapping.items():
            try:
                result[col_name] = WorkItemState(state_value)
            except ValueError:
                # Unknown state value, skip
                pass
        
        return result if result else DEFAULT_COLUMN_MAP.copy()
    
    @property
    def client(self) -> Client:
        """Get or create Kanboard client (lazy initialization)."""
        if self._client is None:
            self._client = Client(self._url, self._user, self._token)
        return self._client
    
    @property
    def name(self) -> str:
        """Provider identifier."""
        return "kanboard"
    
    # --- Read Operations ---
    
    def get_work_item(self, identity: WorkItemIdentity) -> WorkItem | None:
        """
        Fetch a single work item by identity.
        
        Args:
            identity: Work item identifier (external_id is Kanboard task_id)
            
        Returns:
            WorkItem if found, None otherwise
        """
        try:
            task_id = int(identity.external_id)
            task = self.client.get_task(task_id=task_id)
            
            if not task:
                return None
            
            return self._task_to_workitem(task)
        
        except Exception:
            return None
    
    def query_work_items(self, query: WorkItemQuery) -> list[WorkItem]:
        """
        Query work items with optional filters.
        
        Args:
            query: Query parameters (project_id, states, tags)
            
        Returns:
            List of matching WorkItems
        """
        try:
            project_id = int(query.project_id) if query.project_id else self._default_project_id
            tasks = self.client.get_all_tasks(project_id=project_id)
            
            if not tasks:
                return []
            
            # Convert to WorkItems
            items = []
            for task in tasks:
                item = self._task_to_workitem(task, project_id=project_id)
                if item:
                    items.append(item)
            
            # Apply state filter
            if query.states:
                items = [i for i in items if i.state in query.states]
            
            # Apply tag filter
            if query.tags:
                items = [
                    i for i in items 
                    if all(tag in i.tags for tag in query.tags)
                ]
            
            # Apply limit
            return items[:query.limit]
        
        except Exception:
            return []
    
    def get_tags(self, identity: WorkItemIdentity) -> list[str]:
        """
        Get all tags for a work item.
        
        Args:
            identity: Work item identifier
            
        Returns:
            List of tag names
        """
        try:
            task_id = int(identity.external_id)
            tags = self.client.get_task_tags(task_id=task_id)
            
            if not tags:
                return []
            
            # Kanboard returns dict {tag_id: tag_name}
            if isinstance(tags, dict):
                return list(tags.values())
            
            # Or might return list of dicts
            if isinstance(tags, list):
                if tags and isinstance(tags[0], dict):
                    return [t.get("name", "") for t in tags if t.get("name")]
                return [str(t) for t in tags]
            
            return []
        
        except Exception:
            return []
    
    # --- Helpers ---
    
    def _get_column_name(self, column_id: int, project_id: int) -> str:
        """Get column name from ID, using cache."""
        cache_key = project_id
        
        if cache_key not in self._column_cache:
            try:
                columns = self.client.get_columns(project_id=project_id)
                self._column_cache[cache_key] = {
                    int(c["id"]): c["title"] for c in columns
                }
            except Exception:
                return ""
        
        return self._column_cache[cache_key].get(int(column_id), "")
    
    def _column_to_state(self, column_name: str) -> WorkItemState:
        """Map column name to WorkItemState."""
        return self._column_map.get(column_name, WorkItemState.UNKNOWN)
    
    def _task_to_workitem(
        self, 
        task: dict, 
        project_id: int | None = None
    ) -> WorkItem | None:
        """
        Convert Kanboard task dict to WorkItem.
        
        Args:
            task: Kanboard task dictionary
            project_id: Project ID for column lookup
            
        Returns:
            WorkItem or None on error
        """
        try:
            task_id = str(task.get("id", ""))
            if not task_id:
                return None
            
            # Build identity
            url = f"{self._url.replace('/jsonrpc.php', '')}/?controller=TaskViewController&action=show&task_id={task_id}"
            identity = WorkItemIdentity(
                provider="kanboard",
                external_id=task_id,
                url=url,
            )
            
            # Determine state from column
            proj_id = project_id or int(task.get("project_id", self._default_project_id))
            column_id = int(task.get("column_id", 0))
            column_name = self._get_column_name(column_id, proj_id)
            state = self._column_to_state(column_name)
            
            # Get tags
            tags = self.get_tags(identity)
            
            # Parse task fields from metadata or description
            fields = self._get_task_fields(task)
            
            # Parse timestamps
            created_at = self._parse_timestamp(task.get("date_creation"))
            updated_at = self._parse_timestamp(task.get("date_modification"))
            
            # Get status metadata
            status = self._get_status_metadata(int(task_id))
            
            return WorkItem(
                identity=identity,
                title=task.get("title", ""),
                description=task.get("description", "") or "",
                state=state,
                dirname=fields.get("dirname"),
                context_mode=fields.get("context_mode"),
                acceptance_criteria=fields.get("acceptance_criteria"),
                complexity=fields.get("complexity"),
                agent_status=status.get("agent_status"),
                current_phase=status.get("current_phase"),
                tags=tags,
                created_at=created_at,
                updated_at=updated_at,
                metadata={
                    "project_id": proj_id,
                    "column_id": column_id,
                    "column_name": column_name,
                },
            )
        
        except Exception:
            return None
    
    def _get_task_fields(self, task: dict) -> dict:
        """
        Extract task fields from metadata or description.
        
        Uses similar logic to lib/task_fields.py but without the validation.
        """
        task_id = task.get("id")
        
        # Try metadata first (MetaMagik custom fields)
        try:
            metadata = self.client.execute("getTaskMetadata", task_id=task_id)
            if metadata and "dirname" in metadata:
                return {
                    "dirname": metadata.get("dirname"),
                    "context_mode": str(metadata.get("context_mode", "NEW")).upper(),
                    "acceptance_criteria": metadata.get("acceptance_criteria", ""),
                    "complexity": metadata.get("complexity"),
                }
        except Exception:
            pass
        
        # Fallback: parse YAML from description
        return self._parse_yaml_description(task.get("description", "") or "")
    
    def _parse_yaml_description(self, description: str) -> dict:
        """Parse YAML-style task description for fields."""
        import re
        
        data: dict[str, Any] = {}
        if not description:
            return data
        
        # Parse dirname
        dirname_match = re.search(r'dirname:\s*(.+)', description)
        if dirname_match:
            data['dirname'] = dirname_match.group(1).strip()
        
        # Parse context_mode
        mode_match = re.search(r'context_mode:\s*(.+)', description)
        if mode_match:
            data['context_mode'] = mode_match.group(1).strip().upper()
        else:
            data['context_mode'] = 'NEW'
        
        # Parse acceptance_criteria (simplified)
        ac_match = re.search(
            r'acceptance_criteria:\s*\|?\s*\n((?:[ \t]+.+\n?)+)',
            description,
            re.MULTILINE
        )
        if ac_match:
            data['acceptance_criteria'] = ac_match.group(1).strip()
        
        # Parse complexity
        complexity_match = re.search(r'complexity:\s*(.+)', description)
        if complexity_match:
            data['complexity'] = complexity_match.group(1).strip().upper()
        
        return data
    
    def _get_status_metadata(self, task_id: int) -> dict:
        """Get agent status metadata for task."""
        try:
            metadata = self.client.execute("getTaskMetadata", task_id=task_id)
            if metadata:
                return {
                    "agent_status": metadata.get("agent_status", ""),
                    "current_phase": metadata.get("current_phase", ""),
                }
        except Exception:
            pass
        return {"agent_status": "", "current_phase": ""}
    
    def _parse_timestamp(self, ts: Any) -> datetime | None:
        """Parse Unix timestamp to datetime."""
        if not ts:
            return None
        try:
            return datetime.fromtimestamp(int(ts))
        except (ValueError, TypeError, OSError):
            return None
