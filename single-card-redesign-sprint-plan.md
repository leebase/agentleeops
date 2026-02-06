# Single Card Redesign - Sprint Plan

**Status:** IN PROGRESS (planning only, implementation not started)

## Status Legend

- `NOT_STARTED`: Step not yet begun
- `IN_PROGRESS`: Work actively underway
- `BLOCKED`: Waiting on decision or dependency
- `DONE`: Completed and validated

## Planning Principles

- Every sprint must end with a functional vertical slice.
- Every sprint must have an explicit exit test.
- Every sprint must leave a checkpoint artifact so work can resume with low context.
- No sprint depends on hidden chat context; state lives in repo artifacts.

## Sprint 1 - Core Work Package Model

**Goal:** Establish a single work package as the source of truth.

1. Define `WorkPackage` schema v1 (`manifest` fields, stage config, owners). `Status: DONE`
2. Define canonical local directory layout for stage artifacts. `Status: DONE`
3. Implement bootstrap path to create a new work package folder from card input. `Status: DONE`
4. Add manifest validation (schema + required fields). `Status: DONE`

**Functional Outcome**
- A work package can be initialized locally and validated without stage automation.

**Exit Test**
- Initialize one sample package and pass schema validation with no manual edits.

**Checkpoint Artifacts**
- `work-packages/<id>/manifest.yaml`
- `work-packages/<id>/artifacts/`
- Initial validation report/log

**Sprint 1 Validation (2026-02-06)**
- ✅ `pytest tests/` passed (`322 passed`) using local Kanboard env vars
- ✅ Work package bootstrap + validate succeeded via `tools/workpackage.py`
- ✅ Live Kanboard smoke flow executed with orchestrator/webhook + MetaMagik metadata

## Sprint 2 - Lifecycle State Machine + Approval Events

**Goal:** Make card movement equivalent to stage approval in local state.

1. Define ordered lifecycle states and transition rules. `Status: NOT_STARTED`
2. Implement transition engine with precondition checks. `Status: NOT_STARTED`
3. Record immutable approval event per stage transition. `Status: NOT_STARTED`
4. Implement rollback/reopen semantics (what gets unlocked and what stays historical). `Status: NOT_STARTED`

**Functional Outcome**
- Stage transitions can be executed locally with durable approval history.

**Exit Test**
- Run a transition sequence on a sample package and verify approval events are written and replayable.

**Checkpoint Artifacts**
- `work-packages/<id>/approvals/*.json`
- Lifecycle replay output from event history

## Sprint 3 - Artifact Integrity + Stale Detection

**Goal:** Detect artifact drift after approval.

1. Implement artifact indexing for all stage directories. `Status: NOT_STARTED`
2. Compute and persist integrity hashes for tracked artifacts. `Status: NOT_STARTED`
3. Add state model per artifact (`draft`, `approved`, `stale`, `superseded`). `Status: NOT_STARTED`
4. Implement stale recomputation after file change and transition events. `Status: NOT_STARTED`

**Functional Outcome**
- Approved artifacts automatically become stale when modified.

**Exit Test**
- Approve a stage, modify one approved artifact, and confirm stale status is surfaced deterministically.

**Checkpoint Artifacts**
- Updated `manifest.yaml` artifact registry
- Hash snapshot data
- Staleness evaluation log

## Sprint 4 - Dashboard Data + Static HTML

**Goal:** Provide local visibility into lifecycle and artifact health.

1. Generate canonical dashboard data file from manifest + approvals + artifact states. `Status: NOT_STARTED`
2. Render static `dashboard.html` from dashboard data. `Status: NOT_STARTED`
3. Add links to stage artifacts and approval history in dashboard output. `Status: NOT_STARTED`
4. Trigger dashboard refresh on transition and artifact update events. `Status: NOT_STARTED`

**Functional Outcome**
- A local HTML file shows stage status, approvals, freshness, and artifact links.

**Exit Test**
- Open the dashboard locally and verify it reflects one stale artifact and one approved stage correctly.

**Checkpoint Artifacts**
- `work-packages/<id>/dashboard/dashboard.json`
- `work-packages/<id>/dashboard/dashboard.html`

