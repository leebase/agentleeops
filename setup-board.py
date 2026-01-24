#!/usr/bin/env python3
"""
AgentLeeOps Board Configurator
------------------------------
Run this ONCE to configure your Kanboard project to the AgentLeeOps spec.
It will:
1. Create the Project (if missing).
2. Wipe default columns and creating the 10 PRD columns.
3. Set WIP limits (1 for Agent columns, Unlimited for Human columns).
4. Create the standard Tags.
"""

import sys
from kanboard import Client

# --- CONFIGURATION ---
KB_URL = "http://localhost:88/jsonrpc.php"
KB_USER = "jsonrpc"
KB_TOKEN = "REMOVED_API_KEY"  # <--- PASTE YOUR TOKEN

PROJECT_NAME = "AgentLeeOps"

# The Exact PRD Column Structure
# Format: (Title, Task Limit) - 0 means unlimited
COLUMNS = [
    ("1. Inbox", 0),
    ("2. Design Draft", 1),        # Agent focused on one design
    ("3. Design Approved", 0),
    ("4. Repo & Tests Draft", 1),  # Agent scaffolding one repo
    ("5. Tests Approved", 0),
    ("6. Planning Draft", 1),      # Agent breaking down one plan
    ("7. Plan Approved", 0),
    ("8. Ralph Loop", 1),          # The Grind: Focus on ONE thing
    ("9. Final Review", 0),
    ("10. Done", 0)
]

# Standard Tags
TAGS = ["needs-human", "approved", "EXISTING", "NEW"]

def connect():
    try:
        return Client(KB_URL, KB_USER, KB_TOKEN)
    except Exception as e:
        print(f"❌ Could not connect to {KB_URL}. Check Docker is up.")
        sys.exit(1)

def setup_project(kb):
    print(f"🔍 Checking for project: '{PROJECT_NAME}'...")

    # 1. Find or Create Project
    project_id = kb.get_project_by_name(name=PROJECT_NAME)
    if not project_id:
        print(f"   -> Project not found. Creating '{PROJECT_NAME}'...")
        project_id = kb.create_project(name=PROJECT_NAME, description="AgentLeeOps Automated Board")
    else:
        print(f"   -> Found Project ID: {project_id}")

    return project_id

def configure_columns(kb, project_id):
    print("🚧 Configuring Columns...")

    # Get current columns
    current_cols = kb.get_columns(project_id=project_id)

    # 1. Check if board is already perfect (optimization)
    current_titles = [c['title'] for c in current_cols]
    target_titles = [c[0] for c in COLUMNS]

    if current_titles == target_titles:
        print("   -> Columns already match PRD. Skipping.")
        return

    # 2. The "Nuclear Option": Delete all existing columns to ensure order
    # (Kanboard moves tasks to the first remaining column if you delete theirs,
    # so be careful if you have active tasks. For setup, this is fine.)
    print("   -> Normalizing columns (This might take a moment)...")

    # Kanboard requires at least one column. We create a temp one, delete others, then remove temp.
    kb.add_column(project_id=project_id, title="TEMP_SETUP")
    temp_cols = kb.get_columns(project_id=project_id)
    temp_id = next(c['id'] for c in temp_cols if c['title'] == "TEMP_SETUP")

    for col in current_cols:
        kb.remove_column(column_id=col['id'])

    # 3. Create New Columns in Order
    for title, limit in COLUMNS:
        kb.add_column(project_id=project_id, title=title, task_limit=limit)
        print(f"      + Created: {title} (Limit: {limit})")

    # 4. Remove Temp
    kb.remove_column(column_id=temp_id)
    print("   -> Columns synced to PRD.")

def configure_tags(kb, project_id):
    print("🏷️  Configuring Tags...")
    existing_tags = kb.get_tags(project_id=project_id)
    existing_names = {t['name'] for t in existing_tags}

    for tag in TAGS:
        if tag not in existing_names:
            kb.create_tag(project_id=project_id, tag=tag)
            print(f"      + Created Tag: {tag}")
        else:
            print(f"      . Tag '{tag}' exists.")

if __name__ == "__main__":
    kb = connect()
    p_id = setup_project(kb)
    configure_columns(kb, p_id)
    configure_tags(kb, p_id)

    print("\n✅ Board Setup Complete. You are ready for AgentLeeOps.")
