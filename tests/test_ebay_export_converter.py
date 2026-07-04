from __future__ import annotations
import sys
from pathlib import Path

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from ebay_export_to_jsonl import read_export_file, deduplicate_records


def test_ebay_export_converter_basic():
    sample_path = Path(__file__).parent / "fixtures" / "ebay_export_sample.json"
    records = read_export_file(sample_path)
    records = deduplicate_records(records)

    assert len(records) == 2
    for r in records:
        assert r["title"] is not None and len(r["title"]) > 0
        assert r["price_raw"] is not None and len(r["price_raw"]) > 0
        assert r["url"] is not None and str(r["url"]).startswith("https://www.ebay.com.au/itm/")
        assert r["full_listing_text"] is not None and r["title"] in r["full_listing_text"]
