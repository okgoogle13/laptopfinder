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

## 6. When to Use Deep Research vs Other Modes

Use Deep Research when:

- You need exhaustive multi‑source research with citations and structured outputs on markets, hardware, or vendors. [web:17][web:20][web:28]
- You want to avoid burning many Pro queries for ad‑hoc checks and instead run a periodic, high‑value sweep.

Defer to Labs for:

- Building code, dashboards, or daemons from the research outputs. [web:2][web:22][web:29]
