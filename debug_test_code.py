
import os
import sys
from dotenv import load_dotenv
from kanboard import Client
from agents.test_code_agent import run_test_code_agent
from agents.governance import run_governance_agent

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    project_id = 1
    
    # Get columns
    cols = kb.get_columns(project_id=project_id)
    target_col = next((c for c in cols if "Tests Approved" in c['title']), None)
    
    if not target_col:
        print("Column 'Tests Approved' not found!")
        return

    print(f"Target Column: {target_col['title']} (ID: {target_col['id']})")
    
    # Get tasks in column
    all_tasks = kb.get_all_tasks(project_id=project_id)
    tasks = [t for t in all_tasks if int(t['column_id']) == int(target_col['id'])]
    
    if not tasks:
        print("No tasks found in 'Tests Approved'.")
        return

    for task in tasks:
        print(f"\nFound Task #{task['id']}: {task['title']}")
        
        # Get Directory
        try:
            desc = task.get('description', '')
            import yaml
            # Simple parsing if metadata missing
            dirname = "hello-fire" # Assumption for debug
            # Try to parse
            for line in desc.split('\n'):
                if line.startswith('dirname:'):
                    dirname = line.split(':')[1].strip()
        except:
             dirname = "hello-fire"
             
        print(f"Dirname: {dirname}")
        
        # Run Agent
        print("Running Test Code Agent...")
        res = run_test_code_agent(
            task_id=task['id'],
            title=task['title'],
            dirname=dirname,
            kb_client=kb,
            project_id=project_id
        )
        print(f"Result: {res}")
        
        if res['success']:
             print("Running Governance Agent...")
             gov_res = run_governance_agent(
                 task_id=task['id'],
                 title=task['title'],
                 dirname=dirname,
                 column_title=target_col['title'],
                 kb_client=kb,
                 project_id=project_id
             )
             print(f"Gov Result: {gov_res}")

if __name__ == "__main__":
    main()
