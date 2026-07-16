# TASKS — laptopfinder
> **NOTICE (2026-07-16):** This document is the sprint archive index + unsprinted backlog + operator reference guides. **Sprint-by-sprint "why", status, and "what shipped" live in `memory/project/sprint.md` — that is the only place sprint task lists are tracked going forward.** `STATUS.md` NEXT_TASK is the single ordered queue of what to work on right now. Do not re-duplicate sprint checklists here; link to the sprint.md section instead.

## Status key: [ ] pending · [~] in progress · [x] done

---

## Sprint Archive Index

All sprints below are complete unless noted. Full Why/Status/Shipped detail lives in `memory/project/sprint.md`.

- Alternative-Silicon Scoring Layer (2026-06-30) — complete
- Evidence-Based Target Pipeline (June 2026) — complete
- AU Market Alignment — Config Update (2026-07-01) — complete
- Secondary Market Topology Report Ingestion (2026-07-01) — complete
- Pipeline Audit (June–July 2026) — complete
- Sprint 2 — Config Injection, Live Scraping, Decision Matrix — complete (`scrape_live.py` since superseded by eBay API)
- Sprint 3 — Prompt Hygiene + eGPU Scoring — complete
- Sprint 4 — Light Fixture Collection (eBay AU + Gumtree, FB minimal) — complete
- Sprint 5 — Firecrawl Live Wiring + batch_decide — CANCELLED (Firecrawl replaced by eBay Developer API); `batch_decide()` remains open, see BACKLOG below
- Sprint 6 — Architecture Penalty + eBay-First End-to-End Validation — Architecture Penalty complete; End-to-End Live Validation open, see Human Runbook below
- eBay AU Active Sniper Setup (2026-07-05) — complete, pending daemon launch sign-off, see Human Runbook below
- Sprint 7 — eBay Browse & Developer API Discovery Expansion — mostly complete, Batch C blocked on human D1 (OAuth scope request)
- Sprint 8 — Hardening Closeout & Daemon Reliability — in progress
- Sprint 9 — PWM Workflow Implementation — queued (see `STATUS.md` NEXT_TASK for the active items)

**Platform priority:** eBay AU is the primary target for all remaining sprints. eBay API runners plus the sniper are primary. Gumtree AU is secondary/opportunistic. Facebook Marketplace is deferred to discovery-only; no full scraping parity.

**Tooling constraint:** No Playwright or Browserbase introduced in this roadmap. Legacy Firecrawl references are historical. Manual batch export via Chrome data-export extensions (Instant Data Scraper / Web Scraper / Data Miner) remains the fallback for eBay search-results batches.

**Output path & routing policy:** `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md` are the only authoritative decision/shortlist output paths — see CLAUDE.md. PWM/Perplexity research artifacts (`data/lf-*.csv`, `reports/lf-*.md`) are supplementary research inputs, not decision outputs, and must never be treated as a substitute for the two canonical files. Routing/scoring logic (`SHORTLIST`/`MONITOR`/`SKIP`, `llm_index_score`) lives solely in `src/laptopfinder/decide.py` + `config/static_reference_layer.json`. Perplexity/PWM outputs and any LLM (Claude, Gemini, Codex) are qualitative research/audit inputs only — they never set or alter a routing decision.

---

## Open Human Runbook Items

Items confirmed still open as of 2026-07-16 (not superseded, not duplicated in STATUS.md NEXT_TASK).

- `[ ]` `[HUMAN]` Sprint 6: `python -m laptopfinder.runners.ebay_hunter` runs to completion on ≥3 eBay AU listings without crash.
- `[ ]` `[HUMAN]` Sprint 6: `data/purchase_matrix.md` renders with ≥1 SHORTLIST candidate and a plausible ranking.
- `[ ]` `[HUMAN]` Sprint 6: `make scan-gaps` produces output (even if zero alerts).
- `[ ]` `[HUMAN/CLAUDE]` eBay Sniper Stage 4: Execute Codex peer review (`scripts/deep_plan_peer_review.sh`), confirm with user, launch daemon (`make start-sniper`), log heartbeat to `docs/ebay_sniper.md`.
- `[ ]` `[IDE/DEV]` Sprint 7: `.venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run` still populates corpus/SHORTLIST/underpriced counts.
- `[ ]` `[HUMAN]` Sprint 7: Run `ebay_hunter --dry-run --no-enrich` (once that flag exists) to verify taxonomy/seller-watch wiring without LLM calls.
- `[ ]` `[HUMAN]` Sprint 7: Run a full `ebay_hunter --dry-run` with enrichment only when explicitly approved.
- `[ ]` `[HUMAN]` Run `gh secret list` and confirm `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` are present in GitHub Secrets.
- `[ ]` `[HUMAN]` Run `make render-matrix` and confirm `data/purchase_matrix.md` contains a ranked SHORTLIST section.

