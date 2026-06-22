"""Stage 2 (Analysis) fixture-driven tests.

Validates that:
  - Valid Stage 2 fixtures pass schema validation and the hint/fact
    firewall (facts grounded in full_listing_text).
  - A fixture promoting a hint to a fact without textual support is
    rejected by the firewall check.
  - risk_score must be a number in [0, 10], enforced by the schema.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import json

from laptopfinder.core import (
    run_stage2,
    run_stage2_from_fixture,
)

def load_fixture(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "stage2"

VALID_FIXTURES = [
    "ebay_facts_grounded.json",
    "gumtree_hint_not_promoted.json",
    "fb_high_risk_listing.json",
]


@pytest.mark.parametrize("fixture_name", VALID_FIXTURES)
def test_valid_stage2_fixture_passes(fixture_name: str) -> None:
    result = run_stage2_from_fixture(FIXTURES_DIR / fixture_name)
    analysis = result["analysis"]
    assert isinstance(analysis["risk_score"], float)
    assert 0.0 <= analysis["risk_score"] <= 10.0
    assert 0.0 <= analysis["confidence"] <= 1.0


def test_stage2_hint_not_promoted_without_textual_support() -> None:
    """The Gumtree fixture's handoff hint (RTX 3090 / 24GB) is NOT
    restated in full_listing_text, so extracted_data facts for gpu and
    vram_capacity must remain null — confirming the firewall holds in
    the no-evidence direction, not just that it rejects bad input."""
    result = run_stage2_from_fixture(FIXTURES_DIR / "gumtree_hint_not_promoted.json")
    extracted = result["extracted_data"]
    assert extracted["gpu"] is None
    assert extracted["vram_capacity"] is None
    assert extracted["exact_model_name"] is None


def test_stage2_rejects_ungrounded_fact_via_firewall() -> None:
    """A Stage 2 fact (gpu="RTX 3080 Ti") not present anywhere in
    full_listing_text must be rejected by the hint/fact firewall."""
    with pytest.raises(ValueError):
        run_stage2_from_fixture(FIXTURES_DIR / "invalid_ungrounded_fact.json")


def test_stage2_rejects_out_of_range_risk_score_via_schema() -> None:
    """risk_score outside [0, 10] must be rejected — enforced by
    laptopfinder/schemas/stage2.analysis.schema.json's minimum/maximum
    constraints,
    not by a separate Python-level type check."""
    payload = load_fixture(FIXTURES_DIR / "ebay_facts_grounded.json")
    payload["analysis_output"]["analysis"]["risk_score"] = 11.5
    with pytest.raises(ValueError):
        run_stage2(
            payload["handoff_packet"],
            payload["full_listing_text"],
            payload["analysis_output"],
        )


def test_stage2_rejects_schema_invalid_handoff_packet() -> None:
    bad_handoff = {
        "source_platform": "EBAY_AU",
        "listing_title": "x",
        "listing_price_aud": None,
        "listing_url_or_identifier": None,
        "inferred_component_category": None,
        "inferred_model_hint": None,
        "inferred_gpu_hint": None,
        "inferred_vram_hint": None,
        "inferred_condition_hint": None,
        # discovery_flags intentionally omitted (required field)
    }
    minimal_valid_analysis = {
        "metadata": {
            "source_platform": "EBAY_AU",
            "listing_url_or_identifier": None,
            "listing_title": "x",
            "listing_price_aud": None,
            "seller_name_or_identifier": None,
            "seller_rating_or_profile_signal": None,
        },
        "extracted_data": {
            "exact_model_name": None,
            "component_category": "OTHER",
            "cpu": None,
            "gpu": None,
            "ram": None,
            "storage": None,
            "vram_capacity": None,
            "stated_condition": None,
            "shipping_or_pickup_signal": "UNKNOWN",
            "missing_information": [],
        },
        "analysis": {
            "risk_score": 5.0,
            "risk_flags": [],
            "stated_pickup_location": None,
            "confidence": 0.5,
        },
    }
    with pytest.raises(ValueError):
        run_stage2(bad_handoff, "some listing text", minimal_valid_analysis)


def test_stage2_rejects_substring_collision_via_firewall() -> None:
    """A fact (ram='4GB') that is only a substring of a different value
    in the text ('64GB') must be rejected. This catches false positives
    from naive substring matching."""
    with pytest.raises(ValueError, match="firewall violation"):
        run_stage2_from_fixture(FIXTURES_DIR / "invalid_substring_collision.json")

