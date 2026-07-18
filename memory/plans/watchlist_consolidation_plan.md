# Plan: Watchlist Consolidation into Stage 2 Hunter Pipeline

This plan outlines the steps to deprecate the title-only regex scoring script (`score_active_watchlist.py`) and route eBay watchlist items directly through the canonical Stage 2/`decide.py` decision pipeline.

---

## 1. Objective

Enable watchlist items to be fully enriched via `getItem` (description + specifics) and scored via the robust `decide.py` rules, resolving inaccurate spec parsing and eliminating arbitrary `"Needs Spec Check"` labels.

---

## 2. Actionable Tasks

### Phase 1: Configuration & Search Integration
- [ ] **S10-07:** Create the watchlist hunt run configuration at `config/runs/watchlist_hunt.json` declaring `"source": "watchlist"`.
- [ ] **S10-08:** Refactor `collect_corpus` in `src/laptopfinder/runners/legacy/hunter/search.py` to check for `source == "watchlist"` and fetch raw watchlist items using `tools.ebay_watchlist_snapshot`.

### Phase 2: Hunter Pipeline Adjustment
- [ ] **S10-09:** Refactor `src/laptopfinder/runners/legacy/ebay_hunter.py` to dynamically adjust results and matrix output paths when running in watchlist mode:
  - Scored JSONL: `output/shortlist/watchlist_scored_active.jsonl`
  - Markdown Matrix: `output/shortlist/watchlist_purchase_matrix.md`
- [ ] **S10-10:** Update the Makefile to point `ebay-watchlist-snapshot` (or a new `score-watchlist` target) to the consolidated `make hunt CONFIG=config/runs/watchlist_hunt.json` flow.

### Phase 3: Cleanup & Validation
- [ ] **S10-11:** Delete the deprecated `scripts/score_active_watchlist.py` script.
- [ ] **S10-12:** Verify the entire test suite passes and execute a live dry-run of the new watchlist hunter flow.

---

## 3. Verification Plan

- **Dry-run Execution**: Run `make hunt CONFIG=config/runs/watchlist_hunt.json DRY_RUN=1` and ensure it runs to completion without traceback.
- **Output Inspection**: Confirm `output/shortlist/watchlist_purchase_matrix.md` is rendered with full, accurate spec columns and no fallback labels.
- **Unit Tests**: Confirm `make test` remains green.
