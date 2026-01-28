Bundle 1 — Architecture + Governance + Idempotency (Codex Review Brief)

Mission

Review AgentLeeOps post–Sprint 18 for (1) clean architecture boundaries, (2) governance/ratchet enforcement integrity, and (3) idempotency safety across webhook + orchestrator + spawner flows.

This is not a style review. It’s a “can this system be trusted under retries, races, and human mis-clicks?” review.

⸻

1) Scope

In-scope components
	•	Orchestration
	•	orchestrator.py
	•	webhook_server.py (or equivalent webhook entry)
	•	Any agent runner / dispatch module
	•	Governance / ratchet
	•	workspace.py (or file write helpers)
	•	ratchet enforcement modules (e.g., lib/ratchet.py, tests/test_ratchet.py)
	•	test immutability guards in agents/ralph.py
	•	any “governance agent” implementation
	•	Kanboard integration + task metadata
	•	Kanboard client wrapper(s)
	•	lib/task_fields.py (or tags/custom fields helper)
	•	spawner implementation + MetaMagik workaround
	•	LLM abstraction only insofar as it affects these
	•	e.g., prompt injection surfaces into file paths/commands, but don’t deep-review providers here

Out-of-scope (for this bundle)
	•	Provider performance, compression, monitoring dashboards, profiling internals (those belong to later bundles)
	•	Documentation polish
	•	Dependency / supply-chain analysis (security bundle)

⸻

2) Expected Deliverables

A) Executive summary (10–15 lines)
	•	“Ready / not ready” with 2–4 bullet reasons.

B) Findings table

For each finding:
	•	Title
	•	Severity: P0 blocker / P1 high / P2 medium / P3 low
	•	Component
	•	Failure mode (how it breaks)
	•	Repro steps (if applicable)
	•	Recommended fix (concrete, minimal change)
	•	Suggested test to prevent regression

C) “Governance invariants” checklist

Codex should explicitly state whether each is proven, likely, or not guaranteed.

D) Optional: small patch suggestions

Not full refactor PRs—just targeted diffs or function-level edits if a fix is obvious.

⸻

3) Review Questions (Codex must answer)

3.1 Architecture & boundaries
	1.	Are responsibilities cleanly separated among:

	•	orchestration (event → agent selection)
	•	governance enforcement (ratchet/test immutability)
	•	Kanboard integration (metadata + column transitions)
	•	workspace I/O (write guards, path safety)
	•	LLM calls (pure function-like interface)

	2.	Any import-order dependency or side-effect registration that could fail in production?
	3.	Any areas where agent logic is duplicated across webhook vs orchestrator paths (risk of divergence)?
	4.	Are “sources of truth” unambiguous?

	•	config
	•	card state
	•	tags/custom fields
	•	filesystem artifacts

⸻

3.2 Governance / ratchet integrity

Codex should validate these invariants end-to-end:

Invariant G1 — Approved artifacts cannot be silently overwritten
	•	DESIGN.md / prd.json / tests / etc. once marked approved (however you model it)
	•	Edge cases to check:
	•	delete + recreate bypass
	•	rename/move bypass
	•	symlink/path traversal
	•	writes through alternate helper functions that skip the guard

Invariant G2 — Ralph cannot change tests
	•	Not just staged changes—also:
	•	unstaged edits that still affect runtime
	•	edits via generated code writing into tests/ indirectly
	•	glob/git add . mistakes
	•	“temporary file” tricks

Invariant G3 — Governance is enforced consistently
	•	Whether workflow is triggered by:
	•	webhook events
	•	polling orchestrator
	•	manual CLI runs
	•	No alternate entrypoint bypass.

Invariant G4 — Injection resistance for file paths/commands
	•	Untrusted Kanboard card content cannot escape allowed workspace directories
	•	No shell injection paths via card text
	•	If agents run subprocess commands, confirm safe argument usage

⸻

3.3 Idempotency & fan-out safety

Codex should reason about and/or test these behaviors:

Invariant I1 — Webhook idempotency
	•	Duplicate webhook deliveries don’t double-run agents or double-advance state.

Invariant I2 — Spawner idempotency
	•	Running spawner twice on same epic does not create duplicate children.
	•	Running spawner after partial failure:
	•	does it clean up orphans?
	•	does it detect already-created children by atomic_id/custom field/link?

Invariant I3 — Flood control
	•	Misconfigured epic cannot spawn 1,000 cards (or if it can, it fails safely with a visible error and no partial disaster).

Invariant I4 — Concurrency
	•	Two orchestrators (or webhook + poller) running simultaneously:
	•	do they race and duplicate work?
	•	is there a lock/tag/TTL mechanism?
	•	if no lock exists, does design assume single-runner and is that enforced/documented?

⸻

4) What Codex should inspect (file targets)

Codex should locate the real filenames in your repo; these are likely candidates:
	•	orchestrator.py
	•	webhook_server.py / webhooks.py
	•	agents/ralph.py
	•	agents/spawner.py
	•	agents/architect.py, agents/pm.py, agents/test_agent.py (only insofar as they touch artifacts)
	•	lib/task_fields.py
	•	lib/workspace.py
	•	lib/syntax_guard.py (path validation / parsing)
	•	lib/kanboard*.py client wrapper(s)
	•	tests:
	•	tests/test_ratchet.py
	•	spawner tests
	•	webhook/orchestrator tests
	•	any test immutability tests

⸻

5) Commands Codex can run (if allowed)

If Codex can execute:

pytest -q
pytest -q tests/test_ratchet.py -q
pytest -q tests/test_spawner.py -q
pytest -q tests/test_webhook* -q
pytest -q tests/test_workspace.py -q

Static checks / discovery:

rg -n "ratchet|immutable|approve|approved|lock|integrity" .
rg -n "webhook|orchestrator|poll|dispatch|column" .
rg -n "spawn|duplicate|atomic_id|MetaMagik|custom field|link" .
rg -n "tests/|git add|verify_no_test_changes|diff -- tests" agents/ lib/
rg -n "subprocess|shell=True|os.system|bash -lc" .


⸻

6) Acceptance bar for “PASS”

This bundle “passes” if Codex concludes:
	•	Architecture boundaries are clear, with no brittle import-side-effect traps
	•	Ratchet & test immutability invariants are actually enforceable under edge cases
	•	Webhook + spawner are idempotent under retry and partial failure
	•	Concurrency assumptions are explicit and safe (lock or enforced single runner)

Anything that violates G1/G2/I1/I2 is P0.

⸻

If you want, Bundle 2 next will be: Observability + Config/Deployability + Docs (and I’ll keep it at the same “review brief” level).