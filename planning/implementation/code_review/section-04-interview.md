# Code Review Interview — section-04-render-matrix

## Auto-fixed (no user input needed)

**MUST-FIX #1 — score=0 bug in `sort_candidates`**
`-(c.get("llm_index_score") or -1)` treats 0 as falsy. Fixed with explicit None check:
```python
v = c.get("llm_index_score")
score = -(v if v is not None else -1)
```

**MUST-FIX #2 — missing test for `llm_index_score: 0`**
Added `test_sort_zero_score_above_null` to `TestSortCandidates`. Confirms score=0 sorts above null.

**SUGGEST #4 — opaque second assertion in `test_render_table_newline_stripped`**
Dropped the `"\n\n" not in output.replace(...)` assertion. Intent already covered by `"Laptop Bundle" in output`.

**NITPICK #6 — trailing spaces in `render_table` row f-strings**
Reformatted row f-strings so pipe placement is consistent with header/separator.

## User decision

**SUGGEST #3 — FileNotFoundError guard in `main()`**
User chose: **Yes, add the guard**
Applied: check `os.path.exists(args.input)` before `load_candidates()`; print clear message and `sys.exit(1)` if missing.
