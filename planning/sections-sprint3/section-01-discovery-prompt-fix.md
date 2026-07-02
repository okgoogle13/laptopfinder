# Section 01: Discovery Prompt UMA Threshold Fix

## Goal

Fix a discovery blind spot: `prompts/comet_discovery_agent.txt` filters UMA platforms at `64GB+` unified RAM, but the decision engine shortlists at `32GB` (`uma_unified_min_gb` in SRL). Mac Studio M2 Max (32 GB), M3 Max (48 GB), and similar mid-tier Apple Silicon Max machines are never surfaced by the discovery agent.

Add an `UMA_MIN_RAM_GB` sentinel pair so `make inject-config` keeps the threshold in sync with the SRL going forward.

## Files to Modify

- `prompts/comet_discovery_agent.txt` — fix line 33, add sentinel pair
- `tests/test_prompt_markers.py` — add `UMA_MIN_RAM_GB` to comet assertion

## No Changes Needed

- `scripts/inject_config.py` — `UMA_MIN_RAM_GB` key already exists in `build_substitutions`, maps to `srl["uma_platforms"]["min_total_ram_gb_to_shortlist"]` (value: 32)
- `config/static_reference_layer.json` — `uma_platforms.min_total_ram_gb_to_shortlist` is already 32

## TDD Plan

### Test 1 (write first, expect fail)
In `tests/test_prompt_markers.py`, update the `expected` dict:
```python
"comet_discovery_agent.txt": ["TARGETS", "UMA_MIN_RAM_GB"],
```
Run tests — fails because `comet_discovery_agent.txt` has no `UMA_MIN_RAM_GB` sentinel.

### Implementation
In `prompts/comet_discovery_agent.txt`, replace line 33:

**Before:**
```
- UMA platforms: Apple Silicon Max/Ultra (64GB+ unified RAM) or AMD Strix Halo / Ryzen AI Max (64GB+).
```

**After:**
```
- UMA platforms: Apple Silicon Max/Ultra or AMD Strix Halo / Ryzen AI Max — minimum <!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->32<!-- END_INJECT:UMA_MIN_RAM_GB --> GB unified/system RAM.
```

The HTML comment sentinels are invisible to the LLM. `inject_config.py` replaces `32` with the current SRL value on each `make inject-config` run.

### Test 2 (run tests — expect pass)
`make test` passes. `make inject-config` runs without error.

## Notes

**Why the search heuristic strings (lines 37–44) stay as prose:**
The Boolean strings (`"16GB"`, `"12GB"`, `"64GB RAM"`, `"32GB RAM"`) are eBay search query templates embedded in multi-field Boolean expressions. The inject_config.py replacement pattern (`\1\n{value}\n\2`) replaces the entire block between sentinel tags with a single value — it cannot inject into the middle of a query string. Sentineling them would break the eBay query format. They remain as intentional prose that must be updated manually if the underlying thresholds change.

## Deviations from Plan

**Sentinel format:** Plan specified inline sentinel (`<!-- BEGIN -->32<!-- END -->`). Code review
found this is incompatible with `inject_file`'s `\n{value}\n` replacement template. Changed to
block-format (begin tag / value / end tag each on own line), matching the pattern in
`alternative_silicon_*.txt`. The prompt line was restructured to:
```
- UMA platforms: ... — minimum unified/system RAM (GB):
<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->
32
<!-- END_INJECT:UMA_MIN_RAM_GB -->
```

**Additional test added:** `test_prompt_parity.py` had no sync guard for the comet prompt's
new sentinel. Added `actual_comet_uma_ram` assertion in `test_prompt_injection_sync()` to catch
stale values after SRL changes.

## Files Actually Modified

- `prompts/comet_discovery_agent.txt` — line 33 restructured, block-format sentinel added
- `tests/test_prompt_markers.py` — `UMA_MIN_RAM_GB` added to comet assertion
- `tests/test_prompt_parity.py` — sync guard added for comet's UMA_MIN_RAM_GB sentinel
- `TASKS.md` — architecture penalty stub correctly reverted to `[ ]`

## Final Test Count

169 passed (baseline 168 → +1 new sentinel marker assertion; parity test added new assertion
within existing test function, no count change).

## Verification

1. `make test` — 169 passed ✓
2. Sentinel present: `grep "BEGIN_INJECT:UMA_MIN_RAM_GB" prompts/comet_discovery_agent.txt` ✓
3. No raw `64GB+` in UMA description line ✓
