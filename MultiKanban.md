# Multi-Kanban Board Support Analysis

**Date:** 2026-01-28
**Status:** Design Phase
**Related:** Sprint 16-18 (LLM Provider Abstraction)

## Executive Summary

AgentLeeOps currently has a hard dependency on Kanboard with the MetaMagik plugin. This document analyzes what would be required to support multiple kanban board systems (GitHub Projects, Trello, Jira, Linear, etc.) through a pluggable abstraction similar to the successful LLM provider system.

**Key Findings:**
- **Feasible:** Yes, with similar architecture to LLM abstraction
- **Development Effort:** 3-6 weeks depending on provider count
- **Breaking Changes:** Moderate (orchestrator refactor required)
- **Recommended Approach:** Phased rollout starting with Kanboard refactor

---

## Table of Contents

1. [Current Kanboard Integration](#current-kanboard-integration)
2. [Required Features from Any Board](#required-features-from-any-board)
3. [Proposed Abstraction Design](#proposed-abstraction-design)
4. [Provider Implementation Analysis](#provider-implementation-analysis)
5. [Development Effort Estimation](#development-effort-estimation)
6. [Migration Strategy](#migration-strategy)
7. [Risks & Challenges](#risks--challenges)
8. [Recommendations](#recommendations)

---

## 1. Current Kanboard Integration

### 1.1 API Surface Area

AgentLeeOps uses **20+ Kanboard API methods** across the following categories:

#### Task Management (8 methods)
- `get_task(task_id)` - Fetch task details
- `execute("getTaskMetadata", task_id)` - Get custom fields (MetaMagik)
- `execute("saveTaskMetadata", task_id, values)` - Save custom fields
- `execute("updateTask", ...)` - Update task properties
- `execute("removeTask", task_id)` - Delete task
- `execute("duplicateTaskToProject", ...)` - Clone task (spawner)
- `execute("getAllTaskLinks", task_id)` - Get relationships
- `create_task_link(...)` - Link parent-child tasks

#### Board Management (2 methods)
- `get_columns(project_id)` - Fetch workflow columns
- `add_column(...)` - Create column (setup only)

#### Tag Management (3 methods)
- `get_task_tags(task_id)` - Fetch tags
- `set_task_tags(...)` - Replace all tags
- `create_tag(...)` - Create new tag (setup only)

#### Communication (1 method)
- `create_comment(task_id, content, user_id)` - Post comments

#### File Management (3 methods)
- `get_task_files(task_id)` - List attachments
- `create_task_file(...)` - Upload file (DESIGN.md, prd.json)
- `remove_task_file(...)` - Delete attachment

### 1.2 Critical Features

**Column-Based Workflow (10 columns):**
```
Inbox → Design Draft → Design Approved → Planning Draft → Plan Approved
  → Tests Draft → Tests Approved → Ralph Loop → Final Review → Done
```

**Custom Metadata (via MetaMagik):**
- `dirname` (required) - Project directory name
- `context_mode` - "NEW" or "FEATURE"
- `acceptance_criteria` - Multi-line requirements
- `complexity` - "S", "M", "L", "XL"
- `atomic_id` - Story ID for child tasks
- `parent_id` - Parent task reference
- `agent_status` - "running", "completed", "failed"
- `current_phase` - Current workflow phase

**Idempotency Tags:**
- `design-started`, `design-generated`
- `planning-started`, `planning-generated`
- `locking`, `locked`
- `spawning-started`, `spawned`
- `tests-started`, `tests-generated`
- `coding-started`, `coding-complete`

**Audit Trail:**
- All agent actions posted as task comments
- Errors, successes, iteration counts logged
- Markdown formatting for readability

**Artifact Storage:**
- `DESIGN.md` uploaded by Architect
- `prd.json` uploaded by PM
- Files attached to tasks for persistence

**Event System:**
- Webhooks: `task.move.column`, `task.create`
- Real-time triggering via HTTP POST
- Fallback: Polling mode (5-second intervals)

### 1.3 Integration Points

**Files with Kanboard API calls:**
- `orchestrator.py` (587 lines) - Main polling/single-run daemon
- `webhook_server.py` (597 lines) - Webhook listener
- `setup-board.py` (134 lines) - Board initialization
- `lib/task_fields.py` (315 lines) - Metadata abstraction
- `agents/architect.py` - DESIGN.md upload
- `agents/pm.py` - prd.json upload
- `agents/spawner.py` - Task duplication, linking
- `agents/governance.py` - Comments
- `agents/test_agent.py` - Metadata reading
- `agents/ralph.py` - Metadata reading

---

## 2. Required Features from Any Board

Based on the analysis, any kanban board system must provide:

### 2.1 Core Requirements (Must Have)

| Feature | Purpose | Current Kanboard Usage |
|---------|---------|------------------------|
| **Column-based workflow** | State machine for agents | 10 columns with WIP limits |
| **Task CRUD** | Create, read, update, delete tasks | All agents |
| **Custom metadata storage** | Store dirname, context_mode, etc. | MetaMagik API |
| **Tag/label system** | Idempotency tracking | 12+ tag types |
| **Task movement** | Trigger agents on column change | Webhook + polling |
| **Comments/notes** | Audit trail, error reporting | All agents |
| **File attachments** | DESIGN.md, prd.json storage | Architect, PM |
| **Task relationships** | Parent-child linking | Spawner fan-out |
| **Webhooks or polling** | Real-time triggers | Webhook preferred |

### 2.2 Advanced Requirements (Nice to Have)

| Feature | Purpose | Fallback if Unavailable |
|---------|---------|-------------------------|
| **WIP limits** | Enforce single-focus | Client-side enforcement |
| **Task duplication** | Spawner cloning | Manual copy with API |
| **Markdown in comments** | Formatted audit trail | Plain text acceptable |
| **Custom field schema** | Type validation | Client-side validation |

### 2.3 Minimal Feature Matrix

| Board System | Columns | Metadata | Tags | Comments | Files | Links | Webhooks | **Viable?** |
|--------------|---------|----------|------|----------|-------|-------|----------|-------------|
| **Kanboard** | ✅ | ✅ (MetaMagik) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ **Yes** |
| **GitHub Projects** | ✅ | ✅ (custom fields) | ✅ (labels) | ✅ | ✅ | ✅ (references) | ✅ | ✅ **Yes** |
| **Trello** | ✅ | ⚠️ (Power-Up, paid) | ✅ (labels) | ✅ | ✅ | ⚠️ (checklists) | ✅ | ⚠️ **Partial** |
| **Linear** | ✅ | ✅ (custom fields) | ✅ (labels) | ✅ | ❌ | ✅ (parent/child) | ✅ | ⚠️ **Partial*** |
| **Jira** | ✅ | ✅ (custom fields) | ✅ (labels) | ✅ | ✅ | ✅ (issue links) | ✅ | ✅ **Yes** |
| **Asana** | ✅ | ✅ (custom fields) | ✅ (tags) | ✅ | ✅ | ✅ (dependencies) | ✅ | ✅ **Yes** |

*Linear requires external file storage workaround (S3, GitHub)

---

## 3. Proposed Abstraction Design

### 3.1 Architecture Overview

Following the successful LLM provider pattern (Sprint 16-18):

```
lib/board/
├── __init__.py              # Public API exports
├── client.py                # BoardClient (like LLMClient)
├── config.py                # YAML config loader
├── protocol.py              # BoardProvider protocol
├── response.py              # BoardTask, BoardColumn, BoardFile dataclasses
├── trace.py                 # Board operation tracing (optional)
└── providers/
    ├── __init__.py
    ├── base.py              # Abstract base classes
    ├── registry.py          # Provider registration
    ├── kanboard.py          # Kanboard provider (refactored)
    ├── github.py            # GitHub Projects v2 provider
    ├── trello.py            # Trello API provider
    ├── linear.py            # Linear GraphQL provider
    └── jira.py              # Jira REST API v3 provider
```

### 3.2 Board Provider Protocol

```python
from typing import Protocol, Any
from dataclasses import dataclass

@dataclass
class BoardTask:
    """Unified task representation."""
    id: str
    title: str
    description: str
    column_id: str
    project_id: str
    metadata: dict[str, str]  # Custom fields
    tags: list[str]
    raw: dict[str, Any]  # Provider-specific data

@dataclass
class BoardColumn:
    """Column representation."""
    id: str
    name: str
    position: int
    wip_limit: int | None

@dataclass
class BoardFile:
    """File attachment representation."""
    id: str
    name: str
    size: int
    url: str | None

class BoardProvider(Protocol):
    """Interface all board providers must implement."""

    # Identity
    id: str
    type: str

    # Configuration
    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate provider configuration."""
        ...

    # Task Operations
    def get_task(self, task_id: str) -> BoardTask:
        """Fetch task by ID."""
        ...

    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        column_id: str | None = None,
    ) -> BoardTask:
        """Update task properties."""
        ...

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        ...

    def duplicate_task(
        self,
        task_id: str,
        project_id: str,
        **overrides
    ) -> BoardTask:
        """Clone a task with optional field overrides."""
        ...

    # Metadata Operations
    def get_metadata(self, task_id: str) -> dict[str, str]:
        """Get all custom metadata for a task."""
        ...

    def set_metadata(
        self,
        task_id: str,
        metadata: dict[str, str]
    ) -> bool:
        """Set custom metadata (replaces all)."""
        ...

    def update_metadata(
        self,
        task_id: str,
        updates: dict[str, str]
    ) -> bool:
        """Update specific metadata fields."""
        ...

    # Tag/Label Operations
    def get_tags(self, task_id: str) -> list[str]:
        """Get all tags for a task."""
        ...

    def set_tags(self, task_id: str, tags: list[str]) -> bool:
        """Set tags (replaces all)."""
        ...

    def add_tag(self, task_id: str, tag: str) -> bool:
        """Add a single tag."""
        ...

    def remove_tag(self, task_id: str, tag: str) -> bool:
        """Remove a single tag."""
        ...

    # Column/Workflow Operations
    def get_columns(self, project_id: str) -> list[BoardColumn]:
        """Get all columns in project."""
        ...

    def get_column_by_name(
        self,
        project_id: str,
        name: str
    ) -> BoardColumn | None:
        """Find column by name."""
        ...

    def move_task(
        self,
        task_id: str,
        column_id: str
    ) -> bool:
        """Move task to a column."""
        ...

    # Communication
    def add_comment(
        self,
        task_id: str,
        content: str,
        markdown: bool = True
    ) -> bool:
        """Post a comment on a task."""
        ...

    # File Attachments
    def get_files(self, task_id: str) -> list[BoardFile]:
        """List file attachments."""
        ...

    def upload_file(
        self,
        task_id: str,
        filename: str,
        content: bytes,
        mime_type: str | None = None
    ) -> BoardFile:
        """Upload a file attachment."""
        ...

    def delete_file(
        self,
        task_id: str,
        file_id: str
    ) -> bool:
        """Delete a file attachment."""
        ...

    # Task Relations
    def link_tasks(
        self,
        parent_id: str,
        child_id: str,
        relation: str = "relates_to"
    ) -> bool:
        """Create relationship between tasks."""
        ...

    def get_linked_tasks(
        self,
        task_id: str
    ) -> list[str]:
        """Get IDs of linked tasks."""
        ...

    # Webhooks (optional)
    def setup_webhook(
        self,
        url: str,
        events: list[str]
    ) -> str | None:
        """Set up webhook (returns webhook ID if supported)."""
        ...

    def parse_webhook_payload(
        self,
        payload: dict[str, Any]
    ) -> tuple[str, str]:
        """Parse webhook payload -> (event_name, task_id)."""
        ...
```

### 3.3 BoardClient (User-Facing API)

```python
class BoardClient:
    """Main client for board operations."""

    def __init__(self, config: BoardConfig, workspace: Path | None = None):
        """Initialize client with configuration."""
        self.config = config
        self.workspace = workspace
        self._provider = None

    @classmethod
    def from_config(
        cls,
        config_path: str | Path,
        workspace: Path | None = None
    ) -> "BoardClient":
        """Load client from YAML config."""
        config = load_config(config_path)
        return cls(config, workspace)

    @property
    def provider(self) -> BoardProvider:
        """Get configured provider."""
        if not self._provider:
            self._provider = get_provider(self.config.type)
            self._provider.validate_config(self.config.provider_config)
        return self._provider

    # Delegate all operations to provider
    def get_task(self, task_id: str) -> BoardTask:
        return self.provider.get_task(task_id)

    def get_metadata(self, task_id: str) -> dict[str, str]:
        return self.provider.get_metadata(task_id)

    # ... etc for all protocol methods
```

### 3.4 Configuration Format

```yaml
# config/board.yaml
board:
  # Active provider
  type: kanboard  # or "github", "trello", "linear", "jira"

  # Provider configurations
  providers:
    kanboard:
      url: "http://localhost:88/jsonrpc.php"
      user: "jsonrpc"
      token_env: "KANBOARD_TOKEN"
      project_id: "1"

    github:
      token_env: "GITHUB_TOKEN"
      owner: "leebase"
      repo: "agentleeops-board"
      project_number: 1

    trello:
      api_key_env: "TRELLO_API_KEY"
      token_env: "TRELLO_TOKEN"
      board_id: "abc123def456"

    linear:
      api_key_env: "LINEAR_API_KEY"
      team_id: "TEAM-123"
      # File storage workaround
      file_storage:
        type: "s3"
        bucket: "agentleeops-artifacts"
        region: "us-east-1"

    jira:
      url: "https://mycompany.atlassian.net"
      email: "bot@mycompany.com"
      token_env: "JIRA_API_TOKEN"
      project_key: "AGENTLEE"

  # Workflow column mapping (provider-independent)
  workflow:
    columns:
      - name: "Inbox"
        agent: null
        wip_limit: 0
      - name: "Design Draft"
        agent: "ARCHITECT"
        wip_limit: 1
      - name: "Design Approved"
        agent: "GOVERNANCE"
        wip_limit: 0
      - name: "Planning Draft"
        agent: "PM"
        wip_limit: 1
      - name: "Plan Approved"
        agent: "SPAWNER"
        wip_limit: 0
      - name: "Tests Draft"
        agent: "TEST"
        wip_limit: 1
      - name: "Tests Approved"
        agent: "GOVERNANCE"
        wip_limit: 0
      - name: "Ralph Loop"
        agent: "RALPH_CODER"
        wip_limit: 1
      - name: "Final Review"
        agent: null
        wip_limit: 0
      - name: "Done"
        agent: null
        wip_limit: 0
```

---

## 4. Provider Implementation Analysis

### 4.1 Kanboard Provider (Refactor Existing)

**Complexity:** ⭐⭐ (Medium - refactor, not greenfield)
**Effort:** 3 days

**Implementation:**
- Extract existing Kanboard logic from orchestrator/webhook into provider
- Implement BoardProvider protocol
- Migrate `lib/task_fields.py` metadata logic
- Keep MetaMagik dependency

**API Mapping:**
| Protocol Method | Kanboard API |
|----------------|--------------|
| `get_task()` | `get_task()` |
| `get_metadata()` | `execute("getTaskMetadata")` |
| `set_metadata()` | `execute("saveTaskMetadata")` |
| `get_tags()` | `get_task_tags()` |
| `set_tags()` | `set_task_tags()` |
| `add_comment()` | `create_comment()` |
| `upload_file()` | `create_task_file()` |
| `duplicate_task()` | `execute("duplicateTaskToProject")` |
| `link_tasks()` | `create_task_link()` |

**Advantages:**
- 100% feature coverage (no compromises)
- Proven stability
- MetaMagik provides robust custom fields
- Direct migration path

**Challenges:**
- MetaMagik plugin dependency (must be installed)
- JSON-RPC client abstraction
- Task duplication logic is complex

---

### 4.2 GitHub Projects Provider

**Complexity:** ⭐⭐⭐ (High - GraphQL, complex API)
**Effort:** 5 days

**Implementation:**
- GraphQL API for Projects v2
- Issues as tasks
- Project custom fields for metadata
- Labels for tags
- Issue comments for communication
- Issue attachments for files

**API Mapping:**
| Protocol Method | GitHub API |
|----------------|------------|
| `get_task()` | `query { issue(number: X) }` |
| `get_metadata()` | `query { issue { projectItems { fieldValues } } }` |
| `set_metadata()` | `mutation { updateProjectV2ItemFieldValue }` |
| `get_tags()` | `issue.labels` |
| `set_tags()` | `mutation { addLabelsToLabelable }` |
| `add_comment()` | `mutation { addComment }` |
| `upload_file()` | Issue attachment API |
| `duplicate_task()` | **Manual copy** (no native API) |
| `link_tasks()` | Issue references in body/comments |

**Advantages:**
- Free for public repos, generous for private
- Rich API with custom fields
- Native CI/CD integration potential
- Strong community support

**Challenges:**
- **GraphQL complexity** (steep learning curve)
- **Rate limiting** (5000 requests/hour)
- **No native task duplication** (must implement manually)
- Custom field schema must be pre-defined in project settings

**Workarounds:**
- Task duplication: Fetch source issue, create new with same data, link via reference
- Rate limiting: Implement request batching, caching

**Example Query:**
```graphql
query GetTask($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      title
      body
      projectItems(first: 1) {
        nodes {
          fieldValues(first: 10) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
        }
      }
      labels(first: 10) {
        nodes { name }
      }
    }
  }
}
```

---

### 4.3 Trello Provider

**Complexity:** ⭐⭐ (Medium - REST API, some limitations)
**Effort:** 4 days

**Implementation:**
- REST API
- Cards as tasks
- Lists as columns
- Custom Fields via Power-Ups (paid)
- Labels for tags
- Comments supported
- Attachments supported

**API Mapping:**
| Protocol Method | Trello API |
|----------------|------------|
| `get_task()` | `GET /cards/{id}` |
| `get_metadata()` | `GET /cards/{id}/customFieldItems` ⚠️ |
| `set_metadata()` | `PUT /cards/{id}/customFieldItem/{id}` ⚠️ |
| `get_tags()` | `GET /cards/{id}/labels` |
| `set_tags()` | `PUT /cards/{id}/idLabels` |
| `add_comment()` | `POST /cards/{id}/actions/comments` |
| `upload_file()` | `POST /cards/{id}/attachments` |
| `duplicate_task()` | `POST /cards/{id}/actions/copyCard` |
| `link_tasks()` | **Checklists workaround** |

⚠️ Requires Trello Power-Up (paid tier) for custom fields

**Advantages:**
- Simple REST API
- Mature, stable platform
- Good file attachment support
- Native card duplication

**Challenges:**
- **Custom fields require Power-Up** (paid, $5-10/user/month)
- **No native task linking** (use checklists or card links workaround)
- **Rate limiting** (300 requests/10 seconds per token)

**Workarounds:**
- If no Power-Up: Encode metadata as JSON in card description (like legacy Kanboard fallback)
- Task linking: Create checklist items with card URLs
- Rate limiting: Implement request queuing

---

### 4.4 Linear Provider

**Complexity:** ⭐⭐⭐ (High - GraphQL, file storage gap)
**Effort:** 4 days

**Implementation:**
- GraphQL API
- Issues as tasks
- Workflow states as columns
- Custom fields supported
- Labels for tags
- **No file attachments** (major gap)

**API Mapping:**
| Protocol Method | Linear API |
|----------------|------------|
| `get_task()` | `query { issue(id: X) }` |
| `get_metadata()` | `issue.customFields` |
| `set_metadata()` | `mutation { issueUpdate }` |
| `get_tags()` | `issue.labels` |
| `set_tags()` | `mutation { issueAddLabel }` |
| `add_comment()` | `mutation { commentCreate }` |
| `upload_file()` | ❌ **Not supported** |
| `duplicate_task()` | `mutation { issueCreate }` (manual copy) |
| `link_tasks()` | `issue.parent`, `issue.children` |

**Advantages:**
- Modern GraphQL API
- Native parent-child relationships
- Fast, responsive UI
- Good custom field support

**Challenges:**
- **NO FILE ATTACHMENTS** (blocking for current workflow)
- Must implement external file storage (S3, GitHub, etc.)
- GraphQL learning curve

**File Storage Workaround:**
```yaml
# In config/board.yaml for Linear
linear:
  api_key_env: "LINEAR_API_KEY"
  team_id: "TEAM-123"
  file_storage:
    type: "github"  # or "s3"
    owner: "leebase"
    repo: "agentleeops-artifacts"
    token_env: "GITHUB_TOKEN"
```

**Implementation:**
1. Upload DESIGN.md/prd.json to GitHub repo
2. Get file URL
3. Post comment on Linear issue with link
4. Store file metadata in custom field

---

### 4.5 Jira Provider

**Complexity:** ⭐⭐⭐⭐ (Very High - complex API, permissions)
**Effort:** 6 days

**Implementation:**
- REST API v3
- Issues as tasks
- Board columns for workflow
- Custom fields (complex typed system)
- Labels for tags
- Comments and attachments supported

**API Mapping:**
| Protocol Method | Jira API |
|----------------|------------|
| `get_task()` | `GET /issue/{issueIdOrKey}` |
| `get_metadata()` | `issue.fields.customfield_XXXXX` |
| `set_metadata()` | `PUT /issue/{issueIdOrKey}` |
| `get_tags()` | `issue.fields.labels` |
| `set_tags()` | `PUT /issue/{issueIdOrKey}` |
| `add_comment()` | `POST /issue/{issueIdOrKey}/comment` |
| `upload_file()` | `POST /issue/{issueIdOrKey}/attachments` |
| `duplicate_task()` | `POST /issue/{issueIdOrKey}/clone` |
| `link_tasks()` | `POST /issueLink` |

**Advantages:**
- Enterprise-grade
- Full feature coverage
- Excellent custom field support
- Native issue cloning and linking

**Challenges:**
- **API complexity** (typed custom fields, field IDs vary per instance)
- **Permission model** (complex role/project permissions)
- **Rate limiting** (varies by Cloud vs Server)
- **Workflow state machine** (transitions, validators, conditions)
- **Custom field discovery** (must query to get field IDs)

**Custom Field Challenge:**
```json
// Custom fields have instance-specific IDs
{
  "fields": {
    "customfield_10001": "my-project",     // dirname
    "customfield_10002": "NEW",            // context_mode
    "customfield_10003": "See description" // acceptance_criteria
  }
}
```

Must implement:
1. Field discovery: `GET /field` → map names to IDs
2. Field caching: Store mappings per Jira instance
3. Type handling: Text, select, number, etc.

---

### 4.6 Feature Comparison Matrix

| Feature | Kanboard | GitHub | Trello | Linear | Jira |
|---------|----------|--------|--------|--------|------|
| **Tasks** | ✅ | ✅ Issues | ✅ Cards | ✅ Issues | ✅ Issues |
| **Columns** | ✅ | ✅ Project views | ✅ Lists | ✅ States | ✅ Board columns |
| **Metadata** | ✅ MetaMagik | ✅ Custom fields | ⚠️ Power-Up | ✅ Custom fields | ✅ Custom fields |
| **Tags** | ✅ | ✅ Labels | ✅ Labels | ✅ Labels | ✅ Labels |
| **Comments** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Files** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Duplication** | ✅ Native | ⚠️ Manual | ✅ Native | ⚠️ Manual | ✅ Native |
| **Linking** | ✅ | ⚠️ References | ⚠️ Checklists | ✅ Parent/child | ✅ Issue links |
| **Webhooks** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **WIP Limits** | ✅ | ❌ | ❌ | ❌ | ⚠️ Plugin |
| **API Type** | JSON-RPC | GraphQL | REST | GraphQL | REST |
| **Rate Limits** | None | 5K/hour | 300/10s | Varies | Varies |
| **Free Tier** | ✅ Self-hosted | ✅ Public repos | ✅ 10 boards | ✅ Unlimited | ❌ Trial only |
| **Complexity** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 5. Development Effort Estimation

### 5.1 Core Abstraction (All Providers)

| Task | Effort | Description |
|------|--------|-------------|
| **Design & Prototyping** | 2 days | Protocol design, config format, dataclasses |
| **lib/board/ module** | 2 days | Client, config, response, registry |
| **Kanboard provider refactor** | 3 days | Extract existing logic into provider |
| **Orchestrator migration** | 5 days | Update orchestrator.py, webhook_server.py |
| **Agent updates** | 3 days | Update all 6 agents to use BoardClient |
| **Testing & validation** | 3 days | Unit tests, integration tests |
| **Documentation** | 2 days | API docs, migration guide |
| **TOTAL (Core)** | **20 days** | **~4 weeks (1 developer)** |

### 5.2 Additional Provider Implementation

| Provider | Effort | Complexity | Notes |
|----------|--------|------------|-------|
| **GitHub Projects** | 5 days | ⭐⭐⭐ | GraphQL, no native duplication |
| **Trello** | 4 days | ⭐⭐ | REST, Power-Up for metadata |
| **Linear** | 4 days | ⭐⭐⭐ | GraphQL, file storage workaround |
| **Jira** | 6 days | ⭐⭐⭐⭐ | Complex custom fields, permissions |

### 5.3 Timeline Scenarios

**Scenario 1: MVP (Kanboard abstraction only)**
- Effort: 20 days = **4 weeks**
- Deliverables: Core abstraction + Kanboard provider
- Benefits: Enables future providers, cleaner architecture
- Risk: No alternative board validated

**Scenario 2: MVP + GitHub (Recommended)**
- Effort: 20 + 5 = 25 days = **5 weeks**
- Deliverables: Core + Kanboard + GitHub
- Benefits: Proven multi-provider support, free alternative
- Risk: Moderate (GitHub GraphQL complexity)

**Scenario 3: Full Suite (4 providers)**
- Effort: 20 + 5 + 4 + 4 + 6 = 39 days = **8 weeks**
- Deliverables: Kanboard + GitHub + Trello + Linear + Jira
- Benefits: Maximum flexibility
- Risk: High (complex, long timeline)

### 5.4 Recommended Phasing

**Sprint 19: Core Abstraction (4 weeks)**
- Design board provider protocol
- Implement `lib/board/` module
- Refactor Kanboard into provider
- Update orchestrator and agents
- 100% test coverage

**Sprint 20: GitHub Provider (1 week)**
- Implement GitHub Projects provider
- Validate multi-provider switching
- Add doctor command: `python -m lib.board.doctor`
- Document GitHub setup

**Sprint 21+: Additional Providers (Optional)**
- Trello (1 week)
- Linear (1 week)
- Jira (1.5 weeks)
- Based on user demand

---

## 6. Migration Strategy

### 6.1 Phase 1: Create Abstraction (No Breaking Changes)

**Goals:**
- Create `lib/board/` module alongside existing code
- Implement Kanboard provider
- No changes to orchestrator yet

**Tasks:**
1. Create board provider protocol
2. Implement Kanboard provider (wraps existing API calls)
3. Add BoardClient wrapper
4. Create `config/board.yaml`
5. Add comprehensive tests

**Validation:**
- All tests pass
- Kanboard provider has 100% feature parity
- No orchestrator changes yet

### 6.2 Phase 2: Refactor Orchestrator (Breaking Changes)

**Goals:**
- Update orchestrator.py to use BoardClient
- Update webhook_server.py to use BoardClient
- Maintain backward compatibility where possible

**Tasks:**
1. Replace `kanboard.Client` with `BoardClient`
2. Update all `kb.get_task()` calls to `board.get_task()`
3. Update `lib/task_fields.py` to use board abstraction
4. Update all agents to use BoardClient

**Migration Path:**
```python
# Old (orchestrator.py)
from kanboard import Client
kb = Client(KB_URL, KB_USER, KB_TOKEN)
task = kb.get_task(task_id)

# New (orchestrator.py)
from lib.board import BoardClient
board = BoardClient.from_config("config/board.yaml")
task = board.get_task(task_id)
```

**Backward Compatibility:**
- Support legacy env vars (KANBOARD_URL, KANBOARD_TOKEN)
- Auto-migrate to board.yaml if not present
- Deprecation warnings for direct Kanboard usage

### 6.3 Phase 3: Add Second Provider (Validation)

**Goals:**
- Implement GitHub Projects provider
- Prove multi-provider switching works
- Document provider setup

**Tasks:**
1. Implement `lib/board/providers/github.py`
2. Add GitHub-specific tests
3. Create GitHub setup guide
4. Test orchestrator with GitHub
5. Document configuration switching

### 6.4 Phase 4: Additional Providers (Optional)

**Goals:**
- Add Trello, Linear, Jira based on demand
- Refine provider protocol based on learnings

**Tasks:**
- Implement additional providers
- Add provider-specific workarounds
- Update documentation
- Community contributions welcome

---

## 7. Risks & Challenges

### 7.1 High-Risk Items

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Orchestrator refactor introduces bugs** | High | Medium | Comprehensive testing, phased rollout, canary deployment |
| **Metadata portability issues** | High | High | Schema validation, migration scripts, clear documentation |
| **Provider API changes break system** | Medium | Low | Version pinning, API wrapper abstraction, monitoring |
| **File storage complexity (Linear)** | Medium | Medium | S3/GitHub fallback, clear error messages |
| **Task duplication logic fragile** | Medium | Medium | Provider-specific implementations, extensive testing |

### 7.2 Medium-Risk Items

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Rate limiting issues** | Medium | Medium | Request queuing, caching, retry logic |
| **Webhook setup complexity** | Low | High | Clear setup docs, automated webhook creation where possible |
| **Custom field schema differences** | Medium | High | Schema mapping layer, validation, defaults |
| **Testing complexity (real boards)** | Low | High | Mock APIs for unit tests, optional integration tests |

### 7.3 Technical Challenges

**1. Metadata Portability**
- **Problem:** Different boards have different custom field models
- **Example:** Jira uses typed fields (text, select, number), GitHub uses untyped fields
- **Solution:** Schema mapping layer in provider, validation on set_metadata()

**2. Task Duplication Variance**
- **Problem:** Kanboard/Trello/Jira have native duplication, GitHub/Linear don't
- **Solution:** Provider-specific implementations:
  - Kanboard: Use native API
  - GitHub: Fetch source, create new, link via reference
  - Linear: Create new issue, copy fields, set parent

**3. File Storage for Linear**
- **Problem:** Linear has no file attachments
- **Solution:** Pluggable file storage backend:
  ```yaml
  linear:
    file_storage:
      type: "github"  # or "s3", "local"
      # Provider-specific config
  ```

**4. Webhook Payload Diversity**
- **Problem:** Each board sends different webhook formats
- **Solution:** `parse_webhook_payload()` in provider converts to standard format:
  ```python
  def parse_webhook_payload(self, payload: dict) -> tuple[str, str]:
      """Returns (event_name, task_id)"""
      # Provider-specific parsing
      return ("task.move.column", "123")
  ```

### 7.4 Migration Risks

**Risk:** Breaking existing Kanboard workflows during refactor
**Mitigation:**
- Feature flag: `USE_BOARD_ABSTRACTION=true/false`
- Parallel testing: Run both old and new code paths
- Rollback plan: Keep old code until abstraction proven

**Risk:** Data loss during provider switching
**Mitigation:**
- Export/import tools for metadata
- Clear migration documentation
- Dry-run mode for testing migrations

---

## 8. Recommendations

### 8.1 Recommended Approach

**Option A: Full Abstraction (Recommended)**
- **Pros:** Maximum flexibility, future-proof, clean architecture
- **Cons:** 4-5 weeks initial development
- **Timeline:** Sprint 19-20 (5 weeks)
- **Deliverables:** Core abstraction + Kanboard + GitHub providers

**Why Recommended:**
1. **Future-proof:** Enables any board system
2. **Proven pattern:** Follows successful LLM abstraction (Sprint 16-18)
3. **Community demand:** Users want GitHub/Trello/Jira support
4. **Clean code:** Removes Kanboard coupling from core logic
5. **Testing:** Easier to test with mock providers

### 8.2 Alternative: Minimal Abstraction

**Option B: Kanboard Adapter Only**
- **Pros:** Faster (2 weeks), less risk
- **Cons:** Still coupled to Kanboard, no multi-provider support
- **Timeline:** Sprint 19 (2 weeks)
- **Deliverables:** Wrapper around Kanboard, no protocol

**Why Not Recommended:**
- Doesn't solve the core problem (Kanboard dependency)
- Would need full refactor later anyway
- Misses opportunity to align with LLM abstraction success

### 8.3 Implementation Plan

**Recommended Timeline:**

| Sprint | Duration | Deliverables | Effort |
|--------|----------|--------------|--------|
| **Sprint 19** | 4 weeks | Core abstraction + Kanboard provider + Orchestrator migration | 20 days |
| **Sprint 20** | 1 week | GitHub Projects provider + Validation | 5 days |
| **Sprint 21** | Optional | Trello provider | 4 days |
| **Sprint 22** | Optional | Linear provider (with file storage) | 4 days |
| **Sprint 23** | Optional | Jira provider | 6 days |

**Total MVP (Kanboard + GitHub):** 5 weeks
**Total Full Suite (5 providers):** 8 weeks

### 8.4 Success Criteria

**Phase 1 (Core Abstraction):**
- [ ] `lib/board/` module created with provider protocol
- [ ] Kanboard provider has 100% feature parity
- [ ] Orchestrator and all agents use BoardClient
- [ ] All 257 existing tests pass
- [ ] 50+ new board abstraction tests pass
- [ ] Doctor command validates configuration

**Phase 2 (Multi-Provider):**
- [ ] GitHub provider implements full protocol
- [ ] Can switch between Kanboard and GitHub via config
- [ ] End-to-end workflow test on both providers
- [ ] Migration documentation complete
- [ ] Setup guides for each provider

### 8.5 Key Decision Points

**Decision 1: Proceed with full abstraction?**
- **Recommended:** Yes
- **Rationale:** Aligns with LLM abstraction success, future-proof, clean architecture
- **Alternative:** Defer to future sprint if bandwidth limited

**Decision 2: Which providers to prioritize?**
- **Recommended:** Kanboard (refactor) + GitHub (validation)
- **Rationale:** GitHub is free, popular, validates abstraction works
- **Alternatives:** Add Trello/Jira based on user requests

**Decision 3: Break orchestrator in one sprint or gradual migration?**
- **Recommended:** One sprint (controlled break)
- **Rationale:** Faster, cleaner, less technical debt
- **Alternative:** Gradual with feature flags (safer but slower)

---

## Appendix A: API Examples

### GitHub Projects Provider Example

```python
# lib/board/providers/github.py
class GitHubProjectsProvider(BoardProvider):
    def __init__(self, config: dict):
        self.token = os.getenv(config["token_env"])
        self.owner = config["owner"]
        self.repo = config["repo"]
        self.project_number = config["project_number"]
        self.graphql_url = "https://api.github.com/graphql"

    def get_task(self, task_id: str) -> BoardTask:
        query = """
        query GetIssue($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
              title
              body
              projectItems(first: 1) {
                nodes {
                  fieldValues(first: 20) {
                    nodes {
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field { ... on ProjectV2FieldCommon { name } }
                      }
                    }
                  }
                }
              }
              labels(first: 20) { nodes { name } }
            }
          }
        }
        """
        response = self._graphql(query, {
            "owner": self.owner,
            "repo": self.repo,
            "number": int(task_id)
        })

        issue = response["data"]["repository"]["issue"]
        return BoardTask(
            id=task_id,
            title=issue["title"],
            description=issue["body"],
            column_id=self._extract_column_id(issue),
            project_id=str(self.project_number),
            metadata=self._extract_metadata(issue),
            tags=[label["name"] for label in issue["labels"]["nodes"]],
            raw=issue
        )

    def _graphql(self, query: str, variables: dict) -> dict:
        """Execute GraphQL query."""
        response = requests.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        return response.json()
```

### Trello Provider Example

```python
# lib/board/providers/trello.py
class TrelloProvider(BoardProvider):
    def __init__(self, config: dict):
        self.api_key = os.getenv(config["api_key_env"])
        self.token = os.getenv(config["token_env"])
        self.board_id = config["board_id"]
        self.base_url = "https://api.trello.com/1"

    def get_task(self, task_id: str) -> BoardTask:
        url = f"{self.base_url}/cards/{task_id}"
        response = requests.get(url, params=self._auth_params())
        response.raise_for_status()
        card = response.json()

        return BoardTask(
            id=card["id"],
            title=card["name"],
            description=card["desc"],
            column_id=card["idList"],
            project_id=self.board_id,
            metadata=self._get_custom_fields(task_id),
            tags=[label["name"] for label in card["labels"]],
            raw=card
        )

    def _auth_params(self) -> dict:
        """Get authentication parameters."""
        return {
            "key": self.api_key,
            "token": self.token
        }

    def _get_custom_fields(self, card_id: str) -> dict:
        """Get custom field values (requires Power-Up)."""
        url = f"{self.base_url}/cards/{card_id}/customFieldItems"
        response = requests.get(url, params=self._auth_params())

        if response.status_code == 404:
            # Power-Up not enabled, fallback to description parsing
            return self._parse_metadata_from_description(card_id)

        response.raise_for_status()
        items = response.json()

        # Convert to dict
        metadata = {}
        for item in items:
            field_name = self._get_field_name(item["idCustomField"])
            metadata[field_name] = item["value"]["text"]

        return metadata
```

---

## Appendix B: Configuration Migration

### Legacy (Current)

```bash
# .env
KANBOARD_URL=http://localhost:88/jsonrpc.php
KANBOARD_USER=jsonrpc
KANBOARD_TOKEN=abc123def456
```

### New (Abstraction)

```yaml
# config/board.yaml
board:
  type: kanboard

  providers:
    kanboard:
      url: "http://localhost:88/jsonrpc.php"
      user: "jsonrpc"
      token_env: "KANBOARD_TOKEN"
      project_id: "1"
```

### Auto-Migration Script

```python
# tools/migrate-board-config.py
#!/usr/bin/env python3
"""Migrate legacy Kanboard env vars to board.yaml"""

import os
import yaml
from pathlib import Path

def migrate():
    # Read legacy env vars
    url = os.getenv("KANBOARD_URL", "http://localhost:88/jsonrpc.php")
    user = os.getenv("KANBOARD_USER", "jsonrpc")

    # Create new config
    config = {
        "board": {
            "type": "kanboard",
            "providers": {
                "kanboard": {
                    "url": url,
                    "user": user,
                    "token_env": "KANBOARD_TOKEN",
                    "project_id": "1"  # Default
                }
            }
        }
    }

    # Write to config/board.yaml
    config_path = Path("config/board.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Migrated to {config_path}")
    print("⚠️  Update KANBOARD_TOKEN in .env if needed")

if __name__ == "__main__":
    migrate()
```

---

## Conclusion

The multi-kanban board abstraction is **feasible and recommended** using the proven LLM provider pattern. The estimated development effort is **4-5 weeks for core + GitHub**, with additional providers taking 1 week each.

**Key Takeaways:**
1. ✅ **Viable:** All major boards support required features
2. ✅ **Proven Pattern:** Follow LLM abstraction (Sprint 16-18)
3. ✅ **Phased Rollout:** Start with Kanboard refactor, add GitHub, then others
4. ⚠️ **Effort:** Moderate (4-8 weeks depending on provider count)
5. ⚠️ **Risk:** Orchestrator refactor is invasive but manageable

**Recommendation:** Proceed with Sprint 19 (core abstraction) using the phased approach outlined in Section 6 (Migration Strategy).
