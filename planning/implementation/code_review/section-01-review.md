# Code Review — section-01-prerequisites

## Finding 1 (HIGH): UMA_MIN_RAM_GB sentinel creates stale-value conflict

In both `prompts/alternative_silicon_gemini.txt` and `prompts/alternative_silicon_perplexity.txt`, the `BEGIN_INJECT:UMA_MIN_RAM_GB` / `END_INJECT:UMA_MIN_RAM_GB` pair was placed *after* the line that already hardcodes the value:

```
  * UMA Platforms (Apple Silicon, Strix Halo): minimum 64 GB total system RAM to qualify.
<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->
<!-- END_INJECT:UMA_MIN_RAM_GB -->
```

When inject_config.py populates the block, the LLM sees the hardcoded "64 GB" immediately above the injected value. If the SRL threshold changes, the static text becomes stale while the injected value is correct — contradictory thresholds. The sentinel should replace or wrap the hardcoded numeric value, not trail it.

The `UMA_CHIP_PATTERNS` sentinel is additive (appends after hardcoded list), which risks duplicate entries if inject_config.py emits patterns already in the static list.

## Finding 2 (MEDIUM): scripts/sync_agent_hooks.py is a scope leak

The diff stages `scripts/sync_agent_hooks.py` as a new file, but it pre-existed as an untracked file before this section ran. Section 01's scope is creating `scripts/.gitkeep` only. Sweeping in sync_agent_hooks.py conflates commits and muddles git bisect attribution.

Also: `sync_agent_hooks.py` has no `path.parent.mkdir(parents=True, exist_ok=True)` guard — latent crash on fresh clone.

## Finding 3 (LOW): firecrawl-py version constraint too loose

`pyproject.toml` specifies `firecrawl-py>=4.31.0`. Should be `~=4.31` (compatible-release) to protect against a future major version breaking the v1 `from firecrawl import Firecrawl` import path.

## Other notes

- `.gitignore` negation (`!.env.example`) is correct.
- `comet_discovery_agent.txt` sentinel replacement is clean (replaced a placeholder, no hardcoded value conflict).
- `alternative_silicon_gemini.txt` line ~147 still references "all UMA platforms capped at 75 total" (stale UMA ceiling reference) — pre-dates this diff, out of scope here.
