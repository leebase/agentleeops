# Work Package CLI

`tools/workpackage.py` provides a Kanban-independent lifecycle workflow for single-card mode.

## Core Commands

```bash
# Initialize a package
python tools/workpackage.py init \
  --id task-101 \
  --title "Example story" \
  --dirname example-story \
  --context-mode NEW \
  --acceptance "first criterion"

# Validate manifest
python tools/workpackage.py validate --work-package-dir work-packages/task-101

# Transition one step (or rollback)
python tools/workpackage.py transition \
  --work-package-dir work-packages/task-101 \
  --to-stage design_draft

# Sync to a target stage (multi-step forward supported)
python tools/workpackage.py sync-stage \
  --work-package-dir work-packages/task-101 \
  --to-stage plan_approved

# Refresh artifact freshness and dashboard
python tools/workpackage.py refresh-artifacts --work-package-dir work-packages/task-101
python tools/workpackage.py refresh-dashboard --work-package-dir work-packages/task-101

# Gate an action using local artifact state
python tools/workpackage.py gate \
  --work-package-dir work-packages/task-101 \
  --action PM_AGENT
```

## External Work Item Mapping

```bash
# Add mapping
python tools/workpackage.py map-add \
  --work-package-dir work-packages/task-101 \
  --provider jira \
  --external-id PROJ-123 \
  --url https://jira.example.com/browse/PROJ-123

# Export mappings
python tools/workpackage.py map-export --work-package-dir work-packages/task-101 --out mapping.json

# Import mappings
python tools/workpackage.py map-import --work-package-dir work-packages/task-101 --from-file mapping.json
```

These mapping commands are designed for future Jira/ADO adapter interoperability.

## Migration Command

```bash
python tools/workpackage.py migrate-workspace \
  --base-dir work-packages \
  --id task-101 \
  --title "Legacy story migration" \
  --dirname legacy-story \
  --context-mode FEATURE \
  --workspace-dir ~/projects/legacy-story \
  --acceptance "migration preserves artifacts"
```

This creates or reconciles `work-packages/task-101`, copies known artifacts, refreshes
artifact/dashboard state, and writes `migration/migration-report.json`.
