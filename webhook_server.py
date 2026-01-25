#!/usr/bin/env python3
"""
AgentLeeOps Webhook Server

Listens for Kanboard webhook events and triggers agents automatically.
When a task is moved to "2. Design Draft", runs ARCHITECT_AGENT.

Usage:
    python webhook_server.py
    python webhook_server.py --port 5000
"""

import argparse
import json
import os
import socketserver
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, cast

from dotenv import load_dotenv
from kanboard import Client

from lib.task_fields import get_task_fields, update_status, TaskFieldError

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

# Column that triggers ARCHITECT_AGENT
DESIGN_DRAFT_COLUMN = "2. Design Draft"

# Tags for state tracking
TAGS = {
    "started": "design-started",
    "completed": "design-generated",
}

# Events we care about
TRIGGER_EVENTS = ["task.move.column", "task.create"]


def get_kb_client() -> Any:
    """Get Kanboard client."""
    if not KB_TOKEN:
        raise RuntimeError("KANBOARD_TOKEN not set")
    token = cast(str, KB_TOKEN)
    return Client(KB_URL, KB_USER, token)


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


def process_design_draft(task_id: int, project_id: int):
    """Process a task that landed in Design Draft column."""
    from agents.architect import run_architect_agent

    kb = get_kb_client()

    # Get task details
    task = cast(dict, kb.get_task(task_id=task_id))
    if not task:
        print(f"  Error: Task #{task_id} not found")
        return

    title = task['title']

    tag_names = get_task_tags(kb, task_id)

    if TAGS["completed"] in tag_names:
        print(f"  Task #{task_id} already processed, skipping")
        return

    if TAGS["started"] in tag_names:
        print(f"  Task #{task_id} already in progress, skipping")
        return

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
        return

    print(f"  Processing: {title}")
    print(f"    dirname: {dirname}")
    print(f"    context_mode: {context_mode}")

    # Mark as started (tag + metadata)
    add_task_tag(kb, project_id, task_id, TAGS["started"])
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
        add_task_tag(kb, project_id, task_id, TAGS["completed"])
        update_status(kb, task_id, agent_status="completed", current_phase="design")
        print(f"  Success: {result['design_path']}")
    else:
        update_status(kb, task_id, agent_status="failed", current_phase="design")
        print(f"  Failed: {result['error']}")


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

        print(f"  Task #{task_id} moved to column: {column_name}")

        if column_name == DESIGN_DRAFT_COLUMN:
            print("  Triggering ARCHITECT_AGENT...")
            process_design_draft(int(task_id), int(project_id))
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
    print(f"  - Task moved to '{DESIGN_DRAFT_COLUMN}' -> ARCHITECT_AGENT")
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