## Sprint 5 - Single-Card Orchestration Integration

**Goal:** Replace multi-card fan-out with single-card lifecycle orchestration.

1. Introduce a work item adapter interface (Kanban-independent contract). `Status: NOT_STARTED`
2. Implement Kanban adapter that maps card moves to lifecycle transitions. `Status: NOT_STARTED`
3. Gate stage automation off local artifact state, not card proliferation. `Status: NOT_STARTED`
4. Add feature flag for legacy multi-card vs new single-card mode. `Status: NOT_STARTED`

**Functional Outcome**
- A single card can drive the full lifecycle while local artifacts remain authoritative.

**Exit Test**
- Run one end-to-end story in single-card mode without creating child cards.

**Checkpoint Artifacts**
- Adapter configuration
- Transition audit log for one full run

## Sprint 6 - CLI-First Flow + External Adapter Readiness

**Goal:** Make the model portable beyond Kanban.

1. Add CLI commands for init, transition, validate, and dashboard refresh. `Status: NOT_STARTED`
2. Ensure all orchestration logic is callable without Kanban dependencies. `Status: NOT_STARTED`
3. Define adapter contract for future Jira/ADO integrations. `Status: NOT_STARTED`
4. Add import/export mapping for external work item identifiers. `Status: NOT_STARTED`

**Functional Outcome**
- Same lifecycle can run locally through CLI with no board required.

**Exit Test**
- Execute full lifecycle for a sample package using CLI only.

**Checkpoint Artifacts**
- CLI command usage docs
- Adapter contract documentation

## Sprint 7 - Migration, Hardening, and Rollout

**Goal:** Safely migrate existing work and reduce operational risk.

1. Build migration utility from current multi-card projects to single-card work packages. `Status: NOT_STARTED`
2. Add interruption recovery tests (mid-transition crash, partial writes, re-run idempotency). `Status: NOT_STARTED`
3. Add regression tests for ratchet/test-integrity constraints in new model. `Status: NOT_STARTED`
4. Publish rollout playbook with phased adoption and rollback plan. `Status: NOT_STARTED`

**Functional Outcome**
- Existing projects can migrate with reproducible state and safety guarantees intact.

**Exit Test**
- Migrate at least one representative existing project and complete one lifecycle in new mode.

**Checkpoint Artifacts**
- Migration report
- Hardening test report
- Rollout checklist

## Sprint 8 - OpenCode Workspace Isolation Bug

**Goal:** Eliminate OpenCode CLI writes outside the intended story workspace.

**Interim Mitigation**
- For active delivery sprints, do not route roles to `opencode_cli`.
- Use an alternate provider (for example Codex CLI/OpenAI provider) until this sprint is complete.

1. Reproduce bug with a deterministic integration test (wrong cwd causes edits in repo root). `Status: NOT_STARTED`
2. Enforce explicit provider `cwd` propagation from `LLMClient` workspace into CLI providers. `Status: NOT_STARTED`
3. Add provider-level validation for invalid/nonexistent `cwd` values. `Status: NOT_STARTED`
4. Add regression tests for `opencode_cli` and `gemini_cli` to verify `subprocess.run(..., cwd=...)`. `Status: NOT_STARTED`
5. Validate end-to-end by running a Kanboard story and confirming all generated artifacts stay under `~/projects/<dirname>/`. `Status: NOT_STARTED`

**Functional Outcome**
- CLI providers are workspace-safe and cannot leak generated files into the orchestrator repo.

**Exit Test**
- A full story flow (Design -> Planning -> Tests -> Ralph) produces no generated artifacts in `/Users/leeharrington/projects/agentleeops`.

**Checkpoint Artifacts**
- Reproduction log and failing test case
- Provider patch diff and passing regression tests
- Post-fix Kanboard smoke-run report

## Operating Cadence

- Update each step status in this file at the end of each work session.
- Only mark `DONE` after the sprint exit test passes.
- If a step fails validation, set `BLOCKED` with a brief note and open a follow-up step in the next sprint.
