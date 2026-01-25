"""
ARCHITECT_AGENT for AgentLeeOps.
Generates DESIGN.md documents from story cards.
"""

import base64
import os
from pathlib import Path
from typing import Optional

from lib.opencode import call_opencode, OpenCodeError
from lib.workspace import setup_workspace, validate_dirname


# Load prompt template
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "design_prompt.txt"


def load_prompt_template() -> str:
    """Load the design prompt template from file."""
    with open(PROMPT_TEMPLATE_PATH, 'r') as f:
        return f.read()


def generate_design(
    title: str,
    context_mode: str,
    acceptance_criteria: str,
    model: Optional[str] = None
) -> str:
    """
    Generate DESIGN.md content using OpenCode.

    Args:
        title: Story/task title
        context_mode: "NEW" or "FEATURE"
        acceptance_criteria: Acceptance criteria from card
        model: Optional model override

    Returns:
        Generated DESIGN.md content

    Raises:
        OpenCodeError: If OpenCode call fails
    """
    template = load_prompt_template()

    prompt = template.format(
        title=title,
        context_mode=context_mode,
        acceptance_criteria=acceptance_criteria
    )

    return call_opencode(prompt, model=model)


def run_architect_agent(
    task_id: str,
    title: str,
    dirname: str,
    context_mode: str,
    acceptance_criteria: str,
    kb_client=None,
    project_id: int = 1
) -> dict:
    """
    Execute the ARCHITECT_AGENT workflow.

    Steps:
    1. Validate dirname
    2. Set up workspace (NEW or FEATURE mode)
    3. Generate DESIGN.md via OpenCode
    4. Write DESIGN.md to workspace
    5. Post status comment to Kanboard card

    Args:
        task_id: Kanboard task ID
        title: Story/task title
        dirname: Project directory name
        context_mode: "NEW" or "FEATURE"
        acceptance_criteria: Acceptance criteria from card
        kb_client: Optional Kanboard client for posting comments

    Returns:
        dict with keys:
            - success: bool
            - workspace: Path to workspace (if successful)
            - design_path: Path to DESIGN.md (if successful)
            - error: Error message (if failed)
    """
    result = {
        "success": False,
        "workspace": None,
        "design_path": None,
        "error": None
    }

    def post_comment(msg):
        """Helper to post comment with error handling."""
        if kb_client:
            try:
                kb_client.create_comment(task_id=int(task_id), user_id=1, content=msg)
            except Exception:
                pass  # Best effort - don't fail workflow on comment errors

    # Step 1: Validate dirname
    if not validate_dirname(dirname):
        result["error"] = (
            f"Invalid dirname '{dirname}'. Must be lowercase, digits, "
            "and dashes only. No spaces, dots, or slashes."
        )
        post_comment(f"**ARCHITECT_AGENT Failed**\n\n{result['error']}")
        return result

    # Step 2: Set up workspace
    try:
        workspace = setup_workspace(dirname, context_mode)
        result["workspace"] = str(workspace)
    except (ValueError, RuntimeError) as e:
        result["error"] = f"Workspace setup failed: {e}"
        post_comment(f"**ARCHITECT_AGENT Failed**\n\n{result['error']}")
        return result

    # Step 3: Generate DESIGN.md
    try:
        design_content = generate_design(
            title=title,
            context_mode=context_mode,
            acceptance_criteria=acceptance_criteria
        )
    except OpenCodeError as e:
        result["error"] = f"Design generation failed: {e}"
        post_comment(f"**ARCHITECT_AGENT Failed**\n\n{result['error']}")
        return result

    # Step 4: Write DESIGN-{task_id}.md (each story gets its own design file)
    design_filename = f"DESIGN-{task_id}.md"
    design_path = workspace / design_filename
    try:
        with open(design_path, 'w') as f:
            f.write(design_content)
        result["design_path"] = str(design_path)
    except IOError as e:
        result["error"] = f"Failed to write DESIGN.md: {e}"
        post_comment(f"**ARCHITECT_AGENT Failed**\n\n{result['error']}")
        return result

    # Step 5: Attach design file to Kanboard task
    if kb_client:
        try:
            encoded = base64.b64encode(design_content.encode()).decode()
            kb_client.create_task_file(
                project_id=project_id,
                task_id=int(task_id),
                filename=design_filename,
                blob=encoded
            )
        except Exception as e:
            print(f"  Note: Could not attach file to Kanboard: {e}")

    # Step 6: Post success comment
    result["success"] = True
    comment = (
        f"**ARCHITECT_AGENT Completed**\n\n"
        f"- **Workspace**: `{workspace}`\n"
        f"- **Context Mode**: {context_mode}\n"
        f"- **Generated**: `{design_filename}`\n\n"
        f"Review the design and move to **3. Design Approved** when ready."
    )
    post_comment(comment)

    return result
