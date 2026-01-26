# AgentLeeOps AGENTS Guide

This file orients automated coding agents working in this repository.

## Workflow Rules (Non-Negotiable)

1.  **Ratchet Effect:**
    -   Check `.agentleeops/ratchet.json` before writing to any file.
    -   If a file is `LOCKED`, you **MUST NOT** overwrite it.
    -   If you need to change a locked file, fail the task and request human intervention.

2.  **Test Integrity (Ralph's Rule):**
    -   You are **strictly forbidden** from modifying any file in `tests/`.
    -   You must never run `git add .`. Always add specific files (e.g., `git add src/`).
    -   If you modify a test file, the orchestrator will reject your work.

3.  **Flood Control (Spawner's Rule):**
    -   Never spawn more than 20 child tasks.
    -   Check for existing child tasks (Idempotency) before creating new ones.

## Agent Triggers

- Column 2 -> `ARCHITECT_AGENT`
- Column 4 -> `PM_AGENT`
- Column 5 -> `SPAWNER_AGENT`
- Column 6 -> `TEST_AGENT`
- Column 8 -> `RALPH_CODER`

## Repository Layout

- `orchestrator.py`: Main daemon.
- `lib/ratchet.py`: **(NEW)** Governance logic for file locking.
- `lib/workspace.py`: Workspace I/O (enforces Ratchet).
- `agents/`: Agent implementations.

## Coding Style & Safety

- **Logging:** Use structured logging (JSON preferred), avoid `print()` for status.
- **Error Handling:** Always clear "started" tags on failure to allow retries.
- **Git:** Use `subprocess` for git commands; always check `returncode`.

## Environment

- `KANBOARD_URL`: Kanboard JSON-RPC endpoint.
- `KANBOARD_TOKEN`: API Token.
- `OPENCODE_CMD`: Path to OpenCode CLI.
