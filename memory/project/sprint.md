---
name: alternative-silicon-sprint
description: Active sprint — June 2026 alternative-silicon scoring layer + pipeline audit
metadata:
  type: project
---

# eBay AU Active Sniper Setup — 2026-07-05 (COMPLETE — PENDING DAEMON LAUNCH)

**Why:** Batch runners (`ebay_hunter.py`) introduce email/LLM latency and token costs that miss underpriced "Buy It Now" private listings. To solve this, a lean, token-free background sniper (`scripts/ebay_sniper.py`) was implemented for instantaneous acquisition of high-VRAM/UMA hardware in AU, alerting via macOS iMessage.

**Status:** Complete (Stages 1–3). 174 tests green. Dry-run verified against live eBay API. Waiting for user sign-off to start background daemon via `make start-sniper` (Stage 4). Handover detailed in `handover.md` and `planning/laptopfinder-ebay-sniper-deep-plan.md`.

## Changes shipped
- `scripts/ebay_sniper.py` — Flat, Karpathy-compliant daemon with national flagship sweep (Strategy A) and local Melbourne algorithmic pricing sweep (Strategy B), HTTP 429 backoff / 401 token auto-refresh, and iMessage alerting.
- `Makefile` — Added `start-sniper`, `stop-sniper`, `status-sniper`, `test-sniper-alert`.
- `tests/test_ebay_sniper.py` — 3 new test functions covering title normalization, data integrity firewall regex, and local SRL price floor logic.
- `docs/ebay_sniper.md` — Usage instructions, configuration constraints, and dry-run verification logs.
- `data/ebay_api_strategy_ideas.json` — 4 concrete API strategy ideas (sold price baselines, feed API pre-caching, local pickup postal gating, and deal clearance monitoring).

---

# Sprint 7 — eBay Browse & Developer API Discovery Expansion — 2026-07-06 (MOSTLY COMPLETE)

**Why:** Extract more value from the eBay Browse API for AU high-VRAM/UMA discovery near Melbourne.

**Status:** Batches A and B complete and pushed. Batch C (Marketplace Insights) blocked on human D1 (OAuth scope request). eBay API runners plus the sniper are the primary live-discovery path. 193 tests green.

## Shipped (2026-07-06)
- `src/laptopfinder/ebay_taxonomy.py` — `build_aspect_filter` / `ebay_category_id` helpers extracted from hunter
- `src/laptopfinder/runners/ebay_hunter.py` — taxonomy-driven `aspect_filter`, seller-scoped watch queries, category id unified to 175672
- `src/laptopfinder/runners/ebay_deals.py` — Deal API clearance runner; scans `clearance_sellers` (SRL) for 64GB+ UMA units; `make scan-deals`
- `scripts/ebay_feed_cache.py` — Feed API pre-cacher; JSONL snapshots in `data/feed_cache/`; `make cache-feed`
- `scripts/ebay_sold_baseline.py` — Finding API `findCompletedItems`; AU sold price medians per GPU keyword → `data/sold_baseline/`; `make sold-baseline` (uses `EBAY_APP_ID`, no extra OAuth scope)
- `pyproject.toml` — `pythonpath=["."]` so `scripts.*` imports resolve in pytest
- `config/static_reference_layer.json` — `clearance_sellers`, `aspect_filter` config, `seller_watch_queries`, `category_id`

### Sprint 7 Backlog (minor, non-blocking)
- [ ] Move `PRICE_MIN_AUD`/`PRICE_MAX_AUD` defaults from `ebay_deals.py` env vars into SRL.
- [ ] Add `json.JSONDecodeError` guard in `load_feed_cache` for truncated JSONL files.
- [ ] Note: `fetch_feed_snapshot` in `ebay_feed_cache.py` assumes JSON response — eBay Feed API actually delivers gzip TSV. Needs rework once `buy.feed` scope granted.
- [ ] Implement `batch_decide()` as documented in CLAUDE.md to enable multi-listing scoring and processing.

