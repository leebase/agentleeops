# State of the Union (February 6, 2026)

## Executive Summary

Single-card redesign Sprints 1-7 are complete, validated, documented, and pushed to `master`.
The platform now supports deterministic local lifecycle state, artifact freshness gating, dashboard output, CLI-first orchestration, migration utilities, and rollout guidance.

## What Is Working

- Work package bootstrap and schema validation (`manifest.yaml`).
- Lifecycle transitions with immutable approval events and replay history.
- Artifact hash indexing with stale/superseded detection.
- Dashboard data + HTML rendering from lifecycle/artifact state.
- Single-card orchestrator mode with local gating and fan-out bypass.
- CLI-first lifecycle execution without Kanboard dependency.
- External work item mapping import/export and adapter contract scaffolding.
- Migration path from legacy workspace artifacts into work packages.
- Transition hardening for partial-write cleanup and idempotent retries.

## Sprint Commit Trail (Sprints 3-7)

- `507eaa3` - Sprint 3: artifact integrity registry and stale detection
- `c93df17` - Sprint 4: dashboard generation and auto-refresh
- `3d94044` - Sprint 5: single-card adapter and orchestration gates
- `5bc1c03` - Sprint 6: CLI-first orchestration and external mapping contract
- `47a6145` - Sprint 7: migration utility, transition hardening, rollout playbook

## Validation Snapshot

- Sprint 3 full suite: `338 passed`
- Sprint 4 full suite: `341 passed`
- Sprint 5 full suite: `345 passed`
- Sprint 6 full suite: `349 passed`
- Sprint 7 full suite: `353 passed`

Live smoke outcomes included:
- single-card Plan Approved flow with no child-card links created in single-card mode
- CLI migration run producing a migration report and dashboard outputs

## Current Operating Guidance

- Prefer single-card mode for new work:

```bash
export AGENTLEEOPS_SINGLE_CARD_MODE=1
```

- Keep Kanboard metadata contract stable (`dirname`, `context_mode`, `acceptance_criteria`).
- Use `tools/workpackage.py` for local lifecycle, gate checks, mapping, and migration operations.

## Remaining Tracked Item

- Sprint 8 remains open: OpenCode workspace isolation bug hardening.
- Interim mitigation remains valid: route active delivery through Codex CLI paths and avoid OpenCode for production flow until Sprint 8 completes.
