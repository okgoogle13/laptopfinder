"""
scrape_benchmark.py — Benchmark dataset builder for laptopfinder.

Accepts saved listing sources (URLs, local HTML files, or JSON API payloads)
and extracts the raw fields the pipeline expects: title, price, seller info,
full listing text, platform, and URL.

Output: one JSONL file where each line is a Stage 2 fixture
        (handoff_packet + full_listing_text + empty analysis_output stub).

Usage:
    # From a URLs file (one URL per line):
    python -m laptopfinder.scrape_benchmark --urls urls.txt --out data/benchmark/benchmark.jsonl

    # From a directory of saved .html or .json files:
    python -m laptopfinder.scrape_benchmark --html-dir saved_pages/ --out data/benchmark/benchmark.jsonl

    # From individual files (HTML or JSON, auto-detected):
    python -m laptopfinder.scrape_benchmark --html-file ebay_titan.html fb_rtx4080.json --out data/benchmark/benchmark.jsonl

    # Mix and match (all flags are additive):
    python -m laptopfinder.scrape_benchmark --urls urls.txt --html-dir saved_pages/ --out data/benchmark/benchmark.jsonl

Ad-hoc single item (from Python):
    from laptopfinder.scrape_benchmark import process_input, to_stage2_fixture
    raw = process_input("https://www.ebay.com.au/itm/123456")
    fixture = to_stage2_fixture(raw)
"""

import argparse
import json
import re
import sys
import time
import hashlib
from pathlib import Path
from urllib.parse import urlparse

# Optional: requests + bs4 for live fetching / rich HTML parsing.
# Falls back to stdlib urllib + regex when absent.
try:
    import requests
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    _BS4_OK = False


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform(url: str) -> str:
    """Map a URL to a canonical platform string."""
    host = urlparse(url).netloc.lower()
    if "ebay" in host:
        return "EBAY_AU"
    if "facebook" in host or "fb.com" in host:
        return "FB_MARKETPLACE"
    if "gumtree" in host:
        return "GUMTREE"
    return "UNKNOWN"


def platform_from_filename(path: Path) -> str:
    """Guess platform from filename conventions (ebay_*, fb_*, gumtree_*)."""
    name = path.stem.lower()
    if name.startswith("ebay"):
        return "EBAY_AU"
    if name.startswith("fb") or name.startswith("facebook"):
        return "FB_MARKETPLACE"
    if name.startswith("gumtree"):
        return "GUMTREE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------

def parse_price_aud(raw: str | None) -> float | None:
    """Extract a float AUD price from a raw string like '$4,200.00 AUD'."""
    if not raw:
        return None
    # Strip currency symbols, letters, commas; keep digits and dot
    cleaned = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# eBay AU extractor
# ---------------------------------------------------------------------------

def extract_ebay(soup: BeautifulSoup, url: str) -> dict:
    """Pull fields from an eBay AU item page."""
    title = None
    t = soup.find("h1", {"class": re.compile(r"x-item-title")})
    if not t:
        t = soup.find("h1", itemprop="name")
    if t:
        title = t.get_text(separator="\n", strip=True)

    price_raw = None
    p = soup.find("div", {"class": re.compile(r"x-price-primary")})
    if not p:
        p = soup.find("span", itemprop="price")
    if p:
        price_raw = p.get_text(strip=True)

    seller_name = None
    s = soup.find("span", {"class": re.compile(r"seller-persona|mbg-nw")})
    if not s:
        s = soup.find("a", {"class": re.compile(r"s-item__seller-info")})
    if s:
        seller_name = s.get_text(strip=True)

    seller_rating = None
    r = soup.find("span", {"class": re.compile(r"mbg-l|feedback-rating")})
    if not r:
        r = soup.find("div", string=re.compile(r"\d+\s*feedback", re.I))
    if r:
        seller_rating = r.get_text(strip=True)

    # Full listing text: item description iframe content is separate, so grab
    # the concatenated visible text of the description container + specs table.
    desc_text = ""
    desc_div = soup.find("div", {"class": re.compile(r"x-item-description|itemDescContainer")})
    if desc_div:
        desc_text = desc_div.get_text(separator="\n", strip=True)

    # Item specifics table (condition, brand, model etc.)
    specifics_text = ""
    specs_table = soup.find("div", {"class": re.compile(r"ux-layout-section--features|x-about-this-item")})
    if specs_table:
        specifics_text = specs_table.get_text(separator="\n", strip=True)

    # Combine: title + specifics + description is the raw text Stage 2 reads
    full_text_parts = [p for p in [title, specifics_text, desc_text] if p]
    full_listing_text = "\n".join(full_text_parts).strip() or None

    # Listing ID from URL (e.g. /itm/123456789)
    m = re.search(r"/itm/(\d+)", url)
    listing_id = f"ebay-au:{m.group(1)}" if m else f"ebay-au:unknown-{_short_hash(url)}"

    return {
        "platform": "EBAY_AU",
        "listing_id": listing_id,
        "url": url,
        "title": title,
        "price_raw": price_raw,
        "seller_name": seller_name,
        "seller_rating": seller_rating,
        "full_listing_text": full_listing_text,
    }


