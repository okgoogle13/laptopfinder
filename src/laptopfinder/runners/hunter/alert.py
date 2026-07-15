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
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


from .state import _now
from .api import log
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










# ----------------------------------------------------------------------------
# Mispricing + alert gating (top acquisition only = SHORTLIST & underpriced)
# ----------------------------------------------------------------------------




# ----------------------------------------------------------------------------
# New-listing state (dedup so re-runs only alert on fresh finds)
# ----------------------------------------------------------------------------






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
    try:
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
    except Exception as exc:
        log(f"SMTP error: failed to send email alerts: {exc}")
        return False


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------








