# Architecture Handover & Review Prompt for Claude Code

This document provides a comprehensive briefing and handover of the **Platform-Agnostic Decision Architecture**, **Generalised Vendor Risk Lens**, **Declarative Capability Governance (`score_0_100` normalisation & missing-data recovery)**, and **Multi-Vendor Watchlist Ranking Engine** developed in the `laptopfinder` workspace.

It is structured specifically as a self-contained briefing and verification prompt for **Claude Code** (`CLAUDE.md` / `AGENTS.md` compliance pass) to conduct a meticulous review, audit, and approval of the architectural enhancements before staging for live production sweeps.

---

## 1. Executive Summary & Objective

The goal of this initiative was to transition `laptopfinder` from an eBay-coupled scoring script into a **Platform-Agnostic, Multi-Vendor Decision Engine**. By establishing a canonical neutral schema and isolating platform quirks (`auction_volatility`, retailer warranties, condition vocabularies) into modular configuration files, the scoring math now applies uniformly across marketplace handles (`EBAY`), major retailers (`SCORPTEC`, `JB_HIFI`), and direct factory outlets (`DIRECT_OEM`).

### Key Milestones Delivered:
1. **Platform-Agnostic Listing Schema (`src/laptopfinder/schemas/platform_agnostic_listing.schema.json`)**: Created the canonical JSON Schema defining the neutral listing structure (`platform`, `listing_id`, `title`, `url`, `vendor_name`, `vendor_type`, `price_aud`, `currency_original`, `is_active`, `condition`, `gpu`, `vram_gb`, `ram_gb`, `cpu_model`, `screen_size_inches`, `screen_type`, `touch`, `paradigm`, `connectivities`).
2. **Modular Platform Adapters & Quirks (`src/laptopfinder/adapters/`, `config/platforms/*.json`)**: Built per-platform adapters (`adapters/ebay.py`, `adapters/scorptec.py`) that normalize raw APIs into the canonical `Listing` structure, governed by independent platform configurations (`config/platforms/ebay.json`, `scorptec.json`, `jb_hifi.json`).
3. **Generalised Vendor Risk Lens (`data/lf-vendor-risk.json`)**: Replaced marketplace-only seller heuristics with a unified database classifying vendors into `MARKETPLACE_PRIVATE`, `MARKETPLACE_STORE`, `RETAILER`, and `OEM_OUTLET` with normalized risk scores ($0.0\text{--}10.0$) and additive flags (`clearance_outlet`, `authorised_reseller`, `grey_import`, `fraud_suspect`).
4. **Declarative Scoring Rules Layer & `score_0_100` Normalisation (`config/static_scoring_rules.json`)**:
   * **Relaxed Professional Lanes**: Expanded `workstation_16_touch_or_pro` (`14–17"` screens) and `uma_dev_rig` (`13–18"` screens, adding `zbook`, `Strix Halo`, `ROG Z13`, `ProArt PX13/PX16`) so compact local-LLM workhorses aren't penalized or dumped into desktop replacement buckets.
   * **Missing-Data Recovery Policy**: Replaced strict "missing field $\rightarrow$ IGNORE" with point deductions (`vram_gb`: $-6$ pts, `system_ram_gb`: $-4$ pts, `cpu_model`: $-2$ pts), routing high-value items or omitted-spec flagship GPUs to **`WATCH`** with the `needs_manual_spec_check` flag.
   * **Future-Proof Connectivity Bonuses**: Flat point additions for high-bandwidth interconnects (`tb4`: $+2$, `tb5`: $+4$, `oculink`: $+5$).
   * **Shared `score_0_100` Scale**: Transparent $0\text{--}100$ score mapping normalized from raw adjusted scores across lane ceilings.