# ---------------------------------------------------------------------------
# Facebook Marketplace extractor
# ---------------------------------------------------------------------------

def extract_facebook(soup: BeautifulSoup, url: str) -> dict:
    """Pull fields from a saved Facebook Marketplace listing page.

    FB Marketplace is heavily client-rendered. This extractor works against
    saved HTML that includes the server-rendered JSON-LD or meta tags — the
    most reliable surface after a manual Save Page As.

    Fallback order for full_listing_text:
      1. application/ld+json description
      2. __REQUIRE__ / RelayPrefetchedStreamCache JSON blob in <script> tags
      3. og:description meta tag
      4. Visible text of the role="main" or <main> element
    """
    title = None
    price_raw = None
    seller_name = None
    full_listing_text = None

    # JSON-LD embedded in the page is the most reliable source
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            title = title or data.get("name")
            price_raw = price_raw or (
                data.get("offers", {}).get("price") if isinstance(data.get("offers"), dict) else None
            )
            desc = data.get("description")
            if desc and not full_listing_text:
                full_listing_text = desc
        except (json.JSONDecodeError, AttributeError):
            continue

    # Relay / require JSON blob fallback — FB embeds full listing data inside
    # plain <script> tags as __REQUIRE__([...]) or RelayPrefetchedStreamCache.
    # These often contain the untruncated description when ld+json is cut short.
    if not full_listing_text:
        relay_patterns = [
            re.compile(r"__REQUIRE__\("),
            re.compile(r"RelayPrefetchedStreamCache"),
        ]
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if not any(pat.search(script_text) for pat in relay_patterns):
                continue
            # Extract candidate description strings: look for "story_body" or
            # "message" keys which FB uses for marketplace listing descriptions.
            desc_match = re.search(
                r'"(?:story_body|message|description)"\s*:\s*"((?:[^"\\]|\\.)+)"',
                script_text,
            )
            if desc_match:
                try:
                    candidate = json.loads(f'"{desc_match.group(1)}"')
                    if len(candidate) > len(full_listing_text or ""):
                        full_listing_text = candidate
                except (json.JSONDecodeError, ValueError):
                    pass
            if full_listing_text:
                break

    # OG meta fallback
    if not title:
        og = soup.find("meta", property="og:title")
        if og:
            title = og.get("content", "").strip() or None
    if not full_listing_text:
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            full_listing_text = og_desc.get("content", "").strip() or None

    # Visible text fallback — FB pages have a div with aria-label="Marketplace"
    if not full_listing_text:
        main = soup.find("div", {"role": "main"}) or soup.find("main")
        if main:
            full_listing_text = main.get_text(separator="\n", strip=True) or None

    # Listing ID from URL (e.g. /marketplace/item/123456789)
    m = re.search(r"/item/(\d+)", url)
    listing_id = f"fb:{m.group(1)}" if m else f"fb:unknown-{_short_hash(url)}"

    return {
        "platform": "FB_MARKETPLACE",
        "listing_id": listing_id,
        "url": url,
        "title": title,
        "price_raw": str(price_raw) if price_raw is not None else None,
        "seller_name": seller_name,  # FB rarely exposes this in static HTML
        "seller_rating": None,
        "full_listing_text": full_listing_text,
    }


