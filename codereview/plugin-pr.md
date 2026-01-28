PR: Add Pluggable LLM Provider System with YAML Routing (OpenCode + Gemini CLI + OpenRouter)

Summary

Introduce a provider-pluggable LLM layer so AgentLeeOps can route requests by role (planner/coder/reviewer/etc.) to different backends using a YAML config, without changing agent logic.

MVP providers included:
	•	OpenCode CLI (to leverage ChatGPT Plus subscription)
	•	Gemini CLI (to leverage Gemini subscription / CLI usage)
	•	OpenRouter API (pay-as-you-go, model selection per role)

Future providers (Anthropic direct, Groq, OpenAI direct, etc.) should be addable as plugins without modifying agent code.

Motivation

Today, AgentLeeOps is implicitly coupled to a single execution path (OpenCode). We want:
	•	Plug-and-play AI with role-based routing
	•	A clear path away from CLI/subscription-based invocation toward direct APIs
	•	Provider extensibility (others can add new backends later)
	•	Reproducible runs via config + trace metadata

Goals
	1.	Stable internal interface used by agents: agents call LLM.complete(role=..., prompt=..., artifacts=...) (exact signature TBD below), not “OpenRouter” or “OpenCode”.
	2.	YAML config defines:
	•	enabled providers
	•	role routing (planner/coder/reviewer)
	•	per-role options (temperature/max_tokens/timeout/json mode)
	•	optional per-provider params passthrough
	3.	Providers implemented for MVP:
	•	opencode_cli provider (uses local OpenCode command)
	•	gemini_cli provider (uses local gemini CLI)
	•	openrouter_http provider (HTTP API)
	4.	Trace recording logs:
	•	provider, model, role, config hash, request_id, timestamps
	•	prompt + response (or at minimum a pointer to stored trace file)
	5.	Keep Kanboard integration unchanged (board abstraction is explicitly out of scope).

Non-goals (for this PR)
	•	No Kanboard abstraction / alternate board backends
	•	No “smart routing” (latency/cost-based dynamic decisions). Routing is static by role.
	•	No background job system, queueing, distributed locking
	•	No full schema enforcement for structured output beyond “best-effort + optional repair” (see below)

⸻

Proposed Architecture

Roles (normalized)

Define a small set of roles AgentLeeOps uses internally:
	•	planner (Design, Plan, Breakdown, Test drafting prompts)
	•	coder (Ralph loop coding)
	•	reviewer (code review / diff critique) — optional but supported
	•	summarizer (PR summary, release notes) — optional but supported

Agents select a role; routing chooses provider+model.

Core interface: LLMClient

Create module: agentleeops/llm/client.py

Primary call:

LLMClient.complete(
  role: str,
  messages: list[dict],      # chat-style: [{"role":"system|user|assistant","content":...}, ...]
  *,
  json_mode: bool = False,   # request JSON-only if provider supports it
  schema: dict | None = None,# optional JSON schema for future use (MVP may ignore)
  max_tokens: int | None = None,
  temperature: float | None = None,
  timeout_s: int | None = None,
  trace: TraceContext | None = None
) -> LLMResponse

LLMResponse should include:
	•	text: str
	•	provider: str
	•	model: str | None
	•	usage: dict | None (tokens/cost if available)
	•	raw: dict | str | None (provider raw response for debugging)
	•	request_id: str (generated)
	•	elapsed_ms: int

Provider plugin contract

Create: agentleeops/llm/providers/base.py

class Provider(Protocol):
    id: str  # unique provider id

    def validate_config(self, cfg: dict) -> None: ...

    def complete(self, request: LLMRequest) -> LLMResponse: ...

Plugin registration (MVP approach)

Use a simple registry for MVP (no packaging/entry-points yet):
	•	agentleeops/llm/providers/registry.py
	•	register_provider(ProviderImpl)
	•	get_provider(id)

(We can evolve to Python entry-points later; keep this simple now.)

⸻

Configuration

Files
	•	config/llm.yaml (committed example; not secrets)
	•	.env (local, secrets only)

YAML schema (MVP)

Example config/llm.yaml:

llm:
  default_role: planner

  providers:
    opencode_plus:
      type: opencode_cli
      command: "opencode"               # or full path
      model_hint: "chatgpt-plus"        # informational only
      timeout_s: 120

    gemini_cli:
      type: gemini_cli
      command: "gemini"
      model: "gemini-3"                 # if CLI supports selecting
      timeout_s: 120

    openrouter:
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      timeout_s: 120
      default_headers:
        HTTP-Referer: "agentleeops"
        X-Title: "AgentLeeOps"

  roles:
    planner:
      provider: openrouter
      model: "openai/gpt-5.2-codex"     # example
      temperature: 0.2
      max_tokens: 4000
      json_mode: true

    coder:
      provider: openrouter
      model: "xai/grok-code-fast"       # example
      temperature: 0.1
      max_tokens: 4000

    reviewer:
      provider: opencode_plus
      temperature: 0.2
      max_tokens: 2000

