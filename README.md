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
- **Stage 3 (Decision):** applies the static reference layer rules — capability band classification, unicorn matching, monitor routing, low-risk gate, and exceptional distance override — to produce a `SHORTLIST`, `MONITOR`, or `SKIP` recommendation.

## Canonical rules

1. **Hint-vs-fact firewall:** Stage 1 produces `inferred_hint` fields only; Stage 2 promotes a hint to a fact only when `full_listing_text` explicitly supports it (verified via word-boundary matching). Unverified specifications must map to null.
2. **Strict null handling:** missing or ambiguous values must be null; never infer specs from category or price averages.
3. **Probabilistic risk only:** `risk_score` is a float 0.0–10.0; never a binary scam/safe verdict. Seller quality is a safety gate, not a reward multiplier.
4. **JSON output contract:** the AI Studio runtime returns raw, unwrapped JSON only — no markdown fences, no prose.

## Scoring philosophy

- Listings are evaluated on compute/VRAM suitability, apparent value, and initial legitimacy.
- High-VRAM assets suitable for CUDA-based local LLM inference receive the highest weighting.
- Apple unified-memory systems are a separate optional non-CUDA branch; Mac Mini 32GB is excluded from default unicorn status.

## Travel logic

- Base mode: `pickup_mode = CAR_OK`.
- Standard local radius: ≤120 minutes one-way drive from Northcote, VIC.
- Exceptional radius: ≤150 minutes one-way, only when an exceptional-distance override applies.

## Unicorn and override logic

- Exceptional-distance override = `(category_jump_trigger OR unicorn_hardware_trigger) AND low_risk_gate`.
- **category_jump_trigger:** hardware appears to offer a higher capability band than its pricing tier implies.
- **unicorn_hardware_trigger:** listing matches the curated unicorn hardware dictionary.
- **low_risk_gate:** low `risk_score` AND minimal missing core fields.
- **Aspirational monitor list** (routes to monitoring, not the actionable shortlist): RTX 5080, RTX 5090, GB200, B200.

## Architecture

- **AI Studio prompt** (`prompts/ai_studio_runtime.txt`): runtime system instructions, stage routing (Stage 1 → 1A → 2), non-invention rules, JSON format contracts, and platform context.
- **Static reference layer** (`config/static_reference_layer.json`): capability bands, unicorn dictionary (with VRAM lookups), monitor list, travel rules, and override rules — maintained externally and never embedded into the runtime prompt.
- **Validation harness** (`src/laptopfinder/core.py`): schema validation via JSON Schema, hint/fact firewall enforcement (word-boundary regex), and CLI for fixture-driven validation.
- **Decision engine** (`src/laptopfinder/decide.py`): computes `exceptional_distance_override`, monitor routing, travel eligibility, and `low_risk_gate` from Stage 2 output plus the static reference layer.
- Runtime prompt uses strict nullability: missing data on used marketplaces is expected, not an invitation for the model to fabricate values. AI Studio is a thin extraction-and-analysis runtime, not the source of truth for governance logic.

## Australian market context

- Platforms: eBay AU, Facebook Marketplace, Gumtree.
- Currency: AUD only.
- Pickup origin: Northcote, VIC.

## Repository layout

- `prompts/` — runtime prompt for AI Studio (Stage 1 → 1A → 2), the Comet discovery agent prompt, the Claude Code audit prompt, and the Perplexity deep-research prompt.
- `config/` — static reference layer (capability bands, unicorn dictionary, travel/override rules).
- `src/laptopfinder/core.py` — fixture-driven Stage 1 / Stage 2 validation harness with hint/fact firewall.
- `src/laptopfinder/decide.py` — downstream decision engine (SHORTLIST / MONITOR / SKIP).
- `src/laptopfinder/schemas/` — JSON Schemas for Stage 1 Discovery, Stage 1A Handoff, and Stage 2 Analysis outputs, packaged with the library.
- `tests/` — fixture-driven pytest suite for Stage 1, Stage 2, and decision engine (41 tests).
- `.github/workflows/` — CI checks (JSON validation + pytest suite).
