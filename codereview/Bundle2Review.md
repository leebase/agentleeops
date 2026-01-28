## Bundle 2 — Observability + Config/Deployability + Docs (Codex Review Brief)

### Mission
Review AgentLeeOps post–Sprint 18 for **(1) operational observability**, **(2) configuration + deployability**, and **(3) documentation quality** sufficient for a new user (or future you) to run it end-to-end without tribal knowledge.

This is **not** a deep security review and not a performance micro-optimization review. It’s: *Can we operate this thing, debug it, and onboard someone to it?*

---

## 1) Scope

### In-scope
- **Logging**
  - JSON logging output format and completeness
  - correlation IDs / request IDs
  - log levels and error logging
- **Tracing**
  - trace file contents, naming, lifecycle, retention implications
  - “raw output” inclusion, repair metadata, provider metadata
- **Monitoring tools**
  - repair/monitor dashboards
  - profiling reports (only as an ops artifact)
  - health check utilities
- **Config**
  - `config/llm.yaml` (and any other config)
  - `.env` usage / `.env.example`
  - doctor command + health checks (operator UX)
- **Deployability**
  - local dev setup
  - Docker assumptions (if any)
  - runtime assumptions (kanboard URL, plugins)
  - “single runner vs multiple runner” deployment guidance
- **Documentation**
  - `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_SUMMARY.md`
  - runbooks / troubleshooting sections
  - “how to add a provider/agent” docs if present

### Out-of-scope (for this bundle)
- ratchet correctness edge cases (Bundle 1)
- supply chain/dependency threat modeling (Security bundle)
- cost optimization, model selection strategy (future bundle)

---

## 2) Expected Deliverables

### A) Executive summary
- “Ready / not ready” plus the top 2–4 operational blockers.

### B) Findings table
For each finding:
- **Title**
- **Severity**: P0 blocker / P1 high / P2 medium / P3 low
- **Area**: logs / traces / config / deploy / docs
- **Failure mode** (how it hurts operators)
- **How to reproduce** (or where to see it)
- **Recommended fix** (minimal)
- **Doc change needed** (if relevant)

### C) Operator UX walkthrough
Codex should simulate being a new user and answer:
- “What commands do I run?”
- “What do I need to set?”
- “How do I know it’s healthy?”
- “Where do I look when it fails?”

### D) “Minimum runbook” checklist
Codex should list missing runbook items.

---

## 3) Review Questions (Codex must answer)

### 3.1 Observability: Logging
1) Do logs always include enough context to correlate:
- agent name
- task/card id
- epic id / project id
- event/phase
- provider + model
- request_id / trace_id (or equivalent)
- outcome (success/failure) and duration

2) Are errors logged with:
- stack trace (when appropriate)
- structured fields (not only freeform strings)
- actionable remediation hints?

3) Are log levels used consistently?
- info vs warning vs error
- noisy logs avoided?

4) Is the JSON formatter capturing *all* “extra” fields reliably?

---

### 3.2 Observability: Tracing
1) Do traces contain the **minimum for post-mortems**?
- request metadata
- provider/model
- timing
- config hash (excluding secrets)
- repair metadata (whether repaired + method)
- raw provider output (especially for CLI)
- final parsed output

2) Are trace paths deterministic and safe?
- directory creation behavior
- potential for unlimited growth
- how to disable or prune traces

3) Is there an easy way to correlate logs ↔ traces?
- shared request_id present in both?

---

### 3.3 Monitoring & health checks
1) Does the monitoring dashboard produce:
- useful summaries
- low-noise recommendations
- clear grouping by provider/role/model
- exportability (json output)

2) Do health checks / doctor commands:
- fail clearly and specifically
- not block the system unnecessarily
- support partial configs (CLI-only ok, HTTP-only ok)
- detect missing binaries, missing keys, unreachable endpoints

3) Is profiling output actionable?
- identifies slow agents/steps
- identifies IO vs LLM latency vs Kanboard latency
- readable report output

---

### 3.4 Config & deployability
1) Is config schema stable and validated?
- missing fields caught with good errors
- unknown providers handled sanely
- role mapping errors actionable

2) Are `.env` semantics clear?
- what is required vs optional
- precedence rules (env overrides yaml?)
- secure defaults

3) Does the system run in common deployment modes?
- local workstation
- headless server
- dockerized (if supported)

4) Are runtime assumptions documented?
- Kanboard plugins like MetaMagik
- custom fields required
- column names required
- permissions required
- webhook setup requirements

---

### 3.5 Documentation: can someone actually run it?
Codex should attempt a “doc-driven install” mentally:

1) Starting from README only, can a dev:
- create venv / install deps
- configure env + yaml
- run doctor/health
- start webhook/orchestrator
- trigger a sample epic through full pipeline
- locate traces and monitoring reports
- understand failure and recovery steps

2) Are there gaps, contradictions, or stale claims?
- sprint plan vs reality
- test count claims
- outdated files referenced (e.g., removed legacy modules)

3) Is there a clear “How to extend” section?
- add a new provider
- add a new stack prompt pack (future)
- add a new agent

---

## 4) What Codex should inspect (file targets)

Codex should locate actual filenames; common candidates:

### Observability / tooling
- `lib/logger.py`
- `lib/llm/trace.py`
- `lib/llm/monitor.py`
- `tools/repair-monitor.py`
- `lib/llm/doctor.py` or `lib/llm/__main__.py`
- `lib/llm/health.py`
- `lib/profiler.py`
- `tools/profile-report.py`

### Config
- `lib/llm/config.py`
- `config/llm.yaml`
- `.env.example`
- any config docs in `README.md`, `CLAUDE.md`, `GEMINI.md`

### Docs
- `README.md`
- `CLAUDE.md`
- `GEMINI.md`
- `IMPLEMENTATION_SUMMARY.md`
- `sprintPlan.md` / `llm-redesign-sprint-plan.md` (consistency check)

---

## 5) Commands Codex can run (if allowed)

Smoke test:
```bash
pytest -q
python -m lib.llm.doctor --config config/llm.yaml
python -m lib.llm.health --config config/llm.yaml  # if exists
python tools/repair-monitor.py --all
python tools/profile-report.py --help
```

Search for observability fields:
```bash
rg -n "request_id|trace_id|correlation|event|provider|model|task_id|project_id" lib agents tools
rg -n "trace(s)?/|\\.agentleeops|retention|prune|delete" .
rg -n "doctor|health|monitor|profile" README.md CLAUDE.md GEMINI.md
```

---

## 6) Acceptance bar for “PASS”
Bundle 2 passes if Codex concludes:

- An operator can diagnose issues using **logs + traces** with clear correlation
- Monitoring tools provide **useful, low-noise** insights
- Config errors are **actionable** and do not unnecessarily block execution
- Docs enable a new user to run the system end-to-end with minimal guessing

**P0 blockers** include:
- logs missing correlation fields needed for debugging
- traces missing raw outputs or identifiers for reconstruction
- doctor/health tools misleading or unusable
- README cannot get a user to “first successful run”
