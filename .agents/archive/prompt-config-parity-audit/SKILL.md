---
name: prompt-config-parity-audit
description: Audits prompt files and repo-level guidelines (CLAUDE.md) for hardcoded threshold drift against static_reference_layer.json. Trigger when editing prompts or configuration.
---

# Prompt-Config Parity Audit

You are an agent auditing configuration and prompt instructions for consistency. Hardcoding numeric limits in natural language files (like prompts and guidelines) leads to drift when configuration changes.

## Triggers
- When you are editing `config/static_reference_layer.json` (SRL).
- When you are editing any file inside the `prompts/` directory.
- When you are editing `CLAUDE.md` (or `AGENTS.md`).

## Parity Checks
Whenever thresholds change, the following locations must remain perfectly aligned:
1. **UMA RAM threshold:** 
   - SRL: `vram_gating_logic.uma_unified_min_gb`
   - Prompt: `prompts/claude_code_audit.txt` (Rule 4.c)
   - Rules: `CLAUDE.md` (Decision Engine Rule 3)
   - Prompt (manual, no injection): `prompts/perplexity_space_description.txt` ("Strict Memory Gates" section)
   - Reference doc: `memory/reference/pipeline.md` (Terminology table + Decision Priority Order) — this file was found stale (64GB) during the 2026-07 doc audit; the correct value is 32GB.
2. **Standard VRAM threshold:** 
   - SRL: `vram_gating_logic.standard_mobile_min_gb`
   - Prompt: `prompts/claude_code_audit.txt` (Rule 4.d)
   - Rules: `CLAUDE.md` (Decision Engine Rule 4)
3. **Touchscreen exception VRAM threshold:** 
   - SRL: `vram_gating_logic.touchscreen_exception_min_gb`
   - Prompt: `prompts/claude_code_audit.txt` (Rule 4.e)
   - Rules: `CLAUDE.md` (Decision Engine Rule 4)
4. **UMA score ceiling (removed 2026-06-30):**
   - SRL: `apple_silicon.score_ceiling` (must remain `null`)
   - Any prompt describing `llm_index_score` scoring guidance for Apple Silicon/UMA (e.g. `prompts/alternative_silicon_gemini.txt` Section 3 "SCORING GUIDANCE") must NOT state a point cap for UMA platforms.
5. **Target GPU / watch list membership:**
   - SRL: `target_gpus`, `watch_list`
   - Auto-synced via injection markers: `prompts/comet_discovery_agent.txt`, `prompts/alternative_silicon_gemini.txt`, `prompts/alternative_silicon_perplexity.txt` (see `scripts/inject_config.py`)
   - NOT auto-synced — must be checked/updated manually: `prompts/perplexity_space_description.txt` (no injection markers; this file drifted out of sync with SRL during the 2026-07 doc audit and was manually corrected — re-check it by hand on every target-list change until it is wired into the injection system)

## Action Plan
- Run `make inject-config` to propagate the latest GPU target list and UMA RAM thresholds to dynamically-injected blocks inside `prompts/comet_discovery_agent.txt` and alternate silicon prompts.
- **ALWAYS** run the deterministic parity test suite before completing your task:
  ```bash
  .venv/bin/pytest tests/test_prompt_parity.py -v
  ```
  This test statically checks `claude_code_audit.txt` and `CLAUDE.md` using regex to verify parity with the SRL. If the test fails, do not commit. Update the natural language files to match the new configuration values.
