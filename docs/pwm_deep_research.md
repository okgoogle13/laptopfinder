# Perplexity `pwm` Deep Research Workflows for Laptopfinder

This document describes Deep Research–based workflows integrated with the `pwm` CLI and Laptopfinder procurement pipeline. Deep Research is used for exhaustive market, technical, and vendor analysis, producing markdown reports and structured JSON artefacts for offline scoring. [web:17][web:20][web:26][web:28]

---

## 1. Goals & Constraints

- Shift high‑value research into Perplexity Deep Research runs (20+ tokens available). [web:17][web:20]
- Target AU second‑hand and refurbished laptops (eBay AU, Dell Outlet AU, Lenovo Clearance AU, Grays Online, Reebelo, local refurb shops).
- Avoid backend APIs and paid dev credits; all consumption is via Perplexity, local scripts, and MCP. [web:7][web:23][web:27]

---

## 2. `pwm lf-outlet-dossier` — AU Refurb & Clearance Sweep

**Purpose**

- Run a periodic Deep Research sweep across AU refurb/clearance markets and consolidate listings into a single dossier and JSON dataset. [web:17][web:20]

**Inputs**

- `hardware_slice`: string (e.g. `"16gb-mobile"`, `"uma-64gb"`, `"strix-halo"`).
- `markets`: array of strings (e.g. `"Dell Outlet AU"`, `"Lenovo Clearance AU"`, `"Grays Online AU"`, `"Reebelo AU"`).

**Outputs**

- `research/outlet_dossier_<date>.md` — markdown report with active listings and citations.
- `data/outlet_listings_<date>.json` — normalised listing objects:
  - `model`, `cpu`, `gpu`, `vram_gb`, `ram_gb`, `price_aud`, `condition`, `vendor`, `url`.

**Integration**

- Feeds into Laptopfinder scoring (`lf-score`), hardware comparisons (`spec-compare`), Labs dashboards (`lf-matrix-app`), and watcher daemons (`lf-alert-forge`).

---

## 3. `pwm lf-price-baseline` — AU Historical Pricing & Depreciation

**Purpose**

- Use Deep Research to derive baseline price bands and depreciation curves for target GPU and platform tiers. [web:17][web:20][web:26]

**Inputs**

- `tier_spec`: string (e.g. `"RTX 4080 Laptop AU"`, `"M2 Max 64GB UMA AU"`, `"ThinkPad P-series Ada AU"`).

**Outputs**

- `research/baselines/<tier>.md` — pricing dossier with sold price analysis.
- `data/baselines/<tier>_pricing.json` — baseline data:
  - `median_price_aud`, `p10_price_aud`, `p25_price_aud`, `p75_price_aud`.
  - `recommended_bargain_threshold_aud`.
  - Segmentation by condition and seller type.

**Integration**

- Provides numeric thresholds to Laptopfinder (`decide.py`, `lf-score`) for bargain detection and sniper rules.
- Used by negotiation playbooks and jury decisions on high‑value listings.

---

## 4. `pwm lf-silicon-ground` — Ambiguous Silicon Facts

**Purpose**

- Resolve ambiguous GPU/SoC SKUs via Deep Research before changing scoring rules or buying hardware. [web:17][web:20]

**Inputs**

- `sku`: string (e.g. `"Radeon RX 7900M"`, `"Strix Halo 128GB"`, `"Minisforum V3 AMD AI"`).

**Outputs**

- `research/silicon_gaps/<sku>.md` — technical report including:
  - Memory bus width, bandwidth, VRAM capacity, architecture, Linux/CUDA/ROCm support, AU‑relevant caveats.
- `data/silicon_profiles/<sku>.json` — structured profile:
  - `bandwidth_gbps`, `bus_width_bits`, `vram_gb`, `arch`, `cuda_support`, `rocm_support`, `linux_support_notes`, `thermal_profile`, `power_draw_w`.

**Integration**

- Updates `data/hardware_taxonomy.json` and scoring logic.
- Informs Labs dashboards and architecture debates.

---

## 5. `pwm lf-vendor-audit` — AU Vendor & Auction Risk Profiles

**Purpose**

- Use Deep Research to build risk matrices for AU refurb vendors and auction houses. [web:17][web:20]

**Inputs**

- `vendor_context`: string describing the vendor/segment (e.g. `"Grays Online AU laptops"`, `"Reebelo AU ThinkPad P-series"`, `"Dell Outlet AU Alienware"`).

**Outputs**

- `research/vendor_audit/<slug>.md` — markdown risk analysis:
  - Statutory warranty implications, buyer’s premiums, restocking fees, known defect classes, reputation notes.
