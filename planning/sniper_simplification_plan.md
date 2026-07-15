# Laptopfinder Simplification Plan

## Overview
- **Architecture**: Strict two-stage pipeline (Stage 1/1A/2) utilizing `decide.py` for config-driven `SHORTLIST`/`MONITOR`/`SKIP` decisions.
- **Pain Points**: Runner/agent sprawl, excessive JSON handoffs, cluttered directories, and redundant routing logic.
- **Outcome Goal**: A streamlined, daily "AU sniper/watch" run resulting in an actionable shortlist.
- **Strict Boundary**: Spec/routing logic stays compiled in code/configs (`decide.py`, `static_reference_layer.json`). Prompts and agents NEVER route or alter scores; they are strictly qualitative auditors.

## Task Groups

### Group 1: Runners & Makefile (Tasks A–B)
- **Files**: `src/laptopfinder/runners/`, `Makefile`
- **Outcome**: Single entry point for sniper pipeline; clean local dev commands.

### Group 2: Agents & deep plan config (Tasks C–D)
- **Files**: `.agents/`, `deep_plan_config.json`
- **Outcome**: Pruned AI assistant skills and minimal plan configuration.

### Group 3: Decision engine, config, outputs & docs (Tasks E–K)
- **Files**: `src/laptopfinder/decide.py`, `config/static_reference_layer.json`, `output/`, `README.md`, `CLAUDE.md`, `AGENTS.md`
- **Standard Outputs Requirement**: Every successful pipeline run must produce two canonical artifacts written by the primary runner (`src/laptopfinder/runners/ebay_sniper.py`):
  - **Decision JSON**: `output/decisions/latest_decisions.json` (machine-readable; contains states, scores, metadata from `decide.py`).
  - **Shortlist MD**: `output/shortlist/latest_shortlist.md` (human-readable markdown matrix summary).
  - *Note*: These are the only files downstream agents read; scratch JSONL files are internal and removed over time.

---

## Tonight’s Focus (Actionable Sprint)

### Task A: Pick primary AU runner, mark legacy
- **Steps**:
  1. Locate `scripts/ebay_sniper.py` and promote to package level as `src/laptopfinder/runners/ebay_sniper.py`.
  2. Suffix or move other runners (e.g., `ebay_deals.py`, `ebay_hunter.py`, `evidence_pipeline.py`) into a `legacy/` subdirectory.
  3. Expose only `ebay_sniper` in `src/laptopfinder/runners/__init__.py`.
  4. Update `tests/test_ebay_sniper.py` imports.
- **Checks**: Run `ls src/laptopfinder/runners/` and execute `pytest tests/test_ebay_sniper.py` to verify imports.

### Task B: Simplify Makefile
- **Steps**:
  1. Open `Makefile`. Delete legacy/unused target definitions.
  2. Define exactly three clean targets: `test` (runs pytest), `pipeline` (runs pipeline local dry-run/mock), `live` (runs sniper script live).
- **Checks**: Run `make test` and dry-run `make pipeline` to ensure syntax is valid.

### Task C: Prune/archive .agents scaffolding
- **Steps**:
  1. Open `.agents/skills/`.
  2. Move non-essential skills (e.g., `cross-agent-plan-review`, `market-gap-scanner`) to `.agents/archive/`.
  3. Sync configurations or imports that referenced these agents.
- **Checks**: Run `tree .agents/` to verify a minimal, pruned structure.

### Task D: Align deep plan config
- **Steps**:
  1. Open `deep_plan_config.json`.
  2. Strip references to legacy runners or decommissioned agents.
  3. Simplify flow to strictly track the 3 core sub-flows of `ebay_sniper.py`.
- **Checks**: Validate syntax via `cat deep_plan_config.json | jq .` (or equivalent parser).

### Task E: Centralise decide.py as routing source of truth
- **Steps**:
  1. Open `src/laptopfinder/decide.py` and `src/laptopfinder/runners/ebay_sniper.py`.
  2. Ensure `decide.py` alone computes `SHORTLIST`/`MONITOR`/`SKIP` states and applies `config/static_reference_layer.json` thresholds.
  3. Strip runner override conditions; make `ebay_sniper.py` feed candidates to `decide.py` and respect its outputs.
  4. Instruct the runner to write results directly to `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md`.
- **Checks**: Run `pytest tests/test_decide.py` and verify `make pipeline` generates both correct files in `output/`.

