# TASKS — laptopfinder
## Status key: [ ] pending · [~] in progress · [x] done

---

## COMPLETE: Alternative-Silicon Scoring Layer (2026-06-30)

- [x] A1: Create `config/silicon_profiles.yaml` — paradigm definitions + workload preferences
- [x] A2: Create `config/scoring_weights.yaml` — per-workload weight profiles
- [x] A3: Create `data/hardware_taxonomy.json` — 4 representative hardware entries
- [x] A4: Create `prompts/system_context.md` — agent paradigm-first instructions
- [x] A5: Create `prompts/bias_guard_prompt.md` — bias self-check rubric
- [x] A6: Create `research/alternative_silicon_dossier_june2026.md` — synthesised research
- [x] A7: Modify `decide.py` — Paradigm type, `_classify_paradigm`, `load_scoring_weights`, `score_text_llm_candidate`, `workload` param, UMA ceiling removed
- [x] A8: Modify `config/static_reference_layer.json` — `score_ceiling: null`, policy comments
- [x] A10: Update `tests/test_decide.py` (2 ceiling tests fixed + 3 new classes) + create `tests/test_prompts.py`
- [x] D1: Update `CLAUDE.md` / `AGENTS.md` — architecture + invariants
- [x] D2: Update `memory/project/sprint.md`
- [x] D3: Update `TASKS.md`

**A9 (targets.json integration) blocked on human gate — see Evidence Pipeline below.**

---

## ACTIVE: Evidence-Based Target Pipeline (June 2026)

**Goal:** Collect macOS telemetry, normalize it, and produce `targets.json` via a manual Claude Pro handoff — then feed those targets into the main pipeline.

### Setup (done)
- [x] Create `data/evidence/raw`, `archive`, `aggregated.jsonl`
- [x] Write `src/laptopfinder/schemas/evidence_normalized.schema.json`
- [x] Write `src/laptopfinder/schemas/evidence_targets.schema.json`
- [x] Write `prompts/gemini_evidence_parser.txt`
- [x] Write `prompts/claude_evidence_analyzer.txt`
- [x] Write `src/laptopfinder/runners/evidence_pipeline.py` (prompt generator + handoff generator)
- [x] Add `evidence-run` / `evidence-run-dry` / `evidence-reset` targets to Makefile
- [x] Verify: `py_compile`, `__init__.py`, Makefile grep, dry-run empty-dir all pass

### Collect Evidence (done — 23 logs archived)
- [x] Drop ≥5 telemetry files into `data/evidence/raw`
- [x] Generate Gemini prompts via `make evidence-run`
- [x] Parse all 23 archive logs locally (no API) → saved to `data/evidence/parsed/`
- [x] Run `make evidence-run` to append 23 records to `aggregated.jsonl` and archive parsed JSONs
- [x] Confirm `claude_handoff.txt` was generated in `data/evidence/`

### Claude Pro Handoff (partially done — targets.json is STALE)
- [x] `claude_handoff.txt` generated with corrected `claude_evidence_analyzer.txt` prompt
- [ ] **PENDING: Paste current `data/evidence/claude_handoff.txt` into Claude Pro**
- [ ] **PENDING: Save Claude's JSON response as `data/evidence/targets.json` (current file is pre-correction)**
- [ ] **PENDING: Validate new `targets.json` against `evidence_targets.schema.json`**

### Pipeline improvements (done this session — 2026-06-30)
- [x] Corrected `prompts/gemini_evidence_parser.txt` — added CONTEXT/PAST FAILURES, HARD CONSTRAINTS, QUALITY CHECK, PIPELINE CLARIFICATION, SUMMARY blocks to enforce parse-only role
- [x] Corrected `prompts/claude_evidence_analyzer.txt` — removed banned language (`bottleneck`, `contention`, `under strain`); replaced with neutral observational phrasing
- [x] Added `make evidence-reset` (`--reset` flag): truncates `aggregated.jsonl` + removes `.claude_prompt.hash` sidecar for clean restarts
- [x] Added prompt staleness check: `generate_claude_handoff()` hashes `claude_evidence_analyzer.txt` and warns if the handoff embeds a stale version of the prompt
- [x] Deleted `normalize_archive.py` — one-off workaround; canonical path is `raw/ → make evidence-run → prompts_for_gemini/ → parsed/ → make evidence-run`

### Next: Integrate targets.json into main pipeline
- [ ] Paste `claude_handoff.txt` into Claude Pro; save corrected `targets.json`
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
