from laptopfinder.runners.ebay_hunter import build_parser, build_queries, summary_to_row


def test_no_enrich_flag_parsed():
    args = build_parser().parse_args(["--dry-run", "--no-enrich"])
    assert args.dry_run is True
    assert args.no_enrich is True


def test_no_enrich_flag_defaults_false():
    args = build_parser().parse_args([])
    assert args.no_enrich is False


def test_build_queries_uses_target_gpus_and_models():
    ref = {
        "target_gpus": {"RTX 3080": {}, "RTX 4090": {}},
        "target_models": ["ASUS ProArt P16"],
    }
    queries = build_queries(ref)
    assert any("RTX 3080" in q for q in queries)
    assert any("RTX 4090" in q for q in queries)
    assert any("ASUS ProArt P16" in q for q in queries)


def test_build_queries_deduplicates():
    ref = {"target_gpus": {"RTX 3080": {}, "RTX 3080": {}}, "target_models": []}
    queries = build_queries(ref)
    assert len(queries) == len(set(queries))


def test_summary_to_row_aud_price():
    item = {
        "itemId": "abc123",
        "title": "Test Laptop",
        "price": {"value": "1500.00", "currency": "AUD"},
        "condition": "USED_EXCELLENT",
        "buyingOptions": ["FIXED_PRICE"],
        "seller": {"username": "seller1", "feedbackPercentage": "99.5", "feedbackScore": 500},
        "itemWebUrl": "https://ebay.com.au/itm/abc123",
    }
    row = summary_to_row(item)
    assert row["item_id"] == "abc123"
    assert row["price_aud"] == 1500.0


def test_summary_to_row_non_aud_price_is_none():
    item = {
        "itemId": "x",
        "title": "US listing",
        "price": {"value": "999.00", "currency": "USD"},
        "condition": "NEW",
        "buyingOptions": [],
        "seller": {},
        "itemWebUrl": "",
    }
    row = summary_to_row(item)
    assert row["price_aud"] is None
