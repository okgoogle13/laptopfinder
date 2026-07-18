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

Running `.venv/bin/python scripts/score_active_watchlist.py` against the 50 active listings produced the following decision matrix:

Scored against `config/static_reference_layer.json`, `config/static_scoring_rules.json`, and `data/lf-vendor-risk.json`.

**Decision Summary**: `SHORTLIST`: **22** | `WATCH`: **3** | `IGNORE`: **25**

## Gaming — 17-18" Desktop Replacements (13 Shortlisted)

| Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Value/$ | Specs | Price Band |
|---|---|---|---|---|---|---|---|---|---|
| **B** | `EBAY` | `PRIVATE` | [Boxed Asus ROG Strix 18" Core i9-13980HX RTX 4090 ...](https://www.ebay.com.au/itm/Boxed-Asus-ROG-Strix-18-Core-i9-13980HX-RTX-4090-Mini-LED-240Hz-Gaming-Laptop-/318571097651) | $1,934.60 | **64/100** | **54** | `0.02791` | RTX 4090 | 16GB VRAM | 32GB RAM | `VALUE_ZONE` |
| **A** | `EBAY` | `PRIVATE` | [NEW Lenovo Legion 9i Gen 10 Intel (18″) with RTX 5...](https://www.ebay.com.au/itm/NEW-Lenovo-Legion-9i-Gen-10-Intel-18-RTX-5090-64GB-4TB-83EY000XUS-/227431543159) | $2,550.00 | **84/100** | **71** | `0.02784` | RTX 5090 | 24GB VRAM | 64GB RAM | `VALUE_ZONE` |
| **A** | `EBAY` | `PRIVATE` | [SCAN 3XS Vengeance 16" Ultra 9 275HX RTX 5090 64GB...](https://www.ebay.com.au/itm/SCAN-3XS-Vengeance-16-Ultra-9-275HX-RTX-5090-64GB-2TB-QHD-240Hz-Laptop-/267724133646) | $2,299.00 | **75/100** | **64** | `0.02784` | RTX 5090 | 24GB VRAM | 64.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [ASUS ROG Strix SCAR 18 Gaming Laptop – RTX 5090 | ...](https://www.ebay.com.au/itm/ASUS-ROG-Strix-SCAR-18-Gaming-Laptop-RTX-5090-Intel-Core-Ultra-9-275HX-32G-/227434303551) | $2,700.00 | **84/100** | **71** | `0.02630` | RTX 5090 | 24GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [Razer Blade 18 300Hz Mini-LED i9-14900HX RTX 4090 ...](https://www.ebay.com.au/itm/Razer-Blade-18-300Hz-Mini-LED-i9-14900HX-RTX-4090-32GB-2TB-Gaming-Laptop-/278176424797) | $2,309.99 | **60/100** | **51** | `0.02208` | RTX 4090 | 16GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [Razer Blade 18 QHD+ 240Hz (Core i9-14900HX, 32GB/2...](https://www.ebay.com.au/itm/Razer-Blade-18-QHD-240Hz-Core-i9-14900HX-32GB-2TB-SSD-RTX-4090-Black-Laptop-/298337367197) | $2,529.99 | **60/100** | **51** | `0.02016` | RTX 4090 | 16GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [ASUS ROG Strix SCAR 18" 2.5K 240Hz 2TB SSD Intel U...](https://www.ebay.com.au/itm/ASUS-ROG-Strix-SCAR-18-2-5K-240Hz-2TB-SSD-Intel-Ultra-9-HX-32GB-RTX-5080-/278170156343) | $2,928.12 | **68/100** | **58** | `0.01981` | RTX 5080 | 16GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **A** | `EBAY` | `PRIVATE` | [Alienware 16 AREA 51 16" Ultra 9 275HX 64GB RAM 2T...](https://www.ebay.com.au/itm/Alienware-16-AREA-51-16-Ultra-9-275HX-64GB-RAM-2TB-SSD-RTX-5080-/800151312100) | $2,639.99 | **60/100** | **51** | `0.01932` | RTX 5080 | 16GB VRAM | 64.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [Razer Blade 18 240Hz QHD+ 2.2 GHz i9-14900HX 32GB ...](https://www.ebay.com.au/itm/Razer-Blade-18-240Hz-QHD-2-2-GHz-i9-14900HX-32GB-2TB-SSD-RTX-4090-Excellent-/297703731870) | $2,694.99 | **60/100** | **51** | `0.01892` | RTX 4090 | 16GB VRAM | 32.0GB RAM | `FAIR_MARKET` |
| **B** | `EBAY` | `PRIVATE` | [Alienware M18 R1 Gaming Laptop 18" i9-13980HX RTX ...](https://www.ebay.com.au/itm/Alienware-M18-R1-Gaming-Laptop-18-i9-13980HX-RTX-4090-32GB-2TB-SSD-Excellent-/278163065343) | $2,749.66 | **60/100** | **51** | `0.01855` | RTX 4090 | 16GB VRAM | 32.0GB RAM | `FAIR_MARKET` |

## RTX Workstations — 14-17" (incl. Touch & UMA Pro) (1 Shortlisted)

| Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Value/$ | Specs | Price Band |
|---|---|---|---|---|---|---|---|---|---|
| **A** | `EBAY` | `PRIVATE` | [Dell XPS 17 9710 Touch | i9, 64GB RAM, 3TB NVMe + ...](https://www.ebay.com.au/itm/Dell-XPS-17-9710-Touch-i9-64GB-RAM-3TB-NVMe-AORUS-RTX-3090-eGPU-Bundle-/298500296064) | $2,713.96 | **69/100** | **55** | `0.02027` | RTX 3090 | 24GB VRAM | 64.0GB RAM | `VALUE_ZONE` |

## High-RAM Apple Silicon — 14-16" / Desktop (2 Shortlisted)

| Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Value/$ | Specs | Price Band |
|---|---|---|---|---|---|---|---|---|---|
| **B** | `EBAY` | `PRIVATE` | [MacBook Pro M5 Max 64gb 2TB Brand New Sealed](https://www.ebay.com.au/itm/MacBook-Pro-M5-Max-64gb-2TB-Brand-New-Sealed-/127970105057) | $2,950.00 | **76/100** | **68** | `0.02305` | UMA Integrated | 64.0GB VRAM | 64.0GB RAM | `VALUE_ZONE` |
| **A** | `EBAY` | `PRIVATE` | [MacBook Pro 16 2024 M4 Max 128GB 4TB Space Black N...](https://www.ebay.com.au/itm/MacBook-Pro-16-2024-M4-Max-128GB-4TB-Space-Black-Nano-Texture-Excellent-/327260100144) | $3,926.05 | **90/100** | **81** | `0.02063` | UMA Integrated | 128.0GB VRAM | 128.0GB RAM | `FAIR_MARKET` |

## UMA Dev Rigs & Workstation Outliers (6 Shortlisted)

| Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Value/$ | Specs | Price Band |
|---|---|---|---|---|---|---|---|---|---|
| **C** | `EBAY` | `PRIVATE` | [ASUS ROG Flow Z13 Ryzen AI MAX 390 8050S 32GB 1TB ...](https://www.ebay.com.au/itm/ASUS-ROG-Flow-Z13-Ryzen-AI-MAX-390-8050S-32GB-1TB-QHD-180Hz-Convertible-Laptop-/267696116748) | $1,369.00 | **66/100** | **56** | `0.04091` | UMA Integrated | 32.0GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **C** | `EBAY` | `PRIVATE` | [ASUS ROG Flow Z13 Ryzen AI MAX 395 8060S 32GB 1TB ...](https://www.ebay.com.au/itm/ASUS-ROG-Flow-Z13-Ryzen-AI-MAX-395-8060S-32GB-1TB-QHD-180Hz-Convertible-Laptop-/267705512556) | $1,499.00 | **66/100** | **56** | `0.03736` | UMA Integrated | 32.0GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [ASUS Proart PX13 Ryzen AI MAX+ 395 64GB 1TB 3K OLE...](https://www.ebay.com.au/itm/ASUS-Proart-PX13-Ryzen-AI-MAX-395-64GB-1TB-3K-OLED-Touch-2-in-1-Laptop-WTY-VAT-/267727340622) | $1,949.00 | **84/100** | **71** | `0.03643` | UMA Integrated | 64.0GB VRAM | 64.0GB RAM | `VALUE_ZONE` |
| **C** | `EBAY` | `PRIVATE` | [HP ZBook Ultra G1a 14” LCD Ryzen AI Max PRO 390 3....](https://www.ebay.com.au/itm/HP-ZBook-Ultra-G1a-14-LCD-Ryzen-AI-Max-PRO-390-3-20GHz-32GB-512GB-WIFI-BT-W11P-/198404782666) | $1,594.99 | **62/100** | **53** | `0.03323` | UMA Integrated | 32.0GB VRAM | 32.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [HP ZBook Ultra G1a 14 Ryzen AI MAX+ PRO 395 64GB 2...](https://www.ebay.com.au/itm/HP-ZBook-Ultra-G1a-14-Ryzen-AI-MAX-PRO-395-64GB-2TB-Workstation-Grade-D-/307011225833) | $2,133.98 | **80/100** | **68** | `0.03187` | UMA Integrated | 64.0GB VRAM | 64.0GB RAM | `VALUE_ZONE` |
| **B** | `EBAY` | `PRIVATE` | [HP ZBook Ultra G1a 14/AMD RYZEN AI MAX PRO 390/Rad...](https://www.ebay.com.au/itm/HP-ZBook-Ultra-G1a-14-AMD-RYZEN-AI-MAX-PRO-390-Radeon-8050S-Itgrt-64-GB-1TB-SSD-/117289670348) | $2,198.90 | **80/100** | **68** | `0.03092` | UMA Integrated | 64.0GB VRAM | 64.0GB RAM | `VALUE_ZONE` |

## Promising Watchlist Candidates (3 Watch Items)
_Items requiring manual specification check or matching a watchlist criteria._

| Lane | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Watch Reason / Flags |
|---|---|---|---|---|---|---|---|
| `gaming_17_18` | `EBAY` | `PRIVATE` | [MSI Vector 17 HX AI A2XWJG 17in QHD+ 240Hz Ul...](https://www.ebay.com.au/itm/MSI-Vector-17-HX-AI-A2XWJG-17in-QHD-240Hz-Ultra-9-275HX-RTX-5090-6TB-SSDs-64GB-/158074702553) | $5,200.00 | **79/100** | **67** | `Needs Spec Check` |
| `gaming_17_18` | `EBAY` | `STORE` | [MSI RAIDER GE68 Mini LED UHD+ RTX 4090 i91398...](https://www.ebay.com.au/itm/MSI-RAIDER-GE68-Mini-LED-UHD-RTX-4090-i913980HX-32GB-RAM-2TB-4K-120HZ-RRP-7999-/227405662429) | $3,650.70 | **60/100** | **51** | `Needs Spec Check` |
| `gaming_17_18` | `EBAY` | `PRIVATE` | [Lenovo Legion Pro 7i 16" | i9 14900HX | RTX 4...](https://www.ebay.com.au/itm/Lenovo-Legion-Pro-7i-16-i9-14900HX-RTX-4090-16GB-32GB-RAM-2TB-SSD-/137503173909) | $3,547.50 | **54/100** | **46** | `Needs Spec Check` |



---

## 5. Multi-Platform Retailer Archetypes, Vendor Legend & Illustrative Test Fixtures

To ensure the scoring architecture operates neutrally across both eBay AU and Australian retailers/OEMs, this section establishes the canonical non-eBay platform codes, vendor type legend, lane archetypes, and illustrative test fixtures.

### 5.1 Retailer Platforms & Procurement Roles

| Platform | Rationale |
|----------|-----------|
| **SCORPTEC** | Specialist Australian retailer with strong coverage of premium gaming, creator, and workstation laptops. A reliable source for high-end RTX and enterprise-class hardware. |
| **JB_HIFI** | National consumer retailer that periodically offers aggressive clearance pricing on premium gaming and creator laptops. Useful as a benchmark for mainstream retail pricing. |
| **LENOVO_OUTLET_AU** | OEM outlet for cancelled orders, refurbished units, and overstock inventory. Often provides strong value on ThinkPad and Legion systems with full OEM warranty. |
| **HP_STORE_AU** | Official HP Australian store offering promotions on ZBook, Omen, and business-class laptops. Valuable for enterprise warranty, direct support, and workstation configurations. |

> **Architecture Note:** `platform_agnostic_listing.schema.json` isolates these platforms cleanly: local retailer warranties and clearance events enter scoring purely through declarative vendor risk bonuses ($+3\text{ to }+5\text{ pts}$) without requiring custom Python branching.

### 5.2 Vendor Type Legend & Relative Risk Stratification

| Vendor Type | Typical Characteristics | Relative Procurement Risk |
|-------------|-------------------------|---------------------------|
| **Specialist retailer** | Specialist PC retailer with enthusiast/workstation focus, knowledgeable support, local warranty. | Low (`risk_score: 0.3`) |
| **National retailer** | Large consumer electronics chain with broad distribution, standard Australian consumer protections. | Low (`risk_score: 0.5`) |
| **OEM outlet** | Manufacturer-operated outlet selling refurbished, cancelled-order or overstock inventory with OEM warranty. | Low (`risk_score: 0.2`) |
| **OEM direct** | Purchased directly from the manufacturer's Australian store with full OEM support and warranty. | Lowest (`risk_score: 0.1`) |

> **Risk Stratification Note:** These canonical legend names map directly to the normalized `0.0–10.0` risk scale in `data/lf-vendor-risk.json` (`OEM direct` $\rightarrow 0.1$, `OEM outlet` $\rightarrow 0.2$, `Specialist retailer` $\rightarrow 0.3$, `National retailer` $\rightarrow 0.5$, compared to unverified `MARKETPLACE_PRIVATE` eBay handles at $1.0\text{--}2.0+$).

### 5.3 Lane Archetypes & Target Specifications

The system governs six core hardware archetypes across our four canonical scoring lanes (`gaming_17_18`, `workstation_16_touch_or_pro`, `uma_dev_rig`, `macbook_16_high_ram`):

1. **Gaming Desktop Replacement** (`gaming_17_18`): RTX 4090 / RTX 5090 (16GB+ VRAM), 32–64GB RAM, 18" QHD+ 240Hz, HX/Core Ultra 9 class. Representative models: Alienware Area-51 18, MSI Raider 18 HX, Acer Predator Helios 18, ASUS ROG Strix Scar 18.
2. **Professional RTX Mobile Workstation** (`workstation_16_touch_or_pro`): RTX 4000 Ada / RTX 5000 Ada, 64GB RAM, 16–17", ISV-certified workstation platform. Representative models: HP ZBook Fury, Dell Precision 7680 / 7780, Lenovo ThinkPad P16.
3. **Creator Laptop** (`workstation_16_touch_or_pro`): RTX 4080 / RTX 4090, 32–64GB RAM, 16" OLED or Mini-LED. Representative models: ASUS ProArt P16, Razer Blade 16, MSI Creator series.
4. **High-RAM UMA Development Rig** (`uma_dev_rig`): Integrated / UMA, 64–128GB unified/shared memory, 14–16", local LLM inference and software development focus. Representative models: ASUS ROG Flow Z13 (Strix Halo), ASUS ProArt PX13 / P16, HP ZBook Ultra G1a (Ryzen AI Max class).
5. **High-Memory MacBook Pro** (`macbook_16_high_ram`): M4 Max, 64–128GB unified memory, 16" Mini-LED. Representative models: MacBook Pro 16 (M4 Max).
6. **Previous-Generation Flagship Value System** (`gaming_17_18`): RTX 3080 Ti 16GB or RTX 4090 16GB, 32GB+ RAM, 17–18". Representative models: Alienware x17 R2, Lenovo Legion Pro 7, MSI GE76 Raider, Gigabyte Aorus 17.

### 5.4 Illustrative Non-eBay Example Rows & Testing Policy

| Lane | Platform | Vendor Type | Example Model | Placeholder Price (AUD) | Placeholder Score | Reason |
|------|----------|-------------|---------------|-------------------------|------------------|--------|
| `gaming_17_18` | `SCORPTEC` | Specialist retailer | MSI Raider 18 HX RTX 5090 64GB | **~$6,400** | **≈94/100** | Premium desktop replacement with strong local warranty and maximum VRAM. |
| `workstation_16_touch_or_pro` | `SCORPTEC` | Specialist retailer | HP ZBook Fury 16 G11 RTX 4000 Ada 64GB | **~$5,700** | **≈89/100** | Enterprise workstation with professional GPU, sustained compute performance, and local warranty. |
| `workstation_16_touch_or_pro` | `JB_HIFI` | National retailer | ASUS ProArt P16 RTX 4080 64GB | **~$4,200** | **≈87/100** | Creator-class laptop that exercises the creator archetype with premium display, high memory, and local retail warranty. |
| `gaming_17_18` | `JB_HIFI` | National retailer | Lenovo Legion Pro 7i RTX 4080 32GB (clearance) | **~$3,600** | **≈86/100** | Clearance pricing with Australian consumer warranty and strong overall value. |
| `uma_dev_rig` | `LENOVO_OUTLET_AU` | OEM outlet | ThinkPad P16s Gen 3 (64GB integrated graphics configuration) | **~$2,900** | **≈79/100** | High-memory development system with low procurement risk and outlet pricing. |
| `uma_dev_rig` | `HP_STORE_AU` | OEM direct | HP ZBook Ultra G1a Ryzen AI Max 64GB UMA | **~$3,900** | **≈88/100** | Unified-memory AI workstation prioritising local LLM workloads, battery life, and OEM support. |

> **IMPORTANT — ILLUSTRATIVE TEST DATA ONLY:** The retailer platforms, archetypes, model names, placeholder prices (e.g. `~$3,600`), and placeholder scores (e.g. `≈86/100`) documented in this section and stored in `tests/fixtures/retail_archetypes.jsonl` are **illustrative examples** intended exclusively for architecture verification, schema compliance audits, and unit testing. **They MUST NOT be treated as real market baselines, true floor prices, or live procurement recommendations.** Live scoring and market sweeps must always execute against real-time API or scraped payloads. When testing, verify that `is_illustrative_fixture` is `True` before asserting against `price_aud_placeholder` or `score_0_100_placeholder`.

---

## 6. Review Instructions & Prompt for Claude Code

Copy and paste the prompt below into **Claude Code** (`claude`) to initiate its architectural review:

```markdown
<CLAUDE_REVIEW_TASK>
You are tasked with conducting a meticulous code review, architectural audit, and compliance check of the new **Platform-Agnostic Decision Architecture**, **Multi-Platform Retailer Archetypes**, and **Declarative Capability Governance** (`score_0_100`, missing-data recovery, and vendor risk lens) in the `laptopfinder` workspace.

Please read `CLAUDE.md` / `AGENTS.md` and review the following files:
1. `src/laptopfinder/schemas/platform_agnostic_listing.schema.json` & `src/laptopfinder/adapters/__init__.py` — verify the neutral `Listing` schema contract and adapter boundary across both eBay and non-eBay retailer platforms (`SCORPTEC`, `JB_HIFI`, `LENOVO_OUTLET_AU`, `HP_STORE_AU`).
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
