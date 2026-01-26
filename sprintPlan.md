# AgentLeeOps Sprint Plan

Persistent sprint tracker for project progress. Updated by humans and coding agents.

---

## Phase 1: Core Functionality (Complete)

- [x] **Sprint 1:** MetaMagik Custom Fields & Basic Board Setup
- [x] **Sprint 2:** Context-Reset TDD Architecture Refactor
- [x] **Sprint 3:** PM Agent & Fan-Out Spawner (with Duplication Hack)
- [x] **Sprint 4:** Test Agent (TDD Generation)
- [x] **Sprint 5:** Ralph Coder (Clean Context Loop)
- [x] **Sprint 6:** End-to-End Verification (Calculator Project)

---

## Phase 2: Governance & Safety (Current)

The system works, but lacks safety rails. Phase 2 focuses on "The Ratchet" (preventing regression) and "Integrity" (preventing cheating).

### Sprint 8: The Ratchet Guard (Governance)
**Priority:** P0
**Status:** open

Implement a file-based locking mechanism to enforce approval gates physically on disk.

**Deliverables:**
- [ ] **Ratchet Manifest:** Create `lib/ratchet.py` to manage `.agentleeops/ratchet.json` (stores file paths, hashes, and lock status).
- [ ] **Orchestrator Integration:** When a card enters an "Approved" column (3, 5, 7), lock the relevant artifacts in the manifest.
- [ ] **Write Guard:** Update `lib/workspace.py` to check the ratchet before writing. Raise `PermissionError` if overwriting a locked file.
- [ ] **Refinement Workflow:** Allow unlocking via specific "Request Revision" moves on the board.

### Sprint 9: Spawner Safety (Flood Control)
**Priority:** P0
**Status:** open

Harden the Spawner Agent against duplicate runs and infinite loops.

**Deliverables:**
- [ ] **Idempotency:** Query Kanboard for existing child tasks with the same `atomic_id` linked to the parent before spawning.
- [ ] **Transaction Safety:** If `updateTask` or `linkTask` fails after duplication, attempt to delete the orphan task.
- [ ] **Flood Control:** Implement `MAX_CHILDREN_PER_EPIC = 20`. Hard fail if `prd.json` requests more.

### Sprint 10: Ralph's Straitjacket (Test Integrity)
**Priority:** P1
**Status:** open

Physically prevent the Coding Agent from modifying tests to get a "Green Bar".

**Deliverables:**
- [ ] **Git Staging Rules:** Modify `agents/ralph.py` to forbid `git add .`. It must specificially add `src/` or intended files.
- [ ] **Pre-Commit Check:** Implement a check: `git diff --cached --name-only`. If `tests/` matches, abort the commit and fail the agent.
- [ ] **Hash Verification:** Ralph verifies the hash of the test file matches the `ratchet.json` record before starting.

### Sprint 11: Observability & Error Handling
**Priority:** P2
**Status:** open

Improve visibility into agent actions and failure states.

**Deliverables:**
- [ ] **Structured Logging:** Replace `print()` with a logger that emits JSON (Timestamp, Level, Agent, TaskID, Message).
- [ ] **Tag Hygiene:** Ensure `*-started` tags are cleared or replaced with `*-failed` tags upon exception in `orchestrator.py`.
- [ ] **Trace Store (Optional):** Simple SQLite log of prompts/completions for cost tracking.

---

## Backlog (Future)

- [ ] **FEATURE Mode:** Finalize support for existing repositories (branch management).
- [ ] **Docker Sandboxing:** Run Ralph in a container.
- [ ] **Webhook Security:** Validate webhook signatures.