"""eBay AU Hunter — one-shot, scraper-free acquisition sweep for local-LLM hardware.

Single-run script that replaces every DOM-scraping workflow with structured eBay
REST payloads + Gemini reasoning, then reuses this repo's own grounding firewall
(`core.run_stage2`) and decision engine (`decide.decide`) so no scoring is
reinvented here. It runs once, processes the AU market, emails new top-acquisition
targets, and exits — no daemon, no webhook, no persistent infrastructure.

Composite of three strategies (see repo brainstorm):
  B  Bulk corpus dump  → one long-context Gemini triage pass over the whole market
                         (relevance de-noising + canonical-SKU normalization).
  A  Structured aspect harvest — `getItem.localizedAspects` are eBay's own parsed
                         specs; they become grounded *facts*. Gemini fills only the
                         residue (usually VRAM) against verbatim listing text.
  D  Multimodal VRAM ground-truth — when VRAM is absent from text, Gemini vision
                         reads GPU-Z / spec-sticker / box photos pulled from the
                         listing's image URLs. Provenance is appended to the
                         grounded listing text so the firewall stays honest.

Alerting: new SHORTLIST-grade listings that are also underpriced vs the live-market
baseline are emailed (stdlib smtplib). "New" = itemId not seen on a prior run
(persisted in data/ebay/seen_items.json), so re-runs only surface fresh finds.

Zero non-stdlib HTTP: all eBay REST and image fetches go through urllib. The only
third-party dependency is google-genai (already in pyproject) for Gemini.

Run:
    .venv/bin/python -m laptopfinder.runners.ebay_hunter                        # full run + email
    .venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run             # no email, no state write
    .venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run --no-enrich # corpus only, zero LLM calls
    .venv/bin/python -m laptopfinder.runners.ebay_hunter --no-vision --enrich-top 15

Required .env keys:
    EBAY_CLIENT_ID, EBAY_CLIENT_SECRET            (OAuth client-credentials)
    GEMINI_API_KEY                                (Gemini reasoning + vision)
Optional .env keys:
    EBAY_API_BASE_URL          (default https://api.ebay.com)
    EBAY_OAUTH_SCOPES          (default https://api.ebay.com/oauth/api_scope)
    EBAY_MARKETPLACE_ID        (default EBAY_AU)
    EBAY_CATEGORY_IDS          (removed — category ID is now owned by SRL ebay_aspect_filter.category_id)
    GEMINI_MODEL               (default gemini-3.5-flash)
    SMTP_HOST                  (default smtp.gmail.com)
    SMTP_PORT                  (default 465, SSL; any other port uses STARTTLS)
    SMTP_USER, SMTP_PASSWORD   (Gmail: use an App Password, not the account password)
    ALERT_EMAIL_TO             (default SMTP_USER)
    ALERT_EMAIL_FROM           (default SMTP_USER)
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[3] / ".env")



# ----------------------------------------------------------------------------
# Paths & tunables (governance defaults; anything market-shaped lives in the SRL)
# ----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "ebay"
SEEN_PATH = DATA_DIR / "seen_items.json"
CORPUS_PATH = DATA_DIR / "corpus.jsonl"
RESULTS_PATH = DATA_DIR / "hunt_results.jsonl"
TOKEN_CACHE_PATH = REPO_ROOT / ".ebay_token_cache.json"
LEGACY_TOKEN_PATH = REPO_ROOT / ".ebay_access_token"

# Price window (AUD) for discovery — broad; scoring/gating is done downstream.
PRICE_MIN_AUD = 500
PRICE_MAX_AUD = 8000
# A listing is "underpriced" when at least this fraction below its model's live median.
UNDERPRICE_DISCOUNT = 0.12
# Negative keywords injected into every query (native eBay exclusion, pre-filter junk).
NEGATIVE_KEYWORDS = ["parts", "faulty", "spares", "broken", "cracked", "repair", "case only", "shell"]

HTTP_RETRIES = 4
HTTP_BACKOFF_SECONDS = 2.0
IMAGE_FETCH_TIMEOUT = 20
MAX_VISION_IMAGES = 4
# Guest Browse-API OAuth scope is a protocol constant, not a tunable. We do NOT read
# EBAY_OAUTH_SCOPES because that env may carry sell-API scopes this app isn't granted
# (→ invalid_scope). This single scope is all guest item search needs, prod or sandbox.
BROWSE_SCOPE = "https://api.ebay.com/oauth/api_scope"


def log(msg: str) -> None:
    print(f"[hunter] {msg}", flush=True)


# ----------------------------------------------------------------------------
# eBay OAuth (client-credentials application token, self-refreshing)
# ----------------------------------------------------------------------------
def _api_base() -> str:
    return os.environ.get("EBAY_API_BASE_URL", "https://api.ebay.com").rstrip("/")


def _load_cached_token() -> str | None:
    if not TOKEN_CACHE_PATH.exists():
        return None
    try:
        cache = json.loads(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    # 5-minute safety margin before stated expiry.
    if cache.get("expires_at", 0) - 300 > time.time():
        return cache.get("access_token")
    return None


def get_ebay_token(force: bool = False) -> str:
    """Return a valid Browse-scope application token, minting a fresh one if needed."""
    if not force:
        env_token = os.environ.get("EBAY_ACCESS_TOKEN")
        if env_token:
            return env_token.strip()
        cached = _load_cached_token()
        if cached:
            return cached

    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET missing from .env")

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": BROWSE_SCOPE}).encode()
    req = urllib.request.Request(
        f"{_api_base()}/identity/v1/oauth2/token",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(
            f"eBay OAuth failed (HTTP {exc.code}): {detail}. "
            f"Check EBAY_CLIENT_ID/SECRET match the environment in EBAY_API_BASE_URL "
            f"({_api_base()})."
        ) from exc

    token = payload["access_token"]
    expires_at = time.time() + int(payload.get("expires_in", 7200))
    TOKEN_CACHE_PATH.write_text(
        json.dumps({"access_token": token, "expires_at": expires_at}), encoding="utf-8"
    )
    LEGACY_TOKEN_PATH.write_text(token, encoding="utf-8")  # keep the bash-flow artifact in sync
    log("minted fresh eBay application token")
    return token


# ----------------------------------------------------------------------------
# eBay Browse API (structured JSON — the scraper replacement)
# ----------------------------------------------------------------------------
def _marketplace_id() -> str:
    return os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_AU")


def ebay_get(path: str, params: dict, token: str) -> dict:
    """GET a Browse endpoint with retry/backoff; transparently refresh on 401."""
    url = f"{_api_base()}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

    for attempt in range(HTTP_RETRIES):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": _marketplace_id(),
                "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=AU",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and attempt == 0:
                token = get_ebay_token(force=True)
                continue
            if exc.code in (429, 500, 502, 503, 504) and attempt < HTTP_RETRIES - 1:
                wait = HTTP_BACKOFF_SECONDS * (2 ** attempt)
                log(f"HTTP {exc.code} on {path} — backing off {wait:.0f}s")
                time.sleep(wait)
                continue
            body = exc.read().decode(errors="replace")[:400]
            raise RuntimeError(f"eBay {path} failed: HTTP {exc.code} {body}") from exc
        except urllib.error.URLError as exc:
            if attempt < HTTP_RETRIES - 1:
                time.sleep(HTTP_BACKOFF_SECONDS * (2 ** attempt))
                continue
            raise RuntimeError(f"eBay {path} network error: {exc}") from exc
    raise RuntimeError(f"eBay {path} exhausted retries")






def browse_search(
    token: str,
    query: str,
    max_items: int,
    *,
    aspect_filter: str | None = None,
    category_id: str = "175672",
    filter_str: str | None = None,
) -> list[dict]:
    """Page item_summary/search for one query up to max_items (Browse caps at 10k).

    aspect_filter: eBay aspect_filter string (e.g. GPU Memory Size values).
    category_id:   Leaf category — 175672 (PC Laptops & Netbooks) is the SRL default.
                   EBAY_CATEGORY_IDS env var overrides when set.
    filter_str:    Full filter override (e.g. for seller-scoped sweeps). When None,
                   uses _build_filter().
    """
    collected: list[dict] = []
    offset = 0
    page = min(200, max_items)
    # SRL owns the category ID (config/static_reference_layer.json → ebay_aspect_filter.category_id).
    # category_id param is passed from collect_corpus via ebay_category_id(ref).
    cat = category_id

    while len(collected) < max_items and offset <= 9800:
        params: dict = {
            "q": query,
            "filter": filter_str,
            "sort": "price",
            "limit": page,
            "offset": offset,
            "category_ids": cat,
        }
        if aspect_filter:
            params["aspect_filter"] = aspect_filter
        data = ebay_get("/buy/browse/v1/item_summary/search", params, token)
        items = data.get("itemSummaries") or []
        if not items:
            break
        collected.extend(items)
        total = data.get("total", 0)
        offset += page
        if offset >= total:
            break
    return collected[:max_items]


def get_item(token: str, item_id: str) -> dict:
    """Fetch full item detail (localizedAspects, images, description)."""
    return ebay_get(f"/buy/browse/v1/item/{urllib.parse.quote(item_id, safe='')}", {}, token)


# ----------------------------------------------------------------------------
# Corpus assembly (Strategy B input)
# ----------------------------------------------------------------------------






# ----------------------------------------------------------------------------
# Gemini client + robust JSON call helper
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# Strategy B — one long-context triage pass over the entire corpus
# ----------------------------------------------------------------------------
TRIAGE_INSTRUCTION = """You are triaging an entire eBay Australia laptop market snapshot for a buyer
sourcing local-LLM inference hardware: laptops with 16GB+ GPU VRAM, NVIDIA RTX
40-/50-series (or high-VRAM Ampere/workstation/Apple-Silicon/Strix-Halo UMA),
and premium mobile workstation chassis.

