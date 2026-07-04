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
- `research/alternative_silicon_dossier_july2026.md` — synthesised AU market research
- `src/laptopfinder/decide.py` — `Paradigm` type, `_classify_paradigm()`, `load_scoring_weights()`, `score_text_llm_candidate()`, `workload` param on `decide()`, UMA ceiling removed
- `config/static_reference_layer.json` — `score_ceiling: null`, policy comments added
- `tests/test_decide.py` — 2 ceiling tests fixed, 3 new test classes (108 tests)
- `tests/test_prompts.py` — prompt content sanity checks
- `CLAUDE.md` / `AGENTS.md` — architecture and invariants updated

## Sprint 2 (active — 2026-07)

**Goal:** Wire three new pipeline components to make the system data-driven and operationally self-sufficient.  
**Plan:** `planning/claude-plan.md` (canonical HOW) · `planning/sections/` (agent work units) · `TASKS.md` Sprint 2 (status).

Deliverables:
- `scripts/inject_config.py` — idempotent marker-based injection of SRL values into prompt sentinel pairs
- `src/laptopfinder/scrape_live.py` — per-listing Firecrawl scrape to `data/feed_live/`; zero-results guard before live pipeline loop
- `scripts/render_matrix.py` — sorted Markdown purchase-decision table from manually assembled JSONL shortlist

---

# AU Market Alignment — Config Update (2026-07-01) — COMPLETE

**Why:** Gemma 2 9B telemetry proved 8 GB is critically insufficient (35 MB free RAM, 80 MB/s pageout). Gemini + Perplexity deep research mapped AU secondary/new market pricing and calibrated scoring rules. All findings propagated to config governance layer only — no Python changes.

**Status:** Complete 2026-07-01. 108 tests green (+1 recovered from pre-existing bug fix).

## Changes shipped

### `config/static_reference_layer.json`
- `target_gpus` — 3 new entries (RTX 3080 Observed_AU, RTX 4080, RTX 5070 Observed_AU); all 13 entries enriched with `platform_class`, `budget_band`, `evidence_type`, AU numeric price min/max
- `gpu_generation_by_name` — added RTX 3080/4080/5070/5090
- `watch_list` — RTX 5090 updated (Observed_AU, >7,500 AUD DEFER); RTX 5000 Ada Mobile HOLD; RTX PRO 5000 Blackwell Mobile DEFER added
- `egpu_enclosures` — added Razer Core X Chroma, Minisforum DEG2
- `target_models` — added ASUS ProArt P16, Lenovo Legion 7 Pro
- New top-level keys: `ram_floors` (32/64/96 GB from telemetry), `egpu_interconnect_penalty` (TB3/4 −3 pts, OCuLink/TB5 0 pts), `architecture_adjustments` (Turing vs Ada stub for Sprint 3)
- **Bug fix**: `standard_mobile_min_gb` corrected 12→16 — was breaking `test_12gb_no_touchscreen_skipped`

### `config/silicon_profiles.yaml`
- `discrete_cuda.architecture_tiers` — Turing (emulated FA, no FP8, −2 pts), Ada (native FA+FP8), Blackwell (native FA+FP8)
- `discrete_rocm` — `ecosystem_score: 15`, known S3/LM Studio/Ollama issues, `review_date: 2026-Q4`
- New top-level `egpu_interconnect` block — TB3/4 vs OCuLink vs TB5 bandwidth + penalty values
- `text_centric_llm_inference.ram_floors` — 32/64/96 GB derived from telemetry

## Sprint 3 (pending)
- Wire `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` into `decide.py` via `_apply_architecture_penalty()`
- Integrate `targets.json` storage spec (`storage_gb.min: 512`) into SRL
- Discovery prompt search term expansion — wire the 8 Boolean search strings from §8.1 of the July 2026 market topology report into the discovery prompt
- Prompt audit: grep `prompts/` for hardcoded VRAM/RAM thresholds that duplicate new config keys

---

# Secondary Market Topology Report Ingestion — 2026-07-01

**Why:** The July 2026 secondary market report (`Secondary-Market Hardware Topologies for Local Large Language Model Inference`) synthesised GRADUATE/HOLD/DEFER verdicts for all AU secondary market hardware, calibrated against the $3,000 AUD used / $5,000 AUD new budget bands and a 150 km Melbourne radius acquisition boundary.

**Status:** Complete 2026-07-01. Config-only changes — no Python touched. Tests should remain green.

## Key findings propagated to config

- **GRADUATE (primary targets):** RTX 3080 Mobile 16GB ($1,200–$2,000 AUD, Ampere SM86, native Flash Attention) and RTX 3080 Ti Mobile 16GB ($1,800–$2,500 AUD). Best VRAM-to-price ratio on AU secondary market.
- **HOLD (secondary/fallback):** RTX 4090 16GB ($3,500–$4,500 AUD), RTX A4500 16GB ($3,000–$4,000 AUD), RTX 5080 16GB (~$4,697 AUD Gigabyte A16 Pro clearance), RTX 4080 12GB ($2,200–$2,800 AUD, 12GB VRAM ceiling limits 13B viability).
- **DEFER (hard disqualifiers):** Quadro RTX 5000/6000 (Turing SM75, no native Flash Attention — hard architectural disqualifier), RX 6800M (RDNA2 ROCm volatile — kernel panics during sustained generation, no ExLlamaV2), RTX 5090 Mobile (>$7,500 AUD, 50%+ budget violation, graduation expected late 2028–2029).

## Changes shipped

### `config/static_reference_layer.json`
- `vram_tiers` — mid max_gb 16→23, high max_gb 24→31 (aligned to report's 4-tier hierarchy)
- `target_gpus.RTX 3080` — vram_gb corrected 12→16; prices $1,200–$2,000 AUD; market_verdict GRADUATE; architecture note added
- `target_gpus.RTX 3080 Ti` — prices $1,800–$2,500 AUD; evidence_type Observed_AU; budget_band used_3k; market_verdict GRADUATE
- `target_gpus.RTX 4080` — prices $2,200–$2,800 AUD; market_verdict HOLD; 12GB ceiling note
- `target_gpus.RTX 4090` — prices $3,500–$4,500 AUD; evidence_type Observed_AU; market_verdict HOLD
- `target_gpus.RTX 5080` — price updated to $4,500–$5,000 AUD; market_verdict HOLD; Gigabyte A16 Pro clearance note
- `target_gpus.RTX A4500` — prices $3,000–$4,000 AUD; evidence_type Observed_AU; market_verdict HOLD; enterprise premium note
- `target_gpus.Quadro RTX 5000` — market_verdict DEFER; architecture_note (Turing SM75, no Flash Attention)
- `target_gpus.Quadro RTX 6000` — market_verdict DEFER; architecture_note (Turing SM75)
- `radeon_mobile_gpus.RX 6800M` — added: vram_gb 12, architecture RDNA2, market_verdict DEFER, ROCm volatility note
- `watch_list[RTX 5090]` — reason enriched: 2028–2029 graduation timeline, confirmed $7,500+ AUD minimum

### `data/evidence/targets.json`
- `platform_classes[NVIDIA]` — added `architecture_minimum: "Ampere (SM86)"`, `throughput_target_tok_s: 25`, Turing DEFER rationale
- `platform_classes[AMD]` — added RDNA2/RDNA3 ecosystem differentiation in caveats

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
