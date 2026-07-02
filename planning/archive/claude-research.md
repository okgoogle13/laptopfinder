# Research Findings — Sprint 2

## Codebase Research

### Architecture Summary

Three-stage pipeline: Stage 1 (Discovery) → Stage 1A (Handoff) → Stage 2 (Analysis) → Decision Engine. All governance via `config/static_reference_layer.json`. Python is flat-function style, no OOP, schema constraints replace Python validation.

### Key Findings for inject_config.py

**Existing placeholder tokens in prompts/:**
- `[INJECT_TARGETS_HERE]` in `prompts/comet_discovery_agent.txt` (line 8) — the only placeholder currently in any prompt file
- No other `alternative_silicon_*.txt` files exist with placeholders; the alternative silicon prompts (`alternative_silicon_gemini.txt`, `alternative_silicon_perplexity.txt`) are present but have no placeholder tokens

**VRAM/UMA values to inject (from static_reference_layer.json):**
```json
vram_gating_logic: {
  "standard_mobile_min_gb": 16,
  "touchscreen_exception_min_gb": 12,
  "uma_unified_min_gb": 32
}
vram_tiers: {
  "entry": {"min_gb": 8, "max_gb": 12},
  "mid": {"min_gb": 16, "max_gb": 23},
  "high": {"min_gb": 24, "max_gb": 31},
  "extreme": {"min_gb": 32, "max_gb": 128}
}
uma_platforms.min_total_ram_gb_to_shortlist: 32
uma_platforms.chip_patterns: [M1 Max, M1 Ultra, M2 Max, M2 Ultra, M3 Max, M3 Ultra, M4 Max, M4 Ultra, Ryzen AI Max, Strix Halo]
target_gpus: 15 entries
watch_list: 5 entries
```

**Implication:** `inject_config.py` needs to either (a) replace the existing `[INJECT_TARGETS_HERE]` token with a formatted targets block, or (b) define new placeholder conventions and add them to the prompt files first. The spec says to replace placeholder text — so option (a) for comet_discovery_agent.txt, and we need to define what placeholders go into the alternative silicon prompts.

### Makefile — Existing Targets

```
make test        → pytest
make lint        → ruff
make decide      → Stage 2 + decision on fixture
make pipeline    → Stage 1 → Stage 2 → decision
make live        → full agentic pipeline on raw text
make evidence-run / evidence-run-dry / evidence-reset
```

New targets to add: `inject-config`, `scrape-and-live`.

### scripts/ Directory

Does **not exist**. Must be created.

### Dependencies

`firecrawl-py` is **not installed**. Must be added via `uv add firecrawl-py`.

Current API deps: google-genai, anthropic, openai, python-dotenv, pyyaml, jsonschema.

### Testing Setup

- Framework: pytest, run via `.venv/bin/pytest tests/ -v`
- Pattern: fixture-driven. Each test file loads JSON fixtures from `tests/fixtures/stage1/` or `tests/fixtures/stage2/`
- New scripts (inject_config.py, scrape_live.py) will need test coverage — either unit tests or fixture-based integration tests

### data/ Structure Relevant to Sprint

- `data/feed_live.txt` — output of scrape_live.py (does not yet exist)
- `data/shortlist_candidates.jsonl` — output of decision engine batch run (does not yet exist)
- `data/feed_manual.txt` — manual FB Marketplace paste target (does not yet exist)

## Web Research — firecrawl-py (completed after research phase)

**v1 client class is `Firecrawl`, not `FirecrawlApp`.** `FirecrawlApp` is v0 (deprecated). Import: `from firecrawl import Firecrawl`.

**v1 scrape method:** `fc.scrape(url, formats=["markdown"])` — not `scrape_url(url, params={...})`. Response is an object: access `doc.markdown`, not `response["markdown"]`.

**`only_main_content=True` is the default** — strips nav/footer/sidebars natively before Markdown conversion. This handles most chrome removal without regex. `exclude_tags=[...]` provides fine-grained CSS-selector-level exclusion.

**Batch scraping:** `fc.batch_scrape(urls, formats=["markdown"])` is 0.5 credits/page vs 1.0 for individual scrapes. Use for 5+ URLs.

**eBay AU specifics:**
- Needs `wait_for=3000` (ms) for JS-rendered price/condition fields
- Include `include_tags=["#prcIsum", ".x-price-primary", "#itemTitle"]` to guarantee key fields survive
- Keep `maxConcurrency ≤ 5` for eBay to avoid blocks

**Error codes:** 401 = bad key (fail fast), 402 = credits exhausted (fail fast), 429 = rate limit (exponential backoff).

**`product` format:** `formats=["markdown", "product"]` returns `doc.product` as a structured dict with title/price/description — useful complement to raw markdown for listing pages.

## Testing Preferences

Existing project uses pytest with fixture-driven integration tests. New modules should follow the same pattern:
- `inject_config.py`: test that known placeholders in a temp copy of a prompt file get replaced correctly
- `scrape_live.py`: test with a saved HTML or mock HTTP response (no live Firecrawl calls in CI)
