# AgentLeeOps Sprint Plan

Persistent sprint tracker for project progress. Updated by humans and coding agents.

---

## Sprint 1: MetaMagik Custom Fields
**Priority:** P1
**Status:** done

Custom field UI for Kanboard tasks via MetaMagik plugin, replacing YAML parsing in task descriptions.

**Deliverables:**
- [x] `lib/task_fields.py` - metadata API with YAML fallback
- [x] Updated `orchestrator.py` to use new field handling
- [x] Updated `webhook_server.py` to use new field handling
- [x] MetaMagik plugin installation docs in CLAUDE.md
- [x] Custom field configuration (dirname, context_mode, acceptance_criteria, complexity)
- [x] Fixed MetaMagik API method (`getTaskMetadata` not `getAllTaskMetadata`)
- [x] Fixed empty field default handling (context_mode defaults to NEW)
- [x] End-to-end validation: webhook -> agent -> DESIGN.md -> file attachment

---

## Sprint 2: Architecture Refactor (Context-Reset TDD)
**Priority:** P0
**Status:** done

Refactor pipeline to support "Breakdown First" workflow: Design -> Plan -> Tests -> Code.

**Deliverables:**
- [x] Update `product-definition.md` with new column order.
- [x] Update `setup-board.py` to reconfigure Kanboard columns.
- [x] Update `orchestrator.py` triggers to match new flow.
- [x] Execute `setup-board.py` to apply changes.

---

## Sprint 3: PM Agent & Fan-Out
**Priority:** P1
**Status:** done

Create PM_AGENT that generates `prd.json` planning document and SPAWNER_AGENT to fan-out tasks.

**Deliverables:**
- [x] `agents/pm.py` - agent implementation
- [x] `prompts/planning_prompt.txt` - prompt template
- [x] Column 4 trigger wiring in orchestrator
- [x] `prd.json` schema definition
- [x] `agents/spawner.py` - Spawner logic implementation.
- [x] **Fix Fan-Out API Error:** Implemented "Duplicate & Update" strategy to bypass MetaMagik mandatory field constraints.

---

## Sprint 4: Test Agent (Column 6)
**Priority:** P1
**Status:** done

Create TEST_AGENT that generates failing test files when atomic story cards reach Column 6 (Tests Draft).

**Deliverables:**
- [x] `agents/test_agent.py` - agent implementation
- [x] `prompts/test_prompt.txt` - prompt template
- [x] Column 6 trigger wiring in orchestrator
- [x] Tests must FAIL initially (by design).

---

## Sprint 5: Ralph Coder (Column 8)
**Priority:** P1
**Status:** done

Create RALPH_CODER agent that writes code to make tests PASS when cards reach Column 8.

**Deliverables:**
- [x] `agents/ralph.py` - agent implementation
- [x] Column 8 trigger wiring in orchestrator
- [x] Test execution and validation
- [x] **Clean Context Loop:** Implemented iterative git commit/retry loop.

---

## Sprint 6: FEATURE Mode
**Priority:** P2
**Status:** open

Support branch creation for existing repositories (context_mode: FEATURE).

**Deliverables:**
- [ ] Branch creation: `feat/<task_id>-<dirname>`
- [ ] Existing repo detection and validation
- [ ] Integration testing with real repos

---

## Sprint 7: End-to-End Testing (Verification)
**Priority:** P2
**Status:** in_progress

Full workflow test from Inbox to Done with all agents.

**Deliverables:**
- [x] **Fan-Out Fix:** Confirmed child cards are spawned correctly via Duplication Hack.
- [x] Test card creation in Inbox
- [x] Automated progression through all columns
- [x] Artifact verification at each stage (Design, PRD, Spawning, Tests, Code)

---

## For Consideration: GenAI Ops Hardening
**Priority:** TBD
**Status:** proposed

Feedback from GenAI Ops review.

**Security & Safety:**
- [ ] **Docker Sandbox for Ralph:** Run `RALPH_CODER` inside a Docker container to prevent host OS damage.
- [ ] **Validation:** Create `Dockerfile.agent-runner`.

**Observability:**
- [ ] **Trace Store:** Implement local SQLite logging for prompt/completion pairs.
- [ ] **Error Handling:** Add robust `retry_with_backoff` for API calls in orchestrator.

**Workflow & Robustness:**
- [ ] **Context Map:** Generate a repo tree/map to feed into context.
- [ ] **Agent Evals:** Create `tests/golden_scenarios/` to test agent performance.
- [ ] **Webhook Security:** Validate webhook source or use shared secret.
- [ ] **New Mode Safety:** Handle case where directory already exists in NEW mode.
