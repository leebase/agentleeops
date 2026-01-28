# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentLeeOps is a multi-agent orchestration framework that combines Kanboard (control plane) with an agentic loop to automate disciplined, artifact-driven software development workflows. It enforces human approval gates to prevent AI hallucinations.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your KANBOARD_TOKEN
```

**Prerequisites:**
- Kanboard running on Docker port 88 with MetaMagik plugin
- LLM provider configured (OpenRouter API key OR OpenCode CLI installed)

## Running the System

```bash
# One-time board setup (creates 10-column workflow)
python setup-board.py

# Webhook mode (recommended)
python -u webhook_server.py --port 5000

# Or polling mode
python orchestrator.py --poll-interval 10

# Or single-run mode
python orchestrator.py --once
```

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_atomic_01.py

# Run with verbose output
pytest -v tests/

# Validate LLM configuration
python -m lib.llm.doctor --config config/llm.yaml

# Monitor JSON repair patterns and provider performance
python tools/repair-monitor.py
python tools/repair-monitor.py --providers
python tools/repair-monitor.py --all
```

## Architecture

### Data Flow

```
Kanboard (Port 88) → Webhook Server → Orchestrator → Agents → ~/projects/<dirname>/
                                           ↓
                                    lib/ (shared utilities)
```

### Agent Pipeline (Column-Based Triggers)

| Column | Agent | Artifact | Key Function |
|--------|-------|----------|--------------|
| 2. Design Draft | ARCHITECT_AGENT | `DESIGN.md` | `agents/architect.py` |
| 3. Design Approved | GOVERNANCE_AGENT | Locks artifacts | `agents/governance.py` |
| 4. Planning Draft | PM_AGENT | `prd.json` | `agents/pm.py` |
| 5. Plan Approved | SPAWNER_AGENT | Child task cards | `agents/spawner.py` |
| 6. Tests Draft | TEST_AGENT | `tests/test_*.py` | `agents/test_agent.py` |
| 7. Tests Approved | GOVERNANCE_AGENT | Locks tests | `agents/governance.py` |
| 8. Ralph Loop | RALPH_CODER | Source code | `agents/ralph.py` |

### Key Library Modules

- `lib/task_fields.py`: Task field handling (metadata API with YAML fallback)
- `lib/workspace.py`: Workspace creation (`~/projects/<dirname>/`) and `safe_write_file()`
- `lib/llm/`: LLM provider abstraction (Sprint 16-17)
  - `client.py`: Role-based LLM client
  - `config.py`: Configuration loading from `config/llm.yaml`
  - `providers/`: Provider implementations (OpenRouter HTTP, OpenCode CLI, Gemini CLI)
  - `json_repair.py`: JSON repair for CLI output
  - `doctor.py`: Configuration validation command
- `lib/ratchet.py`: File locking/integrity via `.agentleeops/ratchet.json`
- `lib/logger.py`: Structured JSON logging
- `lib/trace.py`: Trace store for observability

### Ratchet System (`lib/ratchet.py`)

The Ratchet enforces the "no regression" rule:
- `lock_artifact(workspace, path)`: Hashes and locks a file after human approval
- `verify_integrity(workspace, path)`: Confirms file matches locked hash
- `check_write_permission(workspace, path)`: Returns False if file is locked
- Lock manifest stored in `<workspace>/.agentleeops/ratchet.json`

### Ralph's Integrity Guards (`agents/ralph.py`)

Ralph (implementation agent) has strict constraints:
1. Before coding: `verify_integrity()` confirms test file is unmodified
2. Before commit: `verify_no_test_changes()` ensures no `tests/` files are staged
3. Only stages source files explicitly: `git add src/filename.py`

## Critical Rules

1. **Ratchet Effect**: Once Lee approves an artifact, agents cannot modify it without Lee moving the card back.

2. **Double-Blind Rule**: Ralph never writes tests. TEST_AGENT creates tests; Ralph only makes them pass.