# ---------------------------------------------------------------------------
# Gumtree AU extractor
# ---------------------------------------------------------------------------

def extract_gumtree(soup: BeautifulSoup, url: str) -> dict:
    """Pull fields from a Gumtree AU listing page."""
    title = None
    t = soup.find("h1", {"class": re.compile(r"listing-title|vip-ad-title")})
    if not t:
        t = soup.find("h1")
    if t:
        title = t.get_text(strip=True)

    price_raw = None
    p = soup.find("span", {"class": re.compile(r"price-amount|listing-price")})
    if not p:
        p = soup.find("strong", string=re.compile(r"\$[\d,]+"))
    if p:
        price_raw = p.get_text(strip=True)

    seller_name = None
    s = soup.find("span", {"class": re.compile(r"user-name|seller-name|advertiser-name")})
    if not s:
        s = soup.find("a", {"class": re.compile(r"user-link|profile-link")})
    if s:
        seller_name = s.get_text(strip=True)

    seller_rating = None
    r = soup.find("div", {"class": re.compile(r"rating|feedback")})
    if r:
        seller_rating = r.get_text(strip=True)

    desc_text = ""
    desc_div = soup.find("div", {"class": re.compile(r"description|ad-description|listing-description")})
    if desc_div:
        desc_text = desc_div.get_text(separator="\n", strip=True)

    # Attributes panel (condition, brand, etc.)
    attrs_text = ""
    attrs_div = soup.find("ul", {"class": re.compile(r"attributes|listing-attributes")})
    if attrs_div:
        attrs_text = attrs_div.get_text(separator="\n", strip=True)

    full_text_parts = [p for p in [title, attrs_text, desc_text] if p]
    full_listing_text = "\n".join(full_text_parts).strip() or None

    # Listing ID from URL (e.g. /ad/computers/1234567890)
    m = re.search(r"/(\d{8,})", url)
    listing_id = f"gumtree:{m.group(1)}" if m else f"gumtree:unknown-{_short_hash(url)}"

    return {
        "platform": "GUMTREE",
        "listing_id": listing_id,
        "url": url,
        "title": title,
        "price_raw": price_raw,
        "seller_name": seller_name,
        "seller_rating": seller_rating,
        "full_listing_text": full_listing_text,
    }


# ---------------------------------------------------------------------------
# eBay API JSON extractor (FindingAPI / Browse API response)
# ---------------------------------------------------------------------------

