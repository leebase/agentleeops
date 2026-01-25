# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentLeeOps is a multi-agent orchestration framework that combines Kanboard (control plane) with an agentic loop to automate disciplined, artifact-driven software development workflows. It enforces human approval gates to prevent AI hallucinations.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
# Edit .env with your KANBOARD_TOKEN
```

### Prerequisites

1. **Kanboard** running on Docker port 88
2. **MetaMagik Plugin** installed for custom fields (see below)
3. **OpenCode CLI** installed and connected:
   ```bash
   # Verify OpenCode CLI
   opencode --version
   ```
   - Run `/connect` inside OpenCode and select GPT 5.2 Codex

### MetaMagik Plugin Installation

The MetaMagik plugin adds custom field UI to Kanboard task forms.

```bash
# Install plugin in Kanboard container
docker exec -it kanboard sh
cd /var/www/app/plugins
git clone https://github.com/creecros/MetaMagik.git
chown -R nginx:nginx MetaMagik
exit
```

After installation, configure custom fields in **Settings > Custom Fields**:

| Field Name | Type | Required | Notes |
|------------|------|----------|-------|
| `dirname` | Text | Yes | lowercase, digits, dashes only |
| `context_mode` | Dropdown | No | Options: "NEW", "FEATURE" (default: NEW) |
| `acceptance_criteria` | Textarea | No | Multi-line acceptance criteria |
| `complexity` | Dropdown | No | Options: "S", "M", "L", "XL" |

Status fields (agent-managed, read-only):
- `agent_status`: "pending", "running", "completed", "failed"
- `current_phase`: "design", "scaffold", "planning", "coding"

## Running the System

```bash
# One-time board configuration (creates 10-column Kanboard pipeline)
python setup-board.py

# OPTION 1: Webhook mode (recommended - automatic triggers)
python webhook_server.py --port 5000

# OPTION 2: Single-run mode (manual trigger)
python orchestrator.py --once

# OPTION 3: Polling mode (continuous watching)
python orchestrator.py --poll-interval 10
```

### Webhook Setup (Recommended)

1. Start the webhook server:
   ```bash
   python -u webhook_server.py --port 5000
   ```

2. Configure Kanboard:
   - Go to **Settings > Webhooks**
   - Set Webhook URL: `http://172.17.0.1:5000` (no trailing slash!)
   - Save

3. Now when you move a card to "2. Design Draft", the agent runs automatically.

## Architecture

### Core Components

