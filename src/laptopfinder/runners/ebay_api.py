"""eBay API Pipeline Runner.

Fetches structured listings directly from the eBay Browse API, maps them to the
Stage 2 analysis dict format, applies a lightweight LLM fallback for missing GPU/VRAM facts,
and runs the decision engine.
"""
import os
import sys
import json
from pathlib import Path
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

from laptopfinder.decide import decide

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
        "category_ids": "175672", # Laptops & Netbooks
        "limit": str(limit),
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error searching eBay: {response.status_code} {response.text}", file=sys.stderr)
        return []
    
    return response.json().get("itemSummaries", [])

def compute_risk_score(item: dict) -> float:
    """Deterministic risk score replacing LLM heuristic."""
    score = 0.0
    seller = item.get("seller", {})
    if float(seller.get("feedbackPercentage", 100)) < 97.0:
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
    aspects = {a["name"]: a["values"][0] for a in item.get("localizedAspects", []) if "values" in a}
    
    title = item.get("title", "")
    price_aud = float(item.get("price", {}).get("value", 0.0))
    url = item.get("itemWebUrl", "")
    ships_from_overseas = item.get("itemLocation", {}).get("country") != "AU"
    seller_name = item.get("seller", {}).get("username")
    seller_fb_score = item.get("seller", {}).get("feedbackScore", 0)
    seller_fb_perc = item.get("seller", {}).get("feedbackPercentage", 100)
    
    # 2. Field Mapping
    gpu_str = aspects.get("GPU")
    if "4090" in title and not gpu_str: gpu_str = "RTX 4090"
    elif "4080" in title and not gpu_str: gpu_str = "RTX 4080"
        
    vram_raw = aspects.get("GPU Memory Size") or aspects.get("Maximum Resolution")
    vram_obj = None
    if vram_raw:
        import re
        m = re.search(r'(\d+)', vram_raw)
        if m:
            vram_obj = {
                "semantic_value": float(m.group(1)),
                "verbatim_quote": vram_raw
            }

    cpu_str = aspects.get("Processor")
    ram_str = aspects.get("RAM Size")

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
            "storage": aspects.get("SSD Capacity") or aspects.get("Hard Drive Capacity"),
            "vram_capacity": vram_obj,
            "stated_condition": item.get("condition", ""),
            "shipping_or_pickup_signal": "UNKNOWN",
            "missing_information": {
                "gpu": not bool(gpu_str),
                "vram": not bool(vram_obj),
                "cpu": not bool(cpu_str),
                "ram": not bool(ram_str),
                "storage": False,
                "condition": not bool(item.get("condition"))
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
        }
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
    
    shortlist = []
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] Processing: {item.get('title')[:50]}...")
        analysis_dict = build_analysis_dict(item)
        
        # Load the default static reference layer (ref=None means decide loads it automatically)
        decision = decide(analysis_dict)
        
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
