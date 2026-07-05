#!/usr/bin/env python3
"""
eBay Finding API sold price baseline.
Queries AU completed/sold listings by GPU keyword and writes median prices to data/sold_baseline/.

Usage:
    .venv/bin/python scripts/ebay_sold_baseline.py --keywords "RTX 3080" "RTX 4090"
    .venv/bin/python scripts/ebay_sold_baseline.py  # uses SRL target_gpus keys
"""
import argparse
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

FINDING_API = "https://svcs.ebay.com/services/search/FindingService/v1"
CATEGORY_ID = "175672"
SRL_PATH = Path("config/static_reference_layer.json")
CACHE_DIR = Path("data/sold_baseline")


def _load_ref() -> dict:
    return json.loads(SRL_PATH.read_text())


def fetch_sold_items(app_id: str, keywords: str, category_id: str = CATEGORY_ID) -> dict:
    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.13.0",
        "SECURITY-APPNAME": app_id,
        "RESPONSE-DATA-FORMAT": "JSON",
        "GLOBAL-ID": "EBAY-AU",
        "categoryId": category_id,
        "keywords": keywords,
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "itemFilter(1).name": "LocatedIn",
        "itemFilter(1).value": "AU",
        "paginationInput.entriesPerPage": "100",
    }
    url = FINDING_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"[SOLD] fetch failed for '{keywords}': {exc}", file=sys.stderr)
        return {}


def parse_sold_items(response: dict) -> list[dict]:
    try:
        results = response["findCompletedItemsResponse"][0]["searchResult"][0]
    except (KeyError, IndexError):
        return []
    if int(results.get("@count", 0)) == 0:
        return []
    items = []
    for item in results.get("item", []):
        try:
            price = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
            title = item["title"][0]
            items.append({"price_aud": price, "title": title})
        except (KeyError, IndexError, ValueError):
            continue
    return items


def compute_baseline(items: list[dict]) -> dict:
    """Accept either parsed items (with price_aud key) or raw eBay item dicts."""
    if not items:
        return {}
    prices = []
    for i in items:
        if "price_aud" in i:
            prices.append(i["price_aud"])
        else:
            try:
                prices.append(float(i["sellingStatus"][0]["currentPrice"][0]["__value__"]))
            except (KeyError, IndexError, ValueError):
                continue
    if not prices:
        return {}
    return {
        "count": len(prices),
        "median_aud": statistics.median(prices),
        "min_aud": min(prices),
        "max_aud": max(prices),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="eBay sold price baseline via Finding API")
    parser.add_argument("--keywords", nargs="+", help="GPU keywords to query (default: SRL target_gpus keys)")
    parser.add_argument("--category", default=CATEGORY_ID)
    parser.add_argument("--out-dir", default=str(CACHE_DIR))
    args = parser.parse_args()

    app_id = os.environ.get("EBAY_APP_ID") or ""
    if not app_id:
        sys.exit("[SOLD] EBAY_APP_ID not set — copy .env.example to .env and fill in credentials")

    keywords = args.keywords or list(_load_ref().get("target_gpus", {}).keys())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for kw in keywords:
        response = fetch_sold_items(app_id, f"laptop {kw}", args.category)
        items = parse_sold_items(response)
        baseline = compute_baseline(items)
        if baseline:
            row = {"keyword": kw, **baseline}
            results.append(row)
            print(f"[SOLD] {kw}: median=${baseline['median_aud']:.0f} AUD  n={baseline['count']}")
        else:
            print(f"[SOLD] {kw}: no sold listings found")

    if results:
        today = date.today().isoformat()
        out_path = out_dir / f"baseline_{today}.jsonl"
        with out_path.open("w") as f:
            for row in results:
                f.write(json.dumps(row) + "\n")
        print(f"[SOLD] baseline written → {out_path}")


if __name__ == "__main__":
    main()
