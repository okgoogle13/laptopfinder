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
    .venv/bin/python -m laptopfinder.runners.ebay_hunter            # full run + email
    .venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run  # no email, no state write
    .venv/bin/python -m laptopfinder.runners.ebay_hunter --no-vision --enrich-top 15

Required .env keys:
    EBAY_CLIENT_ID, EBAY_CLIENT_SECRET            (OAuth client-credentials)
    GEMINI_API_KEY                                (Gemini reasoning + vision)
Optional .env keys:
    EBAY_API_BASE_URL          (default https://api.ebay.com)
    EBAY_OAUTH_SCOPES          (default https://api.ebay.com/oauth/api_scope)
    EBAY_MARKETPLACE_ID        (default EBAY_AU)
    EBAY_CATEGORY_IDS          (default 177 = PC Laptops & Netbooks; blank to disable)
    GEMINI_MODEL               (default gemini-3.5-flash)
    SMTP_HOST                  (default smtp.gmail.com)
    SMTP_PORT                  (default 465, SSL; any other port uses STARTTLS)
    SMTP_USER, SMTP_PASSWORD   (Gmail: use an App Password, not the account password)
    ALERT_EMAIL_TO             (default SMTP_USER)
    ALERT_EMAIL_FROM           (default SMTP_USER)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import smtplib
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ..core import run_stage2
from ..decide import decide, load_ref

load_dotenv()

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


def _build_filter() -> str:
    return (
        f"price:[{PRICE_MIN_AUD}..{PRICE_MAX_AUD}],"
        "priceCurrency:AUD,"
        "conditions:{NEW|USED|SELLER_REFURBISHED|CERTIFIED_REFURBISHED},"
        "buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER}"
    )


def build_queries(ref: dict) -> list[str]:
    """Derive the search sweep from the SRL target lists — no hardcoded query strings.

    GPU targets are paired with 'laptop' (RAM/VRAM conflation is resolved downstream
    by Gemini triage). High-signal chassis names are swept directly for niche imports.
    """
    neg = " ".join(f"-{kw}" for kw in NEGATIVE_KEYWORDS)
    queries: list[str] = []
    for gpu in ref.get("target_gpus", {}):
        queries.append(f"{gpu} laptop {neg}")
    for model in ref.get("target_models", []):
        queries.append(f"{model} {neg}")
    # Dedup preserving order.
    seen: set[str] = set()
    ordered = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            ordered.append(q)
    return ordered


def browse_search(token: str, query: str, max_items: int) -> list[dict]:
    """Page item_summary/search for one query up to max_items (Browse caps at 10k)."""
    collected: list[dict] = []
    offset = 0
    page = min(200, max_items)
    category_ids = os.environ.get("EBAY_CATEGORY_IDS", "177").strip()

    while len(collected) < max_items and offset <= 9800:
        params = {
            "q": query,
            "filter": _build_filter(),
            "sort": "price",
            "limit": page,
            "offset": offset,
        }
        if category_ids:
            params["category_ids"] = category_ids
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
def summary_to_row(item: dict) -> dict:
    price = item.get("price") or {}
    seller = item.get("seller") or {}
    return {
        "item_id": item.get("itemId"),
        "title": item.get("title"),
        "price_aud": _num(price.get("value")) if price.get("currency") == "AUD" else None,
        "currency": price.get("currency"),
        "condition": item.get("condition"),
        "buying_options": item.get("buyingOptions"),
        "seller_username": seller.get("username"),
        "seller_feedback_pct": seller.get("feedbackPercentage"),
        "seller_feedback_score": seller.get("feedbackScore"),
        "item_web_url": item.get("itemWebUrl"),
    }


def _num(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def collect_corpus(token: str, ref: dict, max_per_query: int) -> list[dict]:
    """Run the full query sweep, dedup by itemId, return normalized rows."""
    by_id: dict[str, dict] = {}
    for query in build_queries(ref):
        try:
            items = browse_search(token, query, max_per_query)
        except RuntimeError as exc:
            log(f"query failed ({query[:40]}...): {exc}")
            continue
        for item in items:
            row = summary_to_row(item)
            if row["item_id"] and row["item_id"] not in by_id:
                by_id[row["item_id"]] = row
        log(f"query '{query[:44]}...' → {len(items)} items (corpus {len(by_id)})")
    return list(by_id.values())


# ----------------------------------------------------------------------------
# Gemini client + robust JSON call helper
# ----------------------------------------------------------------------------
def gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing from .env")
    return genai.Client(api_key=api_key)


def _gemini_json(client: genai.Client, model: str, parts: list, temperature: float = 0.1):
    """Single Gemini call returning parsed JSON (application/json mode)."""
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    return json.loads(response.text)


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


def triage_corpus(client: genai.Client, model: str, corpus: list[dict]) -> dict[str, dict]:
    """Return {item_id: triage_dict} for the whole corpus in one Gemini call."""
    slim = [
        {
            "item_id": r["item_id"],
            "title": r["title"],
            "price_aud": r["price_aud"],
            "condition": r["condition"],
            "seller_feedback_pct": r["seller_feedback_pct"],
        }
        for r in corpus
    ]
    parts = [types.Part.from_text(
        text=f"{TRIAGE_INSTRUCTION}\n\nLISTINGS:\n{json.dumps(slim, ensure_ascii=False)}"
    )]
    try:
        result = _gemini_json(client, model, parts)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully to raw target matching
        log(f"triage failed ({exc}); falling back to raw target matching")
        return {}
    out: dict[str, dict] = {}
    for entry in result.get("listings", []):
        if entry.get("item_id"):
            out[entry["item_id"]] = entry
    return out


# ----------------------------------------------------------------------------
# Live-market baseline (mispricing detector; Marketplace-Insights-free fallback)
# ----------------------------------------------------------------------------
def compute_baselines(corpus: list[dict], triage: dict[str, dict], min_listings: int) -> dict[str, float]:
    """Median AUD price per canonical model, requiring >= min_listings comparables."""
    groups: dict[str, list[float]] = {}
    for row in corpus:
        t = triage.get(row["item_id"], {})
        model = t.get("canonical_model")
        price = row.get("price_aud")
        if model and price:
            groups.setdefault(model, []).append(price)
    return {m: statistics.median(p) for m, p in groups.items() if len(p) >= min_listings}


# ----------------------------------------------------------------------------
# Strategy A — aspect harvest → grounded listing text
# ----------------------------------------------------------------------------
def aspects_to_dict(detail: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for a in detail.get("localizedAspects", []) or []:
        name, value = a.get("name"), a.get("value")
        if name and value:
            out[name] = value
    return out


def build_listing_text(detail: dict, aspects: dict[str, str]) -> str:
    """Assemble a single grounded text blob from eBay's own structured fields.

    Everything Gemini is later asked to extract verbatim must appear here, so the
    repo's Stage 2 grounding firewall can validate it.
    """
    lines = [detail.get("title", "")]
    price = detail.get("price") or {}
    if price.get("value"):
        lines.append(f"Price: {price.get('currency')} {price.get('value')}")
    if detail.get("condition"):
        lines.append(f"Condition: {detail['condition']}")
    for name, value in aspects.items():
        lines.append(f"{name}: {value}")
    desc = detail.get("shortDescription") or detail.get("description") or ""
    if desc:
        lines.append(desc)
    loc = (detail.get("itemLocation") or {})
    if loc.get("city") or loc.get("stateOrProvince"):
        lines.append(f"Location: {loc.get('city', '')} {loc.get('stateOrProvince', '')}".strip())
    return "\n".join(ln for ln in lines if ln)


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


def recover_vram_from_images(client: genai.Client, model: str, detail: dict) -> dict | None:
    """Strategy D: OCR VRAM from listing photos. Returns None if nothing legible."""
    urls: list[str] = []
    if (detail.get("image") or {}).get("imageUrl"):
        urls.append(detail["image"]["imageUrl"])
    for img in detail.get("additionalImages", []) or []:
        if img.get("imageUrl"):
            urls.append(img["imageUrl"])
    urls = urls[:MAX_VISION_IMAGES]
    if not urls:
        return None

    parts: list = [types.Part.from_text(text=VISION_INSTRUCTION)]
    fetched = 0
    for url in urls:
        got = _fetch_image_bytes(url)
        if got:
            data, mime = got
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
            fetched += 1
    if fetched == 0:
        return None
    try:
        result = _gemini_json(client, model, parts, temperature=0.0)
    except Exception as exc:  # noqa: BLE001 - vision is best-effort
        log(f"vision VRAM recovery failed: {exc}")
        return None
    if result.get("vram_gb") and result.get("confidence", 0) >= 0.5:
        return result
    return None


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


def enrich_listing(client: genai.Client, model: str, detail: dict, listing_text: str) -> dict:
    parts = [types.Part.from_text(text=f"{ENRICH_INSTRUCTION}\n\nFULL LISTING TEXT:\n{listing_text}")]
    return _gemini_json(client, model, parts)


def build_metadata(row: dict, detail: dict) -> dict:
    seller = detail.get("seller") or {}
    price = detail.get("price") or {}
    signal = None
    if seller.get("feedbackScore") is not None:
        signal = f"{seller.get('feedbackScore')} feedback, {seller.get('feedbackPercentage')}% positive"
    return {
        "source_platform": "EBAY_AU",
        "listing_url_or_identifier": detail.get("itemWebUrl") or row.get("item_id"),
        "listing_title": detail.get("title") or row.get("title") or "",
        "listing_price_aud": _num(price.get("value")) if price.get("currency") == "AUD" else row.get("price_aud"),
        "seller_name_or_identifier": seller.get("username") or row.get("seller_username"),
        "seller_rating_or_profile_signal": signal or row.get("seller_feedback_pct"),
    }


def build_handoff(metadata: dict, triage: dict) -> dict:
    return {
        "source_platform": "EBAY_AU",
        "listing_title": metadata["listing_title"],
        "listing_price_aud": metadata["listing_price_aud"],
        "listing_url_or_identifier": metadata["listing_url_or_identifier"],
        "inferred_component_category": "SYSTEM",
        "inferred_model_hint": triage.get("canonical_model"),
        "inferred_gpu_hint": triage.get("gpu_guess"),
        "inferred_vram_hint": str(triage["vram_hint_gb"]) if triage.get("vram_hint_gb") else None,
        "inferred_condition_hint": None,
        "discovery_flags": [],
    }


def enrich_and_decide(
    client: genai.Client,
    model: str,
    token: str,
    row: dict,
    triage: dict,
    ref: dict,
    use_vision: bool,
) -> dict | None:
    """Strategy A+D on one listing → validated Stage 2 analysis + decision, or None."""
    item_id = row["item_id"]
    try:
        detail = get_item(token, item_id)
    except RuntimeError as exc:
        log(f"getItem {item_id} failed: {exc}")
        return None

    aspects = aspects_to_dict(detail)
    listing_text = build_listing_text(detail, aspects)

    try:
        extracted = enrich_listing(client, model, detail, listing_text)
    except Exception as exc:  # noqa: BLE001 - one bad listing shouldn't kill the run
        log(f"enrich {item_id} failed: {exc}")
        return None

    data = extracted.get("extracted_data", {})
    vision_evidence = None

    # Strategy D: if VRAM is still unknown, read it from the listing photos and
    # append the OCR provenance into the grounded text so the fact stays auditable.
    if use_vision and not data.get("vram_capacity"):
        vision_evidence = recover_vram_from_images(client, model, detail)
        if vision_evidence:
            quote = vision_evidence.get("verbatim_quote") or f"{vision_evidence['vram_gb']}GB (image)"
            provenance = f"[IMAGE EVIDENCE {vision_evidence.get('source', 'photo')}]: {quote}"
            listing_text = f"{listing_text}\n{provenance}"
            data["vram_capacity"] = {"semantic_value": float(vision_evidence["vram_gb"]), "verbatim_quote": quote}
            mi = data.setdefault("missing_information", {})
            mi["vram"] = False
            log(f"{item_id}: vision recovered VRAM = {vision_evidence['vram_gb']}GB")

    analysis = {
        "metadata": build_metadata(row, detail),
        "extracted_data": data,
        "analysis": extracted.get("analysis", {}),
    }
    handoff = build_handoff(analysis["metadata"], triage)

    # Reuse the repo's firewall: schema validation + data-integrity + grounding.
    try:
        analysis = run_stage2(handoff, listing_text, analysis)
    except Exception as exc:  # noqa: BLE001 - firewall/schema rejection drops one listing
        log(f"{item_id}: firewall rejected — {exc}")
        return None

    workload = os.environ.get("EBAY_HUNTER_WORKLOAD") or None
    decision = decide(analysis, ref, workload=workload)
    return {
        "item_id": item_id,
        "item_web_url": analysis["metadata"]["listing_url_or_identifier"],
        "canonical_model": triage.get("canonical_model"),
        "price_aud": analysis["metadata"]["listing_price_aud"],
        "vision_used": bool(vision_evidence),
        "analysis": analysis,
        "decision": decision,
    }


# ----------------------------------------------------------------------------
# Mispricing + alert gating (top acquisition only = SHORTLIST & underpriced)
# ----------------------------------------------------------------------------
def annotate_mispricing(result: dict, baselines: dict[str, float]) -> dict:
    model = result.get("canonical_model")
    price = result.get("price_aud")
    baseline = baselines.get(model) if model else None
    underpriced = False
    delta = None
    if baseline and price:
        delta = round(price - baseline, 2)
        underpriced = price <= baseline * (1 - UNDERPRICE_DISCOUNT)
    result["baseline_median_aud"] = baseline
    result["price_delta_aud"] = delta
    result["underpriced"] = underpriced
    return result


def is_top_acquisition(result: dict) -> bool:
    return result["decision"]["recommended_action"] == "SHORTLIST" and result["underpriced"]


# ----------------------------------------------------------------------------
# New-listing state (dedup so re-runs only alert on fresh finds)
# ----------------------------------------------------------------------------
def load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")).get("alerted_ids", []))
    except (OSError, json.JSONDecodeError):
        return set()


def save_seen(ids: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(
        json.dumps({"alerted_ids": sorted(ids), "updated_at": _now()}, indent=2), encoding="utf-8"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# Email alert (stdlib smtplib; no third-party account beyond your mailbox)
# ----------------------------------------------------------------------------
def render_email(alerts: list[dict]) -> str:
    lines = [f"{len(alerts)} new top-acquisition target(s) on eBay AU — {_now()}", ""]
    for a in sorted(alerts, key=lambda x: x["decision"]["llm_index_score"], reverse=True):
        d = a["decision"]
        delta = a.get("price_delta_aud")
        delta_str = f"{delta:+.0f} vs median" if delta is not None else "no baseline"
        lines += [
            f"● {a['canonical_model'] or a['analysis']['metadata']['listing_title']}",
            f"    AUD {a['price_aud']}  ({delta_str}; median {a.get('baseline_median_aud')})",
            f"    VRAM {d['vram_gb']}GB · index {d['llm_index_score']}/100 · {d['recommended_action']}"
            + (" · vision-verified VRAM" if a.get("vision_used") else ""),
            f"    {'; '.join(d['reasons'][:2])}",
            f"    {a['item_web_url']}",
            "",
        ]
    return "\n".join(lines)


def send_email(alerts: list[dict]) -> bool:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to_addr = os.environ.get("ALERT_EMAIL_TO", user)
    from_addr = os.environ.get("ALERT_EMAIL_FROM", user)
    if not (user and password and to_addr):
        log("SMTP not configured (SMTP_USER/SMTP_PASSWORD/ALERT_EMAIL_TO) — skipping email")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"[laptopfinder] {len(alerts)} new AU acquisition target(s)"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(render_email(alerts))

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.send_message(msg)
    log(f"emailed {len(alerts)} alert(s) to {to_addr}")
    return True


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------
def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run(args: argparse.Namespace) -> int:
    ref = load_ref()
    model = args.model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    client = gemini_client()
    token = get_ebay_token()

    log("Stage B — sweeping eBay AU market via Browse API...")
    corpus = collect_corpus(token, ref, args.max_per_query)
    write_jsonl(CORPUS_PATH, corpus)
    log(f"corpus: {len(corpus)} unique listings → {CORPUS_PATH}")
    if not corpus:
        log("empty corpus — nothing to do")
        return 0

    log("Stage B — single long-context Gemini triage pass...")
    triage = triage_corpus(client, model, corpus)
    min_listings = ref.get("data_integrity", {}).get("min_listings_for_baseline", 3)
    baselines = compute_baselines(corpus, triage, min_listings)
    log(f"triage classified {len(triage)} listings; {len(baselines)} model baselines")

    # Select enrichment candidates: relevant, highest priority first (Strategy A+D is costly).
    candidates = [
        r for r in corpus
        if triage.get(r["item_id"], {}).get("is_relevant", not triage)  # if triage empty, take all
    ]
    candidates.sort(key=lambda r: triage.get(r["item_id"], {}).get("priority", 0), reverse=True)
    candidates = candidates[: args.enrich_top]
    log(f"Stage A+D — enriching top {len(candidates)} candidates (getItem + aspects + vision)...")

    results: list[dict] = []
    for row in candidates:
        t = triage.get(row["item_id"], {})
        result = enrich_and_decide(client, model, token, row, t, ref, use_vision=not args.no_vision)
        if result:
            results.append(annotate_mispricing(result, baselines))

    write_jsonl(RESULTS_PATH, results)
    shortlist = [r for r in results if r["decision"]["recommended_action"] == "SHORTLIST"]
    top = [r for r in results if is_top_acquisition(r)]
    log(f"scored {len(results)} listings — {len(shortlist)} SHORTLIST, {len(top)} top-acquisition")

    # New-listing gating + email.
    seen = load_seen()
    fresh = [r for r in top if r["item_id"] not in seen]
    log(f"{len(fresh)} of {len(top)} top-acquisition targets are NEW since last run")

    if fresh and not args.no_email and not args.dry_run:
        try:
            send_email(fresh)
        except (smtplib.SMTPException, OSError) as exc:
            log(f"email send failed: {exc}")
    elif fresh:
        log("email suppressed (--dry-run/--no-email) — preview:\n" + render_email(fresh))

    if not args.dry_run:
        save_seen(seen | {r["item_id"] for r in fresh})

    # Console digest.
    for r in sorted(top, key=lambda x: x["decision"]["llm_index_score"], reverse=True)[:10]:
        d = r["decision"]
        log(f"  ★ {r['canonical_model']} | AUD {r['price_aud']} (Δ{r.get('price_delta_aud')}) "
            f"| {d['vram_gb']}GB | index {d['llm_index_score']} | {r['item_web_url']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m laptopfinder.runners.ebay_hunter",
        description="One-shot eBay AU acquisition sweep for local-LLM hardware (scraper-free).",
    )
    p.add_argument("--max-per-query", type=int, default=200, help="Cap items fetched per query (default 200)")
    p.add_argument("--enrich-top", type=int, default=25, help="How many top candidates to deep-enrich (default 25)")
    p.add_argument("--model", default=None, help="Gemini model id (default env GEMINI_MODEL or gemini-3.5-flash)")
    p.add_argument("--no-vision", action="store_true", help="Disable Strategy D image VRAM recovery")
    p.add_argument("--no-email", action="store_true", help="Score and persist but never send email")
    p.add_argument("--dry-run", action="store_true", help="No email and do not update seen-items state")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return run(args)
    except (ValueError, RuntimeError) as exc:
        log(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
