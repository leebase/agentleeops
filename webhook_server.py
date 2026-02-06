#!/usr/bin/env python3
"""
AgentLeeOps Webhook Server

Listens for Kanboard webhook events and triggers agents automatically.
Supports all 6 agent triggers matching the orchestrator.

Usage:
    python webhook_server.py
    python webhook_server.py --port 5000
"""

import argparse
import json
import os
import re
import socketserver
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, cast

from dotenv import load_dotenv
from kanboard import Client

from lib.task_fields import get_task_fields, update_status, TaskFieldError, get_task_tags, add_task_tag, has_tag

load_dotenv()


_original_handle_error = socketserver.BaseServer.handle_error
_original_handle_one_request = BaseHTTPRequestHandler.handle_one_request


def _quiet_handle_error(self, request, client_address):
    exc_type, exc, _ = sys.exc_info()
    if isinstance(exc, BrokenPipeError):
        return
    return _original_handle_error(self, request, client_address)


socketserver.BaseServer.handle_error = _quiet_handle_error


def _safe_handle_one_request(self):
    try:
        _original_handle_one_request(self)
    except BrokenPipeError:
        return


BaseHTTPRequestHandler.handle_one_request = _safe_handle_one_request

# --- CONFIGURATION ---
KB_URL = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
KB_USER = os.getenv("KANBOARD_USER", "jsonrpc")
KB_TOKEN = os.getenv("KANBOARD_TOKEN")

# Column triggers - matches orchestrator.py
TRIGGERS = {
    "2. Design Draft": "ARCHITECT_AGENT",
    "3. Design Approved": "GOVERNANCE_AGENT",
    "4. Planning Draft": "PM_AGENT",
    "5. Plan Approved": "SPAWNER_AGENT",
    "6. Tests Draft": "TEST_AGENT",
    "7. Tests Approved": "TEST_CODE_AGENT",
    "8. Ralph Loop": "RALPH_CODER",
    "9. Code Review": "CODE_REVIEW_AGENT",
}

# Tags for state tracking - matches orchestrator.py
TAGS = {
    "ARCHITECT_AGENT": {
        "started": "design-started",
        "completed": "design-generated",
        "failed": "design-failed",
    },
    "GOVERNANCE_AGENT": {
        "started": "locking",
        "completed": "locked",
    },
    "PM_AGENT": {
        "started": "planning-started",
        "completed": "planning-generated",
        "failed": "planning-failed",
    },
    "SPAWNER_AGENT": {
        "started": "spawning-started",
        "completed": "spawned",
        "failed": "spawning-failed",
    },
    "TEST_AGENT": {
        "started": "tests-started",
        "completed": "tests-generated",
        "failed": "tests-failed",
    },
    "TEST_CODE_AGENT": {
        "started": "tests-coding-started",
        "completed": "tests-coding-generated",
        "failed": "tests-coding-failed",
    },
    "RALPH_CODER": {
        "started": "coding-started",
        "completed": "coding-complete",
        "failed": "coding-failed",
    },
    "CODE_REVIEW_AGENT": {
        "started": "review-started",
        "completed": "review-complete",
        "failed": "review-failed",
    },
}

# Events we care about
TRIGGER_EVENTS = ["task.move.column", "task.create"]

NORMALIZED_TRIGGER_MAP = {
    "design draft": "ARCHITECT_AGENT",
    "design approved": "GOVERNANCE_AGENT",
    "planning draft": "PM_AGENT",
    "plan approved": "SPAWNER_AGENT",
    "tests draft": "TEST_AGENT",
    "tests approved": "TEST_CODE_AGENT",
    "ralph loop": "RALPH_CODER",
    "code review": "CODE_REVIEW_AGENT",
}


def get_kb_client() -> Any:
    """Get Kanboard client."""
    if not KB_TOKEN:
        raise RuntimeError("KANBOARD_TOKEN not set")
    token = cast(str, KB_TOKEN)
    return Client(KB_URL, KB_USER, token)


def _normalize_column_title(column_title: str) -> str:
    """Strip numeric prefixes so lane renumbering does not break routing."""
    cleaned = re.sub(r"^\s*\d+\.\s*", "", column_title or "")
    return cleaned.strip().lower()