3. **Test Integrity (Non-Negotiable)**: Agents must not modify `tests/` after approval. Enforced by hash verification and git staging guards.

4. **Artifacts over Chat**: All decisions live in version-controlled files (`DESIGN.md`, `prd.json`), not transient chat.

## Card Input Contract

Create tasks in Kanboard with these custom fields (MetaMagik):
- `dirname` (required): Project directory name (lowercase, digits, dashes only)
- `context_mode`: "NEW" (create workspace) or "FEATURE" (use existing)
- `acceptance_criteria`: Multi-line requirements
- `complexity`: S, M, L, or XL

Fallback: YAML block in task description.

## State Tracking

Orchestrator uses tags to prevent re-processing:
- `design-started` / `design-generated`
- `planning-started` / `planning-generated`
- `tests-started` / `tests-generated`
- `coding-started` / `coding-complete`
- `locking` / `locked`
- `spawning-started` / `spawned`

## LLM Configuration (Sprint 16-18)

AgentLeeOps uses a pluggable LLM provider system defined in `config/llm.yaml`:

```yaml
llm:
  default_role: planner

  providers:
    openrouter:  # HTTP API provider (recommended)
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"

    opencode:  # CLI provider (optional)
      type: opencode_cli
      command: "opencode"

  roles:
    planner:  # For DESIGN.md, prd.json, tests
      provider: openrouter
      model: "anthropic/claude-sonnet-4"
      temperature: 0.2

    coder:  # For Ralph's implementation loop
      provider: openrouter
      model: "anthropic/claude-sonnet-4"
      temperature: 0.1
```

**Usage in agents:**
```python
from lib.llm import LLMClient

llm = LLMClient.from_config("config/llm.yaml", workspace=workspace)
response = llm.complete(
    role="planner",  # or "coder"
    messages=[{"role": "user", "content": prompt}],
)
design_content = response.text
```

**Validate configuration:**
```bash
python -m lib.llm.doctor --config config/llm.yaml
```

**Advanced features (Sprint 18):**
```python
# Prompt compression for large inputs
response = llm.complete(
    role="planner",
    messages=messages,
    compress=True,  # or "smart", "whitespace", "aggressive", "extract"
)

# Check provider health
python -m lib.llm.health --provider openrouter

# Profile agent execution
from lib.profiler import Profiler
profiler = Profiler()
with profiler.measure("operation", metadata="value"):
    # Code to profile
    pass
profiler.save("profile.json")
```

## Monitoring & Observability (Sprint 18)

**Provider Health Checks:**
```bash
python -m lib.llm.health                    # Check all providers
python -m lib.llm.health --provider NAME    # Check specific provider
python -m lib.llm.health --json             # JSON output
```

**JSON Repair Monitoring:**
```bash
python tools/repair-monitor.py              # Repair patterns
python tools/repair-monitor.py --providers  # Provider metrics
python tools/repair-monitor.py --all        # Full report
```

**Performance Profiling:**
```bash
python tools/profile-report.py --latest     # Latest profile
python tools/profile-report.py --all        # Aggregate all profiles
python tools/profile-report.py --json       # JSON output
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KANBOARD_URL` | JSON-RPC endpoint (default: `http://localhost:88/jsonrpc.php`) |
| `KANBOARD_USER` | API user (default: `jsonrpc`) |
| `KANBOARD_TOKEN` | API token (required) |
| **LLM Providers** | |
| `OPENROUTER_API_KEY` | OpenRouter API key (required for openrouter_http provider) |
| `OPENCODE_CMD` | OpenCode CLI binary (default: `opencode`, optional for opencode_cli provider) |

## Key Files

- `orchestrator.py`: Main daemon, routes cards to agents based on column
- `webhook_server.py`: HTTP server for Kanboard webhook events
- `setup-board.py`: One-time Kanboard column configuration
- `product-definition.md`: Authoritative specification
- `sprintPlan.md`: Sprint tracker for progress visibility