You are given a JSON array of listings (item_id, title, price_aud, condition,
seller signals). Reason over the WHOLE set at once. For EVERY listing return an
object with:
  item_id            : echo the id verbatim.
  is_relevant        : true only if it is a laptop/eGPU system plausibly meeting
                       the VRAM/GPU targets. Reject "16GB RAM" listings that have
                       no qualifying GPU (RAM/VRAM conflation), desktops, phones,
                       chargers, parts, and unrelated categories.
  canonical_model    : normalized model key so identical hardware collapses
                       together, e.g. "Lenovo Legion 9i Gen 10", "MSI Titan 18 HX",
                       "Apple MacBook Pro 16 M4 Max". Use null if unidentifiable.
  gpu_guess          : best GPU string from the title, or null.
  vram_hint_gb       : integer VRAM if strongly implied by the GPU, else null.
  priority           : 0-100, how worth a deep look this listing is (VRAM ceiling,
                       target match, and how cheap it looks vs peers IN THIS SET).
  note               : one short phrase (e.g. "cheapest RTX 5090 in set").

Return ONLY a JSON object: {"listings": [ ...one object per input listing... ]}.
Do not omit any input listing."""




# ----------------------------------------------------------------------------
# Live-market baseline (mispricing detector; Marketplace-Insights-free fallback)
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# Strategy A — aspect harvest → grounded listing text
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# Strategy D — vision VRAM recovery from listing images
# ----------------------------------------------------------------------------
VISION_INSTRUCTION = """These are photos from an eBay laptop listing. Some may show a GPU-Z screenshot,
a Windows dxdiag/Task Manager panel, a spec sticker, or retail box art stating the
graphics memory. Read any GPU VRAM / "dedicated video memory" / "GDDR" value you can
SEE. Do not infer from the GPU model — only report what is legible in an image.
Return JSON: {"vram_gb": <int or null>, "verbatim_quote": "<exact legible text or null>",
"source": "<which image, e.g. image 3>", "confidence": <0-1>}."""


def _fetch_image_bytes(url: str) -> tuple[bytes, str] | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "laptopfinder-hunter/1.0"})
        with urllib.request.urlopen(req, timeout=IMAGE_FETCH_TIMEOUT) as resp:
            data = resp.read()
            mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None
    if not data or not mime.startswith("image/"):
        return None
    return data, mime




# ----------------------------------------------------------------------------
# Enrichment → Stage 2 analysis (fed back through the firewall + decide())
# ----------------------------------------------------------------------------
ENRICH_INSTRUCTION = """You extract hardware facts from ONE eBay listing for a local-LLM buyer.
Below is the FULL listing text (title + eBay structured aspects + description).
Extract ONLY facts that appear VERBATIM in that text — copy substrings exactly.
Missing data must be null. Never infer specs from the model name or price.

