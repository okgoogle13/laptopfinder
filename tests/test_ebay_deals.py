import json
from pathlib import Path
from unittest.mock import patch
from laptopfinder.runners.ebay_deals import scan_clearance, build_clearance_filter

REF = json.loads(Path("config/static_reference_layer.json").read_text())


def test_build_clearance_filter_includes_sellers():
    result = build_clearance_filter(["delloutletau", "lenovoaustralia"])
    assert "sellers:{delloutletau|lenovoaustralia}" in result


def test_scan_clearance_returns_list():
    mock_items = [{"itemId": "abc", "title": "Dell XPS 16 M4 Max 64GB", "price": {"value": "2500", "currency": "AUD"}}]
    with patch("laptopfinder.runners.ebay_deals.ebay_get", return_value={"itemSummaries": mock_items, "total": 1}):
        results = scan_clearance("tok", REF)
    assert isinstance(results, list)


def test_scan_clearance_empty_when_no_sellers():
    ref_no_sellers = {**REF, "clearance_sellers": []}
    results = scan_clearance("tok", ref_no_sellers)
    assert results == []