### Sprint 7 backlog (minor, non-blocking)
- `[ ]` Move `PRICE_MIN_AUD`/`PRICE_MAX_AUD` defaults from `ebay_deals.py` env vars into SRL.
- `[ ]` Add `json.JSONDecodeError` guard in `load_feed_cache` for truncated JSONL files.
- `[ ]` `fetch_feed_snapshot` in `ebay_feed_cache.py` assumes a JSON response — eBay Feed API actually delivers gzip TSV. Needs rework once `buy.feed` scope granted.
- `[ ]` Revisit true pairwise architecture penalty only if shortlist-ranking context becomes available.
- `[ ]` Keep Marketplace Insights blocked on D1; FB Marketplace and Gumtree remain discovery-only until a supported manual/agent-assisted workflow is chosen.

### Sprint 8 — Hardening Closeout & Daemon Reliability (active — see sprint.md for shipped items)
- `[ ]` **S8-07:** Add fallback aspect-name lookup via `ebay_taxonomy.py` when hardcoded aspect matches fail. *(src/laptopfinder/runners/legacy/ebay_hunter.py)*
- `[ ]` **S8-08:** Confirm/add `risk_score == 3.0` boundary test. *(verified 2026-07-16: already covered — `test_boundary_exactly_3_0_passes`/`test_boundary_3_1_fails` exist in `tests/test_decide.py`, CLAUDE.md:95 documents it. Close this item.)*
- `[ ]` **S8-09:** Confirm/add "reference only" header comment. *(config/silicon_profiles.yaml — verified 2026-07-16: still missing, genuinely open.)*

---

## BACKLOG (unsprinted)

- `[ ]` Implement `batch_decide()` as documented in CLAUDE.md to enable multi-listing scoring and processing. *(originally scoped under cancelled Sprint 5 — see sprint.md)*

---

## User Testing Guide

> Written for a non-developer operator. Use these walkthroughs to validate each sprint's work. Exact commands are provided; expected output is noted. "Pass" and "fail" criteria are explicit.

---

### eBay AU Testing Walkthrough

**What you need before starting:**
- Project dependencies installed (`uv sync` from the project root)
- A terminal open in the project root (`/Users/okgoogle13/Projects/laptopfinder`)
- `.env` file with valid `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `EBAY_APP_ID`, `EBAY_CERT_ID`

**Step 1 — Run the live eBay API scrape on a short URL list**

Open `data/urls.txt` in a text editor and add 3–5 eBay AU laptop listing URLs (one per line, no blank lines). Then run:

```bash
make benchmark-live
```

Expected terminal output:
```
[LIVE] https://www.ebay.com.au/itm/... → title: "ASUS ROG Zephyrus RTX 3080 16GB..." price: "$1,850.00"
[LIVE] ...
[DONE] 3 records → data/feed_live/benchmark_live.jsonl
```

**Pass:** `benchmark_live.jsonl` exists; open it and confirm `title` and `price_raw` are non-null in each line.
**Fail:** "FIRECRAWL_API_KEY not set" → add the key to your `.env` file. "0 records" → check that URLs in `data/urls.txt` are real active listings.

**Step 4 — Convert to feed text files and run the live pipeline**

```bash
make benchmark-to-feed
```

Then, for each listing file created:

```bash
make live SOURCE=data/feed_live/listing-001.txt
```

Expected terminal output (abbreviated):
```
[Stage 1] Discovered 1 candidate: "ASUS ROG Zephyrus G15 RTX 3080 16GB"
[Stage 2] Analysis complete. GPU: RTX 3080, VRAM: 16GB, Risk: 1.5
[Decision] SHORTLIST — llm_index_score: 72
```

**Pass:** Decision printed without Python traceback; `recommended_action` is SHORTLIST, MONITOR, or SKIP.
**Fail:** `ValueError: grounding firewall` → the LLM fabricated a fact not in the listing text; this is expected occasionally and not a bug. `JSONDecodeError` → the LLM returned malformed JSON; retry once, then file as a fixture-level issue.

**Step 5 — Render the purchase matrix**

Manually assemble any SHORTLIST outputs (the JSON printed to terminal) into `data/shortlist_candidates.jsonl` (one JSON object per line). Then:

```bash
make render-matrix
```

Open `data/purchase_matrix.md` in any text editor or Markdown viewer.

**Pass:** Table renders with ≥1 row; RTX 3080 16GB ranks above RTX 4090 16GB (better VRAM-to-price ratio).
**Fail:** "No candidates found" → `data/shortlist_candidates.jsonl` is empty or malformed. Confirm each line is valid JSON.

**Step 6 — Scan for market gaps**

```bash
make scan-gaps
```

**Pass:** Script runs without crash; prints `[GRADUATION_ALERT]`, `[PRICE_DRIFT_ALERT]`, `[NEW_SIGHTING_ALERT]` lines, or "No alerts" if feed files have no relevant sightings.
**Fail:** `FileNotFoundError` → no feed files in `data/feed_live/`. Run `make benchmark-to-feed` first.

---

### Gumtree AU Testing Walkthrough

**What you need:** A real Gumtree AU laptop listing saved locally (from Sprint 4). Chrome DevTools access.

**Step 1 — Save a Gumtree listing page**

1. Open a Gumtree AU laptop listing URL in Chrome.
2. Right-click the price element on the page and choose "Inspect". In DevTools, note the exact CSS class name on the `<span>` or `<strong>` element that contains the price.
3. Go to File → Save Page As → "Complete" and save to `tests/fixtures/saved_pages/gumtree_laptop_sample.html`.

**Step 2 — Run the extractor against the saved page**

```bash
.venv/bin/python -m laptopfinder.scrape_benchmark \
  --html-file tests/fixtures/saved_pages/gumtree_laptop_sample.html \
  --out /tmp/gumtree_test.jsonl
