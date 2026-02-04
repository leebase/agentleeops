
import os
import sys
from dotenv import load_dotenv
from kanboard import Client
from agents.test_agent import run_test_agent
from agents.test_code_agent import run_test_code_agent
from agents.governance import run_governance_agent

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

PARENT_ID = 11
ATOMIC_ID = "atomic-03"
TITLE = "[atomic-03] Create Project README"
DIRNAME = "hello-fire"

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    project_id = 1
    
    # Get Col ID
    cols = kb.get_columns(project_id=project_id)
    target_col = next((c for c in cols if "Tests Approved" in c['title']), None)
    
    print(f"Restoring {ATOMIC_ID} via Duplication of #{PARENT_ID}...")
    
    # 1. Duplicate
    task_id = kb.execute("duplicateTaskToProject", task_id=PARENT_ID, project_id=project_id)
    if not task_id:
        print("Error: Duplication failed")
        return
    print(f"Created Task #{task_id}")
    
    # 2. Update Content
    kb.execute("updateTask", 
        id=int(task_id), 
        title=TITLE, 
        description=f"Restored {ATOMIC_ID}",
        column_id=int(target_col['id'])
    )
    
    # 3. Set Metadata
    kb.execute("saveTaskMetadata", task_id=int(task_id), values={
        "atomic_id": ATOMIC_ID,
        "parent_id": str(PARENT_ID),
        "dirname": DIRNAME
    })
    
    # 4. Link
    kb.create_task_link(task_id=int(task_id), opposite_task_id=PARENT_ID, link_id=1)
    
    # 5. Force Agents
    print("\n--- STEP 1: TEST PLAN ---")
    res1 = run_test_agent(task_id, TITLE, DIRNAME, kb, project_id)
    if not res1['success']: 
        print(f"Failed: {res1}")
        return

    print("\n--- STEP 2: TEST CODE ---")
    res2 = run_test_code_agent(task_id, TITLE, DIRNAME, kb, project_id)
    if not res2['success']: 
        print(f"Failed: {res2}")
        return

    print("\n--- STEP 3: LOCK ---")
    res3 = run_governance_agent(task_id, TITLE, DIRNAME, target_col['title'], kb, project_id)
    print(f"Result: {res3}")

if __name__ == "__main__":
    main()
