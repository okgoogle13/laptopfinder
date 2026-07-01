# Code Review Interview — section-02-inject-config

## Finding 1 (HIGH): TARGETS vs TARGET_GPU_LIST scope

**Decision: Targets + watch-list in TARGETS only (user approved)**

- `TARGETS` (injected into `comet_discovery_agent.txt`): gpu_names + watch_names — comet gets both as awareness context.
- `TARGET_GPU_LIST` (injected into alt-silicon prompts): gpu_names only — watch-list items must not leak into alt-silicon prompts.

Added `test_target_gpu_list_excludes_watch_list_names` to prevent regression.

## Finding 2 (HIGH): Prompt file changes absent from diff

Not actionable — prompt edits were committed in section-01 (fd602ad). Reviewer context limitation.

## Finding 3 (MEDIUM): inject_file writes unconditionally

**Auto-fix:** Gated `p.write_text()` on `if count:` — no-op files no longer have mtime touched.

## Finding 4 (MEDIUM): Idempotency test weak assertion

**Auto-fix:** `assert count2 >= 1` → `assert count2 == 1`.

## Finding 5 (MEDIUM): No test for partial marker corruption

**Auto-fix:** Added `test_inject_file_partial_marker_returns_zero` — asserts count==0 and file unchanged when BEGIN exists but END is missing.

## Findings 6-7 (LOW): Missing SRL key guards

**Let go** — project philosophy (CLAUDE.md): schema constraints replace Python validation. Opaque KeyError is acceptable here.

## Finding 8 (LOW): write_text missing encoding

**Auto-fix:** Added `encoding="utf-8"` to `srl_file.write_text()` in test.

## Finding 9 (LOW): Integration test only asserts TARGETS

**Auto-fix:** Added assertions for `UMA_MIN_RAM_GB` sentinel and `"64"` value in all three stub files.
