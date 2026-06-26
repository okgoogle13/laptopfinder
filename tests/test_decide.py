"""Decision engine (decide.py) fixture-driven tests."""
from __future__ import annotations

import json
from pathlib import Path


from laptopfinder.decide import (
    _vram_tier,
    _is_target,
    _is_watch,
    _passes_risk_gate,
    decide,
    load_ref,
    _vram_gb,
    _ram_gb,
    _is_uma_platform,
    _is_radeon_mobile,
    _has_egpu_bundle,
    _capacity_points,
    _gpu_generation_points,
    _seller_reward_points,
    _deduction_points,
)

REF = load_ref()
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "stage2"


def load_fixture(name: str) -> dict:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


# --- Unit tests ---

class TestParseVramGb:
    def test_standard(self):
        assert _vram_gb("16GB GDDR6") == 16.0

    def test_bare(self):
        assert _vram_gb("24GB") == 24.0

    def test_none(self):
        assert _vram_gb(None) is None

    def test_unparseable(self):
        assert _vram_gb("lots of memory") is None

    def test_decimal(self):
        assert _vram_gb("11.5GB") == 11.5


class TestVramTier:
    def test_entry(self):
        assert _vram_tier(8.0, REF) == "entry"
        assert _vram_tier(12.0, REF) == "entry"

    def test_mid(self):
        assert _vram_tier(16.0, REF) == "mid"

    def test_high(self):
        assert _vram_tier(24.0, REF) == "high"

    def test_extreme(self):
        assert _vram_tier(64.0, REF) == "extreme"
        assert _vram_tier(128.0, REF) == "extreme"

    def test_none(self):
        assert _vram_tier(None, REF) is None

    def test_below_range(self):
        assert _vram_tier(4.0, REF) is None


class TestIsTarget:
    def test_gpu_match(self):
        assert _is_target(None, "RTX 3080 Ti", REF) is True

    def test_model_match(self):
        assert _is_target("MSI Titan 18 HX", None, REF) is True

    def test_no_match(self):
        assert _is_target("HP Pavilion", "GTX 1650", REF) is False

    def test_none_inputs(self):
        assert _is_target(None, None, REF) is False


class TestIsWatch:
    def test_watch_gpu(self):
        assert _is_watch("RTX 5090", REF) is True

    def test_non_watch_gpu(self):
        assert _is_watch("RTX 4090", REF) is False

    def test_none(self):
        assert _is_watch(None, REF) is False


class TestPassesRiskGate:
    def test_passes(self):
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        assert _passes_risk_gate(analysis, REF) is True

    def test_fails_high_risk(self):
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        assert _passes_risk_gate(analysis, REF) is False


# --- Integration tests ---

