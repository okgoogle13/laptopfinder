---
name: alternative-silicon-sprint
description: Active sprint — June 2026 alternative-silicon scoring layer + pipeline audit
metadata:
  type: project
---

# Alternative-Silicon Scoring Layer — June 2026 (COMPLETE)

**Why:** UMA platforms (Apple Silicon, Strix Halo) were artificially capped at 75 points, making them appear weaker than discrete GPU laptops for text-centric inference workloads where they are actually superior. The scoring layer now reflects real inference capability.

**Status:** Complete 2026-06-30. 108 tests green.

## Changes shipped

- `config/silicon_profiles.yaml` — paradigm definitions + workload preferences
- `config/scoring_weights.yaml` — per-workload weight profiles (text_llm_default, training_or_diffusion)
- `data/hardware_taxonomy.json` — 4 representative hardware entries by paradigm
- `prompts/system_context.md` — agent system instructions (paradigm-first)
- `prompts/bias_guard_prompt.md` — bias self-check rubric for CUDA inclusion
- `research/alternative_silicon_dossier_june2026.md` — synthesised AU market research
- `src/laptopfinder/decide.py` — `Paradigm` type, `_classify_paradigm()`, `load_scoring_weights()`, `score_text_llm_candidate()`, `workload` param on `decide()`, UMA ceiling removed
- `config/static_reference_layer.json` — `score_ceiling: null`, policy comments added
- `tests/test_decide.py` — 2 ceiling tests fixed, 3 new test classes (108 tests)
- `tests/test_prompts.py` — prompt content sanity checks
- `CLAUDE.md` / `AGENTS.md` — architecture and invariants updated

## Sprint 2 (pending)

- Watchlist extraction pipeline (eBay AU, Gumtree, FB Marketplace)
- Prompt discovery updates (paradigm-first language + watchlist URL patterns)

---

# Pipeline Audit — June 2026

**Why:** Benchmark sprint validated the engine against known-good fixtures. This sprint expands target lists and scoring weights based on what's actually appearing on AU used markets.

**Status:** In progress. See TASKS.md for item-level tracking.

## Phases

### 1. Market Gap Analysis (Deep Research)
Use Perplexity or manual eBay/Gumtree/FB searches to surface:
- High-VRAM GPUs (≥16GB) not yet in `target_gpus` (e.g. RTX 4070 Ti SUPER variants, Radeon W7900M)
- Laptop/workstation models not in `target_models` but appearing frequently
- Watch list graduation candidates: RTX 5080/5090 (check if used units are actually listed at real AU prices)
- New UMA platforms: any Apple Silicon Max/Ultra configs ≥64GB or AMD Strix Halo laptops

### 2. Spec Comparison
Build a comparative table of the top 5 shortlisted candidates:
- Price-to-VRAM ratio (AUD/GB)
- Thermals (TDP, cooling solution notes)
- Availability depth (# of listings found)

### 3. Pipeline Enhancements
Propose concrete edits to `config/static_reference_layer.json`:
- New entries for `target_gpus`, `target_models`, `radeon_mobile_gpus`, `conditional_models`
- Updated generation scores for Blackwell (RTX 50xx) and RDNA3 (ROCm penalty calibration)
- 5–10 additional discovery prompt search terms
- Watch list graduation conditions and new watch list entries
- 1–3 documented blind spots with proposed fixes

## Definition of Done
- [ ] Config JSON fragments drafted and reviewed
- [ ] `make test` still green after any SRL changes
- [ ] Market gap findings documented in `deep_research_output.md`

---

# Evidence-Based Target Pipeline — June 2026

**Why:** Current target lists are static. This pipeline derives provisional hardware spec ranges from real observed macOS workload telemetry, then hands off to Claude Pro for inference. Prevents the decision engine from chasing the wrong VRAM tier.

**Status:** Pipeline complete. 23 telemetry records collected and aggregated. `targets.json` requires regeneration using the corrected Claude prompt (see Pending below).

## Architecture
1. Drop telemetry files → `data/evidence/raw/`
2. `make evidence-run` → generates Gemini prompts in `data/evidence/prompts_for_gemini/`
3. Human pastes each prompt into the Gemini web UI and saves the resulting JSON files to `data/evidence/parsed/`
4. `make evidence-run` → parses files from `parsed/`, appends to `data/evidence/aggregated.jsonl`, archives originals
5. At ≥5 records → generates `data/evidence/claude_handoff.txt`
6. Human pastes handoff into Claude Pro, saves response as `data/evidence/targets.json`
7. `targets.json` feeds into `static_reference_layer.json` or a runtime override

**Reset procedure:** `make evidence-reset` truncates `aggregated.jsonl` and removes the prompt hash sidecar for a clean restart.

## Session changes (2026-06-30)
- `prompts/gemini_evidence_parser.txt` — rewritten with corrective task constraints: CONTEXT/PAST FAILURES, HARD CONSTRAINTS, QUALITY CHECK, PIPELINE CLARIFICATION. Parser role is now strictly parse-only with no interpretation or hardware advice.
- `prompts/claude_evidence_analyzer.txt` — removed banned language (`bottleneck`, `contention`, `under strain`). Now uses neutral observational phrasing consistent with the corrective task.
- `evidence_pipeline.py` — added `--reset` flag and `make evidence-reset` target. Added SHA-256 prompt staleness check: warns at handoff generation time if `claude_evidence_analyzer.txt` has changed since the last handoff.
- `normalize_archive.py` — deleted. Was a one-off workaround. Canonical path restored.
- `claude_handoff.txt` — regenerated with corrected prompt. Ready to paste into Claude Pro.

## Pending
- [ ] **Paste `data/evidence/claude_handoff.txt` into Claude Pro and save corrected `targets.json`** — current file contains pre-correction interpretive language and must be replaced before feeding into the main pipeline
- [ ] Integrate corrected `targets.json` spec ranges into `config/static_reference_layer.json`
- [ ] Confirm `make test` stays green

## Definition of Done
- [x] `targets.json` validated against `evidence_targets.schema.json`
- [x] Gemini parser converted from API stub to manual prompt generator
- [x] Pipeline prompt constraints enforced (corrective task applied)
- [x] `make evidence-reset` available for clean restarts
- [x] Prompt staleness check in place
- [ ] Corrected `targets.json` generated from updated Claude prompt
- [ ] Spec ranges reflected in `static_reference_layer.json`
- [ ] `make test` still green
