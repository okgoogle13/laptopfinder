import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import subprocess

TOKEN_FILE = ".ebay_access_token"
SRL_FILE = "config/static_reference_layer.json"
OUTPUT_FILE = "output/shortlist/rtx5090_search_results.md"

MARKETPLACES = ["EBAY_AU", "EBAY_US", "EBAY_GB"]
QUERIES = [
    "RTX 5090 laptop",
    "RTX 5090 Laptop GPU",
    "RTX 5090 24GB laptop",
    "RTX 5090 laptop open box",
    "RTX 5090 laptop refurbished",
    "RTX 5090 laptop ex demo",
    "RTX 5090 laptop demo",
    "RTX 5090 laptop floor stock",
    "RTX 5090 laptop display model",
    "RTX 5090 laptop used",
    "RTX 5090 laptop clearance"
]

def get_token() -> str:
    env_token = os.environ.get("EBAY_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()
    if not os.path.exists(TOKEN_FILE):
        print("[WARN] Token file missing. Running scripts/authenticate_ebay.sh...", file=sys.stderr)
        try:
            subprocess.run(["bash", "scripts/authenticate_ebay.sh"], check=True, timeout=15)
        except Exception as e:
            print(f"[ERROR] Failed to authenticate: {e}", file=sys.stderr)
            sys.exit(1)
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def fetch_search(token: str, query: str, marketplace: str):
    params = {
        "q": query,
        "limit": "50",
        "fieldgroups": "EXTENDED",
    }
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-EBAY-C-MARKETPLACE-ID", marketplace)
    req.add_header("X-EBAY-C-ENDUSERCTX", "contextualLocation=country=AU,zip=3000")
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (2 ** attempt))
                continue
            if e.code == 401:
                subprocess.run(["bash", "scripts/authenticate_ebay.sh"], check=True, timeout=15)
                token = get_token()
                req.add_header("Authorization", f"Bearer {token}")
                continue
            print(f"[ERROR] HTTP {e.code} for {query} on {marketplace}", file=sys.stderr)
            return None
        except URLError as e:
            time.sleep(5)
    return None

def fetch_item(token: str, item_id: str, marketplace: str):
    encoded_id = urllib.parse.quote(item_id)
    url = f"https://api.ebay.com/buy/browse/v1/item/{encoded_id}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-EBAY-C-MARKETPLACE-ID", marketplace)
    req.add_header("X-EBAY-C-ENDUSERCTX", "contextualLocation=country=AU,zip=3000")
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                time.sleep(10 * (2 ** attempt))
                continue
            if e.code == 401:
                subprocess.run(["bash", "scripts/authenticate_ebay.sh"], check=True, timeout=15)
                token = get_token()
                req.add_header("Authorization", f"Bearer {token}")
                continue
            return None
        except URLError as e:
            time.sleep(5)
    return None

def extract_aspects(item):
    aspects = {}
    for entry in item.get("localizedAspects", []):
        name = entry.get("name")
        val = entry.get("value")
        if name and val:
            aspects[name.lower()] = val.lower()
    return aspects

def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip().lower()

def is_verified(title, description, aspects):
    title = title.lower()
    combined_text = title + " " + description + " " + " ".join([f"{k} {v}" for k, v in aspects.items()])
    
    # Exclude desktops, mini PC, eGPU, GPU-only, case
    excludes = ["desktop", "mini pc", "egpu", "external gpu", "enclosure", "gpu only", "graphics card only", "accessory", "case only"]
    for ex in excludes:
        if ex in title:
            return False, f"Flagged by exclusion rule: {ex}"
            
    # Check for RTX 5090
    if "5090" not in combined_text:
        return False, "5090 not explicitly mentioned"
        
    # Is it a laptop?
    if "laptop" not in combined_text and aspects.get("type", "") != "laptop":
        return False, "Does not appear to be a laptop"
        
    # Check for 24GB
    has_24gb = "24gb" in combined_text or "24 gb" in combined_text
    
    # Check for exact 'RTX 5090 Laptop GPU' phrasing or equivalent
    has_laptop_gpu = "laptop gpu" in combined_text or "mobile" in combined_text
    
    if has_24gb and "5090" in combined_text:
        return True, "Verified 24GB RTX 5090"
    
    return False, "Needs Verification (Lacks explicit 24GB or Laptop GPU wording)"

def load_exchange_rates():
    with open(SRL_FILE, "r") as f:
        srl = json.load(f)
    return srl.get("currency_normalization", {})

