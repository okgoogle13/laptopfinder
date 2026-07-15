"""Tests for src/laptopfinder/ingest_csv.py"""
import json
from pathlib import Path
import pytest
import jsonschema

from laptopfinder.ingest_csv import clean_price, parse_vram_gb, parse_ram_gb

def test_clean_price():
    assert clean_price("(AU $7,324.68)") == 7324.68
    assert clean_price("AU $1,900.00*") == 1900.00
    assert clean_price("AU $2,999.00") == 2999.00
    assert clean_price("AU $802.00") == 802.00
    assert clean_price("Item not available") is None
    assert clean_price("") is None
    assert clean_price(None) is None

def test_parse_vram_gb():
    assert parse_vram_gb("16GB") == 16
    assert parse_vram_gb("16 GB GDDR6") == 16
    assert parse_vram_gb("8GB") == 8
    assert parse_vram_gb(16) == 16
    assert parse_vram_gb(None) is None

def test_parse_ram_gb():
    assert parse_ram_gb("64GB") == 64
    assert parse_ram_gb("32 GB LPDDR5") == 32
    assert parse_ram_gb(128) == 128
    assert parse_ram_gb(None) is None

def test_schema_validation():
    schema_path = Path(__file__).resolve().parents[1] / "src" / "laptopfinder" / "schemas" / "ebay_hardware_listing.schema.json"
    assert schema_path.exists()
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Valid candidate dictionary matching schema
    valid_candidate = {
        "platform": "EBAY_AU",
        "listing_id": "325123456789",
        "url": "https://www.ebay.com.au/itm/325123456789",
        "title": "MSI Titan 18 HX - RTX 4090 - 128GB RAM - 4TB SSD",
        "price_aud": 6500.00,
        "seller_name": "tech_store_melbourne",
        "seller_rating": None,
        "condition_code": None,
        "condition_label": "Brand New",
        "shipping_type": None,
        "pickup_location_text": None,
        "category_path": "Computers/Tablets & Networking > Laptops & Netbooks",
        "full_listing_text": "Up for sale is a brand new MSI Titan 18 HX",
        "scraped_at": "2026-07-04T01:10:16Z",
        "gpu_name": "NVIDIA GeForce RTX 4090 Laptop GPU",
        "vram_capacity": 16,
        "cpu_name": "Intel Core i9-14900HX",
        "total_system_ram": 128,
        "storage": "4TB NVMe SSD",
        "egpu_model": None,
        "touchscreen_digitizer": False,
        "exact_model_name": "MSI Titan 18 HX"
    }

    # Should not raise validation error
    jsonschema.validate(valid_candidate, schema)

    # Invalid: string instead of integer for total_system_ram
    invalid_candidate = valid_candidate.copy()
    invalid_candidate["total_system_ram"] = "128GB"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_candidate, schema)

    # Invalid: missing required key platform
    invalid_candidate = valid_candidate.copy()
    del invalid_candidate["platform"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_candidate, schema)

def test_missing_csv_columns_raises_valueerror(monkeypatch, tmp_path):
    from laptopfinder.ingest_csv import main
    import csv

    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    csv_file = tmp_path / "missing_cols.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["listing_id", "title", "url"])
        writer.writerow(["123", "Laptop", "http"])
        
    with pytest.raises(ValueError, match="CSV is missing required columns"):
        main(csv_file)

def test_empty_csv_raises_valueerror(monkeypatch, tmp_path):
    from laptopfinder.ingest_csv import main

    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    csv_file = tmp_path / "empty.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        pass
        
    with pytest.raises(ValueError, match="CSV file is empty or has no header row"):
        main(csv_file)
