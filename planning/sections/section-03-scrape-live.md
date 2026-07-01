# Section 03 — Live Scraper (`scrape_live.py`)

## Dependencies

This section depends on **section-01-prerequisites** being complete:
- `firecrawl-py` installed and pinned in `pyproject.toml`
- `FIRECRAWL_API_KEY` documented in `.env.example`
- `data/feed_live/` added to `.gitignore`

This section is parallel-safe with section-02 and section-04. Section-05 (Makefile integration) blocks on this one.

---

## Background

The existing `make live` pipeline accepts a pre-assembled text file (`SOURCE=feed.txt`). There is no automated way to populate that file from real listing URLs. Concatenating all listings into one file would be batch-fatal: one bad listing matching the data-integrity `exclusion_regex` in `static_reference_layer.json` aborts Stage 2 for all others.

The solution is per-listing output files. `scrape_live.py` writes each successfully fetched listing to a separate file in `data/feed_live/` (e.g. `data/feed_live/listing-001.txt`). The `scrape-and-live` Makefile target then iterates over these files, running `make live SOURCE=<file>` for each. Failures are isolated at the per-listing level.

---

## Files Created

- `src/laptopfinder/scrape_live.py` — scraper module (~70 lines incl. None guard)
- `tests/test_scrape_live.py` — 18 tests, zero live HTTP
- `data/urls.txt` — sample/operator URL list (all entries commented out)

