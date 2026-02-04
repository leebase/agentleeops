"""
Fan-Out Spawner Agent
---------------------
Responsibility:
1. Triggered when Parent Card is in 'Plan Approved' (Column 5)
2. Reads prd.json
3. Spawns Child Cards in 'Plan Approved' (same column - gives human control)
   - Human moves each child to 'Tests Draft' when ready
   - USES DUPLICATION HACK to bypass MetaMagik mandatory field issues.
4. Links Child Cards to Parent
5. IMPLEMENTS IDEMPOTENCY, FLOOD CONTROL, and TRANSACTION SAFETY.
"""

import json
from pathlib import Path
from lib.workspace import get_workspace_path
from lib.task_fields import get_task_fields, update_status

MAX_CHILDREN_PER_EPIC = 20

def get_existing_child_atomic_ids(kb_client, parent_id: int):
    """
    Fetch all linked children and extract their atomic_id metadata.
    """
    existing_ids = set()
    try:
        # Get tasks linked to parent
        links = kb_client.execute("getAllTaskLinks", task_id=parent_id)
        if not links:
            return existing_ids
            
        for link in links:
            # getAllTaskLinks returns tasks linked to parent_id
            # task_id in the result is the linked task
            child_id = link.get("task_id")
            if child_id:
                # Fetch metadata for the child
                meta = kb_client.execute("getTaskMetadata", task_id=int(child_id))
                if meta and "atomic_id" in meta:
                    existing_ids.add(meta["atomic_id"])
    except Exception as e:
        print(f"  [Spawner] Warning: Failed to fetch existing children: {e}")
    
    return existing_ids

def run_spawner_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int):
    """
    Executes the Fan-Out Logic with safety rails.
    """
    print(f"  [Spawner] Starting fan-out for '{title}'...")

    # 0. Recursion Guard: Am I a child?
    try:
        # Check if I have an atomic_id (meaning I am a child)
        if isinstance(kb_client, object): # Duck typing check or just try calling it
             current_meta = kb_client.get_task_metadata(task_id=int(task_id))
        else:
             current_meta = {}
             
        if current_meta and current_meta.get("atomic_id"):
             msg = f"Recursion Guard: Task '{title}' is a Child Card ({current_meta['atomic_id']}). Aborting spawn."
             print(f"  [Spawner] {msg}")
             return {"success": False, "error": msg}
    except Exception as e:
        print(f"  [Spawner] Warning: Failed to check metadata for recursion guard: {e}")

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

    # 3. Flood Control
    if len(stories) > MAX_CHILDREN_PER_EPIC:
        return {
            "success": False, 
            "error": f"Flood Control: PRD requests {len(stories)} stories, but limit is {MAX_CHILDREN_PER_EPIC}. Aborting."
        }

    # 4. Get Parent Context
    try:
        parent_fields = get_task_fields(kb_client, int(task_id))
        context_mode = parent_fields.get("context_mode", "NEW")
    except Exception as e:
         return {"success": False, "error": f"Failed to get parent context: {e}"}

    # 5. Idempotency: Check what's already spawned
    existing_atomic_ids = get_existing_child_atomic_ids(kb_client, int(task_id))
    if existing_atomic_ids:
        print(f"  [Spawner] Found {len(existing_atomic_ids)} existing child tasks. Skipping duplicates.")

    spawned_count = 0
    skipped_count = 0
    
    # 6. Find destination column ID (Column 5: "Plan Approved" - gives human control)
    try:
        cols = kb_client.get_columns(project_id=project_id)
        dest_col = next((c for c in cols if "Plan Approved" in c['title']), None)
        if not dest_col:
             return {"success": False, "error": "Could not find 'Plan Approved' column."}
        dest_col_id = int(dest_col['id'])
    except Exception as e:
        return {"success": False, "error": f"Failed to get board columns: {e}"}

    print(f"  [Spawner] Processing {len(stories)} stories...")

    for story in stories:
        atomic_id = story.get("id")
        story_title = story.get("title")
        
        if not atomic_id:
            print("    [Spawner] Warning: Story missing ID. Skipping.")
            continue
            
        if atomic_id in existing_atomic_ids:
            print(f"    . Already exists: {atomic_id}. Skipping.")
            skipped_count += 1
            continue

        child_title = f"[{atomic_id}] {story_title}"
        new_task_id = None
        
        try:
            # TRANSACTION START: Duplicate the Parent Task
            new_task_id = kb_client.execute("duplicateTaskToProject", task_id=int(task_id), project_id=project_id)
            
            if not new_task_id:
                raise RuntimeError(f"API returned no ID for duplicate of {atomic_id}")

            # TRANSACTION STEP 2: Update Content
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

            # TRANSACTION STEP 3: Set Metadata
            metadata = {
                "atomic_id": atomic_id,
                "parent_id": str(task_id),
                "agent_status": "pending"
            }
            kb_client.execute("saveTaskMetadata", task_id=int(new_task_id), values=metadata)
            
            # TRANSACTION STEP 4: Link to Parent
            # Link type 1: "relates to"
            res = kb_client.create_task_link(task_id=int(new_task_id), opposite_task_id=int(task_id), link_id=1)
            if not res:
                # Linking is secondary but nice to have. We won't roll back just for a link failure
                # unless you want strict adherence. Let's just log it.
                print(f"    Warning: Could not link #{new_task_id} to parent.")

            print(f"    + Created Child #{new_task_id}: {child_title}")
            spawned_count += 1

        except Exception as e:
            print(f"    ❌ Error spawning {atomic_id}: {e}")
            # TRANSACTION ROLLBACK: Delete orphan if we have an ID
            if new_task_id:
                print(f"    [Rollback] Deleting orphan task #{new_task_id}...")
                try:
                    kb_client.execute("removeTask", task_id=int(new_task_id))
                except Exception as rollback_e:
                    print(f"    [Critical] Rollback failed for #{new_task_id}: {rollback_e}")

    # 7. Summary
    if spawned_count > 0 or skipped_count > 0:
        return {
            "success": True, 
            "count": spawned_count, 
            "skipped": skipped_count,
            "total": len(stories)
        }
    else:
        return {"success": False, "error": "No tasks created or skipped."}