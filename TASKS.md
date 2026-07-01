# TASKS — laptopfinder
## Status key: [ ] pending · [~] in progress · [x] done

---

## COMPLETE: Alternative-Silicon Scoring Layer (2026-06-30)

- [x] A1: Create `config/silicon_profiles.yaml` — paradigm definitions + workload preferences
- [x] A2: Create `config/scoring_weights.yaml` — per-workload weight profiles
- [x] A3: Create `data/hardware_taxonomy.json` — 4 representative hardware entries
- [x] A4: Create `prompts/system_context.md` — agent paradigm-first instructions
- [x] A5: Create `prompts/bias_guard_prompt.md` — bias self-check rubric
- [x] A6: Create `research/alternative_silicon_dossier_june2026.md` — synthesised research
- [x] A7: Modify `decide.py` — Paradigm type, `_classify_paradigm`, `load_scoring_weights`, `score_text_llm_candidate`, `workload` param, UMA ceiling removed
- [x] A8: Modify `config/static_reference_layer.json` — `score_ceiling: null`, policy comments
- [x] A10: Update `tests/test_decide.py` (2 ceiling tests fixed + 3 new classes) + create `tests/test_prompts.py`
- [x] D1: Update `CLAUDE.md` / `AGENTS.md` — architecture + invariants
- [x] D2: Update `memory/project/sprint.md`
- [x] D3: Update `TASKS.md`

**A9 (targets.json integration) blocked on human gate — see Evidence Pipeline below.**

---

## ACTIVE: Evidence-Based Target Pipeline (June 2026)

**Goal:** Collect macOS telemetry, normalize it, and produce `targets.json` via a manual Claude Pro handoff — then feed those targets into the main pipeline.

### Setup (done)
- [x] Create `data/evidence/raw`, `archive`, `aggregated.jsonl`
- [x] Write `src/laptopfinder/schemas/evidence_normalized.schema.json`
- [x] Write `src/laptopfinder/schemas/evidence_targets.schema.json`
- [x] Write `prompts/gemini_evidence_parser.txt`
- [x] Write `prompts/claude_evidence_analyzer.txt`
- [x] Write `src/laptopfinder/runners/evidence_pipeline.py` (prompt generator + handoff generator)
- [x] Add `evidence-run` / `evidence-run-dry` / `evidence-reset` targets to Makefile
- [x] Verify: `py_compile`, `__init__.py`, Makefile grep, dry-run empty-dir all pass

### Collect Evidence (done — 23 logs archived)
- [x] Drop ≥5 telemetry files into `data/evidence/raw`
- [x] Generate Gemini prompts via `make evidence-run`
- [x] Parse all 23 archive logs locally (no API) → saved to `data/evidence/parsed/`
- [x] Run `make evidence-run` to append 23 records to `aggregated.jsonl` and archive parsed JSONs
- [x] Confirm `claude_handoff.txt` was generated in `data/evidence/`

### Claude Pro Handoff (partially done — targets.json is STALE)
- [x] `claude_handoff.txt` generated with corrected `claude_evidence_analyzer.txt` prompt
- [ ] **PENDING: Paste current `data/evidence/claude_handoff.txt` into Claude Pro**
- [ ] **PENDING: Save Claude's JSON response as `data/evidence/targets.json` (current file is pre-correction)**
- [ ] **PENDING: Validate new `targets.json` against `evidence_targets.schema.json`**

### Pipeline improvements (done this session — 2026-06-30)
- [x] Corrected `prompts/gemini_evidence_parser.txt` — added CONTEXT/PAST FAILURES, HARD CONSTRAINTS, QUALITY CHECK, PIPELINE CLARIFICATION, SUMMARY blocks to enforce parse-only role
- [x] Corrected `prompts/claude_evidence_analyzer.txt` — removed banned language (`bottleneck`, `contention`, `under strain`); replaced with neutral observational phrasing
- [x] Added `make evidence-reset` (`--reset` flag): truncates `aggregated.jsonl` + removes `.claude_prompt.hash` sidecar for clean restarts
- [x] Added prompt staleness check: `generate_claude_handoff()` hashes `claude_evidence_analyzer.txt` and warns if the handoff embeds a stale version of the prompt
- [x] Deleted `normalize_archive.py` — one-off workaround; canonical path is `raw/ → make evidence-run → prompts_for_gemini/ → parsed/ → make evidence-run`

### Telemetry (2026-07-01)
- [x] 2026-07-01: Gemma 2B/9B telemetry captured; 32 GB floor, 64 GB recommended RAM, 12–16 GB VRAM confirmed.

### Claude Pro Handoff (2026-07-01)
- [x] Paste `claude_handoff.txt` into Claude Pro; `targets.json` saved (min 32 GB RAM, min 12 GB VRAM, min 512 GB storage)
- [x] `ram_floors` and VRAM thresholds reflected in `config/static_reference_layer.json` (2026-07-01)
- [x] Integrate `storage_gb` spec from `targets.json` into SRL — `storage_floors` block at SRL:366 (min_gb: 512, recommended_gb: 1024)
- [x] `make test` green after storage integration

