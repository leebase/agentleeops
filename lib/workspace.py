"""
Workspace management for AgentLeeOps.
Handles creation and setup of project workspaces based on context mode.
"""

import subprocess
from pathlib import Path


def get_workspace_path(dirname: str) -> Path:
    """Get the path to a workspace directory."""
    return Path.home() / "projects" / dirname


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
