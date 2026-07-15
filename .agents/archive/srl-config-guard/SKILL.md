---
name: srl-config-guard
description: Acts as an adversarial peer reviewer for any changes to the Static Reference Layer (config/static_reference_layer.json) to prevent config drift and schema violations.
---

# SRL Config Guard

You are acting in a peer review capacity. Your job is to review proposed changes to `config/static_reference_layer.json` (the Static Reference Layer / SRL) before they are committed, or whenever the user asks you to audit the config.

## Triggers
- When the user asks you to review a diff or changes to `static_reference_layer.json`.
- When another agent (like Claude Code) proposes changes to `static_reference_layer.json`.

## Core Guidelines

The SRL is the single source of truth for the decision engine's governance. Treat it as safety-critical. Changes here silently impact the decision cascade.

Perform the following checks on any proposed change or diff:

### 1. Structural Constraints
- Check that every entry in `target_gpus` includes at least: `platform_class`, `budget_band`, `evidence_type`, `price_min_aud`, and `price_max_aud`.
- Ensure prices are numeric or formatted correctly according to existing patterns.

### 2. Orphaned References
- Cross-check `target_gpus` additions/removals against `gpu_generation_by_name`.
- A GPU listed in `target_gpus` MUST have a corresponding generation assigned in `gpu_generation_by_name`.

### 3. Threshold Consistency
- Confirm that `standard_mobile_min_gb` remains greater than or equal to `touchscreen_exception_min_gb`.
- Ensure that `vram_tiers` defining `low`, `mid`, `high`, and `ultra` do not overlap and do not leave gaps (e.g., if mid ends at 23, high must start at 24).
- Ensure `score_ceiling` for UMA platforms remains `null`. Do not allow the re-introduction of a numeric score ceiling.

### 4. Policy Conflict Prevention
- Check for contradictory verdicts: A GPU with a `market_verdict` of `"GRADUATE"` should NOT also be listed in the `watch_list`.
- DEFER verdicts should have a clear `architecture_note` or `reason` (e.g., lack of native Flash Attention).

## Reporting
If you detect ANY violations of the above rules, explicitly call them out and suggest the exact JSON correction required to fix them. If the changes are clean, state clearly: "SRL Audit PASSED. No schema or policy violations detected."
