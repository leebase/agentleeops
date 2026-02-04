
import os
from dotenv import load_dotenv
from kanboard import Client

load_dotenv()

KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

def main():
    kb = Client(KB_URL, KB_USER, KB_TOKEN)
    
    print("--- Projects ---")
    projects = kb.get_all_projects()
    for p in projects:
        print(f"ID: {p['id']} | Name: {p['name']}")

    print("\n--- Search 'Cloudflared' ---")
    # Search across all projects if possible, or iterate
    for p in projects:
        tasks = kb.search_tasks(project_id=p['id'], query="Cloudflared")
        for t in tasks:
             print(f"FOUND in Project {p['id']}: #{t['id']} - {t['title']} (Column: {t['column_id']})")
             
    print("\n--- Search 'hello-fire' ---")
    for p in projects:
        tasks = kb.search_tasks(project_id=p['id'], query="hello-fire")
        for t in tasks:
             print(f"FOUND in Project {p['id']}: #{t['id']} - {t['title']}")

if __name__ == "__main__":
    main()
