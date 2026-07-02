---
name: pipeline-reference
description: Key terminology, data contracts, and invariants for the laptopfinder pipeline — things not derivable from reading the code
metadata:
  type: reference
---

# Pipeline Reference

## Terminology

| Term | Meaning |
|------|---------|
| Hint/Fact Firewall | Stage 1 may only output `inferred_*` fields. Enforced in `run_stage1`, not the prompt. |
| Grounding Firewall | Stage 2 facts must appear verbatim (word-boundary regex) in `full_listing_text`. Enforced in `run_stage2`. |
| SRL | `config/static_reference_layer.json` — all scoring weights, tier lists, hardware lists. Edit here, not Python. |
| LLM Index Score | VRAM tier (max 60) + GPU generation (max 25) + seller modifier (~±20) − deductions. Informational only. |
| UMA | Unified Memory Architecture — Apple Silicon Max/Ultra and Strix Halo. Uses system RAM; 32GB threshold (`vram_gating_logic.uma_unified_min_gb` in SRL). |
| Low Risk Gate | risk_score + Radeon penalty must be ≤ 3.0 to reach SHORTLIST. |
| eGPU Bundle | Explicit enclosure named in listing; its VRAM governs the decision, not the internal GPU. |

## Data Contracts

- `vram_capacity`: `{semantic_value: number, verbatim_quote: string} | null` — never a flat string
- `missing_information`: 6-boolean object `{gpu, vram, cpu, ram, storage, condition}` — never omit fields
- Stage 2 fixture format: `{handoff_packet, full_listing_text, analysis_output}` at top level
- Stage 1A `inferred_component_category` enum: `["GPU", "CPU", "RAM", "SYSTEM", "OTHER"]`

## Expected Score Ranges (ground-truth sanity check)

| Hardware | Expected llm_index_score |
|----------|--------------------------|
| RTX 4090 16GB laptop | ~75–85 |
| RTX 4080 16GB laptop | ~65–75 |
| Apple Silicon Max/Ultra 64GB+ | ~75–90 (UMA score ceiling removed 2026-06-30 — competes at full 0–100 scale; e.g. Mac Studio 128GB ~89) |

## Decision Priority Order

1. Watch-list GPU → `MONITOR`
2. Risk gate failure (risk > 3.0 or too many missing fields) → `SKIP`
3. UMA platform with system RAM ≥ 32GB → `SHORTLIST`
4. Target GPU/model match, or eGPU bundle, or VRAM ≥ 16GB → `SHORTLIST`
5. Otherwise → `SKIP`
