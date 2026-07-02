# Implementation Plan — Sprint 2 (Laptopfinder)

> **Role:** Implementation contract — interfaces, function signatures, test requirements. Item tracking: `TASKS.md` Sprint 2. Agent work units: `planning/sections/`. Source of truth for HOW; TASKS.md owns status.

## Context

Laptopfinder is a multi-stage pipeline for discovering and evaluating second-hand laptops suited to local LLM inference. The pipeline currently has hardcoded prompt text and no live web-scraping capability. This sprint wires three new components that make the system data-driven and operationally self-sufficient for a real purchase decision in the Australian used-hardware market.

The three deliverables are:
1. **`scripts/inject_config.py`** — replaces injected blocks in prompt files via idempotent marker-based substitution, keeping prompts in sync with config
2. **`src/laptopfinder/scrape_live.py`** — fetches listing pages as Markdown via Firecrawl and writes per-listing files for the existing `make live` pipeline
3. **`scripts/render_matrix.py`** — renders a manually assembled JSONL shortlist into a sorted Markdown purchase-decision table

All three components follow the project's established conventions: flat top-level functions, no OOP, no custom exceptions, config-driven values, fixture-driven tests.

---

## 1. Prerequisites

**Install firecrawl-py** — not yet in `pyproject.toml`. Add with `uv add firecrawl-py==<pinned-version>`. The v1 client is `Firecrawl` (from `firecrawl import Firecrawl`) — `FirecrawlApp` is the deprecated v0 interface. The v1 scrape method is `fc.scrape(url, formats=["markdown"])` and the response is an object: `doc.markdown`. Pin the confirmed version in `pyproject.toml`.

**Document `FIRECRAWL_API_KEY`** in `.env.example` alongside the existing API keys.

**Create `scripts/` directory** — does not yet exist. No `__init__.py` needed.

**Update `.gitignore`** — add `data/feed_live/`, `data/purchase_matrix.md`. Generated scrape output and rendered matrices are build artifacts, not source.

---

## 2. Config Injection (`scripts/inject_config.py`)

### Problem

`prompts/comet_discovery_agent.txt` contains `[INJECT_TARGETS_HERE]`, which must be manually updated when the target GPU list changes. The alternative silicon prompts are entirely disconnected from config. A one-shot token-replacement approach would consume tokens on the first run and silently produce stale output on subsequent runs — the exact failure mode the feature exists to prevent.

### Solution: Marker-Based Idempotent Injection

Prompt files use paired sentinel comments that survive each injection run. `inject_file` replaces the content *between* the markers, leaving markers in place. Running `make inject-config` twice produces identical output.

**Sentinel format:**
```
<!-- BEGIN_INJECT:TARGETS -->
...rendered content written here by inject_config.py...
<!-- END_INJECT:TARGETS -->
```

**Markers to use:**
- `BEGIN_INJECT:TARGETS` / `END_INJECT:TARGETS` — formatted block of target GPU names and watch-list GPUs
- `BEGIN_INJECT:UMA_MIN_RAM_GB` / `END_INJECT:UMA_MIN_RAM_GB` — integer value of `uma_platforms.min_total_ram_gb_to_shortlist`
- `BEGIN_INJECT:UMA_CHIP_PATTERNS` / `END_INJECT:UMA_CHIP_PATTERNS` — comma-separated chip pattern list
- `BEGIN_INJECT:TARGET_GPU_LIST` / `END_INJECT:TARGET_GPU_LIST` — formatted GPU list (same as TARGETS, usable in alt-silicon prompts)

**One-time manual edit required:** Before first run, add the appropriate sentinel pairs to each target prompt file at the location where the injected content belongs:
- `prompts/comet_discovery_agent.txt`: replace existing `[INJECT_TARGETS_HERE]` with `BEGIN_INJECT:TARGETS` / `END_INJECT:TARGETS` markers
- `prompts/alternative_silicon_gemini.txt`: add `BEGIN_INJECT:UMA_MIN_RAM_GB`, `BEGIN_INJECT:UMA_CHIP_PATTERNS`, and `BEGIN_INJECT:TARGET_GPU_LIST` marker pairs at appropriate locations
- `prompts/alternative_silicon_perplexity.txt`: same marker pairs as gemini variant

### Git Strategy

Prompt files remain committed source. The `scrape-and-live` Makefile target does **not** depend on `inject-config`.

**Note: this intentionally diverges from the original sprint spec**, which listed `scrape-and-live: inject-config` as a dependency. That dependency was removed after review because it silently re-mutates git-tracked prompt files on every scrape run, creating noisy diffs and a second source of truth in version control. Operators run `make inject-config` explicitly when the SRL changes, not as a side effect of scraping.

### Config Sources

Only `static_reference_layer.json` (SRL) is loaded in v1. It provides all four injected values:
- `target_gpus` (dict — names are keys)
- `watch_list` (list of dicts — `entry["name"]`)
- `uma_platforms` (chip patterns and min RAM)
- `vram_gating_logic` (12/16/24/32 GB thresholds)

`silicon_profiles.yaml` is not loaded. The alternative silicon prompts need ecosystem maturity context, but those tokens are not defined in v1 — adding them is a future task. Loading the file now with no token to inject is speculative code.

