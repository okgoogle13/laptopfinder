"""Stage 1 (Discovery) fixture-driven tests.

Validates that:
  - Valid Stage 1 fixtures pass schema validation and the hint/fact
    firewall (only inferred_* fields permitted).
  - A fixture leaking a fact-shaped key (e.g. "gpu") is rejected by the
    firewall check.
  - A structurally invalid fixture is rejected by schema validation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from laptopfinder.core import (
    run_stage1,
    run_stage1_from_fixture,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "stage1"

VALID_FIXTURES = [
    "ebay_rtx4090_laptop.json",
    "fb_vague_gpu_desktop.json",
    "gumtree_mixed_batch.json",
]


@pytest.mark.parametrize("fixture_name", VALID_FIXTURES)
def test_valid_stage1_fixture_passes(fixture_name: str) -> None:
    result = run_stage1_from_fixture(FIXTURES_DIR / fixture_name)
    assert isinstance(result, list)
    assert len(result) >= 1
    for candidate in result:
        assert candidate["source_platform"] in {
            "EBAY_AU",
            "FB_MARKETPLACE",
            "GUMTREE",
            "UNKNOWN",
        }
        assert 0.0 <= candidate["discovery_confidence"] <= 1.0


def test_stage1_strict_null_handling_on_vague_listing() -> None:
    """The FB vague-listing fixture has no inferable specs; every
    inferred_* field except category must be null, never fabricated."""
    result = run_stage1_from_fixture(FIXTURES_DIR / "fb_vague_gpu_desktop.json")
    candidate = result[0]
    assert candidate["listing_price_aud"] is None
    assert candidate["inferred_model_hint"] is None
    assert candidate["inferred_gpu_hint"] is None
    assert candidate["inferred_vram_hint"] is None
    assert candidate["inferred_condition_hint"] is None


def test_stage1_rejects_fact_leak_via_firewall() -> None:
    """A Stage 1 candidate carrying a fact-shaped key ("gpu") must be
    rejected by the hint/fact firewall, independent of schema shape."""
    with pytest.raises(ValueError):
        run_stage1_from_fixture(FIXTURES_DIR / "invalid_fact_leak.json")


def test_stage1_rejects_non_list_payload() -> None:
    with pytest.raises(TypeError):
        run_stage1({"not": "a list"})  # type: ignore[arg-type]


def test_stage1_rejects_schema_invalid_payload() -> None:
    bad_payload = [
        {
            "source_platform": "NOT_A_REAL_PLATFORM",
            "listing_title": "x",
            "listing_price_aud": None,
            "listing_url_or_identifier": None,
            "inferred_component_category": "GPU",
            "inferred_model_hint": None,
            "inferred_gpu_hint": None,
            "inferred_vram_hint": None,
            "inferred_condition_hint": None,
            "discovery_flags": [],
            "discovery_confidence": 0.5,
        }
    ]
    with pytest.raises(ValueError):
        run_stage1(bad_payload)


def test_stage1_rejects_missing_required_field() -> None:
    bad_payload = [
        {
            "source_platform": "EBAY_AU",
            "listing_title": "x",
            "listing_price_aud": None,
            "listing_url_or_identifier": None,
            "inferred_component_category": "GPU",
            "inferred_model_hint": None,
            "inferred_gpu_hint": None,
            "inferred_vram_hint": None,
            "inferred_condition_hint": None,
            "discovery_flags": [],
            # discovery_confidence intentionally omitted
        }
    ]
    with pytest.raises(ValueError):
        run_stage1(bad_payload)
