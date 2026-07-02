Now I have all the context needed. Here is the section content:

---

# Section 01 — Prerequisites

**Blocks:** All other sections (02, 03, 04, 05). Complete this before starting any other section.

**No automated tests.** The TDD plan explicitly excludes tests for these setup steps. Verify each item manually.

---

## Overview

This section creates the structural scaffolding required by the three Sprint 2 deliverables:

- `scripts/inject_config.py` (section 02)
- `src/laptopfinder/scrape_live.py` (section 03)
- `scripts/render_matrix.py` (section 04)

The work is purely mechanical: install a new dependency, create a directory, update ignore and env files, and insert sentinel markers into three prompt files.

---

## 1. Create the `scripts/` Directory

The `scripts/` directory does not yet exist. Create it with a placeholder to make it git-trackable:

```
/Users/okgoogle13/Projects/laptopfinder/scripts/.gitkeep
```

No `__init__.py` is needed — scripts in this directory are invoked directly, not imported as a package.

---

## 2. Install `firecrawl-py`

The Firecrawl client is not yet in `pyproject.toml`. Add it using uv so the version is pinned in `pyproject.toml` and `uv.lock`:

```bash
cd /Users/okgoogle13/Projects/laptopfinder
uv add firecrawl-py
```

Pin to the specific version uv resolves. After running, verify that `pyproject.toml` at `/Users/okgoogle13/Projects/laptopfinder/pyproject.toml` now lists `firecrawl-py` under `[project] dependencies`.

**Critical API shape for section 03** — the v1 client interface (confirm this matches the installed version before section 03 proceeds):

```python
from firecrawl import Firecrawl          # v1 — NOT FirecrawlApp (deprecated v0)
fc = Firecrawl(api_key="...")
doc = fc.scrape(url, formats=["markdown"], wait_for=3000)
content = doc.markdown                   # attribute, not dict key
```

If `doc.markdown` raises `AttributeError`, the installed version may be v0. Check `pip show firecrawl-py` and the package changelog to confirm the v1 scrape response shape.

---

## 3. Document `FIRECRAWL_API_KEY` in `.env.example`

File: `/Users/okgoogle13/Projects/laptopfinder/.env.example`

Add one line after the existing `PERPLEXITY_API_KEY` entry:

```
# Firecrawl API (used by scrape_live for listing page fetch)
FIRECRAWL_API_KEY="your_firecrawl_api_key_here"
```

The existing `.env.example` already has `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, and `PERPLEXITY_API_KEY`. Do not remove or reorder those entries.

---

## 4. Update `.gitignore`

File: `/Users/okgoogle13/Projects/laptopfinder/.gitignore`

Add two entries for build artifacts that must not be committed:

```
# Live scrape output and rendered matrices (generated build artifacts)
data/feed_live/
data/purchase_matrix.md
```

Append these after the existing `restored_conversations/` entry. Both paths are outputs of the Sprint 2 pipeline — they change on every run and must not be tracked in source control.

---

## 5. Add Sentinel Marker Pairs to Prompt Files

This is a **one-time manual edit** to the three prompt files that `inject_config.py` will manage. The sentinel format is:

```
<!-- BEGIN_INJECT:TOKEN_NAME -->
...content injected here by inject_config.py...
<!-- END_INJECT:TOKEN_NAME -->
```

`inject_config.py` replaces content *between* the markers, leaving the markers in place. The markers must be present before the first run of `make inject-config`.

### 5a. `prompts/comet_discovery_agent.txt`

File: `/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt`

Line 8 currently contains:

```
  [INJECT_TARGETS_HERE]
