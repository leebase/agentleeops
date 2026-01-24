# AgentLeeOps — Product Definition v1.0 (FINAL)

## 1. Executive Summary

**AgentLeeOps** is a single-user, approval-gated delivery system that turns a Story into tested, working code. It combines a **Kanban Control Plane** (Kanboard) with an **Agentic Loop** (OpenCode) to ensure AI speed without AI hallucinations.

## 2. The Core Philosophy

* **The Ratchet Effect:** Agents can draft work, but only **Lee** can approve it. Once approved, the artifact is frozen. Agents cannot regress approved decisions.
* **The Double-Blind Rule:** The Agent writing the code (**Ralph**) is never the same Agent that wrote the tests.
* **Artifacts over Chat:** We do not rely on chat logs. We rely on durable files (`DESIGN.md`, `tests/`, `prd.json`).

### 2.1 Test Integrity Rule (Non-Negotiable)
Once tests are approved (Column 5), **agents must not modify anything under `tests/`** unless **Lee explicitly moves the card back to Column 4**.

This prevents the classic failure mode: “the agent made the tests pass by changing the tests.”

## 3. The "Context Mode" (Greenfield vs. Brownfield)

Every story must declare its Context Mode to determine how the agent bootstraps the workspace.

| Mode | Trigger | Agent Behavior |
| --- | --- | --- |
| **NEW** | `context_mode: NEW` | `mkdir <dirname>`, `git init`, scaffolding. |
| **FEATURE** | `context_mode: FEATURE` | Uses existing repo at `~/projects/<dirname>`, `git pull`, creates `feat/<story-id>` branch. |

## 4. The 10-Step Workflow (State Machine)

The Kanboard Columns must match this exact flow.

| # | Column Name | Owner | Artifact Produced | Exit Criteria |
| --- | --- | --- | --- | --- |
| **1** | **Inbox** | Lee | One-line Story card | Lee moves to Draft. |
| **2** | **Design Draft** | **Agent** | `DESIGN.md` | Agent updates card. |
| **3** | **Design Approved** | Lee | **(Approval Gate)** | Lee validates architecture. |
| **4** | **Repo & Tests Draft** | **Agent** | Repo bootstrap + `tests/*.py` | Repo exists (NEW or FEATURE) and tests exist and **FAIL** (Red). |
| **5** | **Tests Approved** | Lee | **(Approval Gate)** | Lee confirms tests measure success. |
| **6** | **Planning Draft** | **Agent** | `prd.json` (Atomic Stories) | Story breakdown exists. |
| **7** | **Plan Approved** | Lee | **(Approval Gate)** | Lee agrees to the plan. |
| **8** | **Ralph Loop** | **Ralph** | Source Code (`src/`) | **GREEN BAR** (Tests Pass). |
| **9** | **Final Review** | Lee | Pull Request / Diff | Lee merges code. |
| **10** | **Done** | System | Archived Card | N/A |

### 4.1 Definitions
- **Ralph:** The implementation agent responsible for executing the approved `prd.json` plan, writing code, running tests, committing changes, and iterating until the test suite passes.

## 5. The Card Template (Input Contract)

Every card in the "Inbox" must eventually conform to this YAML-style description before moving to Column 2.

```yaml
dirname: my-cool-project
context_mode: NEW  # or FEATURE
acceptance_criteria: |
  - Must parse CSV files
  - Must return JSON output
  - Must handle empty file error
```

### 5.1 Naming Rules (Safety Contract)

To avoid filesystem/path issues, dirname must be:
- lowercase
- digits and dashes only
- no spaces
- no leading dot
- no slashes
- no `.`.

## 6. Technical Stack

- **Control Plane:** Kanboard (Docker on Port 88).
- **Orchestrator:** Python Script (`orchestrator.py`) polling Port 88.
- **Agent Engine:** OpenCode (configured with `.opencode/rules.md`).
- **Verification:** pytest (Backend) / playwright (Frontend).

### 6.1 Git Contract (Standardization)

- **Workspace root:** `~/projects/<dirname>`
- **Repo ownership:** `leebase/<dirname>`
- **Branch format:** `feat/<task_id>-<dirname>`
- **Commit discipline:** incremental commits during loops; squash or merge policy is decided by Lee at Final Review.

## 7. Success Metrics

1. Zero “Green Bar Hallucinations”: Ralph never edits a test file to make it pass.
2. Clean Git History: Every story results in a squashed, readable commit (or an intentionally reviewed commit series).
3. Resumability: If the power goes out, the artifacts (`DESIGN.md`, `prd.json`) allow the agent to resume exactly where it left off.

---

## Next Step: Implementation

Now that the Product Definition is frozen, we are ready to execute the Orchestrator Logic.

1. **Config:** Ensure your Kanboard columns (Port 88) match Section 4 exactly.
2. **Code:** Run the `orchestrator.py` script to verify it can read tasks and locate cards in Column 2.
3. **Parse:** Implement parsing of the Card Template fields (`dirname`, `context_mode`, `acceptance_criteria`) from the task description.
4. **Trigger:** Implement the first real automation: when a task enters Design Draft, generate `DESIGN.md` via OpenCode Plan Mode and attach/link it back to the card.

We have moved from “Architecture” to “Engineering.” The system is defined.

---

## Appendix: Reference (Optional)

This video is relevant because it demonstrates the specific OpenCode “Plan vs. Build” workflow that powers the “Ralph Loop” in this architecture.

- [OpenCode AI: Free Cursor Alternative | Build Apps with AI](https://www.youtube.com/watch?v=EXAMPLE)
