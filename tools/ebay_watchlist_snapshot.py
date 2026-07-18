"""One-shot eBay Watchlist snapshot → data/pwm/lf-watchlist/watchlist_raw.jsonl

Auth order:
  1. eBay Trading API GetMyeBayBuying (token from .ebay_access_token, site ID 15 = AU).
     Returns None if the token's OAuth scope doesn't cover the Watchlist endpoint,
     in which case we fall through to the session cookie path.
  2. EBAY_SESSION_COOKIE env var — non-committed, injected via op run --env-file=.env --.

Output schema per item (missing fields written as null, never omitted):
  item_id, title, seller_username, current_price, buy_now_price,
  auction_end_time, url, currency, listing_type
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


def harvest_watchlist(html_file: pathlib.Path | None = None, limit: int = 500) -> list[dict]:
    if html_file and html_file.exists():
        html = html_file.read_text(encoding="utf-8", errors="ignore")
        return [_normalize_snapshot_item(i) for i in _extract_items_from_html(html)[:limit]]

    token_path = pathlib.Path(".ebay_access_token")
    token = token_path.read_text().strip() if token_path.exists() else None
    cookie = os.environ.get("EBAY_SESSION_COOKIE")

    if token:
        items = _fetch_via_trading_api(token)
        if items is not None:
            return [_normalize_snapshot_item(i) for i in items[:limit]]

    if cookie:
        return [_normalize_snapshot_item(i) for i in _fetch_via_session_cookie(cookie)[:limit]]

    raise RuntimeError(
        "No auth available: provide --html-file, .ebay_access_token (with watchlist scope) "
        "or set EBAY_SESSION_COOKIE env var"
    )


def _fetch_via_trading_api(token: str, limit: int = 500) -> list[dict] | None:
    """Return list of watchlist items across all pages, or None if scope is insufficient."""
    url = "https://api.ebay.com/ws/api.dll"
    ns = {"e": "urn:ebay:apis:eBLBaseComponents"}
    all_items: list[dict] = []
    page = 1
    total_pages = 1

    while page <= total_pages and len(all_items) < limit:
        per_page = min(200, limit - len(all_items))
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<GetMyeBayBuyingRequest xmlns="urn:ebay:apis:eBLBaseComponents">'
            f"<RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>"
            "<WatchList>"
            "<Include>true</Include>"
            "<SortOrder>WatchlistDateAdded</SortOrder>"
            f"<Pagination><EntriesPerPage>{per_page}</EntriesPerPage><PageNumber>{page}</PageNumber></Pagination>"
            "</WatchList>"
            "</GetMyeBayBuyingRequest>"
        )
        headers = {
            "X-EBAY-API-CALL-NAME": "GetMyeBayBuying",
            "X-EBAY-API-SITEID": "15",
            "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
            "Content-Type": "text/xml",
        }
        try:
            req = urllib.request.Request(url, body.encode(), headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                root = ET.fromstring(resp.read())
        except urllib.error.HTTPError as e:
            print(f"[WARN] Trading API HTTP {e.code} — falling back to session cookie", file=sys.stderr)
            return None

        ack = root.findtext("e:Ack", namespaces=ns)
        if ack not in ("Success", "Warning"):
            errors = root.findall(".//e:ShortMessage", ns)
            for err in errors:
                print(f"[WARN] Trading API: {err.text}", file=sys.stderr)
            return None

        # Parse total pages from first response
        if page == 1:
            total_pages_text = root.findtext(".//e:WatchList/e:PaginationResult/e:TotalNumberOfPages", namespaces=ns)
            if total_pages_text:
                total_pages = int(total_pages_text)
            print(f"[INFO] Trading API: fetching {total_pages} page(s) of watchlist", file=sys.stderr)

        for item in root.findall(".//e:WatchList/e:ItemArray/e:Item", ns):
            all_items.append({
                "item_id": item.findtext("e:ItemID", namespaces=ns),
                "title": item.findtext("e:Title", namespaces=ns),
                "seller_username": item.findtext("e:Seller/e:UserID", namespaces=ns),
                "current_price": _float_or_null(
                    item.findtext("e:SellingStatus/e:CurrentPrice", namespaces=ns)
                ),
                "buy_now_price": _float_or_null(
                    item.findtext("e:BuyItNowPrice", namespaces=ns)
                ),
                "auction_end_time": item.findtext("e:ListingDetails/e:EndTime", namespaces=ns),
                "url": item.findtext("e:ListingDetails/e:ViewItemURL", namespaces=ns),
                "currency": "AUD",
                "listing_type": item.findtext("e:ListingType", namespaces=ns),
            })
        page += 1

    print(f"[INFO] Trading API: fetched {len(all_items)} total watchlist items", file=sys.stderr)
    return all_items



def _fetch_via_session_cookie(cookie: str) -> list[dict]:
    """Scrape Watchlist via browser session cookie using BeautifulSoup."""
    url = "https://www.ebay.com.au/mye/myebay/watchlist"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] Failed to fetch Watchlist HTML: {e}", file=sys.stderr)
        return []

    return _extract_items_from_html(html)


def _extract_items_from_html(html: str) -> list[dict]:
    """Extract watchlist item dicts from raw browser HTML or preloaded state."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("BeautifulSoup is required for HTML parsing. Run: pip install beautifulsoup4 lxml")

    soup = BeautifulSoup(html, "lxml")
    items = []
    
    # 1. Try to extract JSON state (Apollo or Preloaded)
    script_tags = soup.find_all("script")
    state_json_str = None
    for script in script_tags:
        content = script.string
        if content and "window.__PRELOADED_STATE__" in content:
            match = re.search(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});", content)
            if match:
                state_json_str = match.group(1)
                break
        elif content and "window.__APOLLO_STATE__" in content:
            match = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\});", content)
            if match:
                state_json_str = match.group(1)
                break

    if state_json_str:
        try:
            state = json.loads(state_json_str)
            for key, val in state.items():
                if isinstance(val, dict) and "itemId" in val and "title" in val:
                    items.append({
                        "item_id": val.get("itemId"),
                        "title": val.get("title", {}).get("text") if isinstance(val.get("title"), dict) else val.get("title"),
                        "seller_username": val.get("seller", {}).get("username") if isinstance(val.get("seller"), dict) else None,
                        "current_price": _float_or_null(val.get("currentPrice", {}).get("value") if isinstance(val.get("currentPrice"), dict) else None),
                        "buy_now_price": _float_or_null(val.get("buyItNowPrice", {}).get("value") if isinstance(val.get("buyItNowPrice"), dict) else None),
                        "auction_end_time": val.get("endDate"),
                        "url": f"https://www.ebay.com.au/itm/{val.get('itemId')}",
                        "currency": "AUD",
                        "listing_type": val.get("buyingFormat")
                    })
        except Exception:
            pass

    # 2. Fallback to naive DOM scraping if state extraction fails
    if not items:
        for row in soup.find_all("div", class_=re.compile("m-item-list__item")):
            title_el = row.find("a", class_="title")
            price_el = row.find("span", class_="DEFAULT")
            seller_el = row.find("span", class_="seller-name")
            
            if title_el and title_el.get("href"):
                url = title_el.get("href")
                match = re.search(r"/itm/(\d+)", url)
                item_id = match.group(1) if match else None
                title = title_el.get_text(strip=True)
                
                price_str = price_el.get_text(strip=True) if price_el else ""
                price = None
                p_match = re.search(r"([\d,\.]+)", price_str)
                if p_match:
                    price = _float_or_null(p_match.group(1).replace(",", ""))
                
                items.append({
                    "item_id": item_id,
                    "title": title,
                    "seller_username": seller_el.get_text(strip=True) if seller_el else None,
                    "current_price": price,
                    "buy_now_price": price,
                    "auction_end_time": None,
                    "url": url,
                    "currency": "AUD",
                    "listing_type": "FixedPriceItem"
                })

    return items


