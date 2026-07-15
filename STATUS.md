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

*Completed Tasks:*
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

- Example:
  - [ ] eBay OAuth token expired — must re-run `scripts/authenticate_ebay.sh`.
  - [ ] Decide.py RAM schema fix not yet applied.
