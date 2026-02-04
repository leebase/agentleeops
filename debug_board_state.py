
import os
from dotenv import load_dotenv
from kanboard import Client

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    tasks = kb.get_all_tasks(project_id=1)
    
    # Get columns map
    cols = kb.get_columns(project_id=1)
    col_map = {int(c['id']): c['title'] for c in cols}

    print(f"{'ID':<5} {'Column':<20} {'Title'}")
    print("-" * 60)
    for t in tasks:
        cid = int(t['column_id'])
        cname = col_map.get(cid, "Unknown")
        print(f"{t['id']:<5} {cname[:20]:<20} {t['title']}")
        
        # Check links
        try:
            links = kb.get_all_task_links(task_id=t['id'])
            for link in links:
                print(f"      -> Linked to #{link['task_id']} ({link['label']})")
        except:
            pass

if __name__ == "__main__":
    main()