- `data/vendor_risk/<slug>.json` — numeric risk profile:
  - `warranty_risk_0_10`, `fee_risk_0_10`, `hardware_defect_risk_0_10`, `support_reliability_0_10`, `notes`.

**Integration**

- Calibrates seller modifiers in Laptopfinder scoring.
- Provides inputs to risk calibration workflows and procurement playbooks.

---

## 6. `pwm lf-floor-sync` — AU Price Floor Refresh

**Purpose**

Derive current eBay AU sold-price floors for each `target_gpus` entry and produce a patch file the operator reviews before updating `observed_au_price_min_aud` in the SRL.

**Sniper feed:** `target_gpus.<gpu>.observed_au_price_min_aud` — Strategy B local sweep gate.

**When to run:** Monthly, or when a GPU tier's eBay AU price moves >15% from the current floor.

**Prep (free — no API):**
```
make pwm-floor-sync-prep
```
Prints current floors from SRL to anchor the Deep Research query.

**Inputs to Perplexity:**
- SRL floor table printed by prep target.

**Outputs:**
- `data/pwm/lf-floor-sync/price_patches.json` — array of `{gpu, current_min_aud, new_min_aud, new_max_aud, source_date, rationale}`. Missing data → `null`.
- `data/pwm/lf-floor-sync/floor_sync_report.md` — citations and methodology.

**Check:**
```
make pwm-floor-sync-check
```
Validates: file exists, non-empty, age ≤ 30 days.

**Done criterion:** `price_patches.json` contains ≥ 1 entry with a non-null `new_min_aud`.

**Cost:** 1 deep.

---

## 7. `pwm lf-watch-grad` — Watch List Graduation Monitor

**Purpose**

Assess each `watch_list` entry against its `graduation_condition` using current market data and output a verdict (GRADUATE / HOLD / DEFER) per entry.

**Sniper feed:** `watch_list[*]` → `target_gpus` promotion expands Strategy A keyword sweep.

**When to run:** Monthly, or on major GPU launch news (Blackwell mobile, RTX 5000 Ada).

**Prep (free — no API):**
```
make pwm-watch-grad-prep
```
Prints each watch entry and its graduation condition.

**Inputs to Perplexity:**
- Watch list entries + conditions printed by prep target.

**Outputs:**
- `data/pwm/lf-watch-grad/graduation_report.md` — per-entry GRADUATE / HOLD / DEFER verdict with rationale and AU availability evidence.

**Check:**
```
make pwm-watch-grad-check
```
Validates: file exists and contains at least one GRADUATE/HOLD/DEFER verdict.

**Done criterion:** `graduation_report.md` has a verdict for every current `watch_list` entry.

**Cost:** 1 deep. Optional `council-3` if graduation is ambiguous for a high-value entry.

---

## 8. `pwm lf-query-expand` — eBay Browse API Query Expansion

**Purpose**

Identify gaps in `prompts/search_queries.txt` by comparing current queries against SRL `target_gpus` and propose ≥ 3 new Browse API–compatible query strings.

**Sniper feed:** `prompts/search_queries.txt` — directly expands Strategy A discovery.

**When to run:** Monthly, or when a new target GPU is added to the SRL.

**Prep (free — no API):**
```
make pwm-query-expand-prep
```
Prints active queries and SRL GPU names side by side.

**Inputs to Perplexity:**
- Active query list + SRL GPU names printed by prep target.
- Constraint: Browse API `q=` does not support Boolean operators — queries must be single keyword or short phrase.

**Outputs:**
- `data/pwm/lf-query-expand/proposed_queries.txt` — one query per line, no comments. Human appends approved lines to `prompts/search_queries.txt`.

**Check:**
```
make pwm-query-expand-check
```
Validates: proposed file has ≥ 3 non-comment lines.

**Done criterion:** `proposed_queries.txt` has ≥ 3 new queries not currently in `search_queries.txt`.

**Cost:** 1 deep.

---

## 9. `pwm lf-exclusion-tune` — Exclusion Regex Evolution

**Purpose**

Analyse eBay AU corpus titles for false-positive patterns not caught by `data_integrity.exclusion_regex` and propose regex additions with false-negative risk ratings.

**Sniper feed:** `data_integrity.exclusion_regex` — reduces junk hits in both Strategy A and B.

**When to run:** When a false-positive cluster appears in sniper output (parts listings, eGPU-only, salvage chassis).

**Prep (free — no API):**
```
make pwm-exclusion-tune-prep
```
Prints current regex and 50 corpus titles.

**Inputs to Perplexity:**
- Current regex + corpus title sample printed by prep target.

**Outputs:**
- `data/pwm/lf-exclusion-tune/exclusion_patch.json` — array of `{pattern, rationale, false_negative_risk: "low"|"medium"|"high", example_titles: [...]}`. Human merges low/medium patterns into SRL.

