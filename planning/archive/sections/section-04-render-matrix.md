# Section 04 — Render Matrix

## Overview

This section implements `scripts/render_matrix.py`, a stdlib-only script that renders a manually assembled JSONL shortlist into a sorted Markdown purchase-decision table. It depends only on section-01-prerequisites (the `scripts/` directory existing). It can be implemented in parallel with sections 02 and 03.

**Files created:**
- `scripts/render_matrix.py`
- `tests/test_render_matrix.py`

**Files to modify:**
- `Makefile` (add `render-matrix` target — handled in section-05)

No external dependencies. Only Python stdlib is needed (`json`, `sys`, `argparse`, `datetime`, `os`).

### Implementation notes (post-review)

- **Score=0 bug fixed:** The plan's suggested sort key `-(c.get("llm_index_score") or -1)` treats 0 as falsy. Implementation uses an explicit None check: `v = c.get("llm_index_score"); score = -(v if v is not None else -1)`.
- **FileNotFoundError guard added:** `main()` checks `os.path.exists(args.input)` before calling `load_candidates()` and exits with a clear message if missing (not in original spec).
- **Test count:** 15 tests (14 planned + `test_sort_zero_score_above_null` added during review).

---

## Tests First

Write `tests/test_render_matrix.py` before implementing the script. All tests use only stdlib — no mocking of external APIs needed.

### load_candidates

```python
def test_load_candidates_two_valid_entries():
    """Valid JSONL with two entries returns list of two dicts."""

def test_load_candidates_skips_bad_line():
    """File with one malformed JSON line: valid lines load, WARN emitted to stderr, no exception."""

def test_load_candidates_empty_file():
    """Empty file returns empty list."""
```

Write the malformed-line test by creating a temp file with content like:
```
{"recommended_action": "SHORTLIST", "llm_index_score": 80}
this is not json
{"recommended_action": "SKIP", "llm_index_score": 10}
```
Assert the return value has length 2 and that `capsys.readouterr().err` contains `WARN`.

### sort_candidates

```python
def test_sort_group_order():
    """SHORTLIST entries appear before MONITOR, MONITOR before SKIP."""

def test_sort_within_group_descending_score():
    """Within a group, higher llm_index_score appears first."""

def test_sort_null_score_last_in_group():
    """Entry with llm_index_score: null sorts last within its group."""

def test_sort_missing_action_last():
    """Entry with missing recommended_action sorts after SKIP (unknown group)."""

def test_sort_missing_score_key_last():
    """Entry with llm_index_score key absent (not null) sorts last within its group."""
```

For the sort tests, construct small in-memory lists of dicts and call `sort_candidates()` directly. Assert ordering by inspecting the resulting list's `recommended_action` and `llm_index_score` fields in sequence.

### render_table

```python
def test_render_table_header():
    """Output contains Markdown table header row with Rank, Action, Score, Title, GPU, Price, Notes columns."""

def test_render_table_pipe_escaping():
    """Listing title containing | is escaped as \| in output."""

def test_render_table_newline_stripped():
    """Listing title containing a newline has newline stripped before rendering."""

def test_render_table_missing_field_dash():
    """Missing field (key absent from dict) renders as — in the cell."""

def test_render_table_two_rows():
    """Two entries produce exactly two data rows (not counting header/separator)."""
```

Pass constructed dicts directly to `render_table()`. Inspect the returned string.

### main (integration)

```python
def test_main_integration(tmp_path):
    """Two-entry JSONL file → --out file contains valid Markdown table with both entries, SHORTLIST before SKIP."""
```

Write a temp JSONL file with one SHORTLIST and one SKIP entry. Call `main()` via `monkeypatch` on `sys.argv` pointing to the temp file and a temp output path. Read the output file and assert it contains both entries in correct order.

---

## Implementation

### `scripts/render_matrix.py`

No `__init__.py` needed in `scripts/`. The file is invoked directly as `python scripts/render_matrix.py`.

#### Function signatures and docstrings

```python
def load_candidates(path: str) -> list[dict]:
    """Read JSONL file at path. Parse each line as JSON.
    Skip malformed lines with a WARN to stderr (try/except per line).
    Return list of successfully parsed dicts."""

def sort_candidates(candidates: list[dict]) -> list[dict]:
    """Sort by action priority group: SHORTLIST=0, MONITOR=1, SKIP=2, unknown=3.
    Within each group, sort descending by llm_index_score.
    Treat missing or null llm_index_score as -1 (sorts last in group).
    Does not mutate the input list."""

def render_table(candidates: list[dict]) -> str:
    """Return a Markdown table string for the given candidates.
    Columns: Rank, Action, Score, Title, GPU, Price, Notes.
    All cell values have | escaped as \| and newlines stripped.
    Missing keys render as — (em dash, not hyphen)."""

def main() -> None:
    """CLI entry point.
    Flags: --in (default: data/shortlist_candidates.jsonl), --out (default: data/purchase_matrix.md).
    Loads candidates, sorts, renders table, prepends a heading with ISO timestamp, writes to --out.
    Prints confirmation line to stdout."""
```