### Function Signatures

```python
def load_srl(path: str) -> dict:
    """Load and return static_reference_layer.json."""

def build_substitutions(srl: dict) -> dict[str, str]:
    """Return mapping of marker name → rendered content string.

    Keys: "TARGETS", "UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"
    Reads target_gpus (dict — use .keys()), watch_list (list — use entry["name"]),
    and uma_platforms from srl. No other config needed in v1.
    """

def inject_file(path: str, substitutions: dict[str, str]) -> int:
    """Replace content between BEGIN_INJECT/END_INJECT marker pairs in file.

    Writes file in-place. Leaves markers intact. Idempotent.
    Returns count of marker pairs replaced.
    Raises FileNotFoundError if file does not exist.
    """

def main() -> None:
    """Load SRL, build substitutions, inject all three target prompt files.

    Prints one summary line per file: filename and replacement count.
    """
```

### Makefile

```makefile
inject-config:
	.venv/bin/python scripts/inject_config.py
```

Note: `scrape-and-live` does NOT depend on `inject-config`. Run them independently.

---

## 3. Live Scraper (`src/laptopfinder/scrape_live.py`)

### Problem

The existing `make live` pipeline accepts a pre-assembled text file. There is no automated way to populate that file from real listing URLs. Concatenating all listings into one file would be batch-fatal: one bad listing matching the data-integrity `exclusion_regex` aborts Stage 2 for all others.

### Solution: Per-Listing Output Files

`scrape_live.py` writes each successfully fetched listing to a separate file in `data/feed_live/` (e.g. `data/feed_live/listing-001.txt`). The `scrape-and-live` Makefile target then iterates over these files, running `make live SOURCE=<file>` for each. This isolates failures at the per-listing level.

### Behaviour Contract

- Read `--urls-file` line by line; skip blank lines and `#` comment lines.
- Construct one `Firecrawl` instance using `api_key` read from environment (or omit and let the SDK pick up `FIRECRAWL_API_KEY` automatically). If the key is unset, print a clear error message to stderr and `sys.exit(1)` before any network calls.
- Call `fc.scrape(url, formats=["markdown"], wait_for=3000)` for each URL in a loop. Extract Markdown via `doc.markdown` (v1 returns a response object, not a dict). The `wait_for=3000` ms handles JS-rendered fields on eBay AU pages.
- Strip nav chrome via `strip_nav()`. Apply markdown normalisation via `normalise_md()`.
- **Minimum content check**: if cleaned content is under 200 characters, print `WARN: suspiciously short content for {url} ({n} chars) — possible login wall` to stderr and skip the URL.
- On any exception from the Firecrawl call: print `WARN: failed {url}: {e}` to stderr and continue.
- Write each successful listing to `data/feed_live/listing-{n:03d}.txt`, prefixed with `<!-- {url_without_query_string} -->`.
- `--out-dir` flag controls the output directory (default: `data/feed_live/`).

### Nav Stripping and Markdown Normalisation

`strip_nav` must use word-boundary anchoring, not unbounded substring matching. The pattern should target common nav-only lines rather than any line containing a keyword. A safe approach: match lines where the keyword appears at the start or as a standalone element — e.g. `r'(?im)^\s*(breadcrumb|cart|watchlist|sign in|cookie notice).*$'` with `re.MULTILINE`.

`normalise_md` strips Markdown emphasis and link syntax from the text that will become `full_listing_text`, so the Stage 2 grounding firewall sees plain text matching what the listing actually says:
- Remove `**text**` → `text`
- Remove `[text](url)` → `text`
- Remove `|`-table row syntax from non-table lines

### Function Signatures

```python
def read_urls(path: str) -> list[str]:
    """Return non-blank, non-comment lines from the URL file."""

def strip_nav(md: str) -> str:
    """Remove nav/chrome lines using word-boundary multiline regex."""

def normalise_md(md: str) -> str:
    """Strip Markdown emphasis, link syntax, and table artifacts for grounding compatibility."""

def fetch_markdown(url: str, client: Firecrawl) -> str | None:
    """Fetch URL via v1 client (doc.markdown). Return cleaned Markdown or None on failure or thin content."""

def main() -> None:
    """CLI entry point: parse --urls-file and --out-dir, construct one Firecrawl client,
    scrape each URL, write per-listing output files."""
```

### Makefile

```makefile
FIRECRAWL_URLS ?= data/urls.txt

# Note: intentionally does NOT depend on inject-config.
# Run `make inject-config` separately when config changes.
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
```

`data/urls.txt` must be created in the repo with a comment explaining the format (one URL per line, `#` for comments). Add `data/feed_live/` to `.gitignore`.

---

## 4. Purchase Decision Matrix (`scripts/render_matrix.py`)

### Problem

After a scraping run, the operator has a set of SHORTLIST/MONITOR/SKIP decisions with scores. There is no tool to render these into a human-readable comparison table for the final purchase recommendation.

### Input Format

`data/shortlist_candidates.jsonl` is manually assembled by the operator. Each line is a JSON object. Fields come from two sources:

| Field | Origin |
|-------|--------|
| `recommended_action` | decide() output |
| `llm_index_score` | decide() output |
| `listing_title` | Stage 2 handoff_packet.listing_title |
| `price` | Stage 2 handoff_packet.price |
| `gpu` | Stage 2 analysis_output.extracted_data.gpu |
| `notes` | Operator-written free text |

Any field may be absent; missing fields render as `—` in the table.

### Sort Order

Priority groups: SHORTLIST → MONITOR → SKIP. Within each group, descending by `llm_index_score`. Missing or null `llm_index_score` sorts last within its group (treated as -1). Unknown `recommended_action` values sort after SKIP.

### Output

A Markdown file with heading, ISO timestamp, and a table:

| Rank | Action | Score | Title | GPU | Price | Notes |
|------|--------|-------|-------|-----|-------|-------|

All cell values have `|` escaped as `\|` and newlines stripped before rendering.

### Function Signatures

```python
def load_candidates(path: str) -> list[dict]:
    """Read JSONL. Skip-and-warn on malformed lines (try/except per line).
    Returns list of parsed dicts."""

def sort_candidates(candidates: list[dict]) -> list[dict]:
    """Sort by action priority (SHORTLIST=0, MONITOR=1, SKIP=2, unknown=3),
    then by llm_index_score descending (missing treated as -1)."""

def render_table(candidates: list[dict]) -> str:
    """Return Markdown table. Escape | and strip newlines in all cell values."""

def main() -> None:
    """CLI: --in and --out flags. Load → sort → render → write."""
```

### Makefile

```makefile
render-matrix:
	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
	@echo "Matrix written to data/purchase_matrix.md"
```

---

## 5. Testing

All tests run with `.venv/bin/pytest tests/ -v`.

### Prompt marker tests (`tests/test_prompt_markers.py`)

- **`test_prompt_files_have_sentinel_markers`**: read the three real `prompts/*.txt` files; assert each expected `<!-- BEGIN_INJECT:X -->` / `<!-- END_INJECT:X -->` pair is present. This catches missing markers before any scrape run — fulfills the "all changes verifiable with `make test`" invariant for the one-time manual prerequisite.

### inject_config.py tests (`tests/test_inject_config.py`)

- **`test_build_substitutions`**: construct a mock SRL with `target_gpus` as a dict (with name keys), `watch_list` as a list of `{"name": "..."}` dicts, and `uma_platforms` with known values. Assert correct token values and that dict/list shapes are handled correctly.
- **`test_inject_file_idempotent`**: write a temp file with `<!-- BEGIN_INJECT:TARGETS -->` / `<!-- END_INJECT:TARGETS -->` markers (with stale content between them); call `inject_file()` twice; assert both runs produce identical file content and both return a non-zero replacement count.
- **`test_inject_file_no_markers`**: file with no markers; assert return value is 0 and file is unchanged.

### scrape_live.py tests (`tests/test_scrape_live.py`)

- **`test_strip_nav`**: call `strip_nav()` with Markdown containing a `breadcrumb` line and a legitimate line containing `cart` as a substring of a word (e.g. `"cartridge case"`); assert nav line removed, legitimate line survives.
- **`test_normalise_md`**: verify `**bold**` → `bold`, `[link](url)` → `link`.
- **`test_fetch_markdown_thin_content`**: mock `scrape_url` to return a 50-char string; assert `fetch_markdown` returns `None` and emits a stderr warning.
- **`test_error_continues`**: mock `scrape_url` to raise on URL 1, return valid Markdown on URL 2; assert URL 2's output file is written and stderr contains `WARN`.
- **`test_read_urls_skips_blanks_and_comments`**: assert blank lines and `#` lines are excluded.
- **`test_missing_api_key`**: assert `main()` exits with code 1 and a clear message when env var absent.

### render_matrix.py tests (`tests/test_render_matrix.py`)

- **`test_sort_candidates`**: mixed SHORTLIST/MONITOR/SKIP list with one null score; assert correct group and score ordering, null score sorts last in its group.
- **`test_render_table_pipe_escaping`**: title contains `|`; assert output contains `\|`.
- **`test_load_candidates_skips_bad_line`**: JSONL with one malformed line; assert valid lines load, warning emitted, no exception raised.

---

## 6. Delivery Sequence

1. Create `scripts/` directory
2. `uv add firecrawl-py==<pinned>`, confirm API shape, update `.env.example`
3. Update `.gitignore` with `data/feed_live/`, `data/purchase_matrix.md`
4. Add sentinel marker pairs to the three target prompt files (one-time manual edit)
5. Write and test `scripts/inject_config.py`
6. Add `inject-config` Makefile target; run `make inject-config` on real prompt files; verify git diff shows expected content between markers
7. Write and test `src/laptopfinder/scrape_live.py`; confirm Firecrawl API shape matches pinned version
8. Add `FIRECRAWL_URLS` default, `data/urls.txt` sample, and `scrape-and-live` target to Makefile
9. Write and test `scripts/render_matrix.py`
10. Add `render-matrix` target to Makefile
11. Run `make test` — all new and existing tests must pass