Config resolution rules
	•	Role selection required (defaults to default_role if omitted).
	•	Provider must exist and be enabled.
	•	Model may be omitted for CLI providers if not supported; store model=None but still record provider/role/config hash.
	•	Provider-specific extras allowed under provider_params: (optional) without breaking schema.

⸻

Provider Implementations (MVP)

1) OpenRouter HTTP provider

File: agentleeops/llm/providers/openrouter_http.py
	•	Reads API key from env var indicated in YAML.
	•	Implements /chat/completions (OpenAI-style) per OpenRouter.
	•	Supports json_mode if possible (e.g., response_format or system instruction fallback).
	•	Returns usage info if provided.

2) OpenCode CLI provider

File: agentleeops/llm/providers/opencode_cli.py
	•	Executes configured command (default opencode) with prompt piped via stdin or temp file (choose one; must be robust).
	•	Captures stdout as model output.
	•	Must record:
	•	command used
	•	exit code
	•	stderr (in trace only, not in normal logs unless error)
	•	Treat as “best effort” re JSON mode:
	•	If json_mode=True, include strong instruction in the prompt and optionally run a local “json repair” helper (optional; see below).

3) Gemini CLI provider

File: agentleeops/llm/providers/gemini_cli.py
	•	Executes gemini command (from YAML), passes prompt similarly.
	•	Captures stdout, records invocation metadata.
	•	Same best-effort JSON mode behavior.

Note: exact CLI flags differ by install; implement in a way that is configurable in YAML (command, args_template) so Lee can adapt without code changes.

⸻

Trace / Observability

Structured JSON logging
	•	All LLM calls must log one JSON event:
	•	event: llm.complete
	•	role, provider, model, request_id, elapsed_ms, success/failure
	•	config_hash (hash of effective role config + provider config excluding secrets)

Trace recording to file

Store per-call traces under:
	•	.agentleeops/traces/<YYYYMMDD>/<request_id>.json

Trace file includes:
	•	resolved config snapshot (with secrets removed)
	•	request messages (system/user)
	•	response text
	•	raw provider response (if safe)
	•	stderr for CLI providers
	•	timing/exit code

⸻

Integration Points

Where to use it

Replace direct model invocation in:
	•	PM agent (plan/breakdown)
	•	Test agent (test generation)
	•	Ralph loop (coding)
	•	Reviewer steps (if any)

Each agent should call:

llm = LLMClient.from_config("config/llm.yaml")
resp = llm.complete(role="planner", messages=[...], trace=...)

No agent should reference OpenRouter/OpenCode/Gemini directly after this PR.

⸻

Acceptance Criteria
	1.	With config/llm.yaml pointing planner/coder to OpenRouter:
	•	planning calls go through OpenRouter with specified model
	•	coding calls go through OpenRouter with specified model
	2.	With config/llm.yaml planner set to opencode_plus:
	•	planning calls execute via OpenCode CLI
	3.	With config/llm.yaml planner set to gemini_cli:
	•	planning calls execute via Gemini CLI
	4.	All LLM calls:
	•	emit structured JSON log event
	•	write a trace file with request + response + metadata
	5.	If OpenRouter key missing:
	•	failure is explicit and actionable (Missing env var OPENROUTER_API_KEY)
	6.	No changes required in agent logic when switching providers; only YAML changes.

⸻

Testing

Unit tests (minimum)
	•	Config loading + resolution:
	•	invalid provider reference fails
	•	missing env var for OpenRouter fails
	•	Registry loads all MVP providers
	•	Config hash stable and excludes secrets

Provider tests (lightweight)
	•	OpenRouter provider: mock HTTP response and verify parsing.
	•	CLI providers: mock subprocess runner to simulate stdout/stderr/exit code.

(Do not require real network calls for tests.)

⸻

Dev UX

Add a doctor command (optional but highly recommended):
	•	agentleeops llm doctor --config config/llm.yaml
Outputs:
	•	providers found
	•	required env vars present
	•	CLI commands exist on PATH
	•	sample completion “ping” per provider (dry-run or optional)

⸻

Documentation

Add docs/llm-providers.md with:
	1.	How to configure .env (OpenRouter key)
	2.	How to switch roles in YAML (planner/coder)
	3.	How to add a new provider:
	•	copy template provider
	•	register in registry
	•	add YAML stanza
	4.	Notes on CLI providers vs direct APIs
	5.	Security note: .agentleeops/traces may contain prompts; add .gitignore entry

⸻

Notes / Future Work (explicitly not in this PR)
	•	Move from registry to Python entry-points for “real plugins”
	•	Add Anthropic direct provider
	•	Add Groq provider
	•	Add “structured output repair” as a first-class step for json_mode
	•	Card-level ratcheting of provider/model config (lock routing per card run)

⸻

Implementation Checklist (for the coder)
	•	Add YAML loader + config model (dataclasses ok)
	•	Implement provider registry + base protocol
	•	Implement openrouter_http provider
	•	Implement opencode_cli provider
	•	Implement gemini_cli provider
	•	Implement LLMClient routing by role
	•	Replace direct calls in agents to use LLMClient
	•	Add trace recording + structured logging
	•	Add .gitignore for .agentleeops/traces/
	•	Add unit tests
	•	Add docs
