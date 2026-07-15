from laptopfinder.runners.legacy.hunter.score import compute_baselines, annotate_mispricing, is_top_acquisition

def test_compute_baselines():
    corpus = [
        {"item_id": "1", "price_aud": 1000},
        {"item_id": "2", "price_aud": 1500},
        {"item_id": "3", "price_aud": 1200},
        {"item_id": "4", "price_aud": 500}
    ]
    triage = {
        "1": {"canonical_model": "Model A"},
        "2": {"canonical_model": "Model A"},
        "3": {"canonical_model": "Model A"},
        "4": {"canonical_model": None}
    }
    baselines = compute_baselines(corpus, triage, 3)
    assert baselines["Model A"] == 1200.0

def test_annotate_mispricing():
    result = {"price_aud": 1000, "canonical_model": "Model A"}
    baselines = {"Model A": 1200.0}
    res = annotate_mispricing(result, baselines)
    assert res["baseline_median_aud"] == 1200.0
    assert res["price_delta_aud"] == -200.0

def test_is_top_acquisition():
    
    assert not is_top_acquisition({"decision": {"recommended_action": "SKIP"}})
    assert is_top_acquisition({"decision": {"recommended_action": "SHORTLIST"}, "underpriced": True})
    assert not is_top_acquisition({"decision": {"recommended_action": "SHORTLIST"}, "underpriced": False})
