# Single-Card Rollout Playbook

## Goal

Migrate from multi-card fan-out to single-card lifecycle orchestration with low operational risk.

## Phase 0: Readiness

1. Verify `AGENTLEEOPS_SINGLE_CARD_MODE` is supported in deployed orchestrator/webhook.
2. Validate `tools/workpackage.py` commands locally (`sync-stage`, `gate`, `migrate-workspace`).
3. Confirm board metadata contract is stable (`dirname`, `context_mode`, `acceptance_criteria`).

## Phase 1: Pilot (1-2 stories)

1. Select representative stories with moderate complexity.
2. Run `migrate-workspace` to seed work packages from existing artifacts.
3. Enable `AGENTLEEOPS_SINGLE_CARD_MODE=1`.
4. Move only pilot cards through columns; verify no child-card fan-out occurs.
5. Capture migration report + lifecycle/dashboard outputs per pilot.

## Phase 2: Controlled Expansion

1. Expand to one project lane or swimlane at a time.
2. Monitor gate-block causes (stale artifacts, missing approvals) and tune operator guidance.
3. Keep legacy mode available for emergency fallback during expansion.

## Phase 3: Default On

1. Set single-card mode as default deployment configuration.
2. Retain documented rollback toggle for at least one release cycle.
3. Require migration reports for any legacy project entering active development.

## Rollback Plan

1. Disable single-card mode (`AGENTLEEOPS_SINGLE_CARD_MODE=0`).
2. Resume legacy multi-card flow from current Kanboard columns.
3. Preserve generated `work-packages/` directories for audit; do not delete.
4. Record rollback reason and impacted task IDs in incident notes.

## Operational Checklist

- Full regression suite passes before each rollout phase.
- At least one live smoke story passes per phase with no fan-out regressions.
- Migration reports and dashboard artifacts are retained for traceability.
