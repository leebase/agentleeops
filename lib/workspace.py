"""
Workspace management for AgentLeeOps.
Handles creation and setup of project workspaces based on context mode.
Enforces Ratchet Governance for file writes.
"""

import subprocess
import os
from pathlib import Path
from lib.ratchet import check_write_permission

def get_workspace_path(dirname: str) -> Path:
    """Get the path to a workspace directory."""
    return Path.home() / "projects" / dirname

def safe_write_file(workspace: Path, relative_path: str, content: str, force: bool = False):
    """
    Write content to a file, strictly enforcing the Ratchet Guard.
    
    Args:
        workspace: Base workspace path
        relative_path: Path relative to workspace (e.g., "DESIGN.md")
        content: String content to write
        force: If True, bypass checks (Use with caution!)
        
    Raises:
        PermissionError: If file is LOCKED.
    """
    full_path = workspace / relative_path
    
    # Ratchet Check
    if not force and full_path.exists():
        if not check_write_permission(workspace, relative_path):
            raise PermissionError(f"RATCHET GUARD: {relative_path} is LOCKED. Cannot overwrite.")

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)

def setup_workspace(dirname: str, context_mode: str) -> Path:
    """
    Set up a workspace based on context mode.

    Args:
        dirname: Project directory name (lowercase, digits, dashes only)
        context_mode: Either "NEW" or "FEATURE"

    Returns:
        Path to the workspace directory

    Raises:
        ValueError: If context_mode is invalid or FEATURE workspace doesn't exist
    """
    path = Path.home() / "projects" / dirname

    if context_mode == "NEW":
        path.mkdir(parents=True, exist_ok=True)

        # Initialize git repo if not already initialized
        git_dir = path / ".git"
        if not git_dir.exists():
            result = subprocess.run(
                ["git", "init"],
                cwd=path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to init git repo: {result.stderr}")
        
        # Init Ratchet
        ratchet_dir = path / ".agentleeops"
        ratchet_dir.mkdir(exist_ok=True)

        return path

    elif context_mode == "FEATURE":
        if not path.exists():
            raise ValueError(
                f"Workspace {path} does not exist for FEATURE mode. "
                "Use NEW mode to create a new project."
            )
        return path

    else:
        raise ValueError(
            f"Invalid context_mode: {context_mode}. Must be 'NEW' or 'FEATURE'."
        )


def create_feature_branch(workspace: Path, task_id: str, dirname: str) -> str:
    """
    Create a feature branch for FEATURE mode.

    Args:
        workspace: Path to the workspace
        task_id: Kanboard task ID
        dirname: Project directory name

    Returns:
        Branch name that was created
    """
    branch_name = f"feat/{task_id}-{dirname}"

    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=workspace,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # Branch might already exist, try to check it out
        result = subprocess.run(
            ["git", "checkout", branch_name],
            cwd=workspace,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create/checkout branch: {result.stderr}")

    return branch_name


def validate_dirname(dirname: str) -> bool:
    """
    Validate dirname follows naming rules.
    Rules: lowercase, digits and dashes only, no spaces, no leading dot,
    no slashes, no periods.

    Args:
        dirname: Directory name to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    if not dirname:
        return False

    # Must not start with a dot
    if dirname.startswith('.'):
        return False

    # Must only contain lowercase letters, digits, and dashes
    if not re.match(r'^[a-z0-9-]+$', dirname):
        return False

    return True