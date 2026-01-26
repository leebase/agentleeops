"""
Fan-Out Spawner Agent
---------------------
Responsibility:
1. Triggered when Parent Card is in 'Plan Approved' (Column 5)
2. Reads prd.json
3. Spawns Child Cards in 'Tests Draft' (Column 6)
   - USES DUPLICATION HACK to bypass MetaMagik mandatory field issues.
4. Links Child Cards to Parent
"""

import json
from pathlib import Path
from lib.workspace import get_workspace_path
from lib.task_fields import get_task_fields, update_status

def run_spawner_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int):
    """
    Executes the Fan-Out Logic using the Duplication Hack.
    """
    print(f"  [Spawner] Starting fan-out for '{title}'...")

    # 1. Setup Workspace Paths
    workspace = get_workspace_path(dirname)
    prd_path = workspace / "prd.json"

    if not prd_path.exists():
        return {
            "success": False,
            "error": f"prd.json not found at {prd_path}. Cannot spawn child cards."
        }

    # 2. Read prd.json
    try:
        prd_data = json.loads(prd_path.read_text())
        stories = prd_data.get("stories", [])
    except Exception as e:
        return {"success": False, "error": f"Failed to read/parse prd.json: {e}"}

    if not stories:
        return {"success": False, "error": "prd.json contains no stories."}

    # 3. Get Parent Context
    try:
        parent_fields = get_task_fields(kb_client, int(task_id))
        context_mode = parent_fields.get("context_mode", "NEW")
    except Exception as e:
         return {"success": False, "error": f"Failed to get parent context: {e}"}

    spawned_count = 0
    
    # 4. Find destination column ID (Column 6: "Tests Draft")
    try:
        cols = kb_client.get_columns(project_id=project_id)
        dest_col = next((c for c in cols if "Tests Draft" in c['title']), None)
        if not dest_col:
             return {"success": False, "error": "Could not find 'Tests Draft' column."}
        dest_col_id = int(dest_col['id'])
    except Exception as e:
        return {"success": False, "error": f"Failed to get board columns: {e}"}

    print(f"  [Spawner] Found {len(stories)} stories. Spawning via Duplication of Task #{task_id}...")

    for story in stories:
        atomic_id = story.get("id")
        story_title = story.get("title")
        child_title = f"[{atomic_id}] {story_title}"
        
        try:
            # THE HACK: Duplicate the Parent Task to Project 1
            # This creates a task with all MetaMagik fields satisfied.
            new_task_id = kb_client.execute("duplicateTaskToProject", task_id=int(task_id), project_id=project_id)
            
            if not new_task_id:
                print(f"    Failed to duplicate task for {atomic_id}.")
                continue

            # 5. Clean up the Duplicate
            # Update Title, Description, and move to Column 6
            description = (
                f"**Atomic Story**: {atomic_id}\n"
                f"**Parent**: #{task_id}\n\n"
                f"{story.get('description', '')}\n\n"
                f"**Acceptance Criteria**:\n" + "\n".join(f"- {c}" for c in story.get("acceptance_criteria", []))
            )
            
            kb_client.execute("updateTask", 
                id=int(new_task_id), 
                title=child_title, 
                description=description,
                column_id=dest_col_id
            )

            # 6. Set Metadata
            # dirname and context_mode are already copied by duplicate, but we ensure consistency
            metadata = {
                "atomic_id": atomic_id,
                "parent_id": str(task_id),
                "agent_status": "pending"
            }
            kb_client.execute("saveTaskMetadata", task_id=int(new_task_id), values=metadata)
            
            # 7. Link to Parent
            try:
                # Link type 1: "relates to"
                kb_client.create_task_link(task_id=int(new_task_id), opposite_task_id=int(task_id), link_id=1)
            except Exception as link_e:
                print(f"    Warning: Link failed: {link_e}")

            print(f"    + Created Child #{new_task_id}: {child_title}")
            spawned_count += 1

        except Exception as e:
            print(f"    Error duplicating for {atomic_id}: {e}")

    if spawned_count > 0:
        return {"success": True, "count": spawned_count}
    else:
        return {"success": False, "error": "No tasks created."}
