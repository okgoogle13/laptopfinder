from laptopfinder.runners.ebay_sniper import evaluate_rtx5090_candidate

def mock_fetch_item(token, item_id, marketplace_id="EBAY_AU"):
    # Return mock details based on item_id
    if item_id == "LENOVO_FROM":
        return {"description": "Available from RTX 5070 Ti.", "localizedAspects": []}
    if item_id == "TITLE_ONLY":
        return {"description": "Just a normal description", "localizedAspects": []}
    if item_id == "TRUE_LAPTOP":
        return {"description": "RTX 5090 Laptop GPU 24GB GDDR7", "localizedAspects": []}
    if item_id == "DESKTOP_GPU":
        return {"description": "Desktop GPU", "localizedAspects": []}
    if item_id == "UNKNOWN_SHIPPING":
        return {"description": "RTX 5090 Laptop GPU 24GB GDDR7", "localizedAspects": []}
    if item_id == "EXACT_SKU":
        return {"description": "", "localizedAspects": [{"name": "MPN", "value": "A18-5090"}]}
    if item_id == "ALIENWARE_18":
        return {"description": "RTX 5090 Laptop GPU 24GB GDDR7", "localizedAspects": []}
    if item_id == "MIKEPC":
        return {"description": "RTX 5090 Laptop GPU 24GB GDDR7", "localizedAspects": []}
    return {}

def test_rtx5090_evaluation(monkeypatch):
    monkeypatch.setattr("laptopfinder.runners.ebay_sniper.fetch_item", mock_fetch_item)
    
    # 1. Lenovo from pricing tied to RTX 5070 Ti must not become RTX 5090 evidence
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|LENOVO_FROM|0", "title": "Lenovo Legion"}, "EBAY_AU")
    assert res["state"] == "REJECTED"
    
    # 2. Title-only RTX 5090 remains NEEDS_VERIFICATION
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|TITLE_ONLY|0", "title": "RTX 5090 Laptop"}, "EBAY_AU")
    assert res["state"] == "NEEDS_VERIFICATION"
    
    # 3. True laptops are not rejected merely because “laptop” is absent from the title
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|TRUE_LAPTOP|0", "title": "Lenovo Legion Pro 7i RTX 5090"}, "EBAY_AU")
    assert res["state"] == "VERIFIED_LISTING"
    
    # 4. Desktop RTX 5090 cards and eGPUs are rejected
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|DESKTOP_GPU|0", "title": "NVIDIA RTX 5090 Desktop Graphics Card"}, "EBAY_AU")
    assert res["state"] == "REJECTED"
    
    # 5. Unknown shipping yields LANDED_COST_INCOMPLETE
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|UNKNOWN_SHIPPING|0", "title": "RTX 5090", "shippingOptions": []}, "EBAY_AU")
    assert res["cost_status"] == "LANDED_COST_INCOMPLETE"
    
    # 6. Exact SKU evidence promotes to VERIFIED_SKU
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|EXACT_SKU|0", "title": "Laptop"}, "EBAY_AU")
    assert res["state"] == "VERIFIED_SKU"
    
    # 7. Alienware 18 Area-51 is scored as ASPIRATIONAL_BUY_CANDIDATE
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|ALIENWARE_18|0", "title": "Alienware 18 Area-51 RTX 5090"}, "EBAY_AU")
    assert res["classification"] == "ASPIRATIONAL_BUY_CANDIDATE"
    
    # 8. MikePC Legion Pro 7i AU$4,999 is a reference only
    res = evaluate_rtx5090_candidate("token", {"itemId": "v1|MIKEPC|0", "title": "Lenovo Legion Pro 7i", "price": {"value": "4999.0"}, "seller": {"username": "mikepc"}}, "EBAY_AU")
    assert res["state"] == "REJECTED"
