# User Guide: Creating and Running a Story End-to-End

This guide explains how to create a story in AgentLeeOps, why each lane exists, where human approvals are required, and how parent/child execution works in the Ralph loop.

## Why This Workflow Exists

AgentLeeOps is designed for safe, auditable delivery with AI:

- Design, tests, and code are separated.
- Human approvals create governance checkpoints.
- Approved artifacts are locked (ratchet) so later stages cannot silently rewrite requirements.
- Progress is resumable and deterministic with tag/state tracking.

## The 10 Lanes and Their Purpose

1. `1. Inbox`
- Purpose: intake and triage.
- Human action: create or refine story intent.

2. `2. Design Draft`
- Purpose: ARCHITECT_AGENT generates `DESIGN.md`.
- Human action: review design quality and scope.

3. `3. Design Approved`
- Purpose: GOVERNANCE_AGENT locks `DESIGN.md`.
- Human action: approval gate; only approve when design is good enough to freeze.

4. `4. Planning Draft`
- Purpose: PM_AGENT generates `prd.json` with atomic stories.
- Human action: check decomposition quality.

5. `5. Plan Approved`
- Purpose: GOVERNANCE_AGENT locks `prd.json`; SPAWNER_AGENT creates child stories.
- Human action: confirm plan before fan-out.

6. `6. Tests Draft`
- Purpose: TEST_AGENT creates test plans/spec artifacts for each child.
- Human action: verify test intent before code implementation.

7. `7. Tests Approved`
- Purpose: GOVERNANCE_AGENT locks tests.
- Human action: approval gate for test contract.

8. `8. Ralph Loop`
- Purpose: RALPH_CODER implements code to satisfy locked tests.
- Human action: monitor failures/escalations only; no test rewriting.

9. `9. Final Review`
- Purpose: human validation of delivered behavior and diffs.
- Human action: accept/reject implementation quality.

10. `10. Done`
- Purpose: workflow complete.

## Creating a Story Card

Create a Kanboard card with required fields:

- `dirname`: workspace name (lowercase letters, digits, dashes only)
- `context_mode`: `NEW` or `FEATURE`
- `acceptance_criteria`: explicit checklist

You can provide these via MetaMagik custom fields (preferred) or YAML in description (legacy).

Example YAML fallback:

```yaml
dirname: cf-tunnel-create
context_mode: NEW
acceptance_criteria: |
  - CLI can apply a tunnel spec
  - Operation is idempotent
  - Tests cover parser and state behavior
```

## How to Move a Story Through the Lanes

Use this sequence for a parent story:

1. Move parent card to `2. Design Draft`.
2. Wait for design generation, review artifact, then move to `3. Design Approved`.
3. Move to `4. Planning Draft`, review plan, then move to `5. Plan Approved`.
4. After spawn, work child stories one at a time:
- Child: `5 -> 6 -> 7 -> 8 -> 9 -> 10`
5. After all children are complete, move parent to `8. Ralph Loop` (if using parent batch path), then `9`, then `10`.

## Human Interaction and Governance: What Must Stay Human

Human approval is intentionally required at:

- `3. Design Approved`
- `5. Plan Approved`
- `7. Tests Approved`
- `9. Final Review`

Why:

- These gates prevent hidden requirement drift.
- They preserve test integrity and traceability.
- They enforce the ratchet effect (approved artifacts become immutable for agents).

## Important: Parent Story in Ralph Loop (Top Story Behavior)

### What happens when you move the parent (top story) to `8. Ralph Loop`?

Confirmed behavior in current product:

- Moving the parent to `8. Ralph Loop` triggers Ralph for that parent task.
- Ralph detects linked child stories and can run in batch mode against their tests.
- This can implement multiple linked atomic stories in one loop if required test files exist.

### What does NOT happen automatically?

- Child cards are **not automatically moved between Kanboard lanes** when you move the parent.
- Lane movement remains explicit and visible in Kanboard for governance/auditability.

So, moving the top story to Ralph loop can drive batch implementation logic, but it does not physically drag linked cards across columns.

## Retry and Stale Tag Handling

AgentLeeOps uses `started/completed/failed` tags per phase.

- On failure: system removes `*-started` and adds `*-failed`.
- On success: system adds `*-completed` and clears stale `*-failed`.
- If a task has both `*-started` and `*-failed` (legacy stale state), system auto-clears `*-started` to unblock retry.

This enables safe, autonomous retries without manual tag cleanup.