5. **Multi-Dimensional Active Watchlist Engine (`scripts/score_active_watchlist.py`)**: Rebuilt the zero-LLM scoring script to output multi-dimensional JSONL (`watchlist_scored_active.jsonl`) and a markdown purchase matrix (`watchlist_purchase_matrix.md`) featuring explicit columns for `Score (0-100)`, `Platform`, `Vendor Type`, and a dedicated **Promising Watchlist Candidates** table.

---

## 2. File Modification Audit

All modifications strictly adhere to flat, Karpathy-style Python doctrine (`from __future__ import annotations`, zero custom exceptions) and declarative JSON governance:

### New Files Created
| File Path | Description |
|---|---|
| `src/laptopfinder/schemas/platform_agnostic_listing.schema.json` | Canonical JSON Schema contract defining required dimensions (`platform`, `vendor_type`, `connectivities`, `paradigm`, normalized `condition`) for all incoming items. |
| `src/laptopfinder/adapters/__init__.py` | Neutral `Listing` data class and `AdapterFunc` signature establishing the platform-agnostic adapter boundary. |
| `src/laptopfinder/adapters/ebay.py` | eBay adapter mapping Browse API payloads (`item_id`, `seller_username`, condition IDs `1000`/`1500`/`2000`) into `Listing`. |
| `src/laptopfinder/adapters/scorptec.py` | Scorptec adapter mapping product page SKU/in-stock/condition dicts into `Listing`. |
| `config/platforms/ebay.json` | Parameterizes eBay auction volatility (`-4 pts`), money-back guarantee (`+2 pts`), default shipping ($25 AUD), and condition vocabulary. |
| `config/platforms/scorptec.json` | Parameterizes Scorptec local warranty (`+5 pts`), store pickup options (`+3 pts`), authorised reseller status (`+4 pts`), and condition vocabulary. |
| `config/platforms/jb_hifi.json` | Parameterizes JB Hi-Fi local warranty (`+5 pts`), pickup options (`+4 pts`), and commercial refurbished condition vocabulary. |
| `data/lf-vendor-risk.json` | Unified vendor risk database profiling Australian retailers (`scorptec_au`, `jb_hifi_au`, `lenovo_outlet_au`) and marketplace stores/private sellers (`minipcsnmore`, `realslimginz`) with `risk_score` and `flags`. |

### Existing Files Modified
| File Path | Nature of Change | Rationale |
|---|---|---|
| `config/static_scoring_rules.json` | Added `platform_agnostic_listing_fields`, `connectivity_bonuses`, `vendor_risk_lens`, `missing_data_handling`, and `score_0_100_normalization`. Expanded `workstation_16_touch_or_pro` (`14-17"`) and `uma_dev_rig` (`13-18"`) screen gates and keywords. | Move governance of vendor risk, connectivity, normalization math, and missing-data recovery into declarative configuration. |
| `scripts/score_active_watchlist.py` | Integrated `data/lf-vendor-risk.json` lookup, connectivity detection (`tb4`/`tb5`/`oculink`), missing-data deductions, `scope_ok` recovery for high-tier GPUs, and `score_0_100` normalisation. Rendered `Platform`, `Vendor Type`, and `WATCH` table in markdown matrix. | Output multi-dimensional scores across all active listings while capturing promising items needing spec verification. |

---

## 3. Platform-Agnostic Scoring & Normalisation Math

### A. Vendor Risk & Connectivity Additions
When scoring an item across platforms, `adjusted_score` incorporates flat additive signals:
\[
\text{Adjusted Score} = \text{round}(\text{llm\_index} \times \text{workload\_mult}) + \text{FormFactor} + \text{Bottleneck} + \text{Connectivity} + \text{VendorRisk} + \text{MissingDataPenalty}
\]
Where:
* **Connectivity Bonus**: $\sum(\text{tb4}: +2, \text{tb5}: +4, \text{oculink}: +5, \text{usb4}: +1, \text{10gbe}: +2)$.
* **Vendor Risk Adjustment**: $\text{Type Bonus (`AUTHORISED\_RESELLER`: }+4\text{, `RETAILER`: }+3\text{, `OEM\_OUTLET`: }+5\text{, `STORE`: }+1\text{, `PRIVATE`: }0) - \text{round}(\text{risk\_score} \times 1.5)$.

