
import os
import time
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from kanboard import Client

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

REPO_DIR = "/home/lee/projects/hello-fire"
PARENT_ID = 11

def clean_comment(text):
    """Extract relevant part of comment."""
    if "**RALPH**" in text:
        return text.split('\n')[0] # First line
    if "**RATCHET**" in text:
        return "🔒 Locked artifacts"
    return text[:60] + "..." if len(text) > 60 else text

def get_git_status():
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--oneline"], 
            cwd=REPO_DIR, 
            capture_output=True, 
            text=True
        )
        return res.stdout.strip()
    except:
        return "No git repo"

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    print(f"Monitoring Ralph Loop for Parent #{PARENT_ID}...")
    print("Press Ctrl+C to stop.\n")

    last_git = ""
    last_comments = {}

    try:
        while True:
            # Clear screen (optional, or just append)
            # print("\033c", end="") 
            
            # 1. Check Git
            curr_git = get_git_status()
            if curr_git != last_git:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 GIT: {curr_git}")
                last_git = curr_git

            # 2. Check Tasks
            # We want #25 and its children
            ids = [25, 26, 27, 28] # Reconstituted IDs
            
            for tid in ids:
                try:
                    task = kb.get_task(task_id=tid)
                    if not task: continue
                    
                    # Check latest comment
                    comments = kb.get_comments(task_id=tid)
                    if comments:
                        latest = comments[-1]
                        cid = latest['id']
                        ctext = latest['comment']
                        
                        # If new comment
                        if last_comments.get(tid) != cid:
                            clean_text = clean_comment(ctext)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💬 #{tid}: {clean_text}")
                            last_comments[tid] = cid
                            
                except Exception:
                    pass
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
