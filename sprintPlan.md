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
**Status:** done

Implement a file-based locking mechanism to enforce approval gates physically on disk.

**Deliverables:**
- [x] **Ratchet Manifest:** Create `lib/ratchet.py` to manage `.agentleeops/ratchet.json`.
- [x] **Orchestrator Integration:** Lock relevant artifacts in the manifest on board movement.
- [x] **Write Guard:** Update `lib/workspace.py` to check the ratchet before writing.
- [x] **Refinement Workflow:** Allow unlocking via specific "Request Revision" moves.

### Sprint 9: Spawner Safety (Flood Control)
**Priority:** P0
**Status:** done

Harden the Spawner Agent against duplicate runs and infinite loops.

**Deliverables:**
- [x] **Idempotency:** Query Kanboard for existing child tasks with the same `atomic_id` before spawning.
- [x] **Transaction Safety:** Delete orphan tasks if update/link fails after duplication.
- [x] **Flood Control:** Implement `MAX_CHILDREN_PER_EPIC = 20`. Hard fail if `prd.json` requests more.

### Sprint 10: Ralph's Straitjacket (Test Integrity)
**Priority:** P1
**Status:** open

Physically prevent the Coding Agent from modifying tests to get a "Green Bar".

**Deliverables:**
- [ ] **Git Staging Rules:** Modify `agents/ralph.py` to forbid `git add .`.
- [ ] **Pre-Commit Check:** Implement a check: `git diff --cached --name-only`.
- [ ] **Hash Verification:** Ralph verifies the hash of the test file matches the `ratchet.json` record.

### Sprint 11: Observability & Error Handling
**Priority:** P2
**Status:** open

Improve visibility into agent actions and failure states.

**Deliverables:**
- [ ] **Structured Logging:** Replace `print()` with a JSON logger.
- [ ] **Tag Hygiene:** Ensure `*-started` tags are cleared or replaced with `*-failed` tags.
- [ ] **Trace Store (Optional):** Simple SQLite log of prompts/completions.

---

## Backlog (Future)

- [ ] **FEATURE Mode:** Finalize support for existing repositories.
- [ ] **Docker Sandboxing:** Run Ralph in a container.
- [ ] **Webhook Security:** Validate webhook signatures.