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

## Sprint 2: Scaffold Agent
**Priority:** P1
**Status:** open

Create SCAFFOLD_AGENT that generates failing test files when cards reach Column 4.

**Deliverables:**
- [ ] `agents/scaffold.py` - agent implementation
- [ ] `prompts/scaffold_prompt.txt` - prompt template
- [ ] Column 4 trigger wiring in orchestrator
- [ ] Tests must FAIL initially (by design - Double-Blind Rule)
- [ ] File attachment to Kanboard task

---

## Sprint 3: PM Agent
**Priority:** P1
**Status:** open

Create PM_AGENT that generates `prd.json` planning document when cards reach Column 6.

**Deliverables:**
- [ ] `agents/pm.py` - agent implementation
- [ ] `prompts/planning_prompt.txt` - prompt template
- [ ] Column 6 trigger wiring in orchestrator
- [ ] `prd.json` schema definition
- [ ] File attachment to Kanboard task

---

## Sprint 4: Ralph Coder
**Priority:** P1
**Status:** open

Create RALPH_CODER agent that writes code to make tests PASS when cards reach Column 8.

**Deliverables:**
- [ ] `agents/ralph.py` - agent implementation
- [ ] Column 8 trigger wiring in orchestrator
- [ ] Test execution and validation
- [ ] Code must make existing tests PASS (no test modification - Test Integrity rule)

---

## Sprint 5: FEATURE Mode
**Priority:** P2
**Status:** open

Support branch creation for existing repositories (context_mode: FEATURE).

**Deliverables:**
- [ ] Branch creation: `feat/<task_id>-<dirname>`
- [ ] Existing repo detection and validation
- [ ] Integration testing with real repos

---

## Sprint 6: End-to-End Testing
**Priority:** P2
**Status:** open

Full workflow test from Inbox to Done with all agents.

**Deliverables:**
- [ ] Test card creation in Inbox
- [ ] Automated progression through all columns
- [ ] Artifact verification at each stage
- [ ] Documentation of test procedure