def resolve_trigger_action(column_title: str) -> str | None:
    """Resolve trigger action from exact or normalized column title."""
    if column_title in TRIGGERS:
        return TRIGGERS[column_title]
    return NORMALIZED_TRIGGER_MAP.get(_normalize_column_title(column_title))


def _replace_task_tags(kb, project_id: int, task_id: int, tags: list[str]) -> None:
    """Replace task tags with deduped values."""
    seen = set()
    ordered = []
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    kb.set_task_tags(project_id=int(project_id), task_id=int(task_id), tags=ordered)


def _remove_task_tag(kb, project_id: int, task_id: int, tag_name: str) -> None:
    """Remove a tag from a task if present."""
    tags = get_task_tags(kb, task_id)
    if tag_name not in tags:
        return
    _replace_task_tags(kb, project_id, task_id, [t for t in tags if t != tag_name])


def _clear_stale_started(kb, project_id: int, task_id: int, agent_tags: dict[str, str]) -> None:
    """Unblock retries when failed and started tags both exist."""
    failed_tag = agent_tags.get("failed")
    started_tag = agent_tags.get("started")
    if not failed_tag or not started_tag:
        return
    tags = get_task_tags(kb, task_id)
    if failed_tag in tags and started_tag in tags:
        _remove_task_tag(kb, project_id, task_id, started_tag)


def _mark_agent_failed(kb, project_id: int, task_id: int, agent_tags: dict[str, str]) -> None:
    """Mark failed state and clear started tag."""
    started_tag = agent_tags.get("started")
    failed_tag = agent_tags.get("failed")
    if started_tag:
        _remove_task_tag(kb, project_id, task_id, started_tag)
    if failed_tag:
        add_task_tag(kb, project_id, task_id, failed_tag)


def _mark_agent_succeeded(kb, project_id: int, task_id: int, agent_tags: dict[str, str]) -> None:
    """Mark success and clear any stale failed tag."""
    add_task_tag(kb, project_id, task_id, agent_tags["completed"])
    failed_tag = agent_tags.get("failed")
    if failed_tag:
        _remove_task_tag(kb, project_id, task_id, failed_tag)


# --- AGENT PROCESSORS ---

def process_architect_task(kb, task_id: int, project_id: int):
    """Process a task in the Design Draft column."""
    from agents.architect import run_architect_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        print(f"  Error: Task #{task_id} not found")
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["ARCHITECT_AGENT"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    if has_tag(tags, agent_tags["completed"]):
        print(f"  Task #{task_id} already processed, skipping")
        return

    if has_tag(tags, agent_tags["started"]):
        print(f"  Task #{task_id} already in progress, skipping")
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
        context_mode = fields.get("context_mode", "NEW")
        acceptance_criteria = fields.get("acceptance_criteria", "")
    except TaskFieldError as e:
        print(f"  Error: {e}")
        kb.create_comment(task_id=task_id, content=f"**ARCHITECT_AGENT Error**\n\n{e}")
        return

    print(f"  Processing: {title} (dirname: {dirname})")

    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="design")

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
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="completed", current_phase="design")
        print(f"  Success: {result.get('design_path', 'DESIGN.md created')}")
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="design")
        print(f"  Failed: {result['error']}")


def process_governance_task(kb, task_id: int, project_id: int):
    """Process a task in an Approved column (Locking)."""
    from agents.governance import run_governance_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    column_id = task['column_id']

    # Get column name for context
    try:
        cols = kb.get_columns(project_id=project_id)
        col_title = next((c['title'] for c in cols if c['id'] == int(column_id)), "")
    except Exception:
        col_title = ""

    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["GOVERNANCE_AGENT"]

    if has_tag(tags, agent_tags["completed"]):
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Governance for: {title}")

    add_task_tag(kb, project_id, task_id, agent_tags["started"])

    result = run_governance_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        column_title=col_title,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        add_task_tag(kb, project_id, task_id, agent_tags["completed"])
        print(f"  Success: Artifacts locked")


