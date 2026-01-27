"""
Task field handling via Kanboard metadata API.

This module provides unified access to task fields, supporting both:
1. Modern path: MetaMagik custom fields via Kanboard metadata API
2. Legacy path: YAML parsing from task description (backwards compatibility)
"""

import re
from typing import Any, Optional

# Schema for task fields with their defaults
FIELD_SCHEMA = {
    "dirname": {"required": True, "default": None},
    "context_mode": {"required": False, "default": "NEW"},
    "acceptance_criteria": {"required": False, "default": ""},
    "complexity": {"required": False, "default": None},
}

# Status fields managed by agents (not user-editable)
STATUS_FIELDS = ["agent_status", "current_phase"]


class TaskFieldError(Exception):
    """Raised when required task fields are missing or invalid."""
    pass


def get_task_fields(kb_client: Any, task_id: int) -> dict:
    """
    Get task fields from Kanboard metadata.
    Falls back to YAML parsing for backwards compatibility.

    Args:
        kb_client: Kanboard client instance
        task_id: Task ID to fetch fields for

    Returns:
        Dict with dirname, context_mode, acceptance_criteria, complexity

    Raises:
        TaskFieldError: If required fields are missing or invalid
    """
    # Try metadata first (MetaMagik custom fields)
    # MetaMagik uses getTaskMetadata, not getAllTaskMetadata
    try:
        metadata = kb_client.execute('getTaskMetadata', task_id=task_id)
    except Exception:
        metadata = None

    if metadata and "dirname" in metadata:
        # Modern path: use metadata from MetaMagik
        fields = {}
        for key, schema in FIELD_SCHEMA.items():
            value = metadata.get(key)
            # Use default if value is empty or None
            if not value:
                value = schema["default"]
            # Normalize context_mode to uppercase
            if key == "context_mode" and value:
                value = str(value).upper()
            fields[key] = value
    else:
        # Fallback: parse YAML from description
        task = kb_client.get_task(task_id=task_id)
        description = task.get("description", "") if task else ""
        fields = parse_yaml_description(description)

    # Validate
    is_valid, error = validate_task_fields(fields)
    if not is_valid:
        raise TaskFieldError(error)

    return fields


def update_status(kb_client: Any, task_id: int, **kwargs) -> bool:
    """
    Update agent status fields in task metadata.

    Args:
        kb_client: Kanboard client instance
        task_id: Task ID to update
        **kwargs: Status fields to update (agent_status, current_phase)

    Returns:
        True if update succeeded, False otherwise
    """
    # Filter to only valid status fields
    valid_keys = {k: v for k, v in kwargs.items() if k in STATUS_FIELDS}
    if not valid_keys:
        return False

    try:
        # Save each metadata key individually
        for key, value in valid_keys.items():
            kb_client.save_task_metadata(
                task_id=task_id,
                name=key,
                value=str(value)
            )
        return True
    except Exception:
        return False


def get_status(kb_client: Any, task_id: int) -> dict:
    """
    Get agent status fields from task metadata.

    Args:
        kb_client: Kanboard client instance
        task_id: Task ID to fetch status for

    Returns:
        Dict with agent_status, current_phase (may be empty)
    """
    try:
        metadata = kb_client.execute('getTaskMetadata', task_id=task_id)
        if metadata:
            return {k: metadata.get(k, "") for k in STATUS_FIELDS}
    except Exception:
        pass
    return {k: "" for k in STATUS_FIELDS}


