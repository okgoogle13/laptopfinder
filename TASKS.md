# TASKS — laptopfinder
> **NOTICE**: This document serves as a historical archive and high-level backlog. For active sprint tracking, please refer to `memory/project/sprint.md`.

## Status key: [ ] pending · [~] in progress · [x] done

---

## Codebase Status Snapshot (2026-07-06)

**Sprint completion state:** Sprints 1–6 are complete. Evidence Pipeline and AU Market Alignment are shipped. Sprint 7 (eBay API Discovery Expansion) is active and mostly complete.
**Sprint 7 status (2026-07-06):** Batches A and B are complete and pushed. Batch C (Marketplace Insights) is blocked on human D1 (OAuth scope request). eBay API runners plus the sniper are the primary live-discovery path.

**Remaining work:**
- Five backlog items had no sprint assignments, tags, or testing guidance.
- `_apply_architecture_penalty()` is fully implemented in `decide.py` and wired into the scoring logic as of Sprint 6.
- `scrape_benchmark.py` has extractors for EBAY_AU, FB_MARKETPLACE, GUMTREE with best-guess CSS/JSON selectors — none validated against real saved pages.
- Firecrawl / `scrape_live.py` / `make scrape-and-live` are historical references only; eBay API runners plus the sniper are the primary live-discovery path.

**Platform priority:** eBay AU is the primary target for all remaining sprints. eBay API runners plus the sniper are primary. Gumtree AU is secondary/opportunistic. Facebook Marketplace is deferred to discovery-only; no full scraping parity.

**Tooling constraint:** No Playwright or Browserbase introduced in this roadmap. Legacy Firecrawl references are historical. Manual batch export via Chrome data-export extensions (Instant Data Scraper / Web Scraper / Data Miner) remains the fallback for eBay search-results batches.

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

**A9 (targets.json integration) completed in Evidence Pipeline below.**

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

### Claude Pro Handoff (done 2026-07-01)
- [x] `claude_handoff.txt` generated with corrected `claude_evidence_analyzer.txt` prompt
- [x] Paste current `data/evidence/claude_handoff.txt` into Claude Pro
- [x] Save Claude's JSON response as `data/evidence/targets.json`
- [x] Validate `targets.json` against `evidence_targets.schema.json`

### Pipeline improvements (done 2026-06-30)
- [x] Corrected `prompts/gemini_evidence_parser.txt`
- [x] Corrected `prompts/claude_evidence_analyzer.txt` — removed banned language
- [x] Added `make evidence-reset`
- [x] Added prompt staleness check in `generate_claude_handoff()`
- [x] Deleted `normalize_archive.py`

### Telemetry + config integration (done 2026-07-01)
- [x] Gemma 2B/9B telemetry captured; 32 GB floor, 64 GB recommended RAM, 12–16 GB VRAM confirmed
- [x] `ram_floors` and VRAM thresholds reflected in `config/static_reference_layer.json`
- [x] `storage_floors` block integrated into SRL (min_gb: 512, recommended_gb: 1024)
- [x] `make test` green after storage integration

---

## COMPLETE: AU Market Alignment — Config Update (2026-07-01)

- [x] `config/static_reference_layer.json` — added RTX 3080 (Observed_AU), RTX 4080, RTX 5070 to `target_gpus`
- [x] `config/static_reference_layer.json` — enriched all 13 `target_gpus` entries with `platform_class`, `budget_band`, `evidence_type`, and AU price ranges
- [x] `config/static_reference_layer.json` — added RTX 3080/4080/5070/5090 to `gpu_generation_by_name`
- [x] `config/static_reference_layer.json` — watch_list: updated RTX 5090; added RTX 5000 Ada Mobile HOLD and RTX PRO 5000 Blackwell Mobile DEFER
- [x] `config/static_reference_layer.json` — `egpu_enclosures`: added Razer Core X Chroma and Minisforum DEG2
- [x] `config/static_reference_layer.json` — `target_models`: added ASUS ProArt P16 and Lenovo Legion 7 Pro
- [x] `config/static_reference_layer.json` — added top-level `ram_floors`, `egpu_interconnect_penalty`, `architecture_adjustments` blocks
- [x] `config/static_reference_layer.json` — **bug fix**: `standard_mobile_min_gb` corrected 12→16
- [x] `config/silicon_profiles.yaml` — `discrete_cuda`: added `architecture_tiers` (Turing/Ada/Blackwell)
- [x] `config/silicon_profiles.yaml` — `discrete_rocm`: added `ecosystem_score: 15` + known issues
- [x] `config/silicon_profiles.yaml` — new top-level `egpu_interconnect` block
- [x] `config/silicon_profiles.yaml` — `text_centric_llm_inference`: added `ram_floors` sub-key
- [x] 108 tests green

---

## COMPLETE: Pipeline Audit (June–July 2026)

