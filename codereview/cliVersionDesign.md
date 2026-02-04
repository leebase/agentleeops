Below is a repo-grounded, no-code architecture + interface proposal for evolving AgentLeeOps into a skill-first system that external agent frameworks can invoke locally with file‑backed state. I’ve strictly grounded the “current state” sections in the repository artifacts and kept all new design work conceptual.
1) Grounding in the current repo (source‑of‑truth summary)
What AgentLeeOps currently does
Purpose & workflow: AgentLeeOps is an orchestration framework that enforces a 10‑stage Kanboard workflow (Inbox → Design Draft → Design Approved → Planning Draft → Plan Approved → Tests Draft → Tests Approved → Ralph Loop → Final Review → Done). It emphasizes artifact-driven decisions, resumability, and test integrity, with explicit ownership per stage (Architect, PM, Test, Ralph, Governance, human review).
Core agents & artifacts: The pipeline produces and governs key artifacts such as DESIGN.md, prd.json, tests in tests/, and implementation in src/, with explicit locks and approvals at gating steps.
Safety controls: Ratchet governance (hash‑locked artifacts), double‑blind rule (tests by a different agent than coder), and test integrity constraints are foundational to the system’s core philosophy and safety posture.
What Sprint 18 accomplished (decoupling/abstraction & cleanup)
LLM abstraction cleanup and tooling: Sprint 18 delivered cleanup and optimization of the LLM system, including removal of legacy lib/opencode.py, JSON repair monitoring, prompt compression, provider health checks, and profiling (with tests).
Decoupling direction away from Kanboard: The Work Item Provider Architecture explicitly shifts from “board‑centric” thinking to work‑item‑centric abstractions (work item IDs, state transitions, metadata, commentary), positioning Kanboard as a reference implementation rather than the product’s core identity. This is the architectural basis for local-first, file‑backed “skill” interfaces.
Invariants that must remain true
These are mandated by the repo’s safety posture and product definition:
Ratchet governance: Once DESIGN.md or tests are approved, they cannot be modified by agents. Ratchet enforcement is workspace‑based and independent of boards.
Approvals / human‑in‑the‑loop gating: Human approvals mark transitions into gated states (Design Approved, Plan Approved, Tests Approved, Final Review).
Test immutability / double‑blind rule: Tests are authored in a separate stage and locked before the coder loop; Ralph must not edit tests and must pass hash checks before coding/commit.
Traceability / audit trail: Actions and outcomes are recorded via comments and traces, with raw provider output in trace files and JSON repair audit metadata for observability.
Idempotency / replay safety: Idempotency is tracked using tags/markers (e.g., design-generated, tests-generated, coding-complete) to prevent repeated actions on the same work item state.
Safe failure behavior: Flood control (fan‑out limits) and LLM syntax guards prevent runaway actions or unsafe outputs (invalid JSON/Python).
2) Define “Agent Skill” as the primary interface
Skill interface principles (MVP)
JSON-in / JSON-out for every tool.
Local‑first: no daemon required; state is persisted to disk.
File‑backed state: “work items” live in repo/workspace documents, not a Kanban board.
Transport‑agnostic: same tool schemas are callable via CLI wrapper, future MCP server, and internal Python entrypoints.
Toolset: Agent Skill Tool Table (MVP)
Each tool maps to existing stages and artifacts in the 10‑step workflow, but in document‑backed state.
Notation: Schemas are shown as JSON Schema‑like objects for clarity.
Tool	Purpose	Required Inputs (schema)	Outputs (schema)	Failure modes	Stage
init_workspace	Initialize local state and directories for a new work item (or workspace).	{ "workspace_root": "string", "work_item_id": "string", "idempotency_key": "string" }	{ "workspace_root": "string", "state_path": "string", "status": "ok" }	state_exists, lock_held, invalid_workspace	Inbox
create_story	Create a file‑backed work item with metadata and initial state.	`{ "work_item": { "id": "string", "title": "string", "context_mode": "NEW	FEATURE", "dirname": "string", "acceptance_criteria": ["string"] }, "idempotency_key": "string" }`	{ "state_path": "string", "work_item_id": "string", "status": "ok" }	invalid_metadata, duplicate_id, lock_held
generate_design	Produce DESIGN.md draft artifact for a work item.	{ "work_item_id": "string", "inputs": { "constraints": "string", "references": ["string"] }, "idempotency_key": "string" }	{ "artifact_path": "string", "status": "ok" }	ratchet_locked, invalid_state, missing_context	Design Draft
approve_artifact	Human gate: approve a specific artifact and ratchet-lock it.	`{ "work_item_id": "string", "artifact": "DESIGN	PLAN	TESTS", "approver": "string", "timestamp": "string" }`	{ "status": "ok", "ratchet_updated": true }
generate_plan	Generate prd.json with atomic stories.	{ "work_item_id": "string", "idempotency_key": "string" }	{ "artifact_path": "string", "status": "ok" }	ratchet_locked, invalid_state, missing_design	Planning Draft
fanout_atomic_stories	Create child story state documents from approved plan.	{ "work_item_id": "string", "fanout_limit": "number", "idempotency_key": "string" }	{ "child_ids": ["string"], "status": "ok" }	fanout_limit_exceeded, invalid_state, missing_plan	Plan Approved
generate_tests	Create tests/*.py for a story.	{ "work_item_id": "string", "idempotency_key": "string" }	{ "artifact_paths": ["string"], "status": "ok" }	ratchet_locked, invalid_state, missing_plan	Tests Draft
run_governance_check	Enforce ratchet, hash verification, test immutability.	{ "work_item_id": "string" }	{ "status": "ok", "violations": [] }	ratchet_violation, hash_mismatch	Governance
run_coder_loop	Execute Ralph loop against locked tests.	{ "work_item_id": "string", "idempotency_key": "string" }	{ "status": "ok", "tests_passed": true }	tests_modified, invalid_state, ratchet_locked	Ralph Loop
run_review_bundle	Generate review bundle (diffs, artifacts summary).	{ "work_item_id": "string" }	{ "bundle_path": "string", "status": "ok" }	missing_artifacts, invalid_state	Final Review
get_state	Fetch current state document.	{ "work_item_id": "string" }	{ "state": { ... } }	not_found	Any
list_artifacts	List artifacts for a work item.	{ "work_item_id": "string" }	{ "artifacts": [{ "type": "string", "path": "string" }] }	not_found	Any
get_trace_summary	Summarize traces, repairs, and profile data.	{ "work_item_id": "string" }	{ "trace_paths": ["string"], "summary": "string" }	not_found, trace_missing	Any
Grounding: These stages directly mirror the 10‑step workflow and artifact rules defined in the repo (Design/Plan/Tests approvals, Ralph loop constraints).
3) State‑as‑documents spec (MVP)
Canonical state model (hybrid)
Canonical machine state: state.yaml (authoritative).
Human-readable view: state.md (generated; read‑only).
Append‑only audit log: events.jsonl (immutable log).
Locks: state.lock file for concurrency.
Ratchet: .agentleeops/ratchet.json governs artifact immutability as already defined in the system.
Suggested directory structure
.agentleeops/
  work-items/
    WI-2026-001/
      state.yaml
      state.md
      events.jsonl
      state.lock
      artifacts/
        DESIGN.md
        prd.json
        tests/
  traces/
  profiles/
Grounding: traces and profiling are already written into .agentleeops/traces/ and .agentleeops/profiles/ in the current system, so the state layout should preserve this pattern for continuity and auditability.
State fields (schema outline)
work_item:
  id: "WI-2026-001"
  title: "Short title"
  context_mode: "NEW|FEATURE"
  dirname: "repo-name"
  acceptance_criteria:
    - "..."
metadata:
  owner: "human or system"
  created_at: "2026-02-01T12:00:00Z"
  updated_at: "2026-02-01T12:45:00Z"
state:
  current_stage: "design_draft|design_approved|planning_draft|plan_approved|tests_draft|tests_approved|implementation|final_review|done"
  approvals:
    - artifact: "DESIGN"
      approved_by: "lee"
      approved_at: "2026-02-01T12:30:00Z"
  idempotency:
    keys:
      - "design-generated:sha256(...)"  # from tags/markers
  locks:
    held_by: "agent_id"
    expires_at: "2026-02-01T12:50:00Z"
artifacts:
  design: ".agentleeops/work-items/WI-2026-001/artifacts/DESIGN.md"
  plan: ".agentleeops/work-items/WI-2026-001/artifacts/prd.json"
  tests: ".agentleeops/work-items/WI-2026-001/artifacts/tests/"
traces:
  - ".agentleeops/traces/WI-2026-001/trace-001.json"
audit:
  events_path: ".agentleeops/work-items/WI-2026-001/events.jsonl"
Example state.yaml (short but real)
work_item:
  id: "WI-2026-001"
  title: "Add CSV import"
  context_mode: "FEATURE"
  dirname: "agentleeops"
  acceptance_criteria:
    - "CSV import accepts header row"
    - "Import rejects invalid UTF-8"

state:
  current_stage: "tests_approved"
  approvals:
    - artifact: "DESIGN"
      approved_by: "lee"
      approved_at: "2026-02-01T12:20:00Z"
    - artifact: "TESTS"
      approved_by: "lee"
      approved_at: "2026-02-01T12:40:00Z"
  idempotency:
    keys:
      - "design-generated"
      - "tests-generated"
  locks:
    held_by: "governance_agent"
    expires_at: "2026-02-01T12:45:00Z"

artifacts:
  design: ".agentleeops/work-items/WI-2026-001/artifacts/DESIGN.md"
  plan: ".agentleeops/work-items/WI-2026-001/artifacts/prd.json"
  tests: ".agentleeops/work-items/WI-2026-001/artifacts/tests/"

audit:
  events_path: ".agentleeops/work-items/WI-2026-001/events.jsonl"
Grounding: The idempotency markers align with existing tag conventions used in the Kanboard model (e.g., design-generated, tests-generated, coding-complete), preserving replay safety in the file‑backed model.
4) Skill‑first integration model (OpenCode, Claude Code, Gemini CLI, Codex CLI)
Common handoff contract
External agent provides: work_item_id, user prompt context, and idempotency key.
AgentLeeOps skill returns: artifact paths, updated state.yaml, and errors (if any).
External agent does NOT orchestrate workflow state. It simply calls tools.
OpenCode
Call path: CLI wrapper agentleeops skill <tool> --json.
Handoff: OpenCode invokes generate_design, generate_tests, run_coder_loop with JSON payload.
Division of responsibility: OpenCode handles LLM output; AgentLeeOps handles governance/ratchet & state transitions.
Grounding: OpenCode is already a supported provider in the LLM abstraction and referenced in system capabilities.
Claude Code
Call path: Tool calling or shell wrapper; JSON in/out.
Handoff contract: pass work_item_id, idempotency_key, and local path hints (workspace root).
AgentLeeOps role: enforce ratchet, approve artifacts, track state transitions, produce traces.
Gemini CLI
Call path: CLI wrapper or tool calling.
Handoff: generate_plan, generate_tests with output routed into artifact files.
Grounding: Gemini CLI is part of the LLM provider abstraction in Sprint 17/18 scope.
Codex CLI
Call path: CLI wrapper or tool calling; JSON output.
Handoff: run_coder_loop + run_governance_check before writing.
AgentLeeOps role: enforce test immutability + ratchet (hash checks) before committing.
5) MCP as a SECOND step (not first)
MCP mapping (post‑MVP)
MCP tool list: identical to the skill tools above (init_workspace, create_story, generate_design, etc.).
MCP concerns:
File access permissions: need explicit workspace roots.
Streaming & trace size: trace outputs should be written to disk with summary returned.
Identity/role: MCP caller identity should be included in approvals for auditability.
Why MCP after tool schemas stabilize
Skill-first ensures schemas and file layouts are tested locally first.
MCP can then map 1:1 to those same tools without semantic drift.
6) Roadmap (3–5 phases)
Skill Interface MVP (CLI wrapper + file‑backed state)
Implement tool JSON schemas.
Create state.yaml/events.jsonl layouts.
Preserve ratchet, test immutability, approvals.
Reliability & Guardrails
Locks, idempotency keys, retries.
Validate transitions strictly vs. current stage.
MCP Server Wrapper
Expose existing tools via MCP.
Add permission checks and trace streaming.
Optional HTTP Service (FastAPI)
For enterprise integration and multi‑client orchestration.
Optional Multi‑User/Hosted
Auth, RBAC approvals, centralized audit.
Commands run (for traceability)
ls (repo root discovery).
find .. -name AGENTS.md -print (agent instructions).
rg -n "Sprint 18" -S . (locate Sprint 18 docs).
sed -n ... README.md / nl -ba README.md (workflow + capabilities).
sed -n ... product-definition.md / nl -ba product-definition.md (governance & safety).
sed -n ... WorkItemAbstraction.md / nl -ba WorkItemAbstraction.md (work item abstraction).
sed -n ... MultiKanban.md / nl -ba MultiKanban.md (idempotency + audit).
sed -n ... sprintPlan.md / nl -ba sprintPlan.md (Sprint 18 specifics).
Testing
Not run (design‑only request).
