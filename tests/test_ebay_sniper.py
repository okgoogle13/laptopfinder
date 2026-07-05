"""Unit test suite for scripts/ebay_sniper.py.

Verifies normalization, firewall rejection regex, and local price floor logic
without making network requests or invoking osascript.
"""

from scripts.ebay_sniper import normalize, apply_firewall, run_strategy_local


def test_normalize():
    assert normalize("  RTX 4090  ") == "RTX4090"
    assert normalize("m3 max") == "M3MAX"
    assert normalize("Strix   Halo") == "STRIXHALO"


def test_apply_firewall():
    mock_srl = {
        "data_integrity": {
            "exclusion_regex": r"(?i)(bare shell|missing motherboard|screen only|no mobile-gpu|no core|chassis only|parts only|read description|junk|as-is|bare board)"
        }
    }
    
    # Valid gaming laptops should pass
    assert apply_firewall("ASUS ROG Strix SCAR 18 RTX 4090 24GB Gaming Laptop", mock_srl) is True
    assert apply_firewall("MacBook Pro M3 Max 36GB RAM 1TB SSD - Excellent Condition", mock_srl) is True
    
    # Parts-only / salvaged laptops should be rejected by firewall
    assert apply_firewall("ASUS ROG Strix RTX 4090 Laptop - Bare Shell No Motherboard", mock_srl) is False
    assert apply_firewall("Lenovo Legion RTX 4080 Screen Only For Parts", mock_srl) is False
    assert apply_firewall("MSI Titan RTX 3080 Ti Chassis Only Read Description", mock_srl) is False


def test_price_floor_logic(monkeypatch):
    """Verify that Strategy B honors SRL observed_au_price_min_aud thresholds."""
    mock_srl = {
        "data_integrity": {"exclusion_regex": "bare shell"},
        "target_gpus": {
            "RTX 4080": {"observed_au_price_min_aud": 2500},
            "RTX 3080": {"observed_au_price_min_aud": 1400}
        }
    }
    
    mock_items = {
        "itemSummaries": [
            {
                "itemId": "v1|101|0",
                "title": "ASUS ROG Strix RTX 4080 Gaming Laptop",
                "price": {"value": "2600.0"},  # <= 2500 * 1.10 (2750), should HIT
                "itemWebUrl": "http://example.com/101"
            },
            {
                "itemId": "v1|102|0",
                "title": "Razer Blade 16 RTX 4080 Laptop",
                "price": {"value": "3500.0"},  # > 2750, should be IGNORED
                "itemWebUrl": "http://example.com/102"
            },
            {
                "itemId": "v1|103|0",
                "title": "Lenovo Legion 7 RTX 3080 Laptop",
                "price": {"value": "1350.0"},  # <= 1400 * 1.10 (1540), should HIT
                "itemWebUrl": "http://example.com/103"
            }
        ]
    }
    
    # Mock execute_browse_query to return our mock_items
    monkeypatch.setattr("scripts.ebay_sniper.execute_browse_query", lambda token, params, headers=None: mock_items)
    
    seen = set()
    models = list(mock_srl["target_gpus"].keys())
    new_seen = run_strategy_local("mock_token", seen, mock_srl, models=models, dry_run=True)
    
    assert "v1|101|0" in new_seen
    assert "v1|102|0" not in new_seen  # Rejected by price floor threshold
    assert "v1|103|0" in new_seen
