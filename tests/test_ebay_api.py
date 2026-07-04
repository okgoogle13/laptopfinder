import json
from pathlib import Path
from jsonschema import validate
from laptopfinder.runners.ebay_api import build_analysis_dict

def test_ebay_api_builds_valid_stage2_schema():
    # Load schema
    schema_path = Path(__file__).parent.parent / "src" / "laptopfinder" / "schemas" / "stage2.analysis.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    # Mock eBay Browse API Item Summary payload
    mock_item = {
        "title": "ASUS ROG Strix G16 16\" FHD 165Hz i7-13650HX 16GB 512GB RTX 4080 Gaming Laptop",
        "price": {"value": "2999.00"},
        "itemWebUrl": "https://www.ebay.com.au/itm/1234567890",
        "itemLocation": {"country": "AU"},
        "condition": "USED_EXCELLENT",
        "seller": {
            "username": "fast_tech_aus",
            "feedbackScore": 1250,
            "feedbackPercentage": 99.8
        },
        "localizedAspects": [
            {"name": "GPU", "values": ["NVIDIA GeForce RTX 4080"]},
            {"name": "GPU Memory Size", "values": ["12 GB"]},
            {"name": "Processor", "values": ["Intel Core i7 13th Gen."]},
            {"name": "RAM Size", "values": ["16 GB"]},
            {"name": "SSD Capacity", "values": ["512 GB"]},
            {"name": "Model", "values": ["ASUS ROG Strix G16"]}
        ]
    }
    
    analysis_dict = build_analysis_dict(mock_item)
    
    # Validate against stage2 schema
    validate(instance=analysis_dict, schema=schema)
    
    assert analysis_dict["metadata"]["source_platform"] == "EBAY_AU"
    assert analysis_dict["extracted_data"]["gpu"] == "NVIDIA GeForce RTX 4080"
    assert analysis_dict["extracted_data"]["vram_capacity"] == {"semantic_value": 12.0, "verbatim_quote": "12 GB"}
    assert analysis_dict["analysis"]["seller_classification"] == "ESTABLISHED_RESELLER"
    assert analysis_dict["extracted_data"]["missing_information"]["gpu"] is False
    assert analysis_dict["extracted_data"]["missing_information"]["vram"] is False
    assert analysis_dict["extracted_data"]["missing_information"]["storage"] is False


def test_ebay_api_edge_cases():
    mock_item = {
        "title": "ASUS Laptop 16GB RAM",
        "price": {},
        "itemWebUrl": "https://www.ebay.com.au/itm/000",
        "itemLocation": {"country": "AU"},
        "condition": "USED_EXCELLENT",
        "seller": {
            "username": "test_user",
            "feedbackScore": 5,
            "feedbackPercentage": None,  # Should not raise TypeError
        },
        "localizedAspects": [
            {"name": "Maximum Resolution", "value": "1920 x 1080"},  # Should NOT be parsed as VRAM
            {"name": "RAM Size", "value": "16 GB"},  # Scalar value instead of values list
        ],
    }
    
    analysis = build_analysis_dict(mock_item)
    assert analysis["metadata"]["listing_price_aud"] is None
    assert analysis["extracted_data"]["vram_capacity"] is None
    assert analysis["extracted_data"]["missing_information"]["vram"] is True
    assert analysis["extracted_data"]["missing_information"]["storage"] is True
    assert analysis["extracted_data"]["ram"] == "16 GB"
    assert analysis["extracted_data"]["missing_information"]["ram"] is False