def process_pm_task(kb, task_id: int, project_id: int):
    """Process a task in the Planning Draft column."""
    from agents.pm import run_pm_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["PM_AGENT"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    if has_tag(tags, agent_tags["completed"]):
        print(f"  PM Task #{task_id} already processed, skipping")
        return

    if has_tag(tags, agent_tags["started"]):
        print(f"  PM Task #{task_id} already in progress, skipping")
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
        context_mode = fields.get("context_mode", "NEW")
        acceptance_criteria = fields.get("acceptance_criteria", "")
    except TaskFieldError as e:
        print(f"  PM Error: {e}")
        kb.create_comment(task_id=task_id, content=f"**PM_AGENT Error**\n\n{e}")
        return

    print(f"  Processing PM: {title}")

    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="planning")

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
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="completed", current_phase="planning")
        print(f"  Success: prd.json created")
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="planning")
        print(f"  PM Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**PM_AGENT Failed**\n\n{result['error']}")


def process_spawner_task(kb, task_id: int, project_id: int):
    """Process a task in the Plan Approved column (Fan-Out)."""
    from agents.spawner import run_spawner_agent

    # Enforce Governance first
    tags = get_task_tags(kb, task_id)
    _clear_stale_started(kb, project_id, task_id, TAGS["SPAWNER_AGENT"])
    tags = get_task_tags(kb, task_id)
    if not has_tag(tags, TAGS["GOVERNANCE_AGENT"]["completed"]):
        print("  Chaining Governance before Spawning...")
        process_governance_task(kb, task_id, project_id)

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)  # Refresh after governance
    agent_tags = TAGS["SPAWNER_AGENT"]

    if has_tag(tags, agent_tags["completed"]):
        return

    if has_tag(tags, agent_tags["started"]):
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Spawner for: {title}")

    add_task_tag(kb, project_id, task_id, agent_tags["started"])

    result = run_spawner_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        print(f"  Success: Spawned {result.get('count')} child cards")
        kb.create_comment(
            task_id=task_id,
            content=f"**SPAWNER**: Created {result.get('count')} child tasks in 'Tests Draft'."
        )
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        print(f"  Spawner Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**SPAWNER Failed**\n\n{result['error']}")


def process_test_task(kb, task_id: int, project_id: int):
    """Process a task in the Tests Draft column."""
    from agents.test_agent import run_test_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["TEST_AGENT"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    if has_tag(tags, agent_tags["completed"]):
        return

    if has_tag(tags, agent_tags["started"]):
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Test Plan Generation: {title}")

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
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="completed", current_phase="tests")
        print(f"  Success: Created {result.get('test_plan', 'test plan')}")
        kb.create_comment(
            task_id=task_id,
            content=f"**TEST_AGENT**: Created test plan.\n\nReady for Human Review."
        )
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="tests")
        print(f"  Test Agent Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**TEST_AGENT Failed**\n\n{result['error']}")


def process_test_code_task(kb, task_id: int, project_id: int):
    """Process a task in the Tests Approved column (Code Generation)."""
    from agents.test_code_agent import run_test_code_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["TEST_CODE_AGENT"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    # If this is a parent task, fan out test generation to children
    try:
        meta = kb.get_task_metadata(task_id=task_id)
    except Exception:
        meta = {}
    if not meta.get("atomic_id"):
        try:
            links = kb.execute("getAllTaskLinks", task_id=task_id) or []
        except Exception:
            links = []
        child_ids = [l.get("task_id") for l in links if l.get("task_id")]
        child_ids = [int(cid) for cid in child_ids]
        if child_ids:
            try:
                cols = kb.get_columns(project_id=project_id)
                dest_col = next((c for c in cols if "Tests Approved" in c["title"]), None)
                dest_col_id = int(dest_col["id"]) if dest_col else None
            except Exception:
                dest_col_id = None

            print(f"  [Test Code Agent] Parent detected. Generating tests for {len(child_ids)} children...")
            for child_id in child_ids:
                try:
                    if dest_col_id is not None:
                        kb.execute("updateTask", id=child_id, column_id=dest_col_id)
                except Exception:
                    pass
                process_test_code_task(kb, child_id, project_id)
            return

    if has_tag(tags, agent_tags["completed"]):
        # Still enforce governance even if code gen is done
        process_governance_task(kb, task_id, project_id)
        return

    if has_tag(tags, agent_tags["started"]):
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Test Code Generation: {title}")

    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="tests")

    result = run_test_code_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id
    )

    if result["success"]:
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="completed", current_phase="tests")
        print(f"  Success: Created {result.get('test_file', 'test file')}")
        
        # Chain Governance to lock the new tests
        print("  Chaining Governance to lock tests...")
        process_governance_task(kb, task_id, project_id)
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="tests")
        print(f"  Test Code Agent Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**TEST_CODE_AGENT Failed**\n\n{result['error']}")


