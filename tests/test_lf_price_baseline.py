from scripts.lf_price_baseline import (
    normalize_current_row,
    normalize_historical_row,
    parse_price_aud,
)


def test_parse_price_aud_extracts_number():
    assert parse_price_aud("AU $7324.68") == 7324.68


def test_parse_price_aud_handles_commas():
    assert parse_price_aud("AU $1,850.00") == 1850.0


def test_parse_price_aud_missing_dash_returns_none():
    assert parse_price_aud("—") is None


def test_parse_price_aud_none_returns_none():
    assert parse_price_aud(None) is None


def test_normalize_historical_row():
    row = {
        "recommended_action": "SHORTLIST",
        "llm_index_score": 71,
        "listing_title": "Razer Blade 18 RTX 5090",
        "gpu": "RTX 5090",
        "price": "AU $7324.68",
    }
    result = normalize_historical_row(row)
    assert result["source"] == "shortlist_historical"
    assert result["price_aud"] == 7324.68
    assert result["gpu"] == "RTX 5090"


def test_normalize_current_row():
    row = {
        "item_id": "v1|123|0",
        "item_web_url": "https://www.ebay.com.au/itm/123",
        "canonical_model": "ASUS ROG Zephyrus G15",
        "price_aud": 1850.0,
        "analysis": {"extracted_data": {"gpu": "RTX 3080", "vram_capacity": None}},
        "decision": {"recommended_action": "SHORTLIST", "llm_index_score": 72},
    }
    result = normalize_current_row(row)
    assert result["source"] == "hunt_current"
    assert result["price_aud"] == 1850.0
    assert result["title_or_model"] == "ASUS ROG Zephyrus G15"
