# AGENTS.md

**AgentLeeOps – Agent Operating Model & Repo Rules**

This file guides all coding agents operating in this repository. It merges safety rules, execution model, and repo-specific developer workflow.

---

## 1) Non-Negotiable Safety Rules

- **Ratchet governance:** Approved artifacts (designs/tests/schemas/configs) are immutable. Do not overwrite, delete/recreate, or bypass ratchet checks. If changes are required, create a new version or new work item.
- **Test immutability (double-blind):** Tests are the contract. Do not edit tests to make code pass. Implementation must conform to tests.
- **Human gates:** Humans approve designs, tests, and state transitions. Agents never bypass approvals.
- **Determinism > creativity:** Prefer existing tools/libraries/helpers; avoid ad-hoc logic or reimplementation.
- **Idempotency:** Actions must be safe to retry; assume partial state and failures.

---

## 2) Operating Model (Layered)

- **Directive layer:** Intent and artifacts (e.g., DESIGN.md, prd.json, policies).
- **Orchestration layer:** Decide what happens next (state machine, agent selection, capability checks).
- **Execution layer:** Deterministic operations (LLM calls, file ops, validation). Do not embed orchestration logic inside execution code.

---

## 3) Build / Lint / Test Commands

### Environment setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Build
- No explicit build step in this repo; run Python entrypoints directly (e.g., `python orchestrator.py`).

### Lint / Format
- No repo-configured lint/format tool detected. Follow style conventions below.

### Tests (pytest)
```bash
# All tests
pytest tests/

# Multiple specific modules
pytest tests/test_ratchet.py tests/test_syntax_guard.py -v

# Single test file
pytest tests/test_atomic_01.py

# Single test case (pytest node id)
pytest tests/test_workitem_client.py::test_parse_task_fields -v
```

### LLM utilities (repo tools)
```bash
python -m lib.llm.doctor --config config/llm.yaml
python -m lib.llm.health --provider openrouter
python tools/repair-monitor.py --all
python tools/profile-report.py --latest
```

---

## 4) Code Style Guidelines

### Python conventions
- **Formatting:** 4-space indentation, PEP 8 spacing, 1 blank line between logical blocks, 2 blank lines between top-level defs.
- **Imports:** Standard library → third-party → local, separated by a blank line. Prefer explicit imports.
- **Typing:** Use PEP 604 unions (`Path | None`), `list[dict[str, str]]`, and `typing.Any` when needed. Type hints encouraged for public interfaces and complex data.
- **Naming:** `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Docstrings:** Triple-quoted docstrings for modules and non-trivial functions.

### Error handling
- Use specific exceptions when possible; use broad `except Exception` only to isolate external dependencies and return a structured failure.
- Prefer returning `{ "success": bool, "error": str }` patterns in agent flows (see `agents/*.py`).
- Preserve context in error messages; avoid swallowing errors without logging.

### Logging
- Use structured logging via `lib.logger.get_logger()` and pass `extra` fields for context (agent, task_id, etc.).
- Avoid printing secrets; CLI scripts may use `print()` for user-facing output.

### Filesystem and subprocess
- Prefer `pathlib.Path` for paths.
- Use `subprocess.run([...], capture_output=True, text=True)` and check `returncode`.
- Respect ratchet guard: use `lib.workspace.safe_write_file()` for artifact writes.

---

## 5) Repo-Specific Constraints

- Do not modify files under `tests/` unless the card is explicitly moved back to a test-authoring state.
- Ratcheted artifacts are locked via `.agentleeops/ratchet.json` and must not be modified.
- Workspace naming rules: lowercase letters, digits, and dashes only; no dots or slashes.

---

## 6) Cursor / Copilot Rules

- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files detected in this repo.

---

*This file exists to keep AgentLeeOps fast, correct, and safe.*
