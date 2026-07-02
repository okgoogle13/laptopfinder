# Sprint 2 — Laptopfinder

## Goal

Output a data-backed local LLM hardware purchase decision for Northcote, AU with a $3K used / $5K new budget.

## Architecture Rules

- Primary Fast-Path: Firecrawl + Antigravity CLI.
- No Browserbase, no Chrome Extensions, no Comet Browser automation.
- All authenticated scraping (FB Marketplace) is manual copy-paste into `data/feed_manual.txt`.

## Day 1: Config Injection (Stop Hardcoding)

Write a standalone `scripts/inject_config.py` (no classes, top-level functions only). It must:
- Read `config/static_reference_layer.json` only (silicon_profiles.yaml is NOT loaded in v1)
- Use paired sentinel comments (`<!-- BEGIN_INJECT:X --> ... <!-- END_INJECT:X -->`) for idempotent injection — NOT one-shot `str.replace`
- Replace content between markers in `prompts/comet_discovery_agent.txt` and `prompts/alternative_silicon_*.txt`

Add this target to the Makefile:

```makefile
inject-config:
    .venv/bin/python scripts/inject_config.py
```

## Day 3–4: Firecrawl Fetch & Makefile Wiring

Write `src/laptopfinder/scrape_live.py` (under 50 lines). It should:
- Use `firecrawl-py` (v1 client: `from firecrawl import Firecrawl`, not deprecated `FirecrawlApp`)
- Read a `--urls-file`
- Fetch Markdown
- Strip nav chrome via word-boundary multiline regex: `r'(?im)^\s*(breadcrumb|cart|watchlist|sign in|cookie notice).*$'` — NOT an unbounded substring match
- Write each listing to a separate file `data/feed_live/listing-{n:03d}.txt` via `--out-dir` (not a single blob via `--out`)

Add this target to the Makefile:

```makefile
# Note: intentionally does NOT depend on inject-config.
# Run `make inject-config` separately when config changes.
scrape-and-live:
    @echo "=== Firecrawl fetch ==="
    .venv/bin/python -m laptopfinder.scrape_live --urls-file $(FIRECRAWL_URLS) --out-dir data/feed_live/
    @echo "=== Live pipeline (per listing) ==="
    @for f in data/feed_live/listing-*.txt; do $(MAKE) live SOURCE=$$f; done
```

Use `Firecrawl` (v1 client, `from firecrawl import Firecrawl`) — NOT the deprecated `FirecrawlApp`. Nav regex must be word-boundary anchored (`r'(?im)^\s*(breadcrumb|cart|watchlist|sign in|cookie notice).*$'`), not an unbounded substring match. Each listing writes to a separate file in `data/feed_live/` (not a single blob).

## Day 7: Purchase Decision Matrix

Prepare the system to accept a final prompt that:
- Ingests `data/shortlist_candidates.jsonl`
- Outputs a Markdown table sorted by recommended action (SHORTLIST/MONITOR/SKIP) and `llm_index_score`