Return a JSON object with EXACTLY this shape:
{
  "extracted_data": {
    "exact_model_name": str|null,
    "component_category": "GPU"|"CPU"|"RAM"|"SYSTEM"|"OTHER",
    "cpu": str|null,
    "gpu": str|null,
    "ram": str|null,
    "storage": str|null,
    "vram_capacity": {"semantic_value": number, "verbatim_quote": str} | null,
    "stated_condition": str|null,
    "shipping_or_pickup_signal": "SHIPPING_ONLY"|"PICKUP_ONLY"|"BOTH"|"UNKNOWN",
    "missing_information": {"gpu": bool, "vram": bool, "cpu": bool, "ram": bool, "storage": bool, "condition": bool},
    "total_system_ram": str|null,
    "egpu_model": str|null,
    "touchscreen_digitizer": str|null
  },
  "analysis": {
    "risk_score": number 0-10,
    "risk_flags": [str],
    "stated_pickup_location": str|null,
    "confidence": number 0-1,
    "seller_classification": "RETAILER_WITH_WARRANTY"|"ESTABLISHED_RESELLER"|"PRIVATE_ESTABLISHED"|"PRIVATE_NEW_OR_UNKNOWN"
  }
}
verbatim_quote for vram_capacity MUST be an exact substring of the listing text.
Judge risk_score from seller signals, completeness, and any red flags."""










# ----------------------------------------------------------------------------
# Mispricing + alert gating (top acquisition only = SHORTLIST & underpriced)
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# New-listing state (dedup so re-runs only alert on fresh finds)
# ----------------------------------------------------------------------------






# ----------------------------------------------------------------------------
# Email alert (stdlib smtplib; no third-party account beyond your mailbox)
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------








