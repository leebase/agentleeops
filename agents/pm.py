import json
import os
from pathlib import Path
from lib.llm import LLMClient
from lib.task_fields import get_task_fields
from lib.workspace import get_workspace_path, safe_write_file
from lib.syntax_guard import safe_extract_json

PROMPT_TEMPLATE = Path("prompts/planning_prompt.txt")

def run_pm_agent(task_id: str, title: str, dirname: str, context_mode: str, acceptance_criteria: str, kb_client, project_id: int):
    """
    Executes the Planning Phase.
    """
    print(f"  [PM Agent] Starting planning for '{title}'...")

    # 1. Setup Workspace Paths
    workspace = get_workspace_path(dirname)
    design_path = workspace / "DESIGN.md"
    prd_path = workspace / "prd.json"

    if not design_path.exists():
        return {
            "success": False,
            "error": f"DESIGN.md not found at {design_path}. Cannot plan without design."
        }

    # 2. Read DESIGN.md
    try:
        design_content = design_path.read_text()
    except Exception as e:
        return {"success": False, "error": f"Failed to read DESIGN.md: {e}"}

    # 3. Prepare Prompt
    try:
        prompt_base = PROMPT_TEMPLATE.read_text()
        prompt = prompt_base.replace("{{dirname}}", dirname)
        prompt = prompt.replace("{{design_content}}", design_content)
        prompt = prompt.replace("{{acceptance_criteria}}", acceptance_criteria)
    except Exception as e:
        return {"success": False, "error": f"Failed to load prompt template: {e}"}

    # 4. Call LLM (New LLM Client)
    print("  [PM Agent] Generating PRD via LLM...")
    try:
        llm = LLMClient.from_config("config/llm.yaml", workspace=workspace)
        response = llm.complete(
            role="planner",
            messages=[{"role": "user", "content": prompt}],
            json_mode=True
        )
        llm_response = response.text
    except Exception as e:
        return {"success": False, "error": f"LLM call failed: {e}"}

    # 5. Extract and Validate JSON (Syntax Guard)
    clean_json, syntax_error = safe_extract_json(llm_response)
    if syntax_error:
        # Save raw output for debugging
        error_file = workspace / "prd_error.txt"
        error_file.write_text(llm_response)
        return {"success": False, "error": f"LLM generated invalid JSON. Saved to {error_file}. {syntax_error}"}

    try:
        prd_data = json.loads(clean_json)

        # Basic Schema Validation
        if "stories" not in prd_data or not isinstance(prd_data["stories"], list):
            raise ValueError("JSON missing 'stories' list")

        if not prd_data["stories"]:
            raise ValueError("PRD has no stories")

    except ValueError as e:
        return {"success": False, "error": f"Invalid PRD Schema: {e}"}

    # 6. Save prd.json
    try:
        # format nicely
        safe_write_file(workspace, "prd.json", json.dumps(prd_data, indent=2))
        print(f"  [PM Agent] Saved {prd_path}")
    except Exception as e:
        return {"success": False, "error": f"Failed to write prd.json: {e}"}

    # 7. Attach to Kanboard
    try:
        # Check if file already attached, remove if so (to allow updates)
        existing_files = kb_client.get_task_files(task_id=task_id)
        for f in existing_files:
            if f['name'] == "prd.json":
                kb_client.remove_task_file(task_id=task_id, file_id=f['id'])

        # Upload
        with open(prd_path, 'rb') as f:
            kb_client.create_task_file(
                task_id=task_id,
                project_id=project_id,
                name="prd.json",
                file=f
            )
        
        # Add comment
        kb_client.create_comment(
            task_id=task_id,
            content=f"**PM_AGENT**: Generated Implementation Plan (`prd.json`) with {len(prd_data['stories'])} stories.\n\nPlease review in the 'Files' section."
        )

    except Exception as e:
        print(f"  [PM Agent] Warning: Failed to attach file to Kanboard: {e}")

    return {
        "success": True,
        "prd_path": str(prd_path),
        "story_count": len(prd_data['stories'])
    }