### B. Missing-Data Point Deductions & Recovery into `WATCH`
If an item omits exact `vram_gb` or `system_ram_gb`, the engine applies point deductions (`vram_gb`: $-6$, `system_ram_gb`: $-4$, `cpu_model`: $-2$) instead of immediately dropping the listing.
If the item carries a flagship local-LLM GPU (`RTX 5090`, `RTX 5080`, `RTX 4090`, `RTX 3090`, `RTX A4000/A5000`, `RX 7900M`) or UMA keyword (`M4 Max/Ultra`, `Strix Halo`, `128GB`), `scope_ok` recovers to `True` and routes the item directly to **`WATCH`** with `needs_manual_spec_check`.

### C. Shared `score_0_100` Normalisation
To compare candidates cleanly across lanes and platforms, raw adjusted scores normalize against lane-specific ceilings (`gaming_17_18`: 85, `macbook_16_high_ram`: 90, `workstation_16_touch_or_pro`: 80, `uma_dev_rig`: 85):
\[
\text{score\_0\_100} = \max\left(0, \min\left(100, \text{round}\left(\frac{\text{adjusted\_score}}{\text{lane\_score\_ceiling}} \times 100\right)\right)\right)
\]
* **80–100**: Exceptional Local-LLM Workhorse (Immediate `SHORTLIST` consideration).
* **65–79**: Strong Competitor (`SHORTLIST` if $\text{Value/\$} \ge 0.015$).
* **50–64**: Viable / Niche Workstation (`WATCH` or `SHORTLIST` if heavily discounted).
* **0–49**: Insufficient Capability or Excessive Risk (`IGNORE`).

---

## 4. Verified Active Purchase Matrix & Watchlist Results

Running `.venv/bin/python scripts/score_active_watchlist.py` against the 84 active listings produced:
* **`SHORTLIST`**: **3** high-conviction, fully grounded value leaders.
* **`WATCH`**: **30** promising items (including listings needing manual specification verification or matching watch criteria).
* **`IGNORE`**: **51** low-capacity, overpriced, or high-risk listings.