---

## COMPLETE: AU Market Alignment — Config Update (2026-07-01)

**Source:** Gemini Deep Research + Perplexity AU secondary market mapping (July 2026) + Gemma 2 telemetry.

- [x] `config/static_reference_layer.json` — added RTX 3080 (Observed_AU), RTX 4080, RTX 5070 to `target_gpus`
- [x] `config/static_reference_layer.json` — enriched all 13 `target_gpus` entries with `platform_class`, `budget_band`, `evidence_type`, and AU price ranges where observed
- [x] `config/static_reference_layer.json` — added RTX 3080/4080/5070/5090 to `gpu_generation_by_name`
- [x] `config/static_reference_layer.json` — watch_list: updated RTX 5090 (evidence_type Observed_AU); added RTX 5000 Ada Mobile (HOLD) and RTX PRO 5000 Blackwell Mobile (DEFER)
- [x] `config/static_reference_layer.json` — `egpu_enclosures`: added Razer Core X Chroma and Minisforum DEG2
- [x] `config/static_reference_layer.json` — `target_models`: added ASUS ProArt P16 and Lenovo Legion 7 Pro
- [x] `config/static_reference_layer.json` — added top-level `ram_floors`, `egpu_interconnect_penalty`, `architecture_adjustments` blocks
- [x] `config/static_reference_layer.json` — **bug fix**: `standard_mobile_min_gb` corrected 12→16 (test contract + CLAUDE.md logic; test count restored to 108)
- [x] `config/silicon_profiles.yaml` — `discrete_cuda`: added `architecture_tiers` (Turing/Ada/Blackwell annotations)
- [x] `config/silicon_profiles.yaml` — `discrete_rocm`: added `ecosystem_score: 15` + known S3/LM Studio/Ollama issues + review condition
- [x] `config/silicon_profiles.yaml` — new top-level `egpu_interconnect` block (TB3/4 −3 pts, OCuLink/TB5 0 pts)
- [x] `config/silicon_profiles.yaml` — `text_centric_llm_inference`: added `ram_floors` sub-key from telemetry
- [x] 108 tests green

**Sprint 3 stub (architecture_adjustments not yet wired):**
- [ ] Wire `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` into `decide.py` via `_apply_architecture_penalty()` — currently a documented no-op stub (pairwise comparison context required; see docstring)

---

## ACTIVE: Pipeline Audit (June–July 2026)

**Goal:** Validate and expand the pipeline's hardware coverage based on what's actually appearing on AU used markets.

### Market Gap Analysis (done 2026-07-01)
- [x] Identify high-VRAM GPUs appearing on used markets but absent from target lists → RTX 3080, RTX 4080, RTX 5070 added
- [x] Identify laptop/workstation models absent from target_models → ASUS ProArt P16, Lenovo Legion 7 Pro added
- [x] Check watch list graduation for RTX 5080 & 5090 → 5090 updated Observed_AU/DEFER (>7,500 AUD); RTX 5000 Ada Mobile HOLD added
- [x] Identify new UMA platforms → Mac mini M4 (24 GB) and M4 Pro (48 GB) mapped; chassis remain out-of-scope for SRL (desktop consumer)

### Secondary Market Topology Report Ingestion (done 2026-07-01)
**Source:** `research/Secondary-Market Hardware Topologies for Local Large Language Model Inference (July 2026).md`
- [x] Ingest GRADUATE/HOLD/DEFER verdicts across all evaluated AU market hardware
- [x] `config/static_reference_layer.json` — RTX 3080 vram_gb corrected 12→16 (16GB is the graduation target variant); prices updated $1,200–$2,000 AUD Observed_AU
- [x] `config/static_reference_layer.json` — RTX 3080 Ti prices added $1,800–$2,500 AUD, evidence_type → Observed_AU, budget_band → used_3k
- [x] `config/static_reference_layer.json` — RTX 4090 and RTX 4080 prices updated (Observed_AU); market_verdict HOLD with notes on VRAM-to-price ratio
- [x] `config/static_reference_layer.json` — RTX A4500 prices added ($3,000–$4,000 AUD); HOLD — enterprise premium disqualifies vs RTX 3080 16GB
- [x] `config/static_reference_layer.json` — RTX 5080 market_verdict HOLD; price range updated to reflect Gigabyte A16 Pro clearance (~$4,697 AUD)
- [x] `config/static_reference_layer.json` — Quadro RTX 5000 and RTX 6000 marked DEFER; architecture_note added (Turing SM75, no native Flash Attention)
- [x] `config/static_reference_layer.json` — `vram_tiers` updated: mid max_gb 16→23, high max_gb 24→31 (aligned to report tier hierarchy)
- [x] `config/static_reference_layer.json` — `radeon_mobile_gpus`: added RX 6800M (vram_gb: 12, DEFER, RDNA2 ROCm volatility note)
- [x] `config/static_reference_layer.json` — RTX 5090 watch_list reason enriched with 2028–2029 graduation timeline and confirmed budget violation
- [x] `data/evidence/targets.json` — NVIDIA platform class: added architecture_minimum (Ampere SM86), throughput_target_tok_s: 25, Turing DEFER rationale
- [x] `data/evidence/targets.json` — AMD platform class: RDNA2/RDNA3 ecosystem notes added

