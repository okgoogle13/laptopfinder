"""Decision engine (decide.py) fixture-driven tests.

Validates that:
  - Unicorn hardware is shortlisted with override eligibility.
  - Monitor-list GPUs route to MONITOR.
  - High-risk listings are skipped via the low-risk gate.
  - Capability band classification works across all bands.
  - Listings with no VRAM data are skipped gracefully.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from laptopfinder.decide import (
    classify_capability_band,
    check_low_risk_gate,
    check_monitor_list,
    check_unicorn,
    decide,
    load_reference_layer,
    _parse_vram_gb,
)

REF = load_reference_layer()
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "stage2"


def load_fixture(name: str) -> dict:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


# --- Unit tests for sub-functions ---

class TestParseVramGb:
    def test_standard(self):
        assert _parse_vram_gb("16GB GDDR6") == 16.0

    def test_bare(self):
        assert _parse_vram_gb("24GB") == 24.0

    def test_none(self):
        assert _parse_vram_gb(None) is None

    def test_unparseable(self):
        assert _parse_vram_gb("lots of memory") is None

    def test_decimal(self):
        assert _parse_vram_gb("11.5GB") == 11.5


class TestClassifyCapabilityBand:
    def test_entry(self):
        assert classify_capability_band(8.0, REF) == "ENTRY_LOCAL_LLM"
        assert classify_capability_band(12.0, REF) == "ENTRY_LOCAL_LLM"

    def test_mid_tier(self):
        assert classify_capability_band(16.0, REF) == "MID_TIER_LOCAL_LLM"

    def test_strong(self):
        assert classify_capability_band(24.0, REF) == "STRONG_8B_14B"

    def test_quantized_70b(self):
        assert classify_capability_band(64.0, REF) == "POSSIBLE_70B_QUANTIZED"
        assert classify_capability_band(128.0, REF) == "POSSIBLE_70B_QUANTIZED"

    def test_none(self):
        assert classify_capability_band(None, REF) is None

    def test_below_range(self):
        assert classify_capability_band(4.0, REF) is None


class TestCheckUnicorn:
    def test_gpu_match(self):
        assert check_unicorn(None, "RTX 3090", REF) is True

    def test_model_match(self):
        assert check_unicorn("MSI Titan 18 HX", None, REF) is True

    def test_no_match(self):
        assert check_unicorn("HP Pavilion", "GTX 1650", REF) is False

    def test_none_inputs(self):
        assert check_unicorn(None, None, REF) is False


class TestCheckMonitorList:
    def test_monitor_gpu(self):
        assert check_monitor_list("RTX 5090", REF) is True

    def test_non_monitor_gpu(self):
        assert check_monitor_list("RTX 4090", REF) is False

    def test_none(self):
        assert check_monitor_list(None, REF) is False


class TestCheckLowRiskGate:
    def test_passes(self):
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        assert check_low_risk_gate(analysis, REF) is True

    def test_fails_high_risk(self):
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        assert check_low_risk_gate(analysis, REF) is False


# --- Integration tests using decide() ---

class TestDecide:
    def test_unicorn_shortlisted(self):
        """The eBay MSI Titan 18 HX with RTX 4090 should be shortlisted
        as unicorn hardware with exceptional distance override."""
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert result["is_unicorn"] is True
        assert result["capability_band"] == "MID_TIER_LOCAL_LLM"
        assert result["exceptional_distance_override"] is True

    def test_high_risk_skipped(self):
        """The FB scam-like RTX 4090 listing should be skipped
        due to failing the low-risk gate."""
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SKIP"
        assert result["low_risk_gate_passed"] is False

    def test_hint_not_promoted_skipped(self):
        """The Gumtree fixture with null gpu/vram should be skipped
        as there's no VRAM data to classify."""
        analysis = load_fixture("gumtree_hint_not_promoted.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["capability_band"] is None
        assert result["vram_gb"] is None

    def test_monitor_routing(self):
        """A listing with an aspirational GPU should route to MONITOR."""
        # Construct a minimal analysis with a monitor-list GPU
        analysis = {
            "metadata": {
                "source_platform": "EBAY_AU",
                "listing_url_or_identifier": None,
                "listing_title": "RTX 5090 GPU",
                "listing_price_aud": 3000.0,
                "seller_name_or_identifier": None,
                "seller_rating_or_profile_signal": None,
            },
            "extracted_data": {
                "exact_model_name": None,
                "component_category": "GPU",
                "cpu": None,
                "gpu": "RTX 5090",
                "ram": None,
                "storage": None,
                "vram_capacity": "32GB",
                "stated_condition": "New",
                "shipping_or_pickup_signal": "BOTH",
                "missing_information": [],
            },
            "analysis": {
                "risk_score": 1.0,
                "risk_flags": [],
                "stated_pickup_location": "Melbourne VIC",
                "confidence": 0.9,
            },
        }
        result = decide(analysis, REF)
        assert result["recommended_action"] == "MONITOR"
        assert result["is_monitor_only"] is True

    def test_decision_dict_shape(self):
        """Verify the decision dict has all expected keys."""
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        result = decide(analysis, REF)
        expected_keys = {
            "capability_band", "vram_gb", "is_unicorn", "is_monitor_only",
            "low_risk_gate_passed", "exceptional_distance_override",
            "recommended_action", "decision_reasons",
        }
        assert set(result.keys()) == expected_keys
