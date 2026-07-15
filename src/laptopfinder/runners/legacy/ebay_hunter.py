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

import argparse
import os
import smtplib
import sys
from pathlib import Path

from dotenv import load_dotenv

from laptopfinder.decide import load_ref


from .hunter.api import get_ebay_token, log
from .hunter.search import collect_corpus
from .hunter.llm import gemini_client, triage_corpus
from .hunter.enrich import enrich_and_decide
from .hunter.score import compute_baselines, annotate_mispricing, is_top_acquisition
from .hunter.state import load_seen, save_seen, write_jsonl
from .hunter.alert import send_email, render_email
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


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




# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------


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

    if args.no_enrich:
        log(f"--no-enrich: skipping Gemini triage and enrichment. Corpus written to {CORPUS_PATH}")
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
    candidates.sort(
        key=lambda r: float(triage.get(r["item_id"], {}).get("priority") or 0),
        reverse=True,
    )
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
    for r in sorted(top, key=lambda x: float(x.get("decision", {}).get("llm_index_score") or 0), reverse=True)[:10]:
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
    p.add_argument("--no-enrich", action="store_true", help="Stop after corpus collection — skip Gemini triage and enrichment (no LLM calls)")
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
