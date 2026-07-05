import statistics
from scripts.ebay_sold_baseline import compute_baseline, parse_sold_items


def _make_item(price_aud: str, title: str = "Laptop") -> dict:
    return {
        "title": [title],
        "sellingStatus": [{"currentPrice": [{"__value__": price_aud, "@currencyId": "AUD"}]}],
    }


def test_compute_baseline_median():
    items = [_make_item("1000"), _make_item("2000"), _make_item("1500")]
    result = compute_baseline(items)
    assert result["median_aud"] == 1500.0
    assert result["count"] == 3


def test_compute_baseline_empty():
    assert compute_baseline([]) == {}


def test_parse_sold_items_empty_response():
    response = {"findCompletedItemsResponse": [{"searchResult": [{"@count": "0"}]}]}
    assert parse_sold_items(response) == []


def test_parse_sold_items_extracts_prices():
    response = {
        "findCompletedItemsResponse": [{
            "searchResult": [{
                "@count": "1",
                "item": [_make_item("1850", "RTX 3080 Laptop")]
            }]
        }]
    }
    items = parse_sold_items(response)
    assert len(items) == 1
    assert items[0]["price_aud"] == 1850.0
    assert items[0]["title"] == "RTX 3080 Laptop"