```

Replace that exact line with the `TARGETS` sentinel pair (leave surrounding lines unchanged):

```
<!-- BEGIN_INJECT:TARGETS -->
<!-- END_INJECT:TARGETS -->
```

Leave the content between the markers empty — `inject_config.py` will populate it on first run.

### 5b. `prompts/alternative_silicon_gemini.txt`

File: `/Users/okgoogle13/Projects/laptopfinder/prompts/alternative_silicon_gemini.txt`

This file has hardcoded threshold values and chip lists in the `PIPELINE GATE THRESHOLDS` section (lines 9–15 approximately). Add three sentinel pairs at appropriate locations in that section:

- After the UMA minimum RAM sentence, wrap or append a `UMA_MIN_RAM_GB` marker pair so `inject_config.py` can keep that value in sync with `static_reference_layer.json`.
- Near or after the UMA platform chip list, add a `UMA_CHIP_PATTERNS` marker pair.
- At a location where the target GPU list is referenced or should be surfaced, add a `TARGET_GPU_LIST` marker pair.

The exact placement is editorial judgement — put each marker pair where a reader would expect to find that value. Keep surrounding prose intact. Leave the content between each pair empty initially.

### 5c. `prompts/alternative_silicon_perplexity.txt`

File: `/Users/okgoogle13/Projects/laptopfinder/prompts/alternative_silicon_perplexity.txt`

Same three sentinel pairs as 5b — `UMA_MIN_RAM_GB`, `UMA_CHIP_PATTERNS`, and `TARGET_GPU_LIST` — placed in the `MEMORY GATE THRESHOLDS` section and adjacent areas. The perplexity variant has the same categories but different prose structure; place markers where the equivalent values appear in that file.

---

## Verification Checklist

Before proceeding to sections 02–04, confirm:

- [x] `/Users/okgoogle13/Projects/laptopfinder/scripts/` directory exists
- [x] `pyproject.toml` lists `firecrawl-py` with a pinned version (`~=4.31`)
- [x] `uv.lock` is updated
- [x] `.env.example` contains `FIRECRAWL_API_KEY` entry
- [x] `.gitignore` contains `data/feed_live/` and `data/purchase_matrix.md`
- [x] `prompts/comet_discovery_agent.txt` has `BEGIN_INJECT:TARGETS` / `END_INJECT:TARGETS` markers in place of `[INJECT_TARGETS_HERE]`
- [x] `prompts/alternative_silicon_gemini.txt` has all three marker pairs (`UMA_MIN_RAM_GB`, `UMA_CHIP_PATTERNS`, `TARGET_GPU_LIST`)
- [x] `prompts/alternative_silicon_perplexity.txt` has all three marker pairs
- [x] `python -c "from firecrawl import Firecrawl; print('ok')"` succeeds inside `.venv`

## Implementation Notes

**Deviations from plan:**

- `firecrawl-py` pinned as `~=4.31` (compatible-release) rather than `>=4.31.0` — protects the v1 `Firecrawl` import path against future major-version API breakage.
- `.gitignore` got a `!.env.example` negation — the pre-existing `.env.*` pattern blocked `.env.example` from being staged. Added to allow `.env.example` to be tracked without `-f`.
- `UMA_MIN_RAM_GB` sentinel placement revised: the hardcoded "64 GB" was stripped from both gemini/perplexity bullet lines so the sentinel fully owns the threshold value, avoiding stale-value conflict if the SRL threshold changes.
- `scripts/sync_agent_hooks.py` was intentionally excluded from this commit (pre-existing untracked file, out of scope for section-01).

**Files created/modified:**
- `scripts/.gitkeep` (new)
- `pyproject.toml` (firecrawl-py dependency added)
- `uv.lock` (updated)
- `.env.example` (FIRECRAWL_API_KEY entry added; `!.env.example` gitignore negation)
- `.gitignore` (`!.env.example` negation, `data/feed_live/`, `data/purchase_matrix.md`)
- `prompts/comet_discovery_agent.txt` (TARGETS sentinel)
- `prompts/alternative_silicon_gemini.txt` (UMA_MIN_RAM_GB, UMA_CHIP_PATTERNS, TARGET_GPU_LIST sentinels)
- `prompts/alternative_silicon_perplexity.txt` (same three sentinels)