class TestDecide:
    def test_target_hardware_shortlisted(self):
        """A target GPU/model that passes risk gate should be shortlisted."""
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert result["is_target"] is True

    def test_high_risk_skipped(self):
        """A listing that fails the risk gate should be skipped."""
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SKIP"
        assert result["risk_gate_passed"] is False

    def test_no_vram_skipped(self):
        """A listing with no VRAM data should be skipped."""
        analysis = load_fixture("gumtree_hint_not_promoted.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["vram_tier"] is None
        assert result["vram_gb"] is None

    def test_watch_list_routes_to_monitor(self):
        """A listing with a watch-list GPU should route to MONITOR."""
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
                "total_system_ram": None,
                "egpu_model": None,
            },
            "analysis": {
                "risk_score": 1.0,
                "risk_flags": [],
                "stated_pickup_location": "Melbourne VIC",
                "confidence": 0.9,
                "seller_classification": "ESTABLISHED_RESELLER",
            },
        }
        result = decide(analysis, REF)
        assert result["recommended_action"] == "MONITOR"
        assert result["is_watch_only"] is True

    def test_decision_dict_shape(self):
        """Decision dict must have exactly these keys."""
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        result = decide(analysis, REF)
        assert set(result.keys()) == {
            "vram_gb", "vram_tier", "is_target", "is_watch_only",
            "risk_gate_passed", "recommended_action", "reasons",
            "is_uma_platform", "uma_ram_gb", "is_radeon_mobile", "has_egpu_bundle",
            "llm_index_score",
        }

    def test_touchscreen_exception_shortlisted(self):
        """A 12GB listing with touchscreen support should be shortlisted."""
        analysis = {
            "metadata": {
                "source_platform": "GUMTREE",
                "listing_url_or_identifier": None,
                "listing_title": "HP ZBook Fury 12GB Touch",
                "listing_price_aud": 2000.0,
                "seller_name_or_identifier": None,
                "seller_rating_or_profile_signal": None,
            },
            "extracted_data": {
                "exact_model_name": "ZBook Fury",
                "component_category": "SYSTEM",
                "cpu": None,
                "gpu": "RTX A3000",
                "ram": None,
                "storage": None,
                "vram_capacity": "12GB",
                "stated_condition": "Used",
                "shipping_or_pickup_signal": "BOTH",
                "missing_information": [],
                "total_system_ram": None,
                "egpu_model": None,
                "touchscreen_digitizer": "touchscreen",
            },
            "analysis": {
                "risk_score": 1.0,
                "risk_flags": [],
                "stated_pickup_location": "Melbourne",
                "confidence": 0.9,
                "seller_classification": "PRIVATE_ESTABLISHED",
            },
        }
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert any("touchscreen exception" in r for r in result["reasons"])

    def test_12gb_no_touchscreen_skipped(self):
        """A 12GB listing without touchscreen support should be skipped."""
        analysis = {
            "metadata": {
                "source_platform": "GUMTREE",
                "listing_url_or_identifier": None,
                "listing_title": "HP ZBook Fury 12GB NoTouch",
                "listing_price_aud": 2000.0,
                "seller_name_or_identifier": None,
                "seller_rating_or_profile_signal": None,
            },
            "extracted_data": {
                "exact_model_name": "ZBook Fury",
                "component_category": "SYSTEM",
                "cpu": None,
                "gpu": "RTX A3000",
                "ram": None,
                "storage": None,
                "vram_capacity": "12GB",
                "stated_condition": "Used",
                "shipping_or_pickup_signal": "BOTH",
                "missing_information": [],
                "total_system_ram": None,
                "egpu_model": None,
                "touchscreen_digitizer": None,
            },
            "analysis": {
                "risk_score": 1.0,
                "risk_flags": [],
                "stated_pickup_location": "Melbourne",
                "confidence": 0.9,
                "seller_classification": "PRIVATE_ESTABLISHED",
            },
        }
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SKIP"
        assert any("requires touchscreen exception" in r for r in result["reasons"])


# --- UMA (Apple Silicon Max/Ultra, Strix Halo) ---

class TestRamGb:
    def test_standard(self):
        assert _ram_gb("128GB") == 128.0

    def test_none(self):
        assert _ram_gb(None) is None

    def test_unparseable(self):
        assert _ram_gb("plenty") is None


class TestIsUmaPlatform:
    def test_apple_silicon_match(self):
        assert _is_uma_platform("Mac Studio M3 Ultra", None, REF) is True

    def test_strix_halo_match(self):
        assert _is_uma_platform("ASUS ROG Flow Z13", "Ryzen AI Max", REF) is True

    def test_no_match(self):
        assert _is_uma_platform("MSI Titan 18 HX", "i9-14900HX", REF) is False

    def test_none_inputs(self):
        assert _is_uma_platform(None, None, REF) is False


