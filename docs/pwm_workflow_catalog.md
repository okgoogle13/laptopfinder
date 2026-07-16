# PWM Workflow Catalog — Laptopfinder Sprint

This catalog defines all current `pwm` workflows used in the laptopfinder project.
Each workflow is quota-aware and respects the run order:

eBay runners → local pipeline → Perplexity (Deep / Labs) → optional Gemini.

## Conventions

- `TYPE`: Deep-only, Labs-only, or Deep+Labs.
- `DATA SOURCE`: eBay AU scripts, other retailers, local cache.
- `TOOLS`: Perplexity MCP modes (Sonar, Pro, Deep Research, Labs create-files/app),
          local scripts, optional Gemini API.
- `DONE`: Clear artefacts in `data/`, `reports/`, `config/`, or app views.

---

## 1. Core Research & Pricing Workflows

### pwm lf-floor-sync
- TYPE: Deep-only
- GOAL: Maintain an up-to-date floor/ceiling pricing model for target GPU/VRAM tiers.
- DATA SOURCE:
  - Latest `make_hunt` eBay AU results (JSON/CSV).
  - Local cache of past hunts.
- TOOLS:
  - Perplexity Deep Research (1 run) on current eBay price spread for key SKUs.
  - Sonar quick checks for anomalous outliers.
- STEPS:
  1. Run `make_hunt CONFIG=lf-floor` to fetch current listings for target tiers.
  2. Normalize results into `data/lf-floor-listings.csv` (local script).
  3. Call Perplexity Deep Research with the CSV + your existing floor model assumptions.
  4. Ask Perplexity to:
     - Identify current realistic floor and ceiling per GPU/VRAM tier.
     - Flag “too-good-to-be-true” deals and likely junk tiers.
  5. Save a markdown report to `reports/lf-floor-sync.md` and a JSON model to `config/lf-floor-model.json`.
- DONE:
  - `reports/lf-floor-sync.md` exists with updated reasoning.
  - `config/lf-floor-model.json` updated with new floor/ceiling per tier.

---

### pwm lf-price-baseline
- TYPE: Deep-only
- GOAL: Establish baseline “fair price” bands per candidate laptop type (gaming, workstation, etc.).
- DATA SOURCE:
  - `make_hunt` outputs scoped to candidate tiers.
  - Historical shortlist and purchase decisions.
- TOOLS:
  - Perplexity Deep Research (1 run) on cross-section of listings + historical data.
- STEPS:
  1. Run `make_hunt CONFIG=lf-candidates` to gather all candidate listings.
  2. Merge with historical shortlist and prior purchases into `data/lf-price-baseline.csv`.
  3. Call Deep Research with the CSV and your current floor model.
  4. Ask Perplexity to:
     - Derive baseline price ranges per archetype.
     - Highlight where current listings deviate positively/negatively.
  5. Save `reports/lf-price-baseline.md` + `config/lf-price-bands.json`.
- DONE:
  - Baseline bands per archetype defined in JSON.
  - Report explains trade-offs for paying above/below baseline.

---

## 2. Decision & Buy-Jury Workflows

### pwm lf-buy-jury
- TYPE: Deep+Labs
- GOAL: Run a “jury” over 3–7 finalists to decide which to buy now versus monitor.
- DATA SOURCE:
  - Shortlist CSV (`data/lf-shortlist.csv`) from sniper/shortlist scripts.
  - Floor/price models from prior workflows.
- TOOLS:
  - Perplexity Deep Research (1 run) for multi-factor analysis.
  - Labs create-files to generate a structured decision matrix.
- STEPS:
  1. Ensure `data/lf-shortlist.csv` is current from shortlist/sniper runs.
  2. Call Deep Research with:
     - Shortlist CSV.
     - Floor and baseline price JSON models.
     - Your VRAM/workload requirements.
  3. Ask Perplexity to:
     - Score each candidate on VRAM fit, total cost of ownership, and risk.
     - Explicitly recommend “Buy Now”, “Monitor”, or “Reject”.
  4. Use Labs create-files to build `reports/lf-buy-jury.md` and a `data/lf-buy-jury-matrix.csv`.
- DONE:
  - One clear “buy now” recommendation, with alternatives ranked and justification.
  - Decision matrix CSV exists and can be reused in later sprints.

---

