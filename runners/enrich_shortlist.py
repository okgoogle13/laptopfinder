#!/usr/bin/env python3
"""
enrich_shortlist.py — Bridge between ebay_sniper.py (shallow hits) and decide.py (deep scoring).

Reads raw SHORTLIST hits from output/decisions/latest_decisions.json,
fetches full listing text via Firecrawl, runs LLM extraction (Stage 2),
filters outreach questions via qna_filter, passes enriched records through decide(),
and writes a ranked report to the --output path.

Usage:
    python runners/enrich_shortlist.py [--output path/to/report.md]
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from src.laptopfinder.decide import decide, load_ref, _comps_adjustment_points
from src.laptopfinder.qna_filter import filter_questions

# Firecrawl Pipedream webhook
FIRECRAWL_WEBHOOK = os.environ.get("FIRECRAWL_WEBHOOK_URL", "https://hooks.pipedream.com/steps/your_firecrawl_step_id")

# LLM client (Anthropic Claude)
from anthropic import Anthropic
LLM_CLIENT = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "sk-ant-dummy"))

# Stage 2 LLM extraction prompt
STAGE2_EXTRACTION_PROMPT = """
You are extracting structured hardware and seller data from an eBay laptop listing.

INPUT: Full HTML or text content of an eBay listing.

OUTPUT: A single JSON object with this exact schema:

{
  "extracted_data": {
    "gpu": "RTX 5090",
    "cpu": "Intel Core Ultra 9 275HX",
    "exact_model_name": "AORUS Master 16 BZH",
    "vram_capacity": "24GB",
    "total_system_ram": "32GB",
    "storage_tb": 2.0,
    "screen_size_inches": 16,
    "tgp_system_watts": 175,
    "touchscreen_digitizer": null,
    "egpu_model": null,
    "stated_condition": "New",
    "missing_information": {
      "storage": false,
      "tgp": false,
      "screen_size": false
    }
  },
  "analysis": {
    "risk_score": 1.2,
    "seller_classification": "ESTABLISHED_RESELLER"
  },
  "metadata": {
    "source_platform": "EBAY_US",
    "ships_from_overseas": true,
    "seller_trust_score": 20874,
    "comps_median_sold_aud": 3500.00,
    "listing_price_aud": 2701.00
  }
}

EXTRACTION RULES:
1. GPU: Extract exact model (e.g., "RTX 5090", "RTX 5080"). Default RTX 5090 = 24GB VRAM.
2. CPU: Extract full model name (e.g., "Intel Core Ultra 9 275HX").
3. RAM: Extract in GB (e.g., 32, 64, 96).
4. Storage: Extract in TB (e.g., 1.0, 2.0, 4.0). If unknown, set to null and flag in missing_information.
5. Screen size: Extract in inches (16 or 18).
6. TGP: Extract system TGP in watts if specified; otherwise null and flag.
7. Condition: Extract from listing (New, Used, Refurbished, Open Box, For Parts).
8. Seller classification: RETAILER_WITH_WARRANTY, ESTABLISHED_RESELLER, INDIVIDUAL_SELLER, or UNKNOWN.
9. Risk score: 0.0–10.0 based on seller feedback %, transaction count, and listing quality.
10. Ships from overseas: true if seller is not in AU.
11. Seller trust score: feedback_score × (feedback_positive_pct / 100).
12. Comps median sold AUD: Research 5-10 sold comparable listings (same GPU/CPU, similar RAM/storage) and calculate median sale price in AUD. If no sold comps exist, set to null.

If any field is missing or unclear, set it to null and add a flag in missing_information.

