# HANDOVER — UMA SoC bandwidth-tier scoring

**To:** Gemini implementation agent
**From:** Claude (orchestrator)
**Date:** 2026-07-06
**Status:** Validated design, ready to implement. Peer-reviewed via blind-debate (2 rounds, converged); every finding below is test-proven against the existing fixture suite, not hypothetical.

> Supersedes the prior eBay-sniper handoff (completed; preserved in git history + `TASKS.md`/`memory/project/sprint.md`).

## Report-back contract (read first)

When done, reply to Claude with:
1. **Result:** `COMPLETE` / `BLOCKED` / `PARTIAL`.
2. **Diff summary:** files touched + one line each on what changed.
3. **Verification evidence:** paste the tail of `make test` and `make lint` output showing pass/fail counts. Do not claim success without pasted command output.
4. **Deviations:** anything you did differently from this brief and why.
5. **Open questions:** anything you had to guess.

If you get BLOCKED (ambiguous spec, a test you can't satisfy without a design call, a failing assertion you don't understand), stop and report — do **not** improvise a workaround or delete/weaken a test to make it pass.

## Environment (non-negotiable)

- Use `.venv` (uv-managed). Invoke `.venv/bin/python` and `.venv/bin/pytest`, never system Python.
- Run tests with `make test`, lint with `make lint`. Both must be green before you report COMPLETE.
- House style (Karpathy): flat structures, no OOP/custom exceptions, no clever abstractions. **Static JSON config is the governance layer** — thresholds/lists/weights live in `config/static_reference_layer.json` (the "SRL"), logic lives in Python. Missing data → `null`, never inferred.

## Background / why

In the decision engine (`src/laptopfinder/decide.py`), GPUs have a rich semantic stack (identity → generation → points → routing). CPUs do not: `extracted_data.cpu` only feeds UMA detection. On discrete-GPU laptops that is correct (inference is GPU-bound). But in the **UMA branch the SoC IS the accelerator**, and today every qualifying chip collapses to a flat `gpu_generation_points["Apple Silicon"] = 20` plus RAM-tier capacity points. So an M1 Max 64GB and an M3 Ultra 64GB score identically despite a ~2–4× memory-bandwidth gap — the dominant driver of UMA LLM token/s.

**Goal:** give the UMA SoC its own bandwidth-tier → points scoring, mirroring the GPU generation pattern, scoped strictly to the UMA branch. Do **not** add discrete-CPU scoring, a `target_cpus` table, or any unified GPU/CPU abstraction — those were explicitly rejected in review as dead config / anti-simplification.

## Do the tasks in this order, running `make test` after each

### Task 1 — SRL config (`config/static_reference_layer.json`)

Add two new top-level keys mirroring `gpu_generation_by_name` + `gpu_generation_points`:

- `uma_soc_by_name`: dict, **chip name → bandwidth tier string**. Substring-match keys, same convention as `gpu_generation_by_name`.
- `uma_soc_bandwidth_points`: dict, **tier → points (int)**. Keep the max in the same ~25 ballpark as `gpu_generation_points` so UMA and discrete stay commensurable on the 0–100 `llm_index_score`.

Reference bandwidths to guide tier assignment (approximate, GB/s):
- Ultra tier (~800): `M1 Ultra`, `M2 Ultra`, `M3 Ultra`, `M4 Ultra`
- Max tier (~400–550): `M1 Max`, `M2 Max`, `M3 Max`, `M4 Max`
- AMD APU tier (~256): `Strix Halo`, `Ryzen AI Max`

Suggested (adjust only with better data, and justify): `{"ultra_bw": 25, "high_bw": 20, "mid_bw": 15}`. **Do not make later Apple generations score lower than earlier ones** unless real bandwidth data supports it (flagged in review).

**CRITICAL — do NOT derive `uma_platforms.chip_patterns` from `uma_soc_by_name` keys.** Keep `chip_patterns` as a separate materialized list exactly as it is now. Reasons (both test-proven):
- `chip_patterns` also drives `_classify_paradigm()`'s `amd_uma` routing and is read directly by `scripts/inject_config.py:41` to render `UMA_CHIP_PATTERNS` into prompts. Deriving from a single canonical key drops aliases and breaks `tests/test_inject_config.py` + `tests/test_prompt_parity.py`.
- The `"Ryzen AI Max"` alias matters: fixture `tests/fixtures/stage2/fb_uma_strix_halo_low_ram.json` has `cpu="Ryzen AI Max"`. Losing it reroutes the listing to `discrete_cuda` and breaks `test_decide.py::TestIsUmaPlatform::test_strix_halo_match` and `TestParadigmClassification::test_strix_halo_uma`.

