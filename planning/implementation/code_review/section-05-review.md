# Code Review: section-05-makefile-and-integration

## Bugs

**[HIGH] Silent failure swallowing in the `for` loop**
`$(MAKE) live SOURCE=$$f` in the for loop — if any invocation fails except the last, the loop continues silently. POSIX sh for-loop exit code is the last command's exit code only.
Fix: `$(MAKE) live SOURCE=$$f || exit 1;`

**[MEDIUM] Stale `data/feed_live/` files re-processed on subsequent runs**
Scrape step appends to `data/feed_live/` without purging old files. Old listing files from a previous run remain and get fed to the live pipeline again. Especially bad if a URL was removed from `urls.txt`.
Fix: Add `@rm -f data/feed_live/listing-*.txt` as the first recipe line of `scrape-and-live`.

## Improvements

**`FIRECRAWL_URLS ?=` variable placement**
Defined mid-file between a comment and the target recipe — unidiomatic. Conventionally placed at top of Makefile near other overrideable vars. Plan-level issue faithfully reproduced.

## Nitpicks

**`SOURCE=$$f` unquoted through two layers of expansion**
`SOURCE=$$f` → `$(SOURCE)` passed unquoted to `run-live`. Generated filenames won't have spaces so survivable in practice. `SOURCE="$$f"` would be more correct.

**`.gitignore` and `data/urls.txt`** correct and match plan exactly.
