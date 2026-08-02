---
name: tooling-usage
description: Operator usage guide for laptopfinder live discovery and tooling
metadata:
  type: reference
---

# Usage Guide — Live Tooling

Relocated 2026-07-02 from `planning/implementation/usage.md` — this file now holds both the active setup notes and the operational guide, so it lives here in `memory/reference/` alongside the other stable reference docs. See [pipeline.md](pipeline.md) for pipeline terminology.

## Tooling Setup

**Primary workflow:** Antigravity IDE (VS Code fork) + Claude Code CLI in the integrated terminal.

- Antigravity provides file explorer, git panel, and integrated terminal
- Claude Code CLI runs in Antigravity's terminal via `claude` command; no extension needed
- `CLAUDE.md` is read automatically by Claude Code
- `AGENTS.md` is a symlink to `CLAUDE.md`, so Antigravity's Gemini agent reads the same project rules
- Both tools share the same source-of-truth project guidance

**MCP:** Desktop Commander and Filesystem MCP are redundant here. Claude Code has native file access and shell execution, so no extra MCP servers are needed for this project.

**Python environment:** uv-managed `.venv`. Always invoke as `.venv/bin/python` or `.venv/bin/pytest`, never system Python. Execute live scripts via `op run --env-file=.env --` to securely inject credentials.

---

## Live eBay Discovery

There are two primary live paths for discovery (the single "primary" runner was deprecated during the sniper-simplification refactor):

### 1. eBay Sniper (`make live`)
**Runner:** `runners/ebay_sniper.py`

Token-free, zero-LLM daemon. Polls the Browse API directly, applies `static_reference_layer.json` gating in-process, and alerts via macOS iMessage. No Gemini enrichment, no Stage 2 grounding pass — flagship national sweep + local Melbourne basement-price sweep. Simplest and cheapest path to run continuously.

**Run:**
```bash
make live
# equivalent: op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper
```

### 2. Ad Hoc Hunt (`make hunt`)
**Runner:** `runners/hunt.py`

Ad hoc, JSON-config-driven sweep for heavier discovery runs. Loads a `config/runs/*.json` operator config and delegates to `runners/legacy/ebay_hunter.py` which owns Browse API acquisition, Gemini enrichment, `run_stage2` grounding, `decide()` scoring, and email alerting.

**Run:**
```bash
make hunt CONFIG=config/runs/desktop_replacement.json
# add DRY_RUN=1 to suppress email/state writes
make hunt CONFIG=config/runs/desktop_replacement.json DRY_RUN=1
```

---

## Status and Pre-flight

### Zero-LLM Snapshot
Run a mechanical snapshot of the runner/evidence state + NEXT_TASK queue.
```bash
make status
```

### PWM Pre-flight Gate
Validates SRL JSON, search query count, token age, and checks the PWM workflow checklist before launching the sniper.
```bash
make pwm-preflight
```

---

## Testing & Offline Pipeline

### Offline Fixture Pipeline
Run Stage 1 + Stage 2 + decision in sequence using paired fixtures to verify routing logic without making live API calls.
```bash
make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json
```

### Tests & Linting
All logic changes must be verifiable with `make test`.
```bash
# Run all tests
make test
# Lint
make lint
```

---

## Supporting Tooling

Run these directly with `.venv/bin/python` (no Makefile targets):

| Script | Purpose |
|--------|---------|
| `scripts/ebay_feed_cache.py` | Pre-cache Feed API snapshots |
| `scripts/scan_market_gaps.py` | Price drift / watch-list sweep |
| `scripts/inject_config.py` | Inject SRL values into prompt sentinels |
| `scripts/render_matrix.py` | Render JSONL shortlist → Markdown table |
| `src/laptopfinder/scrape_benchmark.py` | Convert saved HTML to Stage 2 fixture format |
| `src/laptopfinder/ingest_csv.py` | Batch CSV ingestion → `data/shortlist_candidates.jsonl` |
