"""
Drops seller-outreach questions whose answer is already present in an
eBay listing (description text, aspects, or returnTerms) — used by the
ebay-market-analyzer skill's Step 5 before drafting clarifying questions.

    .venv/bin/python -m laptopfinder.qna_filter <listing.json> <questions.json>

Both files hold JSON: listing.json is an ebay_api.summarize() dict,
questions.json is a JSON array of candidate question strings.
"""

from __future__ import annotations

import argparse
import json
import sys

# domain -> keywords that indicate the domain is discussed
KEYWORD_MAP = {
    "condition": ["condition", "cosmetic", "scratch", "wear", "damage"],
    "warranty": ["warranty", "guarantee"],
    "accessories": ["charger", "power adapter", "adapter", "box", "packaging", "accessor"],
    "returns": ["return", "refund"],
}


def build_fact_view(listing: dict) -> dict:
    """Which domains does this listing already cover, from description/aspects/returnTerms."""
    text = (listing.get("description_text") or "").lower()
    aspects = " ".join(f"{k} {v}" for k, v in (listing.get("aspects") or {}).items()).lower()
    haystack = f"{text} {aspects}"

    facts = {domain: any(kw in haystack for kw in keywords) for domain, keywords in KEYWORD_MAP.items()}
    if listing.get("returns_accepted") is not None:
        facts["returns"] = True
    return facts


def question_is_already_answered(question: str, facts: dict) -> bool:
    q = question.lower()
    return any(
        facts.get(domain) and any(kw in q for kw in keywords)
        for domain, keywords in KEYWORD_MAP.items()
    )


def filter_questions(questions: list[str], listing: dict) -> list[str]:
    facts = build_fact_view(listing)
    return [q for q in questions if not question_is_already_answered(q, facts)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("listing_json", help="Path to a JSON file holding an ebay_api.summarize() dict")
    parser.add_argument("questions_json", help="Path to a JSON file holding an array of candidate questions")
    args = parser.parse_args()

    with open(args.listing_json) as f:
        listing = json.load(f)
    with open(args.questions_json) as f:
        questions = json.load(f)

    print(json.dumps(filter_questions(questions, listing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
