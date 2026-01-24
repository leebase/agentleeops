#!/usr/bin/env python3
"""
AgentLeeOps Orchestrator (Phase 1 Poller)
Running on: Port 88
"""

import os
import sys
import time
import re
from kanboard import Client

# --- CONFIGURATION ---
KB_URL = "http://localhost:88/jsonrpc.php"
KB_USER = "jsonrpc"
# REPLACE THIS WITH YOUR REAL TOKEN
KB_TOKEN = "YOUR_API_TOKEN_HERE"

# Column triggers (Must match your board EXACTLY)
TRIGGERS = {
    "2. Design Draft": "ARCHITECT_AGENT",
    "4. Repo & Tests Draft": "SCAFFOLD_AGENT",
    "6. Planning Draft": "PM_AGENT",
    "8. Ralph Loop": "RALPH_CODER",
}

def connect_kb():
    try:
        return Client(KB_URL, KB_USER, KB_TOKEN)
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

def parse_card_description(description):
    """
    Parses the new YAML-style template from the card.
    """
    data = {}
    if not description:
        return data

    # Simple Regex to grab values like "key: value"
    dirname_match = re.search(r'dirname:\s*(.+)', description)
    mode_match = re.search(r'context_mode:\s*(.+)', description)

    if dirname_match:
        data['dirname'] = dirname_match.group(1).strip()
    if mode_match:
        data['mode'] = mode_match.group(1).strip().upper() # NEW | FEATURE

    return data

def process_task(kb, task, action):
    task_id = task['id']
    title = task['title']
    desc = task.get('description', '')

    print(f"⚡ Triggering {action} for Task #{task_id}: {title}")

    # 1. Parse the Context
    context = parse_card_description(desc)
    mode = context.get('mode', 'UNKNOWN')
    dirname = context.get('dirname', 'UNKNOWN')

    print(f"   -> Context: Mode={mode}, Dir={dirname}")

    # 2. THE ROUTER (Where we will hook up OpenCode later)
    if action == "ARCHITECT_AGENT":
        # Placeholder for OpenCode Plan Mode
        print(f"   -> 🤖 [Stub] Generating DESIGN.md for {dirname}...")
        time.sleep(1) # Fake work

        # 3. Post Feedback to Board
        comment = f"✅ **{action} Started**\n- Mode: {mode}\n- Target: `~/projects/{dirname}`\n- Status: Analysis Complete."
        kb.create_comment(task_id=task_id, content=comment)

    elif action == "SCAFFOLD_AGENT":
        if mode == "NEW":
            print(f"   -> 📂 [Stub] Running 'mkdir {dirname}' and 'git init'...")
        elif mode == "FEATURE":
            print(f"   -> 🐙 [Stub] Checking out existing repo '{dirname}'...")

    # 4. Prevent Infinite Loop (Important for polling!)
    # In a real app, we check if we already commented or move the card.
    # For this test, we just print.

def main():
    kb = connect_kb()
    print(f"👀 Orchestrator watching {KB_URL}...")

    while True:
        # Get all tasks in project 1 (Assuming ID 1 for now)
        try:
            tasks = kb.get_all_tasks(project_id=1)

            for task in tasks:
                # Kanboard API returns column_id, not name. We need to map them.
                # Ideally, fetch columns once at startup to build a map.
                # For now, we trust the logic:

                # To make this robust, let's just print the column name for debugging
                # In your real run, you will match specific Column IDs.
                pass

                # OPTIMIZATION:
                # Since we don't know your Column IDs yet, run this ONCE to find them:
                # columns = kb.get_columns(project_id=1)
                # print(columns)

        except Exception as e:
            print(f"⚠️ Polling Error: {e}")

        time.sleep(10)

if __name__ == "__main__":
    # HELPER: First run prints your columns so you can map them in 'TRIGGERS'
    kb = connect_kb()
    cols = kb.get_columns(project_id=1)
    print("ℹ️  Your Board Columns:")
    for c in cols:
        print(f"   ID: {c['id']} | Title: {c['title']}")

    print("\nStarting Loop...")

    # Map Titles to IDs for the loop
    col_map = {c['title']: c['id'] for c in cols}

    while True:
        tasks = kb.get_all_tasks(project_id=1)
        for task in tasks:
            col_id = task['column_id']
            # Find the column name for this ID
            col_name = next((k for k, v in col_map.items() if v == col_id), None)

            if col_name in TRIGGERS:
                action = TRIGGERS[col_name]
                # CHECK: Has the agent already run? (Look for a tag or comment)
                # For this test, we skip that check to keep it simple.
                process_task(kb, task, action)

        time.sleep(5)
