
import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from lib.workitem.client import WorkItemClient
from lib.workitem.types import WorkItemQuery, WorkItemState
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv(os.path.join(project_root, ".env"))

    try:
        print("Connecting to Kanboard...")
        client = WorkItemClient.from_config()
        
        # Get raw client to list projects
        raw_client = client._provider.client
        projects = raw_client.get_all_projects()
        print(f"DEBUG: Found {len(projects)} projects.")
        
        for project in projects:
            p_id = int(project['id'])
            p_name = project['name']
            print(f"\nScanning Project {p_id}: {p_name}")
            
            # Search tasks in this project
            tasks = raw_client.get_all_tasks(project_id=p_id)
            print(f"  Found {len(tasks)} tasks.")
            
            for task in tasks:
                 print(f"  - [{task['id']}] {task['title']}")
                 if target_title.lower() in task['title'].lower():
                    print(f"\nSUCCESS: Found story '{task['title']}' in Project {p_id}!")
                    print(f"Identity: kanboard:{task['id']}")
                    found = True
                    # Don't break, see all
        
        if not found:
            print(f"\nFAILURE: Could not find story with title containing '{target_title}' in any project.")
            return 1
            
        return 0

        
    except Exception as e:
        print(f"\nERROR: Failed to connect to Kanboard or query items: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
