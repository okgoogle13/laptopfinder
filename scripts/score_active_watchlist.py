"""
Score active items from data/pwm/lf-watchlist/watchlist_raw.jsonl against static scoring rules.

Produces:
    output/shortlist/watchlist_scored_active.jsonl
    output/shortlist/watchlist_purchase_matrix.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

IN_PATH = Path("data/pwm/lf-watchlist/watchlist_raw.jsonl")
OUT_JSONL = Path("output/shortlist/watchlist_scored_active.jsonl")
OUT_MD = Path("output/shortlist/watchlist_purchase_matrix.md")
SRL_PATH = Path("config/static_reference_layer.json")
RULES_PATH = Path("config/static_scoring_rules.json")
VENDOR_RISK_PATH = Path("data/lf-vendor-risk.json")
BASELINE_PATH = Path("data/lf-price-baseline.csv")


def load_baselines() -> dict[str, float]:
    baselines = {}
    if not BASELINE_PATH.exists():
        return baselines
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 3 and parts[1] and parts[2]:
            try:
                baselines[parts[1]] = float(parts[2])
            except ValueError:
                pass
    return baselines


def load_vendor_risk() -> dict[str, dict]:
    vendor_map = {}
    if VENDOR_RISK_PATH.exists():
        with open(VENDOR_RISK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for v in data.get("vendors", []):
                vendor_map[v["vendor_id"].lower()] = v
    return vendor_map


def extract_screen_inches(title: str) -> int | None:
    m = re.search(r'\b(14|15|16|17|18)\s*["′″]', title)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(14|15|16|17|18)\s*-?\s*inch', title, re.I)
    if m:
        return int(m.group(1))
    for pat, inc in [
        (re.compile(r"\bBlade\s+18\b", re.I), 18),
        (re.compile(r"\bHelios\s+18\b", re.I), 18),
        (re.compile(r"\bVector\s+18\b", re.I), 18),
        (re.compile(r"\bSCAR\s+18\b", re.I), 18),
        (re.compile(r"\bRaider\s+GE[67]8\b", re.I), 17),
        (re.compile(r"\bSCAR\s+17\b", re.I), 17),
        (re.compile(r"\bBlade\s+16\b", re.I), 16),
        (re.compile(r"\bHelios\s+16\b", re.I), 16),
        (re.compile(r"\bP16\b", re.I), 16),
        (re.compile(r"\bProArt\s+P16\b", re.I), 16),
        (re.compile(r"\bZBook\s+14\b", re.I), 14),
        (re.compile(r"\bFlow\s+Z13\b", re.I), 13),
    ]:
        if pat.search(title):
            return inc
    m = re.search(r'\b(14|15|16|17|18)["″]', title)
    if not m:
        m = re.search(r'\b(14|15|16|17|18)\b', title)
    return int(m.group(1)) if m else None


def extract_hardware_from_title(title: str) -> dict:
    gpu_model = None
    vram_gb = None
    system_ram_gb = None
    is_uma = False
    paradigm = "discrete_cuda"
    rocm_disclosure = False

    # Check RAM
    ram_match = re.search(r'\b(\d+)\s*GB\s*(?:RAM|MEM|DDR5|LPDDR5|Unified)\b', title, re.I)
    if ram_match:
        system_ram_gb = float(ram_match.group(1))
    else:
        rm = re.search(r'\b(16|32|64|96|128|192)\s*GB\b.*?\b(512GB|1TB|2TB|4TB|5TB|6TB)\b', title, re.I)
        if rm:
            system_ram_gb = float(rm.group(1))

    # Check UMA
    if re.search(r'\b(M[1-5]\s*(?:Max|Ultra)|Ryzen AI Max|Strix Halo|ROG Z13|ProArt PX13)\b', title, re.I):
        is_uma = True
        if re.search(r'\b(Ryzen AI Max|Strix Halo|ROG Z13|ProArt PX13)\b', title, re.I):
            paradigm = "amd_uma"
        else:
            paradigm = "apple_silicon_uma"

    # Check GPU
    if re.search(r'\b5090\b', title):
        gpu_model = "RTX 5090"
        vram_gb = 24
        if not system_ram_gb and "64GB" in title:
            system_ram_gb = 64
        elif not system_ram_gb and "32GB" in title:
            system_ram_gb = 32
    elif re.search(r'\b5080\b', title):
        gpu_model = "RTX 5080"
        vram_gb = 16
        if not system_ram_gb and "32GB" in title:
            system_ram_gb = 32
        elif not system_ram_gb and "64GB" in title:
            system_ram_gb = 64
    elif re.search(r'\b5070\s*ti\b', title, re.I):
        gpu_model = "RTX 5070 Ti"
        vram_gb = 12
    elif re.search(r'\b5070\b', title):
        gpu_model = "RTX 5070"
        vram_gb = 8
    elif re.search(r'\b4090\b', title):
        gpu_model = "RTX 4090"
        vram_gb = 16
        if "Aurora R12" in title or "Desktop" in title:
            vram_gb = 24
        if not system_ram_gb and "32GB" in title:
            system_ram_gb = 32
        elif not system_ram_gb and "64GB" in title:
            system_ram_gb = 64
    elif re.search(r'\b4080\b', title):
        gpu_model = "RTX 4080"
        vram_gb = 12
    elif re.search(r'\b4070\b', title):
        gpu_model = "RTX 4070"
        vram_gb = 8
    elif re.search(r'\b4060\b', title):
        gpu_model = "RTX 4060"
        vram_gb = 8
    elif re.search(r'\b3090\b', title):
        gpu_model = "RTX 3090"
        vram_gb = 24
    elif re.search(r'\b3080\s*ti\b', title, re.I):
        gpu_model = "RTX 3080 Ti"
        vram_gb = 16
    elif re.search(r'\b3080\b', title):
        gpu_model = "RTX 3080"
        vram_gb = 16
    elif re.search(r'\b3070\s*ti\b', title, re.I):
        gpu_model = "RTX 3070 Ti"
        vram_gb = 8
    elif re.search(r'\b(A3000|3000A)\b', title):
        gpu_model = "RTX A3000"
        vram_gb = 12
    elif re.search(r'\bA4000\b', title):
        gpu_model = "RTX A4000"
        vram_gb = 16
    elif re.search(r'\bA4500\b', title):
        gpu_model = "RTX A4500"
        vram_gb = 16
    elif re.search(r'\bA5000\b', title):
        gpu_model = "RTX A5000"
        vram_gb = 16
    elif re.search(r'\b3500\s*Ada\b', title, re.I):
        gpu_model = "RTX 3500 Ada"
        vram_gb = 12
    elif re.search(r'\bRX\s*7900M\b', title, re.I):
        gpu_model = "RX 7900M"
        vram_gb = 16
        paradigm = "discrete_rocm"
        rocm_disclosure = True
    elif is_uma:
        gpu_model = "UMA Integrated"
        if not system_ram_gb:
            if "128GB" in title:
                system_ram_gb = 128
            elif "96GB" in title:
                system_ram_gb = 96
            elif "64GB" in title:
                system_ram_gb = 64
            elif "32GB" in title:
                system_ram_gb = 32
        vram_gb = system_ram_gb

    return {
        "gpu_model": gpu_model,
        "vram_gb": vram_gb,
        "system_ram_gb": system_ram_gb,
        "is_uma": is_uma,
        "paradigm": paradigm,
        "rocm_disclosure": rocm_disclosure,
    }


def main():
    if not IN_PATH.exists() or not SRL_PATH.exists() or not RULES_PATH.exists():
        print("ERROR: Missing required input/config files.", file=sys.stderr)
        return 1

    with open(SRL_PATH, "r", encoding="utf-8") as f:
        srl = json.load(f)
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        rules = json.load(f)

    baselines = load_baselines()
    vendor_risk_map = load_vendor_risk()

    exclusion_regex = srl["data_integrity"]["exclusion_regex"]
    target_gpus = srl.get("target_gpus", {})
    target_models = srl.get("target_models", [])
    vram_tiers = srl.get("vram_tiers", {})
    cap_points_by_tier = srl["llm_index_score"]["capacity_points_by_tier"]
    gen_points_map = srl["llm_index_score"]["gpu_generation_points"]
    gen_by_name = srl["llm_index_score"]["gpu_generation_by_name"]
    arch_penalty_turing = srl["architecture_adjustments"]["turing_vs_ada_same_vram_penalty_pts"]

    rows = []
    with open(IN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    active_rows = [r for r in rows if r.get("is_available", True) and r.get("status") == "ACTIVE"]
    print(f"Loaded {len(rows)} total rows, filtering to {len(active_rows)} ACTIVE listings.")

    scored_items = []
    lane_counts = {"gaming_17_18": 0, "workstation_16_touch_or_pro": 0, "macbook_16_high_ram": 0, "uma_dev_rig": 0}
    decision_counts = {"SHORTLIST": 0, "WATCH": 0, "IGNORE": 0}

    for item in active_rows:
        title = item["title"]
        price = item.get("current_price") or item.get("price")
        item_id = item["item_id"]
        platform = item.get("platform", "ebay")
        vendor_name = str(item.get("seller_username") or item.get("vendor_name") or "unknown")
        vendor_info = vendor_risk_map.get(vendor_name.lower(), {})
        vendor_type = vendor_info.get("vendor_type") or ("MARKETPLACE_STORE" if "store" in vendor_name.lower() else "MARKETPLACE_PRIVATE")
        vendor_risk_score = vendor_info.get("risk_score", 1.0 if vendor_type == "MARKETPLACE_PRIVATE" else 0.5)

        data_integrity_ok = not bool(re.search(exclusion_regex, title, re.I))
        if "*READ*" in title or "read desc" in title.lower():
            data_integrity_ok = False

        touchscreen_present = bool(re.search(r"\btouch(screen)?\b", title, re.I))
        screen_inches = extract_screen_inches(title)
        hw = extract_hardware_from_title(title)

        gpu_model = hw["gpu_model"]
        vram_gb = hw["vram_gb"]
        system_ram_gb = hw["system_ram_gb"]
        is_uma = hw["is_uma"]
        paradigm = hw["paradigm"]
        rocm_disclosure = hw["rocm_disclosure"]

        # Connectivities detection
        connectivities = list(item.get("connectivities", []))
        if re.search(r"\b(tb4|thunderbolt\s*4)\b", title, re.I) and "tb4" not in connectivities:
            connectivities.append("tb4")
        if re.search(r"\b(tb5|thunderbolt\s*5)\b", title, re.I) and "tb5" not in connectivities:
            connectivities.append("tb5")
        if re.search(r"\boculink\b", title, re.I) and "oculink" not in connectivities:
            connectivities.append("oculink")

        conn_bonuses_cfg = rules.get("signals_and_tiers", {}).get("connectivity_bonuses", {}).get("bonuses_pts", {})
        connectivity_bonus_pts = sum(conn_bonuses_cfg.get(c, 0) for c in connectivities)

        # Vendor risk adjustment
        vendor_bonuses_cfg = rules.get("adjustments_and_penalties", {}).get("vendor_risk_lens", {}).get("vendor_type_bonuses_pts", {})
        vendor_risk_adjustment_pts = vendor_bonuses_cfg.get(vendor_type, 0) - round(vendor_risk_score * 1.5)

        # Classify Lane
        if any(kw in title.lower() for kw in ["macbook pro", "mac studio", "mac mini"]) or any(
            pat.lower() in (gpu_model or "").lower() for pat in ["m1 max", "m1 ultra", "m2 max", "m2 ultra", "m3 max", "m3 ultra", "m4 max", "m4 ultra"]
        ):
            lane = "macbook_16_high_ram"
        elif is_uma or any(kw in title.lower() for kw in ["strix halo", "rog z13", "proart px13", "proart px16", "xg mobile"]):
            lane = "uma_dev_rig" if is_uma else "workstation_16_touch_or_pro"
        elif any(kw in title.lower() for kw in ["precision", "thinkpad p", "zbook", "proart", "creator"]) or (touchscreen_present and screen_inches in [14, 15, 16, 17]):
            lane = "workstation_16_touch_or_pro"
        else:
            lane = "gaming_17_18"

        lane_counts[lane] += 1

        # Classify Tier
        tier = None
        if lane in ("macbook_16_high_ram", "uma_dev_rig"):
            if system_ram_gb and system_ram_gb >= 96:
                tier = "A"
            elif system_ram_gb and system_ram_gb >= 64:
                tier = "B"
            elif system_ram_gb and system_ram_gb >= 32:
                tier = "C"
        else:
            if vram_gb and vram_gb >= 16 and system_ram_gb and system_ram_gb >= 64:
                tier = "A"
            elif vram_gb and vram_gb >= 12 and system_ram_gb and system_ram_gb >= 32:
                tier = "B"
            elif vram_gb and vram_gb >= 8 and system_ram_gb and system_ram_gb >= 32:
                tier = "C"

        vram_tier_name = None
        capacity_points = 0
        if vram_gb is not None and not is_uma:
            for tname, trange in vram_tiers.items():
                if trange["min_gb"] <= vram_gb <= trange["max_gb"]:
                    vram_tier_name = tname
                    capacity_points = cap_points_by_tier[tname]
                    break
        elif is_uma:
            if (system_ram_gb or 0) >= 96:
                capacity_points = 60
            elif (system_ram_gb or 0) >= 64:
                capacity_points = 50
            elif (system_ram_gb or 0) >= 32:
                capacity_points = 35

        scope_ok = False
        if is_uma and (system_ram_gb or 0) >= 32:
            scope_ok = True
        elif vram_gb is not None and not is_uma:
            if vram_gb >= 16 or (vram_gb >= 12 and touchscreen_present):
                scope_ok = True
        elif vram_gb is None and not is_uma and gpu_model in ["RTX 5090", "RTX 5080", "RTX 4090", "RTX 4080", "RTX 3090", "RTX 3080", "RTX A4000", "RTX A5000", "RX 7900M"]:
            scope_ok = True
        elif is_uma and system_ram_gb is None and any(pat in title.lower() for pat in ["max", "ultra", "strix halo", "64gb", "96gb", "128gb"]):
            scope_ok = True

        risk_score = vendor_risk_score
        if not data_integrity_ok:
            risk_score += 5.0
        if vram_gb is None:
            risk_score += 2.0
        if system_ram_gb is None:
            risk_score += 1.0

        missing_data_penalty_pts = 0
        if vram_gb is None and not is_uma:
            missing_data_penalty_pts -= 6
        if system_ram_gb is None:
            missing_data_penalty_pts -= 4
        if item.get("cpu_model") is None and not re.search(r'\b(i[579]|ryzen|m[1-4]|xeon)\b', title, re.I):
            missing_data_penalty_pts -= 2

        gen = gen_by_name.get(gpu_model)
        if is_uma:
            gen = "UMA_Architecture"
        generation_points = gen_points_map.get(gen, 0) if gen else 0

        if gpu_model in target_gpus:
            generation_points += 5
        for tm in target_models:
            if tm.lower() in title.lower():
                generation_points += 3
                break

        arch_penalty_pts = 0
        if gen == "Turing" and vram_tier_name is not None:
            arch_penalty_pts = abs(arch_penalty_turing)

        seller_risk_penalty_pts = 0
        if "import" in title.lower() or "azerty" in title.lower():
            seller_risk_penalty_pts = -10

        llm_index_score = capacity_points + generation_points + seller_risk_penalty_pts - arch_penalty_pts
        if llm_index_score < 0:
            llm_index_score = 0

        workload_penalty_mult = 1.0 if is_uma else 0.85

        # Form factor bonus
        form_factor_bonus_pts = 0
        if not (lane in ("macbook_16_high_ram", "uma_dev_rig")):
            if screen_inches and screen_inches >= 18:
                form_factor_bonus_pts = 8
            elif screen_inches == 17:
                form_factor_bonus_pts = 6
            elif screen_inches == 16 and touchscreen_present:
                form_factor_bonus_pts = 5
            elif screen_inches in [14, 15] and touchscreen_present:
                form_factor_bonus_pts = 4
            elif screen_inches == 16:
                form_factor_bonus_pts = 3

        # Bottleneck adjustments
        bottleneck_pts = 0
        if not is_uma and vram_gb and system_ram_gb:
            if system_ram_gb < vram_gb:
                bottleneck_pts = -5
            elif system_ram_gb >= vram_gb * 1.25:
                bottleneck_pts = 3

        adjusted_score = round(llm_index_score * workload_penalty_mult) + form_factor_bonus_pts + bottleneck_pts + connectivity_bonus_pts + vendor_risk_adjustment_pts + missing_data_penalty_pts

        # 0-100 Score Normalization
        ceilings = {
            "gaming_17_18": 85,
            "workstation_16_touch_or_pro": 80,
            "macbook_16_high_ram": 90,
            "uma_dev_rig": 85
        }
        lane_ceiling = ceilings.get(lane, 85)
        score_0_100 = max(0, min(100, round((adjusted_score / lane_ceiling) * 100)))

        baseline_median_aud = baselines.get(gpu_model)
        value_per_dollar = round(adjusted_score / price, 5) if price and price > 0 else None

        price_band_tag = "UNKNOWN"
        if price is None:
            price_band_tag = "UNKNOWN"
        elif price < 800 and not is_uma and (vram_gb or 0) >= 16:
            price_band_tag = "BELOW_FLOOR"
        elif baseline_median_aud and price <= baseline_median_aud * 0.95:
            price_band_tag = "VALUE_ZONE"
        elif baseline_median_aud and price <= baseline_median_aud * 1.15:
            price_band_tag = "FAIR_MARKET"
        elif baseline_median_aud and price > baseline_median_aud * 1.15:
            price_band_tag = "OVERPRICED"
        else:
            if price <= 3000 and adjusted_score >= 50:
                price_band_tag = "VALUE_ZONE"
            elif price <= 4500 and adjusted_score >= 50:
                price_band_tag = "FAIR_MARKET"
            else:
                price_band_tag = "OVERPRICED" if price > 4500 else "FAIR_MARKET"

        watchlist_reason_flag = None
        for wl in srl.get("watch_list", []):
            if wl["name"].lower() in title.lower():
                watchlist_reason_flag = wl["reason"]
                break

        if not data_integrity_ok or (vendor_info.get("flags", {}).get("fraud_suspect") and risk_score >= 7.0) or (price is None and vram_gb is None and system_ram_gb is None) or price_band_tag == "BELOW_FLOOR":
            decision = "IGNORE"
        elif not scope_ok and adjusted_score < 45:
            decision = "IGNORE"
        elif risk_score > 3.0:
            decision = "IGNORE"
        elif watchlist_reason_flag is not None or (rocm_disclosure and adjusted_score >= 50) or (missing_data_penalty_pts < 0 and scope_ok and adjusted_score >= 45 and price_band_tag in ["VALUE_ZONE", "FAIR_MARKET"]) or (price is None and scope_ok and adjusted_score >= 45):
            decision = "WATCH"
            if missing_data_penalty_pts < 0:
                watchlist_reason_flag = (watchlist_reason_flag + "; " if watchlist_reason_flag else "") + "needs_manual_spec_check"
        elif scope_ok and adjusted_score >= 50 and price_band_tag in ["VALUE_ZONE", "FAIR_MARKET"] and (value_per_dollar or 0) >= 0.015:
            decision = "SHORTLIST"
        elif scope_ok and adjusted_score >= 45 and (missing_data_penalty_pts < 0 or (value_per_dollar or 0) >= 0.012):
            decision = "WATCH"
            if missing_data_penalty_pts < 0:
                watchlist_reason_flag = (watchlist_reason_flag + "; " if watchlist_reason_flag else "") + "needs_manual_spec_check"
        else:
            decision = "IGNORE"

        decision_counts[decision] += 1

        scored_item = {
            "item_id": item_id,
            "platform": platform,
            "vendor_name": vendor_name,
            "vendor_type": vendor_type,
            "title": title,
            "seller_username": item.get("seller_username") or vendor_name,
            "url": item.get("url"),
            "current_price": price,
            "original_currency": item.get("original_currency", "AUD"),
            "original_price": item.get("original_price", price),
            "lane": lane,
            "tier": tier,
            "gpu_model": gpu_model,
            "vram_gb": vram_gb,
            "system_ram_gb": system_ram_gb,
            "screen_inches": screen_inches,
            "has_touchscreen": touchscreen_present,
            "is_uma": is_uma,
            "connectivities": connectivities,
            "data_integrity_ok": data_integrity_ok,
            "scope_ok": scope_ok,
            "risk_score": risk_score,
            "llm_index_score": llm_index_score,
            "adjusted_score": adjusted_score,
            "score_0_100": score_0_100,
            "price_band_tag": price_band_tag,
            "value_per_dollar": value_per_dollar,
            "watchlist_reason_flag": watchlist_reason_flag,
            "decision": decision,
        }
        scored_items.append(scored_item)

    # Save JSONL
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for si in scored_items:
            f.write(json.dumps(si, ensure_ascii=False) + "\n")

    print(f"Saved {len(scored_items)} active scored items to {OUT_JSONL}")
    print(f"\nDecision Summary across {len(scored_items)} Active Items:")
    print(f"  - SHORTLIST: {decision_counts['SHORTLIST']}")
    print(f"  - WATCH    : {decision_counts['WATCH']}")
    print(f"  - IGNORE   : {decision_counts['IGNORE']}")

    # Render Markdown Matrix
    md_lines = [
        f"# Active Watchlist Purchase Matrix ({len(scored_items)} Verified Active Listings)",
        "",
        "Scored against `config/static_reference_layer.json`, `config/static_scoring_rules.json`, and `data/lf-vendor-risk.json`.",
        "",
        f"**Decision Summary**: `SHORTLIST`: **{decision_counts['SHORTLIST']}** | `WATCH`: **{decision_counts['WATCH']}** | `IGNORE`: **{decision_counts['IGNORE']}**",
        "",
    ]

    lane_headings = {
        "gaming_17_18": "Gaming — 17-18\" Desktop Replacements",
        "workstation_16_touch_or_pro": "RTX Workstations — 14-17\" (incl. Touch & UMA Pro)",
        "macbook_16_high_ram": "High-RAM Apple Silicon — 14-16\" / Desktop",
        "uma_dev_rig": "UMA Dev Rigs & Workstation Outliers",
    }

    for l_key, l_title in lane_headings.items():
        lane_items = [si for si in scored_items if si["lane"] == l_key and si["decision"] == "SHORTLIST"]
        lane_items.sort(key=lambda x: (x["value_per_dollar"] or 0), reverse=True)

        md_lines.append(f"## {l_title} ({len(lane_items)} Shortlisted)")
        md_lines.append("")
        if not lane_items:
            md_lines.append("_No SHORTLIST candidates in this lane._")
            md_lines.append("")
            continue

        md_lines.append("| Tier | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Value/$ | Specs | Price Band |")
        md_lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for si in lane_items[:10]:
            tier_str = si["tier"] or "-"
            plat_str = (si.get("platform") or "ebay").upper()
            vtype_str = (si.get("vendor_type") or "PRIVATE").replace("MARKETPLACE_", "")
            p_str = f"${si['current_price']:,.2f}" if si["current_price"] else "N/A"
            v_str = f"{si['value_per_dollar']:.5f}" if si["value_per_dollar"] else "N/A"
            specs = f"{si['gpu_model']} | {si['vram_gb'] or '?'}GB VRAM | {si['system_ram_gb'] or '?'}GB RAM"
            t_short = (si["title"][:50] + "...") if len(si["title"]) > 53 else si["title"]
            md_lines.append(f"| **{tier_str}** | `{plat_str}` | `{vtype_str}` | [{t_short}]({si['url'] or ''}) | {p_str} | **{si.get('score_0_100', 0)}/100** | **{si['adjusted_score']}** | `{v_str}` | {specs} | `{si['price_band_tag']}` |")
        md_lines.append("")

    watch_items = [si for si in scored_items if si["decision"] == "WATCH"]
    if watch_items:
        watch_items.sort(key=lambda x: (x["adjusted_score"] or 0), reverse=True)
        md_lines.append(f"## Promising Watchlist Candidates ({len(watch_items)} Watch Items)")
        md_lines.append("_Items requiring manual specification check or matching a watchlist criteria._")
        md_lines.append("")
        md_lines.append("| Lane | Platform | Vendor Type | Listing Title | Price (AUD) | Score (0-100) | Adj Score | Watch Reason / Flags |")
        md_lines.append("|---|---|---|---|---|---|---|---|")
        for si in watch_items[:15]:
            plat_str = (si.get("platform") or "ebay").upper()
            vtype_str = (si.get("vendor_type") or "PRIVATE").replace("MARKETPLACE_", "")
            p_str = f"${si['current_price']:,.2f}" if si["current_price"] else "N/A"
            t_short = (si["title"][:45] + "...") if len(si["title"]) > 48 else si["title"]
            reason = si.get("watchlist_reason_flag") or "Needs Spec Check"
            md_lines.append(f"| `{si['lane']}` | `{plat_str}` | `{vtype_str}` | [{t_short}]({si['url'] or ''}) | {p_str} | **{si.get('score_0_100', 0)}/100** | **{si['adjusted_score']}** | `{reason}` |")
        md_lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Saved Purchase Matrix to {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