```

**Pass:** Terminal prints a line with non-null `title` and `price_raw`. Open `/tmp/gumtree_test.jsonl` and confirm.
**Fail:** `price_raw: null` → the `price-amount|listing-price` regex did not match. Note the actual class name from DevTools and report it so `extract_gumtree()` can be patched.

**Step 3 — Run the test suite**

```bash
.venv/bin/python -m pytest tests/test_scrape_benchmark_gumtree.py -v
```

**Pass:** All tests green.
**Fail:** `AssertionError: price_raw is None` → extractor needs patching. `FileNotFoundError` → the saved-page fixture is missing.

---

### Facebook Marketplace Testing Walkthrough

> FB Marketplace is secondary. The goal here is to confirm what fallback path the extractor uses, not to achieve full parity.

**Step 1 — Save an FB Marketplace listing**

1. Open a Facebook Marketplace laptop listing in Chrome while logged into Facebook.
2. File → Save Page As → "Complete". Save to `tests/fixtures/saved_pages/fb_laptop_sample.html`.

**Step 2 — Run the extractor**

```bash
.venv/bin/python -m laptopfinder.scrape_benchmark \
  --html-file tests/fixtures/saved_pages/fb_laptop_sample.html \
  --out /tmp/fb_test.jsonl
```

**Pass:** `full_listing_text` is non-null (even if title is null). Note which fallback path fired.
**Fail:** Both `title` and `full_listing_text` are null — the page was too heavily client-rendered at save time. Try: (a) logging into FB first before saving, (b) using DevTools Network tab to intercept the GraphQL/Relay XHR response and saving that JSON directly to a `fb_*.json` file, then running scrape_benchmark on the JSON file.

---

### Common Failure Modes

**`ValueError: grounding firewall`**
The Stage 2 LLM stated a fact (GPU name, VRAM size) that does not appear verbatim in the listing text. This is correct behaviour — the firewall is working. Retry the listing once (LLM output is non-deterministic). If it fails repeatedly, the listing text is too sparse; mark the listing as insufficient and skip.

**`JSONDecodeError` from Stage 1 or Stage 2 runner**
The LLM returned a response that is not valid JSON. Retry once. If persistent, check whether the prompt was correctly injected (`make inject-config`) and whether the model name in the runner is correct.

**`FIRECRAWL_API_KEY not set`**
The `.env` file is missing the key or was not loaded. Confirm `.env` exists at the project root with `FIRECRAWL_API_KEY=fc-...`. Run `make benchmark-live` again.

**`ERROR: scrape produced no listing files`**
`make scrape-and-live` uses `scrape_live.py`. If no `listing-*.txt` files appear in `data/feed_live/`, the Firecrawl scrape returned empty responses. Check that URLs in `data/urls.txt` are real live listings (not ended/removed). Check `FIRECRAWL_API_KEY` credits.

**`AssertionError: title is None` in tests**
A scraper test fixture is mismatched against the extractor. The saved HTML page uses class names different from the regex in the extractor. Run the extractor manually on the saved HTML, inspect the output, and patch the CSS regex in `scrape_benchmark.py`.

**`KeyError` or `AttributeError` in `decide.py`**
A listing's Stage 2 analysis is missing a field the decision engine expects. Save the failing analysis JSON as a fixture in `tests/fixtures/stage2/` and add a regression test that isolates the missing field. Then patch `decide.py` to handle the null case (never infer — return null or 0).

**`make render-matrix` produces "No candidates"**
`data/shortlist_candidates.jsonl` is empty or malformed. Each line must be a single valid JSON object (the full decision dict printed to terminal). Confirm the file has no trailing commas or blank lines.

**GPU appearing in `[NEW_SIGHTING_ALERT]` from `make scan-gaps`**
A GPU was seen in feed files but is absent from both `target_gpus` and `watch_list` in `config/static_reference_layer.json`. Evaluate the hardware against the current market topology and add it to the appropriate list in the SRL if warranted. Run `make test` after any SRL change.