- **Kanboard** (Docker, Port 88): Control plane with 10-column workflow
- **orchestrator.py**: Main daemon that watches columns and triggers agents (supports `--once` mode)
- **webhook_server.py**: HTTP server that receives Kanboard webhooks and triggers agents
- **setup-board.py**: One-time Kanboard configuration script
- **agents/**: Agent implementations (ARCHITECT_AGENT, etc.)
- **lib/**: Shared utilities (workspace management, OpenCode CLI wrapper)
- **prompts/**: Prompt templates for LLM agents

### The 10-Stage Workflow

| Column | Owner | Artifact |
|--------|-------|----------|
| 1. Inbox | Lee | Story card |
| 2. Design Draft | Agent | `DESIGN.md` |
| 3. Design Approved | Lee | Approval gate |
| 4. Repo & Tests Draft | Agent | Repo + `tests/*.py` (must FAIL) |
| 5. Tests Approved | Lee | Approval gate |
| 6. Planning Draft | Agent | `prd.json` |
| 7. Plan Approved | Lee | Approval gate |
| 8. Ralph Loop | Ralph | Source code (tests must PASS) |
| 9. Final Review | Lee | PR/Diff |
| 10. Done | System | Archived |

### Agent Triggers

The orchestrator triggers agents based on column:
- Column 2 → `ARCHITECT_AGENT` (implemented)
- Column 4 → `SCAFFOLD_AGENT` (stub)
- Column 6 → `PM_AGENT` (stub)
- Column 8 → `RALPH_CODER` (stub)

### Context Modes

- **NEW**: Create workspace at `~/projects/<dirname>`, init git repo
- **FEATURE**: Use existing repo at `~/projects/<dirname>`, create `feat/<task_id>-<dirname>` branch

## Critical Rules

1. **Ratchet Effect**: Once Lee approves a design/test/plan, agents cannot regress it without Lee explicitly moving the card back.

2. **Double-Blind Rule**: The implementation agent (Ralph) never writes tests. A separate agent creates tests; Ralph only makes them pass.

3. **Test Integrity (Non-Negotiable)**: Agents must not modify `tests/` unless Lee explicitly moves the card back to Column 4. This prevents "making tests pass by changing the tests."

4. **Artifacts over Chat**: All durable decisions live in version-controlled files (`DESIGN.md`, `prd.json`), not chat.

## Card Input Contract

### Preferred: Custom Fields (MetaMagik)

With the MetaMagik plugin installed, create tasks using the custom field UI:

1. Click "+" to create a new task in Kanboard
2. Fill in the custom fields:
   - **dirname** (required): Project directory name
   - **context_mode**: "NEW" or "FEATURE"
   - **acceptance_criteria**: Multi-line acceptance criteria
   - **complexity**: S, M, L, or XL
3. Save the task

The system reads these fields via Kanboard's metadata API.

### Legacy: YAML Description (Fallback)

For backwards compatibility, the system also supports YAML in the description:

```yaml
dirname: my-project-name
context_mode: NEW  # or FEATURE
acceptance_criteria: |
  - Condition 1
  - Condition 2
```

### dirname Naming Rules

- Lowercase letters, digits, and dashes only
- Cannot start with a dash or dot
- No spaces, slashes, or periods

## Key Files

- `product-definition.md`: Authoritative specification (source of truth)
- `sprintPlan.md`: Persistent sprint tracker (progress visibility for humans and agents)
- `requirements.txt`: Dependencies (kanboard, python-dotenv)
- `orchestrator.py`: Orchestrator entry point
- `webhook_server.py`: Webhook server for automatic triggers
- `setup-board.py`: Board initialization script
- `.env.example`: Environment variable template
- `.env`: Local environment variables (not committed)

### Library Modules (`lib/`)

- `lib/task_fields.py`: Task field handling via metadata API with YAML fallback
- `lib/workspace.py`: Workspace creation and management (NEW/FEATURE modes)
- `lib/opencode.py`: OpenCode CLI wrapper for LLM calls (named opencode.py for historical reasons)

### Agents (`agents/`)

- `agents/architect.py`: ARCHITECT_AGENT - generates DESIGN.md from story cards

### Prompts (`prompts/`)

- `prompts/design_prompt.txt`: Template for DESIGN.md generation

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KANBOARD_URL` | Kanboard JSON-RPC endpoint | `http://localhost:88/jsonrpc.php` |
| `KANBOARD_USER` | Kanboard API user | `jsonrpc` |
| `KANBOARD_TOKEN` | Kanboard API token | (required) |
| `OPENCODE_CMD` | OpenCode CLI binary | `opencode` |
| `OPENCODE_MODEL` | Optional CLI model override | (uses OpenCode config) |
| `OPENCODE_FALLBACK_MODEL` | OpenRouter fallback model | `grok-code-fast` |
| `OPENROUTER_API_KEY` | OpenRouter API key | (optional) |
| `OPENROUTER_API_BASE` | OpenRouter API base | `https://openrouter.ai/api/v1` |

## State Tracking Tags

The orchestrator uses tags to track processing state:
- `design-started` / `design-generated`: ARCHITECT_AGENT state
- `scaffold-started` / `scaffold-generated`: SCAFFOLD_AGENT state
- `planning-started` / `planning-generated`: PM_AGENT state
- `coding-started` / `coding-complete`: RALPH_CODER state

## Artifact Naming Convention

Each project workspace has standard artifact files:
- `DESIGN.md` - Design document
- `prd.json` - Planning document (future)

Artifacts are:
1. Written to the workspace (`~/projects/<dirname>/`)
2. Attached to the Kanboard task

## Current Status

See `sprintPlan.md` for detailed sprint tracking.

### What Works (Sprint 1 Complete)
- `setup-board.py`: Creates 10-column Kanboard workflow
- `orchestrator.py --once`: Manual single-run mode
- `webhook_server.py`: Webhook-triggered automation (recommended)
- **MetaMagik custom fields**: dirname, context_mode, acceptance_criteria, complexity
- `lib/task_fields.py`: Metadata API with YAML fallback
- **ARCHITECT_AGENT**: Full end-to-end flow:
  - Triggers on card move to "2. Design Draft"
  - Creates workspace at `~/projects/<dirname>/`
  - Generates DESIGN.md via LLM
  - Attaches file to Kanboard task
  - Posts status comment

### What Needs Work
1. **SCAFFOLD_AGENT**: Not implemented (stub only) - Sprint 2
2. **PM_AGENT**: Not implemented (stub only) - Sprint 3
3. **RALPH_CODER**: Not implemented (stub only) - Sprint 4
4. **FEATURE mode**: Branch creation not fully tested - Sprint 5

## Next Steps

See `sprintPlan.md` for prioritized sprint backlog.

## Testing the Current Implementation

```bash
# 1. Start webhook server
source .venv/bin/activate
python -u webhook_server.py --port 5000
```

In Kanboard (http://localhost:88):
1. Go to AgentLeeOps project
2. Click "+" to create a new task in "1. Inbox"
3. Fill in the custom fields:
   - **dirname**: `test-project` (required, lowercase/digits/dashes)
   - **context_mode**: Select "NEW" or "FEATURE"
   - **acceptance_criteria**: Enter requirements
   - **complexity**: Select S/M/L/XL
4. Save and drag card to "2. Design Draft"

Verification:
- Check webhook server output for trigger message
- Verify `~/projects/<dirname>/DESIGN.md` created
- Open task in Kanboard - DESIGN.md should be attached
- Comment should show "ARCHITECT_AGENT Completed"

## Troubleshooting

### Webhook not firing
- Check Kanboard logs: `docker logs kanboard --tail 50`
- Ensure URL has no trailing slash: `http://172.17.0.1:5000`
- Test connectivity: `docker exec kanboard wget -q -O- http://172.17.0.1:5000/ --post-data='{}'`

### OpenCode CLI errors
- Verify installed: `opencode --version`
- Re-run `/connect` and confirm the selected model

### Kanboard API errors
- Verify token in `.env` matches `setup-board.py`
- Some APIs (comments, tags) may need different permissions
