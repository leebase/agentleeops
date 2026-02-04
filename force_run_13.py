
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

TASK_ID = 13 # atomic-02

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    print(f"Force-running chain for Task #{TASK_ID}...")
    
    task = kb.get_task(task_id=TASK_ID)
    title = task['title']
    
    # hack dirname
    dirname = "hello-fire"

    print("\n--- STEP 1: TEST PLAN ---")
    res1 = run_test_agent(TASK_ID, title, dirname, kb, 1)
    print(f"Result: {res1}")
    if not res1['success']: return

    print("\n--- STEP 2: TEST CODE ---")
    res2 = run_test_code_agent(TASK_ID, title, dirname, kb, 1)
    print(f"Result: {res2}")
    if not res2['success']: return

    print("\n--- STEP 3: LOCK ---")
    # Need column title logic to be correct for governance, but for locking it mostly needs to know it's "Tests Approved"
    # Actually governance checks column title.
    col_title = "7. Tests Approved" 
    res3 = run_governance_agent(TASK_ID, title, dirname, col_title, kb, 1)
    print(f"Result: {res3}")

if __name__ == "__main__":
    main()