- [x] Identify high-VRAM GPUs on AU market absent from target lists → RTX 3080, 4080, 5070 added
- [x] Identify laptop/workstation models absent from target_models → ASUS ProArt P16, Lenovo Legion 7 Pro added
- [x] Check watch list graduation for RTX 5080 & 5090
- [x] Identify new UMA platforms → Mac mini M4 mapped; desktop chassis out-of-scope for SRL
- [x] Secondary Market Topology Report ingested; GRADUATE/HOLD/DEFER verdicts propagated to SRL
- [x] 8 Boolean search strings extracted to `prompts/search_queries.txt`; `comet_discovery_agent.txt` references by pointer
- [x] 3 systematic blind spots documented in CLAUDE.md

---

## COMPLETE: Sprint 3 — Prompt Hygiene + eGPU Scoring (2026-07)

**Goal:** Close the UMA discovery gap, wire the eGPU interconnect penalty, and put all hardcoded thresholds in prompts under inject_config control.

- [x] S3-01: Fix UMA RAM threshold in `prompts/comet_discovery_agent.txt` (64GB+ → 32GB+)
- [x] S3-01: Add inject_config sentinel pairs around UMA RAM floor, VRAM thresholds
- [x] S3-02: Add `_apply_egpu_interconnect_penalty(analysis, ref)` to `decide.py`
- [x] S3-02: Tests added in `test_decide.py` for TB3/4 penalty, OCuLink zero-penalty, system_ram_gb ≥ 32 zero-penalty override
- [x] S3-03: Grep `prompts/` for hardcoded VRAM/RAM values — all hits are DONE, PROSE, TELEMETRY, or CLEAN

---

## COMPLETE: Sprint 2 — Config Injection, Live Scraping, Decision Matrix (2026-07)

- [x] S2-01: Create `scripts/` directory
- [x] S2-02: `uv add firecrawl-py`; add `FIRECRAWL_API_KEY` to `.env.example`
- [x] S2-03: Update `.gitignore`
- [x] S2-04: Add sentinel marker pairs to 3 prompt files
- [x] S2-05: Write + test `scripts/inject_config.py`
- [x] S2-06: Write + test `src/laptopfinder/scrape_live.py`
- [x] S2-07: Write + test `scripts/render_matrix.py`
- [x] S2-08: Add `tests/test_prompt_markers.py`
- [x] S2-09: Add `inject-config`, `scrape-and-live`, `render-matrix` Makefile targets
- [x] S2-10: Create `data/urls.txt` sample file
- [x] S2-11: `make test` — all tests pass

---

## Sprint 4 — Light Fixture Collection: eBay AU + Gumtree (primary), FB Marketplace (minimal)

**Goal:** Obtain a small set of high-quality real-world fixtures for eBay AU and Gumtree, confirm extractors work at a basic level, and establish a Chrome data-export → pipeline converter for eBay batch collection. Tests remain lean and directly protective.

### eBay AU — Chrome Export → Converter Script

- `[x]` `[HUMAN]` Open an eBay AU laptop search results page in Chrome. Use Instant Data Scraper, Web Scraper, or Data Miner to export a batch of listings as JSON or CSV. Target fields: title, listing URL, price text, and condition. Save the export to `data/fixtures/ebay_export_raw.json` (or `.csv`).
- `[x]` `[IDE/DEV]` Write `scripts/ebay_export_to_jsonl.py`: reads the Chrome-extension JSON/CSV export, maps fields to the `scrape_benchmark.py` raw-record shape (`title`, `price_raw`, `url`, `seller_name: null`, `seller_rating: null`, `full_listing_text: <title + price stub>`), writes to `data/fixtures/ebay_export.jsonl`.
- `[x]` `[IDE/DEV]` Add a minimal test in `tests/test_ebay_export_converter.py`: load a two-record sample fixture from `tests/fixtures/ebay_export_sample.json`, run the converter, assert both output records have non-null `title` and `price_raw`.
- `[x]` `[HUMAN]` Run `python scripts/ebay_export_to_jsonl.py --in data/fixtures/ebay_export_raw.json --out data/fixtures/ebay_export.jsonl` and inspect the first three records for field completeness.
- `[x]` `[IDE/DEV]` Pipe the JSONL output through `to_stage2_fixture()` and confirm the handoff_packet shape is valid (no schema errors from `run_stage2_from_fixture`).

### eBay AU — Saved-Page Extractor Verification

- `[HUMAN]` Open one individual eBay AU laptop listing in Chrome. Use File → Save Page As (complete) to save `tests/fixtures/saved_pages/ebay_rtx3080_sample.html`.
- `[HUMAN]` Run `python -m laptopfinder.scrape_benchmark --html-file tests/fixtures/saved_pages/ebay_rtx3080_sample.html --out /tmp/ebay_verify.jsonl` and record which fields are null.
- `[IDE/DEV]` Patch `extract_ebay()` CSS regex selectors in `scrape_benchmark.py` for any fields that returned null (title, price, full_listing_text are the mandatory three).
- `[IDE/DEV]` Add `tests/test_scrape_benchmark_ebay.py`: load the saved HTML fixture, call `html_to_raw()`, assert `title`, `price_raw`, and `full_listing_text` are all non-null.