def extract_ebay_api_item(item: dict) -> dict:
    """Extract fields from a single eBay API item dict.

    Handles both FindingAPI (searchResult item) and Browse API (item summary)
    shapes. All unknown fields map to null — never inferred.
    """
    # Browse API shape
    title = item.get("title") or item.get("title_")
    item_id = item.get("itemId") or item.get("legacyItemId") or item.get("itemId_", [None])[0]

    # FindingAPI uses nested lists wrapped in single-element arrays
    def _unpack(val):
        if isinstance(val, list) and len(val) == 1:
            return val[0]
        return val

    if not title:
        title = _unpack(item.get("title", [None]))

    price_raw = None
    selling_status = _unpack(item.get("sellingStatus", [{}]))
    if isinstance(selling_status, dict):
        cp = _unpack(selling_status.get("currentPrice", [{}]))
        if isinstance(cp, dict):
            price_raw = str(cp.get("__value__") or cp.get("value", ""))

    # Browse API price
    if not price_raw:
        price_obj = item.get("price") or item.get("currentBidPrice") or {}
        price_raw = str(price_obj.get("value", "")) if price_obj else None

    seller_name = None
    seller_rating = None
    seller_info = _unpack(item.get("sellerInfo", [{}]))
    if isinstance(seller_info, dict):
        seller_name = _unpack(seller_info.get("sellerUserName", [None]))
        fb_score = _unpack(seller_info.get("feedbackScore", [None]))
        fb_pct = _unpack(seller_info.get("positiveFeedbackPercent", [None]))
        if fb_score or fb_pct:
            seller_rating = f"{fb_score} feedback, {fb_pct}% positive"

    # Browse API seller
    if not seller_name:
        sv2 = item.get("seller", {})
        seller_name = sv2.get("username")
        fb_pct = sv2.get("feedbackPercentage")
        fb_score = sv2.get("feedbackScore")
        if fb_score or fb_pct:
            seller_rating = f"{fb_score} feedback, {fb_pct}% positive"

    # Condition
    condition = None
    cond_raw = _unpack(item.get("condition", [{}]))
    if isinstance(cond_raw, dict):
        condition = _unpack(cond_raw.get("conditionDisplayName", [None]))
    if not condition:
        condition = item.get("condition", {}).get("conditionDescription") if isinstance(item.get("condition"), dict) else None

    # Description: API responses usually lack full description; concatenate
    # available fields so Stage 2 has something to parse against.
    short_desc = item.get("shortDescription") or ""
    cat_path = item.get("categoryPath") or ""
    aspects = item.get("localizedAspects", [])
    aspects_text = "\n".join(f"{a.get('name','')}: {a.get('value','')}" for a in aspects)

    subtitle = _unpack(item.get("subtitle", [None])) or item.get("subtitle") or ""
    full_text_parts = [p for p in [title, subtitle, condition, short_desc, cat_path, aspects_text] if p]
    full_listing_text = "\n".join(full_text_parts).strip() or None

    url = item.get("viewItemURL") or item.get("itemWebUrl")
    if isinstance(url, list):
        url = url[0]

    listing_id = f"ebay-au:{item_id}" if item_id else f"ebay-au:unknown-{_short_hash(str(item))}"

    return {
        "platform": "EBAY_AU",
        "listing_id": listing_id,
        "url": url,
        "title": title,
        "price_raw": price_raw,
        "seller_name": seller_name,
        "seller_rating": seller_rating,
        "full_listing_text": full_listing_text,
    }


# ---------------------------------------------------------------------------
# Generic JSON extractor (non-eBay API payloads: Gumtree, FB intercepts, etc.)
# ---------------------------------------------------------------------------

def extract_generic_json(data: dict, url: str = "", platform: str | None = None) -> dict:
    """Extract fields from any generic JSON payload with common field names.

    Covers Gumtree internal API, FB Marketplace intercepts, or any ad-hoc
    JSON you've saved from browser DevTools. Never infers missing fields.
    """
    title = data.get("title") or data.get("name") or data.get("heading")

    price_raw = None
    price_val = data.get("price") or data.get("currentPrice") or data.get("asking_price")
    if isinstance(price_val, (int, float)):
        price_raw = str(price_val)
    elif isinstance(price_val, str):
        price_raw = price_val
    elif isinstance(price_val, dict):
        # e.g. {"amount": 4200, "currency": "AUD"}
        v = price_val.get("amount") or price_val.get("value")
        price_raw = str(v) if v is not None else None

    seller_info = data.get("seller") or data.get("advertiser") or {}
    if isinstance(seller_info, str):
        seller_name = seller_info
        seller_rating = None
    else:
        seller_name = (seller_info.get("username") or seller_info.get("name")
                       or seller_info.get("displayName"))
        fb_score = seller_info.get("feedbackScore") or seller_info.get("rating")
        fb_pct = seller_info.get("feedbackPercentage") or seller_info.get("positivePercent")
        if fb_score or fb_pct:
            seller_rating = f"{fb_score} feedback, {fb_pct}% positive"
        else:
            seller_rating = None

    # Build full_listing_text from the richest available text fields.
    # Never fall back to json.dumps — that would pollute the grounding firewall.
    desc = data.get("description") or data.get("body") or data.get("details") or ""
    attrs = data.get("attributes") or data.get("specs") or {}
    if isinstance(attrs, dict):
        attrs_text = "\n".join(f"{k}: {v}" for k, v in attrs.items())
    elif isinstance(attrs, list):
        attrs_text = "\n".join(
            f"{a.get('name','')}: {a.get('value','')}" for a in attrs if isinstance(a, dict)
        )
    else:
        attrs_text = ""

    full_text_parts = [p for p in [title, attrs_text, desc] if p]
    full_listing_text = "\n".join(full_text_parts).strip() or None

    item_url = data.get("url") or data.get("itemWebUrl") or data.get("link") or url or None
    item_id = data.get("id") or data.get("itemId") or data.get("listingId")
    plat = platform or detect_platform(url or "")
    prefix = {"EBAY_AU": "ebay-au", "FB_MARKETPLACE": "fb", "GUMTREE": "gumtree"}.get(plat, "unknown")
    listing_id = f"{prefix}:{item_id}" if item_id else f"{prefix}:unknown-{_short_hash(str(data))}"

    return {
        "platform": plat,
        "listing_id": listing_id,
        "url": item_url,
        "title": title,
        "price_raw": price_raw,
        "seller_name": seller_name,
        "seller_rating": seller_rating,
        "full_listing_text": full_listing_text,
    }


