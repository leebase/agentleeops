# AgentLeeOps Mission Control — Product Specification v1.3

**Author:** Claude Opus 4.6 (Team Harrington)
**Date:** February 6, 2026
**Status:** DRAFT — Gates as workshops, model picker, review-centric design
**Changelog:**
- v1.0: Initial vision spec
- v1.1: Separated invariant core from experimental surface. Scoped advisory. Killed Electron. Lifecycle as data.
- v1.2: Added adapter contract (I-9), liveness (I-10). State Engine hardening. Artifact classification. Stale = hash drift. Phase 1 discovers existing work packages. Progress indicators throughout.
- v1.3: Added Gate Workshop invariant (I-11). Reframed Editor as Review Workshop with model picker. Elevated AI-assisted review from side feature to core activity. Adjusted phases to reflect review-centric workflow.

---

## 0. What This Document Is

This is a **vision and architecture compass**, not an implementation contract.

It defines two things:

1. **The Invariant Core** — sacred architectural decisions that must survive every iteration. These are the invention. Protect them.
2. **The Experimental Surface** — negotiable UI, interaction, and feature decisions that should evolve fast through building and learning.

When in doubt about a build decision, ask: *Does this strengthen the cockpit or dilute it?*

**North star sentence:**

> AgentLeeOps is a governance pipeline for AI-built software: artifacts on disk, approvals as hashes, and a human-operated cockpit that makes the work trustworthy.

---

## Part I: The Invariant Core

These decisions are non-negotiable. They define what Mission Control IS. They should not change based on UI fashion, technology trends, or scope pressure. Every future feature must be evaluated against these invariants.

---

### I-1. Identity

Mission Control is a **Human-AI Governance Interface**.

It is not a project management tool, not a code editor, not an agent runner, not a dashboard. It is a **governance cockpit** — the surface through which a single human directs, reviews, and approves the work of multiple AI agents.

The product category it belongs to does not yet exist.

### I-2. Work Package as Directory

The Work Package is the atomic unit of delivery. It is a directory on the local filesystem. It contains everything: manifest, artifacts organized by stage, approval history, and integrity metadata.

```
work-packages/<id>/
  manifest.yaml
  artifacts/
    <stage-name>/
      <artifact files>
  approvals/
    <event-id>.json
  integrity/
    hashes.json
```

The filesystem is the single source of truth. Everything else — UI, adapters, dashboards — is a view of the filesystem.

### I-3. Artifacts Are First-Class Citizens

Artifacts are not attachments on cards. They are not links in comments. They are the interface itself.

The UI exists to render, compare, and assess artifacts. Every screen answers artifact questions: What exists? What state is it in? Is it consistent with its upstream dependencies? Has it drifted since approval?

An artifact that cannot be seen inline, diffed, and assessed from within Mission Control has failed the design.

### I-4. State Engine Authority

The UI never touches the filesystem directly. All mutations flow through the State Engine — the Python API layer that enforces governance rules.

This means:
- UI is replaceable (web, CLI, future native app — all equivalent)
- Adapters are pluggable (Kanboard, Jira, ADO, CLI — all equivalent)
- Automation cannot fork the governance logic
- Every state change is validated before it reaches disk

The State Engine exists and is battle-tested for Kanboard workflows. Mission Control will harden it for UI-driven workflows — specifically: atomic multi-file transitions, concurrent access safety (UI + orchestrator operating simultaneously), partial-failure recovery, and schema migration as the manifest evolves.

### I-5. Approval Log as Append-Only History

Every approval, rollback, and intervention is recorded as an immutable event. Events are never deleted or overwritten. The full history of a Work Package's lifecycle is always recoverable.

This is the audit trail. It answers: who approved what, when, with what hash, and why.

### I-6. Ratchet Enforcement in the Interface

The ratchet is not a convention enforced by discipline. It is a constraint enforced by the system.

- Locked artifacts cannot be modified by agents. Period.
- The UI must not offer edit paths to locked artifacts without an explicit unlock action.
- Unlock is a recorded governance event, not a silent state change.
- The visual distinction between locked, draft, and stale must be immediate and unambiguous.

The interface IS the ratchet. If the ratchet can be bypassed through the UI, the UI is broken.

