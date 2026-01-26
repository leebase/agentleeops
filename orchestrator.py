#!/usr/bin/env python3
"""
AgentLeeOps Orchestrator

Watches Kanboard columns and triggers appropriate agents.
Supports both polling mode and single-run mode (--once).

Usage:
    python orchestrator.py          # Polling mode (runs continuously)
    python orchestrator.py --once   # Single-run mode (process one card, exit)
"""

import argparse
import os
import sys
import time

from dotenv import load_dotenv
from kanboard import Client

from lib.task_fields import get_task_fields, update_status, TaskFieldError

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

# Column triggers (Must match your board EXACTLY)
# Updated to match Product Definition v1.1 (Context-Reset TDD)
TRIGGERS = {
    "2. Design Draft": "ARCHITECT_AGENT",
    "4. Planning Draft": "PM_AGENT",      # Moved up (was col 6)
    "5. Plan Approved": "SPAWNER_AGENT",  # New: Fan-Out Trigger
    "6. Tests Draft": "TEST_AGENT",       # Moved down & renamed (was col 4 Scaffold)
    "8. Ralph Loop": "RALPH_CODER",
}

# Tags for state tracking
TAGS = {
    "ARCHITECT_AGENT": {
        "started": "design-started",
        "completed": "design-generated",
    },
    "PM_AGENT": {
        "started": "planning-started",
        "completed": "planning-generated",
    },
    "SPAWNER_AGENT": {
        "started": "spawning-started",
        "completed": "spawned",
    },
    "TEST_AGENT": {
        "started": "tests-started",
        "completed": "tests-generated",
    },
    "RALPH_CODER": {
        "started": "coding-started",
        "completed": "coding-complete",
    },
}


def connect_kb():
    """Connect to Kanboard API."""
    if not KB_TOKEN:
        print("Error: KANBOARD_TOKEN not set. Create a .env file with your token.")
        print("See .env.example for template.")
        sys.exit(1)

    try:
        return Client(KB_URL, KB_USER, KB_TOKEN)
    except Exception as e:
        print(f"Connection Failed: {e}")
        sys.exit(1)


def get_task_tags(kb, task_id: int) -> list:
    """Get tags for a task."""
    try:
        tags = kb.get_task_tags(task_id=task_id)
        if not tags:
            return []
        if isinstance(tags, dict):
            return [str(value) for value in tags.values()]
        if isinstance(tags, list):
            if tags and isinstance(tags[0], dict):
                return [tag.get('name') for tag in tags if tag.get('name')]
            return [str(tag) for tag in tags]
        return []
    except Exception:
        return []


def add_task_tag(kb, project_id: int, task_id: int, tag_name: str):
    """Add a tag to a task (creates tag if needed)."""
    try:
        project_id = int(project_id)
        task_id = int(task_id)
        existing = get_task_tags(kb, task_id)
        if tag_name in existing:
            return
        updated = existing + [tag_name]
        kb.set_task_tags(project_id=project_id, task_id=task_id, tags=updated)
    except Exception as e:
        print(f"  Warning: Could not add tag '{tag_name}': {e}")


def has_tag(tags: list, tag_name: str) -> bool:
    """Check if a tag is in the tags list."""
    return tag_name in tags


def process_architect_task(kb, task: dict, project_id: int) -> bool:
    """
    Process a task in the Design Draft column.

    Returns:
        True if task was processed, False otherwise
    """
    from agents.architect import run_architect_agent

    task_id = task['id']
    title = task['title']
    desc = task.get('description', '')

    # Check if already processed
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["ARCHITECT_AGENT"]

    if has_tag(tags, agent_tags["completed"]):
        print(f"  Task #{task_id} already processed (has {agent_tags['completed']} tag)")
        return False

    if has_tag(tags, agent_tags["started"]):
        print(f"  Task #{task_id} already in progress (has {agent_tags['started']} tag)")
        return False

    # Get task fields (metadata API or YAML fallback)
    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
        context_mode = fields.get("context_mode", "NEW")
        acceptance_criteria = fields.get("acceptance_criteria", "")
    except TaskFieldError as e:
        print(f"  Error: {e}")
        kb.create_comment(
            task_id=task_id,
            content=f"**ARCHITECT_AGENT Error**\n\n{e}"
        )
        return False

    print(f"  Processing: {title}")
    print(f"    dirname: {dirname}")
    print(f"    context_mode: {context_mode}")

    # Mark as started (tag + metadata)
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="design")

    # Run architect agent
    result = run_architect_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        context_mode=context_mode,
        acceptance_criteria=acceptance_criteria,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        # Mark as completed (tag + metadata)
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        update_status(kb, task_id, agent_status="completed", current_phase="design")
        print(f"  Success: DESIGN.md written to {result['design_path']}")
        return True
    else:
        update_status(kb, task_id, agent_status="failed", current_phase="design")
        print(f"  Failed: {result['error']}")
        return False