### pwm lf-paradigm-debate
- TYPE: Deep-only
- GOAL: Run a high-level debate about hardware paradigm: desktop vs laptop, single big GPU vs many small, etc., informed by current market.
- DATA SOURCE:
  - Aggregated research reports in `reports/`.
  - Any latest retailer/eBay snapshots.
- TOOLS:
  - Perplexity Deep Research (1 run) with structured debate prompt.
- STEPS:
  1. Collect existing PWM reports (floor, baseline, jury) plus latest pricing snapshots.
  2. Call Deep Research with a debate-style prompt (pros/cons, long-term strategy).
  3. Ask Perplexity to:
     - Argue both sides of key paradigm choices.
     - Update your “default stance” for upcoming sprints.
  4. Save `reports/lf-paradigm-debate.md`.
- DONE:
  - Updated paradigm stance documented.
  - Future PWM workflows can cite this as “current doctrine”.

---

## 3. Sniper, Shortlist & Scrutiny Workflows

### pwm lf-sniper-shortlist
- TYPE: Deep-only (optionally Labs for dashboard)
- GOAL: Turn raw eBay hunts into a sniper-ready shortlist plus risk notes.
- DATA SOURCE:
  - `make_hunt` outputs for current sprint.
- TOOLS:
  - Perplexity Pro Search for quick weeding.
  - Deep Research (optional) for complex edge cases.
- STEPS:
  1. Run `make_hunt CONFIG=lf-sniper` to collect all candidate listings.
  2. Apply local filters (price caps, VRAM requirements) to generate `data/lf-sniper-raw.csv`.
  3. Use Perplexity Pro Search to:
     - Flag obvious junk and scams.
     - Pull spec details for ambiguous listings.
  4. Optionally call Deep Research when a listing needs multi-source validation.
  5. Produce `data/lf-shortlist.csv` plus `reports/lf-sniper-shortlist.md` with commentary.
- DONE:
  - Shortlist CSV ready for buy-jury and Labs dashboards.
  - Commentary report exists for reference during negotiations.

---

### pwm lf-seller-scrutiny
- TYPE: Deep-only
- GOAL: Evaluate seller trustworthiness and listing consistency for shortlisted items.
- DATA SOURCE:
  - Shortlist CSV, seller profile data from eBay API or scraped pages.
- TOOLS:
  - Perplexity Deep Research for seller risk profiling.
- STEPS:
  1. Enrich `data/lf-shortlist.csv` with seller metadata (feedback, history, etc.).
  2. Call Deep Research with enriched shortlist.
  3. Ask Perplexity to:
     - Score seller risk.
     - Identify inconsistent listings or spec misrepresentation patterns.
  4. Save `reports/lf-seller-scrutiny.md` plus `data/lf-seller-risk.json`.
- DONE:
  - Clear risk scores per seller.
  - Notes usable in message drafting and buy-jury decisions.

---

## 4. Governance & Meta Workflows

> **Dropped 2026-07-16:** Labs dashboard/app-scaffold workflows (`lf-floor-sync-labs`, `lf-shortlist-dashboard-labs`, `lf-retailer-sweep-labs`, `lf-seller-message-drafter-labs`) were removed from this catalog — out of scope per CLAUDE.md's canonical output policy (`output/decisions/latest_decisions.json` + `output/shortlist/latest_shortlist.md` only, no dashboards/visualisers). See `TASKS.md` Sprint 9 backlog.

### pwm lf-status-rollup
- TYPE: Deep-only (light)
- GOAL: Periodically summarize sprint status across all PWM outputs.
- DATA SOURCE:
  - Reports and JSONs from all above workflows.
- TOOLS:
  - Perplexity Pro Search or Deep Research (depending on scope).
- STEPS:
  1. Gather latest artefacts (reports, dashboards, JSON models).
  2. Call Pro or Deep to:
     - Summarize current stance: what floor/ceiling is, current shortlist, paradigm decisions.
     - Highlight TODO PWM commands for next burst.
  3. Update `STATUS.md` at repo root.
- DONE:
  - STATUS.md accurately reflects current sprint state.
  - Only heavier PWM commands run when explicitly needed.

---

## 5. Run Order & Quota Rules (Meta)

- Run order for all workflows:
  - eBay runners → local filters & caches → Perplexity (Sonar/Pro/Deep) → Gemini API (optional).
- Quota usage:
  - Deep Research: reserved for floor/baseline, buy-jury, paradigm-debate, serious seller scrutiny.
- Never trigger Deep Research autonomously; every Deep call is tied to a named PWM workflow and a sprint decision.
