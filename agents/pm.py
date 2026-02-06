import json
import os
from pathlib import Path
from lib.llm import LLMClient
from lib.task_fields import get_task_fields
from lib.workspace import get_workspace_path, safe_write_file
from lib.syntax_guard import safe_extract_json

PROMPT_TEMPLATE = Path("prompts/planning_prompt.txt")
MAX_PM_RETRIES = 3
PM_MAX_TOKENS = 8000

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

    # 4-5. Call LLM + Extract/Validate JSON with retries
    print("  [PM Agent] Generating PRD via LLM...")
    llm = LLMClient.from_config("config/llm.yaml", workspace=workspace)
    prd_data = None
    last_error = ""
    last_response = ""

    for attempt in range(1, MAX_PM_RETRIES + 1):
        try:
            response = llm.complete(
                role="planner",
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
                max_tokens=PM_MAX_TOKENS
            )
            llm_response = response.text
            last_response = llm_response
        except Exception as e:
            last_error = f"LLM call failed: {e}"
            continue

        clean_json, syntax_error = safe_extract_json(llm_response)
        if syntax_error:
            last_error = f"Invalid JSON on attempt {attempt}: {syntax_error}"
            continue

        try:
            parsed = json.loads(clean_json)

            # Basic Schema Validation
            if "stories" not in parsed or not isinstance(parsed["stories"], list):
                raise ValueError("JSON missing 'stories' list")

            if not parsed["stories"]:
                raise ValueError("PRD has no stories")

            prd_data = parsed
            break
        except ValueError as e:
            last_error = f"Invalid PRD Schema on attempt {attempt}: {e}"

    if prd_data is None:
        error_file = workspace / "prd_error.txt"
        if last_response:
            error_file.write_text(last_response)
        return {"success": False, "error": f"Failed PRD generation after {MAX_PM_RETRIES} attempts. {last_error}. Saved to {error_file}"}

    # 6. Save prd.json
    try:
        # format nicely
        safe_write_file(workspace, "prd.json", json.dumps(prd_data, indent=2))
        print(f"  [PM Agent] Saved {prd_path}")
    except Exception as e:
        return {"success": False, "error": f"Failed to write prd.json: {e}"}

    # 7. Attach to Kanboard
    try:
        import base64
        with open(prd_path, 'r') as f:
            content = f.read()
        encoded = base64.b64encode(content.encode()).decode()
        
        # Check if file already attached, remove if so (to allow updates)
        existing_files = kb_client.execute('getAllTaskFiles', task_id=int(task_id))
        for f in (existing_files or []):
            if f.get('name') == "prd.json":
                kb_client.execute('removeTaskFile', file_id=int(f['id']))

        # Upload
        kb_client.execute(
            'createTaskFile',
            project_id=project_id,
            task_id=int(task_id),
            filename="prd.json",
            blob=encoded
        )
        
        # Add comment
        kb_client.create_comment(
            task_id=int(task_id),
            content=f"**PM_AGENT**: Generated Implementation Plan (`prd.json`) with {len(prd_data['stories'])} stories.\n\nPlease review in the 'Files' section."
        )

    except Exception as e:
        print(f"  [PM Agent] Warning: Failed to attach file to Kanboard: {e}")

    return {
        "success": True,
        "prd_path": str(prd_path),
        "story_count": len(prd_data['stories'])
    }
