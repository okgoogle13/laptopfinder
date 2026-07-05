import os
from laptopfinder.runners.ebay_hunter import ebay_get
from laptopfinder.ebay_taxonomy import build_aspect_filter, ebay_category_id

PRICE_MIN_AUD = int(os.environ.get("EBAY_PRICE_MIN_AUD", "800"))
PRICE_MAX_AUD = int(os.environ.get("EBAY_PRICE_MAX_AUD", "8000"))


def build_clearance_filter(sellers: list[str]) -> str:
    encoded = "|".join(sellers)
    return (
        f"price:[{PRICE_MIN_AUD}..{PRICE_MAX_AUD}],"
        "priceCurrency:AUD,"
        "conditions:{NEW|SELLER_REFURBISHED|CERTIFIED_REFURBISHED},"
        "buyingOptions:{FIXED_PRICE},"
        f"sellers:{{{encoded}}}"
    )


def scan_clearance(token: str, ref: dict) -> list[dict]:
    sellers = ref.get("clearance_sellers", [])
    if not sellers:
        return []
    af = build_aspect_filter(ref)
    cat_id = ebay_category_id(ref)
    params = {
        "q": "laptop",
        "filter": build_clearance_filter(sellers),
        "sort": "newlyListed",
        "limit": 50,
        "category_ids": cat_id,
    }
    if af:
        params["aspect_filter"] = af
    data = ebay_get("/buy/browse/v1/item_summary/search", params, token)
    return data.get("itemSummaries") or []
