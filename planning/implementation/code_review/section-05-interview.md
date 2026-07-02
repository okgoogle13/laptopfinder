# Code Review Interview: section-05-makefile-and-integration

## Auto-fixes applied

**[HIGH] for-loop fail-fast** — Added `|| exit 1` after each `$(MAKE) live SOURCE="$$f"` call. Without this, a failing `make live` on any listing except the last would be silently swallowed.

**[MEDIUM] Stale feed_live purge** — Added `@rm -f data/feed_live/listing-*.txt` as the first recipe line of `scrape-and-live`. Prevents old listing files from previous runs being re-processed.

**[IMPROVEMENT] FIRECRAWL_URLS variable moved to top** — User approved. Moved `FIRECRAWL_URLS ?= data/urls.txt` to a dedicated "Overrideable variables" section at the top of the Makefile, after `.PHONY`. Removed the inline definition from between the comment block and the `scrape-and-live:` target.

**[NITPICK] SOURCE quoting** — Changed `SOURCE=$$f` to `SOURCE="$$f"` at the recursive `$(MAKE)` call site for correctness under shell expansion.

## Let go

**`.gitignore` and `data/urls.txt` content** — correct, no action needed.
