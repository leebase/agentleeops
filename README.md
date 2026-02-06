# AgentLeeOps

AgentLeeOps is an approval-gated software delivery system that combines Kanboard orchestration with local, durable artifacts. It now supports both legacy multi-card fan-out and a single-card lifecycle model backed by local work packages.

## Current Scope (Sprints 1-7)

- 11-stage Kanboard lifecycle with human gates.
- Work package model under `work-packages/task-<id>/`.
- Lifecycle transitions with immutable approval events.
- Artifact integrity tracking (`draft`, `approved`, `stale`, `superseded`).
- Static dashboard output (`dashboard/dashboard.json`, `dashboard/dashboard.html`).
- Single-card mode with local artifact gating.
- CLI-first lifecycle operations (no board required).
- External work-item mapping import/export and adapter contract.
- Migration utility + rollout playbook.

## Workflow Modes

### 1) Legacy Multi-Card Mode

- Plan approval spawns child cards.
- Child cards move through tests/coding lanes individually.
- Existing fan-out workflow remains supported.

### 2) Single-Card Mode (Recommended)

Enable with:

```bash
export AGENTLEEOPS_SINGLE_CARD_MODE=1
```

Behavior:
- Kanboard lane moves sync to local lifecycle state in `work-packages/task-<id>/`.
- Spawner fan-out is disabled.
- Agent actions are gated by local artifact freshness (for example, stale design blocks planning).

## 11-Lane Board

1. Inbox
2. Design Draft
3. Design Approved
4. Planning Draft
5. Plan Approved
6. Tests Draft
7. Tests Approved
8. Ralph Loop
9. Code Review
10. Final Review
11. Done

## Local Work Package Layout

Each task package is materialized as:

```text
work-packages/task-<id>/
  manifest.yaml
  approvals/*.json
  artifacts/
    design/
    planning/
    tests/
    implementation/
  dashboard/
    dashboard.json
    dashboard.html
  migration/
    migration-report.json   # when migration utility is used
```

## Core Rules

- Ratchet governance: approved artifacts are immutable unless intentionally reopened.
- Double-blind testing: implementation and tests are produced by different roles.
- Test integrity: agents do not modify `tests/` unless explicitly in test-authoring flow.
- Idempotent retries: started/failed/completed tag logic auto-unblocks stale states.
- Artifacts over chat: durable state lives in versioned files.

## Running Automation

### Webhook server

```bash
python -u webhook_server.py --port 5000
```

### Polling orchestrator

```bash
python orchestrator.py --poll-interval 10
```

Both modes require Kanboard env vars (`KANBOARD_URL`, `KANBOARD_USER`, `KANBOARD_TOKEN`).

## CLI-First Lifecycle

`tools/workpackage.py` can execute lifecycle work without Kanboard.

Key commands:

```bash
python tools/workpackage.py init --id task-101 --title "Example" --dirname example --context-mode NEW --acceptance "criterion"
python tools/workpackage.py validate --work-package-dir work-packages/task-101
python tools/workpackage.py transition --work-package-dir work-packages/task-101 --to-stage design_draft
python tools/workpackage.py sync-stage --work-package-dir work-packages/task-101 --to-stage plan_approved
python tools/workpackage.py gate --work-package-dir work-packages/task-101 --action PM_AGENT
python tools/workpackage.py refresh-artifacts --work-package-dir work-packages/task-101
python tools/workpackage.py refresh-dashboard --work-package-dir work-packages/task-101
python tools/workpackage.py map-add --work-package-dir work-packages/task-101 --provider jira --external-id PROJ-123
python tools/workpackage.py map-export --work-package-dir work-packages/task-101 --out mapping.json
python tools/workpackage.py map-import --work-package-dir work-packages/task-101 --from-file mapping.json
python tools/workpackage.py migrate-workspace --base-dir work-packages --id task-101 --title "Legacy migration" --dirname legacy --context-mode FEATURE --workspace-dir ~/projects/legacy
```

See:
- `WORKPACKAGE_CLI.md`
- `EXTERNAL_ADAPTER_CONTRACT.md`
- `SINGLE_CARD_ROLLOUT_PLAYBOOK.md`

## Local Kanboard Setup (MetaMagik + Swimlanes)

```bash
docker run -d --name kanboard-local -p 18080:80 kanboard/kanboard:latest
```

Install MetaMagik plugin:

```bash
docker exec kanboard-local sh -lc 'apk add --no-cache git && cd /var/www/app/plugins && git clone --depth 1 https://github.com/creecros/MetaMagik.git'
```

Create Python environment (macOS):

```bash
python3.11 -m venv .macenv
source .macenv/bin/activate
pip install -r requirements.txt
```

Provision board columns/swimlanes/tags:

```bash
KANBOARD_URL=http://127.0.0.1:18080/jsonrpc.php \
KANBOARD_USER=admin \
KANBOARD_TOKEN=admin \
python setup-board.py
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `.venv` came from Linux, use `.macenv` on macOS.

## Testing

```bash
pytest tests/
```

Current full-suite baseline after Sprint 7: `353 passed`.

## Status

Single-card redesign Sprints 1-7 are implemented and validated.
Sprint 8 (OpenCode workspace isolation hardening) remains tracked in `single-card-redesign-sprint-plan.md`.
