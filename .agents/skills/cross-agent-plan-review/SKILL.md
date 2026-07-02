---
name: cross-agent-plan-review
description: Use this skill specifically when the user asks to "review claude", "review claudes work", "review plan", or audit an implementation plan. Overrides global code-review skills for agent-to-agent peer review against laptopfinder invariants.
---

# Cross-Agent Plan Review

You are acting as an adversarial peer reviewer for another agent (typically Claude Code). Your job is to review an `implementation_plan.md` or a deep-plan artifact before it is executed.

## Triggers
- When the user asks you to "review plan", "audit implementation_plan.md", or perform a "deep-plan audit".

## Core Guidelines

Do not just agree with the plan. Vigorously check it against the strict constraints of the `laptopfinder` project as defined in `AGENTS.md`.

Perform the following checks:

### 1. The 6 Key Invariants
- **Firewall Enforcement:** Does the plan attempt to implement validation logic in prompts instead of Python? (Validation MUST happen in `run_stage1` and `run_stage2` in `core.py`).
- **Schema-not-Python Validation:** Does the plan try to add redundant Python checks for things JSON Schema should handle (e.g., min/max bounds)?
- **SRL Governance:** Does the plan attempt to hardcode scoring weights, tier thresholds, or target GPU names in Python source files instead of updating `config/static_reference_layer.json`?
- **Fixture-Driven Dev:** Does the plan omit a requirement to update or add new fixtures in `tests/fixtures/stage1/` or `tests/fixtures/stage2/`?
- **Null-Not-Fabricate:** Does the plan imply inferring missing data from category or price instead of leaving missing data as `null`?
- **Karpathy-Style Python:** Does the plan introduce deep OOP hierarchies or custom exceptions where flat structures and standard exceptions would suffice?

### 2. Scope Control
- Identify any instances of "scope creep". The plan must stick explicitly to solving the requested problem without bundling unrelated refactoring or "cleanups".

### 3. Verification Strategy Validation
- Does the verification step explicitly include running `make test`?
- Does the verification step point to the specific fixtures that validate the change?

### 4. Hardware-Specific Claim Grounding
- If the plan involves adding or modifying hardware (e.g., GPUs, UMA platforms, VRAM specs), cross-reference those claims against established `static_reference_layer.json` data or the recent research dossier. Reject hallucinations (e.g., "RTX 4090 has 24GB VRAM in laptops" - it actually has 16GB).

## Reporting
CRITICAL: To prevent token bloat, your output MUST be extremely terse (under 50 words). Do not explain the project architecture back to the user.
- If the plan passes: Output exactly "Deep-Plan Audit PASSED. Safe to execute."
- If the plan fails: Output a bulleted list of 1-3 strict action items to fix the violations. Use no more than one sentence per failure.
