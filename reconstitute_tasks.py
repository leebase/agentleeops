
import os
import json
from dotenv import load_dotenv
from kanboard import Client

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")
PROJECT_ID = 1
DIRNAME = "hello-fire"

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    
    # 1. Read PRD
    prd_path = f"/home/lee/projects/{DIRNAME}/prd.json"
    with open(prd_path, 'r') as f:
        prd = json.load(f)
        
    print(f"Reconstituting '{prd['project_name']}'...")
    
    # 2. Get Columns
    cols = kb.get_columns(project_id=PROJECT_ID)
    col_map = {c['title']: c['id'] for c in cols}
    
    # Target: Ralph Loop (since tests are already done/locked locally)
    # Actually, let's put them in Tests Approved first, then move parent?
    # Or just put directly in Ralph Loop?
    # Ralph needs them to be in Ralph Loop.
    # But wait, if we put them in Ralph Loop, we need to ensure the *tests* are recognized.
    # Ralph checks for existing test files. They exist.
    # So we can go straight to Ralph Loop or Tests Approved.
    # Let's target "Tests Approved" to be safe and verify lock manually? 
    # No, let's go for "Ralph Loop" to verify batch.
    
    target_col_id = col_map.get("8. Ralph Loop") 
    if not target_col_id:
        # Fallback
        target_col_id = col_map.get("7. Tests Approved")
        
    print(f"Target Column: {target_col_id}")
    
    TEMPLATE_TASK_ID = 7 # Known existing task
    
    print(f"Target Column: {target_col_id}")
    
    # 3. Create Parent (via Duplication)
    parent_title = f"{prd['project_name']} Implementation"
    parent_id = kb.execute("duplicateTaskToProject", task_id=TEMPLATE_TASK_ID, project_id=PROJECT_ID)
    
    if not parent_id:
        print("Failed to duplicate parent template.")
        return

    kb.execute("updateTask", 
        id=int(parent_id), 
        title=parent_title, 
        description="Reconstituted Parent",
        column_id=target_col_id
    )
    print(f"Created Parent #{parent_id}: {parent_title}")
    
    # 4. Create Children
    for story in prd['stories']:
        title = f"[{story['id']}] {story['title']}"
        child_id = kb.execute("duplicateTaskToProject", task_id=TEMPLATE_TASK_ID, project_id=PROJECT_ID)
        
        kb.execute("updateTask", 
             id=int(child_id), 
             title=title, 
             description=story['description'],
             column_id=target_col_id
        )
        
        # Metadata
        kb.execute("saveTaskMetadata", task_id=int(child_id), values={
            "atomic_id": story['id'],
            "parent_id": str(parent_id),
            "dirname": DIRNAME
        })
        
        # Link
        kb.create_task_link(task_id=int(child_id), opposite_task_id=int(parent_id), link_id=1)
        print(f"  Created Child #{child_id}: {title} (Linked)")

    print("\nDone. You can now run Ralph on Parent #" + str(parent_id))

if __name__ == "__main__":
    main()
