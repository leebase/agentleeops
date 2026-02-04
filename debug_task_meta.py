
import os
from dotenv import load_dotenv
from kanboard import Client

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")
PROJECT_ID = 1

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    tid = 25
    meta = kb.get_task_metadata(task_id=tid)
    print(f"Metadata for #{tid}: {meta}")
    
    # Check children
    links = kb.get_all_task_links(task_id=tid)
    print(f"Links: {len(links)}")
    for l in links:
         print(f" - {l['task_id']}: {l['label']}")

if __name__ == "__main__":
    main()