## Blocked / Next
- `[ ]` **D1 (HUMAN):** Open an **eBay Dev Support ticket** to enable `buy.marketplace.insights` on the app — it's a restricted/limited-release API, not self-service in the developer portal. Unblocks Batch C (Task 6 in plan).
- `[ ]` **D2 (IDE/DEV, blocked on D1):** Marketplace Insights runner — `data/ebay_api_strategy_ideas.json` E3
- `[ ]` **Sprint 7 live validation** — `ebay_hunter --dry-run` populates corpus/SHORTLIST counts (human-gated, needs live API keys)


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

## Sprint 2 — Config Injection, Live Scraping, Decision Matrix (2026-07) — COMPLETE

**Goal:** Wire three new pipeline components to make the system data-driven and operationally self-sufficient.
**Status:** Complete. Verified 2026-07-16: `scripts/inject_config.py` and `scripts/render_matrix.py` present and in active use. `src/laptopfinder/scrape_live.py` no longer exists — Firecrawl live-fetch was superseded by the eBay Developer API path (see Sprint 5 CANCELLED below); its removal is expected, not a regression.

Deliverables:
- `scripts/inject_config.py` — idempotent marker-based injection of SRL values into prompt sentinel pairs
- `scripts/render_matrix.py` — sorted Markdown purchase-decision table from manually assembled JSONL shortlist
- (superseded) `src/laptopfinder/scrape_live.py` — per-listing Firecrawl scrape; replaced by eBay Browse API runners

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

## Sprint 3 — Prompt Hygiene + eGPU Scoring (2026-07) — COMPLETE

**Why:** Close the UMA discovery gap, wire the eGPU interconnect penalty, and put all hardcoded thresholds in prompts under `inject_config` control.
**Status:** Complete. Verified 2026-07-16: `_apply_egpu_interconnect_penalty()` implemented and wired into `calculate_llm_index_score()` in `decide.py`.

## Changes shipped
- Fixed UMA RAM threshold in `prompts/comet_discovery_agent.txt` (64GB+ → 32GB+); added inject_config sentinel pairs around UMA RAM floor and VRAM thresholds
- `_apply_egpu_interconnect_penalty(analysis, ref)` added to `decide.py`, with TB3/4 penalty, OCuLink zero-penalty, and `system_ram_gb ≥ 32` zero-penalty override tests in `test_decide.py`
- Grepped `prompts/` for hardcoded VRAM/RAM values — all hits resolved (done, prose, telemetry, or clean)

*(Note: the architecture-penalty wiring listed under the original Sprint 3 draft above was actually delivered as part of Sprint 6 — see below — via `_apply_architecture_penalty()`, a distinct function from the eGPU interconnect penalty.)*

---

## Sprint 4 — Light Fixture Collection: eBay AU + Gumtree, FB Marketplace minimal — COMPLETE

**Why:** Obtain a small set of high-quality real-world fixtures for eBay AU and Gumtree, confirm extractors work at a basic level, and establish a Chrome data-export → pipeline converter for eBay batch collection.
**Status:** Complete. Full task-by-task checklist archived in `TASKS.md` git history (pre-2026-07-16 consolidation) if step-level detail is ever needed.

## Changes shipped
- `scripts/ebay_export_to_jsonl.py` — converts Chrome data-export JSON/CSV into the `scrape_benchmark.py` raw-record shape
- `extract_ebay()` / `extract_gumtree()` CSS/regex selectors in `scrape_benchmark.py` patched against real saved-page fixtures
- `extract_facebook()` fallback path verified against a real saved FB Marketplace page (discovery-only scope, no full parity)
- 108+ tests green

---

## Sprint 5 — Firecrawl Live Wiring + batch_decide — CANCELLED

**Why cancelled:** Firecrawl was replaced by the eBay Developer API as the live-discovery path (see Sprint 7 below); the planned `fetch_live_firecrawl()` / `make benchmark-live` / `make benchmark-to-feed` wiring was never built for that reason.
**Status:** Cancelled 2026-07. The `batch_decide()` sub-task originally scoped under this sprint remains open — tracked in `TASKS.md` BACKLOG, not implemented as of 2026-07-16.

---

## Sprint 6 — Architecture Penalty + eBay-First End-to-End Validation