# ---------------------------------------------------------------------------
# process_input — convenience wrapper for ad-hoc single-item use
# ---------------------------------------------------------------------------

def process_input(path_or_url: str, platform: str | None = None) -> dict | None:
    """Accept a URL, a local HTML file, or a local JSON file and return a raw record.

    Auto-detects content type: tries JSON parse first, falls back to HTML.
    Platform is inferred from URL/filename if not provided.
    """
    content = ""
    url = ""

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
        content = fetch_html(url)
        if not content:
            return None
    else:
        p = Path(path_or_url)
        if not p.exists():
            print(f"[ERROR] File not found: {path_or_url}", file=sys.stderr)
            return None
        content = p.read_text(encoding="utf-8", errors="replace")
        platform = platform or platform_from_filename(p)

    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict):
            # Route eBay API items through the dedicated extractor
            if "sellingStatus" in data or "localizedAspects" in data or "legacyItemId" in data:
                return extract_ebay_api_item(data)
            return extract_generic_json(data, url=url, platform=platform)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fall through to HTML parsing
    return html_to_raw(content, url or path_or_url, platform=platform)


# ---------------------------------------------------------------------------
# Live fetching (optional, may be blocked by anti-bot)
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_html(url: str, delay: float = 2.0) -> str | None:
    """Fetch a URL and return raw HTML. Uses requests if available, else stdlib urllib."""
    time.sleep(delay)
    if _BS4_OK:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"[WARN] fetch failed for {url}: {e}", file=sys.stderr)
            return None
    else:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers=_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[WARN] fetch failed for {url}: {e}", file=sys.stderr)
            return None


# ---------------------------------------------------------------------------
# HTML → raw record
# ---------------------------------------------------------------------------

