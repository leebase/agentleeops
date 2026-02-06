
import os
import sys
import base64

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from lib.workitem.client import WorkItemClient
from lib.workitem.types import WorkItemQuery

def main():
    load_dotenv(os.path.join(project_root, ".env"))
    
    print("Connecting to Kanboard...")
    client = WorkItemClient.from_config()
    raw_client = client._provider.client
    
    # 1. Find Task
    target_title = "Data Contract Guard"
    task = None
    
    projects = raw_client.get_all_projects()
    for p in projects:
        tasks = raw_client.get_all_tasks(project_id=p['id'])
        for t in tasks:
            if target_title.lower() in t['title'].lower():
                task = t
                print(f"Found task: [{task['id']}] {task['title']}")
                break
        if task: break
    
    if not task:
        print("Task not found.")
        return 1

    task_id = task['id']
    project_id = task['project_id']

    # 2. Skip Check existing files (Method not found error)
    # files = raw_client.get_task_files(task_id=task_id)
    # print(f"Existing files: {[f['name'] for f in files]}")
    
    # if any(f['name'] == 'DESIGN.md' for f in files):
    #     print("DESIGN.md already attached.")
    #     return 0

    # 3. Attach file
    design_path = "/home/lee/projects/data-guard/DESIGN.md"
    if not os.path.exists(design_path):
        print(f"File not found: {design_path}")
        return 1
        
    print(f"Reading {design_path}...")
    with open(design_path, 'r') as f:
        content = f.read()
        
    encoded = base64.b64encode(content.encode()).decode()
    
    print("Uploading DESIGN.md...")
    try:
        # Using execute to be explicit about method name
        result = raw_client.execute(
            'createTaskFile',
            project_id=project_id,
            task_id=task_id,
            filename="DESIGN.md",
            blob=encoded
        )
        print(f"Upload result: {result}")
        print("SUCCESS: Attached DESIGN.md")
    except Exception as e:
        print(f"Upload failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
