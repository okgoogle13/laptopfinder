# Code Review — section-02-inject-config

## Finding 1 (HIGH): TARGETS and TARGET_GPU_LIST inject identical content

`build_substitutions` sets both `TARGETS` and `TARGET_GPU_LIST` to `gpu_names + watch_names`. But `watch_list` items (RTX 5090, GB200 etc.) carry `routing_behaviour: "MONITOR overrides all positive signals"` — they are explicitly NOT confirmed targets. Injecting them into `TARGET_GPU_LIST` (used by alt-silicon prompts) will instruct those agents to seek listings the decision engine is designed to reject. The two tokens should differ: `TARGET_GPU_LIST` = `gpu_names` only; `TARGETS` may optionally include watch-list names as awareness context.

## Finding 2 (HIGH): Prompt file changes absent from diff

Prompt sentinels were committed in section-01. Reviewer notes they can't verify placement — not actionable here, context limitation.

## Finding 3 (MEDIUM): inject_file writes unconditionally

Line 63 calls `p.write_text()` even when `count == 0`, touching mtime and producing VCS noise. Should be gated on `count > 0`.

## Finding 4 (MEDIUM): Idempotency test uses weak assertion

`assert count2 >= 1` should be `assert count2 == 1`. A double-replacement bug would pass the current assertion.

## Finding 5 (MEDIUM): No test for partial marker corruption

If `END_INJECT` is deleted, `inject_file` silently returns 0. No test covers this failure mode. Should add a test verifying the function returns 0 (not raises) and file is unchanged.

## Finding 6-7 (LOW): Missing SRL key guards

Project philosophy: schema constraints replace Python validation. Let go.

## Finding 8 (LOW): test_load_srl write_text missing encoding

`srl_file.write_text(json.dumps(MOCK_SRL))` should be `write_text(..., encoding="utf-8")`.

## Finding 9 (LOW): Integration test only asserts TARGETS

The integration test should also assert `UMA_MIN_RAM_GB` content was injected into the alt-silicon prompt stubs.
