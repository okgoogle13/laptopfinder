# Section 02: eGPU Interconnect Penalty

## Goal

Wire `egpu_interconnect_penalty` from the SRL into `decide.py`. Currently eGPU listings on TB3/4 connections receive a -3 pt penalty in config but zero effect on `llm_index_score`.

## Design Decision — Keyword Detection, No Schema Change

`egpu_interconnect_type` does not exist in Stage 2 `extracted_data`. Rather than adding a new schema field (which would require LLM prompt changes + fixture updates + Stage 2 schema migration), detect interconnect type from the existing `egpu_model` string using keyword matching — consistent with how `_has_egpu_bundle()` already works.

## Files to Modify

- `src/laptopfinder/decide.py` — add `_apply_egpu_interconnect_penalty()`, wire into `calculate_llm_index_score()`
- `tests/test_decide.py` — add `TestApplyEgpuInterconnectPenalty` class, update imports

## TDD Plan

### Step 1: Write failing tests

Add to `tests/test_decide.py` (after the `TestApplyArchitecturePenalty` class):

```python
class TestApplyEgpuInterconnectPenalty:
    def _make_analysis(self, egpu_model=None, exact_model_name=None, system_ram=None):
        return {
            "extracted_data": {
                "exact_model_name": exact_model_name,
                "egpu_model": egpu_model,
                "total_system_ram": system_ram,
            }
        }

    def test_non_egpu_returns_zero(self):
        analysis = self._make_analysis(exact_model_name="Dell XPS 15", egpu_model=None)
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0

    def test_egpu_tb34_returns_penalty(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=16)
        assert _apply_egpu_interconnect_penalty(analysis, REF) == -3

    def test_egpu_oculink_returns_zero(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Minisforum DEG2 OCuLink")
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0

    def test_egpu_thunderbolt5_returns_zero(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X Thunderbolt 5")
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0

    def test_egpu_tb5_shorthand_returns_zero(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Some Dock TB5")
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0

    def test_zero_penalty_condition_system_ram_32(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=32)
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0

    def test_zero_penalty_condition_system_ram_64(self):
        analysis = self._make_analysis(exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=64)
        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
```

Import to add at line ~25: `_apply_egpu_interconnect_penalty`

Run `make test` — expect 7 failures (function doesn't exist yet).

### Step 2: Implement

Add to `src/laptopfinder/decide.py` (after `_apply_architecture_penalty`, before `calculate_llm_index_score`):

```python
def _apply_egpu_interconnect_penalty(analysis: dict, ref: dict) -> int:
    """Return TB3/4 interconnect penalty for eGPU bundles; 0 otherwise.

    Interconnect type is inferred from egpu_model keywords (no schema field exists).
    zero_penalty_condition: system_ram_gb >= 32 waives penalty regardless of interconnect.
    """
    extracted = analysis.get("extracted_data", {})
    model = extracted.get("exact_model_name")
    egpu_model = extracted.get("egpu_model")
    if not _has_egpu_bundle(model, egpu_model, ref):
        return 0
    system_ram = extracted.get("total_system_ram")
    if system_ram and system_ram >= 32:
        return 0
    cfg = ref.get("egpu_interconnect_penalty", {})
    egpu_lower = (egpu_model or "").lower()
    if "oculink" in egpu_lower or "thunderbolt 5" in egpu_lower or "tb5" in egpu_lower:
        return cfg.get("oculink_pts", 0)
    return cfg.get("thunderbolt_3_4_pts", -3)
```

Wire into `calculate_llm_index_score()` — add after the `_apply_architecture_penalty` call:
```python
raw += _apply_egpu_interconnect_penalty(analysis, ref)
```

### Step 3: Run tests — expect pass

`make test` green.

## Existing Fixture Coverage

`tests/fixtures/stage2/ebay_egpu_bundle.json` has `egpu_model: "XG Mobile RTX 4090"` — no OCuLink/TB5 keyword, `total_system_ram: null`. This fixture will produce a -3 penalty after wiring. No fixture modification needed, but verify that the existing `ebay_egpu_bundle.json`-based decide tests still pass (the score will be 3 pts lower — check if any test hardcodes a specific score value that would break).

## Verification

1. `make test` — green (7 new tests pass)
2. Confirm `ebay_egpu_bundle.json` fixture-driven decide test still passes
3. Spot-check: `decide(egpu_analysis, ref)["llm_index_score"]` is 3 pts lower than equivalent non-eGPU analysis
