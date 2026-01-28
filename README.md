# AgentLeeOps

AgentLeeOps is an orchestration framework for running high-discipline, multi-agent software development workflows on top of Kanboard and a local git workspace. It encodes a strict, artifact-driven process so that work can be resumed, audited, and extended reliably over time.

## Goals

- Enforce a **10-stage Kanboard workflow** from idea intake through final review.
- Preserve **test integrity** by separating authorship of implementation and tests.
- Prefer **written artifacts over chat** for all durable decisions and designs.
- Make the system **resumable** so work can stop and restart without losing context.

## Workflow Overview

AgentLeeOps v1.0 defines a Kanboard pipeline with the following columns (left to right):

1. **Inbox** – New work items arrive, minimally triaged.
2. **Design Draft** – A design agent produces a draft `DESIGN.md` for the card.
3. **Design Approved** – Lee reviews and approves the design.
4. **Repo & Tests Draft** – A tests-focused agent drafts or updates tests.
5. **Tests Approved** – Lee reviews and blesses the tests.
6. **Planning Draft** – An implementation plan is drafted based on approved tests.
7. **Plan Approved** – Lee reviews and approves the implementation plan.
8. **Ralph Loop** – Ralph (the implementation agent) writes code to make tests pass.
9. **Final Review** – Lee performs final review on code and artifacts.
10. **Done** – Work is complete and merged.

Each column has an explicit owner and required artifacts (e.g., `DESIGN.md`, test files, plan documents), as defined in `product-definition.md`.

## Core Rules

- **Ratchet Effect**
  - Once Lee has approved a design, tests, or a plan, agents must not regress these guarantees without Lee explicitly moving the card back to an earlier column.

- **Double-Blind Rule**
  - Ralph (implementation) does not design tests for his own work.
  - A separate tests agent creates or updates tests; Ralph only works to make those tests pass.

- **Test Integrity (Non‑Negotiable)**
  - Agents must not modify anything under `tests/` unless Lee explicitly moves the card back to the "Repo & Tests Draft" column.

- **Artifacts over Chat**
  - Durable decisions, designs, and plans live in version-controlled artifacts (e.g., `DESIGN.md`, plan docs) rather than transient chat.

## Card Input Contract

Every Kanboard card is expected to provide a YAML input block (typically in its description) with at least:

- `dirname` – The project directory name.
- `context_mode` – One of:
  - `NEW` – Create a brand new repository/workspace for this card.
  - `FEATURE` – Work in an existing repository.
- `acceptance_criteria` – A structured list of conditions that must be satisfied for the card to be considered done.

The orchestrator parses this block and uses it to decide how to set up the workspace and what actions to take.

## Context Modes

- **NEW**
  - Create a fresh workspace at `~/projects/<dirname>`.
  - Initialize a new git repository.
  - Scaffold initial structure and configuration according to the design.

- **FEATURE**
  - Use an existing workspace at `~/projects/<dirname>`.
  - Ensure it is up to date (e.g., `git pull`).
  - Create a feature branch for the card and apply changes there.

## Git and Workspace Conventions

- **Workspace root:** `~/projects/<dirname>`.
- **Repository ownership:** typically `leebase/<dirname>`.
- **Branch naming:** `feat/<task_id>-<dirname>`.
- **History:** aim for clean, reviewable commits that reflect artifact checkpoints (design, tests, plan, implementation).

## Running the System

Two modes are available:

### Webhook Mode (Recommended)
```bash
python -u webhook_server.py --port 5000
```
Configure Kanboard webhook URL to `http://<your-ip>:5000/`. Cards moving to trigger columns automatically invoke agents.

### Polling Mode
```bash
python orchestrator.py --poll-interval 10
```

Both modes support all 6 agents: ARCHITECT, GOVERNANCE, PM, SPAWNER, TEST, and RALPH.

See `product-definition.md` for the full workflow specification.

## Development

- Dependencies are listed in `requirements.txt`.
- Use a virtual environment (e.g., `.venv/`) and install with:

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

- **LLM Configuration:** Set `OPENROUTER_API_KEY` in `.env` for production LLM calls
  - Get your API key from: https://openrouter.ai/keys
  - See `config/llm.yaml` for role-based LLM routing configuration
- Legacy: Verify OpenCode CLI: `opencode --version` (optional, for backward compatibility)

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_ratchet.py tests/test_syntax_guard.py -v
```

The test suite (186 tests) covers: ratchet governance, LLM syntax validation, LLM provider abstraction (HTTP & CLI providers), JSON repair monitoring, task field parsing, workspace management, and Sprint 17 production readiness fixes.

## Monitoring & Observability

AgentLeeOps includes comprehensive monitoring tools for LLM operations:

```bash
# View JSON repair patterns and statistics
python tools/repair-monitor.py

# View provider performance metrics
python tools/repair-monitor.py --providers

# View all reports (repair + performance)
python tools/repair-monitor.py --all

# Analyze specific workspace
python tools/repair-monitor.py --workspace ~/projects/myapp

# Export statistics as JSON
python tools/repair-monitor.py --json
```

The monitoring dashboard provides:
- JSON repair rate and method distribution
- Repair patterns by provider, role, and model
- Provider performance metrics (latency, success rate, cost)
- Actionable recommendations for improving JSON mode prompts
- Cost tracking and token usage statistics

## Status

AgentLeeOps is production-ready through Sprint 17 (LLM Provider Abstraction + Post-Review Fixes complete). See `sprintPlan.md` for detailed progress tracking.

**Current capabilities:**
- Full 10-column Kanboard workflow
- 6 agents (Architect, PM, Spawner, Test, Ralph, Governance) - all using LLM abstraction
- Pluggable LLM provider system with role-based routing (Sprint 16-17)
  - OpenRouter HTTP provider with Claude Sonnet 4
  - OpenCode CLI provider with JSON repair (tested: gpt-5.2-codex)
  - Gemini CLI provider with Gemini 3 support (tested: gemini-3-flash-preview)
  - Configuration validation via `python -m lib.llm.doctor`
  - Lazy provider validation (system starts with partial configs)
  - Large prompt handling (stdin fallback for prompts >100KB)
- Ratchet governance with SHA256 hash verification
- LLM syntax guards to prevent refusal injection
- JSON repair for CLI output (trailing commas, unquoted keys, etc.)
- Enhanced observability:
  - Dynamic log field extraction (all LLM context in logs)
  - JSON repair audit trail (metadata in logs/traces)
  - Raw provider output in trace files
  - Trace recording (`.agentleeops/traces/`)
  - Monitoring dashboard for repair patterns and provider performance
- Webhook and polling automation modes
