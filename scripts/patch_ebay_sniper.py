import re

with open("src/laptopfinder/runners/ebay_sniper.py", "r") as f:
    content = f.read()

# Add imports
imports = """from urllib.error import URLError, HTTPError
from laptopfinder.adapters.ebay_api import fetch_item, extract_description_text, parse_aspects"""
content = content.replace("from urllib.error import URLError, HTTPError", imports)

# Add evaluate_rtx5090_candidate and run_strategy_rtx5090
new_funcs = """
def evaluate_rtx5090_candidate(token: str, item_summary: dict, marketplace: str) -> dict | None:
    item_id = item_summary.get("itemId")
    if not item_id:
        return None
    clean_id = item_id.split("|")[1] if "|" in item_id else item_id
    try:
        details = fetch_item(token, clean_id, marketplace_id=marketplace)
    except Exception as e:
        print(f"  [ERROR] fetch_item failed for {clean_id}: {e}")
        return None
        
    title = item_summary.get("title", "")
    price_val = float(item_summary.get("price", {}).get("value", 0))
    url = item_summary.get("itemWebUrl", "")
    condition = item_summary.get("condition", "Unknown")
    
    seller_dict = item_summary.get("seller", {})
    seller_info = f"{seller_dict.get('username', 'Unknown')} ({seller_dict.get('feedbackPercentage', '?')}%, {seller_dict.get('feedbackScore', '?')})"
    
    aspects = parse_aspects(details)
    desc = extract_description_text(details)
    
    haystack = f"{title} {desc} {' '.join(str(v) for v in aspects.values())}".lower()
    
    if re.search(r"\\b(desktop|pc|tower|egpu|enclosure|graphics card only)\\b", title, re.I):
        return {"item_id": item_id, "url": url, "marketplace": marketplace, "title": title, "sku": "", "state": "REJECTED", "reason": "Desktop/eGPU/Parts"}
    
    sku = aspects.get("MPN") or aspects.get("Model") or ""
    
    state = "NEEDS_VERIFICATION"
    evidence = ""
    
    has_5090 = "5090" in haystack
    has_24gb = "24gb" in haystack
    
    if "5070 ti" in haystack and "5090" not in title.lower():
        return {"item_id": item_id, "url": url, "marketplace": marketplace, "title": title, "sku": sku, "state": "REJECTED", "reason": "Lenovo 'from' pricing"}
        
    if "rtx 5090" in haystack and has_24gb:
        state = "VERIFIED_LISTING"
        evidence = "Text/Specs"
    
    verified_skus = ["A18-5090", "L7I-5090"]
    if sku in verified_skus:
        state = "VERIFIED_SKU"
        evidence = f"SKU {sku}"
    
    if seller_dict.get("username", "").lower() == "mikepc" and price_val == 4999:
        return {"item_id": item_id, "url": url, "marketplace": marketplace, "title": title, "sku": sku, "state": "REJECTED", "reason": "MikePC Reference"}
        
    shipping_opts = item_summary.get("shippingOptions", [])
    shipping_cost = 0.0
    cost_status = "LANDED_COST_INCOMPLETE"
    if shipping_opts:
        try:
            shipping_cost = float(shipping_opts[0].get("shippingCost", {}).get("value", 0))
            cost_status = "OK"
        except (TypeError, ValueError):
            pass
            
    landed_cost = price_val + shipping_cost if cost_status == "OK" else price_val
    
    classification = "WATCH"
    if "area-51" in haystack and state in ["VERIFIED_LISTING", "VERIFIED_SKU"]:
        classification = "ASPIRATIONAL_BUY_CANDIDATE"
    elif state in ["VERIFIED_LISTING", "VERIFIED_SKU"]:
        if landed_cost <= 5500:
            classification = "REALISTIC_BUY_CANDIDATE"
        else:
            classification = "OVER_BUDGET"
            
    return {
        "item_id": item_id, "url": url, "marketplace": marketplace, "title": title,
        "sku": sku, "state": state, "evidence": evidence, "condition": condition,
        "price": price_val, "shipping": shipping_cost, "tax": 0, "landed_cost": landed_cost,
        "cost_status": cost_status, "ram": "Unknown", "ssd": "Unknown",
        "seller": seller_info, "returns": "Unknown", "delivery": "Unknown",
        "end_time": "Unknown", "risk_flags": "", "classification": classification,
        "action": "SHORTLIST_5090", "price_aud": price_val
    }

def run_strategy_rtx5090(token: str, seen: set[str], srl: dict, dry_run: bool = False) -> tuple[set[str], list[dict]]:
    print("[SNIPER] Running Strategy RTX 5090...")
    markets = {"EBAY_AU": "AU", "EBAY_US": "US", "EBAY_GB": "GB"}
    hits = []
    
    for market, country in markets.items():
        print(f"  Querying {market}...")
        params = {
            "q": "RTX 5090 laptop",
            "category_ids": "175672",
            "sort": "newlyListed",
            "limit": "20",
            "fieldgroups": "EXTENDED",
        }
        headers = {"X-EBAY-C-MARKETPLACE-ID": market}
        data = execute_browse_query(token, params, headers)
        if not data or "itemSummaries" not in data:
            continue
            
        for item in data["itemSummaries"]:
            item_id = item.get("itemId")
            if not item_id or item_id in seen:
                continue
                
            res = evaluate_rtx5090_candidate(token, item, market)
            if res:
                hits.append(res)
                if res["state"] in ["VERIFIED_LISTING", "VERIFIED_SKU"]:
                    msg = (
                        "🚨 [RTX 5090] Verified Match!\\n"
                        f"📦 {res['title']}\\n"
                        f"💰 Price: ${res['landed_cost']} AUD\\n"
                        f"🔗 {res['url']}"
                    )
                    send_imessage(TARGET_APPLE_ID, msg, dry_run=dry_run)
            seen.add(item_id)
            
    return seen, hits
"""
content = content.replace("def write_outputs(decisions: list[dict]) -> None:", new_funcs + "\n\ndef write_outputs(decisions: list[dict]) -> None:")

