---
name: pipeline-audit-sprint
description: Active sprint — June 2026 pipeline audit to expand hardware coverage based on real AU market data
metadata:
  type: project
---

# Pipeline Audit — June 2026

**Why:** Benchmark sprint validated the engine against known-good fixtures. This sprint expands target lists and scoring weights based on what's actually appearing on AU used markets.

**Status:** In progress. See TASKS.md for item-level tracking.

## Phases

### 1. Market Gap Analysis (Deep Research)
Use Perplexity or manual eBay/Gumtree/FB searches to surface:
- High-VRAM GPUs (≥16GB) not yet in `target_gpus` (e.g. RTX 4070 Ti SUPER variants, Radeon W7900M)
- Laptop/workstation models not in `target_models` but appearing frequently
- Watch list graduation candidates: RTX 5080/5090 (check if used units are actually listed at real AU prices)
- New UMA platforms: any Apple Silicon Max/Ultra configs ≥64GB or AMD Strix Halo laptops

### 2. Spec Comparison
Build a comparative table of the top 5 shortlisted candidates:
- Price-to-VRAM ratio (AUD/GB)
- Thermals (TDP, cooling solution notes)
- Availability depth (# of listings found)

### 3. Pipeline Enhancements
Propose concrete edits to `config/static_reference_layer.json`:
- New entries for `target_gpus`, `target_models`, `radeon_mobile_gpus`, `conditional_models`
- Updated generation scores for Blackwell (RTX 50xx) and RDNA3 (ROCm penalty calibration)
- 5–10 additional discovery prompt search terms
- Watch list graduation conditions and new watch list entries
- 1–3 documented blind spots with proposed fixes

## Definition of Done
- [ ] Config JSON fragments drafted and reviewed
- [ ] `make test` still green after any SRL changes
- [ ] Market gap findings documented in `deep_research_output.md`

---

# Evidence-Based Target Pipeline — June 2026

**Why:** Current target lists are static. This pipeline derives provisional hardware spec ranges from real observed macOS workload telemetry, then hands off to Claude Pro for inference. Prevents the decision engine from chasing the wrong VRAM tier.

**Status:** Repo scaffolding complete (2026-06-28). Awaiting telemetry collection and manual Claude Pro handoff.

## Architecture
1. Drop telemetry files → `data/evidence/raw`
2. `make evidence-run` → normalizes via Gemini stub, appends to `aggregated.jsonl`, archives files
3. At ≥5 records → generates `data/evidence/claude_handoff.txt`
4. Human pastes handoff into Claude Pro, saves response as `data/evidence/targets.json`
5. `targets.json` feeds into `static_reference_layer.json` or a runtime override

## Immediate Next Steps
1. Collect ≥5 telemetry screenshots/logs → drop into `data/evidence/raw`
2. Run `make evidence-run` and confirm `claude_handoff.txt` is generated
3. Complete Claude Pro handoff, save `targets.json`
4. Wire real Gemini API call into `run_gemini_parser()` (replace stub)
5. Integrate `targets.json` spec ranges into main pipeline config

## Definition of Done
- [ ] `targets.json` validated against `evidence_targets.schema.json`
- [ ] Real Gemini parser wired and tested against a screenshot
- [ ] Spec ranges reflected in `static_reference_layer.json`
- [ ] `make test` still green
