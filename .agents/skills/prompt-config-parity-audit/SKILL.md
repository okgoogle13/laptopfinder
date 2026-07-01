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
2. **Standard VRAM threshold:** 
   - SRL: `vram_gating_logic.standard_mobile_min_gb`
   - Prompt: `prompts/claude_code_audit.txt` (Rule 4.d)
   - Rules: `CLAUDE.md` (Decision Engine Rule 4)
3. **Touchscreen exception VRAM threshold:** 
   - SRL: `vram_gating_logic.touchscreen_exception_min_gb`
   - Prompt: `prompts/claude_code_audit.txt` (Rule 4.e)
   - Rules: `CLAUDE.md` (Decision Engine Rule 4)

## Action Plan
- Run `make inject-config` to propagate the latest GPU target list and UMA RAM thresholds to dynamically-injected blocks inside `prompts/comet_discovery_agent.txt` and alternate silicon prompts.
- **ALWAYS** run the deterministic parity test suite before completing your task:
  ```bash
  .venv/bin/pytest tests/test_prompt_parity.py -v
  ```
  This test statically checks `claude_code_audit.txt` and `CLAUDE.md` using regex to verify parity with the SRL. If the test fails, do not commit. Update the natural language files to match the new configuration values.
