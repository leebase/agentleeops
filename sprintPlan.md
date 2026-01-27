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

- [x] **Sprint 8: The Ratchet Guard** (Governance)
- [x] **Sprint 9: Spawner Safety** (Flood Control/Idempotency)
- [x] **Sprint 10: Ralph's Straitjacket** (Test Integrity)
- [x] **Sprint 11: Observability & Error Handling**

---

## Phase 3: Scaling & Polish (Next)

The system is operational, but the "Discount Engine" demo revealed edge cases in LLM reliability and git history management.

### Sprint 12: Robustness & LLM Guards
**Priority:** P1
**Status:** open

Prevent "LLM Refusal Injection" and ensure artifacts are properly committed.

**Deliverables:**
- [ ] **Ralph's Syntax Guard:** Before writing code to disk, run `ast.parse()`. If the LLM output isn't valid Python (e.g. "I cannot do that"), reject it and retry.
- [ ] **Artifact Committer:** The `GOVERNANCE_AGENT` (or Test Agent) must `git add/commit` generated tests/designs to `master` so they exist in history before Ralph branches off.
- [ ] **Context Fix:** Ensure Ralph's prompt explicitly includes the absolute path to files to prevent LLM confusion.

### Sprint 13: Feature Mode & Branching
**Priority:** P2
**Status:** open

Support existing repositories and complex branching strategies.

**Deliverables:**
- [ ] **Branch Detection:** Handle `feat/` branch creation robustly (check for existing).
- [ ] **Merge Requests:** Automate PR creation (if using GitHub/GitLab) or a local "Merge Ready" signal.

### Sprint 14: Docker Sandboxing
**Priority:** P3
**Status:** open

Run Ralph in a container to prevent host filesystem damage.

**Deliverables:**
- [ ] **Agent Runner Image:** Dockerfile with python, git, pytest.
- [ ] **Volume Mounting:** Safe mounting of `~/projects/<dirname>`.

### Sprint 15: Webhook Security
**Priority:** P3
**Status:** open

**Deliverables:**
- [ ] Validate webhook signatures to prevent unauthorized triggers.
