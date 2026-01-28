```markdown
# Executive Summary (Architecture + Governance + Idempotency Review)

**Status:** Not Ready.

## P0 Issues
- **Ratchet lock can be bypassed via delete/recreate** because `safe_write_file` only checks locks if the file currently exists. This breaks **G1** (approved artifacts can be overwritten).
- **Webhook/orchestrator idempotency** relies only on tags and has no lock/TTL or dedupe key; duplicate deliveries or concurrent runners can execute the same agent twice. This breaks **I1/I4** in practice.
- **Spawner idempotency** only detects children via linked tasks + `atomic_id` metadata, so partial failures can create orphans that get duplicated on rerun. This breaks **I2**.
- **Ralph’s test immutability guard** only checks staged files and only verifies a single test file hash when ratcheted; unstaged or missing tests are not blocked, so **G2** is not guaranteed under retries or accidental edits.

Boundaries are mostly separated (orchestrator vs. governance vs. workspace), but webhook and orchestrator duplicate logic (triggers/tags and agent routing), raising divergence risk.

Path safety for `dirname` is strong (no dots/slashes, lowercase/dashes), but `safe_write_file` doesn’t normalize or block absolute paths if misused, so **G4** is “likely” rather than proven.

Flood control is implemented in spawner (max 20 children), which is a positive guard for **I3**.

## Findings Table

| Title | Severity | Component | Failure Mode | Repro Steps | Recommended Fix | Suggested Test |
|-------|----------|-----------|--------------|-------------|-----------------|---------------|
| Ratchet bypass via delete/recreate | P0 | `lib/workspace.py`, `lib/ratchet.py` | Locked files can be deleted and re-written because `safe_write_file` checks lock only if file exists; ratchet doesn’t block recreation. | 1) Lock `DESIGN.md` via governance. 2) Delete file. 3) Call `safe_write_file` to recreate—write succeeds despite lock. | Always check ratchet status regardless of file existence; deny writes when lock exists even if file missing. Consider storing locks on normalized paths and block recreate. | Add test: lock file, delete it, assert `safe_write_file` raises `PermissionError`. |
| Webhook/orchestrator idempotency race | P0 | `orchestrator.py`, `webhook_server.py`, `lib/task_fields.py` | Duplicate webhook deliveries or concurrent orchestrators can run the same agent twice because tag-based checks aren’t atomic and there’s no lock/dedupe key. | Send same webhook twice quickly or run two orchestrators; both may observe “no started tag” and trigger agent. | Add a lock/tag with TTL or per-task metadata lock (e.g., `agent_lock=ARCHITECT_AGENT + timestamp`) and refuse if lock already set; ensure lock release on failure. | Simulate concurrent invocations: run two worker threads and verify only one executes agent. |
| Spawner idempotency misses orphans | P0 | `agents/spawner.py` | Idempotency uses links + metadata; if a child is created but link or metadata write fails, reruns will duplicate because the orphan isn’t detected. | Force error after duplicate creation but before metadata/link; rerun spawner creates another child with same atomic ID. | Add fallback idempotency scan of “Tests Draft” tasks filtering by `parent_id`/`atomic ID` in description or metadata; ensure spawner writes an idempotency marker early. | Test: create an orphan child without link/metadata and ensure spawner skips it. |
| Ralph test immutability not enforced for unstaged changes | P0 | `agents/ralph.py`, `lib/ratchet.py` | Guard only checks staged files; unstaged test edits or missing/altered tests (when not ratcheted) won’t fail. Only one test file hash checked. | Modify `tests/test_x.py` without staging; Ralph runs and commits source changes without detecting test modification. | Extend guard to detect any changes in `tests/` (staged or unstaged) and verify all ratcheted test hashes. | Test: modify test file without staging and assert Ralph aborts before commit. |
| Orchestrator/Webhook logic duplication | P2 | `orchestrator.py`, `webhook_server.py` | `TRIGGERS`/`TAGS` and per-agent routing logic are duplicated; divergences can create inconsistent behavior across entrypoints. | Change `TRIGGERS` in one file; webhook and orchestrator diverge. | Extract shared constants + processor functions into a module used by both. | Unit test ensures trigger map and tag set are identical across entrypoints. |
| “Started” tags never cleared on failure | P2 | `orchestrator.py`, `webhook_server.py` | Failed agents leave “started” tags set, preventing retries and causing “stuck” cards. | Force an agent failure; observe `*-started` tag stays and task never reprocesses. | On failure, either clear the started tag or set a failed tag with TTL-based retry logic. | Test: simulated failure clears started tag or marks failed to allow manual retry. |
| Global monkeypatch of HTTP handler | P3 | `webhook_server.py` | Module import mutates `BaseHTTPRequestHandler` and `BaseServer` error handling globally, which can affect other server instances in-process. | Import webhook module into another HTTP server context; handlers are globally patched. | Scope the behavior to the webhook server class instead of global monkeypatching. | Test: import webhook module and verify other HTTP handlers remain unmodified. |

## Governance Invariants Checklist

- **G1 — Approved artifacts cannot be silently overwritten:** Not guaranteed.  
  `safe_write_file` only checks ratchet locks if the file already exists, so delete/recreate bypasses locks. Also ratchet is path-keyed with no rename/delete guard.

- **G2 — Ralph cannot change tests:** Not guaranteed.  
  Ralph only checks staged files and only validates a single ratcheted test file hash. Unstaged edits or missing tests can slip through under retries.

- **G3 — Governance enforced consistently across entrypoints:** Likely but not guaranteed.  
  Orchestrator and webhook call governance; however, they duplicate logic, and manual agent invocation bypasses governance enforcement (no centralized guard).

- **G4 — Injection resistance for file paths/commands:** Likely.  
  `dirname` is validated for lowercase/digits/dashes with no dots/slashes; subprocess calls are list-based (no `shell=True`). However, `safe_write_file` does not block absolute paths if misused, so this is not proven end-to-end.

- **I1 — Webhook idempotency:** Not guaranteed.  
  No dedupe key or lock; tag checks are not atomic and can race across retries/concurrency.

- **I2 — Spawner idempotency:** Not guaranteed.  
  Idempotency only based on linked tasks + metadata; orphans or partial failures create duplicates.

- **I3 — Flood control:** Proven.  
  Spawner enforces `MAX_CHILDREN_PER_EPIC = 20` and aborts beyond that limit.

- **I4 — Concurrency safety (dual orchestrators/webhook+poller):** Not guaranteed.  
  No lock/TTL/lease mechanism present; multiple runners can process the same task concurrently before tags update.

## Architecture & Boundaries (Direct Answers)

**Responsibilities separation:**
- **Orchestration:** Implemented in `orchestrator.py` and `webhook_server.py` (event → agent selection).
- **Governance enforcement:** `agents/governance.py` locks artifacts; triggered by orchestrator/webhook on approved columns.
- **Kanboard integration:** `lib/task_fields.py` handles metadata + tags; orchestrator/webhook use it for status and tags.
- **Workspace I/O:** `lib/workspace.py` provides `safe_write_file` with ratchet checks; used by agents.
- **LLM calls:** LLM client used in agents; no obvious side effects across orchestration boundary.

**Conclusion:** Boundaries are mostly clean, but duplicated orchestration logic increases divergence risk.

**Import-order dependency / side-effect registration risk:**  
Webhook server globally monkeypatches HTTP handler error behavior at import-time, which can affect other server usage in-process.

**Duplicate agent logic across webhook vs orchestrator:**  
Both files replicate `TRIGGERS`/`TAGS` and per-agent `process_*` flows; risk of drift is real.

**Sources of truth are ambiguous in practice:**
- **Config:** Environment variables via `load_dotenv` are primary for Kanboard connection in both entrypoints.
- **Card state:** Tags + column position are used for orchestration, but tags are mutable and not atomic (race risks).
- **Tags/Custom fields:** `lib/task_fields.py` centralizes metadata usage, but tag mutations occur in multiple places (orchestrator/webhook).
- **Filesystem artifacts:** Ratchet lock manifest is the only authoritative lock for approved files, but enforcement is incomplete on delete/recreate.

## Optional Small Patch Suggestions (Targeted)

- **Ratchet hardening (G1):** Update `safe_write_file` to call `check_write_permission` even when the file doesn’t exist, and reject absolute/`..` paths. This prevents delete/recreate bypass and path traversal.
- **Spawner idempotency (I2):** Add a fallback search for existing children in “Tests Draft” by `parent_id` or `atomic_id` in metadata/description, even when links are missing; write idempotency marker early before link creation.
- **Webhook/orchestrator lock (I1/I4):** Add a per-task lock metadata key (e.g., `agent_lock=ARCHITECT_AGENT`, with timestamp/TTL) set before running agents and cleared on failure/success.
- **Ralph guard expansion (G2):** Extend `verify_no_test_changes` to check unstaged changes in `tests/` and verify all ratcheted test hashes, not just the active test file.

## Commands Run
```
rg -n "kanboard" -S .
rg -n "subprocess|shell=True|os.system|bash -lc" -S agents lib orchestrator.py webhook_server.py
rg --files -g 'AGENTS.md'
nl -ba <file> | sed -n '<range>p' (used to inspect orchestrator.py, webhook_server.py, lib/ratchet.py, lib/workspace.py, lib/task_fields.py, agents/*.py, and tests/*.py)
```

**Tests:** Tests were not run (review-only).
```