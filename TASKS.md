# TASKS — laptopfinder

## Status key: [ ] pending · [~] in progress · [x] done

---

## ACTIVE: Evidence-Based Target Pipeline (June 2026)

**Goal:** Collect macOS telemetry, normalize it via Gemini, and produce `targets.json` via a manual Claude Pro handoff — then feed those targets into the main pipeline.

### Setup (done this session)
- [x] Create `data/evidence/raw`, `archive`, `aggregated.jsonl`
- [x] Write `src/laptopfinder/schemas/evidence_normalized.schema.json`
- [x] Write `src/laptopfinder/schemas/evidence_targets.schema.json`
- [x] Write `prompts/gemini_evidence_parser.txt`
- [x] Write `prompts/claude_evidence_analyzer.txt`
- [x] Write `src/laptopfinder/runners/evidence_pipeline.py` (Gemini stub + handoff generator)
- [x] Add `evidence-run` / `evidence-run-dry` targets to Makefile
- [x] Verify: `py_compile`, `__init__.py`, Makefile grep, dry-run empty-dir all pass

### Next: Collect Evidence (manual)
- [ ] Drop ≥5 telemetry files (screenshots or log exports from Activity Monitor) into `data/evidence/raw`
- [ ] Run `make evidence-run` to normalize and append to `aggregated.jsonl`
- [ ] Confirm `claude_handoff.txt` was generated in `data/evidence/`

### Next: Claude Pro Handoff (manual)
- [ ] Open Claude Pro, paste contents of `data/evidence/claude_handoff.txt`
- [ ] Save Claude's JSON response as `data/evidence/targets.json`
- [ ] Validate `targets.json` against `evidence_targets.schema.json`

### Next: Wire Gemini Parser (code)
- [ ] Replace stub in `run_gemini_parser()` with real `google-genai` call using `gemini_evidence_parser.txt`
- [ ] Test against a real screenshot: confirm all telemetry fields populate or null correctly
- [ ] Add `uncertainty_flags` assertions in a new test fixture

### Next: Integrate targets.json into main pipeline
- [ ] Load `targets.json` spec ranges into `config/static_reference_layer.json` or as a runtime override
- [ ] Confirm `make test` stays green after integration

---

## ACTIVE: Pipeline Audit (June 2026)

**Goal:** Validate and expand the pipeline's hardware coverage based on what's actually appearing on AU used markets.

### Market Gap Analysis
- [ ] Identify high-VRAM GPUs (≥16GB) appearing on used markets but absent from target lists
- [ ] Identify laptop/workstation models on used markets but absent from target models
- [ ] Check watch list graduation for RTX 5080 & 5090 using real used-listing evidence
- [ ] Identify new UMA platforms (≥64GB) appearing on used markets

### Spec Comparison
- [ ] Compare top 5 candidates: price-to-VRAM ratio, thermals, availability depth (table)

### Pipeline Enhancements
- [ ] Propose target config JSON fragments for `target_gpus`, `target_models`, `radeon_mobile_gpus`, `conditional_models`
- [ ] Recalibrate generation scores (Blackwell and RDNA3/ROCm weights)
- [ ] Identify 5–10 high-value search terms/variants for the discovery prompt
- [ ] Recommend watch list graduations and new watch list entries with conditions
- [ ] Document 1–3 systematic blind spots and propose fixes

---

## BACKLOG

- [ ] Playwright-based scraper for live eBay fetching (eBay blocks simple requests)
- [ ] FB Marketplace: evaluate JSON-LD availability in "Save Page As" vs DevTools intercept
- [ ] Gumtree: verify `price-amount` selector against a real saved page
- [ ] Wire `scrape_benchmark.py` output directly into `make live`