**Why:** Resolve the architecture penalty stub as a per-listing heuristic, run a full end-to-end live pass on eBay AU, capture any runtime failures as fixtures, and produce a plausible purchase matrix.
**Status:** Architecture Penalty sub-section complete (2026-07-03). End-to-End Live Validation remains open — requires real eBay AU URLs and valid API keys not available in the automated session that implemented the penalty. Tracked as open Human Runbook items in `TASKS.md`.

## Changes shipped
- `_apply_architecture_penalty(gpu, tier, ref)` in `decide.py` — reads `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` from SRL; resolves Turing generation via the shared `_resolve_gpu_generation()` helper (extracted from `_gpu_generation_points()`); wired into `calculate_llm_index_score()`
- Tests: `test_turing_gpu_receives_architecture_penalty`, `test_ada_gpu_receives_no_architecture_penalty`, `TestArchitecturePenaltyIntegration::test_turing_gpu_scores_lower_than_equivalent_ada_gpu`, plus null/unrecognized-GPU edge cases — 183 tests green (up from 180)
- CLAUDE.md invariants updated: `_apply_architecture_penalty()` documented as a per-listing Turing heuristic, not a pairwise comparator

**Still open (End-to-End Live Validation):** live eBay AU sweep via `ebay_hunter`, purchase matrix render + plausibility check, `make scan-gaps` run — see `TASKS.md` Human Runbook.

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

**Status:** Complete. Verified 2026-07-16: RTX 3080/4080/5070 confirmed present in `config/static_reference_layer.json` `target_gpus`.

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
- [x] Config JSON fragments drafted and reviewed
- [x] `make test` still green after any SRL changes
- [x] Market gap findings documented (folded into `research/alternative_silicon_dossier_july2026.md` rather than a standalone `deep_research_output.md`)

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
- [x] **Paste `data/evidence/claude_handoff.txt` into Claude Pro and save corrected `targets.json`** — current file contains pre-correction interpretive language and must be replaced before feeding into the main pipeline
- [x] Integrate corrected `targets.json` spec ranges into `config/static_reference_layer.json`
- [x] Confirm `make test` stays green

## Definition of Done
- [x] `targets.json` validated against `evidence_targets.schema.json`
- [x] Gemini parser converted from API stub to manual prompt generator
- [x] Pipeline prompt constraints enforced (corrective task applied)
- [x] `make evidence-reset` available for clean restarts
- [x] Prompt staleness check in place
- [x] Corrected `targets.json` generated from updated Claude prompt
- [x] Spec ranges reflected in `static_reference_layer.json`
- [x] `make test` still green

---

# Sprint 8 — Hardening Closeout & Daemon Reliability (Active)

**Why:** Close real hardening backlog; make `make live` reliable unattended.

**Status:** In Progress.

## Tasks
- [x] **S8-01:** Fix `docs/ebay_sniper.md` — drop nonexistent daemon targets, document real `make live`. *(docs/ebay_sniper.md)*
- [x] **S8-02:** Pick one unattended-run method for `make live` (nohup+log vs launchd vs tmux) and document it. *(docs/ebay_sniper.md, Makefile)*
- [ ] **S8-03:** `ingest_csv.py` — raise `ValueError` on missing required CSV columns at open time. *(src/laptopfinder/ingest_csv.py, tests/test_ingest_csv.py)*
- [ ] **S8-04:** Dedupe `_log_undiscovered_hardware` by `listing_id` before append — check `data/evidence/undiscovered_hardware.jsonl` local diff first (uncommitted changes present).
- [ ] **S8-05:** Add screen-size regex fallback `\b(14|15|16|17|18)["″]`. *(scripts/build_shortlist_value.py)*
- [ ] **S8-06:** Add `tests/test_build_shortlist_value.py` (only pipeline script with no coverage).
- [ ] **S8-07:** Add fallback aspect-name lookup via `ebay_taxonomy.py` when hardcoded aspect matches fail. *(src/laptopfinder/runners/legacy/ebay_hunter.py)*
- [ ] **S8-08:** Confirm/add `risk_score == 3.0` boundary test. *(tests/test_decide.py)*
- [ ] **S8-09:** Confirm/add "reference only" header comment. *(config/silicon_profiles.yaml)*

---

# Perplexity Web MCP — Installed & Active (2026-07-16)

**Why:** `pwm doctor` verification confirmed the tool underlying `docs/pwm_workflow_catalog.md` is not hypothetical.