Include **both** `"Strix Halo"` and `"Ryzen AI Max"` as keys in `uma_soc_by_name` (both → the AMD APU tier) so the SoC lookup has alias coverage matching `chip_patterns`.

### Task 2 — Precompute (`_precompute_ref` in `decide.py`, ~line 29)

Add a lowercased lookup mirroring the existing `_gen_by_name_lower` block exactly:

```python
ref["_uma_soc_by_name_lower"] = {
    name.lower(): tier
    for name, tier in ref.get("uma_soc_by_name", {}).items()
}
```

### Task 3 — Parallel scoring helper (`decide.py`)

Add a **new** function `_uma_soc_points(cpu, model, ref)` — do NOT overload `_gpu_generation_points`. (Reviewed: overloading forces a broken signature because UMA fixtures have `gpu=null` and the SoC identity lives in `cpu`/`model`, which `_gpu_generation_points(gpu, is_uma, ref)` never receives.)

Mirror `_resolve_gpu_generation` (`decide.py:225`): case-insensitive substring match of the `cpu`+`model` haystack against `_uma_soc_by_name_lower` → tier → `uma_soc_bandwidth_points[tier]`.

**Mandatory fallback:** if no SoC matches (e.g. a future `M5 Max` present in `chip_patterns` but not yet in `uma_soc_by_name`), return `points_by_gen.get("Apple Silicon", 0)` — the current flat value — so new chips never silently drop to 0. Do not return 0 on miss.

### Task 4 — Wire it in, at BOTH call sites

`_gpu_generation_points` is called twice; both must become UMA-aware so the UMA path uses SoC points instead of the flat `"Apple Silicon"` value:

- **`calculate_llm_index_score` (`decide.py:367`, uses it at line 381):** thread `cpu` and `model` into this function's signature and, when `is_uma`, use `_uma_soc_points(cpu, model, ref)` instead of `_gpu_generation_points(...)`. Update its caller `decide()` at line 444 to pass `cpu`/`model` (both already local vars in `decide()`).
- **`decide()` line 431 (`generation_points = _gpu_generation_points(gpu, is_uma, ref)`):** this value feeds `_log_undiscovered_hardware`, which early-returns when it is non-zero. Make this UMA-aware too (use `_uma_soc_points` when `is_uma`) so UMA listings keep a non-zero value and are not spuriously logged as undiscovered hardware.

Cleanest: have both sites select via `is_uma` (`_uma_soc_points(cpu, model, ref) if is_uma else _gpu_generation_points(gpu, is_uma, ref)`), or introduce one tiny dispatcher both call. Keep it flat.

### Task 5 — Fixtures + tests

- Add at least one new Stage 2 fixture pair under `tests/fixtures/stage2/` that isolates the new signal: two UMA listings at **equal system RAM** but different SoC tiers (e.g. an M3 Ultra vs an M1 Max, both 64GB) so their `llm_index_score` now differs. Follow the format of existing `ebay_uma_mac_studio.json` / `fb_uma_macbook_pro.json` (top-level `handoff_packet`, `full_listing_text`, `analysis_output`; every extracted fact must appear verbatim in `full_listing_text` — the grounding firewall will reject otherwise).
- Add a test in `tests/test_decide.py` asserting the higher-bandwidth SoC scores strictly higher, and a test for the fallback path (a UMA chip in `chip_patterns` but absent from `uma_soc_by_name` still scores the Apple-Silicon fallback, not 0).
- Confirm the existing Strix Halo / inject_config / prompt_parity tests still pass unchanged.

## Acceptance criteria

- `make test` fully green (paste output). `make lint` clean (paste output).
- No existing fixture's routing (`recommended_action`) changes except intended UMA `llm_index_score` differentiation.
- No `chip_patterns` derivation; `"Ryzen AI Max"` alias preserved in both `chip_patterns` and `uma_soc_by_name`.
- New helper is a standalone function with a real fallback; no overload of `_gpu_generation_points`.
- Config carries the values; Python only carries logic.

When all criteria are met, report back per the contract at the top.
