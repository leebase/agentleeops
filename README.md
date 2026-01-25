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

## Orchestrator

The main entrypoint is `orchestrator.py`, which is responsible for:

- Reading the Kanboard card metadata.
- Parsing the YAML input contract (dirname, context_mode, acceptance_criteria).
- Preparing the workspace according to context mode.
- Driving agents through the Kanboard columns and ensuring required artifacts are produced.

See `product-definition.md` for the full, authoritative specification of the workflow and rules.

## Development

- Dependencies are listed in `requirements.txt`.
- Use a virtual environment (e.g., `.venv/`) and install with:

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

- Verify OpenCode CLI: `opencode --version`
- Connect OpenCode to ChatGPT Plus: run `/connect` in OpenCode and select GPT 5.2 Codex

- Run tests with the project’s configured test runner (e.g., `pytest` or Playwright) once the test suite and tooling are wired up.

## Status

AgentLeeOps is currently under active development. The `product-definition.md` file is the source of truth for intended behavior and should be kept in sync with any changes to the workflow or tooling.
