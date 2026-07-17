"""Refresh watchlist items from eBay Browse API to capture live AUD cost and original currency.

Loops over data/pwm/lf-watchlist/watchlist_raw.jsonl (or specified input path),
queries eBay Browse API (getItem) for each item_id using OAuth credentials,
multiplies price by exchange_rates_to_aud in static_reference_layer.json,
and overwrites the JSONL with normalized AUD figures and source currency metadata.

Run:
    op run --env-file=.env -- .venv/bin/python scripts/refresh_watchlist_currency.py
    op run --env-file=.env -- .venv/bin/python scripts/refresh_watchlist_currency.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path

# Ensure src/ directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from laptopfinder.decide import load_ref
from laptopfinder.runners.legacy.hunter.api import get_ebay_token, get_item, log


def normalize_item_currency(row: dict, token: str, ref: dict, dry_run: bool = False) -> dict:
    """Query Browse API for item_id and update currency/price fields plus availability status."""
    item_id = str(row.get("item_id", "")).strip()
    if not item_id:
        return row

    # eBay Browse API getItem accepts REST syntax: v1|legacy_id|0
    rest_id = item_id if item_id.startswith("v1|") else f"v1|{item_id}|0"

    detail = None
    try:
        detail = get_item(token, rest_id)
    except RuntimeError as exc:
        # If rest_id fails and it was prefixed, try bare item_id fallback
        if rest_id != item_id:
            try:
                detail = get_item(token, item_id)
            except RuntimeError as fallback_exc:
                log(f"[STATUS] {item_id} ENDED_OR_SOLD (getItem failed: {fallback_exc})")
        else:
            log(f"[STATUS] {item_id} ENDED_OR_SOLD (getItem failed: {exc})")

    if not detail:
        # Mark as ended/sold if item cannot be retrieved from live Browse API
        row["is_available"] = False
        row["status"] = "ENDED_OR_SOLD"
        return row

    # Check availability status from returned detail
    is_avail = True
    status_str = "ACTIVE"
    avail_list = detail.get("estimatedAvailabilities", [])
    if isinstance(avail_list, list) and avail_list:
        first_avail = avail_list[0]
        if first_avail.get("estimatedAvailableQuantity", 1) == 0 or first_avail.get("availabilityThresholdType") == "OUT_OF_STOCK":
            is_avail = False
            status_str = "OUT_OF_STOCK"

    row["is_available"] = is_avail
    row["status"] = status_str

    price_block = detail.get("price") or {}
    raw_val_str = price_block.get("value")
    price_curr = price_block.get("currency", "AUD").upper()

    if raw_val_str is not None:
        try:
            raw_val = float(raw_val_str)
            rates = ref.get("currency_normalization", {}).get("exchange_rates_to_aud", {"AUD": 1.0})
            rate = rates.get(price_curr, 1.0)
            converted_aud = round(raw_val * rate, 2)

            row["current_price"] = converted_aud
            if "price" in row:
                row["price"] = converted_aud
            row["currency"] = "AUD"
            row["original_currency"] = price_curr
            row["original_price"] = raw_val
            if price_curr != "AUD":
                log(f"[CONVERTED] {item_id}: {raw_val} {price_curr} -> ${converted_aud} AUD (rate {rate})")
        except ValueError:
            log(f"[WARN] Unparseable price value '{raw_val_str}' for item {item_id}")

    # Optionally refresh title and URL if provided by live API
    if detail.get("title"):
        row["title"] = detail["title"]
    if detail.get("itemWebUrl"):
        row["url"] = detail["itemWebUrl"]

    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh watchlist currency and prices via eBay Browse API.")
    parser.add_argument(
        "--input",
        default="data/pwm/lf-watchlist/watchlist_raw.jsonl",
        help="Path to raw watchlist JSONL (default: data/pwm/lf-watchlist/watchlist_raw.jsonl)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run API lookups without writing updated JSONL to disk",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Seconds to sleep between API requests (default: 0.2s)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: Input file not found at {in_path}", file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else in_path

    ref = load_ref()
    try:
        token = get_ebay_token()
    except Exception as exc:
        print(f"ERROR acquiring eBay token: {exc}\nEnsure you run via: op run --env-file=.env -- .venv/bin/python ...", file=sys.stderr)
        return 1

    rows: list[dict] = []
    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"Processing {len(rows)} watchlist items from {in_path}...")
    updated_rows: list[dict] = []

    for idx, row in enumerate(rows, 1):
        item_id = row.get("item_id", "unknown")
        print(f"[{idx}/{len(rows)}] Refreshing item {item_id}...", end="\r")
        updated = normalize_item_currency(row, token, ref, dry_run=args.dry_run)
        updated_rows.append(updated)
        if args.delay > 0 and idx < len(rows):
            time.sleep(args.delay)

    print(f"\nCompleted live API refresh for {len(updated_rows)} items.")

    active_cnt = sum(1 for r in updated_rows if r.get("status") == "ACTIVE")
    oos_cnt = sum(1 for r in updated_rows if r.get("status") == "OUT_OF_STOCK")
    ended_cnt = sum(1 for r in updated_rows if r.get("status") == "ENDED_OR_SOLD")
    converted_cnt = sum(1 for r in updated_rows if r.get("original_currency") and r.get("original_currency") != "AUD")

    print(f"\n=== Availability & Currency Summary ===")
    print(f"  - Active Available Listings : {active_cnt}")
    print(f"  - Out of Stock Listings     : {oos_cnt}")
    print(f"  - Ended / Sold / 404        : {ended_cnt}")
    print(f"  - Foreign Currency Converted: {converted_cnt}")
    print("=======================================\n")

    if args.dry_run:
        print(f"[DRY-RUN] Would write {len(updated_rows)} rows to {out_path}")
        return 0

    # Atomic write
    tmp_path = out_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        for r in updated_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_path.replace(out_path)
    print(f"Successfully saved updated watchlist to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
