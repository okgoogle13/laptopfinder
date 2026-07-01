# Code Review Interview — section-01-prerequisites

## Finding 1 (HIGH): UMA_MIN_RAM_GB sentinel stale-value conflict

**Decision: Replace hardcoded value (user approved)**

The hardcoded "64 GB" was removed from both bullet lines. The sentinel block now fully owns the threshold value:

```
  * UMA Platforms (Apple Silicon, Strix Halo):
<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->
<!-- END_INJECT:UMA_MIN_RAM_GB -->
```

inject_config.py (section 02) will inject the threshold value from `static_reference_layer.json` so no static text can conflict.

**Applied to:** `prompts/alternative_silicon_gemini.txt`, `prompts/alternative_silicon_perplexity.txt`

---

## Finding 2 (MEDIUM): scripts/sync_agent_hooks.py scope leak

**Decision: Auto-fix — unstage the file**

`scripts/sync_agent_hooks.py` was a pre-existing untracked file swept in by `git add scripts/`. Unstaged from this commit. Will be committed separately.

---

## Finding 3 (LOW): firecrawl-py version constraint

**Decision: Auto-fix**

Changed `firecrawl-py>=4.31.0` → `firecrawl-py~=4.31` in `pyproject.toml` to protect against future major-version API breakage. `uv sync --extra test` confirmed no breakage; `from firecrawl import Firecrawl` still works.
