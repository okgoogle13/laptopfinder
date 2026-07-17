"""
Scorptec adapter mapping product page or CSV dicts into generic Listing schema.
"""

from __future__ import annotations

import re
from typing import Any

from laptopfinder.adapters import Listing


def adapt_scorptec(raw: dict[str, Any]) -> Listing:
    listing_id = str(raw.get("sku") or raw.get("listing_id") or "unknown")
    title = str(raw.get("name") or raw.get("title") or "")
    url = str(raw.get("url") or f"https://www.scorptec.com.au/product/laptops-&-notebooks/{listing_id}")

    price_aud = None
    if raw.get("price_aud") is not None:
        try:
            price_aud = float(raw["price_aud"])
        except (ValueError, TypeError):
            price_aud = None

    cond_raw = str(raw.get("condition") or "Brand New")
    if "refurb" in cond_raw.lower():
        condition = "REFURB"
    elif "demo" in cond_raw.lower() or "open" in cond_raw.lower():
        condition = "OPEN_BOX"
    else:
        condition = "NEW"

    return Listing(
        platform="scorptec",
        listing_id=listing_id,
        title=title,
        url=url,
        vendor_name="scorptec_au",
        vendor_type="RETAILER",
        price_aud=price_aud,
        currency_original="AUD",
        is_active=bool(raw.get("in_stock", True)),
        condition=condition,
        gpu=raw.get("gpu"),
        vram_gb=raw.get("vram_gb"),
        ram_gb=raw.get("ram_gb"),
        cpu_model=raw.get("cpu_model"),
        screen_size_inches=raw.get("screen_size_inches"),
        touch=bool(raw.get("touch") or re.search(r"\btouch\b", title, re.I)),
        paradigm=raw.get("paradigm", "discrete_cuda"),
        connectivities=raw.get("connectivities", []),
        raw_payload=raw,
    )