### Deviations from plan
- File is ~70 lines (plan target 50). The `doc.markdown is None` guard added during review necessitated an extra branch.
- `_make_doc(None)` test case added for the None-markdown code path (plan didn't enumerate this but the spec implied it).
- Counter filename assertion (`listing-002.txt`) added to `test_main_first_fails_second_succeeds` to enforce the all-URLs-counted contract.

---

## Tests First (`tests/test_scrape_live.py`)

Write these tests before implementing the module. All tests mock the Firecrawl client — zero live HTTP calls. Use `unittest.mock.patch`.

### `read_urls`

- Blank lines are excluded from the returned list.
- Lines starting with `#` are excluded.
- Valid URLs are returned in order.
- File containing only blanks and comments returns an empty list.

### `strip_nav`

- A line starting with the `breadcrumb` keyword is removed.
- A line where `cart` appears as a substring of another word (e.g. `"cartridge case"`) is NOT removed — test for false-positive safety.
- A `<!-- URL -->` provenance comment line is NOT removed by nav stripping.
- Unrelated listing content lines survive unchanged.

### `normalise_md`

- `**bold**` → `bold`
- `[link text](https://example.com)` → `link text`
- Plain text with no Markdown syntax is returned unchanged.

### `fetch_markdown`

- Mock client returns a valid doc object with a `.markdown` attribute containing ≥ 200 chars; `fetch_markdown` returns a cleaned non-None string.
- Mock client returns a doc with `.markdown` of length < 200; `fetch_markdown` returns `None` and emits a `WARN` message to stderr.
- Mock client raises `Exception`; `fetch_markdown` returns `None` and emits a `WARN` message to stderr.

### `main`

- `FIRECRAWL_API_KEY` env var absent → exits with code 1 and a clear error message on stderr, before any network call.
- Two URLs where the first raises and the second succeeds → only the second listing file is written; first URL emits `WARN` to stderr.
- Successful URL → output file is written to `--out-dir` with a `<!-- url -->` prefix; query string parameters are stripped from the comment (the URL in the comment must not contain `?` or `&`).

---

## Implementation (`src/laptopfinder/scrape_live.py`)

### Firecrawl v1 API

The correct import is `from firecrawl import Firecrawl` (NOT `FirecrawlApp` — that is the deprecated v0 interface). The scrape call is:

```python
doc = fc.scrape(url, formats=["markdown"], wait_for=3000)
content = doc.markdown
```

The response is an object, not a dict. `wait_for=3000` (ms) is required to handle JS-rendered fields on eBay AU pages. The `Firecrawl` client picks up `FIRECRAWL_API_KEY` from the environment automatically if no `api_key` argument is passed.

### Function Signatures

```python
def read_urls(path: str) -> list[str]:
    """Return non-blank, non-comment lines from the URL file."""

def strip_nav(md: str) -> str:
    """Remove nav/chrome lines using word-boundary multiline regex.

    Pattern must target lines where the keyword appears at the start or
    as a standalone element, not any line containing the substring.
    Safe pattern: r'(?im)^\s*(breadcrumb|cart|watchlist|sign in|cookie notice).*$'
    with re.MULTILINE.
    """

def normalise_md(md: str) -> str:
    """Strip Markdown emphasis, link syntax, and table artifacts.

    - **text** → text
    - [text](url) → text
    - Pipe-table row syntax on non-table lines (optional in v1)
    This keeps full_listing_text compatible with the Stage 2 grounding firewall,
    which does verbatim word-boundary regex matches against plain text.
    """

def fetch_markdown(url: str, client) -> str | None:
    """Fetch URL via Firecrawl v1 client (doc.markdown).

    Returns cleaned Markdown string, or None on any exception or thin content.
    Thin content = cleaned string under 200 characters.
    On thin content: print WARN to stderr and return None.
    On exception: print WARN to stderr and return None.
    """

def main() -> None:
    """CLI entry point.

    Parse --urls-file (default: data/urls.txt) and --out-dir (default: data/feed_live/).
    Check FIRECRAWL_API_KEY env var; if absent, print error to stderr and sys.exit(1).
    Construct one Firecrawl client instance.
    For each URL: call fetch_markdown, write to data/feed_live/listing-{n:03d}.txt.
    Output files are prefixed with <!-- {url_without_query_string} -->.
    """
```

### Behaviour Contract Details

- Read `--urls-file` line by line; skip blank lines and `#` comment lines (delegate to `read_urls`).
- Check `FIRECRAWL_API_KEY` in `os.environ` before constructing the client. If absent, `print(..., file=sys.stderr)` and `sys.exit(1)`.
- Construct a single `Firecrawl` client for the whole run (not one per URL).
- Call `fetch_markdown(url, client)` for each URL. If it returns `None`, skip writing any file for that URL.
- Write successful output to `{out_dir}/listing-{n:03d}.txt` where `n` is 1-indexed and counts only the URLs attempted (not just successful ones — keep a loop counter).
- File prefix: strip query string from the URL before writing to the comment. Use `urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl()` or equivalent.
- On Firecrawl exception inside `fetch_markdown`: `print(f"WARN: failed {url}: {e}", file=sys.stderr)` and continue.

### Nav Stripping Detail

`strip_nav` must use word-boundary anchoring — do not match any line that contains a keyword anywhere. The pattern targets lines where the keyword is the leading element:

```python
import re
_NAV_PATTERN = re.compile(
    r'(?im)^\s*(breadcrumb|cart|watchlist|sign in|cookie notice).*$'
)

def strip_nav(md: str) -> str:
    return _NAV_PATTERN.sub("", md)
```

This correctly removes a line like `breadcrumb: Home > Laptops` while preserving `cartridge case details` because `cartridge` does not start with `cart` as a standalone token at the line boundary under this regex (note: test this carefully — `(?im)` with `^\s*(cart)` would match `cartridge` since it starts with `cart`). To be safe, use alternation that anchors the keyword as a whole word:

```python
_NAV_PATTERN = re.compile(
    r'(?im)^\s*(breadcrumb|watchlist|sign in|cookie notice).*$|^\s*cart\s*$.*'
)
```

Or use `\b` word boundaries. The test fixture for `"cartridge case"` must pass — verify the regex against it before shipping.

### `normalise_md` Detail

Transformations applied in order:

1. `**text**` → `text` via `re.sub(r'\*\*(.+?)\*\*', r'\1', md)`
2. `[text](url)` → `text` via `re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', md)`

---

## Sample `data/urls.txt`

Create this file in the repo (committed, not gitignored). It documents the format for operators:

```
# URLs to scrape for the live pipeline.
# One URL per line. Blank lines and lines starting with # are ignored.
# Run: make scrape-and-live
#
# https://www.ebay.com.au/itm/example-listing-1
# https://www.ebay.com.au/itm/example-listing-2
```

---

## Makefile Target (for reference — implemented in section-05)

The `scrape-and-live` target that section-05 will add:

```makefile
FIRECRAWL_URLS ?= data/urls.txt

# Note: intentionally does NOT depend on inject-config.
# Run `make inject-config` separately when config changes.
scrape-and-live:
	@echo "=== Firecrawl fetch ==="
	.venv/bin/python -m laptopfinder.scrape_live --urls-file $(FIRECRAWL_URLS) --out-dir data/feed_live/
	@echo "=== Live pipeline (per listing) ==="
	@for f in data/feed_live/listing-*.txt; do \
	    echo "--- $$f ---"; \
	    $(MAKE) live SOURCE=$$f; \
	done
```

Do not implement the Makefile target here — that belongs to section-05. Document it here for context only.

---

## Implementation Notes

- Keep the file under 50 lines by avoiding docstring verbosity and keeping regex patterns at module level.
- `strip_nav` and `normalise_md` are pure string functions — no I/O, easy to unit test.
- `fetch_markdown` takes the client as a parameter (not constructing it internally) so tests can inject a mock without patching import-time state.
- `main` is the only function that touches `os.environ`, `sys.exit`, `argparse`, and the filesystem — isolate side effects here.
- The module is invoked as `python -m laptopfinder.scrape_live`, so it needs an `if __name__ == "__main__": main()` guard at the bottom.
- No custom exceptions. Failures are warnings; the loop continues. Only the missing API key is fatal.