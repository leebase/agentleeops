# User Guide: Running a Story End-to-End

This guide covers current AgentLeeOps execution after single-card redesign Sprints 1-7.

## Choose an Operating Mode

### Mode A: Single-Card (Recommended)

- Enable `AGENTLEEOPS_SINGLE_CARD_MODE=1`.
- Keep one card moving through all lanes.
- Local package `work-packages/task-<id>/` is authoritative for lifecycle and artifacts.
- Spawner fan-out is disabled.

### Mode B: Legacy Multi-Card

- Default when single-card mode is off.
- Plan Approved can still spawn child cards.
- Use if you explicitly want parent/child fan-out behavior.

## Lanes and Human Gates

1. `1. Inbox` - intake.
2. `2. Design Draft` - ARCHITECT_AGENT writes design artifact.
3. `3. Design Approved` - human gate.
4. `4. Planning Draft` - PM_AGENT writes planning artifact.
5. `5. Plan Approved` - human gate.
6. `6. Tests Draft` - TEST_AGENT writes test plan artifacts.
7. `7. Tests Approved` - human gate; test code generation/lock flow.
8. `8. Ralph Loop` - implementation against test contract.
9. `9. Code Review` - review agent gate artifacts.
10. `10. Final Review` - human final approval.
11. `11. Done` - completion.

Required human approvals remain at:
- `3. Design Approved`
- `5. Plan Approved`
- `7. Tests Approved`
- `10. Final Review`

## Services Required for Board Automation

Run both processes from repo root:

```bash
python -u webhook_server.py --port 5000
python orchestrator.py --poll-interval 10
```

Verify quickly:

```bash
tail -n 5 webhook_server.out
tail -n 5 orchestrator.out
```

## Local Kanboard Setup (MetaMagik + Swimlanes)

```bash
docker run -d --name kanboard-local -p 18080:80 kanboard/kanboard:latest
```

Install MetaMagik:

```bash
docker exec kanboard-local sh -lc 'apk add --no-cache git && cd /var/www/app/plugins && git clone --depth 1 https://github.com/creecros/MetaMagik.git'
```

Provision board layout:

```bash
KANBOARD_URL=http://127.0.0.1:18080/jsonrpc.php \
KANBOARD_USER=admin \
KANBOARD_TOKEN=admin \
python setup-board.py
```

`setup-board.py` configures:
- all 11 columns
- swimlanes (`Parent Stories`, `Atomic Stories`)
- standard tags

## Card Metadata Contract

Preferred: MetaMagik task metadata.
Fallback: YAML in card description.

Required fields:
- `dirname`
- `context_mode` (`NEW` or `FEATURE`)
- `acceptance_criteria`

## Single-Card Lane Movement

Move the same card through:

`2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11`

At each stage, verify local package state in:
- `manifest.yaml`
- `approvals/*.json`
- `dashboard/dashboard.json`

## CLI-Only Alternative (No Kanboard)

You can run lifecycle locally:

```bash
python tools/workpackage.py init --id task-101 --title "Example" --dirname example --context-mode NEW --acceptance "criterion"
python tools/workpackage.py sync-stage --work-package-dir work-packages/task-101 --to-stage plan_approved
python tools/workpackage.py gate --work-package-dir work-packages/task-101 --action PM_AGENT
python tools/workpackage.py refresh-artifacts --work-package-dir work-packages/task-101
python tools/workpackage.py refresh-dashboard --work-package-dir work-packages/task-101
```

## Retry and Recovery

- Failed actions clear stale `*-started` and set `*-failed`.
- Successful actions clear stale `*-failed`.
- Transition persistence is hardened for partial-failure cleanup and idempotent same-stage retries.
- Use `tools/workpackage.py history` for replay visibility.

## Migration from Legacy Workspaces

Migrate existing story artifacts into work packages:

```bash
python tools/workpackage.py migrate-workspace \
  --base-dir work-packages \
  --id task-101 \
  --title "Migrated story" \
  --dirname migrated-story \
  --context-mode FEATURE \
  --workspace-dir ~/projects/migrated-story \
  --acceptance "migration keeps artifacts"
```

This creates `migration/migration-report.json` in the target work package.
