# Sprint 10 Implementation Plan: Platform-Agnostic Decision Architecture & Multi-Vendor Engine

This document is for planning only. Execution is performed according to approved sprint tasks in `STATUS.md`.

## Goal

Transition `laptopfinder` to a Platform-Agnostic, Multi-Vendor Decision Engine by integrating the neutral `Listing` adapter layer, unified declarative scoring rules (`config/static_scoring_rules.json`), vendor risk lens (`data/lf-vendor-risk.json`), and consolidated watchlist hunt runner (`make hunt CONFIG=config/runs/watchlist_hunt.json`).

## Architectural Audit & Peer Review (S10-00)

### Verified Enhancements in `docs/handover.md`:
1. **Neutral Schema & Platform Adapters (`src/laptopfinder/adapters/`)**:
   - Clean dataclass representation (`Listing`) standardizing `platform`, `vendor_name`, `vendor_type`, `connectivities`, `paradigm`, and normalized `condition` across marketplace and retail channels.
   - Decouples platform-specific API quirks (`auction_volatility`, shipping estimates, local warranty bonuses) into declarative platform JSON files (`config/platforms/*.json`).

2. **Declarative Capability Governance & Normalisation (`config/static_scoring_rules.json`)**:
   - Expanded screen gates for `workstation_16_touch_or_pro` (14-17") and `uma_dev_rig` (13-18") correctly accommodate compact high-RAM workstations (e.g. ASUS ROG Flow Z13, HP ZBook Ultra G1a) without misclassifying them as desktop replacements.
   - Missing-data deduction policy (`vram_gb`: -6, `system_ram_gb`: -4, `cpu_model`: -2) recovers flagship GPUs/UMA platforms into **`WATCH`** with `needs_manual_spec_check` instead of dropping them.
   - Unified `score_0_100` scale provides fair cross-lane ranking normalized against lane ceilings (`gaming_17_18`: 85, `workstation_16_touch_or_pro`: 80, `macbook_16_high_ram`: 90, `uma_dev_rig`: 85).

3. **Vendor Risk Lens (`data/lf-vendor-risk.json`)**:
   - Unified database supporting eBay handles and Australian retailers/OEM outlets (`SCORPTEC`, `JB_HIFI`, `LENOVO_OUTLET_AU`, `HP_STORE_AU`).
   - Additive adjustments reward pristine retailer channels while enforcing linear deductions for unverified sellers.

## Phased Implementation Plan (S10-01 to S10-12)

### Phase 1: Cleanup & Legacy File Consolidation
- **S10-01**: Remove duplicate `scripts/ebay_sniper.py` file; update `Makefile` to reference `src/laptopfinder/runners/ebay_sniper.py`.

### Phase 2: Decision Engine Integration
- **S10-02**: Update `src/laptopfinder/decide.py` to ingest `Listing` instances directly, loading vendor risk adjustments and `score_0_100` normalisation parameters from `static_scoring_rules.json` and `lf-vendor-risk.json`.

### Phase 3: Runner & Watchlist Migration
- **S10-03**: Wrap incoming raw listings in `src/laptopfinder/runners/ebay_sniper.py` and `src/laptopfinder/ingest_csv.py` with platform adapters before calling `decide()`.
- **S10-07**: Create watchlist hunt run config at `config/runs/watchlist_hunt.json`.
- **S10-08**: Refactor `collect_corpus` in `src/laptopfinder/runners/legacy/hunter/search.py` to support watchlist loading via `tools.ebay_watchlist_snapshot`.
- **S10-09**: Refactor `src/laptopfinder/runners/legacy/ebay_hunter.py` to output paths dynamically for watchlist sweeps.
- **S10-10**: Update `Makefile` to map `ebay-watchlist-snapshot` target to consolidated `make hunt CONFIG=config/runs/watchlist_hunt.json`.
- **S10-11**: Deprecate and delete obsolete `scripts/score_active_watchlist.py`.

### Phase 4: Output Rendering & Status Reporting
- **S10-04**: Update `scripts/render_matrix.py` and `scripts/build_shortlist_value.py` to output unified multi-vendor columns (`Score 0-100`, `Platform`, `Vendor Type`).
- **S10-05**: Update `scripts/status_snapshot.py` status dashboard counts to report across watchlist and sniper outputs.
- **S10-06 & S10-12**: Verify unit test suite coverage (264+ tests passing) and perform live dry-run sweeps.

## Acceptance Criteria
- All 264+ unit tests in `pytest tests/ -v` pass cleanly.
- `make hunt CONFIG=config/runs/watchlist_hunt.json DRY_RUN=1` completes without errors.
- `output/shortlist/purchase_matrix.md` renders normalized 0-100 scores and vendor columns.