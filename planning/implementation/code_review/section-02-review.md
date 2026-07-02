# Code Review — section-02-egpu-interconnect-penalty

## HIGH — TB5 returns oculink_pts instead of thunderbolt_5_pts
Both OCuLink and TB5 use `cfg.get("oculink_pts", 0)`. SRL has a separate `thunderbolt_5_pts`
key. Both are 0 now so tests pass, but if either key changes the wrong enclosure type is affected.
**Fix:** Split OCuLink and TB5 into separate return paths using their respective SRL keys.

## HIGH — Minisforum DEG2 (OCuLink) incorrectly gets TB3/4 penalty
SRL `egpu_enclosures` has "Minisforum DEG2" (no "OCuLink" in name). `_has_egpu_bundle` returns
True for it, but `"oculink" in egpu_lower` is False → falls through to -3 penalty.
Test covers "Minisforum DEG2 OCuLink" (not a real seller string).
**Fix:** Add `oculink_enclosures` key to SRL; check against it in addition to the keyword.

## MEDIUM — Truthiness check on numeric field
`if system_ram and system_ram >= 32:` conflates None with 0.
**Fix:** `if system_ram is not None and system_ram >= 32:`

## Additional (untested path, document)
`egpu_model=None` + enclosure keyword only in `exact_model_name` → `_has_egpu_bundle` True,
`egpu_lower=""`, no keyword match → returns -3. Conservative but untested. Add a test.
