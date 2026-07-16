# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Response structure (laptopfinder-specific)

Every substantive reply in this repo ends with a `Next steps` section (3–5 deterministic, terminal-ready commands, no meta-advice). Choose commands by what changed:

- **Python logic changes** (`core.py`, `decide.py`, `ingest_csv.py`, etc.) → relevant `make test` / targeted `pytest` node id, plus the fixture path under `tests/fixtures/stage1/` or `tests/fixtures/stage2/` that exercises it.
- **Config changes** (`static_reference_layer.json`, `silicon_profiles.yaml`, `scoring_weights.yaml`, `hardware_taxonomy.json`) → `make pipeline STAGE1=... STAGE2=...` to show the new thresholds/weights take effect, plus `make test` to confirm no regression.
- **Runner/integration changes** (`ebay_sniper.py`, `hunt.py`, `runners/legacy/ebay_hunter.py`, evidence pipeline) → the narrowest applicable dry/test path (`make hunt CONFIG=... DRY_RUN=1`) rather than a full live run unless explicitly requested.

Prefer commands already documented below (make targets, `laptopfinder.scrape_benchmark`, etc.) over inventing new invocations.

This rule is hook-enforced, not just prose: `.claude/hooks/check-next-steps.sh` runs as a `Stop` hook (wired via `config/agent_hooks.json`, synced to `.claude/settings.json` / `.codex/hooks.json` by `scripts/sync_agent_hooks.py`) and blocks any substantive reply missing a `## Next steps` / `**Next steps**` section. It's a plain transcript string-check — no LLM call.

## Commands

```bash
# Run all tests
make test
# equivalent: .venv/bin/python -m pytest tests/ -v

# Run a single test file
.venv/bin/python -m pytest tests/test_decide.py -v

# Run a single test by name
.venv/bin/python -m pytest tests/test_decide.py::TestDecide::test_high_risk_skipped -v

# Lint
make lint
# equivalent: .venv/bin/python -m ruff check src/ tests/

# Zero-LLM snapshot of runner/evidence state + NEXT_TASK queue
make status

# Run Stage 1 + Stage 2 + decision in sequence using paired fixtures
make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json

# Run the token-free eBay sniper daemon (single-pass or continuous; requires 1Password-backed .env)
make live
# equivalent: op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper

# Run an ad hoc, JSON-config-driven discovery sweep (Browse API + Gemini enrichment + decide())
make hunt CONFIG=config/runs/desktop_replacement.json
# add DRY_RUN=1 to suppress email/state writes regardless of what the config says
make hunt CONFIG=config/runs/desktop_replacement.json DRY_RUN=1

# Run benchmark scraper against saved HTML pages
.venv/bin/python -m laptopfinder.scrape_benchmark --html-dir saved_pages/ --out data/benchmark/benchmark.jsonl

# eBay OAuth flow
scripts/authenticate_ebay.sh

# Batch CSV ingestion → data/shortlist_candidates.jsonl
.venv/bin/python -m laptopfinder.ingest_csv <csv_path>

# Render JSONL shortlist → output/shortlist/purchase_matrix.md
.venv/bin/python scripts/render_matrix.py

# Supporting eBay tooling (run via op_wrap.sh or op run for credentialed calls)
.venv/bin/python scripts/ebay_feed_cache.py       # pre-cache Feed API snapshots
.venv/bin/python scripts/ebay_sold_baseline.py     # sold price medians via Finding API
.venv/bin/python scripts/scan_market_gaps.py       # price drift / watch-list sweep
.venv/bin/python scripts/inject_config.py          # inject SRL values into prompt sentinels
```

`make live` and `make hunt` are the only live-discovery Makefile targets — everything else above is invoked directly with `.venv/bin/python`. `runners/legacy/` (`ebay_hunter.py`, `ebay_deals.py`, `evidence_pipeline.py`, `claude_audit.py`) holds retired-but-still-imported modules: `hunt.py` calls into `runners.legacy.ebay_hunter.run()` directly, so don't delete it. Treat everything under `runners/legacy/` as maintenance-only — no new features there.

