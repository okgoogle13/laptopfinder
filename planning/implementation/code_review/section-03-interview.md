# Interview Transcript: section-03-scrape-live

No user interview required — all findings resolved as auto-fixes.

## Auto-fixes applied

1. **MUST_FIX #1** — Added filename assertion to `test_main_first_fails_second_succeeds`:
   Assert that the written file is named `listing-002.txt` (n=2, since first URL was attempted but failed).

2. **MUST_FIX #2** — Added `doc.markdown is None` guard in `fetch_markdown`:
   Returns `None` + WARN message before attempting string operations.

3. **NITPICK #1** — Removed redundant `os.environ.pop` from `test_main_missing_api_key_exits`.

4. **NITPICK #2** — Changed `ln.rstrip()` to `ln.strip()` in `read_urls` return value.

## Let go

- CONSIDER #1: `cart` nav pattern — safe against false positives; real-world nav quality is a runtime concern not testable offline.
- CONSIDER #2: line count overage — 68 vs 50 lines is a doc constraint, not a correctness issue.
