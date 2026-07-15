# Perplexity Labs Workflows for Laptopfinder

This document describes Perplexity Labs / “Create Files & Apps” workflows used in the Laptopfinder ecosystem. Labs is used to generate code bundles, dashboards, and utilities that you download and run locally. [web:2][web:22][web:25][web:29]

---

## 1. Labs Role in the Stack

- Consume Labs tokens (25+ available) instead of Pro queries. [web:25][web:29]
- Produce durable artefacts:
  - Python scripts, CLIs, daemons.
  - HTML/JS dashboards and interactive apps.
  - Test suites and scraper rule modules.
- Everything runs locally; no backend cloud infra.

---

## 2. `pwm lf-alert-forge` — AU Bargain Watcher Daemon

**Purpose**

- Generate a self‑contained local project that watches AU marketplaces and sends macOS notifications/iMessages when a listing beats your Laptopfinder thresholds.

**Mode**

- Perplexity Labs “create files & apps”. [web:2][web:22][web:29]

**Inputs (to Labs)**

- `config/static_reference_layer.json` — targets and scoring tiers.
- `config/scoring_weights.yaml` — weights for llm_index_score and risk.
- `config/search_sources.json` — saved search URLs/feeds (eBay AU, OzBargain, refurb outlets).

**Required project outputs**

- `scripts/watchers/watcher.py`  
  - Uses `requests` + `BeautifulSoup` to fetch/search AMP/HTML pages (no Playwright).  
  - Emits normalised listing JSON: `id`, `title`, `price_aud`, `vendor`, `gpu`, `vram_gb`, `ram_gb`, `llm_index_estimate`, `risk_score`.
- `scripts/watchers/db.py`  
  - SQLite wrapper (`watcher.db`) to persist listings, prices, alert state.
- `scripts/watchers/notify.py` and `scripts/watchers/notify.applescript`  
  - `notify.py` consumes JSON from stdin and calls `osascript` with message payload.  
  - `notify.applescript` sends iMessage or macOS notification with title/price/link.
- `scripts/watchers/config.yaml`  
  - `search_sources`, `risk_score_threshold`, `llm_index_threshold`, `poll_interval_minutes`.
- `scripts/watchers/requirements.txt`  
  - Minimal dependencies: `requests`, `beautifulsoup4`, `pyyaml`, `sqlite3` (stdlib).
- `scripts/watchers/README.md`  
  - Install instructions, `python watcher.py run` usage, optional launchd/cron hints.

**Integration**

- Continuous monitoring for Laptopfinder; new candidates are scored and visualised via `lf-score`, `lf-matrix-app`, `lf-compare-studio`.

---

## 3. `pwm lf-matrix-app` — Interactive Value Matrix Dashboard

**Purpose**

- Generate an offline, interactive dashboard for visualising VRAM/$, llm_index_score, and risk bands across shortlisted candidates.

**Mode**

- Labs “create files & apps”. [web:2][web:22][web:29]

**Inputs**

- `data/shortlist_candidates.jsonl` — JSON lines of candidate machines (post‑scoring).
- `config/scoring_weights.yaml` — weighting configuration.

**Outputs**

- `apps/lf_matrix/index.html` (+ minimal JS/CSS) with:
  - Scatter plot: `price_aud` vs `llm_index_score`.
  - Bar charts: `vram_per_dollar`.
  - Filters: `gpu_arch`, `uma_vs_discrete`, `vendor`, `risk_band`.
- `apps/lf_matrix/README.md` — how to open the app locally (no backend).

**Integration**

- Used by you to visually inspect tradeoffs and avoid over‑spec’d gaming rigs that don’t materially improve LLM throughput.

---

## 4. `pwm lf-compare-studio` — Multi‑Listing Tradeoff Sandbox

**Purpose**

- Generate an interactive app to compare 3–5 candidate machines side by side, including derived metrics and adjustable weights.

**Mode**

- Labs “create files & apps”. [web:2][web:22][web:29]

**Inputs**

- `data/candidates.json` — array of candidate listings with full specs and derived metrics.
- `data/silicon_profiles.yaml` — hardware profiles (bandwidth, VRAM, etc.).

**Outputs**

- `apps/lf_compare_studio/index.html` — interactive UI:
  - Spec cards and summary metrics per candidate.
  - Derived metrics (tokens/sec estimate, vram_per_dollar, bandwidth_per_dollar).
  - Sliders for importance of VRAM, bandwidth, portability, noise, price.
- `apps/lf_compare_studio/chosen_candidate.json` — exported recommendation with rationale.

**Integration**

- Primarily used when you have a short list of serious contenders, often after `lf-alert-forge` and any jury/council‑style decisions.

---

