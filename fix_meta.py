
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
    
    print(f"Cleaning metadata for #{tid}...")
    
    # 1. Remove atomic_id (set to empty string)
    # 2. Fix dirname
    kb.execute("saveTaskMetadata", task_id=tid, values={
        "atomic_id": "",
        "dirname": "hello-fire",
        "context_mode": "NEW" # It's a new project
    })
    
    # Verify
    meta = kb.get_task_metadata(task_id=tid)
    print(f"New Metadata: {meta}")

if __name__ == "__main__":
    main()