def _normalize_snapshot_item(raw: dict) -> dict:
    """Normalize raw snapshot item to canonical platform_agnostic_listing and scoring schema."""
    item_id = raw.get("item_id")
    price = _float_or_null(raw.get("current_price") or raw.get("buy_now_price") or raw.get("price"))
    curr = raw.get("currency") or "AUD"
    seller = raw.get("seller_username") or raw.get("vendor_name") or "unknown"

    title = raw.get("title") or ""
    condition = "UNKNOWN"
    title_upper = title.upper()
    if "NEW" in title_upper or "SEALED" in title_upper:
        condition = "NEW"
    elif "REFURB" in title_upper:
        condition = "REFURB"
    elif "OPEN BOX" in title_upper or "OPEN-BOX" in title_upper:
        condition = "OPEN_BOX"
    elif "USED" in title_upper or "PRE-OWNED" in title_upper:
        condition = "USED"

    return {
        # Legacy & score_active_watchlist.py expected fields
        "item_id": item_id,
        "title": title,
        "seller_username": seller,
        "current_price": price,
        "price": price,
        "buy_now_price": _float_or_null(raw.get("buy_now_price") or price),
        "auction_end_time": raw.get("auction_end_time"),
        "url": raw.get("url"),
        "currency": "AUD" if curr == "AUD" else curr,
        "original_currency": curr,
        "original_price": price,
        "listing_type": raw.get("listing_type", "FixedPriceItem"),
        "status": "ACTIVE",
        "is_available": True,
        # Canonical platform_agnostic_listing required schema fields
        "platform": "EBAY",
        "listing_id": str(item_id) if item_id else None,
        "vendor_name": seller,
        "vendor_type": "MARKETPLACE_STORE" if "store" in seller.lower() else "MARKETPLACE_PRIVATE",
        "price_aud": price if curr == "AUD" else price,
        "currency_original": curr,
        "is_active": True,
        "condition": condition,
        "connectivities": raw.get("connectivities", []),
        "paradigm": raw.get("paradigm", "discrete_cuda"),
    }


def _float_or_null(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Snapshot eBay Watchlist to jsonl")
    parser.add_argument(
        "--html-file",
        type=pathlib.Path,
        help="Optional path to locally saved browser HTML source code for watchlist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of watchlist items to fetch (default: 500, was hard-coded to 50)",
    )
    args = parser.parse_args()

    items = harvest_watchlist(html_file=args.html_file, limit=args.limit)
    out = pathlib.Path("data/pwm/lf-watchlist/watchlist_raw.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
    print(f"Wrote {len(items)} items → {out}")


if __name__ == "__main__":
    main()
