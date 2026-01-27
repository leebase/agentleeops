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

## Phase 3: Scaling & Polish (In Progress)

### Sprint 12: Robustness & LLM Guards
**Priority:** P1
**Status:** complete

Prevent "LLM Refusal Injection" and ensure system reliability.

**Deliverables:**
- [x] **Syntax Guard (`lib/syntax_guard.py`):** Validates LLM output with `ast.parse()` (Python) and `json.loads()` (JSON) before writing to disk. Rejects prose/"I cannot do that" responses.
- [x] **Agent Integration:** Ralph, Test Agent, and PM Agent all use syntax guard.
- [x] **Webhook Parity:** `webhook_server.py` now triggers all 6 agents (was only ARCHITECT). Full automation via webhook now possible.
- [x] **Code Consolidation:** Tag helpers (`get_task_tags`, `add_task_tag`, `has_tag`) moved to `lib/task_fields.py`.
- [x] **Integration Test Suite:** 59 tests covering ratchet, syntax guard, task fields, and workspace modules.

**Remaining (deferred to Sprint 13):**
- [ ] **Artifact Committer:** Auto-commit designs/tests to master before Ralph branches.

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
