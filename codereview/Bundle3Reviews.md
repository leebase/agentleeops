Bundle 3 — Security Review (Secrets, Injection Surfaces, Subprocess Safety, Threat Model) (Codex Review Brief)

Mission

Review AgentLeeOps post–Sprint 18 for practical security risks in a single-user, local/self-hosted workflow that still interfaces with:
	•	external LLM providers (HTTP + CLI wrappers)
	•	Kanboard (webhook + API)
	•	git + filesystem writes
	•	subprocess execution

This is a “realistic attacker + realistic mistakes” review, not enterprise compliance theater.

⸻

1) Scope

In-scope
	•	Secrets handling
	•	env vars, .env, config hashing, traces/logs
	•	provider headers, API keys, tokens
	•	Prompt injection / untrusted input
	•	Kanboard card content used as LLM input
	•	LLM output used to write files / run commands
	•	Filesystem safety
	•	path traversal, symlinks, deletion/recreate bypass, unsafe writes
	•	Subprocess safety
	•	CLI providers (OpenCode/Gemini)
	•	any subprocess, shell=True, bash -lc, os.system usage
	•	Webhook/API exposure
	•	webhook auth, replay/duplication, denial-of-service by event spam
	•	Kanboard API permissions & token use
	•	Data exfiltration vectors
	•	what gets sent to LLM providers
	•	what gets written to traces
	•	what gets logged

Out-of-scope
	•	supply chain / SBOM deep audit (we can note obvious issues, but no full CVE sweep)
	•	multi-tenant hardening (unless you already claim to support it)

⸻

2) Expected Deliverables

A) Threat model (short, specific)

Codex must define:
	•	Assets to protect
	•	Trust boundaries
	•	Attacker models

B) Findings table

For each finding:
	•	Severity: P0 / P1 / P2 / P3
	•	Attack scenario (step-by-step)
	•	Impact
	•	Likelihood
	•	Minimal fix
	•	Test / guard recommendation

C) “Security invariants” checklist

Codex marks each as:
	•	guaranteed, likely, or not guaranteed

D) Optional: targeted patch suggestions

Small diffs welcome; no refactor sprawl.

⸻

3) Threat Model (Codex should use these attackers)

Attacker A — Malicious Kanboard content

A user (or compromised Kanboard instance) can create/edit card fields:
	•	title/description/comments/custom fields/tags
Goal: cause prompt injection, unsafe writes, command execution, or secret leaks.

Attacker B — Malicious or compromised LLM output

LLM returns:
	•	malformed JSON
	•	code that writes outside workspace
	•	instructions to run dangerous shell commands
Goal: filesystem damage, exfiltration, persistence.

Attacker C — Local workstation risk

A different local user or malware reads:
	•	traces/logs
	•	.env
	•	config files
Goal: steal API keys, leak proprietary prompts/data.

Attacker D — Network/Webhook abuse

Someone hits your webhook endpoint repeatedly or replays events.
Goal: DoS, spam agent runs, force trace growth, exhaust tokens/cost.

⸻

4) Security Review Questions (Codex must answer)

4.1 Secrets & leakage
	1.	Do logs/traces ever include:

	•	API keys
	•	Authorization headers
	•	full env dumps
	•	provider responses that might contain secrets

	2.	Is config hashing guaranteed to exclude secrets everywhere it’s computed/stored?
	3.	Are trace files protected by:

	•	location under user home
	•	.gitignore
	•	permission expectations documented

	4.	Do CLI providers risk leaking secrets via:

	•	command-line args (visible in ps)
	•	writing temp files
	•	shell history

P0 example: passing API keys via argv, or logging headers.

⸻

4.2 Prompt injection & untrusted inputs
	1.	What untrusted inputs enter prompts?

	•	Kanboard title/description/comments
	•	custom fields (atomic_id, dirname, stack, etc.)

	2.	Are there explicit prompt-injection mitigations?

	•	instruction hierarchy (system vs user)
	•	strict output contracts (JSON schema)
	•	refusal handling / syntax guard before write

	3.	Are LLM outputs ever used to create:

	•	filenames/paths
	•	shell commands
	•	git commands
	•	network calls

