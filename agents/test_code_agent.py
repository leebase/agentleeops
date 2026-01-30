"""
Test Code Agent (TDD Implementer)
---------------------------------
Responsibility:
1. Read the approved TEST_PLAN.md
2. Generate actual pytest test code
3. Lock the test files (tests are now immutable)

Triggered by: Tests Approved column
Output: tests/test_{atomic_id}.py
"""

import json
import re
import base64
from pathlib import Path
from lib.llm import LLMClient
from lib.workspace import get_workspace_path, safe_write_file
from lib.syntax_guard import safe_extract_python

PROMPT_TEMPLATE = Path("prompts/test_code_prompt.txt")


def run_test_code_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int):
    """
    Executes the Test Code Generation Phase for an Atomic Story.
    Reads the approved TEST_PLAN.md and generates actual pytest code.
    """
    print(f"  [Test Code Agent] Generating test code for '{title}'...")

    # 1. Setup Workspace
    workspace = get_workspace_path(dirname)
    design_path = workspace / "DESIGN.md"
    prd_path = workspace / "prd.json"
    tests_dir = workspace / "tests"

    if not prd_path.exists():
        return {"success": False, "error": "prd.json missing. Cannot generate tests."}

    # 2. Get Atomic ID from Metadata
    try:
        meta = kb_client.get_task_metadata(task_id=task_id)
        atomic_id = meta.get("atomic_id")
        
        if not atomic_id:
            # Fallback: Try to parse from title "[atomic-id] Title"
            match = re.search(r"^\[(.*?)\]", title)
            if match:
                atomic_id = match.group(1)
            else:
                return {"success": False, "error": "Could not determine atomic_id from metadata or title."}
    except Exception as e:
        return {"success": False, "error": f"Failed to get metadata: {e}"}

    atomic_id_clean = re.sub(r"[^a-zA-Z0-9]", "_", atomic_id)

    # 3. Check for Test Plan
    test_plan_path = tests_dir / f"TEST_PLAN_{atomic_id_clean}.md"
    if not test_plan_path.exists():
        return {"success": False, "error": f"TEST_PLAN_{atomic_id_clean}.md not found. Run Tests Draft first."}

    # 4. Read Context
    try:
        design_content = design_path.read_text() if design_path.exists() else ""
        prd_data = json.loads(prd_path.read_text())
        test_plan_content = test_plan_path.read_text()
        
        # Find the specific story
        story = next((s for s in prd_data.get("stories", []) if s["id"] == atomic_id), None)
        if not story:
             return {"success": False, "error": f"Story ID '{atomic_id}' not found in prd.json"}

    except Exception as e:
        return {"success": False, "error": f"Failed to read context: {e}"}

    # 5. Prepare Prompt (include test plan for reference)
    try:
        prompt_base = PROMPT_TEMPLATE.read_text()
        prompt = prompt_base.replace("{{dirname}}", dirname)
        prompt = prompt.replace("{{atomic_id}}", atomic_id)
        prompt = prompt.replace("{{atomic_id_clean}}", atomic_id_clean)
        prompt = prompt.replace("{{story_title}}", story.get("title", ""))
        prompt = prompt.replace("{{story_json}}", json.dumps(story, indent=2))
        prompt = prompt.replace("{{design_content}}", design_content)
        # Add test plan as additional context
        prompt += f"\n\n**Approved Test Plan:**\n{test_plan_content}"
    except Exception as e:
        return {"success": False, "error": f"Failed to prepare prompt: {e}"}

    # 6. Call LLM
    print(f"  [Test Code Agent] Asking LLM to write tests/test_{atomic_id_clean}.py...")
    llm = LLMClient.from_config("config/llm.yaml", workspace=str(workspace))
    response = llm.complete(
        role="planner",  # Tests are specs, not implementation (Double-Blind Rule)
        messages=[{"role": "user", "content": prompt}],
    )
    llm_response = response.text

    # 7. Extract and Validate Code (Syntax Guard)
    code_block, syntax_error = safe_extract_python(llm_response)
    if syntax_error:
        return {"success": False, "error": f"LLM returned invalid test code: {syntax_error}"}

    # 8. Save Test Code
    try:
        test_filename = f"test_{atomic_id_clean}.py"
        test_file_path = tests_dir / test_filename
        relative_path = f"tests/{test_filename}"
        safe_write_file(workspace, relative_path, code_block)
        print(f"  [Test Code Agent] Wrote {test_file_path}")

    except Exception as e:
        return {"success": False, "error": f"Failed to save test file: {e}"}

    # 9. Attach to Kanboard
    try:
        encoded = base64.b64encode(code_block.encode()).decode()
        kb_client.execute(
            'createTaskFile',
            project_id=project_id,
            task_id=int(task_id),
            filename=test_filename,
            blob=encoded
        )
        print(f"  [Test Code Agent] Attached {test_filename} to card")
    except Exception as e:
        print(f"  [Test Code Agent] Warning: Could not attach to card: {e}")

    # 10. Post comment
    try:
        kb_client.create_comment(
            task_id=int(task_id),
            content=f"**TEST_CODE_AGENT**: Generated test file `{test_filename}` from approved test plan.\n\nTests are now locked. Move to **Ralph Loop** for implementation."
        )
    except Exception:
        pass

    return {
        "success": True,
        "test_file": str(test_file_path)
    }
