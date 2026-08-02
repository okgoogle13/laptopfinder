from laptopfinder.runners.legacy.hunter.api import ebay_get
from laptopfinder.ebay_taxonomy import build_aspect_filter, ebay_category_id

def build_clearance_filter(ref: dict) -> str:
    sellers = ref.get("clearance_sellers", [])
    deals_config = ref.get("deals_config", {})
    price_min_aud = deals_config.get("price_min_aud", 800)
    price_max_aud = deals_config.get("price_max_aud", 8000)
    
    encoded = "|".join(sellers)
    return (
        f"price:[{price_min_aud}..{price_max_aud}],"
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
        "filter": build_clearance_filter(ref),
        "sort": "newlyListed",
        "limit": 50,
        "category_ids": cat_id,
    }
    if af:
        params["aspect_filter"] = af
    data = ebay_get("/buy/browse/v1/item_summary/search", params, token)
    return data.get("itemSummaries") or []
