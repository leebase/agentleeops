# AgentLeeOps AGENTS Guide

This file orients automated coding agents working in this repository.
It summarizes how to build, test, and keep code consistent with the
existing style and workflow rules.

## Quick Commands

### Environment Setup
- Create a virtualenv: `python -m venv .venv`
- Activate (bash/zsh): `source .venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Copy env template: `cp .env.example .env` (then set `KANBOARD_TOKEN`)
- Verify OpenCode CLI: `opencode --version`
- Connect OpenCode to ChatGPT Plus: run `/connect` in OpenCode and select GPT 5.2 Codex
- Ensure Kanboard is running (Docker on port 88)

### Board Setup
- One-time Kanboard column setup: `python setup-board.py`

### Run Core Services
- Webhook mode (recommended): `python -u webhook_server.py --port 5000`
- Orchestrator (polling): `python orchestrator.py`
- Orchestrator (single run): `python orchestrator.py --once`
- Orchestrator (custom interval): `python orchestrator.py --poll-interval 10`

### Webhook Setup
- Kanboard Settings > Webhooks
- URL (no trailing slash): `http://172.17.0.1:5000`
- Trigger: moving a card to "2. Design Draft"

### Tests
There is no committed test suite yet. When tests are introduced, prefer
`pytest` as referenced in `product-definition.md`.

- Run all tests: `pytest`
- Run a single file: `pytest tests/test_example.py`
- Run a single test: `pytest tests/test_example.py -k test_name`
- Run by keyword: `pytest -k "keyword"`

### Linting/Formatting
No lint/format tooling is configured in the repo. If you add one, document
the command here and keep it lightweight (ruff/black/mypy are preferred).

## Repository Layout

- `orchestrator.py`: Main daemon/poller (Kanboard triggers).
- `webhook_server.py`: Webhook-based trigger (HTTP server).
- `setup-board.py`: One-time Kanboard column initialization.
- `agents/`: Agent implementations (only `architect.py` is real today).
- `lib/`: Shared utilities (workspace management, LLM wrapper).
- `prompts/`: Prompt templates (e.g., `design_prompt.txt`).
- `product-definition.md`: Authoritative spec for workflow rules.
- `CLAUDE.md`: Additional operating constraints for assistants.

## Workflow Rules (Non-Negotiable)

- Ratchet Effect: approved artifacts must not be regressed without Lee
  explicitly moving the Kanboard card back to an earlier column.
- Double-Blind Rule: code-writing agent (Ralph) never writes tests.
- Test Integrity: do not modify `tests/` unless the card is in column 4.
- Artifacts over Chat: durable decisions belong in `DESIGN-{task_id}.md`
  and `prd-{task_id}.json`, not transient conversation.

## Agent Triggers

- Column 2 -> `ARCHITECT_AGENT` (implemented).
- Column 4 -> `SCAFFOLD_AGENT` (stub).
- Column 6 -> `PM_AGENT` (stub).
- Column 8 -> `RALPH_CODER` (stub).

## Coding Style Guide (Python)

### Formatting
- Use 4-space indentation, no tabs.
- Keep line length reasonable (~88-100 chars) but follow readability.
- Use triple-double-quote docstrings for modules/classes/functions.
- Prefer f-strings for interpolation.
- Use trailing commas in multi-line literals.

### Imports
- Order: standard library, third-party, then local imports.
- Group imports with a blank line between each group.
- Prefer `pathlib.Path` over `os.path` for filesystem paths.
- Avoid wildcard imports.

### Naming
- Modules/files: lowercase with underscores.
- Functions/variables: `snake_case`.
- Classes/exceptions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- CLI flags: use kebab-case in docs, `argparse` options in code.

### Types
- Use type hints for public functions and key return values.
- Use `Optional[...]` instead of `Union[T, None]`.
- Prefer explicit types for structured return dicts.

### Error Handling
- Raise `ValueError` for input validation failures.
- Raise `RuntimeError` for external system failures (git, CLI calls).
- Use `try/except Exception` only at integration boundaries.
- Log errors with clear context (task id, project id, command).
- For Kanboard interactions, fail gracefully and continue when possible.

### I/O and Subprocesses
- Use `subprocess.run([...], capture_output=True, text=True)`.
- Check `returncode` and raise with stderr on failure.
- Prefer `Path` operations for file reads/writes.
- Use explicit encoding when dealing with binary data (base64, etc.).

### Logging/Output
- Simple `print()` logging is acceptable; avoid noisy debug logs.
- Prefix warnings with "Warning:" or "Error:" when appropriate.
- Do not log secrets or tokens.

## Domain Conventions

- `dirname` must be lowercase, digits/dashes only (no dots or slashes).
- NEW mode creates `~/projects/<dirname>` and initializes git.
- FEATURE mode uses existing repo and creates `feat/<task_id>-<dirname>`.
- Kanboard columns must match names in `TRIGGERS`.
- Tagging in Kanboard uses `design-started`, `design-generated`, etc.

## Environment Variables

- `KANBOARD_URL`: Kanboard JSON-RPC endpoint (default `http://localhost:88/jsonrpc.php`).
- `KANBOARD_USER`: Kanboard API user (default `jsonrpc`).
- `KANBOARD_TOKEN`: Kanboard API token (required).
- `OPENCODE_CMD`: OpenCode CLI binary (default `opencode`).
- `OPENCODE_MODEL`: Optional CLI model override (default uses OpenCode config).
- `OPENCODE_FALLBACK_MODEL`: OpenRouter fallback model (default `grok-code-fast`).
- `OPENROUTER_API_KEY`: OpenRouter API key for fallback requests.
- `OPENROUTER_API_BASE`: OpenRouter API base (default `https://openrouter.ai/api/v1`).

## State Tracking Tags

- `design-started` / `design-generated`: ARCHITECT_AGENT state.
- `scaffold-started` / `scaffold-generated`: SCAFFOLD_AGENT state.
- `planning-started` / `planning-generated`: PM_AGENT state.
- `coding-started` / `coding-complete`: RALPH_CODER state.

## Artifact Naming

- `DESIGN-{task_id}.md`: Design artifact (written to workspace, attached to card).
- `prd-{task_id}.json`: Planning artifact (future).

## Contribution Guidelines for Agents

- Respect existing structure; do not move files without a reason.
- Keep functions short and focused; avoid large monoliths.
- Update `product-definition.md` if you change workflow behavior.
- Update this `AGENTS.md` when adding new commands, tools, or rules.
- Avoid changing `.env` and never commit secrets.

## No Cursor/Copilot Rules Found

No additional rules exist in `.cursor/rules/`, `.cursorrules`, or
`.github/copilot-instructions.md` at this time.
