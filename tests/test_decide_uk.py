import pytest
from laptopfinder.decide import decide, load_ref

def test_decide_with_uk_scenarios():
    ref = load_ref()
    analysis = {
        "metadata": {
            "source_platform": "EBAY_UK",
            "listing_url_or_identifier": "123",
            "listing_title": "UK RTX 4090 Laptop",
            "listing_price_aud": 4500.0,
            "listing_price_local": 2500.0,
            "currency": "GBP",
            "item_location_country": "UK",
            "seller_name_or_identifier": "some_uk_seller",
            "seller_rating_or_profile_signal": "100%"
        },
        "extracted_data": {
            "exact_model_name": "MSI Titan",
            "component_category": "SYSTEM",
            "cpu": "i9",
            "gpu": "RTX 4090",
            "ram": "64GB",
            "storage": "2TB",
            "vram_capacity": {"semantic_value": 16.0, "verbatim_quote": "16GB"},
            "stated_condition": "Used",
            "shipping_or_pickup_signal": "BOTH",
            "missing_information": {
                "gpu": False, "vram": False, "cpu": False, 
                "ram": False, "storage": False, "condition": False
            },
            "total_system_ram": "64GB",
            "egpu_model": None,
            "touchscreen_digitizer": None
        },
        "analysis": {
            "risk_score": 1.0,
            "risk_flags": [],
            "stated_pickup_location": "London",
            "confidence": 0.9,
            "seller_classification": "ESTABLISHED_RESELLER",
            "delivery_deadline_feasibility": "Likely"
        }
    }
    
    result = decide(analysis, ref)
    assert result["recommended_action"] == "SHORTLIST"
    assert "landed_cost_scenarios" in result
    scenarios = result["landed_cost_scenarios"]
    assert len(scenarios) == 3
    # Check that the hand-carry scenario exists
    carry_scenario = next(s for s in scenarios if s["scenario_name"] == "UK purchase hand-carried to Australia")
    assert carry_scenario["total_landed_cost_aud"] > 0
    assert carry_scenario["delivery_feasibility"] == "Likely"
