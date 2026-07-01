# Section 05 — Makefile and Integration

## Overview

This section wires the three components from sections 02, 03, and 04 into the project's `Makefile` and creates the remaining runtime support files. It assumes `inject_config.py`, `scrape_live.py`, and `render_matrix.py` are all implemented and their test suites pass.

**Dependencies:** section-02-inject-config, section-03-scrape-live, section-04-render-matrix must all be complete before starting this section.

**Files touched:**
- `/Users/okgoogle13/Projects/laptopfinder/Makefile` — modified
- `/Users/okgoogle13/Projects/laptopfinder/data/urls.txt` — created

---

## Tests

There are no new test files for this section. Validation is done by running the full test suite and then smoke-testing the Makefile targets manually.

The integration acceptance criteria are:
1. `make test` — all new and existing tests pass (zero failures, zero errors)
2. `make inject-config` — runs without error against the real prompt files; `git diff` shows content inserted between markers, markers themselves unchanged
3. `make render-matrix` — errors clearly when `data/shortlist_candidates.jsonl` is absent; succeeds and writes `data/purchase_matrix.md` with a sample input
4. `make scrape-and-live FIRECRAWL_URLS=data/urls.txt` — with a valid `FIRECRAWL_API_KEY` in `.env`, fetches listings and writes per-listing files to `data/feed_live/`

---

## Makefile Changes

The existing `/Users/okgoogle13/Projects/laptopfinder/Makefile` defines `.PHONY` on the first line and then lists targets. Add the three new targets and update `.PHONY` to include them.

### Updated `.PHONY` line

Replace the existing `.PHONY` line with:

```makefile
.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset inject-config scrape-and-live render-matrix
```

### New targets to append

Append the following three blocks to the bottom of the Makefile, after the `evidence-reset` target:

```makefile
# Inject config values from static_reference_layer.json into prompt sentinel markers.
# Run explicitly when SRL changes. NOT a dependency of scrape-and-live.
inject-config:
	.venv/bin/python scripts/inject_config.py

# Scrape listing URLs via Firecrawl, then run the live pipeline per listing.
# Requires FIRECRAWL_API_KEY in .env. Does NOT depend on inject-config.
# Usage: make scrape-and-live
#        make scrape-and-live FIRECRAWL_URLS=path/to/other_urls.txt
FIRECRAWL_URLS ?= data/urls.txt

scrape-and-live:
	@echo "=== Firecrawl fetch ==="
	.venv/bin/python -m laptopfinder.scrape_live --urls-file $(FIRECRAWL_URLS) --out-dir data/feed_live/
	@echo "=== Live pipeline (per listing) ==="
	@if ! ls data/feed_live/listing-*.txt 1>/dev/null 2>&1; then \
	    echo "ERROR: scrape produced no listing files — check FIRECRAWL_API_KEY and $(FIRECRAWL_URLS)"; \
	    exit 1; \
	fi
	@for f in data/feed_live/listing-*.txt; do \
	    echo "--- $$f ---"; \
	    $(MAKE) live SOURCE=$$f; \
	done

# Render JSONL shortlist into a sorted Markdown purchase-decision table.
# Input:  data/shortlist_candidates.jsonl (manually assembled by operator)
# Output: data/purchase_matrix.md
render-matrix:
	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
	@echo "Matrix written to data/purchase_matrix.md"
```

Note the use of `$$f` (not `$f`) in the shell `for` loop — Makefile requires doubling the `$` sign to prevent Make from interpreting it as a Make variable.

---

## `data/urls.txt` — Sample File

Create `/Users/okgoogle13/Projects/laptopfinder/data/urls.txt` with this exact content:

```
# One listing URL per line.
# Lines starting with # are ignored.
# Blank lines are ignored.
# Override with: make scrape-and-live FIRECRAWL_URLS=path/to/other.txt
#
# Example eBay AU listing:
# https://www.ebay.com.au/itm/123456789012
#
# Example Gumtree listing:
# https://www.gumtree.com.au/s-ad/sydney/laptops-computers/...
```

This file ships empty of real URLs — it is a template that the operator populates before running `make scrape-and-live`. Committing it with only comments means the file exists in source control, the format is self-documented, and `make scrape-and-live` will not error on a missing file.

---

## `.gitignore` Additions

Section 01 (prerequisites) is responsible for adding the generated artifact paths to `.gitignore`, but confirm these two lines are present before integration testing. If section 01 is not yet merged, add them now:

```
data/feed_live/
data/purchase_matrix.md
```