class TestUmaDecide:
    def test_high_ram_uma_shortlisted(self):
        """Mac Studio M3 Ultra with 128GB unified memory should shortlist
        on system RAM, even with vram_capacity null."""
        analysis = load_fixture("ebay_uma_mac_studio.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert result["is_uma_platform"] is True
        assert result["uma_ram_gb"] == 128.0

    def test_low_ram_uma_skipped(self):
        """Strix Halo with only 32GB unified memory is below the UMA
        threshold and should be skipped, not crash on missing vram."""
        analysis = load_fixture("fb_uma_strix_halo_low_ram.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SKIP"
        assert result["is_uma_platform"] is True
        assert result["uma_ram_gb"] == 32.0


# --- Radeon mobile (ROCm ecosystem risk penalty) ---

class TestIsRadeonMobile:
    def test_match(self):
        assert _is_radeon_mobile("RX 7900M", REF) == "RX 7900M"

    def test_no_match(self):
        assert _is_radeon_mobile("RTX 4090", REF) is None

    def test_none(self):
        assert _is_radeon_mobile(None, REF) is None


class TestRadeonDecide:
    def test_low_risk_radeon_still_shortlisted(self):
        """A clean Radeon RX 7900M listing should pass the risk gate even
        with the ecosystem penalty applied, and still shortlist on VRAM."""
        analysis = load_fixture("gumtree_radeon_7900m.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert result["is_radeon_mobile"] == "RX 7900M"

    def test_radeon_no_risk_penalty_at_gate(self):
        """Radeon listings are evaluated at the same risk_score <= 3.0 threshold
        as NVIDIA. A risk_score of 2.0 passes the gate regardless of GPU brand —
        the Radeon ecosystem disclosure is a buyer note, not a numeric gate penalty."""
        analysis = load_fixture("gumtree_radeon_7900m.json")["analysis_output"]
        analysis["analysis"]["risk_score"] = 2.0
        result = decide(analysis, REF)
        assert result["risk_gate_passed"] is True
        assert result["recommended_action"] == "SHORTLIST"


# --- eGPU bundles (XG Mobile etc.) ---

class TestHasEgpuBundle:
    def test_match_on_egpu_model(self):
        assert _has_egpu_bundle(None, "XG Mobile RTX 4090", REF) is True

    def test_match_on_model_name(self):
        assert _has_egpu_bundle("ROG Flow X13 with XG Mobile dock", None, REF) is True

    def test_no_match(self):
        assert _has_egpu_bundle("MSI Titan 18 HX", None, REF) is False

    def test_none_inputs(self):
        assert _has_egpu_bundle(None, None, REF) is False


class TestEgpuDecide:
    def test_egpu_bundle_bypasses_weak_internal_gpu(self):
        """The base laptop's GTX 1650 would normally fail the VRAM gate, but
        the bundled XG Mobile RTX 4090 (16GB, parsed from vram_capacity)
        should drive the shortlist decision instead."""
        analysis = load_fixture("ebay_egpu_bundle.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SHORTLIST"
        assert result["has_egpu_bundle"] is True


# --- Local_LLM_Index_Score (0-100 scoring matrix) ---

class TestCapacityPoints:
    def test_known_tiers(self):
        assert _capacity_points("entry", REF) == 15
        assert _capacity_points("mid", REF) == 25
        assert _capacity_points("high", REF) == 40
        assert _capacity_points("extreme", REF) == 60

    def test_none_tier_scores_zero(self):
        assert _capacity_points(None, REF) == 0


class TestGpuGenerationPoints:
    def test_ada_lovelace(self):
        assert _gpu_generation_points("RTX 4090", is_uma=False, ref=REF) == 20

    def test_ampere(self):
        assert _gpu_generation_points("RTX 3080 Ti", is_uma=False, ref=REF) == 12

    def test_blackwell(self):
        assert _gpu_generation_points("RTX 5090", is_uma=False, ref=REF) == 25

    def test_rdna3_score(self):
        assert _gpu_generation_points("RX 7900M", is_uma=False, ref=REF) == 15

    def test_uma_scores_as_apple_silicon(self):
        """UMA platforms (Apple Silicon, Strix Halo) score on the Apple Silicon
        generation line regardless of gpu field. Value is 20 — parity with Ada Lovelace
        rather than Blackwell, reflecting UMA bandwidth constraints."""
        assert _gpu_generation_points(None, is_uma=True, ref=REF) == 20

    def test_unrecognized_gpu_scores_zero_not_penalty(self):
        assert _gpu_generation_points("GTX 1650", is_uma=False, ref=REF) == 0

    def test_none_gpu_no_uma_scores_zero(self):
        assert _gpu_generation_points(None, is_uma=False, ref=REF) == 0


class TestSellerRewardPoints:
    def test_retailer_with_warranty_on_ebay(self):
        analysis = {
            "metadata": {"source_platform": "EBAY_AU"},
            "analysis": {"seller_classification": "RETAILER_WITH_WARRANTY"},
        }
        assert _seller_reward_points(analysis, REF) == 15 + 5

    def test_private_new_on_fb(self):
        analysis = {
            "metadata": {"source_platform": "FB_MARKETPLACE"},
            "analysis": {"seller_classification": "PRIVATE_NEW_OR_UNKNOWN"},
        }
        assert _seller_reward_points(analysis, REF) == -15 + -5

    def test_established_reseller_on_ebay(self):
        analysis = {
            "metadata": {"source_platform": "EBAY_AU"},
            "analysis": {"seller_classification": "ESTABLISHED_RESELLER"},
        }
        assert _seller_reward_points(analysis, REF) == 8 + 5


class TestDeductionPoints:
    def test_no_missing_no_risk(self):
        analysis = {"extracted_data": {"missing_information": []}, "analysis": {"risk_score": 0.0}}
        assert _deduction_points(analysis, REF) == 0

    def test_missing_fields_only(self):
        analysis = {"extracted_data": {"missing_information": ["a", "b"]}, "analysis": {"risk_score": 0.0}}
        assert _deduction_points(analysis, REF) == 2 * 3

    def test_risk_score_only(self):
        analysis = {"extracted_data": {"missing_information": []}, "analysis": {"risk_score": 9.2}}
        assert _deduction_points(analysis, REF) == round(9.2 * 4)


class TestLlmIndexScoreIntegration:
    """Hand-verified totals: capacity + generation + seller − deductions, clamped [0, 100]."""

    def test_ada_lovelace_mid_tier_established_reseller(self):
        """RTX 4090 16GB (mid=25) + Ada Lovelace (20) + ESTABLISHED_RESELLER on
        EBAY_AU (8+5=13) − risk 1.0 deduction (4) + GPU hint RTX 4090 in target_gpus
        (+5) + model hint 'MSI Titan 18' in target_models (+3) = 62."""
        analysis = load_fixture("ebay_facts_grounded.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["llm_index_score"] == 62

    def test_uma_extreme_tier_scores_highest(self):
        """Mac Studio 128GB (extreme=60) + Apple Silicon (20) + ESTABLISHED_RESELLER
        on EBAY_AU (13) − risk 1.0 deduction (4) = 89 raw, clamped to UMA
        score_ceiling of 75."""
        analysis = load_fixture("ebay_uma_mac_studio.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["llm_index_score"] == 75

    def test_radeon_mobile_score(self):
        """RX 7900M 16GB (mid=25) + RDNA3 (15) + PRIVATE_NEW_OR_UNKNOWN on
        GUMTREE (-15-5=-20) − risk 1.0 deduction (4) + model hint 'ASUS ROG Strix SCAR 18'
        in target_models (+3) = 19. RDNA3 now scores on inference capability, not
        ecosystem friction (that's a disclosure note, not a score penalty)."""
        analysis = load_fixture("gumtree_radeon_7900m.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["llm_index_score"] == 19

    def test_high_risk_listing_clamped_to_zero(self):
        """Negative raw score (no capacity, no generation, large risk/missing
        deductions, private+unknown seller penalty) clamps to 0, not negative."""
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["llm_index_score"] == 0

    def test_score_never_exceeds_100(self):
        analysis = load_fixture("ebay_uma_mac_studio.json")["analysis_output"]
        analysis["analysis"]["seller_classification"] = "RETAILER_WITH_WARRANTY"
        analysis["analysis"]["risk_score"] = 0.0
        result = decide(analysis, REF)
        assert result["llm_index_score"] <= 100
        # UMA platforms are additionally capped at apple_silicon.score_ceiling (75).
        assert result["llm_index_score"] <= REF["apple_silicon"]["score_ceiling"]

    def test_score_is_additive_not_blocking(self):
        """A SKIP-routed listing (failed risk gate) still gets a computed score —
        the score is informational/ranking, never gates recommended_action."""
        analysis = load_fixture("fb_high_risk_listing.json")["analysis_output"]
        result = decide(analysis, REF)
        assert result["recommended_action"] == "SKIP"
        assert isinstance(result["llm_index_score"], int)

    def test_target_model_hint_adds_bonus_but_does_not_gate_routing(self):
        """A listing on target_models with only 8GB VRAM earns the +3 model hint
        bonus in its score, but still routes to SKIP — target_models is a scoring
        hint, not a routing whitelist."""
        analysis = {
            "metadata": {
                "source_platform": "EBAY_AU",
                "listing_url_or_identifier": None,
                "listing_title": "ASUS ROG Zephyrus Duo 16 8GB VRAM",
                "listing_price_aud": 1800.0,
                "seller_name_or_identifier": "seller123",
                "seller_rating_or_profile_signal": "50 feedback, 100% positive",
            },
            "extracted_data": {
                "exact_model_name": "ASUS ROG Zephyrus Duo 16",
                "component_category": "SYSTEM",
                "cpu": "Ryzen 9 6900HX",
                "gpu": "RX 6700M",
                "ram": "32GB",
                "storage": "1TB NVMe",
                "vram_capacity": "8GB",
                "stated_condition": "Good",
                "shipping_or_pickup_signal": "BOTH",
                "missing_information": [],
                "total_system_ram": None,
                "egpu_model": None,
            },
            "analysis": {
                "risk_score": 0.5,
                "risk_flags": [],
                "stated_pickup_location": "Melbourne VIC",
                "confidence": 0.9,
                "seller_classification": "ESTABLISHED_RESELLER",
            },
        }
        result = decide(analysis, REF)
        # VRAM 8GB < 16GB threshold → SKIP regardless of model list membership.
        assert result["recommended_action"] == "SKIP"
        assert result["is_target"] is True
        # Score: entry(15) + gen_0_for_RX6700M(0) + ESTABLISHED_RESELLER+EBAY_AU(13)
        # − risk 0.5*4(2) + model_hint(+3) = 29
        assert result["llm_index_score"] == 29
