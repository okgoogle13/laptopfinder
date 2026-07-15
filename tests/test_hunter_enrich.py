from unittest.mock import patch
from laptopfinder.runners.hunter.enrich import enrich_and_decide, build_handoff

def test_build_handoff():
    metadata = {"listing_title": "Test", "listing_price_aud": 2000, "listing_url_or_identifier": "http"}
    triage = {"gpu_guess": "RTX 4090", "vram_hint_gb": 16}
    handoff = build_handoff(metadata, triage)
    assert handoff["inferred_vram_hint"] == "16"
    assert handoff["inferred_gpu_hint"] == "RTX 4090"

@patch("laptopfinder.runners.hunter.enrich.get_item")
@patch("laptopfinder.runners.hunter.enrich.enrich_listing")
@patch("laptopfinder.runners.hunter.enrich.run_stage2")
@patch("laptopfinder.runners.hunter.enrich.decide")
def test_enrich_and_decide_success(mock_decide, mock_stage2, mock_enrich, mock_get_item):
    mock_get_item.return_value = {"localizedAspects": [], "itemWebUrl": "http", "price": {"value": "2000", "currency": "AUD"}, "title": "Test Laptop"}
    mock_enrich.return_value = {
        "extracted_data": {"component_category": "GPU", "vram_capacity": {"semantic_value": 16}}
    }
    mock_stage2.return_value = {"metadata": {"listing_title": "Test Laptop", "listing_price_aud": 2000, "listing_url_or_identifier": "http"}}
    mock_decide.return_value = {"recommended_action": "SHORTLIST", "llm_index_score": 90}
    
    item = {"item_id": "123", "title": "Test Laptop", "price_aud": 2000, "itemWebUrl": "http"}
    res = enrich_and_decide(None, "model", "token", item, {}, {"ebay_aspect_filter": {}}, False)
    
    assert res is not None
    assert res["decision"]["recommended_action"] == "SHORTLIST"
    assert res["decision"]["llm_index_score"] == 90

@patch("laptopfinder.runners.hunter.enrich.get_item")
@patch("laptopfinder.runners.hunter.enrich.enrich_listing")
@patch("laptopfinder.runners.hunter.enrich.run_stage2")
def test_enrich_and_decide_stage2_fail(mock_stage2, mock_enrich, mock_get_item):
    mock_get_item.return_value = {"localizedAspects": [], "itemWebUrl": "http", "price": {"value": "2000", "currency": "AUD"}, "title": "Test Laptop"}
    mock_enrich.return_value = {
        "extracted_data": {"component_category": "GPU"}
    }
    mock_stage2.side_effect = ValueError("Stage 2 Grounding Firewall Failed")
    
    item = {"item_id": "123", "title": "Test"}
    res = enrich_and_decide(None, "model", "token", item, {}, {"ebay_aspect_filter": {}}, False)
    
    # Drops the listing on firewall fail
    assert res is None