**Stale definition for v1:** An artifact is stale when its current file hash differs from its approved hash. That's it. No upstream propagation, no dependency graph analysis. Hash drift is the only trigger.

v2+ may introduce upstream-driven staleness (e.g., design change propagates staleness to test plan). That is explicitly deferred.

### I-7. Lifecycle as Data, Not Code

The lifecycle pipeline (Inbox → Design Draft → Design Approved → Planning Draft → ...) is defined in a configuration file, not hardcoded into the UI or the State Engine.

A lifecycle definition includes:
- Ordered stages
- Stage type: `draft` (agent-owned) or `gate` (Lee-owned)
- Expected artifacts per stage, classified as:
  - **Required:** Must be present and healthy to pass the gate
  - **Optional:** Tracked if present, not required for gate passage
  - **Derived:** Generated by the system (dashboards, reports), tracked but not gate-blocking
- Entry/exit conditions
- Ratchet actions on transition

Lifecycle defines required artifacts. Additional artifacts may exist in a stage directory and are tracked by the integrity system, but gates only require required artifacts to be present and healthy.

This means:
- Different project types can have different lifecycles
- Experimental pipelines can be tested without code changes
- The canonical 11-step workflow is the default, not the only option
- The UI renders whatever lifecycle the data defines

```yaml
# Example: lifecycle.yaml
lifecycle:
  name: "standard-11"
  stages:
    - id: inbox
      type: gate
      owner: human
      artifacts: []

    - id: design-draft
      type: draft
      owner: architect
      artifacts:
        - name: "DESIGN.md"
          classification: required

    - id: design-approved
      type: gate
      owner: human
      ratchet_action: lock
      locks: ["DESIGN.md"]

    - id: planning-draft
      type: draft
      owner: pm
      artifacts:
        - name: "prd.json"
          classification: required

    - id: plan-approved
      type: gate
      owner: human
      ratchet_action: lock
      locks: ["prd.json"]

    - id: tests-draft
      type: draft
      owner: test-agent
      artifacts:
        - name: "TEST_PLAN_*.md"
          classification: required
        - name: "test_*.py"
          classification: derived

    - id: tests-approved
      type: gate
      owner: human
      ratchet_action: lock
      locks: ["tests/*.py"]

    - id: ralph-loop
      type: draft
      owner: ralph
      artifacts:
        - name: "src/**"
          classification: required

    - id: code-review
      type: draft
      owner: review-agent
      artifacts:
        - name: "CODE_REVIEW_REPORT.json"
          classification: required
        - name: "CODE_REVIEW_NEXT_STEPS.md"
          classification: optional

    - id: final-review
      type: gate
      owner: human

    - id: done
      type: terminal
```

### I-8. The Human Decides

The LLM advises. The LLM proposes. The LLM surfaces.

The LLM never writes to locked artifacts. The LLM never approves. The LLM never advances a gate. The LLM never overrides the ratchet.

Every write to disk that changes governance state requires Lee's explicit action.

This is not a safety rail bolted on. It is the core philosophy: the bottleneck in AI-assisted development is trust, and trust requires human judgment at every governance boundary.

### I-9. Adapter Contract

Adapters (Kanboard, Jira, ADO, CLI, Mission Control UI) interact with the State Engine through a defined contract. The contract permits:

- CRUD operations on Work Packages
- Reading lifecycle configuration and current state
- Advancing or rolling back lifecycle stages (subject to preconditions)
- Attaching artifacts to stages
- Reading and writing approval events
- Writing comments and telemetry

The contract prohibits:

- Direct artifact mutation bypassing the State Engine
- Modifying ratchet state without a recorded governance event
- Altering approval history
- Bypassing precondition checks on transitions

Every adapter — including the Mission Control UI — is bound by this contract. No adapter gets special privileges. This prevents "adapter creep" where integrations become special cases that fork governance logic.

### I-10. Liveness and Progress Transparency

The cockpit must always answer: **"Is something happening, or is it dead?"**

Every operation that does not complete instantly must provide observable progress. This includes:

- Agent runs (design generation, planning, test writing, Ralph loop iterations, code review)
- LLM review conversations and advisory analysis
- Artifact hashing and integrity checks
- Stage transitions (especially if they trigger downstream actions)

The system must distinguish between three states for any non-instant operation:

