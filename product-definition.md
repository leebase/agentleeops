# AgentLeeOps — Product Definition v1.5 (Code Review Lane Edition)

## 1. Executive Summary

**AgentLeeOps** is a single-user, approval-gated delivery system that turns a Story into tested, working code. It combines a **Kanban Control Plane** (Kanboard) with an **Agentic Loop** (OpenCode) to ensure AI speed without AI hallucinations.

## 2. The Core Philosophy

*   **The Ratchet Effect (Governance):** Approval is not just a column; it is a cryptographic lock. Once artifacts (`DESIGN.md`, `tests/`) are approved by Lee, they become **immutable** to agents. Only Lee can unlock them.
*   **The Double-Blind Rule:** The Agent writing the code (**Ralph**) is never the same Agent that wrote the tests.
*   **Test Integrity:** Ralph is technically prevented from modifying tests. A "Green Bar" is only valid if the test file hash matches the approved version.
*   **Artifacts over Chat:** We do not rely on chat logs. We rely on durable files.

## 3. The 11-Step Workflow (State Machine)

| # | Column | Owner | Artifact | Governance Action |
|---|---|---|---|---|
| **1** | Inbox | Lee | Story Card | - |
| **2** | Design Draft | Architect | `DESIGN.md` | Agent can overwrite |
| **3** | **Design Approved** | Lee | **(Gate)** | **LOCK** `DESIGN.md` |
| **4** | Planning Draft | PM | `prd.json` | Agent can overwrite |
| **5** | **Plan Approved** | Lee | **(Gate)** | **LOCK** `prd.json` + **SPAWN** Children |
| **6** | Tests Draft | Test Agent | `tests/*.py` | Agent can overwrite |
| **7** | **Tests Approved** | Lee | **(Gate)** | **LOCK** `tests/*.py` |
| **8** | Ralph Loop | Ralph | `src/` | **VERIFY** Test Hash + **BAN** Test Edits |
| **9** | Code Review | Review Agent | `reviews/CODE_REVIEW_REPORT.json`, `reviews/CODE_REVIEW_NEXT_STEPS.md` | **REVIEW GATE** (fail blocks progression) |
| **10** | Final Review | Lee | PR/Diff + review artifacts | Manual Merge |
| **11** | Done | System | Archived | - |

## 4. Governance & Safety Mechanisms

### 4.1 The Ratchet System
A local manifest `.agentleeops/ratchet.json` tracks the approval state of critical files.
- **Locked:** File cannot be modified by any agent.
- **Unlocked:** File is in a "Draft" column.
- **Enforcement:** `workspace.write_file()` checks this manifest before IO operations.

### 4.2 Ralph's Straitjacket
To prevent "Cheating" (making tests pass by deleting assertions):
1.  **Staging Restriction:** Ralph cannot run `git add .`. He must add specific source paths.
2.  **Diff Check:** Before commit, the system runs `git diff --cached --name-only`. If any file in `tests/` is present, the operation aborts.

### 4.3 Fan-Out Flood Control
The Spawner Agent enforces a hard limit (default: 20) on the number of child cards generated from a single `prd.json` to prevent runaway API calls or cost explosions.

### 4.4 LLM Syntax Guard
To prevent "LLM Refusal Injection" (model responds with prose instead of code):
1.  **Python Validation:** All code is validated with `ast.parse()` before writing to disk.
2.  **JSON Validation:** All JSON is validated with `json.loads()` before writing.
3.  **Rejection & Retry:** Invalid output is rejected and the agent retries (up to MAX_RETRIES).
4.  **Implementation:** `lib/syntax_guard.py` provides `safe_extract_python()` and `safe_extract_json()`.

### 4.5 Agent State Tags and Retry Unblocking
The orchestrator and webhook server track execution state with task tags and metadata:
- **Started tags:** e.g., `design-started`, `planning-started`, `spawning-started`, `tests-started`, `coding-started`
- **Completed tags:** e.g., `design-generated`, `planning-generated`, `spawned`, `tests-generated`, `coding-complete`
- **Failed tags:** e.g., `design-failed`, `planning-failed`, `spawning-failed`, `tests-failed`, `coding-failed`

Retry behavior is deterministic:
1. On failure, the system removes the `*-started` tag and adds `*-failed`.
2. On success, the system adds `*-complete` and clears stale `*-failed`.
3. If legacy/stale state has both `*-started` and `*-failed`, the system auto-clears `*-started` so retries can proceed without manual cleanup.

## 5. The "Context Mode"

| Mode | Trigger | Agent Behavior |
| --- | --- | --- |
| **NEW** | `context_mode: NEW` | `mkdir <dirname>`, `git init`, scaffolding. |
| **FEATURE** | `context_mode: FEATURE` | Uses existing repo, creates `feat/<story-id>` branch. |

## 6. Technical Stack

- **Control Plane:** Kanboard (Docker on Port 88).
- **Orchestrator:** Python Script (`orchestrator.py`) polling Port 88.
- **Agent Architecture:** Role-based Agents using `lib.llm` abstraction.
- **LLM Providers:** Pluggable (OpenRouter, OpenCode CLI, Gemini CLI) via `config/llm.yaml`.
- **Verification:** pytest (Backend).
