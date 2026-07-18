# Laptopfinder Status & Progress

## Overview

- Project: Laptopfinder (structured eBay AU discovery + shortlist + matrix)
- Mode: finite burst — stop when a good laptop is found and bought
- Current sprint: 7 (Hardening + Live Discovery)
- High-level path: auth → dry-run → shortlist → matrix → buy

## Progress by Area

| Area                    | Status       | Estimate (h) |
|-------------------------|-------------|--------------|
| Doctrine/docs (CLAUDE.md, README)      | done          | 1–2          |
| Decision engine (decide.py fixes)      | done          | 2–3          |
| Runners/Makefile cleanup               | done          | 2–3          |
| Live eBay AU smoke test + matrix       | done          | 1–2          |
| Final “shipping & launch” checklist    | in progress   | 1–2          |

_Update these rows as work completes. Keep estimates rough and honest._

## NEXT_TASK

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

*Completed Tasks:*
- [x] **S9-02:** `lf-price-baseline`: `scripts/lf_price_baseline.py` merges `data/hunt_results.jsonl` + `data/shortlist_candidates.jsonl` into `data/lf-price-baseline.csv`. *(scripts/lf_price_baseline.py, tests/test_lf_price_baseline.py)* — fixed cross-script import (inlined `lf_floor_sync` helpers) so `python scripts/lf_price_baseline.py` works directly without pytest's pythonpath shim. The three PWM workflow "designs" in the blocker are complementary layers (Makefile gates → local CSV prep → Perplexity Deep Research), not conflicts.
- [x] **S9-01:** `lf-floor-sync`: `scripts/lf_floor_sync.py` normalizes `data/hunt_results.jsonl` (from `make hunt`) into `data/lf-floor-listings.csv`. *(scripts/lf_floor_sync.py, tests/test_lf_floor_sync.py)* — note: original spec referenced `make_hunt CONFIG=lf-floor`, which doesn't exist (typo for `make hunt`, and no `config/runs/lf-floor.json` config file exists yet). Script normalizes whatever `data/hunt_results.jsonl` a human produces via any `make hunt CONFIG=...` run; creating a dedicated `lf-floor` run config is a separate open item, not blocking this script.
- [x] **S8-06:** `risk_score` rules & documentation *(CLAUDE.md, tests/test_decide.py)* — CLAUDE.md:95 documents `risk_score == 3.0` passes exactly; CLAUDE.md:142 documents `min_vram_to_shortlist_gb` deprecation; `test_boundary_exactly_3_0_passes` / `test_boundary_3_1_fails` in tests/test_decide.py cover the boundary.
- [x] **S8-05:** Add final fallback regex for screen sizes in `build_shortlist_value.py`. *(scripts/build_shortlist_value.py)*
- [x] **S8-04:** Deduplicate `data/evidence/undiscovered_hardware.jsonl` entries in `_log_undiscovered_hardware` by matching `listing_id`. *(src/laptopfinder/decide.py, tests/test_decide.py)*
- [x] **S8-03:** `ingest_csv.py` — raise `ValueError` on missing required CSV columns at open time. *(src/laptopfinder/ingest_csv.py, tests/test_ingest_csv.py)*
- [x] **S8-01:** Fix `docs/ebay_sniper.md` — drop nonexistent daemon targets, document real `make live`.
- [x] **S8-02:** Added `live-daemon`/`live-stop`/`live-tail` Makefile targets (nohup + PID file + log); documented in `docs/ebay_sniper.md`.
- [x] Resolve GitHub Issue #8: [bugfix] Make _ram_gb schema-safe (already implemented).
- [x] Resolve GitHub Issue #9: [bugfix] Merge global_constraints in load_scoring_weights (already implemented).
- [x] Resolve GitHub Issue #10: [bugfix] Tighten eGPU SHORTLIST gate to use VRAM only (already implemented).
- [x] Resolve GitHub Issue #11: [bugfix] Use bool(touchscreen_digitizer) for touchscreen exception (already implemented).
- [x] Resolve GitHub Issue #12: [perf/robustness] Precompute custom ref in decide().
- [x] Resolve GitHub Issue #13: [refactor] Deprecate legacy LLM runners.
- [x] Resolve GitHub Issue #14: [refactor] Fold ebay_api.py into ebay_hunter.py.
- [x] Resolve GitHub Issue #15: [feature] Implement search refinement logic.
- [x] Resolve GitHub Issue #16: [test] Unit tests for live discovery components.
- [x] Resolve GitHub Issue #17: [harden] Token refresh and state-machine tests.
- [x] Resolve GitHub Issue #18: [harden] Gemini 429 retry backoff in enrichment.
- [x] Run an eBay AU end-to-end smoke test (auth → live discovery → shortlist → matrix) and capture findings.
  - *Findings*: `make ebay-auth` successfully minted token. `make live` queried Browse API correctly but found 0 new items (possibly restrictive config/aspects). `make render-matrix` successfully rendered 63 existing pre-cached candidates.

Agents must:
- Work on the **first** bullet in NEXT_TASK.
- When finished, remove or mark it as done and promote the next one.
- Never ask the user “what next?” if NEXT_TASK has items.

## Sprint & Tasks Pointers

- `TASKS.md` contains the full task list and backlog.
- `sprint.md` (if present) contains detailed phase plans.
- Agents must read these before changing code or docs.
- Run `make status` for a mechanical snapshot (last sniper/hunt run, evidence record count, NEXT_TASK) — no LLM calls, reads existing runner output files only.

## Blockers

- List any current blockers here (e.g. missing API keys, failing tests, merge conflicts).
- Agents should update this when they hit or clear a blocker.