**Status:** `perplexity-web-mcp-cli` v0.14.2 confirmed installed and authenticated (Pro subscription, active). MCP server configured for both `claude-code` and `antigravity` clients. Agent Skills refreshed to v0.14.2 across claude-code, codex, gemini-cli, antigravity (were v0.12.2). Prior "Phantom MCP Setup" language in `planning/pvm_mcp_execution_audit.md` is stale as of this date.

---

# Sprint 9 — PWM Workflow Implementation (COMPLETE)

**Why:** Implement the local scaffolding and data preparation scripts required to execute the PWM Deep Research workflows defined in the catalog.

**Status:** Complete. `lf-floor-sync` and `lf-price-baseline` local scripts written and verified.

## Tasks
- [x] **S9-01:** `lf-floor-sync`: `scripts/lf_floor_sync.py` normalizes `data/hunt_results.jsonl` (written by `make hunt CONFIG=...`, not `output/decisions/` — that path belongs to `make live` only, see CLAUDE.md) into `data/lf-floor-listings.csv`. 4 tests in `tests/test_lf_floor_sync.py`. No dedicated `config/runs/lf-floor.json` exists yet — the script normalizes whatever `hunt_results.jsonl` a human produces from any `make hunt` run; a floor-specific run config is a separate open item.
- [x] **S9-02:** `lf-price-baseline`: Write local script to merge candidate listings and historical data into `data/lf-price-baseline.csv`.

---

# Sprint 10 — Platform-Agnostic Integration & Refactoring (PENDING)

**Why:** Transition `laptopfinder` from an eBay-coupled scoring script to a clean Platform-Agnostic, Multi-Vendor Decision Engine as outlined in `docs/handover.md`. This will unify the scoring rule mathematical boundaries, vendor risk profile parameters, and missing-data recovery logic across all platforms.

**Status:** Pending.

## Tasks
- [ ] **S10-00 (Phase 1):** Execute peer review, audit, critique, and flag gaps of the new scoring rules and workflows defined in [handover.md](file:///Users/okgoogle13/Projects/laptopfinder/docs/handover.md).
- [ ] **S10-01 (Phase 1):** Clean up obsolete `scripts/ebay_sniper.py` duplicate file and ensure `Makefile` targets reference `src/laptopfinder/runners/ebay_sniper.py`.
- [ ] **S10-02 (Phase 2):** Refactor `src/laptopfinder/decide.py` to ingest `Listing` instances and load unified `static_scoring_rules.json` and `lf-vendor-risk.json` parameters.
- [ ] **S10-03 (Phase 3):** Migrate `src/laptopfinder/runners/ebay_sniper.py` and `src/laptopfinder/ingest_csv.py` to wrap raw listings in adapters before decision scoring.
- [ ] **S10-04 (Phase 4):** Align `scripts/render_matrix.py` and `scripts/build_shortlist_value.py` to render unified multi-vendor columns and rank via `score_0_100`.
- [ ] **S10-05:** Update status dashboard counts in `scripts/status_snapshot.py` to report across watchlist and sniper outputs.
- [ ] **S10-06:** Verify validation suite passes 264+ tests cleanly and confirm dry-run sweeps function without regression.
- [ ] **S10-07 (Phase 3):** Create watchlist hunt run config at `config/runs/watchlist_hunt.json` declaring `"source": "watchlist"`.
- [ ] **S10-08 (Phase 3):** Refactor `collect_corpus` in `src/laptopfinder/runners/legacy/hunter/search.py` to support watchlist loading via `tools.ebay_watchlist_snapshot`.
- [ ] **S10-09 (Phase 3):** Refactor `src/laptopfinder/runners/legacy/ebay_hunter.py` to route output paths dynamically for watchlist sweeps.
- [ ] **S10-10 (Phase 3):** Update Makefile to link `ebay-watchlist-snapshot` target to consolidated `make hunt CONFIG=config/runs/watchlist_hunt.json` flow.
- [ ] **S10-11 (Phase 3):** Deprecate and delete obsolete `scripts/score_active_watchlist.py`.
- [ ] **S10-12 (Phase 3):** Verify complete test suite coverage and perform live dry-run of watchlist hunter.