DATA INTEGRITY CHECK:
- If the listing mentions "parts only", "salvaged", "for parts", "missing motherboard", or "not working", set risk_score to 10.0 and seller_classification to UNKNOWN.
"""


def fetch_listing_html(url: str) -> str:
    """Fetch full listing HTML via Firecrawl Pipedream webhook."""
    import requests
    response = requests.post(FIRECRAWL_WEBHOOK, json={"url": url})
    response.raise_for_status()
    result = response.json()
    return result.get("text", "") or result.get("html", "")


def run_stage2_extraction(listing_content: str) -> dict:
    """Run LLM extraction (Stage 2) on listing content."""
    response = LLM_CLIENT.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {"role": "system", "content": "You are a precise data extraction assistant. Output valid JSON only."},
            {"role": "user", "content": f"{STAGE2_EXTRACTION_PROMPT}\n\nLISTING CONTENT:\n{listing_content[:50000]}"},
        ],
    )
    content = response.content[0].text
    return json.loads(content)


def check_data_integrity(analysis: dict) -> None:
    """Raise ValueError if listing is parts-only or salvaged hardware."""
    ref = load_ref()
    exclusion_pattern = ref.get("data_integrity", {}).get("exclusion_regex")
    if not exclusion_pattern:
        return
    title = analysis.get("metadata", {}).get("listing_title", "")
    if re.search(exclusion_pattern, title, re.IGNORECASE):
        raise ValueError(f"Data integrity violation: salvaged/parts-only listing detected ({title})")


def generate_outreach_messages(listing: dict, offer_target: float, logistics_preference: bool = True) -> dict:
    """Draft two seller outreach messages using qna_filter."""
    candidate_questions = [
        "Does it come with the original charger?",
        "What condition is it in cosmetically?",
        "Is the warranty still valid?",
        "Do you accept returns?",
        "Are there any scratches or wear on the screen?",
        "Has it been used for gaming or just work?",
    ]
    filtered_questions = filter_questions(candidate_questions, listing)

    message_a = (
        f"Hi! I'm interested in your {listing.get('exact_model_name', 'laptop')}.\n\n"
        f"I saw you mentioned it's in {listing.get('stated_condition', 'used')} condition. Quick questions:\n"
        + "\n".join(f"- {q}" for q in filtered_questions[:3])
        + "\n\nThanks!"
    )
    message_b = (
        f"Hi again! Thanks for the info.\n\n"
        f"Based on comparable sold listings, I'd like to offer ${offer_target:.0f} AUD. "
        f"I can arrange {'local pickup to save you shipping hassle' if logistics_preference else 'prompt payment via PayPal'}.\n\n"
        "Would that work for you?"
    )
    return {"message_a": message_a, "message_b": message_b, "filtered_questions": filtered_questions}


def _comps_position_label(analysis: dict) -> str:
    """Return a human-readable pricing position vs sold comps."""
    metadata = analysis.get("metadata", {})
    comps_median = metadata.get("comps_median_sold_aud")
    listing_price = metadata.get("listing_price_aud")
    if not comps_median or not listing_price:
        return "unknown (no comps)"
    try:
        ratio = float(listing_price) / float(comps_median)
    except (ValueError, TypeError, ZeroDivisionError):
        return "unknown (invalid data)"
    pct = (ratio - 1.0) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.0f}% vs comps median (${comps_median:,.0f})"


def _missing_facts(enriched: dict) -> list[str]:
    """Return list of fact fields that are null or flagged missing."""
    missing = []
    extracted = enriched.get("extracted_data", {})
    mi = extracted.get("missing_information", {})
    if isinstance(mi, dict):
        missing.extend(k for k, v in mi.items() if v)
    # Also check key facts directly
    for field in ("gpu", "vram_capacity", "cpu", "total_system_ram"):
        if not extracted.get(field):
            if field not in missing:
                missing.append(field)
    return missing


def _derive_enriched_action(enriched: dict) -> str:
    """
    Map decide() output + comps position to a buyer-facing action.

    BUY_NOW    — SHORTLIST + priced at or below comps median (ratio <= 1.0)
    NEGOTIATE  — SHORTLIST + priced above comps median but ratio < 1.15
    WATCH      — SHORTLIST + ratio >= 1.15, no comps data, or MONITOR from decide()
    VERIFY     — SHORTLIST but critical facts missing (gpu or vram unknown)
    PASS       — SKIP from decide(), or risk gate failed
    """
    decide_action = enriched.get("recommended_action", "SKIP")

    if decide_action == "SKIP":
        return "PASS"
    if decide_action == "MONITOR":
        return "WATCH"

    # decide_action == "SHORTLIST"
    missing = _missing_facts(enriched)
    critical_missing = [f for f in missing if f in ("gpu", "vram_capacity")]
    if critical_missing:
        return "VERIFY"

    metadata = enriched.get("metadata", {})
    comps_median = metadata.get("comps_median_sold_aud")
    listing_price = metadata.get("listing_price_aud")

    if not comps_median or not listing_price:
        return "WATCH"

    try:
        ratio = float(listing_price) / float(comps_median)
    except (ValueError, TypeError, ZeroDivisionError):
        return "WATCH"

    if ratio <= 1.0:
        return "BUY_NOW"
    if ratio < 1.15:
        return "NEGOTIATE"
    return "WATCH"


def _rank_candidates(candidates: list[dict]) -> list[dict]:
    """
    Sort enriched candidates by descending priority.

    Primary:  action rank (BUY_NOW > NEGOTIATE > WATCH > VERIFY > PASS)
    Secondary: llm_index_score descending
    Tertiary:  comps_adjustment (already baked into score; use listing_price ascending as tiebreak)
    """
    action_rank = {"BUY_NOW": 0, "NEGOTIATE": 1, "WATCH": 2, "VERIFY": 3, "PASS": 4}

    def sort_key(c: dict):
        action = c.get("action", "PASS")
        score = c.get("llm_index_score", 0)
        price = c.get("metadata", {}).get("listing_price_aud") or float("inf")
        return (action_rank.get(action, 4), -score, price)

    return sorted(candidates, key=sort_key)


def _build_markdown_report(candidates: list[dict], run_ts: str) -> str:
    """Render enriched candidates as a prioritised markdown report."""
    lines = [
        f"# Enriched Shortlist — {run_ts}",
        "",
        f"**{len(candidates)} candidate(s)** ranked by action priority then capability score.",
        "",
    ]

    action_emoji = {
        "BUY_NOW": "🟢",
        "NEGOTIATE": "🟡",
        "WATCH": "🔵",
        "VERIFY": "🟠",
        "PASS": "🔴",
    }

    for i, c in enumerate(candidates, 1):
        action = c.get("action", "PASS")
        emoji = action_emoji.get(action, "⚪")
        title = c.get("title") or c.get("extracted_data", {}).get("exact_model_name") or "Unknown listing"
        score = c.get("llm_index_score", 0)
        score_100 = c.get("score_0_100", 0)
        url = c.get("url", "")
        price = c.get("metadata", {}).get("listing_price_aud") or c.get("price_aud", 0)
        comps_label = _comps_position_label(c)
        risk = c.get("analysis", {}).get("risk_score", "?")
        condition = c.get("extracted_data", {}).get("stated_condition") or "Unknown"
        vram = c.get("vram_gb")
        vram_str = f"{vram}GB" if vram else "Unknown"
        gpu = c.get("extracted_data", {}).get("gpu") or "Unknown"
        paradigm = c.get("paradigm", "")
        reasons = c.get("reasons", [])
        missing = _missing_facts(c)

        lines.append(f"## {i}. {emoji} `{action}` — {title}")
        lines.append("")
        lines.append(f"- **URL**: {url}")
        lines.append(f"- **Price**: ${price:,.2f} AUD")
        lines.append(f"- **Score**: {score}/100 (normalised: {score_100}/100) | Paradigm: `{paradigm}`")
        lines.append(f"- **GPU**: {gpu} | VRAM: {vram_str} | Condition: {condition}")
        lines.append(f"- **Comps position**: {comps_label}")
        lines.append(f"- **Risk score**: {risk}")

        if missing:
            lines.append(f"- ⚠️ **Missing facts**: {', '.join(missing)}")

        if reasons:
            lines.append(f"- **Decide reasons**: {'; '.join(reasons)}")

        if "outreach_messages" in c:
            lines.append("")
            lines.append("**Outreach drafts:**")
            lines.append(f"> **Message A (clarification):** {c['outreach_messages'].get('message_a', '').splitlines()[0]}…")
            lines.append(f"> **Message B (offer):** {c['outreach_messages'].get('message_b', '').splitlines()[0]}…")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def enrich_decision(decision: dict) -> dict:
    """Enrich a single sniper decision with Stage 2 extraction and scoring."""
    url = decision["url"]

    # Fetch listing content
    print(f"  → Fetching {url} via Firecrawl...")
    listing_content = fetch_listing_html(url)

    # Run LLM extraction
    print(f"  → Running Stage 2 extraction...")
    extracted = run_stage2_extraction(listing_content)

    # Merge extracted data with original decision properly nested
    enriched = {
        **decision,
        "extracted_data": extracted["extracted_data"],
        "analysis": extracted["analysis"],
        "metadata": extracted["metadata"],
    }

    # Data integrity check
    check_data_integrity(enriched)

    # Pass through decide() to get llm_index_score, score_0_100, recommended_action, reasons
    scoring_result = decide(enriched)
    enriched.update(scoring_result)

    # Derive buyer-facing action from decide() output + comps position
    enriched["action"] = _derive_enriched_action(enriched)

    # Generate outreach messages for shortlisted candidates
    if enriched["action"] in ("BUY_NOW", "NEGOTIATE"):
        print(f"  → Generating outreach messages...")
        enriched["outreach_messages"] = generate_outreach_messages(
            enriched,
            offer_target=enriched.get("metadata", {}).get("comps_median_sold_aud") or decision.get("price_aud", 0),
            logistics_preference=True,
        )

    return enriched


def load_sniper_decisions(decisions_path: Path) -> list:
    """Load raw SHORTLIST hits from ebay_sniper.py output."""
    with open(decisions_path, "r") as f:
        decisions = json.load(f)
    return [d for d in decisions if d.get("action") == "SHORTLIST"]


def main():
    parser = argparse.ArgumentParser(description="Enrich shortlist candidates")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/shortlist/latest_enriched.md"),
        help="Path to output file (.md for report, other for JSONL)",
    )
    args = parser.parse_args()

    decisions_path = Path("output/decisions/latest_decisions.json")
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not decisions_path.exists():
        print(f"❌ No decisions file found at {decisions_path}")
        print("   Run 'make live' first to generate latest_decisions.json")
        return

    decisions = load_sniper_decisions(decisions_path)
    print(f"Loaded {len(decisions)} SHORTLIST hits from {decisions_path}")

    if not decisions:
        print("No SHORTLIST candidates to enrich. Exiting.")
        return

    # Enrich each decision
    enriched_candidates = []
    for i, decision in enumerate(decisions, 1):
        print(f"Enriching [{i}/{len(decisions)}]: {decision.get('title', decision.get('url'))}")
        try:
            enriched = enrich_decision(decision)
            enriched_candidates.append(enriched)
            print(f"  ✅ Score: {enriched['llm_index_score']}/100, Action: {enriched['action']}")
        except Exception as e:
            print(f"  ⚠️  Error enriching {decision.get('url')}: {e}")
            continue

    # Atomic write to output_path
    if enriched_candidates:
        ranked = _rank_candidates(enriched_candidates)

        if output_path.suffix == ".md":
            run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            report_text = _build_markdown_report(ranked, run_ts)
        else:
            report_lines = [
                json.dumps({k: v for k, v in c.items() if k != "outreach_messages"})
                for c in ranked
            ]
            report_text = "\n".join(report_lines) + "\n"

        tmp = output_path.with_suffix(".tmp")
        tmp.write_text(report_text, encoding="utf-8")
        tmp.replace(output_path)

        print(f"\n✅ Atomically wrote {len(ranked)} enriched candidates to {output_path}")
        action_counts = {}
        for c in ranked:
            a = c.get("action", "PASS")
            action_counts[a] = action_counts.get(a, 0) + 1
        for action, count in sorted(action_counts.items()):
            print(f"   {action}: {count}")
    else:
        print("\n⚠️  No candidates successfully enriched.")


if __name__ == "__main__":
    main()