### Gumtree AU — Minimal Selector Verification

- `[HUMAN]` Open one real Gumtree AU laptop listing in Chrome. Inspect the price element in DevTools to confirm the actual CSS class name; compare against the `price-amount|listing-price` regex in `extract_gumtree()`.
- `[HUMAN]` Use File → Save Page As to save `tests/fixtures/saved_pages/gumtree_laptop_sample.html`.
- `[IDE/DEV]` Patch `extract_gumtree()` in `scrape_benchmark.py` if the observed class name does not match the regex.
- `[IDE/DEV]` Add `tests/test_scrape_benchmark_gumtree.py`: load the saved Gumtree fixture, call `html_to_raw()`, assert `title` and `price_raw` are non-null.

### Facebook Marketplace — Minimal Discovery Only

- `[HUMAN]` Open one FB Marketplace laptop listing in Chrome. Attempt File → Save Page As and run scrape_benchmark on it. Record which fallback path fires (JSON-LD, Relay blob, OG meta, or visible text). No patching required unless title and full_listing_text are both null.
- `[IDE/DEV]` If both title and full_listing_text are null: apply a targeted patch to `extract_facebook()` to fix the highest-priority fallback path only. No new test file required for FB at this stage.

### Sprint 4 Validation

- `[IDE/DEV]` Run `make test` — all 108+ tests green.
- `[HUMAN]` Confirm the eBay saved-page extractor test passes on the real HTML fixture.
- `[HUMAN]` Confirm the Gumtree saved-page extractor test passes on the real HTML fixture.

---

## ~~Sprint 5 — Firecrawl Live Wiring + batch_decide~~ [CANCELLED]

**Goal:** ~~Add a Firecrawl live-fetch path to `scrape_benchmark.py` so it can retrieve and parse structured fields from live eBay AU URLs, wire it into a new Makefile feed target, and implement the missing `batch_decide()` function.~~ Firecrawl was replaced by eBay Developer API.

### Firecrawl Live Fetch in scrape_benchmark.py

- `[IDE/DEV]` Add `fetch_live_firecrawl(url: str) -> str | None` to `scrape_benchmark.py`: checks for `FIRECRAWL_API_KEY` in env (via `python-dotenv`), instantiates the existing `Firecrawl` client (already a dependency from Sprint 2), calls `app.scrape_url(url, params={"formats": ["html"]})`, returns the raw HTML string or `None` on error. Gate the function behind a `FIRECRAWL_API_KEY` presence check that prints a clear error and returns `None` if unset.
- `[IDE/DEV]` Add `--live` flag to `scrape_benchmark.py` CLI: when set, routes each URL from `--urls FILE` through `fetch_live_firecrawl()` instead of `fetch_html()`. Existing extractors (`extract_ebay`, `extract_gumtree`) parse the returned HTML normally.
- `[IDE/DEV]` Add `make benchmark-live` Makefile target:
  ```
  benchmark-live:
      .venv/bin/python -m laptopfinder.scrape_benchmark \
          --urls data/urls.txt --live \
          --out data/feed_live/benchmark_live.jsonl
  ```
- `[IDE/DEV]` Add `make benchmark-to-feed` Makefile target and companion script `scripts/benchmark_to_feed.py`: reads `data/feed_live/benchmark_live.jsonl`, writes each `full_listing_text` value as a standalone `data/feed_live/listing-NNN.txt` file, then the existing `make live` loop can process them.
- `[IDE/DEV]` Add one focused test in `tests/test_scrape_live.py` (or a new `tests/test_scrape_benchmark_live.py`): mock the Firecrawl client to return a known HTML string for an eBay URL; assert `fetch_live_firecrawl()` returns non-null and the downstream `extract_ebay()` call produces a non-null title.
- `[HUMAN]` Populate `data/urls.txt` with 3–5 real eBay AU laptop listing URLs.
- `[HUMAN]` Run `make benchmark-live` and inspect `data/feed_live/benchmark_live.jsonl` for non-null title + price + full_listing_text.
- `[HUMAN]` Run `make benchmark-to-feed` and confirm `data/feed_live/listing-*.txt` files are created.
- `[HUMAN]` Run `make live SOURCE=data/feed_live/listing-001.txt` on one file and confirm Stage 1 → Stage 2 → Decision runs without error.

### batch_decide

- `[IDE/DEV]` Implement `batch_decide(taxonomy_path: str | Path, workload: str = "text_llm_default", ref: dict | None = None) -> list[dict]` in `decide.py`:
  - Loads `data/hardware_taxonomy.json` (or the path argument).
  - Loads scoring weights via `load_scoring_weights(workload)`.
  - Calls `score_text_llm_candidate(entry, weights)` for each entry in the taxonomy.
  - Returns a list of dicts `{"paradigm": ..., "ram_gb": ..., "bandwidth_gbps": ..., "score": ...}` sorted descending by score.
