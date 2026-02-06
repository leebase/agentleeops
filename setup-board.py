#!/usr/bin/env python3
"""
AgentLeeOps Board Configurator
------------------------------
Run this ONCE to configure your Kanboard project to the AgentLeeOps spec.
It will:
1. Create the Project (if missing).
2. Wipe default columns and create the 11 workflow columns.
3. Create standard swimlanes.
4. Set WIP limits (1 for Agent columns, Unlimited for Human columns).
5. Create the standard Tags.
"""

import os
import sys
from dotenv import load_dotenv
from kanboard import Client

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

if not KB_TOKEN:
    print("Error: KANBOARD_TOKEN not set in .env file")
    sys.exit(1)

PROJECT_NAME = "AgentLeeOps"

# The Exact PRD Column Structure
# Format: (Title, Task Limit) - 0 means unlimited
COLUMNS = [
    ("1. Inbox", 0),
    ("2. Design Draft", 1),        # Agent focused on one design
    ("3. Design Approved", 0),
    ("4. Planning Draft", 1),      # Agent breaking down one plan
    ("5. Plan Approved", 0),       # Fan-Out point
    ("6. Tests Draft", 1),         # Agent writing tests for Atomic Story
    ("7. Tests Approved", 0),
    ("8. Ralph Loop", 1),          # The Grind: Focus on ONE thing
    ("9. Code Review", 1),         # Review agent
    ("10. Final Review", 0),
    ("11. Done", 0)
]

# Swimlanes used for story organization
SWIMLANES = [
    "Parent Stories",
    "Atomic Stories",
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
        print(f"   -> Found Project ID: {project_id['id']}")
        project_id = project_id['id']

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
    try:
        existing_tags = kb.get_project_tags(project_id=project_id)
    except Exception:
        # Fallback if method mapping is tricky or method doesn't exist
        existing_tags = []
    
    if isinstance(existing_tags, dict):
       # Sometimes it returns a dict of id->name
       existing_names = set(existing_tags.values())
    else:
       existing_names = {t['name'] for t in existing_tags}

    for tag in TAGS:
        if tag not in existing_names:
            kb.create_tag(project_id=project_id, tag=tag)
            print(f"      + Created Tag: {tag}")
        else:
            print(f"      . Tag '{tag}' exists.")


def configure_swimlanes(kb, project_id):
    print("🏊 Configuring Swimlanes...")

    try:
        current = kb.execute("getAllSwimlanes", project_id=int(project_id))
    except Exception as e:
        print(f"   -> Could not load swimlanes: {e}")
        return

    existing_names = {lane["name"] for lane in current}

    for idx, lane_name in enumerate(SWIMLANES, start=2):
        if lane_name in existing_names:
            print(f"      . Swimlane '{lane_name}' exists.")
            continue

        try:
            kb.execute(
                "addSwimlane",
                project_id=int(project_id),
                name=lane_name,
                position=idx,
            )
            print(f"      + Created Swimlane: {lane_name}")
        except Exception as e:
            print(f"      ! Failed to create swimlane '{lane_name}': {e}")

    try:
        refreshed = kb.execute("getAllSwimlanes", project_id=int(project_id))
        parent_lane = next((lane for lane in refreshed if lane["name"] == "Parent Stories"), None)
        if parent_lane:
            kb.execute(
                "setDefaultSwimlane",
                project_id=int(project_id),
                swimlane_id=int(parent_lane["id"]),
            )
            print("      . Default swimlane set to 'Parent Stories'.")
    except Exception:
        # Optional enhancement; continue even if API support differs by version.
        pass

if __name__ == "__main__":
    kb = connect()
    p_id = setup_project(kb)
    configure_columns(kb, p_id)
    configure_swimlanes(kb, p_id)
    configure_tags(kb, p_id)

    print("\n✅ Board Setup Complete. You are ready for AgentLeeOps.")
