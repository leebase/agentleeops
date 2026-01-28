Demo Story: “Configurable Discount Engine (with Audit Trail)”

Why this is the right showcase story (before the story itself)

This story is designed to:
	•	Require real design (not just coding)
	•	Naturally decompose into atomic stories
	•	Demand tests as contracts
	•	Expose ratchet boundaries
	•	Demonstrate fan-out clearly
	•	Produce a non-trivial but bounded code artifact
	•	Be understandable to non-engineers watching the board

It is not a toy calculator — but it’s still small enough to finish in one sprint.

⸻

Stage 0 — Human Story (what you create)

Story: Configurable Discount Engine with Audit Log

As a business user,
I want a discount engine that can apply percentage or fixed discounts to an order total,
so that pricing rules can be changed without modifying core logic,
and every discount application is recorded for audit and debugging.

Acceptance Criteria
	•	Supports percentage discounts (e.g. 10%)
	•	Supports fixed-amount discounts (e.g. $15)
	•	Never allows total to go below $0
	•	Every discount application produces an audit record
	•	Invalid discount types are rejected with a clear error

Non-Goals
	•	No persistence (in-memory only)
	•	No UI
	•	No external dependencies

This is perfect because:
	•	It’s business-shaped
	•	It has policy vs mechanism tension
	•	It requires explicit decisions in design

⸻

Stage 1 — Design Draft (ARCHITECT_AGENT shines here)

This story forces design choices, such as:
	•	Strategy pattern vs conditionals
	•	Data shape for discount rules
	•	Shape of audit records
	•	Error-handling philosophy

Expected DESIGN.md topics:
	•	Core entities (Order, Discount, AuditEntry)
	•	Discount evaluation flow
	•	Guardrails (no negative totals)
	•	Extension points for new discount types
	•	Explicit statement of what won’t be handled

This is where humans reviewing the design can visibly say:

“Yes — this is the system I want built.”

⸻

Stage 2 — Plan / Breakdown (PM_AGENT fan-out showcase)

This story decomposes cleanly into atomic stories that are:
	•	independently testable
	•	logically ordered
	•	non-overlapping

Canonical atomic breakdown (example):
	1.	atomic-01: Define core data models (Order, Discount, AuditEntry)
	2.	atomic-02: Implement percentage discount logic
	3.	atomic-03: Implement fixed-amount discount logic
	4.	atomic-04: Enforce non-negative totals
	5.	atomic-05: Implement audit trail capture
	6.	atomic-06: Reject invalid discount types

This makes fan-out visually obvious on the board.

⸻

Stage 3 — Tests Draft (TEST_AGENT earns its keep)

Each atomic story has crisp, unambiguous tests:

Examples:
	•	Percentage discount math
	•	Fixed discount math
	•	Edge case: discount > total
	•	Audit entry contents (before/after totals)
	•	Error raised on unknown discount type

This stage demonstrates:
	•	Tests as contracts
	•	Human approval of test intent
	•	Ratchet protection once approved

Observers will see:

“Once tests are approved, the agent cannot wiggle.”

⸻

Stage 4 — Code (Ralph Loop demonstration)

Ralph now:
	•	Implements exactly what tests demand
	•	Cannot modify tests
	•	Is forced into correctness, not cleverness

This story is excellent because:
	•	There are multiple correct implementations
	•	But tests constrain behavior tightly
	•	You can point to tests and say “this is the spec”

⸻

Stage 5 — UAT (human validation)

Manual validation is intuitive:
	•	Call the engine
	•	Apply discounts
	•	Read audit log
	•	Verify totals

No scaffolding needed.

⸻

Why this story shows off AgentLeeOps better than most demos

AgentLeeOps Capability	How This Story Shows It
Human authority	Design & tests require approval
Ratchet governance	Tests + artifacts become immutable
Fan-out	Clear atomic breakdown
Idempotent spawning	Multiple atomic children
TDD discipline	Logic is contract-driven
Observability	Audit log mirrors system logging
Safety	Impossible for Ralph to “get creative”


⸻

Optional “director’s cut” enhancement

If you want maximum flex:

Add one more acceptance criterion after Design Approved:

“Add support for a minimum order total before discounts apply.”

This forces:
	•	a design revision
	•	a test update
	•	a clear ratchet moment

Observers will see controlled change, not chaos.

⸻

One-sentence framing you can reuse publicly

“This story is small enough to finish in a sprint, but rich enough to demonstrate human-governed agentic software delivery end-to-end.”

