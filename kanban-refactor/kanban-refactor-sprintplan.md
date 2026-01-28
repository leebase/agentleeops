# Kanban Refactor Sprint Plan

**Goal:** Refactor AgentLeeOps to use a provider-agnostic `WorkItemAbstraction`, enabling support for Jira/ADO while keeping Kanboard as the reference implementation.

**Strategy:** In-place refactor on a git branch. Planning artifacts live in `kanban-refactor/`.
**Philosophy:** Atomic, testable sprints. Each sprint must leave the system in a working or verifiable state.

---

## Epic 1: Core Abstraction & Kanboard Provider
**Goal:** Establish the `WorkItem` data structures and a working Kanboard implementation of the provider protocol.

- [x] **Sprint 1.1: Interfaces & Data Structures**
  - **Goal:** Define the exact Python protocols and Data Classes.
  - **Deliverables:**
    - `lib/workitem/types.py`: `WorkItem`, `WorkItemIdentity` (provider, external_id, url), `WorkItemQuery`, `WorkItemState` (Enum).
    - `lib/workitem/protocol.py`: `WorkItemProvider` (Protocol).
    - `tests/test_workitem_types.py`: Unit tests ensuring data integrity.
  - **Verification:** `pytest tests/test_workitem_types.py` passes.

- [x] **Sprint 1.2: Kanboard Provider (Read-Only)**
  - **Goal:** Implement fetching data from Kanboard via the new protocol.
  - **Deliverables:**
    - `lib/workitem/providers/kanboard.py`: `KanboardWorkItemProvider` class (init, get_work_item).
    - `lib/workitem/config.py`: Configuration loading for providers.
  - **Verification:** Integration test that connects to local Kanboard and fetches a known card as a `WorkItem`.
  - **Dependencies:** Running Kanboard instance.

- [x] **Sprint 1.3: Kanboard Provider (Write Operations)**
  - **Goal:** Implement state changes and updates.
  - **Deliverables:**
    - `KanboardWorkItemProvider` methods: `update_state`, `post_comment`, `set_metadata`, `add_tag`.
  - **Verification:** Integration test that moves a card, comments on it, and updates metadata; verifies changes via read back.

- [x] **Sprint 1.4: Client Facade & Capability Detection**
  - **Goal:** Create the user-facing client used by agents.
  - **Deliverables:**
    - `lib/workitem/client.py`: `WorkItemClient` factory.
    - `lib/workitem/capabilities.py`: Capability detection logic.
  - **Verification:** Unit test mocking a provider to verify `WorkItemClient` delegates correctly and handles capabilities.

---

## Epic 2: State Machine Logic
**Goal:** Decouple "Columns" from "States" using a config-driven state machine.

- [ ] **Sprint 2.1: State Machine Engine**
  - **Goal:** A pure logic engine that determines "Next Agent" based on "Current State".
  - **Deliverables:**
    - `config/workflow.yaml`: Define logical states (Inbox, Design Draft, etc.).
    - `lib/workflow/state_machine.py`: Class to load config and compute transitions.
  - **Verification:** Unit tests loading the yaml and asserting correct `get_next_agent` output for various inputs.

- [ ] **Sprint 2.2: Webhook & Event Normalization**
  - **Goal:** Translate provider-specific webhooks into generic events (and document polling fallback).
  - **Deliverables:**
    - `lib/workitem/providers/kanboard.py`: Implement `parse_webhook_payload`.
    - Update `webhook_server.py` to use `WorkItemClient.parse_webhook`.
  - **Verification:** Send raw Kanboard JSON webhook to server; verify it decodes into `(event, id, state)`.

- [ ] **Sprint 2.3: Orchestrator Wiring**
  - **Goal:** Replace the old hardcoded orchestrator with the State Machine.
  - **Deliverables:**
    - Refactor `orchestrator.py` to use `WorkItemClient` and `StateMachine`.
    - Remove legacy direct Kanboard calls from the main loop.
  - **Verification:** E2E test: Manually move card in Kanboard; Orchestrator detects change via State Machine logic (logs "Dispatching Agent X").

---

## Epic 3: Agent Migration
**Goal:** Refactor all agents to use `WorkItemClient`. Agents become board-agnostic.

- [ ] **Sprint 3.1: Upstream Agents (Architect & PM)**
  - **Goal:** Convert the "Design" and "Planning" agents.
  - **Deliverables:**
    - `agents/architect.py`: Switch to `WorkItemClient`.
    - `agents/pm.py`: Switch to `WorkItemClient`.
  - **Verification:** Run `agents.architect` against a test card; verify `DESIGN.md` generation and comment posting works.

- [ ] **Sprint 3.2: Governance Agents (Test & Governance)**
  - **Goal:** Convert the "Test" and "Governance" agents (Critical Phase).
  - **Deliverables:**
    - `agents/test_agent.py`: Switch to `WorkItemClient`.
    - `agents/governance.py`: Switch to `WorkItemClient`. ensure Ratchet still works.
  - **Verification:** Run Test agent; verify `tests/` generated. Run Governance; verify files locked.

- [ ] **Sprint 3.3: Downstream Agents (Ralph & Spawner)**
  - **Goal:** Convert the "Implementation" and "Fan-out" agents.
  - **Deliverables:**
    - `agents/ralph.py`: Switch to `WorkItemClient`.
    - `agents/spawner.py`: Switch to `create_work_item` API.
  - **Verification:** Full loop test: Ralph writes code, Spawner works (mocked/dry-run).

---

## Epic 4: Verification & Cleanup
**Goal:** Ensure the system is robust and old code is removed.

- [ ] **Sprint 4.1: End-to-End Regression Test**
  - **Goal:** Run the "Calculator" project flow from Inbox to Done.
  - **Deliverables:**
    - Successful execution trace of the full lifecycle.
  - **Verification:** System works exactly as before but on new architecture.

- [ ] **Sprint 4.2: Enterprise Provider Prototype (Optional)**
  - **Goal:** Prove the abstraction by creating a "Mock" or "Jira" provider.
  - **Deliverables:**
    - `lib/workitem/providers/mock.py` or `jira.py`.
  - **Verification:** Switch config to Mock/Jira and run Architect agent successfully.
