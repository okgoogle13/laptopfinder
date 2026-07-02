---
name: tooling-usage
description: Operator usage guide for inject-config, scrape-live, and render-matrix tooling
metadata:
  type: reference
---

# Usage Guide — Live Tooling

Relocated 2026-07-02 from `planning/implementation/usage.md` (originally built by `/deep-implement` from `planning/sections/` during Sprint 2) — this file documents still-active tooling, so it lives here in `memory/reference/` alongside the other stable reference docs rather than in the historical `planning/` tree. See [[tooling]] for IDE/MCP setup and [[pipeline]] for pipeline terminology.

Covers `inject_config.py`, `scrape_live.py`, `render_matrix.py`, and their Makefile targets.

---

## Quick Start

```bash
# 1. Inject current SRL values into prompt sentinel markers
make inject-config

# 2. Populate your URL list
echo "https://www.ebay.com.au/itm/123456789012" >> data/urls.txt

# 3. Scrape listings and run the full pipeline on each
make scrape-and-live          # uses data/urls.txt by default
# or override:
make scrape-and-live FIRECRAWL_URLS=path/to/other.txt

# 4. Assemble shortlisted candidates and render the decision matrix
# (manually populate data/shortlist_candidates.jsonl first)
make render-matrix
cat data/purchase_matrix.md
```

---

## inject-config (`scripts/inject_config.py`)

Reads `config/static_reference_layer.json` and replaces content between `<!-- BEGIN_INJECT:KEY -->` / `<!-- END_INJECT:KEY -->` sentinel pairs in the three prompt files.

**Markers supported:**
| Key | Injected content |
|-----|-----------------|
| `target_gpu_list` | Comma-separated GPU names from SRL `target_hardware.gpus` (excludes watch-list entries) |
| `target_model_list` | All target GPU + watch-list names combined |
| `uma_min_ram_gb` | Value of `vram_gating_logic.uma_unified_min_gb` as a string |
| `uma_chip_patterns` | Comma-separated chip name patterns from `uma_platforms.chip_patterns` |

**Run:**
```bash
make inject-config
# or directly:
.venv/bin/python scripts/inject_config.py
```

**Expected output:**
```
comet_discovery_agent.txt: 1 block(s) replaced
alternative_silicon_gemini.txt: 3 block(s) replaced
alternative_silicon_perplexity.txt: 3 block(s) replaced
```

Idempotent — running twice produces no further `git diff`.

Note (2026-07-02 doc audit): `prompts/perplexity_space_description.txt` has no sentinel markers and is NOT covered by this injection step. Its target/watch lists must be updated by hand whenever SRL's `target_gpus` or `watch_list` change — see `.agents/skills/prompt-config-parity-audit/SKILL.md`.

---

## scrape-live (`src/laptopfinder/scrape_live.py`)

Fetches listing pages via Firecrawl and writes one `listing-NNN.txt` file per URL to the output directory.

**CLI:**
```bash
.venv/bin/python -m laptopfinder.scrape_live \
    --urls-file data/urls.txt \
    --out-dir data/feed_live/
```

**URL file format** (`data/urls.txt`):
```
# Lines starting with # are ignored
# Blank lines are ignored
https://www.ebay.com.au/itm/123456789012
https://www.gumtree.com.au/s-ad/sydney/...
```

**Requires:** `FIRECRAWL_API_KEY` in `.env`. Exits with code 1 and a clear error if the key is missing.

**Output files:** `data/feed_live/listing-001.txt`, `listing-002.txt`, … Each file begins with a provenance comment `# source: <url>`.

---

## render-matrix (`scripts/render_matrix.py`)

Reads a JSONL shortlist file and writes a sorted Markdown purchase-decision table.

**CLI:**
```bash
.venv/bin/python scripts/render_matrix.py \
    --in data/shortlist_candidates.jsonl \
    --out data/purchase_matrix.md
```

**Makefile:**
```bash
make render-matrix
```

**Input JSONL schema** (one JSON object per line):
```json
{
  "recommended_action": "SHORTLIST|MONITOR|SKIP",
  "llm_index_score": 72,
  "listing_title": "ASUS ROG Zephyrus G14 RTX 4090",
  "price": "AUD 2,800",
  "gpu": "RTX 4090 Laptop",
  "notes": "Clean listing, includes charger"
}
```

**Sort order:** SHORTLIST → MONITOR → SKIP; within group, descending `llm_index_score` (nulls last).

**Example output** (`data/purchase_matrix.md`):
```markdown
# Purchase Decision Matrix

Generated: 2026-07-02T05:47:12

| Rank | Action | Score | Title | GPU | Price | Notes |
|------|--------|-------|-------|-----|-------|-------|
| 1 | SHORTLIST | 72 | ASUS ROG Zephyrus G14 RTX 4090 | RTX 4090 Laptop | AUD 2,800 | Clean listing, includes charger |
| 2 | MONITOR | — | MSI Titan \| parts only? | RTX 3080 Ti | AUD 1,200 | Uncertain condition |
| 3 | SKIP | 31 | Dell XPS 15 | — | AUD 800 | No GPU info |
```

Pipe characters in titles are escaped as `\|`. Missing fields render as `—`.

---

## Makefile Targets Summary

| Target | What it does | Key variable |
|--------|-------------|--------------|
| `inject-config` | Inject SRL values into prompt sentinels | — |
| `scrape-and-live` | Scrape URLs → run `make live` per listing | `FIRECRAWL_URLS` (default: `data/urls.txt`) |
| `render-matrix` | Render shortlist JSONL → Markdown table | — |

`scrape-and-live` purges `data/feed_live/listing-*.txt` before each run to prevent stale re-processing. Each per-listing `make live` failure aborts the loop immediately.

---

## Tests

```bash
make test          # 163 tests
make lint          # ruff check
```

Tests covering this tooling:
- `tests/test_inject_config.py` — 14 tests
- `tests/test_scrape_live.py` — 14 tests
- `tests/test_render_matrix.py` — 15 tests
- `tests/test_prompt_markers.py` — 1 test (sentinel markers present in all prompt files)
