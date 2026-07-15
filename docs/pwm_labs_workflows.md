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

## 6. When to Use Labs vs Deep Research

Use Labs when:

- You need code, dashboards, or scripts created and bundled into files/projects. [web:2][web:22][web:29]
- You want to overwrite default files or write new scripts locally to run.

Use Deep Research for:

- Upstream data acquisition and multi‑source analysis (markets, silicon, vendors). [web:17][web:20]
