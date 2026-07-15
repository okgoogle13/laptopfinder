# PWM Labs Workflow Design Spec
**Date:** 2026-07-16  
**Session:** Gemini 3.1 Pro · Deep Think (High)

> **NOTE — Partially superseded.** `lf-retail-compare` and `lf-grays-auction-assessor` have been reclassified as Deep Research (both use `search_grounding: true`) and now live in `docs/pwm_deep_research.md` §§11–12. The remaining 5 workflows feed `docs/pwm_labs_workflows.md` §§6–8 and `docs/pwm_local_scripts.md`. Do not add `lf-retail-compare` or `lf-grays-auction-assessor` to `docs/pwm_labs_workflows.md`.

---

## Context

The Perplexity Workflow Manager (PWM) serves the laptopfinder eBay AU sniper pipeline. This spec adds 7 new PWM Labs workflows that sit on top of the Opus/Deep Research outputs and the core sniper outputs, providing the action layer: triage, evaluation, messaging, retail comparison, negotiation, and alert wiring.

---

## 1. URL Rubric

```yaml
name: lf-url-rubric-labs
pwm_command: pwm lf-url-rubric --labs

Tier: Labs
Purpose: |
  Instantly scores a pasted eBay AU or AU retail URL against the static reference layer,
  returning a SHORTLIST or SKIP verdict with spec-gap and risk reasoning.

Gap it fills: |
  URL-based scoring for ad-hoc finds. Eliminates the need to wait for the next batch runner
  sweep when evaluating a single listing discovered outside the normal pipeline.

Relationship_to_opus: |
  Consumes config/static_reference_layer.json (vram_gating_logic, risk_gate,
  data_integrity.exclusion_regex) established and maintained by Opus workflows
  (lf-floor-sync, lf-exclusion-tune). Sits downstream of lf-floor-sync by optionally
  comparing the listing's VRAM tier and risk profile against the current SRL gates.

Sprint_role: evaluation

Inputs:
  repo_files:
    - config/static_reference_layer.json (vram_gating_logic, risk_gate, data_integrity.exclusion_regex)
  attachment_method:
    antigravity: Reads config from the local repo; URL HTML/body is obtained separately and
                 passed into the Labs app when needed.
    labs: Upload config file into the Perplexity Labs project; paste the URL and optionally
          page HTML or text into the app for evaluation.
    chatgpt: Upload config and url_eval.json into a ChatGPT laptopfinder project to maintain
             a ledger of evaluated URLs.
  search_grounding: false

Outputs:
  reports:
    - url_verdict.md (Markdown report: extracted specs, SHORTLIST/SKIP verdict,
      spec-gap flags, and SRL rule/risk rationale)
  data:
    - url_eval.json (JSON payload: {url, gpu_guess, vram_gb, host_ram_gb,
      passes_vram_gate, passes_risk_gate, spec_gaps: [...], verdict: SHORTLIST|SKIP})
  charts: []
  app: |
    Interactive UI accepting a URL input (and optionally pasted HTML), displaying extracted
    GPU/VRAM/RAM/price fields, showing which SRL gates passed or failed, and returning
    a SHORTLIST/SKIP verdict with spec-gap highlights.

Human_interaction:
  in_labs: |
    Paste a URL (and optionally page content), review extracted specs and gate status,
    and decide whether to contact the seller immediately based on SHORTLIST/SKIP and spec gaps.
  in_antigravity: |
    Use a CLI wrapper (pwm lf-url-rubric --labs <url>) to generate url_verdict.md and url_eval.json,
    then inspect these files or surface key fields in terminal output.
  in_chatgpt: |
    Upload url_eval.json into a ChatGPT laptopfinder project to log accepted/rejected URLs,
    run aggregate analysis, or generate follow-up scripts/messages based on the evaluation ledger.

Budget_justification: |
  Requires an interactive_UI for URL input and inspection, plus code_generation/HTML parsing to
  extract specs from arbitrary listing content, and a chatgpt_export_pipeline via url_eval.json
  so downstream ChatGPT Projects can consume structured evaluations.

Done_criterion: |
  App accepts a URL, extracts specs, and:
  - Outputs SKIP when the listing fails any SRL risk or VRAM gate or has critical spec gaps.
  - Outputs SHORTLIST only when required gates pass and no critical spec gaps remain.
```

