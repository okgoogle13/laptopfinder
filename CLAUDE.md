# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

# Validate a Stage 2 fixture and run the decision engine
make decide FIXTURE=tests/fixtures/stage2/ebay_facts_grounded.json

# Run Stage 1 + Stage 2 + decision in sequence using paired fixtures
make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json

# Run the live pipeline on raw text (requires API keys in .env)
make live SOURCE=feed.txt

# Run benchmark scraper against saved HTML pages
.venv/bin/python -m laptopfinder.scrape_benchmark --html-dir saved_pages/ --out data/benchmark/benchmark.jsonl

# Evidence pipeline — normalize telemetry files in data/evidence/raw/ and append to aggregated.jsonl
make evidence-run

# Evidence pipeline dry-run — parse and append but skip archiving and handoff generation
make evidence-run-dry

# Evidence pipeline — reset parsed/archived state for a re-run
make evidence-reset
```

**Environment:** uses `.venv` (uv-managed). Always invoke Python as `.venv/bin/python` or `.venv/bin/pytest`, not the system Python. Copy `.env.example` → `.env` and fill in `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY` before running the live pipeline.

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
2. Risk gate failure (risk_score > 3.0, or too many missing fields) → `SKIP`
3. UMA platform (Apple Silicon Max/Ultra, Strix Halo) with system RAM ≥ 32GB → `SHORTLIST`
4. eGPU bundle, VRAM ≥ 16GB, or **touchscreen exception** (VRAM ≥ 12GB + `touchscreen_digitizer` present) → `SHORTLIST`
5. Otherwise → `SKIP`

Radeon mobile GPUs surface a buyer disclosure note (`radeon_ecosystem_disclosure`) but are NOT penalized at the risk gate — evaluated at the same risk_score ≤ 3.0 threshold as all other listings.

Also computes a `llm_index_score` (0–100): capacity points (max 60) + GPU generation points (max 25) + seller reward/risk modifier (~±20) − uncapped deductions. The score is informational and never gates `recommended_action`. All thresholds driving these rules (`standard_mobile_min_gb`, `touchscreen_exception_min_gb`, `uma_unified_min_gb`) live in `vram_gating_logic` inside `static_reference_layer.json`. The UMA score ceiling (formerly 75) was removed 2026-06-30 — Apple Silicon and Strix Halo UMA platforms now compete at the full 0–100 scale.

`decide()` accepts an optional `workload` parameter. When `workload="text_llm"`, discrete CUDA/ROCm candidates that would otherwise SHORTLIST are routed to SKIP with a `paradigm_note` explaining the UMA alternative.

**Evidence Pipeline** (`src/laptopfinder/runners/evidence_pipeline.py`)  
A secondary sub-pipeline that derives hardware spec requirements from real macOS workload telemetry rather than static config. Workflow:
1. Drop telemetry files (screenshots or terminal logs) into `data/evidence/raw/`
2. `make evidence-run` → generates Gemini prompts in `data/evidence/prompts_for_gemini/`
3. Human pastes each prompt into the Gemini web UI and saves the resulting JSON files to `data/evidence/parsed/`
4. `make evidence-run` → parses files from `parsed/`, appends to `data/evidence/aggregated.jsonl`, and archives originals.
5. At ≥ 5 records → generates `data/evidence/claude_handoff.txt` using `prompts/claude_evidence_analyzer.txt`
6. Human pastes handoff into Claude Pro and saves the JSON response as `data/evidence/targets.json`
7. `targets.json` (validated against `schemas/evidence_targets.schema.json`) feeds into `static_reference_layer.json` or a runtime override

**Benchmark Scraper** (`src/laptopfinder/scrape_benchmark.py`)  
Converts saved HTML pages or JSON API payloads from eBay AU / FB Marketplace / Gumtree into Stage 2 fixture format (`handoff_packet + full_listing_text + analysis_output stub`). CSS selectors are best-guess — verify against real saved pages before trusting output. Input modes: `--html-dir`, `--html-file`, `--urls`, `--ebay-api`. Platform auto-detected from filename prefix or URL hostname.

**Discovery Blind Spots (documented 2026-07)**  
1. **RAM/VRAM conflation** — eBay AU search surfaces "16GB RAM" (system) listings alongside "16GB VRAM" listings. The Stage 1 hint/fact firewall catches misclassification downstream, but raw discovery may return irrelevant results. Manual photo/spec-sheet verification of VRAM is mandatory on any hit flagged by the search heuristics in `prompts/comet_discovery_agent.txt`.  
2. **Mislabelled eGPU bundles** — sellers list "RTX 3090 Laptop" when the GPU is in an external enclosure (Razer Core X, OCuLink dock). `_has_egpu_bundle()` in `decide.py` handles this only when enclosure keywords appear in the listing text; listings omitting the enclosure brand name will be scored as internal discrete GPU laptops.  
3. **Niche workstation imports** — ASUS ProArt P16, ThinkPad P-series, and similar non-gaming chassis from overseas resellers carry the `OVERSEAS_IMPORT` −10 seller penalty. High-value Strix Halo and Ada workstation units from international sellers may still warrant manual review despite the scoring penalty.

**Static Reference Layer** (`config/static_reference_layer.json`)  
The single source of truth for all scoring weights, VRAM tier thresholds, target GPU/model lists, watch lists, UMA chip patterns, Radeon mobile GPUs, eGPU enclosure names, risk gate limits, geolocation filters, and the data integrity exclusion regex. Change scoring/thresholds here, not in Python source. `decide.py` loads it at runtime via `load_ref()`.

**Silicon Profiles** (`config/silicon_profiles.yaml`)  
Paradigm definitions (`apple_silicon_uma`, `amd_strix_halo_uma`, `discrete_cuda`, `discrete_rocm`) and workload preferences for `text_centric_llm_inference`. Read by agents and prompts; not loaded at runtime by `decide.py`.

**Scoring Weights** (`config/scoring_weights.yaml`)  
Per-workload weight profiles for `score_text_llm_candidate()`. Profiles: `text_llm_default`, `training_or_diffusion`. Per-paradigm ecosystem and thermal multipliers live here, not in Python.

**Hardware Taxonomy** (`data/hardware_taxonomy.json`)  
Representative hardware entries by paradigm (bandwidth_gbps, ram_gb, inference_stack). Input to `score_text_llm_candidate()` via `batch_decide()`.

**Research Dossier** (`research/alternative_silicon_dossier_june2026.md`)  
Synthesised alternative silicon findings (AU market, June 2026). Source for agent and prompt grounding.

**Live Pipeline Runners** (`src/laptopfinder/runners/`)  
- `comet.py` — Gemini 3.1 Pro via `google-genai`; runs the `prompts/comet_discovery_agent.txt` prompt to produce Stage 1 JSON
- `aistudio.py` — Gemini 3.1 Pro via AI Studio; runs `prompts/ai_studio_runtime.txt` for Stage 2 analysis
- `claude_audit.py` — Anthropic API; optional post-decision audit pass
- `perplexity.py` — Perplexity API; deep research runner

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

## Tooling context

This project is developed using **Antigravity IDE** as the visual environment with **Claude Code CLI** running in the integrated terminal. `AGENTS.md` is a symlink to `CLAUDE.md`, ensuring a single source of truth for both tools.

**MCP:** Antigravity IDE is the host MCP client. Claude Code has native file access and shell execution, but Antigravity handles any MCP connections. Desktop Commander and Filesystem MCP are redundant for this project.

**Agent hook config:** maintain hook policy in `config/agent_hooks.json` and sync tool-specific files with `.venv/bin/python scripts/sync_agent_hooks.py`. Do not hand-edit `.claude/settings.json`, `.claude/settings.local.json`, or `.codex/hooks.json` independently.

**Agent Peer Review Philosophy:** Reserve Codex/Claude peer review strictly for the unstructured boundary where deterministic tooling fails: English execution plans, English prompt files, and cross-config policy logic. Do not build LLM validation skills for invariants that are already enforced by JSON schemas, Python firewalls, or `make test`.

## Sprint tracking

See `memory/project/sprint.md` and `TASKS.md` for current item-level tracking.
