---
name: scrape-benchmark
description: Design decisions, caveats, and known risks for scrape_benchmark.py
metadata:
  type: project
---

# scrape_benchmark.py

**Location:** `src/laptopfinder/scrape_benchmark.py`
**Run as:** `python -m laptopfinder.scrape_benchmark`

## What it does
Converts saved HTML pages or JSON API payloads from eBay AU / FB Marketplace / Gumtree into Stage 2 fixture format (`handoff_packet + full_listing_text + analysis_output stub`).

## Input modes (all additive)
| Flag | Input |
|------|-------|
| `--urls urls.txt` | Live HTTP fetch (likely blocked by eBay/FB) |
| `--html-dir saved_pages/` | Directory of `.html` or `.json` files |
| `--html-file f1.html f2.json` | Individual files, auto-detects content type |
| `--ebay-api response.json` | eBay FindingAPI or Browse API response |

Platform detected from URL hostname or filename prefix (`ebay_*`, `fb_*`, `gumtree_*`).

## Output format
JSONL — one Stage 2 fixture per line. `inferred_*` fields are null (Stage 1 not yet run). `analysis_output` is null (Stage 2 not yet run). `_meta` carries seller info for benchmark tracking.

Use `--format stage1` to output Stage 1 fixture arrays instead.

## Key design decisions
- `full_listing_text` is always raw, unedited text — never fabricated, never `json.dumps()`
- Missing fields → null, never inferred
- Falls back to regex extraction if bs4/lxml not installed (coarser output)
- `process_input(path_or_url)` is a convenience function for ad-hoc single-item use from a REPL

## Known caveats (verify against real pages before trusting)
- **eBay:** CSS selectors (`x-item-title`, `x-price-primary`, `ux-layout-section--features`) are best-guess — eBay changes markup regularly. Inspect a saved page in DevTools if extraction looks wrong.
- **FB Marketplace:** Heavily client-rendered. JSON-LD extraction is the most reliable surface. If `full_listing_text` is empty, try DevTools Network intercept to get the API JSON instead.
- **Gumtree:** `price-amount` and `listing-title` selectors are educated guesses against real DOM. May need adjustment.
- **eBay live fetch:** eBay blocks simple HTTP requests. `--urls` mode will likely fail; always prefer `--html-dir` with saved pages.

## Dependencies
```
pip install beautifulsoup4 lxml requests
```
Falls back gracefully to stdlib urllib + regex if absent.
