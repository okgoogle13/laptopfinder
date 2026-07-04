"""eBay API Pipeline Runner.

Fetches structured listings directly from the eBay Browse API, maps them to the
Stage 2 analysis dict format, and runs the decision engine.
"""
import os
import sys
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

from laptopfinder.core import validate
from laptopfinder.decide import decide, load_ref

load_dotenv()

def get_ebay_token() -> str:
    token_path = Path(".ebay_access_token")
    if not token_path.exists():
        raise FileNotFoundError("eBay access token not found. Run scripts/authenticate_ebay.sh first.")
    return token_path.read_text().strip()

def search_ebay(token: str, query: str = "(RTX 4090, RTX 4080, M3 Max, M3 Ultra, Strix Halo)", limit: int = 10) -> list[dict]:
    env = os.environ.get("EBAY_ENVIRONMENT", "production")
    base_url = "https://api.sandbox.ebay.com" if env == "sandbox" else "https://api.ebay.com"
    url = f"{base_url}/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU",
    }
    params = {
        "q": query,
        "filter": "price:[1000..5500],priceCurrency:AUD,itemLocationCountry:AU",
        "category_ids": "175672",  # Laptops & Netbooks
        "limit": str(limit),
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    req = urllib.request.Request(full_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status != 200:
                print(f"Error searching eBay: {resp.status}", file=sys.stderr)
                return []
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("itemSummaries", [])
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        print(f"Error searching eBay: {e.code} {err_body}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error searching eBay: {e}", file=sys.stderr)
        return []

def compute_risk_score(item: dict) -> float:
    """Deterministic risk score replacing LLM heuristic."""
    score = 0.0
    seller = item.get("seller", {})
    fb_pct_raw = seller.get("feedbackPercentage")
    fb_pct = float(fb_pct_raw) if fb_pct_raw is not None else 100.0
    if fb_pct < 97.0:
        score += 1.5
    
    # Check conditions
    cond = item.get("condition", "")
    if cond not in ("USED_EXCELLENT", "NEW", "CERTIFIED_REFURBISHED"):
        score += 1.0
        
    loc = item.get("itemLocation", {})
    if loc.get("country") != "AU":
        score += 1.5
        
    return score



def build_analysis_dict(item: dict) -> dict:
    # 1. Deterministic Extraction from itemSpecifics
    aspects = {}
    for a in item.get("localizedAspects", []):
        name = a.get("name")
        if not name:
            continue
        if "values" in a and a["values"]:
            aspects[name] = a["values"][0]
        elif "value" in a and a["value"] is not None:
            aspects[name] = a["value"]
    
    title = item.get("title", "")
    price_val = item.get("price", {}).get("value")
    price_aud = float(price_val) if price_val is not None else None
    url = item.get("itemWebUrl", "")
    seller_name = item.get("seller", {}).get("username")
    seller_fb_score = item.get("seller", {}).get("feedbackScore", 0)
    seller_fb_perc = item.get("seller", {}).get("feedbackPercentage", 100)
    
    # 2. Field Mapping
    gpu_str = aspects.get("GPU")
    if "4090" in title and not gpu_str:
        gpu_str = "RTX 4090"
    elif "4080" in title and not gpu_str:
        gpu_str = "RTX 4080"
        
    vram_raw = aspects.get("GPU Memory Size") or aspects.get("Video Memory")
    vram_obj = None
    if vram_raw:
        m = re.search(r"(\d+)", vram_raw)
        if m:
            vram_obj = {
                "semantic_value": float(m.group(1)),
                "verbatim_quote": vram_raw,
            }

    cpu_str = aspects.get("Processor")
    ram_str = aspects.get("RAM Size")
    storage_val = aspects.get("SSD Capacity") or aspects.get("Hard Drive Capacity")

    risk_score = compute_risk_score(item)
    
    if seller_fb_score > 500:
        seller_classification = "ESTABLISHED_RESELLER"
    elif seller_fb_score > 10:
        seller_classification = "PRIVATE_ESTABLISHED"
    else:
        seller_classification = "PRIVATE_NEW_OR_UNKNOWN"
    
    analysis = {
        "metadata": {
            "source_platform": "EBAY_AU",
            "listing_url_or_identifier": url,
            "listing_title": title,
            "listing_price_aud": price_aud,
            "seller_name_or_identifier": seller_name,
            "seller_rating_or_profile_signal": f"{seller_fb_score} ({seller_fb_perc}%)",
        },
        "extracted_data": {
            "exact_model_name": aspects.get("Model"),
            "component_category": "SYSTEM",
            "cpu": cpu_str,
            "gpu": gpu_str,
            "ram": ram_str,
            "storage": storage_val,
            "vram_capacity": vram_obj,
            "stated_condition": item.get("condition", ""),
            "shipping_or_pickup_signal": "UNKNOWN",
            "missing_information": {
                "gpu": not bool(gpu_str),
                "vram": not bool(vram_obj),
                "cpu": not bool(cpu_str),
                "ram": not bool(ram_str),
                "storage": not bool(storage_val),
                "condition": not bool(item.get("condition")),
            },
            "total_system_ram": ram_str,
            "egpu_model": None,
            "touchscreen_digitizer": None,
        },
        "analysis": {
            "risk_score": risk_score,
            "risk_flags": [],
            "stated_pickup_location": None,
            "confidence": 1.0,
            "seller_classification": seller_classification,
        },
    }
    return analysis

def main():
    try:
        token = get_ebay_token()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
        
    print("Fetching listings from eBay API...")
    items = search_ebay(token)
    if not items:
        print("No items found.")
        sys.exit(0)
        
    print(f"Found {len(items)} items. Running decision engine...\n")
    
    ref = load_ref()
    exclusion_pattern = ref.get("data_integrity", {}).get("exclusion_regex")
    
    shortlist = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        print(f"[{i}/{len(items)}] Processing: {title[:50]}...")
        analysis_dict = build_analysis_dict(item)
        
        # Enforce Stage 2 invariants: schema validation & data integrity (parts-only exclusion)
        try:
            validate(analysis_dict, "stage2.analysis.schema.json")
        except ValueError as e:
            print(f"     [FIREWALL REJECTED - SCHEMA]: {e}")
            continue

        if exclusion_pattern and re.search(exclusion_pattern, title):
            print("     [FIREWALL REJECTED - DATA INTEGRITY]: Parts-only / salvaged listing detected in title")
            continue
            
        decision = decide(analysis_dict, ref=ref)
        
        if decision["recommended_action"] == "SHORTLIST":
            shortlist.append((decision["llm_index_score"], item, decision, analysis_dict))
            
    # Sort by score descending
    shortlist.sort(key=lambda x: x[0], reverse=True)
    
    print("\n" + "="*80)
    print("🏆 LIVE API SHORTLIST")
    print("="*80)
    for score, item, decision, analysis in shortlist:
        print(f"[{score:02d}] {analysis['metadata']['listing_title']}")
        print(f"     Price: ${analysis['metadata']['listing_price_aud']} | GPU: {analysis['extracted_data']['gpu']} | VRAM: {analysis['extracted_data']['vram_capacity']}")
        print(f"     URL: {analysis['metadata']['listing_url_or_identifier']}\n")

if __name__ == "__main__":
    main()
