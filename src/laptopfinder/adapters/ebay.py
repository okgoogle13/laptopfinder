"""
eBay adapter mapping raw Browse/JSONL dicts into generic Listing schema.
"""

from __future__ import annotations

import re
from typing import Any

from laptopfinder.adapters import Listing


def adapt_ebay(raw: dict[str, Any]) -> Listing:
    listing_id = str(raw.get("item_id") or raw.get("itemId") or raw.get("id") or "unknown")
    title = str(raw.get("title") or "")
    seller = str(raw.get("seller_username") or raw.get("seller", {}).get("username") or "unknown_ebay_seller")
    url = str(raw.get("url") or raw.get("itemWebUrl") or f"https://www.ebay.com.au/itm/{listing_id}")

    price_aud = raw.get("current_price") or raw.get("price")
    if price_aud is None and isinstance(raw.get("price"), dict):
        price_aud = float(raw["price"].get("value", 0))
    elif price_aud is not None:
        try:
            price_aud = float(price_aud)
        except (ValueError, TypeError):
            price_aud = None

    is_active = bool(raw.get("is_available", True)) and raw.get("status", "ACTIVE") == "ACTIVE"

    # Condition mapping
    cond_raw = str(raw.get("conditionId") or raw.get("condition") or "")
    cond_map = {
        "1000": "NEW",
        "1500": "OPEN_BOX",
        "2000": "REFURB",
        "2500": "REFURB",
        "3000": "USED",
    }
    condition = cond_map.get(cond_raw, "USED" if "used" in cond_raw.lower() else "UNKNOWN")

    vendor_type = "MARKETPLACE_STORE" if raw.get("is_store") or "store" in seller.lower() else "MARKETPLACE_PRIVATE"

    return Listing(
        platform="ebay",
        listing_id=listing_id,
        title=title,
        url=url,
        vendor_name=seller,
        vendor_type=vendor_type,
        price_aud=price_aud,
        currency_original=raw.get("original_currency", "AUD"),
        is_active=is_active,
        condition=condition,
        gpu=raw.get("gpu_model"),
        vram_gb=raw.get("vram_gb"),
        ram_gb=raw.get("system_ram_gb"),
        cpu_model=raw.get("cpu_model"),
        screen_size_inches=raw.get("screen_inches"),
        touch=bool(raw.get("has_touchscreen") or re.search(r"\btouch\b", title, re.I)),
        paradigm=raw.get("paradigm", "discrete_cuda"),
        connectivities=raw.get("connectivities", []),
        raw_payload=raw,
    )
