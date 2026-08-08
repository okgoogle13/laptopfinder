import re

def evaluate_rtx5090(item_summary: dict, item_details: dict) -> dict:
    title = item_summary.get("title", "")
    price_aud = float(item_summary.get("price", {}).get("value", 0))
    url = item_summary.get("itemWebUrl", "")
    item_id = item_summary.get("itemId", "")
    market = item_summary.get("listingMarketplaceId", "EBAY_AU")
    
    desc = item_details.get("description_text", "")
    aspects = item_details.get("aspects", {})
    
    haystack = f"{title} {desc} {' '.join(aspects.values())}".lower()
    
    # 1. Reject Desktops and eGPUs
    if re.search(r"\b(desktop|pc|tower|egpu|enclosure|graphics card only)\b", title, re.I):
        return {"state": "REJECTED", "reason": "Desktop/eGPU/Parts"}
    
    # "laptop" doesn't strictly need to be in the title, but if it's explicitly a desktop card, reject.
    # 2. Extract SKU/MPN
    sku = aspects.get("MPN") or aspects.get("Model")
    
    # 3. Evidence Model
    has_5090 = "5090" in haystack
    has_24gb = "24gb" in haystack
    
    state = "NEEDS_VERIFICATION"
    evidence_source = None
    
    if "rtx 5090" in haystack and has_24gb:
        state = "VERIFIED_LISTING"
        evidence_source = "Text/Specs"
    
    # Exact SKU promotion (Mock list of verified SKUs)
    verified_skus = ["A18-5090", "L7I-5090"]
    if sku in verified_skus:
        state = "VERIFIED_SKU"
        evidence_source = f"SKU {sku}"
        
    # Reject fake Lenovo from pricing (e.g. 5070 Ti)
    if "5070 ti" in haystack and "5090" not in title.lower():
        state = "REJECTED"
        
    # MikePC is reference only. If seller is MikePC and it's $4999, it's just the reference.
    if item_summary.get("seller", {}).get("username") == "mikepc" and price_aud == 4999:
        state = "REJECTED" # or REFERENCE
        
    # Classification
    classification = "WATCH"
    if "area-51" in haystack and state in ["VERIFIED_LISTING", "VERIFIED_SKU"]:
        classification = "ASPIRATIONAL_BUY_CANDIDATE"
    elif state in ["VERIFIED_LISTING", "VERIFIED_SKU"]:
        if price_aud <= 5500:
            classification = "REALISTIC_BUY_CANDIDATE"
        else:
            classification = "OVER_BUDGET"
            
    # Delivery
    shipping = item_summary.get("shippingOptions", [])
    shipping_cost = 0
    landed_cost = price_aud
    cost_status = "OK"
    if not shipping:
        cost_status = "LANDED_COST_INCOMPLETE"
    else:
        # simplified mock calculation
        landed_cost += 50
        
    return {
        "item_id": item_id,
        "url": url,
        "market": market,
        "title": title,
        "sku": sku,
        "state": state,
        "evidence": evidence_source,
        "classification": classification,
        "price_aud": price_aud,
        "landed_cost": landed_cost,
        "cost_status": cost_status,
        "ram": 32, # Mock
        "ssd": "1TB", # Mock
        "seller": item_summary.get("seller", {}).get("username"),
        "end_time": "N/A"
    }