| State | Meaning | Visual |
|-------|---------|--------|
| **Working** | Process is actively running | Animated indicator + elapsed time |
| **Completed** | Process finished successfully | Success indicator + result summary |
| **Failed/Stalled** | Process errored or stopped progressing | Alert indicator + last known state |

**Stall detection:** If an agent run has produced no output (no file writes, no log entries) for a configurable duration, the system surfaces a stall warning. The human can then investigate, retry, or reassign.

**Heartbeat model:** Agent processes should emit periodic signals (file writes, log entries, or explicit heartbeat events) that the State Engine can monitor. Absence of signal for longer than the stall threshold triggers the warning.

This is an invariant because a governance cockpit with blind spots is a cockpit that can't govern.

### I-11. Gates Are Workshops, Not Checkpoints

An agent produces a first draft. The real quality work happens at the gate.

Every gate stage is a **review workshop** where Lee collaborates with AI to pressure test, critique, and refine artifacts before approval. This is not a side feature. This is not an optional enhancement. This is the core activity of the system.

The workflow at every gate is:

1. Agent generates artifact (first draft)
2. Lee reads the artifact in Mission Control
3. Lee **talks to an AI about it** — asks questions, challenges assumptions, identifies gaps, explores alternatives
4. The AI proposes revisions based on the conversation
5. Lee reviews the proposed changes, accepts or rejects
6. Steps 3-5 repeat until Lee is satisfied — possibly with a different AI model for a second opinion
7. Lee saves the refined artifact
8. Lee approves and advances. The ratchet locks.

Approval does not mean "the artifact exists." Approval means **the artifact survived adversarial review and Lee is confident in its quality.**

The interface must support this loop natively:
- Artifact is visible while conversing with the AI (no tab switching, no copy-paste)
- The AI can read the full artifact and its upstream dependencies
- The AI's suggestions become concrete diffs on the artifact, not chat messages Lee has to manually transcribe
- Lee can switch AI models mid-review to get a different perspective
- The conversation and its resulting changes are part of the Work Package record

This is how Lee works. This is how the Eternal Now manifesto was built, how these prompts were refined, how this spec evolved through three AI reviewers. Mission Control must make this natural workflow frictionless.

---

## Part II: The Experimental Surface

Everything below is negotiable, iterable, and expected to evolve. These are starting hypotheses about how the invariant core should be presented and interacted with. Build fast. Learn fast. Change freely.

---

### II-1. The Three-Layer Interaction Model

A hypothesis about cognitive modes:

**Layer 1 — Navigator:** "What needs my attention?"
A scan view. All active Work Packages, their pipeline position, and whether any require Lee's action. Optimized for the 5-second rule: Lee should assess total state in one glance.

**Layer 2 — Inspector:** "What is the state of this thing?"
A detail view. One Work Package, its full lifecycle, every artifact with state and integrity, approval history, and any advisories. This is where Lee sees what's ready for review.

**Layer 3 — The Workshop:** "Let me review and refine this artifact."
The primary working environment. Where Lee reads an artifact, converses with AI about it, accepts revisions, and builds confidence before approving. This is where Lee spends most of his active time.

This model may change. The invariant is that the UI must support all three cognitive modes. How it organizes them into screens is experimental.

### II-2. The Navigator — Starting Hypothesis

Each active Work Package is a horizontal pipeline row:

- Pipeline nodes represent stages (completed, active, pending)
- Visual badges indicate: decision needed, stale artifacts, agent working, agent stalled, blocked
- Minimal information: title, current stage, time in stage, next action needed
- **Active agent indicator:** When an agent is running, the active stage pulses with elapsed time. When stalled, it shifts to an alert state.
- **Review ready indicator:** When a gate has artifacts ready for Lee's review workshop, a distinct "ready for review" badge appears.

**Design constraint:** Resist the Christmas tree. Every indicator added to the Navigator must earn its place by answering a question Lee actually asks during his scan. If he doesn't ask the question in practice, remove the indicator.

**Open question:** How many Work Packages will be active simultaneously? If typically 1-3, the Navigator can be richer per row. If 10+, it must be sparser. Build and observe.

### II-3. The Inspector — Starting Hypothesis

Stages expand vertically, each showing:

