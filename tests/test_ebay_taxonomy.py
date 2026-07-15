import json
from pathlib import Path
from unittest.mock import patch

from laptopfinder.ebay_taxonomy import build_aspect_filter, ebay_category_id
from laptopfinder.runners.legacy.hunter import api, search

REF = json.loads(Path("config/static_reference_layer.json").read_text())


# --- ebay_category_id ---

def test_category_id_from_srl():
    assert ebay_category_id(REF) == "175672"


def test_category_id_default_when_no_config():
    assert ebay_category_id({}) == "175672"


# --- build_aspect_filter ---

def test_build_aspect_filter_returns_string():
    result = build_aspect_filter(REF)
    assert result is not None
    assert "GPU Memory Size" in result


def test_build_aspect_filter_includes_16gb():
    result = build_aspect_filter(REF)
    assert "16 GB" in result


def test_build_aspect_filter_includes_category_id():
    result = build_aspect_filter(REF)
    assert "categoryId:175672" in result


def test_build_aspect_filter_none_when_no_config():
    assert build_aspect_filter({}) is None


def test_build_aspect_filter_none_when_empty_values():
    ref = {"ebay_aspect_filter": {"category_id": "175672", "gpu_memory_size_values": []}}
    assert build_aspect_filter(ref) is None


# --- browse_search integration ---

def test_browse_search_sends_aspect_filter():
    mock_resp = {"itemSummaries": [], "total": 0}
    with patch("laptopfinder.runners.legacy.hunter.api.ebay_get", return_value=mock_resp) as mock_get:
        api.browse_search(
            "tok", "RTX 3080 laptop", 10,
            aspect_filter="categoryId:175672,GPU Memory Size:{16 GB|24 GB}",
            category_id="175672",
        )
        params = mock_get.call_args[0][1]
        assert params.get("aspect_filter") == "categoryId:175672,GPU Memory Size:{16 GB|24 GB}"
        assert params.get("category_ids") == "175672"


def test_browse_search_omits_aspect_filter_when_none():
    mock_resp = {"itemSummaries": [], "total": 0}
    with patch("laptopfinder.runners.legacy.hunter.api.ebay_get", return_value=mock_resp) as mock_get:
        api.browse_search("tok", "RTX 3080 laptop", 10)
        params = mock_get.call_args[0][1]
        assert "aspect_filter" not in params


# --- collect_corpus threads aspect_filter and category_id ---

def test_collect_corpus_passes_aspect_filter_to_browse_search():
    mock_resp = {"itemSummaries": [], "total": 0}
    with patch("laptopfinder.runners.legacy.hunter.api.ebay_get", return_value=mock_resp) as mock_get:
        search.collect_corpus("tok", REF, max_per_query=5)
        if mock_get.call_args_list:
            params = mock_get.call_args_list[0][0][1]
            assert params.get("category_ids") == "175672"
            assert "aspect_filter" in params


# --- _build_filter seller scoping ---

def test_build_filter_with_sellers():
    result = search._build_filter(sellers=["seller_au_123", "seller_au_456"])
    assert "sellers:{seller_au_123|seller_au_456}" in result


def test_build_filter_no_sellers_omits_sellers_token():
    result = search._build_filter()
    assert "sellers:" not in result


# --- seller sweeps in collect_corpus ---

def test_collect_corpus_fires_seller_sweep_when_watched_sellers_set():
    ref_with_seller = {**REF, "watched_sellers": ["test_seller_au"]}
    mock_resp = {"itemSummaries": [], "total": 0}
    with patch("laptopfinder.runners.legacy.hunter.api.ebay_get", return_value=mock_resp) as mock_get:
        search.collect_corpus("tok", ref_with_seller, max_per_query=5)
        # At least one call should have the seller filter
        all_filters = [c[0][1].get("filter", "") for c in mock_get.call_args_list]
        assert any("test_seller_au" in f for f in all_filters)


def test_collect_corpus_no_seller_sweep_when_list_empty():
    ref_no_sellers = {**REF, "watched_sellers": []}
    mock_resp = {"itemSummaries": [], "total": 0}
    with patch("laptopfinder.runners.legacy.hunter.api.ebay_get", return_value=mock_resp) as mock_get:
        search.collect_corpus("tok", ref_no_sellers, max_per_query=5)
        all_filters = [c[0][1].get("filter", "") for c in mock_get.call_args_list]
        assert not any("sellers:" in f for f in all_filters)