# Update write_outputs
old_write = """def write_outputs(decisions: list[dict]) -> None:
    \"\"\"Write sweep results to standard output paths.\"\"\"
    import os
    os.makedirs("output/decisions", exist_ok=True)
    os.makedirs("output/shortlist", exist_ok=True)
    with open(OUTPUT_DECISIONS, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)
    shortlist = [d for d in decisions if d.get("action") == "SHORTLIST"]
    lines = ["# Shortlist", f"_{len(shortlist)} of {len(decisions)} hits_", ""]
    for d in shortlist:
        lines.append(f"- **{d['title']}** — ${d['price_aud']} AUD  ")
        lines.append(f"  {d['url']}")
    with open(OUTPUT_SHORTLIST, "w", encoding="utf-8") as f:
        f.write("\\n".join(lines) + "\\n")"""

new_write = """def write_outputs(decisions: list[dict]) -> None:
    \"\"\"Write sweep results to standard output paths.\"\"\"
    import os
    os.makedirs("output/decisions", exist_ok=True)
    os.makedirs("output/shortlist", exist_ok=True)
    with open(OUTPUT_DECISIONS, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)
        
    lines = []
    
    rtx_hits = [d for d in decisions if d.get("action") == "SHORTLIST_5090"]
    if rtx_hits:
        lines.append("# RTX 5090 Search Results\\n")
        
        sections = {
            "ASPIRATIONAL_BUY_CANDIDATE": "1. Alienware 18 Area-51 aspirational matches",
            "REALISTIC_BUY_CANDIDATE": "2. Realistic candidates versus the AU$4,999 MikePC Legion reference",
            "COMPARE": "3. Verified 64GB candidates",
            "WATCH": "5. Auctions/listings ending within 24 hours",
            "OVER_BUDGET": "6. Over-budget inventory",
            "NEEDS_VERIFICATION": "7. Needs Verification",
            "REJECTED": "8. Rejection summary and coverage gaps"
        }
        
        for classification, header in sections.items():
            matches = [d for d in rtx_hits if d.get("classification") == classification or d.get("state") == classification]
            if not matches:
                continue
            lines.append(f"## {header}")
            for d in matches:
                # item ID | listing URL | marketplace | title | exact SKU/MPN | evidence state | exact GPU/VRAM evidence | condition | item price | shipping | tax/imports | total landed AUD or reason incomplete | RAM/slots/max | SSD | seller feedback/count | returns | delivery evidence | end time | risk flags | classification
                lines.append(f"### {d.get('title')}")
                lines.append(f"- **URL**: {d.get('url')}")
                lines.append(f"- **State**: {d.get('state')} ({d.get('classification', '')})")
                lines.append(f"- **Evidence**: {d.get('evidence', '')}")
                lines.append(f"- **Price**: {d.get('price')} (Landed: {d.get('landed_cost')} - {d.get('cost_status')})")
                lines.append(f"- **Seller**: {d.get('seller')}")
                lines.append(f"- **Market**: {d.get('marketplace')}\\n")
                
    shortlist = [d for d in decisions if d.get("action") == "SHORTLIST"]
    if shortlist:
        lines.extend(["# Shortlist", f"_{len(shortlist)} of {len(decisions)} hits_", ""])
        for d in shortlist:
            lines.append(f"- **{d['title']}** — ${d['price_aud']} AUD  ")
            lines.append(f"  {d['url']}")
            
    with open(OUTPUT_SHORTLIST, "w", encoding="utf-8") as f:
        f.write("\\n".join(lines) + "\\n")"""

content = content.replace(old_write, new_write)

# Add to main_loop
content = content.replace("seen, hits_a = run_strategy_flagship", "seen, hits_rtx = run_strategy_rtx5090(token, seen, srl, dry_run=dry_run)\n        seen, hits_a = run_strategy_flagship")
content = content.replace("write_outputs(hits_a + hits_b)", "write_outputs(hits_rtx + hits_a + hits_b)")

with open("src/laptopfinder/runners/ebay_sniper.py", "w") as f:
    f.write(content)