def parse_yaml_description(description: str) -> dict:
    """
    Parse YAML-style card description (legacy format).

    Expected format:
        dirname: my-project-name
        context_mode: NEW
        acceptance_criteria: |
          - Condition 1
          - Condition 2

    Args:
        description: Task description text

    Returns:
        Dict with parsed fields (may be empty)
    """
    data = {}
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
        data['context_mode'] = 'NEW'  # Default

    # Parse acceptance_criteria (multiline)
    # Look for "acceptance_criteria:" followed by a pipe or content
    ac_match = re.search(
        r'acceptance_criteria:\s*\|?\s*\n((?:[ \t]+.+\n?)+)',
        description,
        re.MULTILINE
    )
    if ac_match:
        # Dedent the criteria
        criteria = ac_match.group(1)
        # Remove common leading whitespace
        lines = criteria.split('\n')
        if lines:
            # Find minimum indentation
            min_indent = float('inf')
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)
            if min_indent < float('inf'):
                criteria = '\n'.join(
                    line[int(min_indent):] if len(line) > min_indent else line.strip()
                    for line in lines
                )
        data['acceptance_criteria'] = criteria.strip()
    else:
        data['acceptance_criteria'] = ''

    # Parse complexity (optional)
    complexity_match = re.search(r'complexity:\s*(.+)', description)
    if complexity_match:
        data['complexity'] = complexity_match.group(1).strip().upper()
    else:
        data['complexity'] = None

    return data


def validate_task_fields(fields: dict) -> tuple:
    """
    Validate required fields and dirname format.

    Args:
        fields: Dict of task fields to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    # Check required field: dirname
    if not fields.get("dirname"):
        return False, "Missing required field: dirname"

    dirname = fields["dirname"]

    # Validate dirname format: lowercase, digits, dashes only, no leading dot
    if not re.match(r'^[a-z0-9][a-z0-9-]*$', dirname):
        return False, (
            f"Invalid dirname '{dirname}': must be lowercase letters, "
            "digits, and dashes only, cannot start with dash"
        )

    # No slashes or dots allowed
    if '/' in dirname or '.' in dirname:
        return False, (
            f"Invalid dirname '{dirname}': cannot contain slashes or dots"
        )

    # Validate context_mode if present
    context_mode = fields.get("context_mode", "NEW")
    if context_mode:
        context_mode = str(context_mode).upper()
        if context_mode not in ("NEW", "FEATURE"):
            return False, (
                f"Invalid context_mode '{context_mode}': "
                "must be 'NEW' or 'FEATURE'"
            )

    # Validate complexity if present
    complexity = fields.get("complexity")
    if complexity:
        complexity = str(complexity).upper()
        if complexity not in ("S", "M", "L", "XL"):
            return False, (
                f"Invalid complexity '{complexity}': "
                "must be 'S', 'M', 'L', or 'XL'"
            )

    return True, ""


# --- Tag Helper Functions ---
# Used by orchestrator and webhook_server for idempotency tracking

def get_task_tags(kb_client: Any, task_id: int) -> list:
    """
    Get tags for a task.

    Args:
        kb_client: Kanboard client instance
        task_id: Task ID to fetch tags for

    Returns:
        List of tag names (strings)
    """
    try:
        tags = kb_client.get_task_tags(task_id=task_id)
        if not tags:
            return []
        if isinstance(tags, dict):
            return [str(value) for value in tags.values()]
        if isinstance(tags, list):
            if tags and isinstance(tags[0], dict):
                return [tag.get('name') for tag in tags if tag.get('name')]
            return [str(tag) for tag in tags]
        return []
    except Exception:
        return []


def add_task_tag(kb_client: Any, project_id: int, task_id: int, tag_name: str) -> None:
    """
    Add a tag to a task (creates tag if needed).

    Args:
        kb_client: Kanboard client instance
        project_id: Project ID
        task_id: Task ID
        tag_name: Tag name to add
    """
    try:
        project_id = int(project_id)
        task_id = int(task_id)
        existing = get_task_tags(kb_client, task_id)
        if tag_name in existing:
            return
        updated = existing + [tag_name]
        kb_client.set_task_tags(project_id=project_id, task_id=task_id, tags=updated)
    except Exception as e:
        from lib.logger import get_logger
        log = get_logger("TAGS")
        log.warning(f"Could not add tag '{tag_name}': {e}", task_id=task_id)


def has_tag(tags: list, tag_name: str) -> bool:
    """
    Check if a tag is in the tags list.

    Args:
        tags: List of tag names
        tag_name: Tag name to check for

    Returns:
        True if tag is present, False otherwise
    """
    return tag_name in tags