def process_pm_task(kb, task: dict, project_id: int) -> bool:
    """
    Process a task in the Planning Draft column.
    """
    from agents.pm import run_pm_agent

    task_id = task['id']
    title = task['title']

    # Check if already processed
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["PM_AGENT"]

    if has_tag(tags, agent_tags["completed"]):
        print(f"  Task #{task_id} already processed (has {agent_tags['completed']} tag)")
        return False

    if has_tag(tags, agent_tags["started"]):
        print(f"  Task #{task_id} already in progress (has {agent_tags['started']} tag)")
        return False

    # Get task fields
    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
        context_mode = fields.get("context_mode", "NEW")
        acceptance_criteria = fields.get("acceptance_criteria", "")
    except TaskFieldError as e:
        print(f"  Error: {e}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**PM_AGENT Error**\n\n{e}")
        return False

    print(f"  Processing: {title}")

    # Mark as started
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="planning")

    # Run PM agent
    result = run_pm_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        context_mode=context_mode,
        acceptance_criteria=acceptance_criteria,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        update_status(kb, task_id, agent_status="completed", current_phase="planning")
        print(f"  Success: prd.json written with {result['story_count']} stories.")
        return True
    else:
        update_status(kb, task_id, agent_status="failed", current_phase="planning")
        print(f"  Failed: {result['error']}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**PM_AGENT Failed**\n\n{result['error']}")
        return False


def process_spawner_task(kb, task: dict, project_id: int) -> bool:
    """
    Process a task in the Plan Approved column (Fan-Out).
    """
    from agents.spawner import run_spawner_agent

    task_id = task['id']
    title = task['title']

    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["SPAWNER_AGENT"]

    # Only run if not already spawned
    if has_tag(tags, agent_tags["completed"]):
        return False
    
    if has_tag(tags, agent_tags["started"]):
        return False

    # Check for prd.json existence? The agent does that.
    
    # Get fields for dirname
    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return False

    print(f"  Processing Spawner for: {title}")
    
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    # No status update needed? Or maybe "spawning"
    
    result = run_spawner_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        print(f"  Success: Spawned {result['count']} child cards.")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**SPAWNER**: Automatically created {result['count']} child tasks in 'Tests Draft'.")
        return True
    else:
        # If failed, remove started tag so it retries? Or tag failed?
        # For now, just log.
        print(f"  Failed: {result['error']}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**SPAWNER Failed**\n\n{result['error']}")
        return False


def process_test_task(kb, task: dict, project_id: int) -> bool:
    """
    Process a task in the Tests Draft column.
    """
    from agents.test_agent import run_test_agent

    task_id = task['id']
    title = task['title']

    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["TEST_AGENT"]

    if has_tag(tags, agent_tags["completed"]):
        return False
    if has_tag(tags, agent_tags["started"]):
        return False

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return False

    print(f"  Processing Test Generation for: {title}")
    
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="tests")

    result = run_test_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        update_status(kb, task_id, agent_status="completed", current_phase="tests")
        print(f"  Success: Created {result['test_file']}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**TEST_AGENT**: Created test file `{result['test_file']}`.\n\nReady for Human Review.")
        return True
    else:
        update_status(kb, task_id, agent_status="failed", current_phase="tests")
        print(f"  Failed: {result['error']}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**TEST_AGENT Failed**\n\n{result['error']}")
        return False


def process_ralph_task(kb, task: dict, project_id: int) -> bool:
    """
    Process a task in the Ralph Loop column.
    """
    from agents.ralph import run_ralph_agent

    task_id = task['id']
    title = task['title']
    
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["RALPH_CODER"]

    if has_tag(tags, agent_tags["completed"]):
        return False
    if has_tag(tags, agent_tags["started"]):
        return False
    
    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return False

    print(f"  Processing Ralph Loop for: {title}")
    
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="coding")

    result = run_ralph_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        update_status(kb, task_id, agent_status="completed", current_phase="coding")
        print(f"  Success: Green Bar in {result['iterations']} iterations.")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**RALPH**: Tests passed in {result['iterations']} iterations. Code committed.")
        return True
    else:
        update_status(kb, task_id, agent_status="failed", current_phase="coding")
        print(f"  Failed: {result['error']}")
        kb.create_comment(task_id=task_id, user_id=1, content=f"**RALPH Failed**\n\n{result['error']}")
        return False