## 5. `pwm lf-sniper-rules` — Scraper Selector & Regex Generator

**Purpose**

- Generate Python scraper modules and exclusion rules for new AU refurb sites using sample HTML/text.

**Mode**

- Labs “create files & apps”. [web:2][web:22][web:29]

**Inputs**

- `saved_pages/<site>.html` — representative HTML snapshot for a refurb site.

**Outputs**

- `scrapers/<site>_rules.py`  
  - Functions: `extract_listing_specs(html: str) -> dict`, `is_salvage_or_parts(html: str) -> bool`.
- `tests/test_<site>_rules.py`  
  - PyTest fixtures covering match/non‑match behaviours.
- `config/<site>_exclusion_keywords.yaml`  
  - Keywords for salvage/for‑parts/no‑warranty patterns.

**Integration**

- Imported by watcher scripts and Stage 2 firewalls.  
- Allows rapid extension of monitoring to new AU refurb vendors without extra LLM calls at runtime.

---

## 6. `pwm lf-url-rubric-labs` — Ad-Hoc URL Scorer

**Purpose**

Instantly score a pasted eBay AU or AU retail URL against `config/static_reference_layer.json` and return a SHORTLIST / SKIP verdict with spec-gap and risk reasoning. Eliminates waiting for the next batch sweep when evaluating a single off-pipeline listing.

**Mode:** Labs "Create Files & Apps". `search_grounding: false`.

**Inputs (upload to Labs):**
- `config/static_reference_layer.json` (`vram_gating_logic`, `risk_gate`, `data_integrity.exclusion_regex`).

**Outputs:**
- `data/pwm/lf-url-rubric/url_verdict.md` — extracted specs, SHORTLIST/SKIP verdict, spec-gap flags, SRL rule rationale.
- `data/pwm/lf-url-rubric/url_eval.json` — `{url, gpu_guess, vram_gb, host_ram_gb, passes_vram_gate, passes_risk_gate, spec_gaps: [...], verdict: "SHORTLIST"|"SKIP"}`.

**Done criterion:** App accepts a URL, returns SKIP when any SRL gate fails, SHORTLIST only when all required gates pass with no critical spec gaps.

**Cost:** 1 labs.

---

## 7. `pwm lf-triage-dash` — Shortlist Triage Dashboard

**Purpose**

Generate an interactive dashboard for filtering, ranking, and exporting SHORTLIST entries by risk score, `llm_index_score`, and price delta vs floor. Replaces static Markdown matrices with sortable, filterable views.

**Mode:** Labs "Create Files & Apps". `search_grounding: false`.

**Inputs (upload to Labs):**
- `output/decisions/latest_decisions.json` (SHORTLIST entries).
- `output/shortlist/purchase_matrix.md` (ranking context).
- `data/pwm/lf-floor-sync/price_patches.json` (AU price floor patches).

**Outputs:**
- `data/pwm/lf-triage-dash/triage_snapshot.md` — filtered view of top 3 immediate action items.
- `data/pwm/lf-triage-dash/triage_export.json` — filtered and sorted shortlist array.
- `data/pwm/lf-triage-dash/offer_bands.png` — scatter plot of shortlisted prices vs price floors per GPU tier.

**Done criterion:** Dashboard loads all SHORTLIST entries with filtering by risk score and sorting by price delta vs floor.

**Cost:** 1 labs.

---

## 8. `pwm lf-alert-scaffold` — Non-eBay Endpoint Watcher Scaffold

**Purpose**

Generate a starter Python watcher script with CSS selectors to monitor AU retail and outlet endpoints beyond eBay (Grays, Gumtree, Dell Outlet AU). Complements `ebay_sniper.py`; does not replace it.

**Mode:** Labs "Create Files & Apps". `search_grounding: true` (to verify current DOM structure).

**Inputs (upload to Labs):**
- `config/static_reference_layer.json` (`target_gpus`).

**Outputs:**
- `data/pwm/lf-alert-scaffold/endpoint_map.md` — documented endpoints and selectors.
- `data/pwm/lf-alert-scaffold/alert_config.json` — JSON schema defining endpoints for operator review.
- `data/pwm/lf-alert-scaffold/watcher.py` — generated watcher script; operator reviews before committing.

**Done criterion:** `watcher.py` is generated with valid selector functions for ≥ 3 non-eBay AU endpoints.

**Cost:** 1 labs.

---

## 9. When to Use Labs vs Deep Research

Use Labs when:

- You need code, dashboards, or scripts created and bundled into files/projects. [web:2][web:22][web:29]
- You want to overwrite default files or write new scripts locally to run.

Use Deep Research for:

- Upstream data acquisition and multi‑source analysis (markets, silicon, vendors). [web:17][web:20]
