"""
Ad hoc, single-listing eBay Browse API lookup.

Standalone CLI: given one eBay AU listing URL, mints an OAuth application
token (client_credentials) and fetches item detail via getItem. Used by the
ebay-market-analyzer skill to ground specs/asking-price before comps research.

    python src/laptopfinder/adapters/ebay_api.py "<EBAY_URL>" [--json]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys

import requests

# Optional: bs4 for stripping HTML tags out of the `description` field.
# Falls back to a regex tag-stripper when absent (same pattern as scrape_benchmark.py).
try:
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    _BS4_OK = False

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
ITEM_URL = "https://api.ebay.com/buy/browse/v1/item/v1|{item_id}|0"
BROWSE_SCOPE = "https://api.ebay.com/oauth/api_scope"

ITEM_ID_RE = re.compile(r"/itm/(?:[^/]+/)?(\d{9,13})(?:[/?]|$)")


class EbayApiError(RuntimeError):
    pass


def get_access_token() -> str:
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EbayApiError(
            "Missing EBAY_CLIENT_ID / EBAY_CLIENT_SECRET. "
            "Copy .env.example to .env, fill in your eBay app credentials, "
            "and run this via `op run --env-file=.env -- python ...` "
            "or otherwise export both vars first."
        )

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials", "scope": BROWSE_SCOPE}

    try:
        resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)
    except requests.RequestException as exc:
        raise EbayApiError(f"OAuth token request failed: {exc}") from exc

    if resp.status_code != 200:
        raise EbayApiError(f"OAuth token request failed (HTTP {resp.status_code}): {resp.text}")

    token = resp.json().get("access_token")
    if not token:
        raise EbayApiError(f"OAuth response missing access_token: {resp.text}")
    return token


def extract_item_id(url: str) -> str:
    match = ITEM_ID_RE.search(url)
    if not match:
        raise EbayApiError(
            f"Could not extract an eBay item ID (9-13 digits) from URL: {url}"
        )
    return match.group(1)


def fetch_item(token: str, item_id: str, marketplace_id: str = "EBAY_AU") -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
    }
    url = ITEM_URL.format(item_id=item_id)
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as exc:
        raise EbayApiError(f"getItem request failed: {exc}") from exc

    if resp.status_code != 200:
        raise EbayApiError(f"getItem failed (HTTP {resp.status_code}): {resp.text}")

    return resp.json()


def parse_aspects(item: dict) -> dict:
    aspects = {}
    for entry in item.get("localizedAspects") or []:
        name = entry.get("name")
        value = entry.get("value")
        if name and value:
            aspects[name] = value
    return aspects


def strip_html(html: str) -> str:
    """Plain text from the getItem `description` field (rich HTML)."""
    if not html:
        return ""
    if _BS4_OK:
        return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def extract_description_text(item: dict) -> str:
    """Prefer the full `description` (HTML, stripped); fall back to `shortDescription`."""
    stripped = strip_html(item.get("description") or "")
    if stripped:
        return stripped
    return item.get("shortDescription") or ""


def summarize(url: str, item: dict) -> dict:
    price = item.get("price") or {}
    return_terms = item.get("returnTerms") or {}
    return {
        "item_id": item.get("itemId"),
        "url": url,
        "title": item.get("title"),
        "price_value": float(price["value"]) if price.get("value") is not None else None,
        "price_currency": price.get("currency"),
        "condition": item.get("condition"),
        "buying_options": item.get("buyingOptions", []),
        "aspects": parse_aspects(item),
        "description_text": extract_description_text(item),
        "returns_accepted": return_terms.get("returnsAccepted"),
    }


def print_human(summary: dict) -> None:
    print(f"Item ID:   {summary['item_id']}")
    print(f"Title:     {summary['title']}")
    price = summary["price_value"]
    currency = summary["price_currency"]
    print(f"Price:     {price} {currency}" if price is not None else "Price:     Unknown")
    print(f"Condition: {summary['condition']}")
    print(f"Buying options: {', '.join(summary['buying_options']) or 'Unknown'}")
    print("Aspects:")
    for key, value in summary["aspects"].items():
        print(f"  {key}: {value}")
    print(f"Returns accepted: {summary['returns_accepted']}")
    print(f"Description: {summary['description_text'][:300]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Look up a single eBay AU listing via the Browse API.")
    parser.add_argument("url", help="eBay listing URL (e.g. https://www.ebay.com.au/itm/1234567890)")
    parser.add_argument("--json", action="store_true", help="print a single JSON object instead of text")
    args = parser.parse_args()

    try:
        item_id = extract_item_id(args.url)
        token = get_access_token()
        item = fetch_item(token, item_id)
        summary = summarize(args.url, item)
    except EbayApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary))
    else:
        print_human(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
