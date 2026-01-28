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

---

## Phase 4: LLM Provider Abstraction (Planned)

**Branch:** `feat/llm-provider-abstraction`
**Detailed Plan:** See `llm-redesign-sprint-plan.md`

### Sprint 16: Core Abstraction + OpenRouter (Phase A)
**Priority:** P1
**Status:** complete

Pluggable LLM provider system with role-based routing.

**Deliverables:**
- [x] `lib/llm/` module with client, config, response, trace
- [x] OpenRouter HTTP provider
- [x] Role definitions: planner, coder, reviewer, summarizer
- [x] PM Agent converted as proof of concept
- [x] Basic trace recording
- [x] 31 new tests (all passing)
- [x] Integration test with real OpenRouter API successful

### Sprint 17: CLI Providers + Full Rollout (Phase B)
**Priority:** P1
**Status:** complete ✅

**Deliverables:**
- [x] OpenCode CLI provider (`lib/llm/providers/opencode_cli.py`)
- [x] JSON repair for CLI output (`lib/llm/json_repair.py`)
  - Multi-strategy repair: markdown extraction, trailing commas, unquoted keys, single quotes
  - 28 comprehensive tests
- [x] All agents converted to use LLMClient
  - Architect: `planner` role for DESIGN.md
  - Test Agent: `planner` role (tests are specs per Double-Blind Rule)
  - Ralph: `coder` role with all integrity guards maintained
- [x] Doctor command for configuration validation (`python -m lib.llm.doctor`)
- [x] Documentation updated (CLAUDE.md, README.md)
- [x] 17 new CLI provider tests (all passing)
- [x] Total test count: 135+ tests passing

**Post-Review Fixes (completed 2026-01-27):**
- [x] **Lazy Provider Validation** - Config loads even with missing API keys; validation happens on first use
- [x] **Dynamic Log Field Extraction** - All LLM context fields (event, role, provider, model, etc.) now appear in logs
- [x] **JSON Repair Metadata** - Full audit trail: `json_repair_applied` and `json_repair_method` in responses, logs, and traces
- [x] **Large Prompt Handling** - CLI providers use stdin for prompts >100KB to avoid argv limits
- [x] **Raw Output in Traces** - Trace files include original provider output before repair
- [x] 11 new comprehensive tests (177/177 passing)
- [x] Documentation: `codereview/fixes-sprint17.md`

**Deferred:**
- [ ] Gemini CLI provider (future, optional)

### Sprint 18: Cleanup & Optimization
**Priority:** P2
**Status:** complete ✅

Post-Sprint 17 cleanup and performance improvements.

**Deliverables:**
- [x] Remove legacy `lib/opencode.py` module (deprecated) - Removed in Sprint 18, all agents using `lib/llm/`
- [x] Add monitoring dashboard for JSON repair patterns - Completed with `tools/repair-monitor.py` CLI tool
  - Analyzes trace files for repair statistics
  - Tracks patterns by provider, role, and model
  - Shows provider performance metrics (latency, success rate, cost)
  - Provides actionable recommendations
  - 9 comprehensive tests added (186/186 passing)
- [x] Prompt compression for very large inputs - Completed with `lib/llm/compression.py`
  - Multiple compression strategies: "smart", "whitespace", "aggressive", "extract"
  - Whitespace normalization, comment removal, string truncation, JSON minification
  - Key section extraction for very large inputs (>50KB)
  - Auto-compression for messages >10KB threshold
  - Token savings estimation (~4 chars = 1 token)
  - Integrated into LLMClient.complete() with compress parameter
  - 27 comprehensive tests added (213/213 passing)
- [x] Provider health checks - Completed with `lib/llm/health.py`
  - Real connectivity tests with minimal LLM requests
  - Latency measurement for each provider
  - Check all providers or specific ones
  - JSON and human-readable output formats
  - CLI: `python -m lib.llm.health [--provider NAME] [--json]`
  - Exit codes for CI/CD integration (0=healthy, 1=unhealthy)
  - 16 comprehensive tests added (229/229 passing)
- [x] Performance profiling of agent loops - Completed with `lib/profiler.py` and `tools/profile-report.py`
  - Profiler class with context managers and decorators
  - Measures execution time for agent operations
  - Tracks nested operations (LLM calls, file I/O, git operations)
  - ProfileEntry dataclass with parent-child hierarchy
  - Statistics generation (count, total, avg, min, max duration)
  - Profile serialization to JSON
  - CLI tool: `python tools/profile-report.py [--latest|--all] [--json]`
  - Execution tree visualization with hierarchical timing
  - Aggregation across multiple runs
  - Profiles stored in `.agentleeops/profiles/`
  - 28 comprehensive tests added (257/257 passing)
