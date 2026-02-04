# AgentLeeOps

AgentLeeOps is an orchestration framework for running high-discipline, multi-agent software development workflows on top of Kanboard and a local git workspace. It encodes a strict, artifact-driven process so that work can be resumed, audited, and extended reliably over time.

## Goals

- Enforce an **11-stage Kanboard workflow** from idea intake through final review.
- Preserve **test integrity** by separating authorship of implementation and tests.
- Prefer **written artifacts over chat** for all durable decisions and designs.
- Make the system **resumable** so work can stop and restart without losing context.

## Workflow Overview

AgentLeeOps defines a Kanboard pipeline with the following columns (left to right):

1. **Inbox** – New work items arrive, minimally triaged.
2. **Design Draft** – ARCHITECT_AGENT produces `DESIGN.md` for the card.
3. **Design Approved** – Human reviews design; GOVERNANCE_AGENT locks artifacts.
4. **Planning Draft** – PM_AGENT generates `prd.json` with atomic stories.
5. **Plan Approved** – Human reviews plan; SPAWNER_AGENT creates child story cards (remain in this column for human control).
6. **Tests Draft** – TEST_AGENT generates tests for each story (move stories here one at a time).
7. **Tests Approved** – Human reviews tests; GOVERNANCE_AGENT locks test files.
8. **Ralph Loop** – RALPH_CODER implements code to pass tests (move stories here one at a time).
9. **Code Review** – CODE_REVIEW_AGENT runs the review suite and publishes prioritized next steps.
10. **Final Review** – Human performs final review on code, artifacts, and review outputs.
11. **Done** – Work is complete and merged.

**Human-Controlled Story Flow:**
- Parent story stays in "Plan Approved" after spawning
- Child stories are created in "Plan Approved" for editing
- Move each child story to "Tests Draft" → "Tests Approved" → "Ralph Loop" → "Code Review" one at a time
- This prevents explosion of simultaneous LLM calls

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

- **Agent Tag State + Auto-Retry**
  - Each agent uses tags to track progress: `*-started`, `*-complete`, and `*-failed`.
  - On failure, orchestrator/webhook remove `*-started` and add `*-failed` so the task is not stuck.
  - On success, orchestrator/webhook add `*-complete` and clear any stale `*-failed`.
  - If a task has both `*-failed` and `*-started` (legacy/stale state), the system auto-clears `*-started` to unblock retries.

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
See `USER_STORY_WORKFLOW.md` for step-by-step operator instructions.

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

The test suite (257 tests) covers: ratchet governance, LLM syntax validation, LLM provider abstraction (HTTP & CLI providers), JSON repair monitoring, prompt compression, provider health checks, performance profiling, task field parsing, workspace management, and Sprint 17 production readiness fixes.

## Monitoring & Observability

AgentLeeOps includes comprehensive monitoring and health check tools for LLM operations:

### Provider Health Checks

```bash
# Check all configured providers
python -m lib.llm.health

# Check specific provider
python -m lib.llm.health --provider openrouter

# Custom timeout (default: 10s)
python -m lib.llm.health --timeout 30

# Export as JSON
python -m lib.llm.health --json
```

The health check system:
- Tests actual connectivity by making minimal LLM requests
- Reports latency for each provider
- Validates provider configuration and availability
- Supports checking all providers or specific ones
- Returns non-zero exit code if any provider is unhealthy (useful for CI/CD)

### Performance Monitoring

#### JSON Repair and Provider Performance

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

#### Agent Execution Profiling

```bash
# Analyze latest profile
python tools/profile-report.py --latest

# Analyze specific profile
python tools/profile-report.py path/to/profile.json

# Aggregate all profiles in workspace
python tools/profile-report.py --workspace ~/projects/myapp --all

# Export as JSON
python tools/profile-report.py --latest --json

# Hide execution tree
python tools/profile-report.py --latest --no-tree
```

The profiling system:
- Measures execution time for agent operations
- Tracks nested operations (LLM calls, file I/O, git operations)
- Generates statistics (count, total, avg, min, max duration)
- Shows slowest operations
- Displays execution tree with hierarchical timing
- Supports aggregation across multiple runs
- Profiles stored in `.agentleeops/profiles/`

**Using profiler in code:**
```python
from lib.profiler import Profiler, profile

# Context manager
profiler = Profiler()
with profiler.measure("operation_name", metadata="value"):
    # Code to profile
    pass

# Decorator
@profile("my_function")
def my_function():
    pass

# Save profile
profiler.save("profile.json")
```

## Status

AgentLeeOps is production-ready through Sprint 18 (LLM Provider Abstraction + Cleanup & Optimization complete). See `sprintPlan.md` for detailed progress tracking.

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
  - Prompt compression for very large inputs (Sprint 18)
    - Smart compression strategies (whitespace, aggressive, extract)
    - Automatic compression for messages >10KB
    - Token savings estimation and logging
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