### Shortlisted Candidates (`SHORTLIST`)
| Lane | Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Value/$ | Specs | Price Band |
|---|---|---|---|---|---|---|---|---|---|
| **Gaming (17-18")** | **A** | `EBAY` | `PRIVATE` | [NEW Lenovo Legion 9i Gen 10 Intel (18″) with RTX 5090...](https://www.ebay.com.au/itm/227431543159) | **$3,640.78** | **84/100** | `0.01950` | RTX 5090 \| 24GB VRAM \| 64GB RAM | `VALUE_ZONE` |
| **High-RAM Apple Silicon** | **A** | `EBAY` | `PRIVATE` | [MacBook Pro 16 2024 M4 Max 128GB 4TB Space Black...](https://www.ebay.com.au/itm/327260100144) | **$3,319.53** | **90/100** | `0.02440` | UMA Integrated \| 128GB Unified | `FAIR_MARKET` |
| **High-RAM Apple Silicon** | **A** | `EBAY` | `PRIVATE` | [Apple MacBook Pro 16" M4 Max 128GB RAM 4TB SSD...](https://www.ebay.com.au/itm/127959150905) | **$3,498.00** | **90/100** | `0.02316` | UMA Integrated \| 128GB Unified | `FAIR_MARKET` |

### Sample Promising Watchlist Items (`WATCH` — Needs Spec Check)
| Lane | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Watch Reason / Flags |
|---|---|---|---|---|---|---|---|
| `gaming_17_18` | `EBAY` | `PRIVATE` | [ASUS ROG Strix SCAR 18 Gaming Laptop – RTX 5090 |...](https://www.ebay.com.au/itm/227413819629) | $3,854.94 | **80/100** | **68** | `needs_manual_spec_check` (Missing RAM spec) |
| `gaming_17_18` | `EBAY` | `PRIVATE` | [Lenovo Legion 9i 18inch 5090 Gaming Laptop Intel...](https://www.ebay.com.au/itm/227432538243) | $3,997.72 | **80/100** | **68** | `needs_manual_spec_check` (Missing RAM spec) |
| `gaming_17_18` | `EBAY` | `PRIVATE` | [ASUS ROG Strix SCAR 18" 2.5K 240Hz 2TB SSD Intel...](https://www.ebay.com.au/itm/278170156343) | $2,856.94 | **68/100** | **58** | `needs_manual_spec_check` |
| `gaming_17_18` | `EBAY` | `PRIVATE` | [Alienware M18 R1 Gaming Laptop 18" i9-13980HX RTX...](https://www.ebay.com.au/itm/278163065343) | $2,535.69 | **60/100** | **51** | `needs_manual_spec_check` |
| `workstation_16_touch_or_pro` | `EBAY` | `PRIVATE` | [HP Zbook Fury 16 G10 Mobile Workstation Laptop A...](https://www.ebay.com.au/itm/116666792610) | $2,499.00 | **60/100** | **48** | `needs_manual_spec_check` |

---

## 5. Review Instructions & Prompt for Claude Code

Copy and paste the prompt below into **Claude Code** (`claude`) to initiate its architectural review:

```markdown
<CLAUDE_REVIEW_TASK>
You are tasked with conducting a meticulous code review, architectural audit, and compliance check of the new **Platform-Agnostic Decision Architecture** and **Declarative Capability Governance** (`score_0_100`, missing-data recovery, and vendor risk lens) in the `laptopfinder` workspace.

Please read `CLAUDE.md` / `AGENTS.md` and review the following files:
1. `src/laptopfinder/schemas/platform_agnostic_listing.schema.json` & `src/laptopfinder/adapters/__init__.py` — verify the neutral `Listing` schema contract and adapter boundary.
2. `src/laptopfinder/adapters/ebay.py` & `src/laptopfinder/adapters/scorptec.py` — check condition mapping (`1000`/`Brand New` -> `NEW`) and parameter isolation.
3. `config/platforms/ebay.json`, `scorptec.json`, `jb_hifi.json` — verify separation of platform quirks (`auction_volatility`, `local_warranty_bonus`, fee estimation).
4. `data/lf-vendor-risk.json` & `config/static_scoring_rules.json` — verify vendor risk profiles (`scorptec_au`, `jb_hifi_au`, `lenovo_outlet_au`), connectivity bonuses (`tb4`/`tb5`/`oculink`), relaxed professional lanes (`workstation_16_touch_or_pro` `[14, 15, 16, 17]`), missing-data point deductions (`needs_manual_spec_check` watch routing), and `score_0_100` normalisation math.
5. `scripts/score_active_watchlist.py` — audit multi-dimensional matrix output (`Score 0-100`, `Platform`, `Vendor Type`, `WATCH` table rendering) and typing compliance.

After completing your review, execute the verification suite:
```bash
# 1. Run all 262 baseline unit tests across stage1/stage2 firewalls, decide() routing, and scoring rules
make test

# 2. Re-run active watchlist scoring to verify 0-100 normalisation, vendor risk, and WATCH recovery
.venv/bin/python scripts/score_active_watchlist.py

# 3. Inspect the active purchase matrix and verify column structure and WATCH integrity
cat output/shortlist/watchlist_purchase_matrix.md
```

Evaluate whether the separation of platform quirks, the generalized vendor risk lens, and the missing-data `WATCH` recovery correctly eliminate platform bias without letting ungrounded facts breach our data integrity firewalls. Provide your final go-live review and confirm approval for multi-vendor market sweeps.
</CLAUDE_REVIEW_TASK>
```
