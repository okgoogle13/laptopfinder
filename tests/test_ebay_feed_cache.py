import json
import os
import tempfile
from pathlib import Path
from scripts.ebay_feed_cache import load_feed_cache, write_feed_cache


def test_write_and_load_feed_cache_roundtrip():
    items = [
        {"itemId": "v1|001|0", "title": "ASUS ROG RTX 4090 24GB"},
        {"itemId": "v1|002|0", "title": "MacBook Pro M3 Max 64GB"},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        write_feed_cache(items, tmpdir, date_str="2026-07-05", category="175672")
        cache = load_feed_cache(tmpdir)
    assert "v1|001|0" in cache
    assert cache["v1|001|0"]["title"] == "ASUS ROG RTX 4090 24GB"
    assert len(cache) == 2


def test_load_feed_cache_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = load_feed_cache(tmpdir)
    assert cache == {}
