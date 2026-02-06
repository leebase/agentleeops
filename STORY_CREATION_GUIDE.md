## Story Creation Guide (for AI)

Use this guide to improve a story before it enters the Design and Planning phases. The output should be a refined story with crisp, testable acceptance criteria and clear scope boundaries.

### 1. Inputs You Must Use
- Story title and description (as provided).
- Business goal or user value (if given).
- Any constraints or non‑goals (if given).

If any of these are missing, list them under **Open Questions**.

### 2. Output Structure
Produce a revised story with these sections:
- **Story Title**
- **Story Summary**
- **User Value**
- **Scope**
- **Out of Scope**
- **Acceptance Criteria**
- **Dependencies**
- **Risks**
- **Open Questions**

### 3. Story Summary
- 2 to 4 sentences, plain language.
- Describe the outcome, not the implementation.

### 4. User Value
- One sentence: “This enables [user/persona] to [do X] so that [outcome].”

### 5. Scope
- List what will be built or changed.
- Prefer observable outcomes over internal tasks.

### 6. Out of Scope
- List anything explicitly not included to avoid scope creep.
- If none, state “None”.

### 7. Acceptance Criteria
Rules:
- Write 3 to 8 criteria.
- Each criterion must be objective, binary, and testable.
- Prefer **Given / When / Then** or **Condition / Expected** phrasing.
- Avoid vague words unless measurable. Examples of vague words: “correctly”, “appropriate”, “robust”, “fast”, “intuitive”.
- Each criterion should map to at least one test case.
- Keep each criterion one sentence.

Example format:
- **AC-1:** Given [context], when [action], then [expected outcome].
- **AC-2:** Condition: [state]. Expected: [result].

### 8. Dependencies
- List any other stories, systems, or artifacts required.
- If none, state “None”.

### 9. Risks
- List technical or product risks that could affect delivery or testability.
- If none, state “None”.

### 10. Open Questions
- List any missing information that blocks clean acceptance criteria or testability.
- Mark each as **Blocking** or **Non‑blocking**.

### 11. Quality Checklist (must pass)
- Acceptance criteria are testable and non‑overlapping.
- Scope and out‑of‑scope are clear and consistent.
- No hidden dependencies.
- Story can be implemented and tested independently when dependencies are met.
