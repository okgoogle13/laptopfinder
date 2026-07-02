# TDD Plan — Sprint 2 (Laptopfinder)

Testing framework: pytest. Tests live in `tests/`. Run with `.venv/bin/pytest tests/ -v`. Fixtures go in `tests/fixtures/` where appropriate. Mocking via `unittest.mock.patch`. No live API calls in CI.

---

## 1. Prerequisites

No tests for prerequisite setup steps (install firecrawl-py, create scripts/, update .gitignore, add sentinel markers to prompt files). Verify manually.

---

## 2. Config Injection (`tests/test_inject_config.py`)

Write these tests before implementing `scripts/inject_config.py`:

### load_srl
- Test: `load_srl` returns a dict containing `target_gpus`, `watch_list`, `uma_platforms`, `vram_gating_logic`
- Test: `load_srl` raises `FileNotFoundError` on missing path

### build_substitutions (takes only `srl`)
- Test: given SRL with `target_gpus` as a dict and `watch_list` as a list of `{"name": ...}` objects, `build_substitutions` returns all four expected marker keys
- Test: `TARGET_GPU_LIST` value contains GPU names from `target_gpus.keys()`
- Test: `TARGETS` value includes watch-list GPU names from `entry["name"]`
- Test: `UMA_MIN_RAM_GB` value matches `srl["uma_platforms"]["min_total_ram_gb_to_shortlist"]` as a string
- Test: `UMA_CHIP_PATTERNS` value is a comma-separated string of the chip patterns list

### inject_file
- Test: file containing `<!-- BEGIN_INJECT:TARGETS -->stale<!-- END_INJECT:TARGETS -->` is updated with new content; markers remain present
- Test: running `inject_file` twice on the same file yields identical output (idempotency)
- Test: return value equals the number of marker pairs replaced
- Test: file with no markers returns 0, file unchanged
- Test: `FileNotFoundError` raised for non-existent path

### main (integration)
- Test: run `main()` against a temp directory containing copies of the three prompt files with sentinel markers; assert all three files have marker content updated; assert no markers are destroyed

---

## 3. Live Scraper (`tests/test_scrape_live.py`)

Write these tests before implementing `src/laptopfinder/scrape_live.py`. All tests mock the Firecrawl client — no live HTTP calls.

### read_urls
- Test: blank lines are excluded
- Test: lines starting with `#` are excluded
- Test: valid URLs are returned in order
- Test: returns empty list for file with only blanks/comments

### strip_nav
- Test: line starting with `breadcrumb` keyword is removed
- Test: line where `cart` appears as substring of another word (e.g. `"cartridge case"`) is NOT removed
- Test: `<!-- URL -->` provenance comment is NOT removed
- Test: unrelated listing content lines survive

### normalise_md
- Test: `**bold**` → `bold`
- Test: `[link text](https://example.com)` → `link text`
- Test: plain text with no Markdown syntax is unchanged

### fetch_markdown
- Test: mock client returns valid doc with `.markdown`; `fetch_markdown` returns cleaned string
- Test: mock client returns doc with `.markdown` of length < 200; returns `None` and emits stderr warning
- Test: mock client raises `Exception`; returns `None` and emits stderr warning

### main
- Test: missing `FIRECRAWL_API_KEY` env var → exits with code 1 and error message on stderr
- Test: two URLs where first raises, second succeeds → only second listing file is written; first emits WARN to stderr
- Test: successful URL → output file is written to `--out-dir` with `<!-- url -->` prefix and no query string parameters in comment

---

## 4. Purchase Decision Matrix (`tests/test_render_matrix.py`)

Write these tests before implementing `scripts/render_matrix.py`.

### load_candidates
- Test: valid JSONL with two entries returns list of two dicts
- Test: file with one malformed line emits WARN to stderr, skips line, returns remaining valid entries
- Test: empty file returns empty list

### sort_candidates
- Test: SHORTLIST entries appear before MONITOR entries, MONITOR before SKIP
- Test: within a group, higher `llm_index_score` appears first
- Test: entry with `llm_index_score: null` sorts last within its group
- Test: entry with missing `recommended_action` sorts after all named groups
- Test: entry with missing `llm_index_score` key (not null, just absent) sorts last within group

### render_table
- Test: output contains Markdown table header row with expected column names
- Test: listing title containing `|` is escaped as `\|` in output
- Test: listing title containing a newline has newline stripped
- Test: missing field renders as `—`
- Test: two entries produce two data rows

### main (integration)
- Test: given a two-entry JSONL file, `--out` file contains a valid Markdown table with both entries sorted correctly

---

## 5. Delivery Sequence (TDD ordering)

Write tests first, then implement, in this order:

1. `test_inject_config.py` stubs → implement `inject_config.py` → run `make test`
2. `test_scrape_live.py` stubs → implement `scrape_live.py` → run `make test`
3. `test_render_matrix.py` stubs → implement `render_matrix.py` → run `make test`
4. Final: `make test` passes all new and existing tests before any live scrape run
