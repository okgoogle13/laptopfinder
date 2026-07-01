# Opus Review

**Model:** claude-opus-4-8
**Generated:** 2026-07-02T00:00:00Z

---

Overall this is a well-structured, convention-aware plan. The function signatures, test list, and delivery sequence are concrete. However there is one serious architectural flaw in the core "config injection" concept, plus several downstream-interaction gaps that will bite during a real purchase run.

## Critical

**1. Section 2 (inject_config) — the injection mechanism is destructive and runs exactly once, defeating its own purpose.**
The stated goal is "prompts never drift from the governance layer." But the design replaces the literal token `[INJECT_TARGETS_HERE]` with a rendered GPU block. After the first `make inject-config`, the token is gone. On the next config change, re-running the script finds no token, makes 0 replacements, and the prompt keeps the *stale* injected list forever. So the prompt drifts silently — the exact failure mode the feature exists to prevent. Same problem for `[UMA_MIN_RAM_GB]`, `[UMA_CHIP_PATTERNS]`, `[TARGET_GPU_LIST]`.

This must be marker-based, not token-consuming. Use paired sentinels, e.g.:
```
<!-- BEGIN_INJECT:TARGETS -->
...rendered block...
<!-- END_INJECT:TARGETS -->
```
and have `inject_file` replace the content *between* markers, leaving the markers in place so it is re-runnable and idempotent.

**2. Section 2 — mutating git-tracked prompt files in place creates commit noise and a second source of truth.**
Every `make inject-config` (and `make scrape-and-live`) rewrites them, producing a git diff. Decide whether injected prompts are generated artifacts (git-ignored) or committed. If committed, `scrape-and-live` should not silently mutate them on every scrape.

## Field/shape mismatches with the actual codebase

**3. Section 2 — `srl["target_gpus"]` is a dict, `srl["watch_list"]` is a list of objects.**
`target_gpus` names are the dict keys. `watch_list` entries each have a `["name"]` field. `build_substitutions` must handle both shapes. Test fixtures should match the real structure.

**4. Section 4 — render_matrix's expected fields do not come from `decide()`.**
`decide()` returns `recommended_action` and `llm_index_score` but has no `listing_title`, `gpu`, `price`, or `notes`. The plan should specify where each field originates and provide a helper that joins decide() output with Stage 2 handoff data.

## Downstream interaction gaps

**5. Section 3 — `strip_nav` will corrupt the grounding firewall.**
The regex `r'(?i)(breadcrumb|cookie|sign in|cart|watchlist).*?\n'` deletes entire lines on substring matches (`cart` hits `cartridge`). Add word boundaries. Also, Firecrawl Markdown emphasis/links (`**bold**`, `[text](url)`) break verbatim word-boundary grounding matches — specify markdown normalization.

**6. Section 3 — multiple listings concatenated into one feed file is batch-fatal.**
One bad listing (matching `exclusion_regex`) aborts the whole Stage 2 run. Per-listing failures must be isolable.

## Robustness / correctness

**7. Firecrawl API shape is version-fragile.** Recent versions use `scrape_url(url, formats=["markdown"])` and return a response object with `.markdown`, not a dict key. Pin the version in `pyproject.toml`.

**8. `os.environ["FIRECRAWL_API_KEY"]` KeyError.** Handle missing key with a clear error message rather than a bare crash.

**9. No content sanity check.** FB/Gumtree may return login-wall content without raising an exception. Add a minimum-content check (warn/skip if cleaned Markdown is under N chars).

**10. `sort_candidates` crashes on missing `llm_index_score`.** `None` compared to `int` raises `TypeError`. Default missing scores to `-1`.

**11. Unescaped `|` breaks the Markdown table.** Listing titles and notes commonly contain `|`. Escape in `render_table`.

**12. `load_candidates` malformed-line handling unspecified.** One bad JSONL line crashes the whole render. Specify skip-and-warn or fail-fast explicitly.

## Minor

- `build_substitutions(srl, profiles)` — `profiles` is unused in v1. Drop the dead parameter.
- Construct `FirecrawlApp` once in `main`, not per-URL.
- `data/feed_live.txt`, `data/purchase_matrix.md` should be `.gitignore`d as generated artifacts.
- Provenance `<!-- {url} -->` comments may embed tracking query params — consider stripping query strings.

## What's good

- Delivery sequence is sensibly ordered.
- Consistent adherence to project conventions (flat functions, config-driven, fixture tests).
- Error-continue behaviour for scraping is the right instinct.

The single most important change is item 1 (marker-based, idempotent injection). Items 5 and 6 are the ones most likely to produce confusing runtime `ValueError`s during an actual purchase run.