def process_task(kb, task: dict, action: str, project_id: int) -> bool:
    """
    Route task to appropriate agent.

    Returns:
        True if task was processed, False otherwise
    """
    task_id = task['id']
    title = task['title']

    print(f"Triggering {action} for Task #{task_id}: {title}")

    if action == "ARCHITECT_AGENT":
        return process_architect_task(kb, task, project_id)

    elif action == "PM_AGENT":
        return process_pm_task(kb, task, project_id)

    elif action == "SPAWNER_AGENT":
        return process_spawner_task(kb, task, project_id)

    elif action == "TEST_AGENT":
        return process_test_task(kb, task, project_id)

    elif action == "RALPH_CODER":
        return process_ralph_task(kb, task, project_id)

    return False

    return False


def run_once(kb, project_id: int = 1):
    """
    Single-run mode: Process one card and exit.
    Looks for cards in trigger columns that haven't been processed yet.
    """
    print(f"Single-run mode: checking for work...")

    # Get column mapping
    cols = kb.get_columns(project_id=project_id)
    col_map = {c['title']: c['id'] for c in cols}
    col_id_to_name = {c['id']: c['title'] for c in cols}

    # Get all tasks
    tasks = kb.get_all_tasks(project_id=project_id)

    for task in tasks:
        col_id = task['column_id']
        col_name = col_id_to_name.get(col_id)

        if col_name in TRIGGERS:
            action = TRIGGERS[col_name]

            # Check if already processed
            tags = get_task_tags(kb, task['id'])
            agent_tags = TAGS.get(action, {})

            if has_tag(tags, agent_tags.get("completed", "")):
                continue  # Skip completed tasks

            if has_tag(tags, agent_tags.get("started", "")):
                continue  # Skip in-progress tasks

            # Found an unprocessed task
            if process_task(kb, task, action, project_id):
                print("Done.")
                return
            else:
                # Task wasn't fully processed, but we tried
                print("Task processing did not complete successfully.")
                return

    print("No unprocessed tasks found in trigger columns.")


def run_polling(kb, project_id: int = 1, poll_interval: int = 5):
    """
    Polling mode: Continuously watch for cards in trigger columns.
    """
    print(f"Polling mode: watching {KB_URL}")
    print(f"Poll interval: {poll_interval}s")
    print("Press Ctrl+C to stop.\n")

    # Get column mapping
    cols = kb.get_columns(project_id=project_id)
    col_map = {c['title']: c['id'] for c in cols}
    col_id_to_name = {c['id']: c['title'] for c in cols}

    print("Board Columns:")
    for c in cols:
        trigger = " <- TRIGGER" if c['title'] in TRIGGERS else ""
        print(f"  {c['id']}: {c['title']}{trigger}")
    print()

    while True:
        try:
            tasks = kb.get_all_tasks(project_id=project_id)

            for task in tasks:
                col_id = task['column_id']
                col_name = col_id_to_name.get(col_id)

                if col_name in TRIGGERS:
                    action = TRIGGERS[col_name]

                    # Check if already processed
                    tags = get_task_tags(kb, task['id'])
                    agent_tags = TAGS.get(action, {})

                    if has_tag(tags, agent_tags.get("completed", "")):
                        continue

                    if has_tag(tags, agent_tags.get("started", "")):
                        continue

                    # Process the task
                    process_task(kb, task, action, project_id)

        except KeyboardInterrupt:
            print("\nStopping orchestrator.")
            break
        except Exception as e:
            print(f"Polling Error: {e}")

        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(
        description="AgentLeeOps Orchestrator - Trigger agents based on Kanboard columns"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single-run mode: process one card and exit"
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=1,
        help="Kanboard project ID (default: 1)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)"
    )

    args = parser.parse_args()

    kb = connect_kb()

    if args.once:
        run_once(kb, project_id=args.project_id)
    else:
        run_polling(kb, project_id=args.project_id, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()