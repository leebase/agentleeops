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

## Phase 2: Governance & Safety (Complete)

The system works, but lacks safety rails. Phase 2 focuses on "The Ratchet" (preventing regression) and "Integrity" (preventing cheating).

- [x] **Sprint 8: The Ratchet Guard** (Governance)
    - [x] Created `lib/ratchet.py` for file locking.
    - [x] Updated `lib/workspace.py` to enforce write guards.
    - [x] Created `agents/governance.py` to lock artifacts on approval.

- [x] **Sprint 9: Spawner Safety** (Flood Control)
    - [x] Implemented Idempotency (skip existing children).
    - [x] Implemented Flood Control (limit 20).
    - [x] Implemented Transaction Rollback.

- [x] **Sprint 10: Ralph's Straitjacket** (Test Integrity)
    - [x] Banned `git add .` in Ralph.
    - [x] Added Pre-Commit Check for `tests/` changes.
    - [x] Added Hash Verification against Ratchet.

- [x] **Sprint 11: Observability & Error Handling**
    - [x] Replaced `print()` with Structured JSON Logging.
    - [x] Added Trace Store for LLM calls (`.agentleeops/trace.db`).
    - [x] Verified full pipeline with logging enabled.

---

## Phase 3: Scaling & Polish (Next)

- [ ] **Sprint 12: Feature Mode & Branching:** Support existing repositories.
- [ ] **Sprint 13: Webhook Security:** Validate signatures.
- [ ] **Sprint 14: Docker Sandboxing:** Run Ralph in a container.