- Stage status (locked / active / pending)
- Artifact cards with state badges and hash indicators
- View and diff actions on each artifact
- For gate stages: the review workshop entry point and approval interaction
- **For active draft stages:** Agent execution panel showing:
  - Agent role and provider
  - Start time and elapsed duration
  - Last activity timestamp (from heartbeat/file events)
  - For Ralph Loop specifically: iteration count, test pass/fail ratio, convergence indicator
  - Log tail (last N lines of agent output, auto-scrolling)

**The Gate — Review Workshop Entry:**

```
GATE: Design Approval

Artifacts ready for review:
  📄 DESIGN.md — draft, hash: a3f8...
     [Open in Workshop]  [Quick View]

[ Approve & Lock ]  [ Send Back ]
```

The primary action at a gate is "Open in Workshop" — not approve. Approve comes after the workshop. The UI should guide Lee toward reviewing before approving, not make approval the first available action.

**The Agent Activity Panel:**

```
ACTIVE: Ralph Loop — Iteration 4

  Agent: ralph (openrouter/claude-sonnet)
  Started: 3m 22s ago
  Last activity: 8s ago ✅

  Tests: 4/7 passing
  Progress: TC-1 ✅  TC-2 ✅  TC-3 ✅  TC-4 ✅  TC-5 ❌  TC-6 ❌  TC-7 ❌
  Trend: Converging (was 2/7 → 3/7 → 4/7)

  [View latest source] [View test output] [Tail log]
```

**When stalled:**

```
⚠ STALLED: Ralph Loop — Iteration 4

  Agent: ralph (openrouter/claude-sonnet)
  Started: 12m 47s ago
  Last activity: 5m 03s ago ⚠ NO RECENT ACTIVITY

  Tests: 4/7 passing (unchanged for 3 iterations)

  [View last attempt] [Retry] [Reassign provider] [Intervene manually]
```

### II-4. The Workshop — Starting Hypothesis

This is the heart of Mission Control. Where the real work happens.

**Layout:** Two-panel view.

- **Left panel:** The artifact, rendered for reading. Markdown rendered as formatted text. JSON as a structured tree. Code with syntax highlighting. Scrollable, searchable. Diffs highlighted when viewing stale artifacts.

- **Right panel:** AI conversation. A chat interface scoped to this artifact. The AI has read access to the current artifact plus all other artifacts in the Work Package for context.

**Model Picker:**

At the top of the right panel, a dropdown (or toggle) to select the active AI model:

```
┌─────────────────────────────────────────────────┐
│  Workshop: DESIGN.md                            │
│                                                 │
│  ┌─────────────────┬───────────────────────────┐│
│  │                 │  Model: [Claude Opus ▾]   ││
│  │  # Design:      │                           ││
│  │  Task Router    │  Lee: Is R3 specific      ││
│  │                 │  enough to test?           ││
│  │  ## 1. Overview │                           ││
│  │  The task       │  Claude: R3 says "handle  ││
│  │  router is...   │  errors gracefully" which ││
│  │                 │  is vague. I'd suggest     ││
│  │  ## 2. Assump-  │  rewriting as: "When the  ││
│  │  tions          │  API returns a non-200     ││
│  │  ...            │  status, the router must   ││
│  │                 │  log the status code and   ││
│  │                 │  return a structured error ││
│  │                 │  within 50ms."             ││
│  │                 │                           ││
│  │                 │  [Apply to artifact]       ││
│  │                 │                           ││
│  │                 │  Lee: Good. Apply it.      ││
│  │                 │                           ││
│  │                 │  ┌─ Proposed diff ────────┐││
│  │                 │  │- handle errors         │││
│  │                 │  │- gracefully            │││
│  │                 │  │+ When the API returns  │││
│  │                 │  │+ a non-200 status,     │││
│  │                 │  │+ the router must log   │││
│  │                 │  │+ the status code and   │││
│  │                 │  │+ return a structured   │││
│  │                 │  │+ error within 50ms.    │││
│  │                 │  └────────────────────────┘││
│  │                 │  [Accept] [Reject] [Edit] ││
│  │                 │                           ││
│  │                 │  ──────────────────────── ││
│  │                 │  Model: [ChatGPT o3 ▾]    ││
│  │                 │                           ││
│  │                 │  Lee: Review what Claude   ││
│  │                 │  just changed in R3.       ││
│  │                 │  Is the 50ms target        ││
│  │                 │  realistic?                ││
│  │                 │                           ││
│  └─────────────────┴───────────────────────────┘│
│                                                 │
│  [Save & Return to Inspector]  [Approve & Lock] │
└─────────────────────────────────────────────────┘
```

