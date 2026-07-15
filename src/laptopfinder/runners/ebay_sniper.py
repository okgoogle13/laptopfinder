"""eBay AU Active Sniper — token-free, low-latency local hardware acquisition.

Runs continuously or in single-pass dry-run mode to detect underpriced flagship
and high-capacity UMA hardware on eBay AU, alerting the buyer via macOS iMessage.
Enforces flat Software 2.0 invariants: zero LLM tokens, zero scraping, dynamic
static_reference_layer.json gating, and clean POSIX daemon compatibility.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

SEEN_FILE = "data/seen_sniper_items.json"
SRL_FILE = "config/static_reference_layer.json"
TOKEN_FILE = ".ebay_access_token"
OUTPUT_DECISIONS = "output/decisions/latest_decisions.json"
OUTPUT_SHORTLIST = "output/shortlist/latest_shortlist.md"
TARGET_APPLE_ID = os.environ.get("SNIPER_APPLE_ID", "your_apple_id@icloud.com")

DEFAULT_FLAGSHIP_KEYWORDS = [
    "RTX 5090", "RTX 4090", "RTX 3080 TI",
    "RTX 5000 ADA", "M3 MAX", "M3 ULTRA", "STRIX HALO"
]

DEFAULT_LOCAL_MODELS = [
    "RTX 4080", "RTX 3080", "RTX 4070 TI", "RX 7900"
]


def normalize(s: str) -> str:
    """Strip whitespace and convert to uppercase for standardized substring matching."""
    return s.replace(" ", "").upper()


def load_seen_state() -> set[str]:
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            elif isinstance(data, dict) and "seen_items" in data:
                return set(data["seen_items"].keys())
            return set()
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_state(seen: set[str], dry_run: bool = False) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would save {len(seen)} seen item IDs to {SEEN_FILE}")
        return
    tmp_file = SEEN_FILE + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(SEEN_FILE)), exist_ok=True)
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2)
    os.replace(tmp_file, SEEN_FILE)


def get_token() -> str | None:
    env_token = os.environ.get("EBAY_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()
    if not os.path.exists(TOKEN_FILE):
        print("[WARN] Token file missing. Running scripts/authenticate_ebay.sh...", file=sys.stderr)
        try:
            subprocess.run(["bash", "scripts/authenticate_ebay.sh"], check=True, timeout=15)
        except Exception as e:
            print(f"[ERROR] Failed to authenticate: {e}", file=sys.stderr)
            return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def send_imessage(target_id: str, text: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"[DRY-RUN] iMessage to {target_id}:\n{text}")
        return True
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{target_id}" of targetService
        send "{safe_text}" to targetBuddy
    end tell
    '''
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            timeout=10
        )
        return True
    except Exception as e:
        print(f"[ERROR] iMessage delivery failed: {e}", file=sys.stderr)
        try:
            subprocess.run([
                "osascript", "-e",
                'display notification "eBay hit found but iMessage failed!" '
                'with title "LaptopFinder Sniper"'
            ], check=False, timeout=5)
        except Exception:
            pass
        return False


def execute_browse_query(token: str, params: dict, headers: dict | None = None) -> dict | None:
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                sleep_time = 60 * (2 ** attempt)
                print(f"[WARN] HTTP 429 Rate Limit Exceeded. Backing off for {sleep_time}s...", file=sys.stderr)
                time.sleep(sleep_time)
                continue
            if e.code == 401:
                print("[ERROR] 401 Unauthorized: eBay token expired. Attempting auto-refresh...", file=sys.stderr)
                try:
                    subprocess.run(["bash", "scripts/authenticate_ebay.sh"], check=True, timeout=15)
                except Exception as refresh_err:
                    print(f"[ERROR] Auto-refresh failed: {refresh_err}", file=sys.stderr)
                return None
            print(f"[ERROR] HTTP error searching eBay: {e.code}", file=sys.stderr)
            return None
        except URLError as e:
            print(f"[WARN] Network error: {e.reason}. Retrying in 10s...", file=sys.stderr)
            time.sleep(10)
    return None


def apply_firewall(title: str, srl: dict) -> bool:
    """Return True if item passes data integrity firewall, False if excluded."""
    exclusion_pattern = srl.get("data_integrity", {}).get("exclusion_regex")
    if not exclusion_pattern:
        exclusion_pattern = r"(?i)(bare shell|missing motherboard|screen only|no mobile-gpu|no core|chassis only|parts only|read description|junk|as-is|bare board)"
    if re.search(exclusion_pattern, title):
        return False
    return True


def write_outputs(decisions: list[dict]) -> None:
    """Write sweep results to standard output paths."""
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
        f.write("\n".join(lines) + "\n")


def run_strategy_flagship(token: str, seen: set[str], srl: dict, keywords: list[str], dry_run: bool = False) -> tuple[set[str], list[dict]]:
    print("[SNIPER] Running Strategy A: Flagship Sweep (National)...")
    cfg = srl.get("sniper_config", {})
    category_id = srl.get("ebay_aspect_filter", {}).get("category_id", "175672")
    limit = str(cfg.get("strategy_a_limit", 20))
    params = {
        "q": f"({', '.join(keywords)})",
        "category_ids": category_id,
        "filter": "itemLocationCountry:AU,priceCurrency:AUD",
        "sort": "newlyListed",
        "limit": limit,
        "fieldgroups": "EXTENDED",
    }
    data = execute_browse_query(token, params)
    if not data or "itemSummaries" not in data:
        print("  -> No items returned for Strategy A.")
        return seen, []

    hits: list[dict] = []
    for item in data["itemSummaries"]:
        item_id = item.get("itemId")
        if not item_id or item_id in seen:
            continue

        title = item.get("title", "")
        if not apply_firewall(title, srl):
            print(f"  [FIREWALL REJECTED] {title[:60]}")
            continue

        title_norm = normalize(title)
        if not any(normalize(k) in title_norm for k in keywords):
            continue

        price = item.get("price", {}).get("value")
        url = item.get("itemWebUrl", "")
        msg = (
            "🚨 [Unicorn] Match!\n"
            f"📦 {title}\n"
            f"💰 Price: ${price} AUD\n"
            f"🔗 {url}"
        )
        print(f"  [HIT] {title[:60]} -> ${price} AUD")
        send_imessage(TARGET_APPLE_ID, msg, dry_run=dry_run)
        seen.add(item_id)
        hits.append({"item_id": item_id, "title": title, "price_aud": price, "url": url, "action": "SHORTLIST", "strategy": "A"})

    return seen, hits


def run_strategy_local(token: str, seen: set[str], srl: dict, models: list[str], dry_run: bool = False) -> tuple[set[str], list[dict]]:
    cfg = srl.get("sniper_config", {})
    postal_code = cfg.get("local_pickup_postal_code", "3070")
    radius_km = cfg.get("local_pickup_radius_km", 100)
    category_id = srl.get("ebay_aspect_filter", {}).get("category_id", "175672")
    print(f"[SNIPER] Running Strategy B: Local Algorithmic Sniper (Melbourne VIC {postal_code})...")
    headers = {
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU",
        "X-EBAY-C-ENDUSERCTX": f"contextualLocation=country=AU,zip={postal_code}",
    }
    params = {
        "q": f"({', '.join(models)})",
        "category_ids": category_id,
        "filter": (
            "pickupCountry:AU,"
            f"pickupPostalCode:{postal_code},"
            f"pickupRadius:{radius_km},"
            "pickupRadiusUnit:km,"
            "buyingOptions:{FIXED_PRICE|BEST_OFFER},"
            "sellerAccountTypes:{INDIVIDUAL}"
        ),
        "sort": "newlyListed",
        "fieldgroups": "EXTENDED",
    }
    data = execute_browse_query(token, params, headers)
    if not data or "itemSummaries" not in data:
        print("  -> No items returned for Strategy B.")
        return seen, []

    targets = srl.get("target_gpus", {})
    hits: list[dict] = []

    for item in data["itemSummaries"]:
        item_id = item.get("itemId")
        if not item_id or item_id in seen:
            continue

        title = item.get("title", "")
        if not apply_firewall(title, srl):
            print(f"  [FIREWALL REJECTED] {title[:60]}")
            continue

        price_val = item.get("price", {}).get("value")
        try:
            price = float(price_val)
        except (TypeError, ValueError):
            continue

        title_norm = normalize(title)
        matched_model = None
        for model in models:
            if normalize(model) in title_norm:
                matched_model = model
                break
        if not matched_model:
            continue

        floor = targets.get(matched_model, {}).get("observed_au_price_min_aud")
        try:
            floor_val = float(floor) if floor is not None else None
        except (TypeError, ValueError):
            floor_val = None

        margin = srl.get("sniper_config", {}).get("local_price_margin_factor", 1.10)
        if floor_val is None or price > floor_val * margin:
            continue  # ignore unless at or below ~110% of observed floor

        url = item.get("itemWebUrl", "")
        msg = (
            "🎯 [Sniper] Local Match!\n"
            f"📦 {title}\n"
            f"💰 Price: ${price} AUD (Floor: ${floor_val})\n"
            f"🔗 {url}"
        )
        print(f"  [LOCAL HIT] {title[:60]} -> ${price} AUD (Floor: ${floor_val})")
        send_imessage(TARGET_APPLE_ID, msg, dry_run=dry_run)
        seen.add(item_id)
        hits.append({"item_id": item_id, "title": title, "price_aud": price, "url": url, "action": "SHORTLIST", "strategy": "B", "floor_aud": floor_val})

    return seen, hits


def main_loop(interval_sec: int = 300, dry_run: bool = False, once: bool = False) -> None:
    try:
        with open(SRL_FILE, "r", encoding="utf-8") as f:
            srl = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[ERROR] Could not load SRL file {SRL_FILE}: {e}", file=sys.stderr)
        return

    while True:
        token = get_token()
        if not token:
            if once:
                print("[ERROR] Aborting single-pass sweep due to missing token.", file=sys.stderr)
                break
            print(f"[WARN] No valid token found. Retrying in {interval_sec}s...", file=sys.stderr)
            time.sleep(interval_sec)
            continue

        local_models = list(srl.get("target_gpus", {}).keys()) or DEFAULT_LOCAL_MODELS
        uma_chips = srl.get("uma_platforms", {}).get("chip_patterns", [])
        flagship_keywords = (local_models + uma_chips) or DEFAULT_FLAGSHIP_KEYWORDS

        seen = load_seen_state()
        seen, hits_a = run_strategy_flagship(token, seen, srl, keywords=flagship_keywords, dry_run=dry_run)
        seen, hits_b = run_strategy_local(token, seen, srl, models=local_models, dry_run=dry_run)
        save_seen_state(seen, dry_run=dry_run)
        write_outputs(hits_a + hits_b)

        if once:
            print("[SNIPER] Single-pass sweep completed.")
            break

        print(f"[SNIPER] Sweep completed. Sleeping for {interval_sec} seconds...")
        time.sleep(interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="eBay AU Active Sniper Script")
    parser.add_argument("--dry-run", action="store_true", help="Log matches without modifying state or sending iMessages")
    parser.add_argument("--once", action="store_true", help="Run a single polling cycle and exit")
    parser.add_argument("--test-alert", action="store_true", help="Send a test iMessage alert and exit")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300)")
    args = parser.parse_args()

    if args.test_alert:
        print("Sending synthetic test iMessage alert...")
        success = send_imessage(
            TARGET_APPLE_ID,
            "🎯 EBAY SNIPER TEST ALERT\nIf you received this message, AppleScript iMessage integration is working correctly!",
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)

    main_loop(interval_sec=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()
