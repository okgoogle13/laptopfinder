"""
Tests for retail archetypes fixture validation against platform_agnostic_listing.schema.json.
"""

import json
from pathlib import Path
import pytest
from jsonschema import validate


@pytest.fixture
def listing_schema() -> dict:
    schema_path = Path(__file__).parent.parent / "src" / "laptopfinder" / "schemas" / "platform_agnostic_listing.schema.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def retail_rows() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "retail_archetypes.jsonl"
    rows = []
    with open(fixture_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_retail_archetypes_fixture_count(retail_rows: list[dict]) -> None:
    assert len(retail_rows) == 6, "Must contain exactly the 6 non-eBay example rows."


def test_retail_archetypes_validate_against_schema(retail_rows: list[dict], listing_schema: dict) -> None:
    for row in retail_rows:
        # To validate against schema when price is null, we can check as-is (since price_aud accepts null)
        validate(instance=row, schema=listing_schema)
        assert row.get("is_illustrative_fixture") is True
        assert row.get("price_aud_placeholder") is not None
        assert row.get("score_0_100_placeholder") is not None
