---
name: prompt-search-term-auditor
description: Audits discovery prompt search terms (prompts/comet_discovery_agent.txt) against SRL target_gpus and watch_list. Triggers when editing prompts or SRL config to catch injection block drift.
---

# Prompt Search Term Auditor

You are auditing that the discovery prompt's injected target lists are in sync with the Static Reference Layer (SRL) before any prompt is submitted to a live LLM agent.

## Triggers
- When editing `config/static_reference_layer.json` (specifically `target_gpus` or `watch_list`).
- When editing any file in `prompts/`.
- When you are about to run `make scrape-and-live` or `make live`.

## Action Plan

Always perform these steps in order:

1. **Run the deterministic injection sync test:**
   ```bash
   .venv/bin/pytest tests/test_prompt_parity.py::test_prompt_injection_sync -v
   ```
   If this test fails, the prompt sentinel blocks are stale. Do NOT proceed to run a live agent.

2. **Fix the stale sentinels by running:**
   ```bash
   make inject-config
   ```
   Then re-run the test to confirm it passes.

3. **Then verify threshold parity:**
   ```bash
   .venv/bin/pytest tests/test_prompt_parity.py -v
   ```

## Why This Matters
The `<!-- BEGIN_INJECT:TARGETS -->` block inside `prompts/comet_discovery_agent.txt` is the primary GPU target list sent to the Gemini discovery agent. If the SRL is updated (e.g., new GPUs added from the enrichment patch) but `make inject-config` is not re-run, the live discovery agent will miss newly added targets like `RTX 4000 Ada`, `RTX 3500 Ada`, and workstation models.
