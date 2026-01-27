"""
Ralph Coder (The Loop)
----------------------
Responsibility:
1. Context-Reset TDD Loop
2. Run specific atomic test
3. If fail: Read code, Generate Fix, Commit, Retry
4. If pass: Push, Done
5. ENFORCES TEST INTEGRITY: Forbidden from modifying tests.
"""

import subprocess
import time
import re
from pathlib import Path
from lib.opencode import run_opencode
from lib.task_fields import get_task_fields
from lib.workspace import get_workspace_path, safe_write_file
from lib.ratchet import verify_integrity

PROMPT_TEMPLATE = Path("prompts/ralph_prompt.txt")
MAX_RETRIES = 5

def verify_no_test_changes(workspace: Path):
    """
    Ensure no files in tests/ are staged for commit.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], 
        cwd=workspace, 
        capture_output=True, 
        text=True
    )
    staged_files = result.stdout.splitlines()
    for f in staged_files:
        if f.startswith("tests/"):
            return False, f
    return True, None

def run_ralph_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int):
    """
    Executes the Ralph Loop with strict integrity guards.
    """
    print(f"  [Ralph] Starting loop for '{title}'...")

    workspace = get_workspace_path(dirname)
    
    # 1. Identify Context (Atomic ID)
    try:
        meta = kb_client.get_task_metadata(task_id=task_id)
        atomic_id = meta.get("atomic_id")
        if not atomic_id:
             # Fallback parsing
             match = re.search(r"^\[(.*?)\]", title)
             if match:
                atomic_id = match.group(1)
             else:
                return {"success": False, "error": "Missing atomic_id"}
    except Exception:
        return {"success": False, "error": "Metadata error"}

    # Clean ID
    atomic_id_clean = re.sub(r"[^a-zA-Z0-9]", "_", atomic_id)
    test_rel_path = f"tests/test_{atomic_id_clean}.py"
    test_file = workspace / test_rel_path
    
    # 1.1 Integrity Guard: Verify test file hash against Ratchet
    if not verify_integrity(workspace, test_rel_path):
        return {
            "success": False, 
            "error": f"INTEGRITY FAILURE: {test_rel_path} has been modified or does not match approved hash."
        }

    # Infer source file
    src_dir = workspace / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    source_filename = f"{dirname.replace('-', '_')}.py"
    source_file_rel = f"src/{source_filename}"
    source_file = src_dir / source_filename
    
    if not source_file.exists():
        safe_write_file(workspace, source_file_rel, "") # Touch

    # 2. Git Branch
    branch_name = f"feat/{task_id}-{atomic_id_clean}"
    try:
        # Check if branch exists, checkout, or create
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=workspace, capture_output=True)
        subprocess.run(["git", "checkout", branch_name], cwd=workspace, capture_output=True)
    except Exception as e:
        return {"success": False, "error": f"Git error: {e}"}

    # 3. The Loop
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"    Loop Iteration {attempt}/{MAX_RETRIES}...")

        # A. Run Test
        cmd = ["python3", "-m", "pytest", str(test_file)]
        result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("    GREEN BAR! Tests Passed.")
            # Commit success - STRICT STAGING
            subprocess.run(["git", "add", source_file_rel], cwd=workspace, capture_output=True)
            
            # Integrity Check before commit
            ok, offending_file = verify_no_test_changes(workspace)
            if not ok:
                return {"success": False, "error": f"INTEGRITY VIOLATION: Agent tried to commit changes to {offending_file}"}
                
            subprocess.run(["git", "commit", "-m", f"Refactor: {atomic_id} passed"], cwd=workspace, capture_output=True)
            return {"success": True, "iterations": attempt}

        # B. RED BAR - Analyze and Fix
        print("    RED BAR. Generating fix...")
        test_output = result.stdout + result.stderr
        current_code = source_file.read_text()

        # Prepare Prompt
        prompt_base = PROMPT_TEMPLATE.read_text()
        prompt = prompt_base.replace("{{atomic_id}}", atomic_id)
        prompt = prompt.replace("{{source_file}}", source_file.name)
        prompt = prompt.replace("{{test_file}}", test_file.name)
        prompt = prompt.replace("{{test_output}}", test_output[-2000:]) # last 2k chars
        prompt = prompt.replace("{{current_code}}", current_code)

        # Call LLM
        llm_response = run_opencode(prompt, model="gpt-4o")

        # Extract Code
        try:
            new_code = llm_response
            if "```python" in new_code:
                new_code = new_code.split("```python")[1].split("```")[0].strip()
            elif "```" in new_code:
                new_code = new_code.split("```")[1].split("```")[0].strip()
            
            # Use safe_write_file (will check ratchet, but src/ is not locked)
            safe_write_file(workspace, source_file_rel, new_code)
        except Exception as e:
            print(f"    Failed to parse LLM output or write file: {e}")
            continue

        # Commit WIP - STRICT STAGING
        subprocess.run(["git", "add", source_file_rel], cwd=workspace, capture_output=True)
        
        # Integrity Check before commit
        ok, offending_file = verify_no_test_changes(workspace)
        if not ok:
             return {"success": False, "error": f"INTEGRITY VIOLATION: Agent tried to commit changes to {offending_file}"}

        subprocess.run(["git", "commit", "-m", f"WIP: {atomic_id} attempt {attempt}"], cwd=workspace, capture_output=True)

    return {"success": False, "error": f"Failed to pass tests after {MAX_RETRIES} attempts."}
