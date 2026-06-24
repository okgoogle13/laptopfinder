# TASKS — laptopfinder final sprint

## Status key: [ ] pending · [~] in progress · [x] done

---

## SPRINT: Benchmark Pipeline

### Scraper / Data Collection
- [ ] Save one real HTML page from each platform (eBay AU, FB Marketplace, Gumtree) using "Save Page As"
- [ ] Run scraper against saved pages: `python -m laptopfinder.scrape_benchmark --html-dir saved_pages/ --out benchmark.jsonl`
- [ ] Inspect `full_listing_text` for each output — confirm the right text is captured, not nav/boilerplate
- [ ] Tune CSS selectors in `scrape_benchmark.py` if extractors miss fields (especially eBay specifics table)
- [ ] Build `benchmark_urls.txt` — curated list of ground-truth listings (high-VRAM, known-good)

### Stage 1 → Stage 2 Fixture Generation
- [ ] For each benchmark listing, run through Stage 1 LLM pass to populate `inferred_*` fields
- [ ] Assemble Stage 1A handoff packets
- [ ] Run Stage 2 LLM pass to produce `analysis_output` for each fixture
- [ ] Save completed fixtures to `tests/fixtures/stage2/` with descriptive filenames

### Decision Engine Validation
- [ ] Run `make decide` against each benchmark fixture
- [ ] Verify all ground-truth listings route to `SHORTLIST`
- [ ] Verify `llm_index_score` is plausible for each listing
- [ ] Document any fixtures that fail or produce unexpected scores

### Test Coverage
- [ ] Add benchmark fixtures to `test_stage2_fixtures.py`
- [ ] Run `make test` — all tests green
- [ ] Add at least one negative fixture per platform (should route SKIP)

---

## BACKLOG

- [ ] Consider Playwright-based scraper for live eBay fetching (eBay blocks simple requests)
- [ ] FB Marketplace: evaluate whether JSON-LD is present in "Save Page As" output or need DevTools intercept
- [ ] Gumtree: verify `price-amount` selector against real page
- [ ] Pipeline integration: wire `scrape_benchmark.py` output directly into `make live`

---

## SPRINT: Pipeline Audit (June 2026)

- [ ] Market Gap Analysis (Deep Research)
  - [ ] Identify high-VRAM GPUs (>= 16GB) appearing on used markets but not in target lists
  - [ ] Identify laptop/workstation models listed on used markets but not in target models
  - [ ] Check watch list graduation for RTX 5080 & RTX 5090 using real used listings evidence
  - [ ] Identify new UMA platforms (>= 64GB) appearing on used markets
- [ ] Spec Comparison of Top 5 Candidates
  - [ ] Compare price-to-VRAM ratios, thermals, and availability depth in a comparative table
- [ ] Pipeline Enhancement Strategies (Design)
  - [ ] Propose target config JSON fragments for `target_gpus`, `target_models`, `radeon_mobile_gpus`, or `conditional_models`
  - [ ] Recalibrate generation scores (Blackwell and RDNA3/ROCm weights)
  - [ ] Identify 5-10 high-value search terms/variants for discovery prompt
  - [ ] Recommend watch list graduations and new watch list entries with conditions
  - [ ] Document 1-3 systematic blind spots and propose fixes

