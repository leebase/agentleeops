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
2. **OpenCode CLI** installed and connected:
   ```bash
   # Verify OpenCode CLI
   opencode --version
   ```
   - Run `/connect` inside OpenCode and select GPT 5.2 Codex

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
| 2. Design Draft | Agent | `DESIGN-{task_id}.md` |
| 3. Design Approved | Lee | Approval gate |
| 4. Repo & Tests Draft | Agent | Repo + `tests/*.py` (must FAIL) |
| 5. Tests Approved | Lee | Approval gate |
| 6. Planning Draft | Agent | `prd-{task_id}.json` |
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

4. **Artifacts over Chat**: All durable decisions live in version-controlled files (`DESIGN-{task_id}.md`, `prd-{task_id}.json`), not chat.

## Card Input Contract

Cards use YAML-style description:
```yaml
dirname: my-project-name
context_mode: NEW  # or FEATURE
acceptance_criteria: |
  - Condition 1
  - Condition 2
```

**dirname naming rules**: lowercase, digits and dashes only, no spaces, no leading dot, no slashes, no periods.

## Key Files

- `product-definition.md`: Authoritative specification (source of truth)
- `requirements.txt`: Dependencies (kanboard, python-dotenv)
- `orchestrator.py`: Orchestrator entry point
- `webhook_server.py`: Webhook server for automatic triggers
- `setup-board.py`: Board initialization script
- `.env.example`: Environment variable template
- `.env`: Local environment variables (not committed)

### Library Modules (`lib/`)

- `lib/workspace.py`: Workspace creation and management (NEW/FEATURE modes)
- `lib/opencode.py`: OpenCode CLI wrapper for LLM calls (named opencode.py for historical reasons)

### Agents (`agents/`)

- `agents/architect.py`: ARCHITECT_AGENT - generates DESIGN-{task_id}.md from story cards

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

Each story/task gets its own artifact files named with the task ID:
- `DESIGN-{task_id}.md` - Design document
- `prd-{task_id}.json` - Planning document (future)

Artifacts are:
1. Written to the workspace (`~/projects/<dirname>/`)
2. Attached to the Kanboard task

## Current Status (as of last session)

### What Works
- `setup-board.py`: Creates 10-column Kanboard workflow
- `orchestrator.py --once`: Manual single-run mode
- `ARCHITECT_AGENT`: Generates DESIGN-{task_id}.md using Claude CLI
- Workspace creation (NEW mode)
- File attachment to Kanboard tasks
- `webhook_server.py`: Receives webhooks from Kanboard

### What Needs Work
1. **Webhook column detection**: The webhook server receives events but needs to look up column names from column IDs (partially implemented, needs testing)
2. **SCAFFOLD_AGENT**: Not implemented (stub only)
3. **PM_AGENT**: Not implemented (stub only)
4. **RALPH_CODER**: Not implemented (stub only)
5. **FEATURE mode**: Branch creation not fully tested
6. **Tag management**: Kanboard tag API has permission issues with jsonrpc user

## Next Steps

### Immediate (to complete webhook flow)
1. Test webhook server with card move to "2. Design Draft"
2. Verify ARCHITECT_AGENT triggers automatically
3. Debug any issues with column name lookup

### Phase 2 - Scaffold Agent
1. Create `agents/scaffold.py`
2. Create `prompts/scaffold_prompt.txt`
3. Implement: Create test files that FAIL
4. Wire up to Column 4 trigger

### Phase 3 - PM Agent
1. Create `agents/pm.py`
2. Create `prompts/planning_prompt.txt`
3. Implement: Generate `prd-{task_id}.json`
4. Wire up to Column 6 trigger

### Phase 4 - Ralph Coder
1. Create `agents/ralph.py`
2. Implement: Write code to make tests PASS
3. Wire up to Column 8 trigger

## Testing the Current Implementation

```bash
# 1. Start webhook server
source .venv/bin/activate
python -u webhook_server.py --port 5000

# 2. In Kanboard (http://localhost:88):
#    - Go to AgentLeeOps project
#    - Create card in "1. Inbox" with:
#      dirname: test-project
#      context_mode: NEW
#      acceptance_criteria: |
#        - Feature A
#        - Feature B
#    - Drag card to "2. Design Draft"

# 3. Check webhook server output for trigger
# 4. Verify ~/projects/test-project/DESIGN-{task_id}.md created
# 5. Verify file attached to Kanboard task
```

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