- `[IDE/DEV]` Add two focused tests in `tests/test_decide.py`:
  - `test_batch_decide_returns_all_paradigms`: assert `batch_decide()` returns ≥4 entries covering all paradigms present in `hardware_taxonomy.json`.
  - `test_batch_decide_uma_leads_for_text_llm`: assert the apple_silicon_uma entry score > discrete_cuda entry score for the `text_llm_default` workload.
- `[IDE/DEV]` Update the `batch_decide` reference in `CLAUDE.md` under "Hardware Taxonomy" to note the function now exists in `decide.py`.

### Sprint 5 Validation

- `[IDE/DEV]` Run `make test` — all tests green.
- `[HUMAN]` `make benchmark-live` produces a non-empty JSONL file from ≥3 real eBay AU URLs.
- `[HUMAN]` `make benchmark-to-feed` writes ≥3 `listing-*.txt` files to `data/feed_live/`.
- `[HUMAN]` `make live SOURCE=<any listing file>` runs to completion without crash or schema error.
- `[IDE/DEV]` `batch_decide()` returns a ranked list; `test_batch_decide_uma_leads_for_text_llm` passes.

---

## Sprint 6 — Architecture Penalty + eBay-First End-to-End Validation

**Goal:** Resolve the architecture penalty stub as a per-listing heuristic, run a full end-to-end live pass on eBay AU, capture any runtime failures as fixtures, and produce a plausible purchase matrix.

**Status (2026-07-03):** Architecture Penalty section complete (`[IDE/DEV]` items). End-to-End Live Validation remains open — `[HUMAN]` items require real eBay AU URLs and valid API keys not available in the automated session that implemented the penalty.

### Architecture Penalty — Single-Listing Heuristic

- `[x]` `[IDE/DEV]` Implement `_apply_architecture_penalty(gpu: str | None, tier: str | None, ref: dict) -> int` in `decide.py`:
  - Reads `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` from SRL.
  - **Correction from the original spec above:** Turing is *not* read from `config/silicon_profiles.yaml` — that key path (`discrete_cuda.architecture_tiers.turing.gpus`) does not exist (the real structure is `architecture_tiers.turing_sm75`/`ada_sm89` with capability flags only, no GPU name list), and CLAUDE.md documents that `silicon_profiles.yaml` is not loaded at runtime by `decide.py`. Instead, Turing generation is resolved via a new shared helper `_resolve_gpu_generation(gpu, ref)` (extracted from the existing `_gpu_generation_points()` substring-match loop) against the SRL's `llm_index_score.gpu_generation_by_name`.
  - If `_resolve_gpu_generation(gpu, ref) == "Turing"` and `tier` is not `None`, returns the penalty value (negative int). Otherwise returns 0.
  - SRL's `architecture_adjustments.applies_when`/`_comment` text updated to describe this per-listing heuristic (no numeric threshold/weight changes).