## 2. Seller Message Generator

```yaml
name: lf-seller-msg-gen
pwm_command: pwm lf-seller-msg-gen

Tier: Labs
Purpose: |
  Generates ready-to-send negotiation and spec-verification messages for shortlisted candidates.

Gap it fills: |
  Shortlist → seller messaging. Bridges the gap between automated discovery and human negotiation.

Relationship_to_opus: |
  Reads output/decisions/latest_decisions.json SHORTLIST entries produced by core runners.
  Consumes data/pwm/lf-floor-sync/price_patches.json established by Opus workflow 
  lf-floor-sync to anchor offer prices.

Sprint_role: negotiation

Inputs:
  repo_files:
    - output/decisions/latest_decisions.json (SHORTLIST entries only)
    - data/pwm/lf-floor-sync/price_patches.json (AU price floor patches)
  attachment_method:
    antigravity: Reads directly from local output and data dirs.
    labs: Upload both JSON files.
    chatgpt: Upload both JSON files.
  search_grounding: false

Outputs:
  reports:
    - negotiation_scripts.md (Compiled list of messages ready to copy-paste)
  data:
    - outbound_messages.csv (Listing IDs mapped to generated message text for ChatGPT tracking)
  charts: []
  app: |
    Dashboard displaying SHORTLIST items with a "Generate Message" button that injects the offer band.

Human_interaction:
  in_labs: |
    Review SHORTLIST items, click to generate a message, and copy-paste it to eBay.
  in_antigravity: |
    Produces markdown list of messages.
  in_chatgpt: |
    Upload CSV to track which sellers have been contacted and at what offer price.

Budget_justification: |
  Requires interactive_UI for message review and chatgpt_export_pipeline for outreach tracking.

Done_criterion: |
  Message generation includes a VRAM confirmation question and an offer anchored to price_patches.json.
```

## 3. Triage Dashboard

```yaml
name: lf-triage-dash
pwm_command: pwm lf-triage-dash

Tier: Labs
Purpose: |
  Provides an interactive dashboard to filter, rank, and export SHORTLIST entries based on sprint fitness and market floors.

Gap it fills: |
  Triage & negotiation dashboard. Replaces static markdown matrices with sortable, filterable views.

Relationship_to_opus: |
  Reads output/decisions/latest_decisions.json and output/shortlist/purchase_matrix.md from core runners.
  Consumes data/pwm/lf-floor-sync/price_patches.json established by Opus workflow lf-floor-sync for offer bands.

Sprint_role: triage

Inputs:
  repo_files:
    - output/decisions/latest_decisions.json (SHORTLIST entries)
    - output/shortlist/purchase_matrix.md (ranking context)
    - data/pwm/lf-floor-sync/price_patches.json (AU price floor patches)
  attachment_method:
    antigravity: Local file read.
    labs: File uploads.
    chatgpt: File uploads.
  search_grounding: false

Outputs:
  reports:
    - triage_snapshot.md (Filtered view of top 3 immediate action items)
  data:
    - triage_export.json (Filtered and sorted shortlist array for ChatGPT)
  charts:
    - offer_bands.png (Scatter plot of shortlisted prices vs price floors per GPU tier)
  app: |
    Interactive table with sortable columns for risk score, LLM index score, and price delta vs floor.

Human_interaction:
  in_labs: |
    Filter out listings with high risk scores or prices too far above floor, exporting the refined list.
  in_antigravity: |
    Run command to generate PNG charts and filtered JSON.
  in_chatgpt: |
    Load triage_export.json to instruct ChatGPT to focus only on the top 3 items for deep analysis.

Budget_justification: |
  Requires interactive_UI for filtering, charts for visual offer bands, and chatgpt_export_pipeline.

Done_criterion: |
  Dashboard successfully loads all SHORTLIST entries, allowing filtering by risk score and sorting by price delta.
```

