---
name: project-context
description: laptopfinder pipeline architecture, terminology, and key invariants
metadata:
  type: project
---

# laptopfinder — Project Context

**Goal:** Evaluate Australian used-hardware listings (eBay AU, FB Marketplace, Gumtree) to find high-VRAM machines suitable for local LLM inference. Outputs SHORTLIST / MONITOR / SKIP with a Local LLM Index Score (0–100).

## Pipeline

```
raw marketplace text
  → Stage 1 (comet.py / Gemini 2.5 Pro)   — discovery, inferred_* hints only
  → Stage 1A handoff packet                — human/agent assembles selected candidate
  → Stage 2 (aistudio.py / Gemini)         — analysis, promotes hints to facts
  → decide.py                              — SHORTLIST / MONITOR / SKIP + score
```

## Key Terminology

| Term | Meaning |
|------|---------|
| Hint/Fact Firewall | Stage 1 output may only carry `inferred_*` fields. Enforced in Python (`run_stage1`), not the prompt. |
| Grounding Firewall | Stage 2 facts must appear verbatim (word-boundary regex) in `full_listing_text`. Enforced in `run_stage2`. |
| SRL | `config/static_reference_layer.json` — all scoring weights, tier lists, hardware lists. Change here, not in Python. |
| LLM Index Score | VRAM tier (max 60) + GPU generation (max 25) + seller modifier (~±20) − deductions. Informational only. |
| UMA | Unified Memory Architecture — Apple Silicon Max/Ultra and Strix Halo. Uses system RAM; 64GB threshold. |
| Low Risk Gate | risk_score + Radeon penalty must be ≤ 3.0 to SHORTLIST. |
| eGPU Bundle | Explicit enclosure named in listing; its VRAM governs decision, not the internal GPU. |

## Invariants
- Missing data → null. Never infer from category or price.
- Schema constraints (JSON Schema min/max) replace Python validation.
- All logic changes verifiable via `make test`.
- Stage 2 fixture format: `{handoff_packet, full_listing_text, analysis_output}`.

## Commands
```bash
make test                                          # run all tests
make decide FIXTURE=tests/fixtures/stage2/foo.json # decision engine
make pipeline STAGE1=... STAGE2=...               # full pipeline
make live SOURCE=feed.txt                         # live run (needs .env)
```