- `[x]` `[IDE/DEV]` Wire the penalty into `calculate_llm_index_score()` — already wired via the pre-existing `raw += _apply_architecture_penalty(gpu, tier, ref)` call site; no call-site change needed.
- `[x]` `[IDE/DEV]` Tests in `tests/test_decide.py`:
  - `test_turing_gpu_receives_architecture_penalty`: asserts the penalty equals `REF["architecture_adjustments"]["turing_vs_ada_same_vram_penalty_pts"]` for `"Quadro RTX 5000"`.
  - `test_ada_gpu_receives_no_architecture_penalty`: asserts 0 for `"RTX 4090"`.
  - `TestArchitecturePenaltyIntegration::test_turing_gpu_scores_lower_than_equivalent_ada_gpu`: asserts `llm_index_score` is lower for a new Turing fixture (`tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json`) than an otherwise-identical Ada fixture (`ebay_rtx4090_laptop.json`).
  - Also added: `test_none_gpu_returns_zero`, `test_none_tier_returns_zero_even_for_turing_gpu`, `test_unrecognized_gpu_returns_zero`. (No dedicated `test_uma_platform_receives_no_architecture_penalty` — UMA listings pass through `_gpu_generation_points`'s separate `is_uma` branch and never reach `_apply_architecture_penalty` with a Turing-resolving `gpu` string, so this is implicitly covered rather than needing its own fixture.)
- `[x]` `[IDE/DEV]` `make test` — 183 tests green (see Sprint 6 Validation below for the up-to-date count).
- `[x]` `[IDE/DEV]` CLAUDE.md invariants updated to note `_apply_architecture_penalty()` is a per-listing Turing heuristic, not a pairwise comparator.

### End-to-End eBay AU Live Validation

- `[HUMAN]` Verify `data/urls.txt` contains ≥3 real eBay AU laptop listing URLs (from Sprint 5 or fresh).
- `[HUMAN]` Run `make inject-config` to sync all SRL values into prompt sentinel pairs.
- `[HUMAN]` Run `make scrape-and-live` (uses `scrape_live.py` Firecrawl path + existing `make live` loop). Monitor console output for schema errors, firewall rejections, or crashes.
- `[HUMAN]` For any listing that crashes or is rejected: save the feed file as a fixture in `tests/fixtures/stage2/` (with a `_failing` suffix), note the failure reason.
- `[IDE/DEV]` For each captured failure fixture: diagnose the root cause (schema mismatch, grounding firewall, bad null handling), apply a targeted fix to the responsible code path, add a regression test, re-run `make test`.
- `[HUMAN]` Assemble SHORTLIST outputs from the console into `data/shortlist_candidates.jsonl` (one JSON object per line, manually edited with pipeline outputs).
- `[HUMAN]` Run `make render-matrix` and review `data/purchase_matrix.md` for plausible ranking order (RTX 3080 16GB / RTX 3080 Ti 16GB should rank above RTX 4090 on price-to-VRAM ratio).
- `[IDE/DEV]` If matrix ranking is wrong, identify the responsible scoring path, add a test fixture that isolates the regression, patch `decide.py` or the SRL, re-run `make test`.
- `[HUMAN]` Run `make scan-gaps` on the live feed files and review any `[GRADUATION_ALERT]`, `[PRICE_DRIFT_ALERT]`, or `[NEW_SIGHTING_ALERT]` output. Log any actionable alerts as new entries in the BACKLOG section below.

### Sprint 6 Validation

- `[x]` `[IDE/DEV]` Run `make test` — 183 tests green (up from 180 pre-Sprint-6; +3 from the rewritten/expanded `TestApplyArchitecturePenalty` class and the new `TestArchitecturePenaltyIntegration` test).
- `[x]` `[IDE/DEV]` Confirm `_apply_architecture_penalty()` is wired: `make decide FIXTURE=tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json` shows a non-zero penalty for the Turing GPU fixture (**correction:** `ebay_facts_grounded.json`, named in the original spec above, is not a Turing fixture — the new `ebay_quadro_rtx5000_turing.json` fixture is the correct target for this check).
- `[ ]` `[HUMAN]` `python -m laptopfinder.runners.ebay_hunter` runs to completion on ≥3 eBay AU listings without crash.
- `[ ]` `[HUMAN]` `data/purchase_matrix.md` renders with ≥1 SHORTLIST candidate and a plausible ranking.
- `[ ]` `[HUMAN]` `make scan-gaps` produces output (even if zero alerts).

---

## COMPLETE: eBay AU Active Sniper Setup (2026-07-05)

**Goal:** Build a lean, token-free real-time background sniper (`scripts/ebay_sniper.py`) for AU high-VRAM/UMA hardware targeting Melbourne VIC 3070, alerting via macOS iMessage. Handover: `handover.md`. Plan: `planning/laptopfinder-ebay-sniper-deep-plan.md`.

- `[x]` `[IDE/DEV]` Stage 1 — Implement flat, Karpathy-compliant `scripts/ebay_sniper.py` with national flagship sweep (Strategy A) and local Melbourne algorithmic pricing sweep (Strategy B).
- `[x]` `[IDE/DEV]` Stage 1 — Wire dynamic SRL gating (`observed_au_price_min_aud` and `exclusion_regex`) and automatic HTTP 401 token refresh.
- `[x]` `[IDE/DEV]` Stage 2 — Wire `Makefile` targets (`start-sniper`, `stop-sniper`, `status-sniper`, `test-sniper-alert`).
- `[x]` `[IDE/DEV]` Stage 2 — Create documentation in `docs/ebay_sniper.md`.
- `[x]` `[IDE/DEV]` Stage 3 — Create unit tests in `tests/test_ebay_sniper.py` covering normalization, firewall regex, and price floor logic. All 174 tests pass (`make test`).
- `[x]` `[IDE/DEV]` Stage 3 — Execute live dry-run sweep (`--dry-run --once`) verifying API connectivity and zero-state mutation.
- `[ ]` `[HUMAN/CLAUDE]` Stage 4 — Execute Codex peer review (`scripts/deep_plan_peer_review.sh`), confirm with user, launch daemon (`make start-sniper`), and log heartbeat to `docs/ebay_sniper.md`.

---

## Sprint 7 — eBay Browse & Developer API Discovery Expansion (active)

**Goal:** Extract more value from the eBay API for AU high-VRAM/UMA discovery near Melbourne. Several quick wins have now been shipped inside `scripts/ebay_sniper.py`. Brainstorm & ideas: `data/ebay_api_strategy_ideas.json` and `planning/ebay-api-discovery-ideas.md`.

### Shipped via eBay AU Sniper (`scripts/ebay_sniper.py`)
- `[x]` `[IDE/DEV]` A1 — Local pickup-radius filter: added `pickupCountry/PostalCode/Radius/RadiusUnit` tokens + zip `3070` in `X-EBAY-C-ENDUSERCTX` for Melbourne Strategy B.
- `[x]` `[IDE/DEV]` B2 — Private-seller isolation pass (`sellerAccountTypes:{INDIVIDUAL}`) in local pricing sweep.
- `[x]` `[IDE/DEV]` C1 — `newlyListed` first-mover sweep: implemented `sort=newlyListed` in national flagship and local sweeps with local state deduplication.
- `[x]` `[IDE/DEV]` C3 — `fieldgroups=EXTENDED` richer item summaries requested at Browse API edge.

### Remaining Quick Wins (for batch runner `ebay_hunter.py` / `ebay_api.py`)
- `[x]` `[IDE/DEV]` B1 — Taxonomy-driven high-VRAM `aspect_filter`: `ebay_taxonomy.py` extracted; `aspect_filter` threaded through `build_queries`/`browse_search`; category id unified to 175672. (2026-07-06)
- `[x]` `[IDE/DEV]` C2 — Seller-scoped watch queries: SRL `watched_sellers` list + `filter=sellers:{...}` in `build_queries`/`_build_filter`. (2026-07-06)

### New Strategy Ideas (`data/ebay_api_strategy_ideas.json`)
- `[x]` `[IDE/DEV]` E1 — Item Feed API Pre-Caching: `scripts/ebay_feed_cache.py` — hourly category JSONL snapshots for O(1) sniper lookups. `make cache-feed` target. 2 tests. (2026-07-06)
- `[x]` `[IDE/DEV]` E2 — Deal & Event API Clearance Monitoring: `src/laptopfinder/runners/ebay_deals.py` — scans AU refurbisher accounts (SRL `clearance_sellers`) for 64GB+ UMA clearance units. `make scan-deals` target. 3 tests. (2026-07-06)
- `[x]` `[IDE/DEV]` D2 — Realized Sold Price Baseline via **eBay Finding API `findCompletedItems`**: uses existing `EBAY_APP_ID` (no restricted scope needed). Queries AU sold listings by target GPU keywords, outputs median sold price per term to `data/sold_baseline/`. Replaces the Marketplace Insights approach (D1 dropped — restricted API, no self-service path).

### Sprint 7 Validation
- `[x]` `[IDE/DEV]` Sanity-check raw Browse calls via live dry-run (`scripts/ebay_sniper.py --dry-run --once`).
- `[ ]` `[IDE/DEV]` `.venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run` still populates corpus/SHORTLIST/underpriced counts.
- `[x]` `[IDE/DEV]` `make test` green (193 tests passing, 2026-07-06); `make lint` clean.

### Runtime checks
- `[ ]` `[HUMAN]` Run `ebay_hunter --dry-run --no-enrich` (once that flag exists) to verify taxonomy/seller-watch wiring without LLM calls.
- `[ ]` `[HUMAN]` Run a full `ebay_hunter --dry-run` with enrichment only when explicitly approved.

### Sprint 7 Backlog (minor, non-blocking)
- `[ ]` Move `PRICE_MIN_AUD`/`PRICE_MAX_AUD` defaults from `ebay_deals.py` env vars into SRL.
- `[ ]` Add `json.JSONDecodeError` guard in `load_feed_cache` for truncated JSONL files.
- `[ ]` Note: `fetch_feed_snapshot` in `ebay_feed_cache.py` assumes JSON response — eBay Feed API actually delivers gzip TSV. Needs rework once `buy.feed` scope granted (comment added, D1 dependency).
- `[ ]` Revisit true pairwise architecture penalty only if shortlist-ranking context becomes available.
- `[ ]` Keep Marketplace Insights blocked on D1; FB Marketplace and Gumtree remain discovery-only until a supported manual/agent-assisted workflow is chosen.

---

## BACKLOG

Items not yet sprint-assigned. Promote to next sprint planning cycle as capacity allows.

- [ ] Implement `batch_decide()` as documented in CLAUDE.md to enable multi-listing scoring and processing.

---

## User Testing Guide

> Written for a non-developer operator. Use these walkthroughs to validate each sprint's work. Exact commands are provided; expected output is noted. "Pass" and "fail" criteria are explicit.

---

### eBay AU Testing Walkthrough

**What you need before starting:**
- Project dependencies installed (`uv sync` from the project root)
- A terminal open in the project root (`/Users/okgoogle13/Projects/laptopfinder`)
- `.env` file with valid `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `EBAY_APP_ID`, `EBAY_CERT_ID`

**Step 1 — Run the live eBay API scrape on a short URL list**

Open `data/urls.txt` in a text editor and add 3–5 eBay AU laptop listing URLs (one per line, no blank lines). Then run:

```bash
make benchmark-live
```

Expected terminal output:
```
[LIVE] https://www.ebay.com.au/itm/... → title: "ASUS ROG Zephyrus RTX 3080 16GB..." price: "$1,850.00"
[LIVE] ...
[DONE] 3 records → data/feed_live/benchmark_live.jsonl
```

**Pass:** `benchmark_live.jsonl` exists; open it and confirm `title` and `price_raw` are non-null in each line.  
**Fail:** "FIRECRAWL_API_KEY not set" → add the key to your `.env` file. "0 records" → check that URLs in `data/urls.txt` are real active listings.

**Step 4 — Convert to feed text files and run the live pipeline**

```bash
make benchmark-to-feed
```

Then, for each listing file created:

```bash
make live SOURCE=data/feed_live/listing-001.txt
```

Expected terminal output (abbreviated):
```
[Stage 1] Discovered 1 candidate: "ASUS ROG Zephyrus G15 RTX 3080 16GB"
[Stage 2] Analysis complete. GPU: RTX 3080, VRAM: 16GB, Risk: 1.5
[Decision] SHORTLIST — llm_index_score: 72
```

**Pass:** Decision printed without Python traceback; `recommended_action` is SHORTLIST, MONITOR, or SKIP.  
**Fail:** `ValueError: grounding firewall` → the LLM fabricated a fact not in the listing text; this is expected occasionally and not a bug. `JSONDecodeError` → the LLM returned malformed JSON; retry once, then file as a fixture-level issue.

**Step 5 — Render the purchase matrix**

Manually assemble any SHORTLIST outputs (the JSON printed to terminal) into `data/shortlist_candidates.jsonl` (one JSON object per line). Then:

```bash
make render-matrix
```

Open `data/purchase_matrix.md` in any text editor or Markdown viewer.

**Pass:** Table renders with ≥1 row; RTX 3080 16GB ranks above RTX 4090 16GB (better VRAM-to-price ratio).  
**Fail:** "No candidates found" → `data/shortlist_candidates.jsonl` is empty or malformed. Confirm each line is valid JSON.

**Step 6 — Scan for market gaps**

```bash
make scan-gaps
```

**Pass:** Script runs without crash; prints `[GRADUATION_ALERT]`, `[PRICE_DRIFT_ALERT]`, `[NEW_SIGHTING_ALERT]` lines, or "No alerts" if feed files have no relevant sightings.  
**Fail:** `FileNotFoundError` → no feed files in `data/feed_live/`. Run `make benchmark-to-feed` first.

---

### Gumtree AU Testing Walkthrough

**What you need:** A real Gumtree AU laptop listing saved locally (from Sprint 4). Chrome DevTools access.

**Step 1 — Save a Gumtree listing page**

1. Open a Gumtree AU laptop listing URL in Chrome.
2. Right-click the price element on the page and choose "Inspect". In DevTools, note the exact CSS class name on the `<span>` or `<strong>` element that contains the price.
3. Go to File → Save Page As → "Complete" and save to `tests/fixtures/saved_pages/gumtree_laptop_sample.html`.

**Step 2 — Run the extractor against the saved page**

```bash
.venv/bin/python -m laptopfinder.scrape_benchmark \
  --html-file tests/fixtures/saved_pages/gumtree_laptop_sample.html \
  --out /tmp/gumtree_test.jsonl
```

**Pass:** Terminal prints a line with non-null `title` and `price_raw`. Open `/tmp/gumtree_test.jsonl` and confirm.  
**Fail:** `price_raw: null` → the `price-amount|listing-price` regex did not match. Note the actual class name from DevTools and report it so `extract_gumtree()` can be patched.

**Step 3 — Run the test suite**

```bash
.venv/bin/python -m pytest tests/test_scrape_benchmark_gumtree.py -v
```

**Pass:** All tests green.  
**Fail:** `AssertionError: price_raw is None` → extractor needs patching. `FileNotFoundError` → the saved-page fixture is missing.

---

### Facebook Marketplace Testing Walkthrough

> FB Marketplace is secondary. The goal here is to confirm what fallback path the extractor uses, not to achieve full parity.

**Step 1 — Save an FB Marketplace listing**

1. Open a Facebook Marketplace laptop listing in Chrome while logged into Facebook.
2. File → Save Page As → "Complete". Save to `tests/fixtures/saved_pages/fb_laptop_sample.html`.

**Step 2 — Run the extractor**

```bash
.venv/bin/python -m laptopfinder.scrape_benchmark \
  --html-file tests/fixtures/saved_pages/fb_laptop_sample.html \
  --out /tmp/fb_test.jsonl
```

**Pass:** `full_listing_text` is non-null (even if title is null). Note which fallback path fired.  
**Fail:** Both `title` and `full_listing_text` are null — the page was too heavily client-rendered at save time. Try: (a) logging into FB first before saving, (b) using DevTools Network tab to intercept the GraphQL/Relay XHR response and saving that JSON directly to a `fb_*.json` file, then running scrape_benchmark on the JSON file.

---

### Common Failure Modes

**`ValueError: grounding firewall`**  
The Stage 2 LLM stated a fact (GPU name, VRAM size) that does not appear verbatim in the listing text. This is correct behaviour — the firewall is working. Retry the listing once (LLM output is non-deterministic). If it fails repeatedly, the listing text is too sparse; mark the listing as insufficient and skip.

**`JSONDecodeError` from Stage 1 or Stage 2 runner**  
The LLM returned a response that is not valid JSON. Retry once. If persistent, check whether the prompt was correctly injected (`make inject-config`) and whether the model name in the runner is correct.

**`FIRECRAWL_API_KEY not set`**  
The `.env` file is missing the key or was not loaded. Confirm `.env` exists at the project root with `FIRECRAWL_API_KEY=fc-...`. Run `make benchmark-live` again.

**`ERROR: scrape produced no listing files`**  
`make scrape-and-live` uses `scrape_live.py`. If no `listing-*.txt` files appear in `data/feed_live/`, the Firecrawl scrape returned empty responses. Check that URLs in `data/urls.txt` are real live listings (not ended/removed). Check `FIRECRAWL_API_KEY` credits.

**`AssertionError: title is None` in tests**  
A scraper test fixture is mismatched against the extractor. The saved HTML page uses class names different from the regex in the extractor. Run the extractor manually on the saved HTML, inspect the output, and patch the CSS regex in `scrape_benchmark.py`.

**`KeyError` or `AttributeError` in `decide.py`**  
A listing's Stage 2 analysis is missing a field the decision engine expects. Save the failing analysis JSON as a fixture in `tests/fixtures/stage2/` and add a regression test that isolates the missing field. Then patch `decide.py` to handle the null case (never infer — return null or 0).

**`make render-matrix` produces "No candidates"**  
`data/shortlist_candidates.jsonl` is empty or malformed. Each line must be a single valid JSON object (the full decision dict printed to terminal). Confirm the file has no trailing commas or blank lines.

**GPU appearing in `[NEW_SIGHTING_ALERT]` from `make scan-gaps`**  
A GPU was seen in feed files but is absent from both `target_gpus` and `watch_list` in `config/static_reference_layer.json`. Evaluate the hardware against the current market topology and add it to the appropriate list in the SRL if warranted. Run `make test` after any SRL change.

---

## Next Steps — eBay API Pipeline

- `[ ]` `[HUMAN]` Run `gh secret list` and confirm `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` are present in GitHub Secrets.
- `[ ]` `[HUMAN]` Populate `.env` with eBay Browse API credentials; run `bash scripts/authenticate_ebay.sh` to confirm OAuth token generation succeeds.
- `[ ]` `[HUMAN]` Run `python -m laptopfinder.runners.ebay_hunter` against a real eBay AU laptop search query; confirm ≥3 listings reach Stage 1 JSON output.
- `[ ]` `[HUMAN]` Run `make pipeline STAGE1=<live_stage1_output> STAGE2=<live_stage2_output>` end-to-end on one real listing; confirm decision output is SHORTLIST/MONITOR/SKIP without crash.
- `[ ]` `[HUMAN]` Run `make render-matrix` and confirm `data/purchase_matrix.md` contains a ranked SHORTLIST section.
- `[ ]` `[IDE/DEV]` Evaluate true pairwise architecture penalty (Turing vs Ada same-VRAM) — current `_apply_architecture_penalty()` is a per-listing heuristic; revisit only if a shortlist-ranking batch pass over multiple Stage 2 outputs becomes available.

---

## Backlog: Pipeline Hardening & Alignment (Claude Assessment)

- `[ ]` `[IDE/DEV]` Wrap Gemini API calls in `src/laptopfinder/runners/comet.py` and `aistudio.py` in try/except with exponential backoff retries.
- `[ ]` `[IDE/DEV]` Add explicit header presence check in `src/laptopfinder/ingest_csv.py` to fail fast on unexpected columns instead of yielding null rows.
- `[ ]` `[IDE/DEV]` Add warnings and fallback to `ebay_taxonomy.py` for aspect lookups in `src/laptopfinder/runners/ebay_api.py`.
- `[ ]` `[IDE/DEV]` Deduplicate `data/evidence/undiscovered_hardware.jsonl` entries in `_log_undiscovered_hardware` by matching `listing_id`.
- `[ ]` `[IDE/DEV]` Add final fallback regex `\b(14|15|16|17|18)["″]` for screen sizes in `scripts/build_shortlist_value.py`.
- `[ ]` `[DOC]` Update `CLAUDE.md` to clarify that `risk_score == 3.0` exactly passes.
- `[ ]` `[DOC]` Update `CLAUDE.md` to state that `min_vram_to_shortlist_gb` is deprecated in favor of `vram_gating_logic`.
- `[ ]` `[IDE/DEV]` Add test case in `tests/test_decide.py` verifying that exactly `risk_score=3.0` passes while `3.1` is skipped.
- `[ ]` `[DOC]` Add note to `config/silicon_profiles.yaml` explaining that it is only used by agents/prompts, not loaded at runtime by `decide.py`.
