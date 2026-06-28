---
name: scrape-benchmark
description: Design decisions, known caveats, and CSS selector risks for scrape_benchmark.py
metadata:
  type: reference
---

# scrape_benchmark.py

**Location:** `src/laptopfinder/scrape_benchmark.py`  
**Run as:** `python -m laptopfinder.scrape_benchmark`

## What it does

Converts saved HTML pages or JSON API payloads (eBay AU / FB Marketplace / Gumtree) into Stage 2 fixture format: `{handoff_packet, full_listing_text, analysis_output stub}`. Platform auto-detected from filename prefix or URL hostname.

## Input modes

| Flag | Source |
|------|--------|
| `--html-dir saved_pages/` | Directory of `.html` or `.json` files |
| `--html-file f1.html` | Individual files |
| `--urls urls.txt` | Live HTTP fetch (likely blocked by eBay/FB — avoid) |
| `--ebay-api response.json` | eBay FindingAPI or Browse API response |
| `--format stage1` | Output Stage 1 fixture arrays instead of Stage 2 |

## Output

JSONL — one Stage 2 fixture per line. `inferred_*` fields are null (Stage 1 not yet run). `analysis_output` is null (Stage 2 not yet run). `_meta` carries seller info for benchmark tracking.

## Key design decisions

- `full_listing_text` is always raw, unedited text — never fabricated or json.dumps()'d
- Missing fields → null, never inferred
- Falls back to regex extraction if bs4/lxml not installed (coarser output)
- `process_input(path_or_url)` convenience function for ad-hoc REPL use

## Known caveats — verify before trusting

- **eBay selectors** (`x-item-title`, `x-price-primary`, `ux-layout-section--features`) are best-guess — eBay changes markup regularly. Inspect a saved page in DevTools if extraction looks wrong.
- **FB Marketplace** is heavily client-rendered. Scraper tries JSON-LD, then falls back to parsing `__REQUIRE__` / `RelayPrefetchedStreamCache` JS blobs. If still empty, use DevTools Network tab to intercept the API JSON directly.
- **Gumtree** selectors (`price-amount`, `listing-title`) are educated guesses — may need adjustment against a real saved page.
- **eBay live fetch** is reliably blocked. Always use `--html-dir` with saved pages.

## Dependencies

```
pip install beautifulsoup4 lxml requests
```

Falls back gracefully to stdlib urllib + regex if absent.
