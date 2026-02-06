# AgentLeeOps - Product Definition v1.7 (Single-Card Lifecycle Edition)

## 1. Executive Summary

AgentLeeOps is an approval-gated delivery system that turns a story into tested code through deterministic lifecycle transitions, immutable approval evidence, and artifact integrity checks.

The control plane can be:
- Kanboard (webhook/polling automation), or
- local CLI orchestration (`tools/workpackage.py`) without board dependency.

## 2. Core Philosophy

- Ratchet governance: approvals create immutable constraints.
- Double-blind testing: implementation and test authorship stay separated.
- Test integrity: approved tests are not mutated during coding flow.
- Artifacts over chat: durable state lives in files, not transient conversation.
- Idempotent recovery: retries are safe after partial failures.

## 3. Lifecycle State Machine (11 Steps)

| # | Column / Stage | Owner | Primary Artifact | Gate / Action |
|---|---|---|---|---|
| 1 | Inbox | Lee | Story card | Intake |
| 2 | Design Draft | Architect | `DESIGN.md` | Draft generated |
| 3 | Design Approved | Lee | Approved design | Lock/review gate |
| 4 | Planning Draft | PM | `prd.json` | Draft generated |
| 5 | Plan Approved | Lee | Approved plan | Lock/review gate |
| 6 | Tests Draft | Test Agent | `TEST_PLAN_*.md` | Draft generated |
| 7 | Tests Approved | Lee | `test_*.py` | Generate + lock tests |
| 8 | Ralph Loop | Ralph | `src/` changes | Implement against locked tests |
| 9 | Code Review | Review Agent | Review reports | Review gate |
| 10 | Final Review | Lee | Final diff/artifacts | Human approval |
| 11 | Done | System | Archived state | Completed |

## 4. Work Package Model (Sprint 1)

Each story maps to a local package:

```text
work-packages/task-<id>/
  manifest.yaml
  approvals/
  artifacts/{design,planning,tests,implementation}
  dashboard/{dashboard.json,dashboard.html}
```

`manifest.yaml` is the canonical local state contract.

## 5. Lifecycle + Approval Events (Sprint 2)

Transitions are deterministic:
- Forward movement is one stage at a time.
- Rollback/reopen to prior stages is supported.
- Every transition records immutable event JSON under `approvals/`.
- Replay/history is available for auditing.

## 6. Artifact Integrity + Freshness (Sprint 3)

Artifacts are indexed and hashed (SHA256) with explicit states:
- `draft`
- `approved`
- `stale`
- `superseded`

Freshness is recomputed after transitions and artifact refresh operations.

## 7. Dashboard Output (Sprint 4)

Canonical dashboard artifacts are generated locally:
- `dashboard/dashboard.json`
- `dashboard/dashboard.html`

Dashboard includes stage status, approval history, artifact states, and local artifact links.

## 8. Single-Card Orchestration Integration (Sprint 5)

Feature flag:

```bash
AGENTLEEOPS_SINGLE_CARD_MODE=1
```

Behavior:
- Kanboard lane movement syncs to local lifecycle.
- Spawner fan-out is disabled in this mode.
- Agent execution is gated by local artifact health.

Legacy multi-card flow remains supported when the flag is off.

## 9. CLI-First + External Adapter Readiness (Sprint 6)

All core lifecycle behavior is callable locally via CLI commands:
- init/validate/transition/sync-stage
- gate/refresh-artifacts/refresh-dashboard
- external mapping (`map-add`, `map-export`, `map-import`)

External provider readiness includes:
- adapter contract in `lib/workitem/adapter_contract.py`
- external reference persistence in work package manifest

## 10. Migration + Hardening (Sprint 7)

Migration:
- `migrate-workspace` imports legacy workspace artifacts into work packages.
- migration report emitted to `migration/migration-report.json`.

Hardening:
- atomic manifest write behavior
- transition failure cleanup for pending event files
- same-stage retry idempotency
- phased rollout and rollback playbook documented

## 11. Safety and Governance Mechanisms

- Ratchet lock enforcement remains mandatory.
- Task tag state machine (`started`, `completed`, `failed`) enables deterministic retries.
- Artifact gates prevent forward progress when required approved artifacts are stale or missing.
- Human approvals remain authoritative at all gate columns.

## 12. Technical Stack

- Control plane: Kanboard JSON-RPC (optional in CLI-first mode)
- Orchestration: `orchestrator.py` + `webhook_server.py`
- Work package services: `lib/workpackage/*`
- Work item abstraction: `lib/workitem/*`
- LLM routing/providers: `lib/llm/*` with role-based config
- Validation: pytest test suite

## 13. Current Product Status

- Sprints 1-7 of the single-card redesign are complete and validated.
- Sprint 8 (OpenCode workspace isolation bug hardening) remains open and tracked in `single-card-redesign-sprint-plan.md`.
