#!/usr/bin/env python3
"""
eBay Feed API pre-cacher.
Downloads hourly category item snapshots and stores as local JSONL for O(1) sniper lookups.

Usage:
    .venv/bin/python scripts/ebay_feed_cache.py --category 175672
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path


CACHE_DIR = Path("data/feed_cache")


def write_feed_cache(items: list[dict], cache_dir: str, date_str: str, category: str) -> Path:
    out_dir = Path(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"items_{category}_{date_str}.jsonl"
    with out_path.open("w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
    return out_path


def load_feed_cache(cache_dir: str) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    for path in sorted(Path(cache_dir).glob("items_*.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                item_id = item.get("itemId")
                if item_id:
                    cache[item_id] = item
    return cache


def fetch_feed_snapshot(token: str, category: str, marketplace: str = "EBAY_AU") -> list[dict]:
    url = f"https://api.ebay.com/buy/feed/v1_beta/item?feed_scope=NEWLY_LISTED&category_id={category}&marketplace_id={marketplace}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("itemSummaries") or []
    except Exception as exc:
        print(f"[FEED] fetch failed: {exc}", file=sys.stderr)
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache eBay Feed API snapshot locally")
    parser.add_argument("--category", default="175672")
    parser.add_argument("--cache-dir", default=str(CACHE_DIR))
    args = parser.parse_args()

    token = os.environ.get("EBAY_ACCESS_TOKEN") or ""
    if not token:
        sys.exit("[FEED] EBAY_ACCESS_TOKEN not set — run make authenticate-ebay first")

    items = fetch_feed_snapshot(token, args.category)
    if not items:
        print("[FEED] No items returned from Feed API (scope may not be granted yet)")
        return

    today = date.today().isoformat()
    path = write_feed_cache(items, args.cache_dir, date_str=today, category=args.category)
    print(f"[FEED] {len(items)} items cached → {path}")


if __name__ == "__main__":
    main()
