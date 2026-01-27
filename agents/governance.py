"""
Governance Agent.
Enforces the Ratchet by locking artifacts when they reach Approved columns.
"""

from pathlib import Path
from lib.workspace import get_workspace_path
from lib.ratchet import lock_artifact

def run_governance_agent(task_id: str, title: str, dirname: str, column_title: str, kb_client, project_id: int):
    """
    Lock artifacts based on the column.
    """
    print(f"  [Governance] Enforcing Ratchet for '{title}' in '{column_title}'...")
    
    workspace = get_workspace_path(dirname)
    
    locked_files = []
    
    if "Design Approved" in column_title:
        if lock_artifact(workspace, "DESIGN.md"):
            locked_files.append("DESIGN.md")
            
    elif "Plan Approved" in column_title:
        if lock_artifact(workspace, "prd.json"):
            locked_files.append("prd.json")
            
    elif "Tests Approved" in column_title:
        # Lock all python files in tests/
        tests_dir = workspace / "tests"
        if tests_dir.exists():
            for test_file in tests_dir.glob("test_*.py"):
                rel_path = f"tests/{test_file.name}"
                if lock_artifact(workspace, rel_path):
                    locked_files.append(rel_path)

    if locked_files:
        msg = f"**RATCHET**: Locked {len(locked_files)} artifacts: " + ", ".join(f"`{f}`" for f in locked_files)
        print(f"    {msg}")
        try:
            kb_client.create_comment(task_id=task_id, user_id=1, content=msg)
        except Exception:
            pass
        return {"success": True, "locked": locked_files}
    else:
        return {"success": True, "locked": []} # No artifacts found/locked is still success