## 4. Retail Compare

```yaml
name: lf-retail-compare
pwm_command: pwm lf-retail-compare --labs

Tier: Labs
Purpose: |
  Discovers current AU retail prices for target GPUs and compares them to used-market price floors.

Gap it fills: |
  Retail extension beyond eBay AU. Contextualises used eBay prices against brand-new retail warranties.

Relationship_to_opus: |
  Consumes config/static_reference_layer.json (target_gpus) to guide retail search.
  Consumes data/pwm/lf-floor-sync/price_patches.json established by Opus workflow
  lf-floor-sync to calculate the used-vs-new delta.

Sprint_role: retail_comparison

Inputs:
  repo_files:
    - config/static_reference_layer.json (target_gpus)
    - data/pwm/lf-floor-sync/price_patches.json (AU price floor patches)
  attachment_method:
    antigravity: Local file read.
    labs: File uploads.
    chatgpt: File uploads.
  search_grounding: true

Outputs:
  reports:
    - retail_vs_used.md (Buy-vs-wait verdicts per GPU tier based on retail premium)
  data:
    - retail_skus.csv (Scraped retail pricing mapped to GPU tiers for ChatGPT)
  charts:
    - retail_premium.png (Bar chart showing the price gap between used floors and retail new)
  app: |
    View comparing JB Hi-Fi/Scorptec prices to eBay floors, with a "Retail Premium %" column.

Human_interaction:
  in_labs: |
    Run search grounding to fetch retail prices, review the premium, and decide if a used eBay listing is actually a good deal.
  in_antigravity: |
    Runs search (if supported) or prompts for manual retail price entry.
  in_chatgpt: |
    Upload retail_skus.csv so ChatGPT knows current retail alternatives during negotiation planning.

Budget_justification: |
  Requires live_search to fetch JB/Scorptec prices and charts to visualize the new-vs-used premium.

Done_criterion: |
  Outputs a CSV containing at least one retail price point for ≥3 target GPUs from AU retailers.
```

## 5. Spec Gap Checklist

```yaml
name: lf-spec-gap-check
pwm_command: pwm lf-spec-gap-check

Tier: Labs
Purpose: |
  Parses listing text to identify missing or ambiguous LLM-critical specs and generates a pre-purchase checklist.

Gap it fills: |
  Spec gap detector & checklist. Ensures human doesn't buy a listing that bypassed automated filters due to ambiguous text.

Relationship_to_opus: |
  Operates on output/decisions/latest_decisions.json SHORTLIST entries,
  verifying the missing_information flags output by Stage 2 grounding.

Sprint_role: spec_verification

Inputs:
  repo_files:
    - output/decisions/latest_decisions.json (SHORTLIST entries)
    - config/static_reference_layer.json (vram_gating_logic)
  attachment_method:
    antigravity: Local file read.
    labs: File uploads.
    chatgpt: File uploads.
  search_grounding: false

Outputs:
  reports:
    - verification_checklist.md (Per-listing bullet points of what to ask the seller)
  data:
    - spec_gaps.json (Machine-readable list of ambiguities per listing for ChatGPT)
  charts: []
  app: |
    UI displaying the listing text alongside highlighted areas of ambiguity (e.g. "16GB RAM" vs VRAM).

Human_interaction:
  in_labs: |
    Review the highlighted listing text and copy the generated checklist to use in eBay messages.
  in_antigravity: |
    CLI output of the markdown checklist.
  in_chatgpt: |
    Upload spec_gaps.json so ChatGPT can draft targeted follow-up questions for the seller.

Budget_justification: |
  Requires interactive_UI to highlight text ambiguities and chatgpt_export_pipeline for drafting questions.

Done_criterion: |
  Generates a checklist that explicitly flags if VRAM capacity is missing or conflated with system RAM.
```