#### Behaviour details

**load_candidates:** Open the file, iterate lines, strip whitespace, skip empty lines. For each non-empty line wrap `json.loads()` in a try/except catching `json.JSONDecodeError`. On failure: `print(f"WARN: skipping malformed line {i}: {e}", file=sys.stderr)` and continue.

**sort_candidates:** Define a priority map: `{"SHORTLIST": 0, "MONITOR": 1, "SKIP": 2}`. Use `.get(c.get("recommended_action"), 3)` for group key. For score key: `-(c.get("llm_index_score") or -1)` — this treats both `None` and absent key as `-1` for descending sort (negate so `sorted()` ascending works). Return `sorted(candidates, key=sort_key)`.

**render_table:** Build the header and separator first:

```
| Rank | Action | Score | Title | GPU | Price | Notes |
|------|--------|-------|-------|-----|-------|-------|
```

For each candidate (1-indexed), extract fields with `.get()` defaulting to `None`, then render each cell value: convert to string, replace `|` with `\|`, replace `\n` with ` `, convert `None` to `—`.

**render_table cell helper** (inline or small inner function):

```python
def cell(v) -> str:
    if v is None:
        return "—"
    return str(v).replace("\n", " ").replace("|", r"\|")
```

**main:** Use `argparse.ArgumentParser`. Flags:
- `--in` (dest `input`, default `data/shortlist_candidates.jsonl`)
- `--out` (default `data/purchase_matrix.md`)

Output file structure:
```markdown
# Purchase Decision Matrix

Generated: 2026-07-02T10:00:00

| Rank | Action | Score | Title | GPU | Price | Notes |
...
```

Use `datetime.datetime.now().isoformat(timespec="seconds")` for the timestamp.

---

## Sort Order Reference

Priority groups: SHORTLIST → MONITOR → SKIP → unknown. Within each group, descending by `llm_index_score`. Missing or null score sorts last within the group (treated as -1 for comparison purposes; all actual scores are ≥ 0).

Example input:

```jsonl
{"recommended_action": "SKIP", "llm_index_score": 20, "listing_title": "Old laptop"}
{"recommended_action": "SHORTLIST", "llm_index_score": null, "listing_title": "M3 Max — no score yet"}
{"recommended_action": "SHORTLIST", "llm_index_score": 85, "listing_title": "RTX 4090 beast"}
{"recommended_action": "MONITOR", "llm_index_score": 60, "listing_title": "Mid-range option"}
```

Expected output order: RTX 4090 beast (SHORTLIST/85), M3 Max (SHORTLIST/null→last in group), Mid-range option (MONITOR/60), Old laptop (SKIP/20).

---

## Input Format

`data/shortlist_candidates.jsonl` is manually assembled by the operator after a pipeline run. Each line is a JSON object with any combination of these fields (all optional):

| Field | Source | Type |
|-------|--------|------|
| `recommended_action` | `decide()` output | `"SHORTLIST"` \| `"MONITOR"` \| `"SKIP"` |
| `llm_index_score` | `decide()` output | number or null |
| `listing_title` | Stage 2 `handoff_packet.listing_title` | string |
| `price` | Stage 2 `handoff_packet.price` | string or number |
| `gpu` | Stage 2 `analysis_output.extracted_data.gpu` | string |
| `notes` | Operator-written free text | string |

Any field may be absent. Missing fields render as `—` in the table.

---

## Makefile Target

The `render-matrix` target is added in section-05. The script must exist and be callable before that section is implemented. The target will be:

```makefile
render-matrix:
	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
	@echo "Matrix written to data/purchase_matrix.md"
```

Add `data/purchase_matrix.md` to `.gitignore` (handled in section-01, but verify it is present).

---

## Dependencies

- **section-01-prerequisites**: `scripts/` directory must exist. `data/purchase_matrix.md` must be in `.gitignore`.
- No other sections are required. This section has no dependency on section-02 or section-03.

---

## Acceptance Criteria

1. `tests/test_render_matrix.py` passes with `.venv/bin/pytest tests/test_render_matrix.py -v`.
2. All existing tests continue to pass (`make test`).
3. `python scripts/render_matrix.py --in tests/fixtures/sample_shortlist.jsonl --out /tmp/matrix.md` (or any valid paths) writes a correctly formatted Markdown file.
4. Running the script on a JSONL with a malformed line prints a WARN to stderr and writes the valid entries without raising an exception.
5. Running twice on the same input produces identical output (deterministic sort + timestamp aside — the table body is identical).