---

## Later Sprint (Tasks F–K)
- **F: Consolidate static references**: Move disjointed parameters into `config/static_reference_layer.json` (Effort: ~1h).
- **G: Standardise data outputs**: Clean up layout so `data/` houses input/fixtures, while outputs strictly write to `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md` (Effort: ~1h).
- **H: Enforce Stage 1/1A/2 strictness**: Audit code to prevent hint/fact leaks before Stage 2 (Effort: ~2h).
- **I: Document standard outputs**: Write user guidelines for output files in `README.md` (Effort: docs-only).
- **J: Sniper Run Quick-Start**: Add a rapid 3-step execution guide to `README.md` (Effort: docs-only).
- **K: Update CLAUDE.md and AGENTS.md for simplified pipeline**:
  - **Steps**:
    1. Open `CLAUDE.md` and `AGENTS.md`.
    2. In `CLAUDE.md`, add or update a short “Agent workflow defaults” section that describes the new behaviour:
       - Read `STATUS.md` to find the current sprint and `NEXT_ACTION`.
       - For pipeline work, run `make pipeline` or `make live` (AU sniper) and inspect `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md`.
       - Treat `planning/sniper_simplification_plan.md` as the spec for this sprint; do not redesign the architecture.
    3. In `AGENTS.md`, update agent descriptions to reflect the simplified roles:
       - Claude Code: local implementation of Tasks A–J, small deep implement, one task at a time.
       - Gemini / Perplexity: AU market research, config/watchlist updates (feeding `static_reference_layer.json` and specs).
       - Claude chat: qualitative audit of `output/shortlist/latest_shortlist.md`, helping compare candidates and advise on purchase.
    4. Remove or clearly mark as legacy any references to multi‑agent orchestrators or runners that are no longer part of the main sniper pipeline.
  - **Checks**: Visually review `CLAUDE.md` and `AGENTS.md` to ensure they mention:
    - `STATUS.md` as the “what next” source.
    - `make pipeline` / `make live` and the new `output/…` paths as the main flow.
    - The strict boundary that LLMs don’t route or score, only audit and research.

---

## Agent & LLM Roles
- **Claude Code (Local CLI)**: Implements code restructuring, file movements, and executes validation commands (e.g., `make test`).
- **Gemini / Perplexity (Web)**: Conducts AU market research, gathers hardware profiles, and designs updates for `config/static_reference_layer.json` watchlists.
- **Claude Chat (UI)**: Acts as a qualitative auditor. Reads final outputs (`output/shortlist/latest_shortlist.md`), comments on trade-offs, and provides purchasing advice.
- **CRITICAL BOUNDARY**: Prompts/agents cannot route, score, or alter decisions. All logic remains in standard executable code.

---

## Execution Checklist (for STATUS.md)
- [ ] Task A - Pick primary runner `ebay_sniper.py` and move legacy runners (Files: `src/laptopfinder/runners/` | Validate by: `ls` and `pytest`)
- [ ] Task B - Clean Makefile to include only `test`, `pipeline`, and `live` (Files: `Makefile` | Validate by: `make pipeline`)
- [ ] Task C - Archive non-essential agent skills (Files: `.agents/skills/` | Validate by: `tree`)
- [ ] Task D - Align `deep_plan_config.json` flows with sniper phases (Files: `deep_plan_config.json` | Validate by: `jq .`)
- [ ] Task E - Centralise routing logic in `decide.py` and write to standard output paths (Files: `src/laptopfinder/decide.py`, `src/laptopfinder/runners/ebay_sniper.py` | Validate by: `make pipeline` output checks)
- [ ] Task F - Consolidate static references to `config/static_reference_layer.json` (Files: `config/` | Validate by: `pytest`)
- [ ] Task G - Relocate data files to standardise output directory layout (Files: `data/`, `output/` | Validate by: checking paths after run)
- [ ] Task H - Enforce strict stage firewall boundary rules (Files: `src/laptopfinder/core.py` | Validate by: `pytest`)
- [ ] Task I - Update output schemas and details in user documentation (Files: `README.md` | Validate by: manual review)
- [ ] Task J - Insert quick-start execution instructions to the README (Files: `README.md` | Validate by: manual review)
- [ ] Task K - Update CLAUDE.md and AGENTS.md for simplified pipeline (Files: `CLAUDE.md`, `AGENTS.md` | Validate by: visual review)