## 6. Alert Scaffold

```yaml
name: lf-alert-scaffold
pwm_command: pwm lf-alert-scaffold

Tier: Labs
Purpose: |
  Generates a starter Python script with CSS selectors to monitor non-eBay AU retail and outlet endpoints.

Gap it fills: |
  Alert setup & automation scaffold. Expands automated discovery beyond eBay without duplicating ebay_sniper.py.

Relationship_to_opus: |
  Complements runners/ebay_sniper.py by covering Grays, Gumtree, and Dell Outlet.
  Adheres to target_gpus from config/static_reference_layer.json.

Sprint_role: alert_wiring

Inputs:
  repo_files:
    - config/static_reference_layer.json (target_gpus)
  attachment_method:
    antigravity: Local file read.
    labs: File uploads.
    chatgpt: File uploads.
  search_grounding: true

Outputs:
  reports:
    - endpoint_map.md (Documentation of the endpoints and selectors discovered via search grounding)
  data:
    - alert_config.json (JSON schema defining the endpoints for ChatGPT to modify)
  charts: []
  app: |
    Code editor view showing the generated watcher.py, allowing manual tweaks before export.

Human_interaction:
  in_labs: |
    Use search grounding to verify endpoint DOM structure, review the generated code, and copy it.
  in_antigravity: |
    Writes the generated watcher.py to the local filesystem.
  in_chatgpt: |
    Upload alert_config.json to have ChatGPT adjust selectors if the retail site structure changes later.

Budget_justification: |
  Requires live_search to verify DOM/endpoints and code_generation to emit watcher.py.

Done_criterion: |
  watcher.py is generated and contains valid selector functions for ≥3 non-eBay AU endpoints.
```

## 7. Grays Auction Assessor

```yaml
name: lf-grays-auction-assessor
pwm_command: pwm lf-grays-auction-assessor

Tier: Labs
Purpose: |
  Assesses a Grays online auction URL, calculates maximum bid based on buyer's premium and eBay price floors, and scores it.

Gap it fills: |
  Retail extension beyond eBay AU / URL scoring. Grays auctions require factoring in buyer's premiums (often +20%) which eBay floors don't have.

Relationship_to_opus: |
  Consumes data/pwm/lf-floor-sync/price_patches.json (established by Opus workflow lf-floor-sync)
  to anchor the max bid. Uses config/static_reference_layer.json for VRAM gating.

Sprint_role: negotiation

Inputs:
  repo_files:
    - config/static_reference_layer.json (vram_gating_logic)
    - data/pwm/lf-floor-sync/price_patches.json (AU price floor patches)
  attachment_method:
    antigravity: Local file read.
    labs: File uploads.
    chatgpt: File uploads.
  search_grounding: true

Outputs:
  reports:
    - grays_bid_strategy.md (Calculated max bid including premium, compared to eBay floor)
  data:
    - grays_auction_eval.csv (Auction details, premium %, and max bid for ChatGPT)
  charts: []
  app: |
    Calculator UI where user pastes a Grays URL, views the extracted specs, and sees a max bid slider adjusting for premium.

Human_interaction:
  in_labs: |
    Paste Grays URL, use search grounding to confirm current buyer's premium %, and get a hard max-bid limit.
  in_antigravity: |
    Command line tool taking a URL and outputting max bid.
  in_chatgpt: |
    Upload the CSV to have ChatGPT monitor auction end times and track bid limits.

Budget_justification: |
  Requires live_search to verify Grays current buyer's premium percentage and interactive_UI for the bid calculator.

Done_criterion: |
  Outputs a maximum bid figure that explicitly subtracts the buyer's premium from the price_patches.json floor.
```