def process_ralph_task(kb, task_id: int, project_id: int):
    """Process a task in the Ralph Loop column."""
    from agents.ralph import run_ralph_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task['title']
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["RALPH_CODER"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    if has_tag(tags, agent_tags["completed"]):
        return

    if has_tag(tags, agent_tags["started"]):
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Ralph Loop: {title}")

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
        _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="completed", current_phase="coding")
        print(f"  Success: Green Bar in {result.get('iterations', '?')} iterations")
        kb.create_comment(
            task_id=task_id,
            content=f"**RALPH**: Tests passed in {result.get('iterations', '?')} iterations. Code committed."
        )
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="coding")
        print(f"  Ralph Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**RALPH Failed**\n\n{result['error']}")


def process_code_review_task(kb, task_id: int, project_id: int):
    """Process a task in the Code Review column."""
    from agents.code_review import run_code_review_agent

    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        return

    title = task["title"]
    tags = get_task_tags(kb, task_id)
    agent_tags = TAGS["CODE_REVIEW_AGENT"]
    _clear_stale_started(kb, project_id, task_id, agent_tags)
    tags = get_task_tags(kb, task_id)

    if has_tag(tags, agent_tags["completed"]):
        return
    if has_tag(tags, agent_tags["started"]):
        return
    if not has_tag(tags, TAGS["RALPH_CODER"]["completed"]):
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="review")
        kb.create_comment(
            task_id=task_id,
            content="**CODE_REVIEW_AGENT Failed**\n\nMissing `coding-complete` tag. Complete Ralph loop before code review.",
        )
        return

    try:
        fields = get_task_fields(kb, task_id)
        dirname = fields["dirname"]
    except TaskFieldError:
        return

    print(f"  Processing Code Review: {title}")
    add_task_tag(kb, project_id, task_id, agent_tags["started"])
    update_status(kb, task_id, agent_status="running", current_phase="review")

    result = run_code_review_agent(
        task_id=str(task_id),
        title=title,
        dirname=dirname,
        kb_client=kb,
        project_id=project_id,
    )

    if result["success"]:
        if result.get("gate_passed", False):
            _mark_agent_succeeded(kb, project_id, task_id, agent_tags)
            update_status(kb, task_id, agent_status="completed", current_phase="review")
            print(
                f"  Success: status={result.get('overall_status')} findings={result.get('finding_count')}"
            )
        else:
            _mark_agent_failed(kb, project_id, task_id, agent_tags)
            update_status(kb, task_id, agent_status="failed", current_phase="review")
            kb.create_comment(
                task_id=task_id,
                content="**CODE_REVIEW_AGENT Gate Failed**\n\nReview status is FAIL. See `reviews/CODE_REVIEW_NEXT_STEPS.md`.",
            )
    else:
        _mark_agent_failed(kb, project_id, task_id, agent_tags)
        update_status(kb, task_id, agent_status="failed", current_phase="review")
        print(f"  Code Review Failed: {result['error']}")
        kb.create_comment(task_id=task_id, content=f"**CODE_REVIEW_AGENT Failed**\n\n{result['error']}")


