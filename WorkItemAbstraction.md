# AgentLeeOps Work Item Provider Architecture

**Date:** 2026-01-28
**Status:** Partially Implemented (Sprints 5-7)
**Supersedes:** MultiKanban.md
**Based on:** Code review feedback (codereview/kanbanRedesignFeedback.md)

---

## Implementation Status Update (Sprints 1-7)

Implemented from this design:
- `lib/workitem/protocol.py` and `lib/workitem/client.py`
- `lib/workitem/providers/kanboard.py`
- `lib/workitem/adapter_contract.py` (external adapter contract scaffold)
- single-card lifecycle adapter in `lib/workpackage/adapter.py`
- local CLI-first orchestration in `lib/workpackage/local_orchestrator.py`

Still pending from full enterprise vision:
- concrete Jira/ADO provider implementations
- production-grade bidirectional sync beyond current mapping/import-export scaffold
- rollout completion for remaining Sprint 8 workspace-isolation hardening

---

## Table of Contents

1. [Purpose & Vision](#1-purpose--vision)
2. [Core Insight: Agents Need Work Items, Not Boards](#2-core-insight-agents-need-work-items-not-boards)
3. [Architecture Overview](#3-architecture-overview)
4. [Work Item Abstraction](#4-work-item-abstraction)
5. [State Machine Design](#5-state-machine-design)
6. [Work Item Provider Protocol](#6-work-item-provider-protocol)
7. [Reference Implementation: Kanboard](#7-reference-implementation-kanboard)
8. [Enterprise Implementations](#8-enterprise-implementations)
9. [Agent Integration Model](#9-agent-integration-model)
10. [Governance & Safety Preservation](#10-governance--safety-preservation)
11. [Migration Strategy](#11-migration-strategy)
12. [Capability Detection & Graceful Degradation](#12-capability-detection--graceful-degradation)
13. [Architecture Validation](#13-architecture-validation)

---

## 1. Purpose & Vision

### 1.1 What We're Building

**AgentLeeOps as a Workflow Accelerator Service**

AgentLeeOps transforms existing enterprise work tracking systems (Jira, Azure DevOps, ServiceNow, etc.) into **agent-capable workflow engines** while preserving the existing system as the authoritative source of truth.

**Not:** A replacement for Jira/ADO/Kanboard
**But:** A service that makes Jira/ADO/Kanboard **smarter and safer** through AI agents

### 1.2 Enterprise Framing

**❌ Wrong Pitch:**
> "AgentLeeOps has its own Kanban board system."

**✅ Right Pitch:**
> "AgentLeeOps doesn't replace Jira. It makes Jira agent-capable — safely."

This reframing is critical for enterprise adoption because:
- Work tracking systems are **systems of record** (integrated with HR, billing, compliance)
- Replacing them is a **political act**, not a technical one
- Enterprises want workflow acceleration, not workflow migration

### 1.3 Core Philosophy

**Agents are stateless workers. Work items are durable entities.**

Current AgentLeeOps thinks in terms of:
- Kanboard columns
- Board structure
- UI metaphors

New AgentLeeOps thinks in terms of:
- Work item references (IDs)
- State transitions
- API semantics

This shift enables:
1. **Provider independence** - Any work tracking system can be an authority
2. **Enterprise compatibility** - Plug into existing infrastructure
3. **Graceful degradation** - Optional features don't block core functionality
4. **Clear contracts** - Well-defined provider interface

### 1.4 Kanboard's New Role

**Kanboard is the reference implementation, not the product.**

Kanboard provides:
- A **known-good environment** for testing agents
- A **controllable substrate** for development
- A **validation target** for the abstraction
- A **bootstrapping path** for new users

But the product is:
> "Agent-capable work item management that plugs into enterprise systems."

---

## 2. Core Insight: Agents Need Work Items, Not Boards

### 2.1 What Agents Actually Need

Analyzing the current AgentLeeOps workflow reveals agents require:

| Agent Need | Current Kanboard Solution | Abstract Requirement |
|------------|---------------------------|----------------------|
| **Discover work** | Poll columns for tasks | Query work items by state |
| **Read context** | Fetch task description, metadata | Read work item fields |
| **Update state** | Move task to next column | Transition work item state |
| **Record decisions** | Post comments | Attach commentary |
| **Store artifacts** | Upload files | Attach/link artifacts |
| **Track relationships** | Link tasks | Reference related work items |
| **Ensure idempotency** | Check/set tags | Read/write markers (tags, custom fields) |

**Key realization:** None of these fundamentally require a "board."

They require:
1. **Work item references** (stable IDs)
2. **State mutation capability** (transitions)
3. **Metadata storage** (custom fields, tags, description)
4. **Commentary** (comments, notes, logs)

Everything else (columns, swimlanes, WIP limits, board UI) is **presentation layer** that agents don't interact with.

### 2.2 Lowest Common Denominator Across Systems

What exists in **every** enterprise work tracking system?

| Feature | Jira | Azure DevOps | Kanboard | GitHub Issues | Linear | ServiceNow |
|---------|------|--------------|----------|---------------|--------|------------|
| **Work item with ID** | ✅ Issue | ✅ Work Item | ✅ Task | ✅ Issue | ✅ Issue | ✅ Incident |
| **Lifecycle state** | ✅ Status | ✅ State | ✅ Column | ✅ Open/Closed | ✅ State | ✅ Status |
| **Metadata** | ✅ Custom fields | ✅ Fields | ✅ Metadata | ✅ Labels | ✅ Custom fields | ✅ Fields |
| **Commentary** | ✅ Comments | ✅ Comments | ✅ Comments | ✅ Comments | ✅ Comments | ✅ Work notes |
| **Attachments** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Relationships** | ✅ Links | ✅ Links | ✅ Links | ✅ References | ✅ Parent/child | ✅ Related |

**Common contract:**
- Work item reference (ID)
- State (string or enum)
- Metadata (key-value or typed fields)
- Commentary (text with optional markdown)

**Optional but common:**
- Attachments
- Relationships
- Custom workflows

### 2.3 What Columns Actually Are

In current AgentLeeOps:
```
Inbox → Design Draft → Design Approved → Planning Draft → ...
```

These aren't "columns." They're **named states in a state machine**.

The fact that Kanboard renders them as columns is UI. The fact that agents trigger on column moves is **really** agents triggering on state transitions.

**Abstraction:**
```
WorkItemState = "inbox" | "design_draft" | "design_approved" | ...
```

Agents care about:
- "When state changes from X to Y, do Z"
- "When state is X and condition C, transition to Y"

They don't care about:
- "Is this rendered as a column or a dropdown?"
- "What color is this column?"
- "Where is this column positioned?"

---

## 3. Architecture Overview

### 3.1 System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AgentLeeOps Service                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Orchestrator (State-Driven)              │  │
│  │  - Monitors work item state transitions               │  │
│  │  - Dispatches agents based on state machine           │  │
│  │  - Enforces governance rules                          │  │
│  └───────────────┬───────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────▼───────────────────────────────────────┐  │
│  │           Work Item Provider Client                   │  │
│  │  - Abstract interface to work tracking systems        │  │
│  │  - Capability detection                               │  │
│  │  - Provider-agnostic operations                       │  │
│  └───────────────┬───────────────────────────────────────┘  │
│                  │                                           │
└──────────────────┼───────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┬─────────────┐
        │                     │              │             │
        ▼                     ▼              ▼             ▼
┌──────────────┐    ┌──────────────┐  ┌──────────┐  ┌──────────┐
│   Kanboard   │    │     Jira     │  │Azure DO  │  │  Linear  │
│   Provider   │    │   Provider   │  │ Provider │  │ Provider │
└──────┬───────┘    └──────┬───────┘  └────┬─────┘  └────┬─────┘
       │                   │               │             │
       ▼                   ▼               ▼             ▼
┌──────────────┐    ┌──────────────┐  ┌──────────┐  ┌──────────┐
│  Kanboard    │    │  Jira API    │  │ ADO API  │  │Linear API│
│  JSON-RPC    │    │  REST v3     │  │   REST   │  │ GraphQL  │
└──────────────┘    └──────────────┘  └──────────┘  └──────────┘
```

### 3.2 Information Flow

**Agent Execution Flow:**

1. **State Change Detection**
   - Webhook triggers on work item state change
   - Or: Polling detects state change
   - Orchestrator receives: `(work_item_id, new_state, old_state)`

2. **State Machine Evaluation**
   - Orchestrator consults state machine: "What agent handles this transition?"
   - Example: `design_draft` state → ARCHITECT agent
   - Check idempotency: "Has this agent already processed this work item?"

3. **Work Item Fetch**
   - Call `provider.get_work_item(work_item_id)`
   - Receive WorkItem with: id, state, metadata, description, tags

4. **Agent Execution**
   - Agent reads context from WorkItem
   - Agent performs work (generate DESIGN.md, run tests, etc.)
   - Agent produces artifacts and decisions

5. **State Update**
   - Agent calls `provider.update_state(work_item_id, next_state)`
   - Agent calls `provider.post_comment(work_item_id, result_summary)`
   - Agent calls `provider.attach_artifact(work_item_id, artifact)` (if supported)
   - Agent calls `provider.set_metadata(work_item_id, {idempotency_marker: true})`

6. **Loop**
   - Return to step 1 (state changed, may trigger next agent)

**Key Properties:**
- Orchestrator is **stateless** (all state in external work tracking system)
- Agents are **stateless workers** (all context from WorkItem)
- Provider is **authority** (source of truth)
- AgentLeeOps is **accelerator** (adds intelligence, doesn't own data)

### 3.3 Component Responsibilities

| Component | Responsibility | Does NOT |
|-----------|---------------|----------|
| **Orchestrator** | State change detection, agent routing, governance enforcement | Own work item data, render UI, manage users |
| **WorkItemProvider** | Abstract interface to external system | Business logic, agent decisions, workflow rules |
| **Agent** | Domain-specific work (design, test, code) | State management, persistence, work item queries |
| **External System** | Authoritative work item storage, user management, reporting | Agent execution, AI decisions, file generation |

---

## 4. Work Item Abstraction

### 4.1 WorkItem Data Structure

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class WorkItem:
    """Universal work item representation."""

    # Identity
    id: str                          # Stable, unique identifier
    type: str                        # "task", "story", "issue", "bug", etc.

    # Core content
    title: str                       # Short summary
    description: str                 # Full description (may contain YAML)
    state: str                       # Current lifecycle state

    # Metadata
    metadata: dict[str, str]         # Custom fields (dirname, context_mode, etc.)
    tags: list[str]                  # Labels/tags for idempotency tracking

    # Context
    project_id: str                  # Parent project/board/repository
    assignee: str | None             # Current owner (optional)
    reporter: str | None             # Creator (optional)

    # Provider-specific
    raw: dict[str, Any]              # Original provider response
    provider_type: str               # "kanboard", "jira", "ado", etc.
```

**Design Notes:**
- **Minimal fields:** Only what agents truly need
- **String states:** Provider-specific state names (not normalized)
- **Metadata as dict:** Flexible key-value storage (maps to custom fields)
- **Tags as list:** Simple string labels (maps to labels/tags)
- **Raw preservation:** Full provider response available for debugging

### 4.2 WorkItemState Enum (Logical States)

AgentLeeOps defines **logical states** that map to provider-specific states:

```python
from enum import Enum

class AgentLeeOpsState(Enum):
    """Logical workflow states for AgentLeeOps."""

    # Intake
    INBOX = "inbox"

    # Design phase
    DESIGN_DRAFT = "design_draft"
    DESIGN_APPROVED = "design_approved"

    # Planning phase
    PLANNING_DRAFT = "planning_draft"
    PLAN_APPROVED = "plan_approved"

    # Test phase
    TESTS_DRAFT = "tests_draft"
    TESTS_APPROVED = "tests_approved"

    # Implementation phase
    IMPLEMENTATION = "implementation"

    # Review phase
    FINAL_REVIEW = "final_review"

    # Terminal
    DONE = "done"
```

**State Mapping:**

Providers map their native states to logical states:

```yaml
# Kanboard mapping (config/state-mapping.yaml)
kanboard:
  state_mapping:
    "Inbox": "inbox"
    "Design Draft": "design_draft"
    "Design Approved": "design_approved"
    "Planning Draft": "planning_draft"
    "Plan Approved": "plan_approved"
    "Tests Draft": "tests_draft"
    "Tests Approved": "tests_approved"
    "Ralph Loop": "implementation"
    "Final Review": "final_review"
    "Done": "done"

# Jira mapping
jira:
  state_mapping:
    "Backlog": "inbox"
    "In Design": "design_draft"
    "Design Review": "design_approved"
    "In Planning": "planning_draft"
    "Ready for Dev": "plan_approved"
    "In Test Creation": "tests_draft"
    "Tests Ready": "tests_approved"
    "In Progress": "implementation"
    "Code Review": "final_review"
    "Done": "done"
```

**Rationale:**
- Providers have different state names (Jira: "In Progress", Kanboard: "Ralph Loop")
- Agents work with **logical states** (don't care about provider names)
- Mapping is **configurable** (enterprises customize Jira workflows)

### 4.3 WorkItemQuery (Discovery)

How orchestrator finds work to process:

```python
@dataclass
class WorkItemQuery:
    """Query for discovering work items."""

    project_id: str
    states: list[str] | None = None       # Filter by states
    tags: list[str] | None = None         # Filter by tags
    updated_since: datetime | None = None # Only recently changed
    limit: int = 100
```

**Usage:**
```python
# Find all work items in "design_draft" state
query = WorkItemQuery(
    project_id="PROJ-1",
    states=["design_draft"],
    limit=10
)
work_items = provider.list_work_items(query)
```

---

## 5. State Machine Design

### 5.1 Agent Workflow as State Transitions

Current AgentLeeOps has a **column-based workflow**:
```
Inbox → Design Draft → Design Approved → Planning Draft → ...
```

This becomes a **state machine** with:
- **States:** Named lifecycle stages
- **Transitions:** Agent actions that move between states
- **Guards:** Conditions that must be true for transitions
- **Actions:** What happens during a transition (agent execution)

### 5.2 State Transition Table

| Current State | Agent | Guard | Action | Next State |
|---------------|-------|-------|--------|------------|
| `inbox` | - | Manual move | - | `design_draft` |
| `design_draft` | ARCHITECT | !has_tag("design-started") | Generate DESIGN.md | `design_draft` (with tag) |
| `design_draft` | - | has_tag("design-generated") | Manual approval | `design_approved` |
| `design_approved` | GOVERNANCE | !has_tag("locked") | Lock DESIGN.md | `design_approved` (with tag) |
| `design_approved` | - | Manual move | - | `planning_draft` |
| `planning_draft` | PM | !has_tag("planning-started") | Generate prd.json | `planning_draft` (with tag) |
| `planning_draft` | - | has_tag("planning-generated") | Manual approval | `plan_approved` |
| `plan_approved` | SPAWNER | !has_tag("spawned") | Create child tasks | `plan_approved` (with tag) |
| `plan_approved` | - | Manual move | - | `tests_draft` |
| `tests_draft` | TEST | !has_tag("tests-started") | Generate tests | `tests_draft` (with tag) |
| `tests_draft` | - | has_tag("tests-generated") | Manual approval | `tests_approved` |
| `tests_approved` | GOVERNANCE | !has_tag("locked-tests") | Lock tests | `tests_approved` (with tag) |
| `tests_approved` | - | Manual move | - | `implementation` |
| `implementation` | RALPH | !has_tag("coding-complete") | TDD loop | `implementation` (iterates) |
| `implementation` | - | has_tag("coding-complete") | Manual approval | `final_review` |
| `final_review` | - | Manual QA | - | `done` |

### 5.3 State Machine Configuration

```yaml
# config/workflow.yaml
workflow:
  states:
    inbox:
      agents: []
      allow_manual_transition_to: ["design_draft"]

    design_draft:
      agents:
        - name: ARCHITECT
          guard: "!has_tag('design-started')"
          action: "generate_design"
          sets_tag: "design-generated"
      allow_manual_transition_to: ["design_approved"]

    design_approved:
      agents:
        - name: GOVERNANCE
          guard: "!has_tag('locked')"
          action: "lock_artifacts"
          sets_tag: "locked"
      allow_manual_transition_to: ["planning_draft"]

    planning_draft:
      agents:
        - name: PM
          guard: "!has_tag('planning-started')"
          action: "generate_prd"
          sets_tag: "planning-generated"
      allow_manual_transition_to: ["plan_approved"]

    # ... etc
```

**Benefits:**
- **Declarative:** Workflow defined in config, not code
- **Inspectable:** Can visualize state machine
- **Testable:** Can validate state transitions
- **Flexible:** Easy to add new states or modify transitions

### 5.4 State Transition Engine

```python
class StateMachine:
    """Manages state transitions and agent dispatch."""

    def __init__(self, config: WorkflowConfig):
        self.states = config.states
        self.transitions = self._build_transition_map(config)

    def should_trigger_agent(
        self,
        work_item: WorkItem,
        agent_name: str
    ) -> bool:
        """Check if agent should run for this work item."""
        state_config = self.states[work_item.state]

        for agent_config in state_config.agents:
            if agent_config.name == agent_name:
                # Evaluate guard condition
                return self._evaluate_guard(
                    agent_config.guard,
                    work_item
                )

        return False

    def _evaluate_guard(self, guard: str, work_item: WorkItem) -> bool:
        """Evaluate guard expression."""
        # Simple expression evaluator
        if guard.startswith("!has_tag("):
            tag = guard.split("'")[1]
            return tag not in work_item.tags
        # ... other guard types
        return True

    def get_next_agent(self, work_item: WorkItem) -> str | None:
        """Determine which agent should process this work item."""
        state_config = self.states.get(work_item.state)
        if not state_config:
            return None

        for agent_config in state_config.agents:
            if self.should_trigger_agent(work_item, agent_config.name):
                return agent_config.name

        return None
```

---

## 6. Work Item Provider Protocol

### 6.1 Core Protocol Definition

```python
from typing import Protocol, Any

class WorkItemProvider(Protocol):
    """Interface all work item providers must implement."""

    # Identity
    id: str                    # Provider instance ID
    type: str                  # Provider type ("kanboard", "jira", etc.)

    # Configuration
    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate provider configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        ...

    # Work Item Operations
    def get_work_item(self, work_item_id: str) -> WorkItem:
        """Fetch a work item by ID.

        Args:
            work_item_id: Stable work item identifier

        Returns:
            WorkItem with all available data

        Raises:
            WorkItemNotFound: If work item doesn't exist
            ProviderError: If API call fails
        """
        ...

    def list_work_items(self, query: WorkItemQuery) -> list[WorkItem]:
        """Query for work items.

        Args:
            query: Filter criteria

        Returns:
            List of matching work items
        """
        ...

    # State Operations
    def update_state(
        self,
        work_item_id: str,
        new_state: str
    ) -> WorkItem:
        """Transition work item to new state.

        Args:
            work_item_id: Work item to update
            new_state: Target state (provider-specific name)

        Returns:
            Updated WorkItem

        Raises:
            InvalidTransition: If transition not allowed
        """
        ...

    def get_available_states(self, project_id: str) -> list[str]:
        """Get all possible states for this project.

        Returns:
            List of state names (provider-specific)
        """
        ...

    # Metadata Operations
    def get_metadata(self, work_item_id: str) -> dict[str, str]:
        """Get custom metadata for work item.

        Returns:
            Key-value pairs (all values as strings)
        """
        ...

    def set_metadata(
        self,
        work_item_id: str,
        metadata: dict[str, str]
    ) -> bool:
        """Set custom metadata (replaces all).

        Args:
            work_item_id: Work item to update
            metadata: Key-value pairs to store

        Returns:
            True if successful
        """
        ...

    def update_metadata(
        self,
        work_item_id: str,
        updates: dict[str, str]
    ) -> bool:
        """Update specific metadata fields.

        Args:
            work_item_id: Work item to update
            updates: Fields to add/update

        Returns:
            True if successful
        """
        ...

    # Tag/Label Operations
    def get_tags(self, work_item_id: str) -> list[str]:
        """Get all tags for work item."""
        ...

    def add_tag(self, work_item_id: str, tag: str) -> bool:
        """Add a tag to work item."""
        ...

    def remove_tag(self, work_item_id: str, tag: str) -> bool:
        """Remove a tag from work item."""
        ...

    # Communication
    def post_comment(
        self,
        work_item_id: str,
        content: str,
        markdown: bool = True
    ) -> bool:
        """Post a comment/note on work item.

        Args:
            work_item_id: Work item to comment on
            content: Comment text
            markdown: Whether content is markdown formatted

        Returns:
            True if successful
        """
        ...

    # Artifact Management (Optional Capability)
    def attach_artifact(
        self,
        work_item_id: str,
        filename: str,
        content: bytes,
        mime_type: str | None = None
    ) -> str | None:
        """Attach a file to work item.

        Returns:
            Artifact ID if successful, None if not supported
        """
        ...

    def get_artifacts(self, work_item_id: str) -> list[dict]:
        """List attached artifacts.

        Returns:
            List of artifact metadata dicts
        """
        ...

    # Relationships (Optional Capability)
    def link_work_items(
        self,
        parent_id: str,
        child_id: str,
        relation_type: str = "relates_to"
    ) -> bool:
        """Create relationship between work items.

        Returns:
            True if successful, False if not supported
        """
        ...

    def get_related_work_items(
        self,
        work_item_id: str
    ) -> list[str]:
        """Get IDs of related work items.

        Returns:
            List of work item IDs
        """
        ...

    # Work Item Creation (For Spawner)
    def create_work_item(
        self,
        project_id: str,
        title: str,
        description: str,
        state: str,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None
    ) -> WorkItem:
        """Create a new work item.

        Args:
            project_id: Target project
            title: Work item title
            description: Full description
            state: Initial state
            metadata: Optional custom metadata
            tags: Optional initial tags

        Returns:
            Newly created WorkItem
        """
        ...

    # Webhook Support (Optional Capability)
    def supports_webhooks(self) -> bool:
        """Check if provider supports webhooks."""
        ...

    def parse_webhook_payload(
        self,
        payload: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """Parse webhook payload.

        Args:
            payload: Raw webhook POST body

        Returns:
            (event_type, work_item_id, new_state) if valid, None otherwise
        """
        ...
```

### 6.2 Capability Detection

Not all providers support all features. Use capability detection:

```python
class ProviderCapabilities:
    """Describes provider capabilities."""

    def __init__(self, provider: WorkItemProvider):
        self.provider = provider
        self._detect_capabilities()

    def _detect_capabilities(self):
        """Detect what provider supports."""
        # Check if attach_artifact returns None (not supported)
        self.supports_artifacts = self._test_artifact_support()

        # Check if link_work_items returns False (not supported)
        self.supports_relationships = self._test_relationship_support()

        # Check webhook support
        self.supports_webhooks = self.provider.supports_webhooks()

    def has_capability(self, capability: str) -> bool:
        """Check if capability is supported."""
        return getattr(self, f"supports_{capability}", False)
```

**Usage in Agents:**

```python
# In architect.py
def upload_design(work_item_id: str, design_content: str):
    if capabilities.has_capability("artifacts"):
        # Preferred: attach as file
        provider.attach_artifact(
            work_item_id,
            "DESIGN.md",
            design_content.encode(),
            "text/markdown"
        )
    else:
        # Fallback: post as comment with link to workspace
        workspace_path = get_workspace_for(work_item_id)
        design_path = workspace_path / "DESIGN.md"
        design_path.write_text(design_content)

        provider.post_comment(
            work_item_id,
            f"✅ DESIGN.md generated: `{design_path}`"
        )
```

### 6.3 Error Handling

```python
class WorkItemNotFound(Exception):
    """Work item doesn't exist."""
    pass

class InvalidTransition(Exception):
    """State transition not allowed."""
    pass

class ProviderError(Exception):
    """Generic provider API error."""
    pass

class MetadataNotSupported(Exception):
    """Provider doesn't support custom metadata."""
    pass
```

---

## 7. Reference Implementation: Kanboard

### 7.1 Kanboard as Proof of Concept

Kanboard validates that the WorkItemProvider abstraction:
- ✅ Supports full agent workflow
- ✅ Handles all required operations
- ✅ Provides necessary metadata storage
- ✅ Enables governance (ratchet, test integrity)

### 7.2 KanboardWorkItemProvider

```python
# lib/workitem/providers/kanboard.py
class KanboardWorkItemProvider(WorkItemProvider):
    """Kanboard implementation of WorkItemProvider."""

    def __init__(self, config: dict):
        from kanboard import Client

        self.id = "kanboard"
        self.type = "kanboard"
        self.url = config["url"]
        self.user = config["user"]
        self.token = os.getenv(config["token_env"])
        self.project_id = config["project_id"]

        self.client = Client(self.url, self.user, self.token)
        self._column_cache = None
        self._state_mapping = config.get("state_mapping", {})

    def get_work_item(self, work_item_id: str) -> WorkItem:
        """Fetch task from Kanboard."""
        task = self.client.get_task(int(work_item_id))
        if not task:
            raise WorkItemNotFound(f"Task {work_item_id} not found")

        # Get column name (state)
        column = self._get_column_name(task["column_id"])

        # Get metadata
        metadata = self.client.execute(
            "getTaskMetadata",
            task_id=int(work_item_id)
        )

        # Get tags
        tags = self._get_tags_list(int(work_item_id))

        return WorkItem(
            id=str(task["id"]),
            type="task",
            title=task["title"],
            description=task["description"],
            state=column,  # Column name is the state
            metadata=metadata or {},
            tags=tags,
            project_id=str(task["project_id"]),
            assignee=str(task["owner_id"]) if task["owner_id"] else None,
            reporter=str(task["creator_id"]),
            raw=task,
            provider_type="kanboard"
        )

    def update_state(
        self,
        work_item_id: str,
        new_state: str
    ) -> WorkItem:
        """Move task to new column."""
        # Resolve column name to ID
        column_id = self._get_column_id(new_state)
        if not column_id:
            raise InvalidTransition(
                f"Invalid state: {new_state}"
            )

        # Execute move
        success = self.client.execute(
            "updateTask",
            id=int(work_item_id),
            column_id=column_id
        )

        if not success:
            raise ProviderError(
                f"Failed to move task {work_item_id} to {new_state}"
            )

        # Return updated work item
        return self.get_work_item(work_item_id)

    def get_metadata(self, work_item_id: str) -> dict[str, str]:
        """Get MetaMagik custom fields."""
        metadata = self.client.execute(
            "getTaskMetadata",
            task_id=int(work_item_id)
        )
        return metadata or {}

    def set_metadata(
        self,
        work_item_id: str,
        metadata: dict[str, str]
    ) -> bool:
        """Save MetaMagik custom fields."""
        success = self.client.execute(
            "saveTaskMetadata",
            task_id=int(work_item_id),
            values=metadata
        )
        return bool(success)

    def add_tag(self, work_item_id: str, tag: str) -> bool:
        """Add tag to task."""
        tags = self.get_tags(work_item_id)
        if tag not in tags:
            tags.append(tag)
            return self.client.set_task_tags(
                project_id=int(self.project_id),
                task_id=int(work_item_id),
                tags=tags
            )
        return True

    def post_comment(
        self,
        work_item_id: str,
        content: str,
        markdown: bool = True
    ) -> bool:
        """Post comment on task."""
        comment_id = self.client.create_comment(
            task_id=int(work_item_id),
            content=content,
            user_id=0  # System user
        )
        return bool(comment_id)

    def attach_artifact(
        self,
        work_item_id: str,
        filename: str,
        content: bytes,
        mime_type: str | None = None
    ) -> str | None:
        """Upload file to task."""
        # Kanboard requires base64 encoding
        import base64
        file_b64 = base64.b64encode(content).decode()

        file_id = self.client.create_task_file(
            task_id=int(work_item_id),
            project_id=int(self.project_id),
            filename=filename,
            blob=file_b64
        )

        return str(file_id) if file_id else None

    def create_work_item(
        self,
        project_id: str,
        title: str,
        description: str,
        state: str,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None
    ) -> WorkItem:
        """Create new task in Kanboard."""
        # Get column ID for state
        column_id = self._get_column_id(state)

        # Create task
        task_id = self.client.execute(
            "createTask",
            title=title,
            project_id=int(project_id),
            column_id=column_id,
            description=description
        )

        if not task_id:
            raise ProviderError("Failed to create task")

        # Set metadata if provided
        if metadata:
            self.set_metadata(str(task_id), metadata)

        # Set tags if provided
        if tags:
            self.client.set_task_tags(
                project_id=int(project_id),
                task_id=task_id,
                tags=tags
            )

        return self.get_work_item(str(task_id))

    def supports_webhooks(self) -> bool:
        """Kanboard supports webhooks."""
        return True

    def parse_webhook_payload(
        self,
        payload: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """Parse Kanboard webhook."""
        event_name = payload.get("event_name")
        if event_name not in ["task.move.column", "task.create"]:
            return None

        task_id = str(payload.get("event_data", {}).get("task_id"))
        if not task_id:
            return None

        # Fetch task to get new state
        task = self.get_work_item(task_id)

        return (event_name, task_id, task.state)

    # Helper methods
    def _get_column_name(self, column_id: int) -> str:
        """Resolve column ID to name."""
        if not self._column_cache:
            self._column_cache = self.client.get_columns(
                int(self.project_id)
            )

        for col in self._column_cache:
            if col["id"] == str(column_id):
                return col["title"]

        return "unknown"

    def _get_column_id(self, column_name: str) -> int | None:
        """Resolve column name to ID."""
        if not self._column_cache:
            self._column_cache = self.client.get_columns(
                int(self.project_id)
            )

        for col in self._column_cache:
            if col["title"] == column_name:
                return int(col["id"])

        return None

    def _get_tags_list(self, task_id: int) -> list[str]:
        """Get task tags as list."""
        tags_data = self.client.get_task_tags(task_id)

        # Handle different response formats
        if isinstance(tags_data, list):
            return tags_data
        elif isinstance(tags_data, dict):
            return list(tags_data.values())

        return []
```

### 7.3 Kanboard Configuration

```yaml
# config/workitem.yaml
workitem:
  type: kanboard

  providers:
    kanboard:
      url: "http://localhost:88/jsonrpc.php"
      user: "jsonrpc"
      token_env: "KANBOARD_TOKEN"
      project_id: "1"

      # Map Kanboard columns to logical states
      state_mapping:
        "Inbox": "inbox"
        "Design Draft": "design_draft"
        "Design Approved": "design_approved"
        "Planning Draft": "planning_draft"
        "Plan Approved": "plan_approved"
        "Tests Draft": "tests_draft"
        "Tests Approved": "tests_approved"
        "Ralph Loop": "implementation"
        "Final Review": "final_review"
        "Done": "done"
```

---

## 8. Enterprise Implementations

### 8.1 Jira Work Item Provider

**Jira Challenges:**
- Typed custom fields (need field discovery)
- Complex permission model
- Workflow state transitions (not just column moves)
- Instance-specific field IDs

**Implementation Sketch:**

```python
# lib/workitem/providers/jira.py
class JiraWorkItemProvider(WorkItemProvider):
    """Jira REST API v3 implementation."""

    def __init__(self, config: dict):
        self.id = "jira"
        self.type = "jira"
        self.url = config["url"]  # https://company.atlassian.net
        self.email = config["email"]
        self.token = os.getenv(config["token_env"])
        self.project_key = config["project_key"]  # e.g., "AGENT"

        self.session = requests.Session()
        self.session.auth = (self.email, self.token)
        self.session.headers.update({
            "Content-Type": "application/json"
        })

        # Discover custom field IDs
        self._field_map = self._discover_custom_fields()

    def get_work_item(self, work_item_id: str) -> WorkItem:
        """Fetch Jira issue."""
        response = self.session.get(
            f"{self.url}/rest/api/3/issue/{work_item_id}"
        )
        response.raise_for_status()
        issue = response.json()

        fields = issue["fields"]

        # Extract metadata from custom fields
        metadata = {}
        for field_name, field_id in self._field_map.items():
            if field_id in fields:
                value = fields[field_id]
                # Handle different field types
                if isinstance(value, dict):
                    metadata[field_name] = str(value.get("value", ""))
                elif isinstance(value, list):
                    metadata[field_name] = ",".join(str(v) for v in value)
                else:
                    metadata[field_name] = str(value) if value else ""

        return WorkItem(
            id=issue["key"],  # e.g., "AGENT-123"
            type=fields["issuetype"]["name"].lower(),
            title=fields["summary"],
            description=fields["description"] or "",
            state=fields["status"]["name"],  # e.g., "In Progress"
            metadata=metadata,
            tags=[label for label in fields.get("labels", [])],
            project_id=fields["project"]["key"],
            assignee=fields.get("assignee", {}).get("emailAddress"),
            reporter=fields.get("reporter", {}).get("emailAddress"),
            raw=issue,
            provider_type="jira"
        )

    def update_state(
        self,
        work_item_id: str,
        new_state: str
    ) -> WorkItem:
        """Transition Jira issue.

        Jira uses workflow transitions, not direct state setting.
        Must find transition ID that leads to target state.
        """
        # Get available transitions
        response = self.session.get(
            f"{self.url}/rest/api/3/issue/{work_item_id}/transitions"
        )
        response.raise_for_status()
        transitions = response.json()["transitions"]

        # Find transition to target state
        transition_id = None
        for trans in transitions:
            if trans["to"]["name"] == new_state:
                transition_id = trans["id"]
                break

        if not transition_id:
            raise InvalidTransition(
                f"No transition available to state: {new_state}"
            )

        # Execute transition
        response = self.session.post(
            f"{self.url}/rest/api/3/issue/{work_item_id}/transitions",
            json={"transition": {"id": transition_id}}
        )
        response.raise_for_status()

        return self.get_work_item(work_item_id)

    def get_metadata(self, work_item_id: str) -> dict[str, str]:
        """Get custom field values."""
        work_item = self.get_work_item(work_item_id)
        return work_item.metadata

    def set_metadata(
        self,
        work_item_id: str,
        metadata: dict[str, str]
    ) -> bool:
        """Update custom fields."""
        # Convert metadata keys to field IDs
        fields = {}
        for field_name, value in metadata.items():
            field_id = self._field_map.get(field_name)
            if field_id:
                # Type handling based on field type
                fields[field_id] = value

        if not fields:
            return True  # Nothing to update

        response = self.session.put(
            f"{self.url}/rest/api/3/issue/{work_item_id}",
            json={"fields": fields}
        )
        response.raise_for_status()
        return True

    def add_tag(self, work_item_id: str, tag: str) -> bool:
        """Add label to issue."""
        response = self.session.put(
            f"{self.url}/rest/api/3/issue/{work_item_id}",
            json={
                "update": {
                    "labels": [{"add": tag}]
                }
            }
        )
        response.raise_for_status()
        return True

    def post_comment(
        self,
        work_item_id: str,
        content: str,
        markdown: bool = True
    ) -> bool:
        """Add comment to issue."""
        # Jira uses ADF (Atlassian Document Format), not markdown
        # For simplicity, convert to plain text for now
        body = {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": content
                }]
            }]
        }

        response = self.session.post(
            f"{self.url}/rest/api/3/issue/{work_item_id}/comment",
            json={"body": body}
        )
        response.raise_for_status()
        return True

    def _discover_custom_fields(self) -> dict[str, str]:
        """Map field names to Jira field IDs.

        Jira custom fields have instance-specific IDs like:
        customfield_10001, customfield_10002, etc.

        We need to discover which IDs map to our field names.
        """
        response = self.session.get(
            f"{self.url}/rest/api/3/field"
        )
        response.raise_for_status()
        fields = response.json()

        # Build mapping of name -> id for custom fields
        field_map = {}
        for field in fields:
            if field.get("custom"):
                name = field["name"]
                field_id = field["id"]
                field_map[name] = field_id

        return field_map

    def supports_webhooks(self) -> bool:
        """Jira supports webhooks."""
        return True

    def parse_webhook_payload(
        self,
        payload: dict[str, Any]
    ) -> tuple[str, str, str] | None:
        """Parse Jira webhook."""
        event = payload.get("webhookEvent")
        if not event or not event.startswith("jira:issue_"):
            return None

        issue = payload.get("issue")
        if not issue:
            return None

        work_item_id = issue["key"]
        new_state = issue["fields"]["status"]["name"]

        return (event, work_item_id, new_state)
```

**Jira Configuration:**

```yaml
# config/workitem.yaml
workitem:
  type: jira

  providers:
    jira:
      url: "https://mycompany.atlassian.net"
      email: "agentbot@mycompany.com"
      token_env: "JIRA_API_TOKEN"
      project_key: "AGENT"

      # Map Jira statuses to logical states
      state_mapping:
        "Backlog": "inbox"
        "In Design": "design_draft"
        "Design Review": "design_approved"
        "In Planning": "planning_draft"
        "Ready for Development": "plan_approved"
        "Test Creation": "tests_draft"
        "Tests Ready": "tests_approved"
        "In Progress": "implementation"
        "Code Review": "final_review"
        "Done": "done"

      # Map logical field names to Jira custom field names
      field_mapping:
        dirname: "Project Directory"
        context_mode: "Context Mode"
        acceptance_criteria: "Acceptance Criteria"
        complexity: "Complexity"
        atomic_id: "Atomic Story ID"
        parent_id: "Parent Epic"
```

### 8.2 Azure DevOps Work Item Provider

**Azure DevOps Challenges:**
- Different API structure (REST, not GraphQL/JSON-RPC)
- "Work Item" is first-class concept (closer to our model)
- State transitions via PATCH operations
- Personal Access Token (PAT) authentication

**Implementation Sketch:**

```python
# lib/workitem/providers/azuredevops.py
class AzureDevOpsWorkItemProvider(WorkItemProvider):
    """Azure DevOps REST API implementation."""

    def __init__(self, config: dict):
        self.id = "ado"
        self.type = "azuredevops"
        self.organization = config["organization"]
        self.project = config["project"]
        self.pat = os.getenv(config["pat_env"])

        self.base_url = (
            f"https://dev.azure.com/{self.organization}"
            f"/{self.project}/_apis"
        )

        self.session = requests.Session()
        # ADO uses basic auth with PAT as password
        self.session.auth = ("", self.pat)
        self.session.headers.update({
            "Content-Type": "application/json-patch+json"
        })

    def get_work_item(self, work_item_id: str) -> WorkItem:
        """Fetch work item from ADO."""
        response = self.session.get(
            f"{self.base_url}/wit/workitems/{work_item_id}",
            params={"api-version": "7.0"}
        )
        response.raise_for_status()
        item = response.json()

        fields = item["fields"]

        # Extract metadata (ADO allows arbitrary fields)
        metadata = {}
        for key, value in fields.items():
            if key.startswith("Custom."):
                field_name = key.replace("Custom.", "")
                metadata[field_name] = str(value)

        # Extract tags (semicolon-separated in ADO)
        tags_str = fields.get("System.Tags", "")
        tags = [t.strip() for t in tags_str.split(";") if t.strip()]

        return WorkItem(
            id=str(item["id"]),
            type=fields["System.WorkItemType"].lower(),
            title=fields["System.Title"],
            description=fields.get("System.Description", ""),
            state=fields["System.State"],
            metadata=metadata,
            tags=tags,
            project_id=self.project,
            assignee=fields.get("System.AssignedTo", {}).get("uniqueName"),
            reporter=fields.get("System.CreatedBy", {}).get("uniqueName"),
            raw=item,
            provider_type="azuredevops"
        )

    def update_state(
        self,
        work_item_id: str,
        new_state: str
    ) -> WorkItem:
        """Update work item state via PATCH."""
        response = self.session.patch(
            f"{self.base_url}/wit/workitems/{work_item_id}",
            params={"api-version": "7.0"},
            json=[{
                "op": "add",
                "path": "/fields/System.State",
                "value": new_state
            }]
        )
        response.raise_for_status()

        return self.get_work_item(work_item_id)

    def set_metadata(
        self,
        work_item_id: str,
        metadata: dict[str, str]
    ) -> bool:
        """Update custom fields."""
        # Build JSON patch operations
        operations = []
        for key, value in metadata.items():
            operations.append({
                "op": "add",
                "path": f"/fields/Custom.{key}",
                "value": value
            })

        response = self.session.patch(
            f"{self.base_url}/wit/workitems/{work_item_id}",
            params={"api-version": "7.0"},
            json=operations
        )
        response.raise_for_status()
        return True

    # ... similar implementations for other methods
```

**Azure DevOps Configuration:**

```yaml
# config/workitem.yaml
workitem:
  type: azuredevops

  providers:
    azuredevops:
      organization: "mycompany"
      project: "AgentLeeOps"
      pat_env: "AZURE_DEVOPS_PAT"

      state_mapping:
        "New": "inbox"
        "In Design": "design_draft"
        "Design Approved": "design_approved"
        "In Planning": "planning_draft"
        "Ready": "plan_approved"
        "Test Draft": "tests_draft"
        "Test Approved": "tests_approved"
        "Active": "implementation"
        "Review": "final_review"
        "Closed": "done"
```

---

## 9. Agent Integration Model

### 9.1 How Agents Consume Work Items

Agents interact with work items through the WorkItemClient (similar to LLMClient):

```python
# lib/workitem/client.py
class WorkItemClient:
    """Main client for work item operations."""

    def __init__(self, config: WorkItemConfig):
        self.config = config
        self._provider = None
        self._capabilities = None

    @classmethod
    def from_config(cls, config_path: str) -> "WorkItemClient":
        """Load from YAML config."""
        config = load_workitem_config(config_path)
        return cls(config)

    @property
    def provider(self) -> WorkItemProvider:
        """Get configured provider."""
        if not self._provider:
            provider_class = get_provider(self.config.type)
            provider_config = self.config.providers[self.config.type]
            self._provider = provider_class(provider_config)
        return self._provider

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        if not self._capabilities:
            self._capabilities = ProviderCapabilities(self.provider)
        return self._capabilities

    # Delegate all operations
    def get_work_item(self, work_item_id: str) -> WorkItem:
        return self.provider.get_work_item(work_item_id)

    def update_state(self, work_item_id: str, new_state: str) -> WorkItem:
        return self.provider.update_state(work_item_id, new_state)

    # ... etc
```

### 9.2 Agent Example: Architect

```python
# agents/architect.py (refactored)
from lib.workitem import WorkItemClient

def architect_agent(work_item_id: str):
    """Generate DESIGN.md for a work item."""
    # Initialize clients
    workitem = WorkItemClient.from_config("config/workitem.yaml")
    llm = LLMClient.from_config("config/llm.yaml")

    # Fetch work item
    item = workitem.get_work_item(work_item_id)

    # Check idempotency
    if "design-started" in item.tags:
        logger.info("Design already started, skipping")
        return

    # Mark as started
    workitem.add_tag(work_item_id, "design-started")
    workitem.post_comment(
        work_item_id,
        "🏗️ ARCHITECT_AGENT started design generation"
    )

    try:
        # Generate design
        prompt = build_design_prompt(item)
        response = llm.complete(
            role="planner",
            messages=[{"role": "user", "content": prompt}]
        )
        design_content = response.text

        # Store design
        if workitem.capabilities.has_capability("artifacts"):
            # Preferred: attach as file
            workitem.attach_artifact(
                work_item_id,
                "DESIGN.md",
                design_content.encode(),
                "text/markdown"
            )
        else:
            # Fallback: save to workspace, link in comment
            workspace = get_workspace(item.metadata["dirname"])
            design_path = workspace / "DESIGN.md"
            design_path.write_text(design_content)

            workitem.post_comment(
                work_item_id,
                f"✅ DESIGN.md generated: `{design_path}`\n\n"
                f"View: file://{design_path}"
            )

        # Mark as complete
        workitem.add_tag(work_item_id, "design-generated")
        workitem.post_comment(
            work_item_id,
            "✅ ARCHITECT_AGENT completed design generation"
        )

    except Exception as e:
        workitem.post_comment(
            work_item_id,
            f"❌ ARCHITECT_AGENT failed: {e}"
        )
        raise
```

### 9.3 Orchestrator Example

```python
# orchestrator.py (refactored)
from lib.workitem import WorkItemClient
from lib.workflow import StateMachine

def main():
    # Initialize
    workitem = WorkItemClient.from_config("config/workitem.yaml")
    workflow = StateMachine.from_config("config/workflow.yaml")

    # Get project ID from config
    project_id = workitem.config.providers[workitem.config.type]["project_id"]

    # Query for work items
    query = WorkItemQuery(
        project_id=project_id,
        updated_since=datetime.now() - timedelta(minutes=5)
    )

    work_items = workitem.list_work_items(query)

    for item in work_items:
        # Determine which agent should run
        agent_name = workflow.get_next_agent(item)

        if agent_name:
            logger.info(f"Triggering {agent_name} for {item.id}")
            dispatch_agent(agent_name, item.id)
        else:
            logger.debug(f"No agent for {item.id} in state {item.state}")

def dispatch_agent(agent_name: str, work_item_id: str):
    """Dispatch agent execution."""
    if agent_name == "ARCHITECT":
        from agents.architect import architect_agent
        architect_agent(work_item_id)
    elif agent_name == "PM":
        from agents.pm import pm_agent
        pm_agent(work_item_id)
    # ... etc
```

---

## 10. Governance & Safety Preservation

### 10.1 Ratchet Enforcement

Current AgentLeeOps uses the "ratchet" to prevent regression:
- Once DESIGN.md is approved, it cannot be modified
- Once tests are approved, they cannot be modified

This continues to work because:
1. **Ratchet is workspace-based**, not board-based
2. **Governance agent** still runs on state transitions
3. **Hash verification** still happens before commits

**Integration:**

```python
# agents/governance.py (refactored)
def governance_agent(work_item_id: str):
    """Lock artifacts after approval."""
    workitem = WorkItemClient.from_config("config/workitem.yaml")
    item = workitem.get_work_item(work_item_id)

    # Get workspace
    dirname = item.metadata.get("dirname")
    if not dirname:
        raise ValueError("No dirname in metadata")

    workspace = Path.home() / "projects" / dirname

    # Lock artifacts based on state
    if item.state == "design_approved":
        # Lock DESIGN.md
        lock_artifact(workspace, "DESIGN.md")
        workitem.add_tag(work_item_id, "locked-design")
        workitem.post_comment(
            work_item_id,
            "🔒 GOVERNANCE: DESIGN.md locked"
        )

    elif item.state == "tests_approved":
        # Lock all test files
        for test_file in (workspace / "tests").glob("test_*.py"):
            lock_artifact(workspace, test_file.relative_to(workspace))

        workitem.add_tag(work_item_id, "locked-tests")
        workitem.post_comment(
            work_item_id,
            "🔒 GOVERNANCE: Tests locked"
        )
```

### 10.2 Test Integrity

Ralph's constraints remain:
1. **Before coding:** Verify test file is unmodified (hash check)
2. **Before commit:** Ensure no test files are staged

This is **independent of board system** because it operates on workspace files.

### 10.3 Double-Blind Rule

The Double-Blind Rule (Ralph doesn't write tests) is enforced by:
1. **State machine:** TEST agent runs in `tests_draft` state, Ralph runs in `implementation` state
2. **Ratchet:** Tests are locked before Ralph starts
3. **Git guards:** Ralph cannot stage test files

All of this remains unchanged because it's **workflow logic, not board logic**.

---

## 11. Migration Strategy

### 11.1 Phase 1: Create Abstraction (Non-Breaking)

**Goal:** Build WorkItem abstraction alongside existing Kanboard code.

**Tasks:**
1. Create `lib/workitem/` module
2. Define WorkItemProvider protocol
3. Implement KanboardWorkItemProvider (wraps existing Kanboard calls)
4. Create WorkItemClient
5. Add comprehensive tests

**Validation:**
- All tests pass
- KanboardWorkItemProvider has 100% feature parity with direct Kanboard usage
- No orchestrator changes yet

**Effort:** 2 weeks

### 11.2 Phase 2: Refactor State Machine

**Goal:** Make orchestrator state-driven instead of column-driven.

**Tasks:**
1. Create StateMachine class
2. Define workflow config (`config/workflow.yaml`)
3. Refactor orchestrator to use StateMachine
4. Update webhook_server to use StateMachine

**Validation:**
- Orchestrator routes agents correctly based on states
- Idempotency still works (tag checking)
- All 6 agents still trigger correctly

**Effort:** 1 week

### 11.3 Phase 3: Refactor Agents

**Goal:** Update all agents to use WorkItemClient instead of direct Kanboard calls.

**Tasks:**
1. Refactor each agent (Architect, PM, Spawner, Test, Ralph, Governance)
2. Replace `kanboard.Client` with `WorkItemClient`
3. Add capability detection (file attachments, relationships)
4. Update all comments/logging

**Validation:**
- All agents work with KanboardWorkItemProvider
- Governance rules preserved (ratchet, test integrity)
- End-to-end workflow test passes

**Effort:** 2 weeks

### 11.4 Phase 4: Add Enterprise Provider

**Goal:** Prove abstraction works with non-Kanboard system.

**Tasks:**
1. Implement JiraWorkItemProvider (or AzureDevOpsWorkItemProvider)
2. Add enterprise-specific tests
3. Create setup documentation
4. Test orchestrator with enterprise provider
5. Validate state mapping

**Validation:**
- Can switch between Kanboard and Jira by changing config
- All agents work with both providers
- Governance rules preserved

**Effort:** 2 weeks (Jira) or 1.5 weeks (Azure DevOps)

### 11.5 Timeline

**Total for MVP (Kanboard + Jira):** 7-8 weeks

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 2 weeks | WorkItem abstraction + Kanboard provider |
| Phase 2 | 1 week | State machine refactor |
| Phase 3 | 2 weeks | All agents refactored |
| Phase 4 | 2 weeks | Jira provider + validation |
| **Total** | **7 weeks** | **Production-ready abstraction** |

---

## 12. Capability Detection & Graceful Degradation

### 12.1 Required vs. Optional Capabilities

| Capability | Required | Fallback if Not Supported |
|------------|----------|---------------------------|
| **Work item fetch** | ✅ Required | - |
| **State transitions** | ✅ Required | - |
| **Metadata storage** | ✅ Required | Parse from description (YAML) |
| **Tags/labels** | ✅ Required | Use metadata field |
| **Comments** | ✅ Required | - |
| **File attachments** | ❌ Optional | Store in workspace, link in comment |
| **Work item creation** | ❌ Optional | Manual creation |
| **Work item relationships** | ❌ Optional | Store parent ID in metadata |
| **Webhooks** | ❌ Optional | Fall back to polling |

### 12.2 Graceful Degradation Examples

**Example 1: No File Attachments (Linear)**

```python
def store_artifact(work_item_id: str, filename: str, content: str):
    if capabilities.has_capability("artifacts"):
        # Preferred: attach to work item
        workitem.attach_artifact(
            work_item_id,
            filename,
            content.encode()
        )
    else:
        # Fallback: workspace + comment
        workspace = get_workspace_for(work_item_id)
        artifact_path = workspace / filename
        artifact_path.write_text(content)

        # Option A: Comment with path
        workitem.post_comment(
            work_item_id,
            f"📎 {filename} generated: `{artifact_path}`"
        )

        # Option B: External storage (S3, GitHub)
        if external_storage_configured():
            url = upload_to_s3(filename, content)
            workitem.post_comment(
                work_item_id,
                f"📎 [{filename}]({url})"
            )
```

**Example 2: No Webhooks**

```python
# orchestrator.py
def main():
    workitem = WorkItemClient.from_config("config/workitem.yaml")

    if workitem.capabilities.supports_webhooks:
        # Webhook mode
        from webhook_server import run_webhook_server
        run_webhook_server()
    else:
        # Polling mode
        logger.info("Provider doesn't support webhooks, using polling")
        poll_for_changes(interval=5)
```

**Example 3: No Metadata API (Use Description Parsing)**

```python
def get_metadata_with_fallback(work_item_id: str) -> dict:
    if capabilities.has_capability("metadata"):
        # Preferred: native metadata API
        return workitem.get_metadata(work_item_id)
    else:
        # Fallback: parse YAML from description
        item = workitem.get_work_item(work_item_id)
        return parse_yaml_from_description(item.description)
```

---

## 13. Architecture Validation

### 13.1 Does This Solve the Enterprise Problem?

**Test Case: Cognizant Adoption**

> "Would Cognizant use this?"

**Before (MultiKanban.md approach):**
- AgentLeeOps: "We support Jira, but you need to migrate to our workflow."
- Cognizant: "We have a custom Jira workflow integrated with billing/HR. Can't change it."
- Result: ❌ **No adoption**

**After (WorkItem abstraction approach):**
- AgentLeeOps: "We plug into your existing Jira workflow and make it agent-capable."
- Cognizant: "Our workflow has custom states. Will your agents work?"
- AgentLeeOps: "Yes, you just map your states to our logical states in config. Agents adapt."
- Result: ✅ **Viable conversation**

### 13.2 Does This Preserve AgentLeeOps Core Value?

**Core value:** Safe, auditable, resumable AI workflow

| AgentLeeOps Principle | Preserved? | How? |
|-----------------------|------------|------|
| **Ratchet Effect** | ✅ Yes | Workspace-based hash locking (independent of board) |
| **Double-Blind Rule** | ✅ Yes | State machine enforces TEST agent before RALPH |
| **Test Integrity** | ✅ Yes | Git guards + ratchet (independent of board) |
| **Artifacts over Chat** | ✅ Yes | DESIGN.md, prd.json still generated and stored |
| **Resumable** | ✅ Yes | Work item state + tags enable idempotency |
| **Auditable** | ✅ Yes | Comments log all agent actions |

All core principles **preserved** because they're enforced by:
1. **State machine** (not Kanboard columns)
2. **Workspace file locks** (not board features)
3. **Git integrity checks** (not board features)
4. **Idempotency tags** (work item metadata, available in all systems)

### 13.3 Does This Simplify or Complicate?

**Complexity Added:**
- Provider abstraction layer
- State mapping configuration
- Capability detection

**Complexity Removed:**
- Kanboard-specific assumptions
- Hard-coded column names
- Board UI coupling

**Net Result:** ✅ **Simpler core architecture**

The orchestrator becomes:
```
State change → State machine → Agent dispatch
```

Instead of:
```
Column move → Column name lookup → Column-specific logic → Agent dispatch
```

### 13.4 Can This Scale?

**Scalability Test:**

1. **New provider (Trello):** Implement WorkItemProvider → Done
2. **New agent (REVIEWER):** Add to workflow.yaml → Done
3. **New workflow state:** Add to state machine → Done
4. **Custom Jira workflow:** Update state_mapping → Done

All extensions are **configuration or provider implementation**, not core changes.

---

## Conclusion

### What We're Building

**AgentLeeOps as a Work Item Accelerator Service**

Not a board replacement. Not a workflow owner.

A service that makes **existing enterprise work tracking systems** agent-capable through:
1. Work item abstraction (not board abstraction)
2. State-driven agents (not column-driven)
3. Provider-agnostic operations (configurable mapping)
4. Capability detection (graceful degradation)
5. Kanboard as reference (not destiny)

### Enterprise Pitch

> "AgentLeeOps doesn't replace Jira. It makes Jira agent-capable — safely."

This framing enables:
- ✅ Enterprise adoption (plug into existing systems)
- ✅ Preserved governance (ratchet, test integrity, double-blind)
- ✅ Provider independence (Kanboard, Jira, ADO, Linear, etc.)
- ✅ Scalable architecture (add providers via protocol)

### Kanboard's Role

**Kanboard is the reference implementation.**

It validates that WorkItemProvider:
- Supports full agent workflow
- Handles required operations
- Enables governance

But the product is agent-capable work item management for **any** system.

### Next Steps

1. Review this architecture
2. Validate state machine design
3. Approve migration strategy
4. Begin implementation (Phase 1: WorkItem abstraction)

---

## Appendix: Configuration Examples

### Full Configuration Example

```yaml
# config/workitem.yaml
workitem:
  # Active provider
  type: jira

  # Provider definitions
  providers:
    kanboard:
      url: "http://localhost:88/jsonrpc.php"
      user: "jsonrpc"
      token_env: "KANBOARD_TOKEN"
      project_id: "1"
      state_mapping:
        "Inbox": "inbox"
        "Design Draft": "design_draft"
        # ... etc

    jira:
      url: "https://mycompany.atlassian.net"
      email: "bot@mycompany.com"
      token_env: "JIRA_API_TOKEN"
      project_key: "AGENT"
      state_mapping:
        "Backlog": "inbox"
        "In Design": "design_draft"
        "Design Review": "design_approved"
        # ... etc
      field_mapping:
        dirname: "Project Directory"
        context_mode: "Context Mode"
        acceptance_criteria: "Acceptance Criteria"

    azuredevops:
      organization: "mycompany"
      project: "AgentLeeOps"
      pat_env: "AZURE_DEVOPS_PAT"
      state_mapping:
        "New": "inbox"
        "In Design": "design_draft"
        # ... etc

# config/workflow.yaml
workflow:
  states:
    inbox:
      agents: []
      transitions_to: ["design_draft"]

    design_draft:
      agents:
        - name: ARCHITECT
          guard: "!has_tag('design-started')"
          sets_tag: "design-generated"
      transitions_to: ["design_approved"]

    design_approved:
      agents:
        - name: GOVERNANCE
          guard: "!has_tag('locked-design')"
          sets_tag: "locked-design"
      transitions_to: ["planning_draft"]

    # ... etc
```

---

**End of Architecture Document**