def _html_to_raw_regex(html: str, url: str) -> dict:
    """Zero-dependency HTML extraction via regex. Used when bs4 is absent.
    Extracts title and full visible text; price/seller will usually be null.
    """
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else None

    price_m = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", html)
    price_raw = price_m.group(0).strip() if price_m else None

    # Strip tags and preserve structural boundaries with newlines
    full_text = re.sub(r"<script[^>]*>.*?</script>", "\n", html, flags=re.DOTALL | re.IGNORECASE)
    full_text = re.sub(r"<style[^>]*>.*?</style>", "\n", full_text, flags=re.DOTALL | re.IGNORECASE)
    full_text = re.sub(r"<[^>]+>", "\n", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip() or None

    return {
        "platform": detect_platform(url),
        "listing_id": f"unknown:{_short_hash(url)}",
        "url": url,
        "title": title,
        "price_raw": price_raw,
        "seller_name": None,
        "seller_rating": None,
        "full_listing_text": full_text,
    }


def html_to_raw(html: str, url: str, platform: str | None = None) -> dict | None:
    """Parse HTML and dispatch to the right extractor.
    Falls back to regex extraction if bs4 is not installed.
    """
    if not _BS4_OK:
        print("[WARN] beautifulsoup4 not installed — using regex fallback (install bs4+lxml for full extraction)", file=sys.stderr)
        return _html_to_raw_regex(html, url)

    soup = BeautifulSoup(html, "lxml")
    plat = platform or detect_platform(url)

    if plat == "EBAY_AU":
        return extract_ebay(soup, url)
    if plat == "FB_MARKETPLACE":
        return extract_facebook(soup, url)
    if plat == "GUMTREE":
        return extract_gumtree(soup, url)

    # UNKNOWN — extract title and body text
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    body = soup.find("body")
    full_text = body.get_text(separator="\n", strip=True) if body else None
    return {
        "platform": "UNKNOWN",
        "listing_id": f"unknown:{_short_hash(url)}",
        "url": url,
        "title": title,
        "price_raw": None,
        "seller_name": None,
        "seller_rating": None,
        "full_listing_text": full_text,
    }


# ---------------------------------------------------------------------------
# Raw record → Stage 2 fixture format
# ---------------------------------------------------------------------------

def to_stage2_fixture(raw: dict) -> dict:
    """Convert a raw extracted record to the Stage 2 fixture shape.

    The analysis_output stub is intentionally empty — it will be filled by
    the LLM pipeline. The handoff_packet inferred_* fields are set to null
    because Stage 1 (the LLM discovery pass) has not run yet; they will be
    populated when this fixture is fed through Stage 1 → Stage 1A.

    To feed directly into Stage 2 (skipping Stage 1), populate
    handoff_packet.inferred_* manually after generation.
    """
    platform = raw.get("platform", "UNKNOWN")
    listing_id = raw.get("listing_id") or f"{platform.lower()}:unknown"
    url = raw.get("url") or listing_id
    title = raw.get("title") or ""
    price = parse_price_aud(raw.get("price_raw"))
    seller_name = raw.get("seller_name")
    seller_rating = raw.get("seller_rating")
    full_text = raw.get("full_listing_text")

    return {
        "handoff_packet": {
            "source_platform": platform,
            "listing_title": title,
            "listing_price_aud": price,
            "listing_url_or_identifier": url,
            "inferred_component_category": raw.get("inferred_component_category", "SYSTEM"),
            "inferred_model_hint": None,
            "inferred_gpu_hint": None,
            "inferred_vram_hint": None,
            "inferred_condition_hint": None,
            "discovery_flags": [],
        },
        "full_listing_text": full_text,
        # Metadata not part of handoff_packet but useful for benchmark tracking
        "_meta": {
            "seller_name_or_identifier": seller_name,
            "seller_rating_or_profile_signal": seller_rating,
            "scrape_source": "benchmark_scraper",
        },
        # Empty stub — to be filled by Stage 2 LLM pass or manually
        "analysis_output": None,
    }


def to_stage1_fixture(raw: dict) -> dict:
    """Convert a raw record to a Stage 1 fixture (single-element array).

    inferred_* fields are null; the LLM discovery pass will fill them.
    Use this if you want to feed through the full pipeline from Stage 1.
    """
    platform = raw.get("platform", "UNKNOWN")
    return [
        {
            "source_platform": platform,
            "listing_title": raw.get("title") or "",
            "listing_price_aud": parse_price_aud(raw.get("price_raw")),
            "listing_url_or_identifier": raw.get("url") or raw.get("listing_id"),
            "inferred_component_category": "SYSTEM",  # safe default for laptop listings
            "inferred_model_hint": None,
            "inferred_gpu_hint": None,
            "inferred_vram_hint": None,
            "inferred_condition_hint": None,
            "discovery_flags": [],
            "discovery_confidence": 0.0,  # not yet scored
        }
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _short_hash(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scrape and convert marketplace listings to laptopfinder benchmark fixtures."
    )
    p.add_argument("--urls", metavar="FILE",
                   help="Text file with one listing URL per line")
    p.add_argument("--html-dir", metavar="DIR",
                   help="Directory of saved .html files (filename must start with ebay_, fb_, or gumtree_)")
    p.add_argument("--html-file", metavar="FILE", nargs="+",
                   help="One or more .html or .json files (platform guessed from filename; content auto-detected)")
    p.add_argument("--ebay-api", metavar="FILE",
                   help="eBay API JSON response file (FindingAPI or Browse API); for generic JSON use --html-file")
    p.add_argument("--out", metavar="FILE", default="data/benchmark/benchmark.jsonl",
                   help="Output JSONL file (default: data/benchmark/benchmark.jsonl)")
    p.add_argument("--format", choices=["stage2", "stage1"], default="stage2",
                   help="Output fixture format (default: stage2)")
    p.add_argument("--fetch-delay", type=float, default=2.0, metavar="SECONDS",
                   help="Delay between live HTTP fetches to avoid rate-limiting (default: 2s)")
    return p


def process_sources(args) -> list[dict]:
    """Collect raw records from all specified sources."""
    raws = []

    # --- Live URL fetch ---
    if args.urls:
        urls_path = Path(args.urls)
        if not urls_path.exists():
            print(f"[ERROR] URLs file not found: {urls_path}", file=sys.stderr)
        else:
            for line in urls_path.read_text().splitlines():
                url = line.strip()
                if not url or url.startswith("#"):
                    continue
                print(f"[FETCH] {url}")
                html = fetch_html(url, delay=args.fetch_delay)
                if html:
                    raw = html_to_raw(html, url)
                    if raw:
                        raws.append(raw)
                else:
                    print("  [SKIP] could not fetch — save the page manually and use --html-file", file=sys.stderr)

    # --- HTML/JSON directory ---
    if args.html_dir:
        html_dir = Path(args.html_dir)
        if not html_dir.is_dir():
            print(f"[ERROR] Not a directory: {html_dir}", file=sys.stderr)
        else:
            glob_patterns = ["*.html", "*.htm", "*.json"]
            all_files = []
            for pat in glob_patterns:
                all_files.extend(html_dir.glob(pat))
            all_files = sorted(set(all_files))
            if not all_files:
                print(f"[WARN] No .html/.json files found in {html_dir}", file=sys.stderr)
            for f in all_files:
                print(f"[FILE] {f.name}")
                raw = process_input(str(f))
                if raw:
                    raw["url"] = raw.get("url") or f.stem
                    raws.append(raw)

    # --- Individual HTML/JSON files ---
    if args.html_file:
        for filepath in args.html_file:
            f = Path(filepath)
            if not f.exists():
                print(f"[ERROR] File not found: {f}", file=sys.stderr)
                continue
            print(f"[FILE] {f.name}")
            raw = process_input(str(f))
            if raw:
                raw["url"] = raw.get("url") or f.stem
                raws.append(raw)

    # --- eBay API JSON ---
    if args.ebay_api:
        api_path = Path(args.ebay_api)
        if not api_path.exists():
            print(f"[ERROR] eBay API file not found: {api_path}", file=sys.stderr)
        else:
            data = json.loads(api_path.read_text())
            # Support FindingAPI, Browse API, or a plain list
            items = []
            if isinstance(data, list):
                items = data
            elif "findItemsAdvancedResponse" in data:
                search_result = (data["findItemsAdvancedResponse"][0]
                                 .get("searchResult", [{}])[0]
                                 .get("item", []))
                items = search_result
            elif "itemSummaries" in data:
                items = data["itemSummaries"]
            elif "item" in data:
                items = [data["item"]]
            else:
                items = [data]  # treat the whole object as one item

            for item in items:
                print(f"[API]  eBay item: {item.get('itemId') or item.get('title','?')[:60]}")
                raws.append(extract_ebay_api_item(item))

    return raws


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not any([args.urls, args.html_dir, args.html_file, args.ebay_api]):
        parser.print_help()
        sys.exit(0)

    raws = process_sources(args)

    if not raws:
        print("[WARN] No records extracted. Check your inputs.", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8") as f:
        for raw in raws:
            if args.format == "stage1":
                fixture = to_stage1_fixture(raw)
            else:
                fixture = to_stage2_fixture(raw)
            f.write(json.dumps(fixture, ensure_ascii=False) + "\n")

    print(f"\n[DONE] {len(raws)} records → {out_path}")
    print(f"       Format: {args.format} fixture")
    print("       Next: fill in analysis_output manually or pipe through Stage 2 LLM pass.")


if __name__ == "__main__":
    main()