Codex must identify every trust boundary crossing where LLM output becomes action.

⸻

4.3 Filesystem / workspace safety
	1.	Are all writes constrained to a workspace root?

	•	path normalization
	•	deny .., absolute paths
	•	deny symlinks escaping root

	2.	Are deletions safe?

	•	no rm -rf style operations unless strictly scoped

	3.	Does ratchet enforcement include:

	•	delete+recreate bypass
	•	symlink trick bypass
	•	alternative write paths bypass

	4.	Are temporary files handled safely?

	•	predictable names?
	•	secure permissions?

⸻

4.4 Subprocess / CLI provider safety
	1.	Confirm:

	•	no shell=True unless strictly necessary and safe
	•	arguments passed as arrays, not string shells
	•	stdin usage for large prompts does not create weird parsing paths

	2.	Validate that prompt content cannot cause:

	•	command injection
	•	argument injection
	•	file redirection tricks

	3.	Timeouts and cancellation:

	•	do subprocesses get killed reliably?
	•	do zombie processes accrue?

⸻

4.5 Webhook & API exposure
	1.	Does webhook endpoint require:

	•	secret token / signature verification
	•	source allowlisting (if feasible)
	•	replay protection (timestamp/nonce)

	2.	Do webhooks or polling cause:

	•	token/cost runaway if spammed
	•	uncontrolled trace growth

	3.	Kanboard API tokens/credentials:

	•	stored in env?
	•	least privilege documented?

⸻

5) Security Invariants Codex must grade

S1 — No secrets in logs/traces
S2 — No secrets passed via argv (ps-visible)
S3 — All file writes are inside workspace root
S4 — LLM outputs never directly become shell commands (unless allowlisted)
S5 — Webhook cannot be spammed into costly infinite work
S6 — Prompt injection cannot alter governance (ratchet/test immutability)
S7 — Trace directory cannot silently grow without operator visibility

Anything failing S1/S2/S3 is P0.

⸻

6) What Codex should inspect (file targets)

Likely files:
	•	lib/llm/providers/*.py (HTTP + CLI providers)
	•	lib/llm/trace.py
	•	lib/logger.py
	•	lib/llm/config.py
	•	.env.example, config docs
	•	webhook_server.py
	•	Kanboard client wrapper(s)
	•	lib/workspace.py
	•	lib/syntax_guard.py (and any validation modules)
	•	agents/ralph.py (command execution patterns)
	•	monitoring tools (trace reading safety)

Tests:
	•	any tests asserting no secrets in trace/log
	•	workspace/path safety tests
	•	webhook auth tests (if any)

⸻

7) Commands Codex can run (if allowed)

Search for risky patterns:

rg -n "Authorization|Bearer|API[_-]?KEY|OPENROUTER|ANTHROPIC|GROQ|GEMINI" .
rg -n "subprocess|Popen|run\(|shell=True|os\.system|bash -lc" .
rg -n "trace|\\.agentleeops|traces|log" lib tools agents
rg -n "webhook|signature|token|HMAC|secret" .
rg -n "open\(|write\(|unlink\(|remove\(|rmtree\(" lib agents
rg -n "pathlib|resolve\(|absolute\(|realpath|\\.\\." lib agents

If runnable:
	•	run doctor/health to see what they print
	•	run a sample workflow and inspect produced traces/logs for leakage

⸻

8) Acceptance bar for “PASS”

Bundle 3 passes if Codex concludes:
	•	No secrets leak to logs/traces/argv
	•	All writes are workspace-contained and resistant to traversal/symlink escape
	•	Subprocess invocations are safe from injection
	•	Webhook has at least basic protection or documented “local-only” assumption + mitigations (token gate, rate limiting, or deployment guidance)
	•	Prompt injection cannot override governance and cannot cause code execution outside intended boundaries

If not, Codex must produce a short prioritized remediation list (P0 then P1).