Bundle 4 — Tests + Performance/Scaling (Codex Review Brief)

Mission

Review AgentLeeOps post–Sprint 18 for (1) test suite quality and risk coverage and (2) performance/scaling characteristics of the agent loops and tooling—especially where AI-driven velocity can amplify failure modes (slow runs, runaway retries, trace growth, subprocess overhead).

This is not a cosmetic test style review. It’s: Do the tests actually protect the system? And will this stay usable as workload grows?

⸻

1) Scope

In-scope
	•	Unit + integration tests
	•	coverage of happy and unhappy paths
	•	determinism and flake risk
	•	mocking strategy correctness (avoid false confidence)
	•	Performance profiling
	•	profiler implementation correctness
	•	report usefulness and accuracy
	•	Agent loop scaling
	•	Ralph loop iteration behavior
	•	retry/backoff behavior
	•	trace/log growth
	•	Kanboard API call patterns
	•	CLI provider overhead (subprocess calls, JSON repair cost)
	•	Monitoring metrics (performance-related)
	•	provider latency stats
	•	error rates
	•	compression and repair rates as performance predictors
	•	Resource usage
	•	CPU/RAM use on long runs
	•	file I/O growth from traces
	•	subprocess churn

Out-of-scope
	•	deep security analysis (Bundle 3)
	•	documentation completeness (Bundle 2)
	•	governance logic correctness (Bundle 1), except where tests should cover it

⸻

2) Expected Deliverables

A) Executive Summary
	•	“Tests protect us / tests give false confidence” + “Perf is safe / perf will degrade” assessment.

B) Test Coverage Map

Codex should produce a short map:
	•	critical modules → tests that cover them
	•	identify gaps and weakly-tested areas

C) Findings Table

For each finding:
	•	Severity: P0 / P1 / P2 / P3
	•	Category: tests / perf / scaling
	•	Failure mode
	•	Evidence (files / tests / code paths)
	•	Fix (minimal)
	•	Add test (where applicable)

D) Suggested performance budgets

Codex should recommend budgets like:
	•	max wall time for an agent step before warning/error
	•	max trace size per run
	•	max retries per card
	•	max spawned children per epic

⸻

3) Review Questions (Codex must answer)

3.1 Test suite quality
	1.	Do tests cover failure paths?

	•	provider timeouts
	•	malformed CLI output (and repair failures)
	•	Kanboard API rejects
	•	webhook duplicate deliveries
	•	partial spawner failures / orphans
	•	ratchet violations
	•	attempt to modify tests in Ralph loop

	2.	Are tests deterministic?

	•	no real network calls unless explicitly flagged integration
	•	no time-based flakiness
	•	subprocess calls mocked safely
	•	filesystem isolated with tmp paths

	3.	Is mocking strategy sound?

	•	avoids testing mocks instead of behavior
	•	uses contract-style tests for providers (inputs → outputs)

	4.	Are there integration tests that matter?

	•	at least one “smoke” path with fake Kanboard + fake LLM provider
	•	verify orchestration picks right agent per column
	•	verify artifacts written and ratchet enforced

	5.	Are tests fast enough for iteration?

	•	identify slow tests
	•	recommend marking heavy tests as integration

⸻

3.2 Performance profiling correctness
	1.	Does lib/profiler.py (and report tool) measure the right things?

	•	wall time per step
	•	LLM latency vs local processing vs Kanboard calls
	•	aggregation by agent and phase
	•	percentiles (p50/p95) if available

	2.	Are reports actionable?

	•	clearly identify bottlenecks
	•	tie back to trace/request_id

	3.	Any overhead or correctness issues in profiling itself?

⸻

3.3 Scaling characteristics & limits

Codex should identify scaling risks for:
	•	Large epics (many child cards)
	•	Large prompts (even with compression)
	•	Long agent runs (hours)
	•	Many trace files (days/weeks)
	•	Many concurrent orchestrators (if allowed)

Questions:
	1.	Does the system have explicit limits?

	•	max children per epic
	•	max retries
	•	max iteration count in Ralph loop
	•	max trace retention

	2.	What happens under degraded conditions?

	•	provider slowdowns
	•	Kanboard slowness
	•	intermittent CLI failures
	•	JSON repair frequently triggered (costly)

	3.	Does the orchestration do redundant work?

	•	repeated reads of same task metadata
	•	excessive Kanboard polling
	•	repeated re-computation of prompt packs/hashes

⸻

3.4 Performance “foot-guns”

Codex should look specifically for:
	•	unbounded loops
	•	retries without backoff/jitter
	•	parsing large traces repeatedly
	•	reading/writing huge files without streaming
	•	subprocess spawning per request without reuse
	•	verbose trace logging in tight loops

⸻

4) What Codex should inspect (file targets)

Tests
	•	tests/ overall structure
	•	tests/test_*provider*.py
	•	tests/test_json_repair.py
	•	tests/test_ratchet.py
	•	tests/test_workspace.py
	•	tests/test_monitor.py
	•	tests/test_compression.py
	•	webhook/orchestrator/spawner tests

Performance tools
	•	lib/profiler.py
	•	tools/profile-report.py
	•	trace reader parts in lib/llm/monitor.py or similar

Runtime hot paths
	•	agents/ralph.py (loop behavior)
	•	agents/spawner.py
	•	webhook_server.py
	•	orchestrator.py
	•	lib/llm/client.py (compression + trace writing)
	•	CLI providers (subprocess behavior)

⸻

5) Commands Codex can run (if allowed)

Basic:

pytest -q
pytest -q --durations=20

If profiling tool supports it:

python tools/profile-report.py --help
python tools/profile-report.py --latest

Search:

rg -n "while True|for .* in range\(|retry|backoff|sleep\(|timeout" agents lib
rg -n "trace|write_trace|open\(.*traces" lib tools
rg -n "spawn|flood|max_children|limit" agents lib
rg -n "pytest\.mark\.slow|integration|network" tests


⸻

6) Acceptance bar for “PASS”

Bundle 4 passes if Codex concludes:
	•	Tests cover critical invariants and failure paths, not just happy paths
	•	Tests are fast, deterministic, and structured for confidence
	•	Profiling outputs are accurate and actionable
	•	System has explicit limits (or clearly documented assumptions) preventing runaway loops, runaway spawning, and runaway trace growth
	•	Identified performance bottlenecks have mitigation paths (batching, caching, backoff, budgets)

P0 blockers include:
	•	unbounded retries or loops without guardrails
	•	tests that silently hit real network/CLI in CI without being marked
	•	profiling/monitoring tools that report misleading results
	•	known scaling disaster paths (e.g., spawner can create thousands of tasks) without limits