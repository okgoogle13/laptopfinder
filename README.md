# laptopfinder

A proactive, two-stage AI assistant designed to discover, filter, and analyze Australian second-hand hardware listings from eBay AU, Facebook Marketplace, and Gumtree, optimized for local LLM inference and general computing.

## Quick Start

```bash
# Validate a Stage 1 discovery fixture
python -m laptopfinder.core stage1 tests/fixtures/stage1/ebay_rtx4090_laptop.json

# Validate a Stage 2 analysis fixture
python -m laptopfinder.core stage2 tests/fixtures/stage2/ebay_facts_grounded.json

# Run Stage 2 validation + decision engine → SHORTLIST / MONITOR / SKIP
python -m laptopfinder.core decide tests/fixtures/stage2/ebay_facts_grounded.json

# Run all tests
make test
```

## Workflow

- **Stage 1 (Discovery):** parses raw marketplace search text, extracts candidate listings, filters anomalies, and generates `inferred_hint` fields only.
- **Stage 1A (Handoff):** preserves discovery context and passes the selected candidate's hints and identifiers to Stage 2.
- **Stage 2 (Analysis):** analyzes full listing text, normalizes explicitly stated facts, applies AU marketplace risk heuristics, and formulates a buyer recommendation.
- **Decision Engine (`decide.py`):** calculates the Local LLM Index Score (0-100), applies hardware-specific heuristics (UMA platforms, eGPU bundles, Radeon ecosystem disclosure), checks the low-risk gate, and produces a `SHORTLIST`, `MONITOR`, or `SKIP` recommendation.

## Canonical rules

1. **Hint-vs-fact firewall:** Stage 1 produces `inferred_hint` fields only; Stage 2 promotes a hint to a fact only when `full_listing_text` explicitly supports it (verified via word-boundary matching). Unverified specifications must map to null.
2. **Strict null handling:** missing or ambiguous values must be null; never infer specs from category or price averages.
3. **Probabilistic risk only:** `risk_score` is a float 0.0–10.0; never a binary scam/safe verdict. Seller quality is a safety gate, not a reward multiplier.
4. **JSON output contract:** the AI Studio runtime returns raw, unwrapped JSON only — no markdown fences, no prose.

## Scoring philosophy (Local LLM Index Score)

Listings are evaluated on a 0-100 scale based on:
- **Capacity (max 60):** VRAM tier (entry/mid/high/extreme) or total system RAM for UMA platforms.
- **GPU Generation (max 25):** Hardware generation score reflects inference generation recency. RDNA3 scores 15 (parity with Ampere-era NVIDIA at equivalent VRAM). Apple Silicon scores 20 (parity with Ada Lovelace), with a separate UMA score ceiling of 75. Unrecognized GPUs score 0 and are not penalized.
- **Target Scoring Hints (informational bonus):** A GPU in `target_gpus` adds +5 points; a chassis in `target_models` adds +3 points. These do not gate routing — any listing with VRAM ≥ 16 GB and risk_score ≤ 3.0 qualifies regardless of list membership.
- **Seller Reward/Risk Modifier (~±20):** Points awarded for established retailers with warranties; penalties for private/unknown sellers and certain platforms.
- **Deductions:** Uncapped point deductions applied for missing fields and high risk scores.

## Heuristics and Overrides

- **UMA Platforms:** Apple Silicon (Max/Ultra) and Strix Halo chips lack discrete VRAM, so their total system RAM capacity is evaluated against a 64GB+ threshold.
- **Radeon Ecosystem Disclosure:** ROCm ecosystem maturity is lower than CUDA for Linux-based LLM inference. This is surfaced as a buyer disclosure flag in Stage 2 output. It is NOT added to risk_score and does not affect the low-risk gate. Radeon listings are evaluated at the same risk_score ≤ 3.0 threshold as all other listings.
- **eGPU Bundles:** If an explicit eGPU enclosure is bundled, the laptop's internal GPU is bypassed, and the eGPU's VRAM dictates the decision.
- **Target Hardware:** `target_gpus` and `target_models` are scoring hint lists. Matching a listed GPU adds +5 points; matching a listed chassis adds +3 points. Neither gates routing — any listing with VRAM ≥ 16 GB and risk_score ≤ 3.0 is eligible for shortlisting regardless of list membership.
- **Watch List (Monitor):** Hardware that was speculative or pre-release at time of listing is routed to `MONITOR`. Each entry carries a `graduation_condition`; once AU used-market availability is confirmed, the entry is promoted to `target_gpus` and no longer routes to MONITOR.
- **Low Risk Gate:** Listings must maintain a risk_score ≤ 3.0 and have minimal missing core fields to be shortlisted. No ecosystem penalty is added to this check.

## Architecture

- **AI Studio prompt** (`prompts/ai_studio_runtime.txt`): runtime system instructions, stage routing (Stage 1 → 1A → 2), non-invention rules, JSON format contracts, and platform context.
- **Static reference layer** (`config/static_reference_layer.json`): capability bands, scoring hint lists (`target_gpus`, `target_models`), watch lists with graduation conditions, UMA chip definitions, LLM index scoring weights, and routing thresholds. `target_gpus` and `target_models` are scoring hints, not routing gates. All shortlist routing is driven by numeric thresholds (VRAM, risk_score, missing_fields). Maintained externally and never embedded into the runtime prompt.
- **Validation harness** (`src/laptopfinder/core.py`): schema validation via JSON Schema, hint/fact firewall enforcement (word-boundary regex), and CLI for fixture-driven validation.
- **Decision engine** (`src/laptopfinder/decide.py`): computes the LLM Index Score, hardware heuristics (UMA, eGPU, Radeon), monitor routing, and the `low_risk_gate` from Stage 2 output plus the static reference layer.
- Runtime prompt uses strict nullability: missing data on used marketplaces is expected, not an invitation for the model to fabricate values. AI Studio is a thin extraction-and-analysis runtime, not the source of truth for governance logic.

## Australian market context

- Platforms: eBay AU, Facebook Marketplace, Gumtree.
- Currency: AUD only.
- Pickup origin: Northcote, VIC.

## Repository layout

- `prompts/` — runtime prompt for AI Studio (Stage 1 → 1A → 2), the Comet discovery agent prompt, the Claude Code audit prompt, and the Perplexity deep-research prompt.
- `config/` — static reference layer (LLM index scores, hardware definitions, watch lists).
- `src/laptopfinder/core.py` — fixture-driven Stage 1 / Stage 2 validation harness with hint/fact firewall and unified CLI.
- `src/laptopfinder/decide.py` — downstream decision engine (SHORTLIST / MONITOR / SKIP).
- `src/laptopfinder/schemas/` — JSON Schemas for Stage 1 Discovery, Stage 1A Handoff, and Stage 2 Analysis outputs, packaged with the library.
- `tests/` — fixture-driven pytest suite for Stage 1, Stage 2, and decision engine.
- `.github/workflows/` — CI checks (JSON validation + pytest suite).
