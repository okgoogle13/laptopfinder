# laptopfinder

Two-stage AI pipeline that discovers, filters, and scores Australian second-hand hardware listings (eBay AU, Facebook Marketplace, Gumtree) for local LLM inference.

## Sniper Quick Start

Three steps to run the AU sniper and read results:

```bash
# 1. Authenticate (one-time or when token expires)
scripts/authenticate_ebay.sh

# 2. Run a single-pass dry sweep — no state written, no iMessages sent
op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper --dry-run --once

# 3. Read results
cat output/decisions/latest_decisions.json   # machine-readable hit list
cat output/shortlist/latest_shortlist.md     # human-readable shortlist
```

To start the background daemon: `make live`

**Environment:** `.venv` managed by uv. Copy `.env.example` → `.env` and configure `EBAY_APP_ID`, `EBAY_CERT_ID`, and 1Password `op://...` references. All credentialed commands run via `op run --env-file=.env --`.

## Standard Outputs

Every sniper sweep writes two files:

| File | Purpose |
|------|---------|
| `output/decisions/latest_decisions.json` | Machine-readable JSON array of all hits with action, price, URL, and strategy |
| `output/shortlist/latest_shortlist.md` | Human-readable Markdown summary of SHORTLIST hits only |

These are the only files downstream agents and manual review should read. Overwritten each sweep.

## Architecture & Pipeline

- **Primary Live Path (`ebay_hunter.py`):** The default structured eBay acquisition runner. It calls the Browse API, enriches with Gemini, reuses the Stage 2 grounding firewall and decision engine, and can email shortlist targets.
- **Legacy Live Paths:** The unstructured raw-text runners (e.g., `make pipeline`) and auxiliary API wrappers (e.g., `ebay_api.py`) are legacy, archival, or experimental workflows.
- **Stage 1 — Discovery [LEGACY]:** parses raw search text, extracts candidates, generates `inferred_hint` fields only. Fact-shaped keys are rejected.
- **Stage 1A — Handoff [LEGACY]:** human/agent assembles the selected candidate's hints into a typed handoff packet. Only this packet crosses into Stage 2.
- **Stage 2 — Analysis:** promotes hints to confirmed facts only when `full_listing_text` explicitly supports them (word-boundary regex). `vram_capacity` is `{semantic_value, verbatim_quote}|null`; `missing_information` is 6 boolean flags.
- **Decision Engine (`decide.py`):** outputs `SHORTLIST` / `MONITOR` / `SKIP` plus a `llm_index_score` (0–100). Score is informational; routing is threshold-driven.

## Key Rules

- **Firewall:** Stage 1 hints never become facts without grounding in listing text.
- **Strict null:** missing or ambiguous values are `null`; never inferred from category or price.
- **Governance lives in JSON:** `config/static_reference_layer.json` owns all scoring weights, tier thresholds, and hardware lists. Edit there, not in Python.
- **Fixture-driven:** all logic changes must pass `make test`.

## Gemma Telemetry

To capture quantitative and subjective memory telemetry for local Gemma 2 models (`2b` and `9b`) via Ollama on macOS, run the automated test script:

```bash
./run_gemma_test.sh 2b
./run_gemma_test.sh 9b
```

This will automatically pull the model, start background `vm_stat` logging, and capture `top` PhysMem snapshots before and after an interactive session. The logs land in the project root as `vmstat-log-<model>-<timestamp>.txt` and `physmem-log-<model>-<timestamp>.txt`. The `telemetry_summary.md` document interprets these logs, demonstrating that a 9B model on an 8GB system results in critical memory pressure.

## Australian Market Context

Platforms: eBay AU, Facebook Marketplace, Gumtree. Currency: AUD. Pickup origin: Northcote, VIC.

## Repository Layout

```
config/                          # static_reference_layer.json — single source of truth for all thresholds
data/                            # inputs, fixtures, and accumulated candidate state
output/
  decisions/latest_decisions.json  # sniper hit list (overwritten each sweep)
  shortlist/latest_shortlist.md    # human-readable shortlist (overwritten each sweep)
  shortlist/purchase_matrix.md     # ranked matrix from render_matrix.py
src/laptopfinder/
  core.py                        # Stage 1 / Stage 2 validation + hint/fact firewall
  decide.py                      # decision engine (SHORTLIST / MONITOR / SKIP)
  schemas/                       # JSON Schemas for Stage 1, 1A, Stage 2
  runners/
    ebay_sniper.py               # primary AU sniper daemon
    hunt.py                      # ad hoc JSON-config-driven sweep
    legacy/                      # retired runners (ebay_hunter, ebay_deals, etc.)
tests/
  fixtures/stage1/               # Stage 1 test fixtures
  fixtures/stage2/               # Stage 2 test fixtures
.github/workflows/               # CI (JSON validation + pytest)
```