**Key Workshop behaviors:**

**Model switching:** Lee selects a model from the dropdown. The conversation continues in the same panel. When the model changes, a visual divider marks the switch so Lee can see which model said what. Each model gets the same artifact context — the current state of the artifact plus the Work Package context. Previous conversation turns are visible but not necessarily sent to the new model (configurable — Lee may want a fresh perspective or may want continuity).

**Apply to artifact:** When the AI suggests a change, it can be converted to a concrete diff on the left panel. Lee sees exactly what will change. Accept writes the change to the artifact (through the State Engine). Reject discards. Edit lets Lee modify the proposed change before accepting.

**Left panel updates live:** When Lee accepts a change, the left panel re-renders immediately with the updated artifact. The AI's next responses are based on the updated version.

**Save and continue vs approve:** Lee can save artifact changes and return to the Inspector without approving. This supports multi-session review — work on the design today, sleep on it, come back tomorrow, run it past a different model, then approve. The artifact state remains `draft` until explicitly approved.

**Workshop context:** The AI always has access to:
- The current artifact (as it stands right now, including any accepted changes)
- All other artifacts in the Work Package (for cross-reference)
- The lifecycle definition (to understand what stage this is and what comes next)
- The approval history (to understand what's already been locked)

The AI does NOT have access to:
- Other Work Packages
- System configuration
- Lee's other conversations outside this workshop

**Model configuration:**

The model dropdown is populated from the existing `config/llm.yaml` provider configuration. Adding a new model to the Workshop means adding it to the LLM config, not changing the UI. The dropdown shows:

```
Claude Opus (anthropic)
Claude Sonnet (anthropic)
ChatGPT o3 (openai)
GPT-4o (openai)
Gemini Pro (google)
Grok (xai)
```

Which models are available depends on which providers are configured. The UI just reads the config.

### II-5. LLM Advisory — Scoped for v1

**v1 philosophy: assistant, not auditor.**

The advisory system in v1 should do three things well rather than ten things poorly:

**1. Artifact Review on Demand**
Lee clicks "Review this artifact" in the Workshop and the AI reads it in context (with upstream artifacts) and surfaces observations. Not a comprehensive audit. A smart colleague's read-through.

**2. Gap Spotting at Gates**
When Lee opens a Workshop at a gate, the AI can perform a lightweight check:
- Are all upstream requirements represented in the current artifact?
- Are there obvious omissions (a requirement with no corresponding story, a story with no test case)?
- Are there vague or untestable acceptance criteria?

This is pattern matching, not graph analysis. It's "does this look complete?" not "prove coverage with a traceability matrix."

**3. Targeted Edit Proposals**
In the Workshop, Lee can ask the AI to fix a specific issue: "Add a test case for R3's timeout behavior." The AI generates a proposal as a diff. Lee reviews.

**What v1 explicitly does NOT do:**
- Full automated coverage graph analysis
- Cross-artifact consistency enforcement
- Automated staleness propagation recommendations
- Architectural linting
- Prompt tuning or self-improvement

These are all valid research tracks for v2+. They are not v1 scope.

**Advisory presentation:**
- Advisories are part of the Workshop conversation, not a separate system
- Lee can dismiss or ignore any observation
- Advisories never block approval — Lee always overrides
- No severity classification in v1. The AI just tells Lee what it notices. Lee judges importance.

### II-6. Technology — v1

**FastAPI + browser. No Electron.**

- Python FastAPI server wrapping the existing State Engine
- Serves a React frontend on localhost
- No deployment. No auth. No packaging.
- Lee opens a browser tab. That's the interface.

Rationale: Lee is in architecture discovery mode. The fastest path to learning is the simplest technology that renders the invariant core. FastAPI + React is that path. Electron is a productization decision for when the interface design has stabilized.

**Frontend stack:**
- React (aligns with existing dashboard generation patterns)
- Tailwind for styling (utility-first, fast iteration)
- react-markdown for artifact rendering
- Monaco or CodeMirror for code/JSON viewing
- A simple diff library for artifact comparison
- WebSocket connection for real-time progress updates from State Engine

**Backend additions:**
- REST endpoints for Work Package CRUD, lifecycle operations, artifact read/write
- WebSocket endpoint for liveness/progress events
- LLM proxy endpoint: receives artifact context + user message + selected model, routes to the appropriate provider via `lib.llm`, streams response back to the Workshop UI
- Artifact diff endpoint: given two versions (or current vs approved hash snapshot), returns structured diff

**LLM integration:**
- Calls through the existing `lib.llm` abstraction
- Same provider pluggability (OpenRouter, Codex, Gemini, Claude, OpenAI, Grok)
- Model selection is a runtime parameter per Workshop request, not a system-wide setting
- Advisory prompts stored as templates alongside existing stage prompts
- Stateless: reads artifacts, returns structured response, no persistence
- Streaming support for responsive Workshop conversations

### II-7. Ratchet Visualization — Starting Hypothesis

Every artifact displays its governance state visually:

| State | Visual Treatment | Meaning |
|-------|-----------------|---------|
| Draft | Soft border, muted | Editable by agents and Lee |
| Approved/Locked | Solid border, lock icon, hash shown | Immutable to agents |
| Stale | Warning border, alert indicator | Hash differs from approved hash |
| Superseded | Dimmed, strikethrough | Downstream of a rollback |

The exact colors, icons, and visual language are experimental. The invariant is that the four states must be visually distinct at a glance.

---

## Part III: Build Plan

### Phase 1 — The Governance Skeleton

**Goal:** Replace Kanboard as Lee's primary view of work state.

Build:
- FastAPI server exposing State Engine operations as REST endpoints
- WebSocket endpoint for real-time state change and progress events
- **Discovery of existing work-packages/ from disk** — render pipeline state for Work Packages that already exist from Kanboard-driven workflows
- Navigator: list of active Work Packages with pipeline visualization
- Inspector: stage detail with artifact state badges
- Gate interaction: approve/send-back with one click
- Ratchet visualization (lock state visible on every artifact)
- Basic liveness indicators: working/completed/failed badges on active stages
- New Work Package creation (title, acceptance criteria, context mode, lifecycle selection)

Do not build:
- Workshop (LLM conversation + editing)
- Agent execution detail monitoring
- Diff views
- Advisory system

**Exit test:** Lee can open Mission Control and see his existing Work Packages (created via Kanboard/CLI) with correct pipeline state. He can create a new Work Package, advance through stages, approve gates, see ratchet state, and roll back — all without touching Kanboard. Active agent runs show a basic "working" indicator.

**Estimated effort with agent assistance:** 1-2 weeks.

### Phase 2 — Artifact Rendering + Agent Visibility

**Goal:** Lee never opens a file browser to read an artifact and always knows if agents are working.

Build:
- Markdown rendering for DESIGN.md, test plans
- JSON structured view for prd.json
- Code view with syntax highlighting for test and source files
- Diff view for stale artifacts (approved version vs current)
- Agent execution panel in Inspector (role, provider, elapsed time, last activity, stall detection)
- Ralph Loop tracker (iteration count, test pass/fail, convergence trend)
- Log tail view for active agent runs

Do not build:
- Workshop editing or LLM conversation
- Advisory system

**Exit test:** Lee can read and review every artifact type inline. When an artifact is stale, he can see exactly what changed. When Ralph is running, Lee sees iteration progress and knows whether Ralph is converging, stuck, or crashed.

**Estimated effort:** 1-2 weeks.

### Phase 3 — The Workshop

**Goal:** Lee can review, discuss, and refine artifacts with AI assistance inside Mission Control.

This is the critical phase. This is where Mission Control becomes the tool Lee actually works in rather than a status display he glances at.

Build:
- Workshop view: artifact left panel + AI conversation right panel
- Model picker dropdown populated from `config/llm.yaml`
- LLM proxy endpoint with streaming responses
- AI can read current artifact + all Work Package artifacts as context
- "Apply to artifact" flow: AI suggestion → structured diff → accept/reject/edit
- Left panel live update on accepted changes
- Save without approving (support multi-session review)
- Visual divider when model switches mid-conversation
- Progress indicator during AI response generation

Do not build:
- Conversation persistence across sessions (v2+ consideration)
- Automated advisory triggers
- Multi-artifact editing

**Exit test:** Lee opens a Workshop on a DESIGN.md, asks Claude a question about it, gets a useful response, asks Claude to revise R3, sees the diff, accepts it, artifact updates on disk. Then Lee switches to ChatGPT, asks it to critique the change Claude made, gets a second opinion. Lee saves and returns to Inspector. Artifact state is `draft` with updated hash. Lee approves from Inspector. Ratchet locks.

**Estimated effort:** 1-2 weeks.

### Phase 4 — Advisory Integration

**Goal:** The Workshop proactively surfaces observations, not just responds to questions.

Build:
- "Review this artifact" quick action that triggers a structured AI review
- Lightweight gap spotting: on Workshop open at a gate, AI automatically offers initial observations
- Observations appear as conversation messages Lee can engage with or ignore
- Dismiss/acknowledge flow

Do not build:
- Full coverage graph
- Automated consistency enforcement
- Severity classification

**Exit test:** Lee opens a Workshop at a gate. Without asking, the AI offers one observation about a coverage gap. Lee finds it useful and acts on it.

**Estimated effort:** 1 week.

### Phase 5 — Hardening and State Engine Maturity

**Goal:** Mission Control is reliable enough to be Lee's sole interface.

Build:
- Atomic multi-file transitions (approve gate = lock artifacts + write events + update manifest in one transaction)
- Concurrent access safety (UI and orchestrator can operate simultaneously without corruption)
- Partial-failure recovery (interrupted transitions leave clean state)
- Schema migration tooling for manifest evolution
- Deprecate Kanboard as primary interface (retain as read-only backup if desired)

**Exit test:** Lee uses Mission Control exclusively for one full project lifecycle. No Kanboard fallback required. One intentional crash/interruption mid-transition recovers cleanly.

**Estimated effort:** 1-2 weeks.

### Future — Unscheduled

These are real capabilities that belong in Mission Control eventually but are explicitly deferred:

- Electron packaging for native app distribution
- Workshop conversation persistence and replay across sessions
- Multi-model simultaneous review (send same question to two models at once, compare responses)
- Full coverage graph analysis (requirements → stories → tests → code)
- Automated staleness propagation across artifact dependencies
- Advisory severity calibration with tunable thresholds
- Lifecycle editor (create/modify pipelines from the UI)
- Multi-Work-Package dependency tracking
- Export/reporting for completed Work Packages
- Notification system for "decision needed" states
- Keyboard-first navigation
- Mobile read-only view
- Agent configuration and reassignment from UI
- Prompt tuning interface for stage prompts

---

## Part IV: How to Read This Document

**If you're building Phase 1:** Read Part I (all of it) and Phase 1 of Part III. Ignore everything else.

**If you're building Phase 3 (Workshop):** Read I-8, I-11, and II-4 carefully. The Workshop is where Mission Control's identity lives.

**If you're making a feature decision:** Check it against Part I. If it violates an invariant, stop. If it's an experimental surface question, try it and learn.

**If you're wondering "should we build X?":** Ask: does X strengthen the governance cockpit? If yes, prioritize. If it makes Mission Control more like an IDE or a project manager, defer or reject.

**If Lee changes his mind about something in Part II:** Great. That's what Part II is for. Change it.

**If Lee changes his mind about something in Part I:** That's a fundamental architecture discussion. Have it deliberately, not accidentally.

---

## Part V: The Thesis

Everyone else in the AI tooling space is optimizing for:

*AI writes more code faster.*

Lee identified a different truth:

*The bottleneck is trust.*

Trust that what the AI produced is correct. Trust that it aligns with intent. Trust that the tests actually test what matters. Trust that nothing was silently weakened to make a green bar. Trust that the agent is actually working and hasn't silently died.

Mission Control is built for that bottleneck. It doesn't make agents faster. It makes Lee's oversight faster, more informed, and more reliable. It treats the human not as a bottleneck to be removed but as the essential quality gate that makes the whole system trustworthy.

The AI writes the code. The AI writes the tests. The AI writes the design.

Lee reviews with AI. Lee refines with AI. Lee pressure tests with AI.

Then Lee decides if any of it is real.

That's the product. That's the category. That's the cockpit.

Build for that.

---

*End of specification.*
