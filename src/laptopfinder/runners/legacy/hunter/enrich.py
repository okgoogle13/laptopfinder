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

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from laptopfinder.core import run_stage2
from laptopfinder.decide import decide

from .api import get_item, log
from .llm import recover_vram_from_images, enrich_listing
from .search import _num
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




# ----------------------------------------------------------------------------
# eBay OAuth (client-credentials application token, self-refreshing)
# ----------------------------------------------------------------------------






# ----------------------------------------------------------------------------
# eBay Browse API (structured JSON — the scraper replacement)
# ----------------------------------------------------------------------------












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




# ----------------------------------------------------------------------------
# New-listing state (dedup so re-runs only alert on fresh finds)
# ----------------------------------------------------------------------------






# ----------------------------------------------------------------------------
# Email alert (stdlib smtplib; no third-party account beyond your mailbox)
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------








