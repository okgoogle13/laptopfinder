# PWM Local Scripts for Laptopfinder

These workflows run entirely on local files — no Perplexity token is consumed. They are free to run at any time.

---

## 1. `lf-seller-msg-gen` — Seller Negotiation Message Generator

**Purpose**

Generate ready-to-send negotiation and spec-verification messages for SHORTLIST entries, with offer prices anchored to `data/pwm/lf-floor-sync/price_patches.json`.

**Inputs (local files):**
- `output/decisions/latest_decisions.json` — SHORTLIST entries.
- `data/pwm/lf-floor-sync/price_patches.json` — AU price floor patches (from `lf-floor-sync`).

**Outputs:**
- `data/pwm/lf-seller-msg-gen/negotiation_scripts.md` — copy-paste messages per listing.
- `data/pwm/lf-seller-msg-gen/outbound_messages.csv` — listing IDs mapped to message text.

**How to run:** Upload both input files to a Perplexity, Claude, or ChatGPT session with a prompt requesting negotiation message generation. No search grounding needed.

**Done criterion:** Each message includes a VRAM confirmation question and an offer anchored to the price floor.

**Cost:** Free (uses existing Pro session or Claude subscription — no deep/labs tokens).

---

## 2. `lf-spec-gap-check` — Spec Gap & Missing Field Checklist

**Purpose**

Parse `missing_information` flags from SHORTLIST Stage 2 outputs and generate a pre-purchase checklist of questions to ask the seller before buying.

**Inputs (local files):**
- `output/decisions/latest_decisions.json` — SHORTLIST entries (Stage 2 `missing_information` flags).
- `config/static_reference_layer.json` — `vram_gating_logic` for context.

**Outputs:**
- `data/pwm/lf-spec-gap-check/verification_checklist.md` — per-listing bullet points of what to ask the seller.
- `data/pwm/lf-spec-gap-check/spec_gaps.json` — machine-readable list of ambiguities per listing.

**How to run:** Upload both input files to a Perplexity, Claude, or ChatGPT session requesting a spec gap checklist. No search grounding needed.

**Done criterion:** Checklist explicitly flags any listing where VRAM capacity is missing or potentially conflated with system RAM.

**Cost:** Free (uses existing Pro session or Claude subscription — no deep/labs tokens).
