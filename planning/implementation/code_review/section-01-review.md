# Code Review — section-01-discovery-prompt-fix

## HIGH — Inline sentinel incompatible with inject_file replacement template

`inject_config.py` uses `replacement = rf"\1\n{value}\n\2"` — always wraps with newlines.
The inline sentinel `<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->32<!-- END_INJECT:UMA_MIN_RAM_GB -->` 
becomes `\n32\n` after first `make inject-config` run, breaking the line into:

    minimum <!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->
    32
    <!-- END_INJECT:UMA_MIN_RAM_GB --> GB unified/system RAM.

LLM reads: `minimum \n32\n GB` — number and unit on different lines, no syntactic glue.
All other UMA_MIN_RAM_GB sentinels in repo (alt-silicon prompts) are block-format.

**Fix:** Restructure to block-format sentinel.

## MEDIUM — test_prompt_parity.py has no sync guard for comet's new UMA_MIN_RAM_GB sentinel

`test_prompt_parity.py:_read_inject_block()` uses `\n(.*?)\n` pattern requiring newlines
immediately after BEGIN tag — inline format wouldn't match. Even after the block-format fix,
no sync assertion exists for comet's sentinel (alt-silicon prompts have them at lines 104-117).

**Fix:** Add a sync assertion for comet's UMA_MIN_RAM_GB in test_prompt_parity.py.

## LOW — TASKS.md revert unrelated to section goal

The diff reverts architecture_adjustments [x] → [ ] with no explanation in the diff context.
Correct (the function IS a stub), but should be called out in the commit message explicitly.

**Fix:** Mention in commit message: "also corrects TASKS.md: architecture penalty stub was incorrectly marked done".