---

## Integration Verification Steps

Run these steps in order after completing the Makefile edits. Each step must succeed before proceeding to the next.

### Step 1 — Full test suite

```bash
make test
```

Expected: all tests pass, including the new tests from sections 02, 03, and 04.

### Step 2 — Smoke-test `inject-config`

```bash
make inject-config
git diff prompts/
```

Expected output from `make inject-config`: three lines like:
```
comet_discovery_agent.txt: 1 marker pair(s) replaced
alternative_silicon_gemini.txt: 3 marker pair(s) replaced
alternative_silicon_perplexity.txt: 3 marker pair(s) replaced
```

Expected `git diff` output: content between `<!-- BEGIN_INJECT:... -->` and `<!-- END_INJECT:... -->` markers is updated; the marker lines themselves are unchanged. If the replacement count is 0 for any file, the sentinel markers have not been added to that prompt file yet — this is a prerequisite from section 01.

Run `make inject-config` a second time and confirm `git diff` shows no further changes (idempotency).

### Step 3 — Smoke-test `render-matrix` with a sample input

Create a minimal `data/shortlist_candidates.jsonl` for the smoke test:

```json
{"recommended_action": "SHORTLIST", "llm_index_score": 72, "listing_title": "ASUS ROG Zephyrus G14 RTX 4090", "price": "AUD 2,800", "gpu": "RTX 4090 Laptop", "notes": "Clean listing, includes charger"}
{"recommended_action": "MONITOR", "llm_index_score": null, "listing_title": "MSI Titan | parts only?", "price": "AUD 1,200", "gpu": "RTX 3080 Ti", "notes": "Uncertain condition"}
{"recommended_action": "SKIP", "llm_index_score": 31, "listing_title": "Dell XPS 15", "price": "AUD 800", "gpu": null, "notes": "No GPU info"}
```

Then run:

```bash
make render-matrix
cat data/purchase_matrix.md
```

Expected: `data/purchase_matrix.md` is written; it contains a Markdown table with three rows; SHORTLIST row is first; the `|` in `MSI Titan | parts only?` is escaped as `\|` in the table.

### Step 4 — Confirm `scrape-and-live` requires `FIRECRAWL_API_KEY`

Without a `.env` file or `FIRECRAWL_API_KEY` set:

```bash
make scrape-and-live
```

Expected: the script exits with code 1 and prints a clear error message to stderr. The `for` loop over `data/feed_live/listing-*.txt` is not reached, so no live target failure occurs.

---

## Implementation Notes (actual)

**Files modified/created:**
- `Makefile` — `.PHONY` updated; `FIRECRAWL_URLS ?=` moved to a top-level "Overrideable variables" section (not mid-file as originally planned); three new targets appended
- `data/urls.txt` — comment-only template updated to match spec

**Deviations from plan:**
1. `FIRECRAWL_URLS ?= data/urls.txt` moved from between the comment block and `scrape-and-live:` to the top of the Makefile for discoverability. Code review flagged mid-file placement as unidiomatic.
2. `scrape-and-live` target gains `@rm -f data/feed_live/listing-*.txt` as the first recipe line — purges stale files from previous runs before the fresh scrape. Without this, removed URLs would still have their old scraped content re-processed.
3. `$(MAKE) live SOURCE=$$f` changed to `$(MAKE) live SOURCE="$$f" || exit 1` — fail-fast on any per-listing failure, and proper quoting added.

**Integration verification passed:**
1. `make test` — 161 passed
2. `make inject-config` — 1/3/3 blocks replaced; idempotent on second run
3. `make render-matrix` (sample JSONL) — 3-row table, SHORTLIST first, pipe escaped
4. `make scrape-and-live` (no API key / empty urls.txt) — exits non-zero with clear error

---

## Dependency Notes

- `inject-config` intentionally does NOT appear as a dependency of `scrape-and-live`. This was a deliberate design decision: `scrape-and-live` re-mutating git-tracked prompt files as a side effect of every scrape run creates noisy diffs and a second source of truth. Operators run `make inject-config` explicitly when `static_reference_layer.json` changes.
- `scrape-and-live` calls `$(MAKE) live SOURCE=$$f` rather than `.venv/bin/python -m laptopfinder.core run-live --source-text $$f` directly, so that the `make live` target's guard (`@test -n "$(SOURCE)"`) and any future changes to that target are picked up automatically.
- `FIRECRAWL_URLS` is defined as a Makefile variable with `?=` so it can be overridden on the command line without editing the file.