def process_task(kb, task_id: int, project_id: int, action: str):
    """Route task to appropriate agent based on column."""
    print(f"  Triggering {action}...")

    if action == "ARCHITECT_AGENT":
        process_architect_task(kb, task_id, project_id)
    elif action == "GOVERNANCE_AGENT":
        process_governance_task(kb, task_id, project_id)
    elif action == "PM_AGENT":
        process_pm_task(kb, task_id, project_id)
    elif action == "SPAWNER_AGENT":
        process_spawner_task(kb, task_id, project_id)
    elif action == "TEST_AGENT":
        process_test_task(kb, task_id, project_id)
    elif action == "TEST_CODE_AGENT":
        process_test_code_task(kb, task_id, project_id)
    elif action == "RALPH_CODER":
        process_ralph_task(kb, task_id, project_id)
    elif action == "CODE_REVIEW_AGENT":
        process_code_review_task(kb, task_id, project_id)


# --- HTTP HANDLER ---

class WebhookHandler(BaseHTTPRequestHandler):
    """Handle incoming webhook requests from Kanboard."""

    def handle(self):
        try:
            super().handle()
        except BrokenPipeError:
            pass

    def finish(self):
        try:
            super().finish()
        except BrokenPipeError:
            pass

    def do_POST(self):
        """Handle POST request (webhook event)."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            # Send response immediately
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # Parse and process event
            try:
                data = json.loads(body)
                self.process_event(data)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {body[:100]}")
            except Exception as e:
                print(f"Error processing webhook: {e}")
        except BrokenPipeError:
            return

    def process_event(self, data):
        """Process a webhook event."""
        event_name = data.get('event_name', '')
        event_data = data.get('event_data', {})

        print(f"\n[Webhook] Event: {event_name}")

        if event_name not in TRIGGER_EVENTS:
            print(f"  Ignoring event: {event_name}")
            return

        task_id = event_data.get('task_id')
        if not task_id:
            print("  Warning: Missing task_id in webhook payload")
            return

        try:
            kb = get_kb_client()
            task = cast(dict, kb.get_task(task_id=int(task_id)))
        except Exception as e:
            print(f"  Error fetching task details: {e}")
            return

        if not task:
            print(f"  Error: Task #{task_id} not found")
            return

        project_id = task.get('project_id')
        column_id = task.get('column_id')

        if not project_id or not column_id:
            print("  Warning: Missing project_id/column_id on task")
            return

        column_name = ""
        try:
            columns = cast(list, kb.get_columns(project_id=int(project_id)))
            for col in columns:
                if str(col['id']) == str(column_id):
                    column_name = col['title']
                    break
        except Exception as e:
            print(f"  Error looking up column: {e}")
            return

        print(f"  Task #{task_id} in column: {column_name}")

        action = resolve_trigger_action(column_name)
        if action:
            process_task(kb, int(task_id), int(project_id), action)
        else:
            print(f"  Column '{column_name}' is not a trigger column")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class QuietHTTPServer(HTTPServer):
    """HTTP server that suppresses BrokenPipeError noise."""

    def handle_error(self, request, client_address):
        exc_type, exc, _ = sys.exc_info()
        if isinstance(exc, BrokenPipeError):
            return
        super().handle_error(request, client_address)


def run_server(port: int = 5000):
    """Run the webhook server."""
    if not KB_TOKEN:
        print("Error: KANBOARD_TOKEN not set in .env")
        sys.exit(1)

    server = QuietHTTPServer(('0.0.0.0', port), WebhookHandler)

    def _handle_error(request, client_address):
        exc_type, exc, _ = sys.exc_info()
        if isinstance(exc, BrokenPipeError):
            return
        HTTPServer.handle_error(server, request, client_address)

    server.handle_error = _handle_error
    print(f"AgentLeeOps Webhook Server")
    print(f"Listening on http://0.0.0.0:{port}")
    print(f"")
    print(f"Configure Kanboard webhook URL to: http://<your-ip>:{port}/")
    print(f"")
    print(f"Triggers:")
    for column, agent in TRIGGERS.items():
        print(f"  - '{column}' -> {agent}")
    print(f"")
    print(f"Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="AgentLeeOps Webhook Server")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)"
    )
    args = parser.parse_args()

    run_server(port=args.port)


if __name__ == "__main__":
    main()
