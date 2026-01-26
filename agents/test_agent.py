"""
Test Agent (TDD Specialist)
---------------------------
Responsibility:
1. Read prd.json and DESIGN.md
2. Identify specific atomic story from task metadata
3. Generate a FAILING test file (tests/test_xyz.py)
4. Attach to Kanboard
"""

import json
import re
from pathlib import Path
from lib.opencode import run_opencode
from lib.task_fields import get_task_fields
from lib.workspace import get_workspace_path

PROMPT_TEMPLATE = Path("prompts/test_prompt.txt")

def run_test_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int):
    """
    Executes the Test Generation Phase for an Atomic Story.
    """
    print(f"  [Test Agent] Generating tests for '{title}'...")

    # 1. Setup Workspace
    workspace = get_workspace_path(dirname)
    design_path = workspace / "DESIGN.md"
    prd_path = workspace / "prd.json"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    if not prd_path.exists():
        return {"success": False, "error": "prd.json missing. Cannot generate tests."}

    # 2. Get Atomic ID from Metadata
    try:
        # We need the atomic_id to know WHICH story to test
        # The Spawner Agent saved this as metadata 'atomic_id'
        # But our lib/task_fields.py mostly gets standard fields.
        # We can use the generic kb_client to get custom metadata.
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

    # 3. Read Context
    try:
        design_content = design_path.read_text()
        prd_data = json.loads(prd_path.read_text())
        
        # Find the specific story
        story = next((s for s in prd_data.get("stories", []) if s["id"] == atomic_id), None)
        if not story:
             return {"success": False, "error": f"Story ID '{atomic_id}' not found in prd.json"}

    except Exception as e:
        return {"success": False, "error": f"Failed to read context: {e}"}

    # 4. Prepare Prompt
    try:
        prompt_base = PROMPT_TEMPLATE.read_text()
        prompt = prompt_base.replace("{{dirname}}", dirname)
        prompt = prompt.replace("{{atomic_id}}", atomic_id)
        # Clean atomic_id for filename (dots/dashes to underscores)
        atomic_id_clean = re.sub(r"[^a-zA-Z0-9]", "_", atomic_id)
        prompt = prompt.replace("{{atomic_id_clean}}", atomic_id_clean)
        prompt = prompt.replace("{{story_title}}", story.get("title", ""))
        prompt = prompt.replace("{{story_json}}", json.dumps(story, indent=2))
        prompt = prompt.replace("{{design_content}}", design_content)
    except Exception as e:
        return {"success": False, "error": f"Failed to prepare prompt: {e}"}

    # 5. Call LLM
    print(f"  [Test Agent] Asking LLM to write tests/test_{atomic_id_clean}.py...")
    llm_response = run_opencode(prompt, model="gpt-4o")

    # 6. Extract Code
    try:
        code_block = llm_response
        if "```python" in code_block:
            code_block = code_block.split("```python")[1].split("```")[0].strip()
        elif "```" in code_block:
            code_block = code_block.split("```")[1].split("```")[0].strip()
        
        test_filename = f"test_{atomic_id_clean}.py"
        test_file_path = tests_dir / test_filename
        test_file_path.write_text(code_block)
        print(f"  [Test Agent] Wrote {test_file_path}")

    except Exception as e:
        return {"success": False, "error": f"Failed to save test file: {e}"}

    # 7. Attach to Kanboard (optional, code is in repo, but maybe link it?)
    # For now, just comment.
    
    return {
        "success": True,
        "test_file": str(test_file_path)
    }