def main():
    token = get_token()
    os.makedirs("output/shortlist", exist_ok=True)
    
    rates_config = load_exchange_rates()
    rates = rates_config.get("exchange_rates_to_aud", {"AUD": 1.0, "USD": 1.55, "GBP": 1.98})
    gst_rate = rates_config.get("au_gst_rate", 0.10)
    
    dedup = {}
    
    print("Searching marketplaces...")
    for market in MARKETPLACES:
        for q in QUERIES:
            print(f"  {market}: {q}")
            res = fetch_search(token, q, market)
            if not res or "itemSummaries" not in res:
                continue
            for item in res["itemSummaries"]:
                iid = item.get("itemId")
                # Strip legacy v1|... prefix if needed, but Browse API returns full ID
                if iid not in dedup:
                    dedup[iid] = {"market": market, "summary": item}

    print(f"Found {len(dedup)} unique items. Fetching details...")
    
    results_verified = []
    results_needs_verif = []
    
    for iid, data in dedup.items():
        market = data["market"]
        item = fetch_item(token, iid, market)
        if not item:
            print(f"  Failed to fetch {iid}")
            continue
            
        title = item.get("title", "")
        desc = strip_html(item.get("description", ""))
        aspects = extract_aspects(item)
        
        # Determine Status
        verified, reason = is_verified(title, desc, aspects)
        
        # Pricing and shipping
        price_val = float(item.get("price", {}).get("value", 0))
        currency = item.get("price", {}).get("currency", "AUD")
        
        shipping_val = 0.0
        shipping_currency = "AUD"
        for option in item.get("shippingOptions", []):
            cost = option.get("shippingCost", {})
            if cost.get("value"):
                shipping_val = float(cost.get("value"))
                shipping_currency = cost.get("currency")
                break
                
        # Exchange rate conversion
        price_aud = price_val * rates.get(currency, 1.0)
        shipping_aud = shipping_val * rates.get(shipping_currency, 1.0)
        
        # Est Landed Cost
        landed_aud = price_aud + shipping_aud
        # apply GST if >1000 AUD and not already applied by eBay global shipping program
        if landed_aud > 1000 and market != "EBAY_AU":
            has_taxes = len(item.get("taxes", [])) > 0
            if not has_taxes:
                landed_aud *= (1 + gst_rate)
                
        seller = item.get("seller", {})
        
        entry = {
            "title": title,
            "url": item.get("itemWebUrl", ""),
            "id": iid,
            "market": market,
            "price": f"{price_val} {currency}",
            "price_aud": price_aud,
            "landed_aud": landed_aud,
            "condition": item.get("condition", "Unknown"),
            "seller_name": seller.get("username", "Unknown"),
            "seller_feedback": seller.get("feedbackPercentage", "Unknown"),
            "seller_score": seller.get("feedbackScore", "Unknown"),
            "reason": reason
        }
        
        if verified:
            results_verified.append(entry)
        else:
            results_needs_verif.append(entry)
            
        time.sleep(0.5) # rate limit safety

    # Write report
    with open(OUTPUT_FILE, "w") as f:
        f.write("# RTX 5090 Laptop GPU Search Results\n\n")
        f.write(f"Found {len(results_verified)} Verified Listings and {len(results_needs_verif)} Listings Needing Verification.\n\n")
        
        f.write("## 🟢 VERIFIED (RTX 5090 + 24GB Explicitly Confirmed)\n")
        if not results_verified:
            f.write("*None found.*\n")
        for r in sorted(results_verified, key=lambda x: x["landed_aud"]):
            f.write(f"### {r['title']}\n")
            f.write(f"- **URL**: {r['url']}\n")
            f.write(f"- **Price**: {r['price']} (Est. Landed AUD: ${r['landed_aud']:.2f})\n")
            f.write(f"- **Condition**: {r['condition']}\n")
            f.write(f"- **Seller**: {r['seller_name']} ({r['seller_feedback']}% positive, {r['seller_score']} score)\n")
            f.write(f"- **Market**: {r['market']}\n\n")
            
        f.write("\n## 🟡 NEEDS VERIFICATION (Uncertain specs or lacks 24GB mention)\n")
        if not results_needs_verif:
            f.write("*None found.*\n")
        for r in sorted(results_needs_verif, key=lambda x: x["landed_aud"]):
            f.write(f"### {r['title']}\n")
            f.write(f"- **URL**: {r['url']}\n")
            f.write(f"- **Price**: {r['price']} (Est. Landed AUD: ${r['landed_aud']:.2f})\n")
            f.write(f"- **Reason**: {r['reason']}\n")
            f.write(f"- **Market**: {r['market']}\n\n")
            
    print(f"Done. Report written to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