### Spec Comparison (addressed by market report 2026-07-01)
- [x] Top tier: RTX 3080 16GB ($1,200–$2,000 AUD, 25+ tok/s 13B Q4) vs RTX 3080 Ti 16GB ($1,800–$2,500 AUD) — both GRADUATE
- [x] Mid tier HOLD: RTX 4090 16GB ($3,500–$4,500 AUD), RTX A4500 16GB ($3,000–$4,000 AUD), RTX 5080 16GB (~$4,697 AUD clearance)
- [x] Floor tier HOLD: RTX 4080 12GB ($2,200–$2,800 AUD) — 12GB VRAM ceiling limits 13B model viability
- [x] DEFER: Quadro RTX 5000/6000 (Turing, no Flash Attention), RX 6800M (RDNA2 ROCm volatile), RTX 5090 (>$7,500 AUD)

### Pipeline Enhancements (done 2026-07-01)
- [x] Config JSON fragments for `target_gpus`, `target_models`, `egpu_enclosures`, `watch_list` — applied
- [x] RDNA3/ROCm ecosystem score held at 15; Turing gen-points gap (5 vs Ada 20) documented
- [x] Identify 5–10 high-value search terms/variants for the discovery prompt — 8 Boolean strings wired into `prompts/comet_discovery_agent.txt:37-44`
- [x] Document 1–3 systematic blind spots — documented in `CLAUDE.md` (RAM/VRAM conflation, mislabelled eGPU bundles, niche workstation imports)

---

## ACTIVE: Sprint 3 — Prompt Hygiene + eGPU Scoring (2026-07)

**Goal:** Close the UMA discovery gap, wire the eGPU interconnect penalty, and put all hardcoded thresholds in prompts under inject_config control.

### Discovery Threshold Fix
- [ ] S3-01: Fix UMA RAM threshold in `prompts/comet_discovery_agent.txt` (currently `64GB+` — must be `32GB+` to match `uma_unified_min_gb` in SRL)
- [ ] S3-01: Add inject_config sentinel pairs around UMA RAM floor, VRAM thresholds in the discovery prompt so `inject_config.py` keeps them in sync with SRL

### eGPU Interconnect Penalty
- [ ] S3-02: Add `_apply_egpu_interconnect_penalty(analysis, ref)` to `decide.py` — reads `egpu_interconnect_penalty` from SRL, applies −3 pts for TB3/4 when eGPU bundle detected; 0 for OCuLink/TB5 or system_ram_gb ≥ 32
- [ ] S3-02: Add tests in `test_decide.py` for TB3/4 penalty, OCuLink zero-penalty, and system_ram_gb ≥ 32 zero-penalty override

### Prompt Audit
- [ ] S3-03: Grep `prompts/` for hardcoded VRAM/RAM values (`16`, `12`, `32`, `64`, `512`) — add sentinel pairs for any that duplicate SRL config keys
- [ ] S3-03: `make test` green after sentinel pair additions

---

## COMPLETE: Sprint 2 — Config Injection, Live Scraping, Decision Matrix (2026-07)

**Plan:** `planning/claude-plan.md` · **Sections:** `planning/sections/`

### Prerequisites
- [x] S2-01: Create `scripts/` directory (`.gitkeep`)
- [x] S2-02: `uv add firecrawl-py` (pinned); add `FIRECRAWL_API_KEY` to `.env.example`
- [x] S2-03: Update `.gitignore` — add `data/feed_live/`, `data/purchase_matrix.md`
- [x] S2-04: Add sentinel marker pairs to 3 prompt files (one-time manual edit per section-01)

### Components
- [x] S2-05: Write + test `scripts/inject_config.py` (`load_srl`, `build_substitutions`, `inject_file`, `main`)
- [x] S2-06: Write + test `src/laptopfinder/scrape_live.py` (`read_urls`, `strip_nav`, `normalise_md`, `fetch_markdown`, `main`)
- [x] S2-07: Write + test `scripts/render_matrix.py` (`load_candidates`, `sort_candidates`, `render_table`, `main`)
- [x] S2-08: Add `tests/test_prompt_markers.py` — asserts real prompt files contain sentinel pairs

### Integration
- [x] S2-09: Add `inject-config`, `scrape-and-live` (with zero-results guard), `render-matrix` Makefile targets
- [x] S2-10: Create `data/urls.txt` sample file
- [x] S2-11: `make test` — all new and existing tests pass (49 Sprint 2 tests green)

---

## BACKLOG

- [ ] Playwright-based scraper for live eBay fetching (eBay blocks simple requests)
- [ ] FB Marketplace: evaluate JSON-LD availability in "Save Page As" vs DevTools intercept
- [ ] Gumtree: verify `price-amount` selector against a real saved page
- [ ] Wire `scrape_benchmark.py` output directly into `make live`
