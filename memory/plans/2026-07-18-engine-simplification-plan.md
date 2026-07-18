# Dated Plan: Multi-Vendor Engine Convergence & Simplification (2026-07-18)

This dated plan guides the transition of the `laptopfinder` decision engine into a fully unified, platform-agnostic pipeline.

---

## 1. Inventory & Roadmap Classifications

### Core Engine & Platform Adapters (`src/laptopfinder/`)
- `adapters/__init__.py` (Neutral `Listing` contract) — **KEEP / CRITICAL**
- `adapters/ebay.py` (eBay Browse payload adapter) — **KEEP / CRITICAL**
- `adapters/scorptec.py` (Scorptec product SKU adapter) — **KEEP / CRITICAL**
- `core.py` (Stage 1/2 discovery & grounding firewalls) — **KEEP / CRITICAL**
- `decide.py` (Decision engine) — **NEEDS REFRACTORING (Phase 2)**: currently hardcoded to SRL, needs upgrade to support `Listing` object ingestion, `static_scoring_rules.json`, and `lf-vendor-risk.json`.
- `ingest_csv.py` (CSV batch import) — **NEEDS UPGRADE (Phase 3)**: must adapt rows into canonical `Listing` before decision.
- `scrape_benchmark.py` (Fixture generation tool) — **KEEP / CRITICAL**
- `ebay_taxonomy.py` (Aspect and Category query builders) — **KEEP**

### Live & Legacy Runners (`src/laptopfinder/runners/`)
- `runners/ebay_sniper.py` (Live sniper daemon) — **NEEDS UPGRADE (Phase 3)**: wrap live items in `Listing` adapter before scoring.
- `runners/hunt.py` (Ad hoc operator sweep) — **KEEP**
- `runners/legacy/*` (Legacy hunter, deals, evidence, audit pipelines) — **MAINTENANCE ONLY**

### Operational Scripts (`scripts/`)
- `scripts/score_active_watchlist.py` (Watchlist normalization engine) — **KEEP**: merge logic to `decide.py` over time.
- `scripts/render_matrix.py` (Matrix markdown generator) — **NEEDS UPGRADE (Phase 4)**: render `Score (0-100)`, `Platform`, and `Vendor Type`.
- `scripts/build_shortlist_value.py` (Lane/tier shortlist sorter) — **NEEDS UPGRADE (Phase 4)**: align sorting to `score_0_100` and `value_index`.
- `scripts/status_snapshot.py` (Dashboard status snapshot) — **NEEDS UPGRADE (Phase 4)**: count results across active watchlist and live sniper.
- `scripts/lf_floor_sync.py` & `scripts/lf_price_baseline.py` (PWM data prep) — **KEEP / CRITICAL**
- `scripts/inject_config.py` & `scripts/sync_agent_hooks.py` (Sync engines) — **KEEP / CRITICAL**
- `scripts/authenticate_ebay_user.py` & `scripts/refresh_ebay_user.py` (OAuth) — **KEEP / CRITICAL**
- `scripts/ebay_sniper.py` (Obsolete duplicate copy) — **OLD / RETIRE / DELETE (Phase 1)**

---

## 2. Convergence Implementation Strategy

### Phase 1: De-duplication
- **Delete `scripts/ebay_sniper.py`**. Confirm that only the canonical runner `src/laptopfinder/runners/ebay_sniper.py` remains.
- Verify `Makefile` targets (`make live`, `make live-daemon`) continue to resolve cleanly to the canonical runner.

### Phase 2: Engine Integration (`decide.py`)
- Refactor `decide.py` to support ingesting `Listing` instances directly.
- Merge the evaluation of connected signals, vendor risk profile parameters, and `score_0_100` normalization into `decide()`.
- Unify the fallback recovery logic so missing-data items carrying flagship GPUs are assigned to `WATCH` with `needs_manual_spec_check=True`.

### Phase 3: Runner Migration
- Update `runners/ebay_sniper.py` to pass raw Browse API items through `ebay_browse_to_listing()` adapter before invoking `decide()`.
- Update `ingest_csv.py` to map extracted specs to a `Listing` before calling `decide()`.
- Ensure decision dictionary writes (`latest_decisions.json`, `shortlist_candidates.jsonl`) store normalized `score_0_100`, `platform`, and `vendor_type`.

### Phase 4: Output & Reporting Refinement
- Update `render_matrix.py` to format markdown purchase matrices with `Score (0-100)`, `Platform`, `Vendor Type`, and `WATCH` sections.
- Refactor `build_shortlist_value.py` to rank items via `score_0_100` and `value_index`.
- Update `status_snapshot.py` to summarize decision outcomes across both watchlists and sniper outputs.

---

## 3. Definition of Done
- [ ] Obsolete `scripts/ebay_sniper.py` deleted.
- [ ] `decide()` natively ingests `Listing` and evaluates via `static_scoring_rules.json` / `lf-vendor-risk.json`.
- [ ] eBay sniper daemon and CSV ingestion execute decisions over adapter-wrapped `Listing` instances.
- [ ] Shortlist outputs render normalized multi-vendor matrices.
- [ ] `make test` executes 264+ unit tests successfully.