**Environment:** uses `.venv` (uv-managed). Always invoke Python as `.venv/bin/python` or `.venv/bin/pytest`, not the system Python. Copy `.env.example` → `.env` and configure 1Password `op://...` references for `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, etc. Always execute live scripts via `op run --env-file=.env --` to securely inject credentials.

## Architecture

The pipeline has two offline-testable stages plus a decision engine, all driven by JSON fixtures in tests:

**Stage 1 — Discovery** (`core.py: run_stage1`)  
Validates raw LLM output (a JSON array of candidates) against `schemas/stage1.discovery.schema.json` and enforces the **hint/fact firewall**: Stage 1 candidates may only carry `inferred_*` prefixed fields. Any fact-shaped key (`gpu`, `vram_capacity`, etc.) is rejected immediately. This is a hard constraint — Stage 1 must never promote a hint to a fact.

**Stage 1A — Handoff**  
A human or agent assembles the selected candidate's hints into a handoff packet (validated against `schemas/stage1a.handoff.schema.json`). Enforces strict enum values `["GPU", "CPU", "RAM", "SYSTEM", "OTHER"]` for `inferred_component_category`. This packet is the only thing that crosses into Stage 2; Stage 1 output is never passed directly.

**Stage 2 — Analysis** (`core.py: run_stage2`)  
Validates the handoff packet + full listing text + LLM analysis output. Two firewalls run in sequence:
1. **Data integrity check**: listing title and full text are matched against `data_integrity.exclusion_regex` in `static_reference_layer.json`. Parts-only / salvaged chassis listings raise `ValueError` immediately.
2. **Grounding firewall**: every fact in `extracted_data` must appear verbatim (word-boundary regex match) in `full_listing_text`. Ungrounded facts cause an immediate `ValueError`.

Schema notes:
- `vram_capacity` is a discriminated object `{semantic_value: number, verbatim_quote: string}|null` rather than a flat string.
- `missing_information` is a discriminated object of 6 boolean flags (`gpu`, `vram`, `cpu`, `ram`, `storage`, `condition`) indicating if each core component attribute is missing.
- Missing data → `null`; never fabricate from category or price.

**Decision Engine** (`decide.py: decide`)  
Reads a validated Stage 2 analysis and `config/static_reference_layer.json` to compute a `SHORTLIST` / `MONITOR` / `SKIP` recommendation. Decision logic in priority order:
1. Watch-list GPU → `MONITOR` (too new/unreleased)
2. Risk gate failure (risk_score > 3.0, or too many missing fields) → `SKIP` — the gate is `<=`, so exactly 3.0 passes; 3.1 does not
3. UMA platform (Apple Silicon Max/Ultra, Strix Halo) with system RAM ≥ 32GB → `SHORTLIST`
4. eGPU bundle, VRAM ≥ 16GB, or **touchscreen exception** (VRAM ≥ 12GB + `touchscreen_digitizer` present) → `SHORTLIST`
5. Otherwise → `SKIP`

Radeon mobile GPUs surface a buyer disclosure note (`radeon_ecosystem_disclosure`) but are NOT penalized at the risk gate — evaluated at the same risk_score ≤ 3.0 threshold as all other listings.

Also computes a `llm_index_score` (0–100): capacity points (max 60) + GPU generation points (max 25) + seller reward/risk modifier (~±20) − uncapped deductions. The score is informational and never gates `recommended_action`. All thresholds driving these rules (`standard_mobile_min_gb`, `touchscreen_exception_min_gb`, `uma_unified_min_gb`) live in `vram_gating_logic` inside `static_reference_layer.json`. The UMA score ceiling (formerly 75) was removed 2026-06-30 — Apple Silicon and Strix Halo UMA platforms now compete at the full 0–100 scale.

`decide()` accepts an optional `workload` parameter. When `workload="text_llm"`, discrete CUDA/ROCm candidates that would otherwise SHORTLIST are routed to SKIP with a `paradigm_note` explaining the UMA alternative.

**Evidence Pipeline** (`src/laptopfinder/runners/legacy/evidence_pipeline.py`)  
A secondary, legacy sub-pipeline that derives hardware spec requirements from real macOS workload telemetry rather than static config. No Makefile target currently wires it up — invoke directly (`.venv/bin/python -m laptopfinder.runners.legacy.evidence_pipeline`) if reviving this workflow. Workflow:
1. Drop telemetry files (screenshots or terminal logs) into `data/evidence/raw/`
2. Run the pipeline → generates Gemini prompts in `data/evidence/prompts_for_gemini/`
3. Human pastes each prompt into the Gemini web UI and saves the resulting JSON files to `data/evidence/parsed/`
4. Run the pipeline again → parses files from `parsed/`, appends to `data/evidence/aggregated.jsonl`, and archives originals.
5. At ≥ 5 records → generates `data/evidence/claude_handoff.txt` using `prompts/claude_evidence_analyzer.txt`
6. Human pastes handoff into Claude Pro and saves the JSON response as `data/evidence/targets.json`
7. `targets.json` (validated against `schemas/evidence_targets.schema.json`) feeds into `static_reference_layer.json` or a runtime override

**Benchmark Scraper** (`src/laptopfinder/scrape_benchmark.py`)  
Converts saved HTML pages or JSON API payloads from eBay AU / FB Marketplace / Gumtree into Stage 2 fixture format (`handoff_packet + full_listing_text + analysis_output stub`). CSS selectors are best-guess — verify against real saved pages before trusting output. Input modes: `--html-dir`, `--html-file`, `--urls`, `--ebay-api`. Platform auto-detected from filename prefix or URL hostname.

**Live eBay Discovery** (`src/laptopfinder/runners/` + `scripts/`)  
Two independent live paths since the sniper-simplification refactor — there is no single "primary" runner:
- `runners/ebay_sniper.py` (`make live`) — Token-free, zero-LLM daemon. Polls the Browse API directly, applies `static_reference_layer.json` gating in-process, and alerts via macOS iMessage. No Gemini enrichment, no Stage 2 grounding pass — flagship national sweep + local Melbourne basement-price sweep. Simplest and cheapest path to run continuously.
- `runners/hunt.py` (`make hunt CONFIG=...`) — Ad hoc, JSON-config-driven sweep for heavier discovery runs. Loads a `config/runs/*.json` operator config and delegates to `runners/legacy/ebay_hunter.py`, which owns Browse API acquisition, Gemini enrichment, `run_stage2` grounding, `decide()` scoring, and email alerting.
- `runners/legacy/ebay_hunter.py` — retired from being the standalone "primary" runner but still the engine behind `make hunt`; treat as maintenance-only.
- `runners/legacy/ebay_deals.py`, `scripts/ebay_feed_cache.py`, `scripts/ebay_sold_baseline.py`, `scripts/scan_market_gaps.py` — supporting helpers for clearance scanning, feed caching, sold price baselines, and watch-list drift sweeps. Run directly with `.venv/bin/python`.
- `ebay_taxonomy.py` — category ID + Browse API aspect filter helpers; governs all Browse queries.
- `ebay_api.py`, `comet.py`, `aistudio.py`, `perplexity.py` have been deleted (folded into `ebay_hunter.py` / deprecated per GitHub issues #13–14) — do not reference them as live paths.

**CSV / Value-Ranking Pipeline**  
`ingest_csv.py` → `build_shortlist_value.py` → `render_matrix.py`
- `src/laptopfinder/ingest_csv.py` — Reads eBay CSV export; calls Gemini to extract specs; runs `decide()`; appends SHORTLIST results to `data/shortlist_candidates.jsonl`. Invoke via `.venv/bin/python -m laptopfinder.ingest_csv <csv_path>` (no Makefile target).
- `scripts/build_shortlist_value.py` — Ranks candidates across 4 form-factor lanes by VRAM/RAM tier; outputs `output/shortlist/shortlist_value.jsonl` + `output/shortlist/shortlist_value.md`.
- `scripts/render_matrix.py` — Renders JSONL shortlist → sorted Markdown decision table at `output/shortlist/purchase_matrix.md`. Invoke via `.venv/bin/python scripts/render_matrix.py` (no Makefile target).

**Discovery Blind Spots (documented 2026-07)**  
1. **RAM/VRAM conflation** — eBay AU search surfaces "16GB RAM" (system) listings alongside "16GB VRAM" listings. The Stage 1 hint/fact firewall catches misclassification downstream, but raw discovery may return irrelevant results. Manual photo/spec-sheet verification of VRAM is mandatory on any hit flagged by the search heuristics in `prompts/comet_discovery_agent.txt`.  
2. **Mislabelled eGPU bundles** — sellers list "RTX 3090 Laptop" when the GPU is in an external enclosure (Razer Core X, OCuLink dock). `_has_egpu_bundle()` in `decide.py` handles this only when enclosure keywords appear in the listing text; listings omitting the enclosure brand name will be scored as internal discrete GPU laptops.  
3. **Niche workstation imports** — ASUS ProArt P16, ThinkPad P-series, and similar non-gaming chassis from overseas resellers carry the `OVERSEAS_IMPORT` −10 seller penalty. High-value Strix Halo and Ada workstation units from international sellers may still warrant manual review despite the scoring penalty.

**Static Reference Layer** (`config/static_reference_layer.json`)  
The single source of truth for all scoring weights, VRAM tier thresholds, target GPU/model lists, watch lists, UMA chip patterns, Radeon mobile GPUs, eGPU enclosure names, risk gate limits, and the data integrity exclusion regex. Change scoring/thresholds here, not in Python source. `decide.py` loads it at runtime via `load_ref()`.

`min_vram_to_shortlist_gb` in the SRL is **deprecated and unused** — `decide.py` does not read it. The live discrete-VRAM shortlist gate is `vram_gating_logic.standard_mobile_min_gb` (16 GB), with `vram_gating_logic.touchscreen_exception_min_gb` (12 GB) as the touchscreen path. UMA platforms use `uma_platforms.min_total_ram_gb_to_shortlist`. Do not edit `min_vram_to_shortlist_gb` expecting it to change routing behavior.

**Silicon Profiles** (`config/silicon_profiles.yaml`)  
Paradigm definitions (`apple_silicon_uma`, `amd_uma`, `discrete_cuda`, `discrete_rocm`) and workload preferences for `text_centric_llm_inference`. Read by agents and prompts; not loaded at runtime by `decide.py`.

**Scoring Weights** (`config/scoring_weights.yaml`)  
Per-workload weight profiles for `score_text_llm_candidate()`. Profiles: `text_llm_default`, `training_or_diffusion`. Per-paradigm ecosystem and thermal multipliers live here, not in Python.

**Hardware Taxonomy** (`data/hardware_taxonomy.json`)  
Representative hardware entries by paradigm (bandwidth_gbps, ram_gb, inference_stack). Input to `score_text_llm_candidate()` via `batch_decide()`.

**Research Dossier** (`research/alternative_silicon_dossier_july2026.md`)  
Canonical alternative silicon findings (AU market, July 2026). Source for agent and prompt grounding. Legacy raw outputs live under `research/archive/`.

**Legacy Live Pipeline Runners** (`src/laptopfinder/runners/legacy/`)  
`comet.py`, `aistudio.py`, and `perplexity.py` (raw-text Gemini/Perplexity discovery runners) have been deleted entirely as part of the legacy-runner deprecation. What remains under `runners/legacy/`:
- `claude_audit.py` — Anthropic API; optional post-decision audit pass
- `ebay_hunter.py` — still imported by `runners/hunt.py`; see Live eBay Discovery above
- `ebay_deals.py` — clearance/Deal & Event API scanning helper
- `evidence_pipeline.py` — see Evidence Pipeline above
- `hunter/` — decomposed submodules (`api.py`, `enrich.py`, `llm.py`, `score.py`, `search.py`, `state.py`, `alert.py`) backing `ebay_hunter.py`

**Perplexity Web MCP** (`pwm` CLI, `docs/pwm_workflow_catalog.md`)
`perplexity-web-mcp-cli` is a separate, current integration from the deleted `perplexity.py` runner above — don't conflate the two. Verify live status anytime with `pwm doctor` / `pwm setup list`; don't trust planning docs claiming it's unconfigured without re-checking. Named Deep Research workflows (`lf-floor-sync`, `lf-price-baseline`, `lf-buy-jury`, `lf-paradigm-debate`, `lf-sniper-shortlist`, `lf-seller-scrutiny`, `lf-status-rollup`) are catalogued in `docs/pwm_workflow_catalog.md`. Per the LLM boundary rule below, PWM output is a qualitative research input only — never a `decide.py` routing input. Shell functions (`pwmh`, `lf-score`, `lf-watchlist`, `lf-price-sweep`, `compare`, etc.) live outside this repo in `~/.config/pwm/workflows.zsh` (sourced by `~/.zshrc`) — not in git, won't show up in an in-repo grep.

## Key invariants

- **Firewall is enforced in Python, not the prompt.** `run_stage1` and `run_stage2` in `core.py` are the enforcement point. Tests in `test_stage1_fixtures.py` and `test_stage2_fixtures.py` verify rejection of invalid fixtures.
- **Schema constraints replace Python validation.** `risk_score` range [0.0, 10.0] is a JSON Schema `minimum`/`maximum` — don't add a redundant Python check.
- **`static_reference_layer.json` is the governance layer.** Scoring weights, tier thresholds, and hardware lists live there. Adding a new target GPU means editing the JSON, not the Python.
- **Fixture-driven development.** All logic changes must be verifiable with `make test`. Add or update fixtures in `tests/fixtures/stage1/` or `tests/fixtures/stage2/` alongside any schema or scoring change.
- **Stage 2 fixture format:** each file contains `handoff_packet`, `full_listing_text`, and `analysis_output` at the top level. `run_stage2_from_fixture` unwraps these.
- **Missing data → null.** Never infer specs from category or price averages. If the listing text doesn't state it, the field is null.
- **Karpathy-style Python.** Flat structures, no deep OOP, no custom exceptions. Schema constraints replace Python validation.
- **`score_text_llm_candidate()` is taxonomy-driven.** It operates on `data/hardware_taxonomy.json` entries, not Stage 2 analysis dicts. Per-paradigm scores come from `config/scoring_weights.yaml`, not Python literals.
- **UMA ceiling removed.** `apple_silicon.score_ceiling` is `null` in the SRL. Do not re-add a ceiling — UMA platforms compete at full 0–100 `llm_index_score` scale.
- **`_apply_architecture_penalty()` is a per-listing Turing heuristic, not a pairwise comparator.** `decide()` scores one listing at a time, so it cannot resolve a true Turing-vs-Ada same-VRAM comparison. Instead it applies the SRL's `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` whenever a listing's GPU resolves to the `Turing` generation (via the same `gpu_generation_by_name` lookup `_gpu_generation_points()` uses, exposed as the shared helper `_resolve_gpu_generation()`) and a VRAM tier is present — regardless of whether an Ada-generation comparator exists in the same batch. True pairwise resolution is a BACKLOG item for a future batch/shortlist-ranking pass.

## Tooling context

This project is developed using **Antigravity IDE** as the visual environment with **Claude Code CLI** running in the integrated terminal. `AGENTS.md` is a symlink to `CLAUDE.md`, ensuring a single source of truth for both tools.

**MCP:** Antigravity IDE is the host MCP client. Claude Code has native file access and shell execution, but Antigravity handles any MCP connections. Desktop Commander and Filesystem MCP are redundant for this project.

**Agent hook config:** maintain hook policy in `config/agent_hooks.json` and sync tool-specific files with `.venv/bin/python scripts/sync_agent_hooks.py`. Do not hand-edit `.claude/settings.json`, `.claude/settings.local.json`, or `.codex/hooks.json` independently.

**Agent Peer Review Philosophy:** Peer review is optional. Run `bash archive/scripts/deep_plan_peer_review.sh <plan-file>` before executing plans that touch SRL governance, Python firewall logic (`core.py`), or multi-file architectural refactors. For everything else — bugfixes, config edits, fixture additions — `make test` is sufficient.

## Sprint tracking

Four planning artifacts exist; each has exactly one job. Do not let sprint-level task lists spread across more than one of them — that produced real drift once already (fixed 2026-07-16) where the same Sprint 9 list existed in three places and `sprint.md` had sprints marked "pending"/"active" that were actually long shipped.

- **`STATUS.md`** — the entry point, read first every session. Owns the single ordered `NEXT_TASK` queue and `Blockers`. Terse by design; work the first `NEXT_TASK` item without asking "what next?" if it's non-empty.
- **`memory/project/sprint.md`** — the *only* place sprint-by-sprint status lives. Each entry is Why → Status → Changes shipped, append-only, one section per sprint. This is the canonical history of what happened and why.
- **`TASKS.md`** — archive index (one-line pointers into `sprint.md`, not duplicate checklists) + the unsprinted `BACKLOG` + evergreen operator reference material (User Testing Guide, Common Failure Modes) that isn't tied to any single sprint. Never re-add a full sprint checklist here — link to `sprint.md` instead.
- **`memory/plans/*.md`** — dated, one-shot deep-plan artifacts (delegation maps, task-by-task batches for subagents) produced by planning skills to execute a specific chunk of work. Archival once the work lands; not maintained afterward. Not a status tracker — check `sprint.md` for whether the plan's work actually shipped, don't assume a plan file being present means it's still active.

Run `make status` for a mechanical snapshot of runner/evidence state (see Commands above) — it's a pull, not a hook, so it doesn't fire on every turn.

Every `sprint.md` entry and `NEXT_TASK` item must carry a one-line Definition of Done and fit in a single sitting. If it doesn't fit in one sitting, split it into sub-bullets rather than writing a vaguer, larger item.

## Agent Workflow Defaults (Claude Code)

When Claude Code works on this repo:

- Always read, in this order:
  1. STATUS.md
  2. TASKS.md
  3. sprint.md (if present)
  4. CLAUDE.md

- Use STATUS.md as the source of truth for:
  - current sprint and phase,
  - progress by area,
  - NEXT_TASK,
  - blockers.

- NEXT_TASK rules:
  - If `STATUS.md` has a NEXT_TASK section with items, work on the **first** item.
  - Do not ask the user “what next?” if NEXT_TASK is non-empty.
  - When a NEXT_TASK item is completed:
    - update STATUS.md (mark it done or remove it),
    - briefly note what changed,
    - then move to the next item.

- Task and sprint updates:
  - When completing a task, update TASKS.md and/or sprint.md to reflect status (`todo` → `doing` → `done`).
  - Keep edits lean and factual (no long essays).

- Spec-to-Task Bridge (Strict):
  - If you are asked to design a new workflow, brainstorm a feature, or write a specification document (e.g., in `docs/`), you MUST immediately extract the actionable implementation steps and append them to `TASKS.md` and `sprint.md`, and queue the first step in `STATUS.md`.
  - Never leave a newly designed workflow un-tracked.

- Blockers:
  - If you hit a genuine blocker (auth, destructive ambiguity, invariant conflict, unrecoverable tests):
    - add a short bullet under “Blockers” in STATUS.md,
    - stop and report, instead of guessing.

- Default behavior:
  - Prefer autonomous execution of NEXT_TASK over asking for new instructions.
  - Use CLAUDE.md only as doctrine and guardrails; do not rewrite it unless explicitly instructed or as part of a docs task in NEXT_TASK.

- Pipeline execution:
  - Use `make pipeline STAGE1=... STAGE2=...` to run the offline fixture pipeline.
  - Use `make live` to run the AU sniper daemon (requires credentialed `.env`).
  - Use `make hunt CONFIG=config/runs/desktop_replacement.json DRY_RUN=1` for a dry ad hoc sweep.
  - `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md` are written only by `runners/ebay_sniper.py` (`make live`). `make hunt` (`runners/hunt.py` → `runners/legacy/ebay_hunter.py`) writes `data/hunt_results.jsonl` and `data/corpus.jsonl` instead — a distinct output path, verified 2026-07-16 against `hunter/state.py` `write_jsonl()` call sites. Check which runner produced a result before assuming which file to read.

- LLM boundary (strict):
  - LLMs (Claude, Gemini, Codex, Copilot) MUST NOT alter routing decisions, scores, or thresholds.
  - All routing logic lives in `decide.py` + `config/static_reference_layer.json`.
  - LLM agents are qualitative auditors and researchers only — they read `output/shortlist/latest_shortlist.md` and advise; they never write scores or change SHORTLIST/SKIP outcomes.

## Agent Workflow Defaults (Gemini, Codex, Copilot)

Other agents (Gemini, Codex, Copilot): Read STATUS.md + TASKS.md before starting. Work the first NEXT_TASK item. Update STATUS.md on completion. If blocked, record it in STATUS.md and stop.
