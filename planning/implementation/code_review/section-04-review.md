# Code Review — section-04-render-matrix

## MUST-FIX

**1. score=0 silently misbehaves in `sort_candidates`** (`scripts/render_matrix.py` line ~40)

`-(c.get("llm_index_score") or -1)` uses Python truthiness: a legitimate score of `0` evaluates as `0 or -1` → `-1`, making it indistinguishable from null/missing. Scores are 0–100, so 0 is a valid value.

Fix: explicit None check:
```python
v = c.get("llm_index_score")
score = -(v if v is not None else -1)
```

Note: the plan (section-04-render-matrix.md line 133) provided the same broken formula — this is a spec defect faithfully reproduced. Still a real correctness bug.

**2. No test for `llm_index_score: 0`** (`tests/test_render_matrix.py`, `TestSortCandidates`)

The five sort tests exercise null and absent keys but never the zero value. Without a `test_sort_zero_score_above_null` case, the score=0 bug won't be caught.

## SUGGEST

**3. No `FileNotFoundError` handling in `main()`** (`render_matrix.py` ~line 85)

Running with the default `--in data/shortlist_candidates.jsonl` before the file exists yields a raw traceback. A check before `load_candidates()` with a clear message would match operator UX intent.

**4. Opaque second assertion in `test_render_table_newline_stripped`** (test line ~226)

`assert "\n\n" not in output.replace("\n| ", "")` is hard to read and already covered by the `"Laptop Bundle" in output` check above it. Should be dropped.

## NITPICK

**5.** Module-level importlib at collection time — if the script has a syntax error, pytest fails the entire file. Minor ergonomics.

**6.** `render_table` row f-strings have a trailing space before each `|` (e.g. `| SHORTLIST `), inconsistent with the header/separator format. Not functional.