**Check:**
```
make pwm-exclusion-tune-check
```
Validates: file exists and contains ≥ 1 pattern with `false_negative_risk` of `low` or `medium`.

**Done criterion:** `exclusion_patch.json` has ≥ 1 low/medium-risk pattern proposal.

**Cost:** 1 deep. Optional `council-3` for `--strict` review of high-traffic patterns.

---

## 10. `pwm lf-seller-intel` — AU Clearance & Watched Seller Intelligence

**Purpose**

Research eBay AU seller usernames from the corpus to identify clearance operators and flag watched sellers, producing a patch for `clearance_sellers` and `watched_sellers` in the SRL.

**Sniper feed:** `clearance_sellers`, `watched_sellers` — gates Strategy B basement-price sweep.

**When to run:** Monthly, or before first `make live` run of a new sprint.

**Prep (free — no API):**
```
make pwm-seller-intel-prep
```
Prints current SRL lists and unique seller usernames from corpus.

**Inputs to Perplexity:**
- Seller username list + current SRL lists printed by prep target.

**Outputs:**
- `data/pwm/lf-seller-intel/seller_patches.json` — `{rationale_by_seller: {<username>: {verdict: "clearance"|"watched"|"ignore", verified_ebay_au_url: "https://www.ebay.com.au/usr/<username>", corpus_evidence: bool, notes: str}}}`.

**Check:**
```
make pwm-seller-intel-check
```
Validates: file exists and every entry has a non-null `verified_ebay_au_url`.

**Done criterion:** Every corpus seller has a verdict, and all clearance/watched entries have verified eBay AU URLs.

**Cost:** 1 deep.

---

## 11. `pwm lf-retail-compare` — AU Retail vs Used Price Delta

**Purpose**

Fetch current AU retail prices (JB Hi-Fi, Scorptec, MSY) for target GPU tiers and compare them to eBay AU used-market floors from `lf-floor-sync`, producing a buy-vs-wait verdict per GPU tier.

**Sniper feed:** Decision-support only — contextualises used prices; does not update SRL keys.

**When to run:** When a major retailer sale or price drop is announced, or quarterly.

**Requires:** `data/pwm/lf-floor-sync/price_patches.json` from a recent `lf-floor-sync` run.

**Inputs to Perplexity (search grounding enabled):**
- `config/static_reference_layer.json` (`target_gpus` names).
- `data/pwm/lf-floor-sync/price_patches.json` (used floors for delta calculation).

**Outputs:**
- `data/pwm/lf-retail-compare/retail_vs_used.md` — per-GPU buy-vs-wait verdict with retail premium %.
- `data/pwm/lf-retail-compare/retail_skus.csv` — `gpu_tier, retailer, price_aud, url, date`.

**Done criterion:** `retail_skus.csv` contains ≥ 3 target GPU price points from AU retailers.

**Cost:** 1 deep (search grounding).

---

## 12. `pwm lf-grays-auction-assessor` — Grays Online Max-Bid Calculator

**Purpose**

For a given Grays Online auction URL, calculate a maximum bid that explicitly subtracts the buyer's premium from the eBay AU floor, accounting for the fact that Grays premiums (often +20%) make headline prices misleading.

**Sniper feed:** Decision-support only — informs per-auction bid ceiling; does not update SRL keys.

**When to run:** When a Grays auction item matches target GPU criteria.

**Requires:** `data/pwm/lf-floor-sync/price_patches.json` to anchor the floor.

**Inputs to Perplexity (search grounding enabled):**
- `config/static_reference_layer.json` (`vram_gating_logic`).
- `data/pwm/lf-floor-sync/price_patches.json` (used floors).
- Grays auction URL pasted into the Perplexity prompt.

**Outputs:**
- `data/pwm/lf-grays-auction-assessor/grays_bid_strategy.md` — max-bid figure, premium breakdown, vs-floor delta.
- `data/pwm/lf-grays-auction-assessor/grays_auction_eval.csv` — `auction_url, gpu_tier, floor_aud, buyers_premium_pct, max_bid_aud, date`.

**Done criterion:** `grays_bid_strategy.md` contains a `max_bid_aud` figure that explicitly subtracts the buyer's premium from the `lf-floor-sync` floor.

**Cost:** 1 deep (search grounding).

---

## 13. When to Use Deep Research vs Other Modes

Use Deep Research when:

- You need exhaustive multi‑source research with citations and structured outputs on markets, hardware, or vendors. [web:17][web:20][web:28]
- You want to avoid burning many Pro queries for ad‑hoc checks and instead run a periodic, high‑value sweep.

Defer to Labs for:

- Building code, dashboards, or daemons from the research outputs. [web:2][web:22][web:29]
