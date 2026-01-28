# LLM Provider Abstraction - Sprint Plan

**Status:** COMPLETE ✅ (Sprint 16-18, completed 2026-01-28)

**Note:** This was the original sprint plan. Implementation completed in Sprint 16-17 with post-review fixes. Sprint 18 added cleanup, monitoring, health checks, compression, and profiling. Legacy `lib/opencode.py` fully removed in Sprint 18.

## Overview

Refactor AgentLeeOps to support pluggable LLM providers with role-based routing. Based on PR spec in `codereview/plugin-pr.md`.

**Branch:** `feat/llm-provider-abstraction`

**Drivers:** Model flexibility, cost control, future-proofing

**Approach:** Phased (2 PRs)

---

## Phase A: Core Abstraction + OpenRouter

**Goal:** Prove the abstraction works with a production-quality API provider.

### Deliverables

1. **Module Structure**
   ```
   lib/llm/
   ├── __init__.py
   ├── client.py          # LLMClient class
   ├── config.py          # YAML config loader
   ├── response.py        # LLMResponse dataclass
   ├── trace.py           # Trace recording
   └── providers/
       ├── __init__.py
       ├── base.py        # Provider protocol
       ├── registry.py    # Provider registration
       └── openrouter.py  # OpenRouter HTTP provider
   ```

2. **Configuration**
   - `config/llm.yaml` - Role routing configuration
   - `.env` additions for `OPENROUTER_API_KEY`

3. **Roles Defined** (all 4, even if not all used yet)
   - `planner` - Design, planning, test generation
   - `coder` - Implementation (Ralph)
   - `reviewer` - Code review / critique
   - `summarizer` - PR summaries, release notes

4. **One Agent Converted** - PM Agent as proof of concept

5. **Basic Trace Recording** - `.agentleeops/traces/`

### Acceptance Criteria (Phase A)

- [x] `LLMClient.complete(role="planner", messages=[...])` routes to OpenRouter
- [x] PM Agent uses new abstraction (no direct OpenRouter/OpenCode calls)
- [x] Trace file written for each LLM call
- [x] Missing API key produces clear error message
- [x] Existing tests still pass

---

## Phase B: CLI Providers + Full Rollout

**Goal:** Add CLI-based providers and convert all agents.

### Deliverables

1. **CLI Providers**
   ```
   lib/llm/providers/
   ├── opencode_cli.py    # OpenCode CLI wrapper
   └── gemini_cli.py      # Gemini CLI wrapper
   ```

2. **JSON Repair** (mandatory, not optional)
   - `lib/llm/repair.py` - Attempt to fix malformed JSON from CLI providers

3. **Agent Conversions**
   - Architect Agent → uses `planner` role
   - Test Agent → uses `planner` role
   - Ralph → uses `coder` role

4. **Doctor Command**
   - `python -m agentleeops.llm.doctor --config config/llm.yaml`
   - Validates providers, env vars, CLI availability

5. **Fallback Configuration** (stretch)
   - Optional fallback provider per role if primary fails

6. **Documentation**
   - `docs/llm-providers.md`

### Acceptance Criteria (Phase B)

- [x] All 3 providers working (OpenRouter, OpenCode CLI, Gemini CLI)
- [x] All agents use `LLMClient` (no direct provider calls)
- [x] `doctor` command validates configuration
- [x] JSON repair handles common CLI output issues
- [x] Full test coverage for new modules (177 tests after Sprint 17)

---

## Sprint 18: Cleanup & Optimization

**Goal:** Polish the LLM system with monitoring, health checks, and performance tools.

### Deliverables

1. **Remove Legacy Code**
   - Delete `lib/opencode.py` (fully deprecated)

2. **JSON Repair Monitoring**
   - `lib/llm/monitor.py` - Analyze trace files for repair patterns
   - `tools/repair-monitor.py` - CLI tool for repair statistics
   - Track repair rates, methods, provider performance

