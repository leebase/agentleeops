
import os
import sys
from dotenv import load_dotenv
from kanboard import Client
from agents.ralph import run_ralph_agent

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

TASK_ID = 25 # Reconstituted Parent

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    print(f"Manually running Ralph for Task #{TASK_ID}...")
    
    # Get Task
    task = kb.get_task(task_id=TASK_ID)
    dirname = "hello-fire" # forced
    
    res = run_ralph_agent(TASK_ID, task['title'], dirname, kb, 1)
    print(f"Result: {res}")

if __name__ == "__main__":
    main()
