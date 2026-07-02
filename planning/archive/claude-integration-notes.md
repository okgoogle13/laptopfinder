# Integration Notes — Opus Review

## Integrating

**Item 1 — Marker-based idempotent injection (CRITICAL)**
The one-shot token consumption design is broken by design. Switching to paired sentinel comments (`<!-- BEGIN_INJECT:X --> ... <!-- END_INJECT:X -->`) fixes the core flaw. `inject_file` now replaces content between markers, leaving markers intact. Running twice yields identical output. The test assertion changes from "token absent" to "idempotent: second run matches first."

**Item 2 — git-tracked files / scrape-and-live dependency**
Decision: treat prompt files as committed source. The `scrape-and-live` target will NOT implicitly depend on `inject-config`. Operators run `make inject-config` explicitly when config changes. This avoids silent re-mutation on every scrape. The Makefile will document this.

**Item 3 — SRL shape correctness**
`target_gpus` is a dict — iterate `.keys()`. `watch_list` is a list of objects — extract `entry["name"]`. Updated in `build_substitutions` spec and test fixtures.

**Item 4 — render_matrix field origins**
The plan will add a `JSONL field reference` section specifying exactly where each column comes from: `recommended_action` and `llm_index_score` from decide() output; `listing_title`, `price`, `gpu` from the Stage 2 handoff_packet the operator used. A note will explain the operator must manually merge these. No helper script added (out of scope for Day 7; the value is the table, not automation).

**Item 5 — strip_nav regex safety**
Replace the unbounded substring match with a more targeted pattern anchored to line-start nav patterns. Also add a step to strip Markdown emphasis and link syntax from `full_listing_text` before it is written to the feed file, to prevent grounding firewall false positives.

**Item 6 — per-listing isolation**
`scrape_live.py` will write each listing as a separate file to `data/feed_live/` rather than concatenating into one blob. A subsequent `make live` step will iterate per-file. This isolates bad listings without aborting the batch. The Makefile `scrape-and-live` target will be updated accordingly.

**Item 7 — Pin firecrawl-py version**
Pin to a specific version (check PyPI for latest stable at install time). Confirm API shape against installed release before coding the fetch call. Document which version was verified.

**Item 8 — FIRECRAWL_API_KEY guard**
Use `os.environ.get("FIRECRAWL_API_KEY")` with an explicit `sys.exit("FIRECRAWL_API_KEY not set")` early-return, consistent with how other runners handle missing keys.

**Item 9 — Minimum content sanity check**
After stripping nav, if cleaned Markdown length < 200 chars, print `WARN: suspiciously short content for {url} ({n} chars) — possible login wall` to stderr and skip. Does not abort the run.

**Item 10 — sort crash on missing score**
`sort_candidates` key: `(-{"SHORTLIST":0,"MONITOR":1}.get(c.get("recommended_action","SKIP"),2), -(c.get("llm_index_score") or -1))` — missing or None score treated as -1 (sorts last within group).

**Item 11 — Pipe escaping**
`render_table` escapes `|` → `\|` and strips newlines in all cell values.

**Item 12 — JSONL malformed line handling**
`load_candidates`: skip-and-warn. Each line is wrapped in try/except; bad lines print `WARN: skipping malformed line {n}` to stderr.

**Minor — drop dead `profiles` parameter**
`build_substitutions(srl)` only. `silicon_profiles.yaml` not loaded in v1.

**Minor — construct Firecrawl client once**
`main()` constructs one `Firecrawl` instance (v1 client — `from firecrawl import Firecrawl`, NOT deprecated `FirecrawlApp`) and passes it to `fetch_markdown`.

**Minor — .gitignore**
`data/feed_live/` and `data/purchase_matrix.md` added to `.gitignore` (already done in section-01 commit fd602ad). `data/feed_live.txt` is NOT a target — output is per-listing files in `data/feed_live/`, not a single blob.

## Not integrating

**"Write rendered prompts to build/ directory"** (Item 2 alternative): The project uses committed prompt files as the source of truth for what gets pasted into Gemini/Perplexity manually. Treating them as generated artifacts would break the human-in-the-loop workflow. The marker-based approach (Item 1) makes re-injection safe; committed files remain the canonical form.

**"Helper that auto-joins decide() output with Stage 2 handoff"** (Item 4): Out of scope for this sprint. Day 7 is a human-assembled JSONL and a renderer. Automation of the join is a future sprint item.

**"Per-URL timeout"** (Item 9): Firecrawl handles HTTP timeouts server-side. Adding a client-side `socket.setdefaulttimeout` is out of scope and potentially interferes with other runners. The minimum-content check catches silent failures.