3. **Prompt Compression**
   - `lib/llm/compression.py` - Compress large prompts
   - Multiple strategies: smart, whitespace, aggressive, extract
   - Auto-compression for messages >10KB
   - Token savings estimation

4. **Provider Health Checks**
   - `lib/llm/health.py` - Real connectivity tests
   - Measure latency for each provider
   - CLI: `python -m lib.llm.health`
   - Exit codes for CI/CD integration

5. **Performance Profiling**
   - `lib/profiler.py` - Profile agent execution
   - `tools/profile-report.py` - Analyze profiles
   - Track operation timing, nested calls
   - Execution tree visualization

### Acceptance Criteria (Sprint 18)

- [x] Legacy `lib/opencode.py` removed
- [x] JSON repair monitoring with CLI tool
- [x] Prompt compression with multiple strategies
- [x] Provider health checks with latency measurement
- [x] Performance profiling system
- [x] All 257 tests passing

---

## Role Mapping

| Current Agent | LLM Role | Notes |
|---------------|----------|-------|
| Architect | `planner` | Generates DESIGN.md |
| PM | `planner` | Generates prd.json |
| Test Agent | `planner` | Generates test files |
| Ralph | `coder` | TDD implementation loop |
| Governance | N/A | No LLM calls |
| Spawner | N/A | No LLM calls |

---

## Configuration Example

```yaml
llm:
  default_role: planner

  providers:
    openrouter:
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      timeout_s: 120

    opencode_plus:
      type: opencode_cli
      command: "opencode"
      timeout_s: 120

    gemini_cli:
      type: gemini_cli
      command: "gemini"
      timeout_s: 120

  roles:
    planner:
      provider: openrouter
      model: "anthropic/claude-sonnet-4"
      temperature: 0.2
      max_tokens: 4000
      json_mode: true

    coder:
      provider: openrouter
      model: "anthropic/claude-sonnet-4"
      temperature: 0.1
      max_tokens: 8000

    reviewer:
      provider: opencode_plus
      temperature: 0.2

    summarizer:
      provider: openrouter
      model: "anthropic/claude-haiku"
      temperature: 0.3
      max_tokens: 2000
```

---

## Files to Create

### Phase A
- `lib/llm/__init__.py`
- `lib/llm/client.py`
- `lib/llm/config.py`
- `lib/llm/response.py`
- `lib/llm/trace.py`
- `lib/llm/providers/__init__.py`
- `lib/llm/providers/base.py`
- `lib/llm/providers/registry.py`
- `lib/llm/providers/openrouter.py`
- `config/llm.yaml`
- `tests/test_llm_client.py`
- `tests/test_llm_config.py`
- `tests/test_openrouter_provider.py`

### Phase B
- `lib/llm/providers/opencode_cli.py`
- `lib/llm/providers/gemini_cli.py`
- `lib/llm/repair.py`
- `lib/llm/doctor.py`
- `docs/llm-providers.md`
- `tests/test_cli_providers.py`

---

## Migration Strategy

1. **Phase A:** New code is additive - doesn't break existing agents
2. **Phase A proof:** PM Agent converted, others unchanged
3. **Phase B:** Convert remaining agents one at a time
4. **Deprecate:** Remove `lib/opencode.py` after all agents migrated

---

## Design Decisions

1. **Fallback behavior:** Fail fast with clear error. No automatic fallback to backup providers. Human intervention preferred over silent degradation.

2. **Cost tracking:** Yes - log estimated cost per call in traces. OpenRouter provides token counts and pricing info. Include in `LLMResponse.usage` dict.

3. **Rate limiting:** Defer. Let providers handle their own rate limiting for now.

---

## Next Steps

1. Create git branch: `feat/llm-provider-abstraction` ✓
2. Create `llm-redesign-sprint-plan.md` in project root ✓
3. Update `sprintPlan.md` to add Phase 4 reference
4. Begin Phase A implementation
