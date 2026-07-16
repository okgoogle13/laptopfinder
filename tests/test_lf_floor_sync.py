from scripts.lf_floor_sync import load_rows, normalize


def test_normalize_extracts_flat_fields():
    row = {
        "item_id": "v1|123|0",
        "item_web_url": "https://www.ebay.com.au/itm/123",
        "canonical_model": "ASUS ROG Zephyrus G15",
        "price_aud": 1850.0,
        "analysis": {
            "extracted_data": {
                "gpu": "RTX 3080",
                "vram_capacity": {"semantic_value": 16.0, "verbatim_quote": "16GB VRAM"},
            }
        },
        "decision": {"recommended_action": "SHORTLIST", "llm_index_score": 72},
    }
    result = normalize(row)
    assert result["gpu"] == "RTX 3080"
    assert result["vram_gb"] == 16.0
    assert result["recommended_action"] == "SHORTLIST"
    assert result["llm_index_score"] == 72


def test_normalize_handles_null_vram():
    row = {
        "item_id": "v1|456|0",
        "item_web_url": "https://www.ebay.com.au/itm/456",
        "canonical_model": None,
        "price_aud": 900.0,
        "analysis": {"extracted_data": {"gpu": None, "vram_capacity": None}},
        "decision": {"recommended_action": "SKIP", "llm_index_score": 10},
    }
    result = normalize(row)
    assert result["gpu"] is None
    assert result["vram_gb"] is None


def test_load_rows_missing_file_returns_empty(tmp_path):
    assert load_rows(tmp_path / "does_not_exist.jsonl") == []


def test_load_rows_parses_jsonl(tmp_path):
    path = tmp_path / "hunt_results.jsonl"
    path.write_text('{"item_id": "a"}\n{"item_id": "b"}\n', encoding="utf-8")
    rows = load_rows(path)
    assert len(rows) == 2
    assert rows[0]["item_id"] == "a"
    assert rows[1]["item_id"] == "b"
