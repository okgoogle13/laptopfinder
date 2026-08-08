import pytest
from src.laptopfinder.decide import _comps_adjustment_points

@pytest.fixture
def base_ref():
    return {"llm_index_score": {}}

def test_comps_adjustment_below_85(base_ref):
    """Below 85% of median comps (e.g. 800 vs 1000)."""
    analysis = {
        "metadata": {
            "listing_price_aud": 800.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 10

def test_comps_adjustment_exactly_85(base_ref):
    """Exactly 85% of median comps."""
    analysis = {
        "metadata": {
            "listing_price_aud": 850.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 10

def test_comps_adjustment_between_85_95(base_ref):
    """Between 85% and 95% of median comps (e.g. 900 vs 1000)."""
    analysis = {
        "metadata": {
            "listing_price_aud": 900.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 5

def test_comps_adjustment_exactly_95(base_ref):
    """Exactly 95% of median comps."""
    analysis = {
        "metadata": {
            "listing_price_aud": 950.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 5

def test_comps_adjustment_between_95_105(base_ref):
    """Between 95% and 105% of median comps (e.g. 1000 vs 1000). Should be 0 points."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1000.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 0

def test_comps_adjustment_exactly_105(base_ref):
    """Exactly 105% of median comps."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1050.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == -5

def test_comps_adjustment_between_105_115(base_ref):
    """Between 105% and 115% of median comps (e.g. 1100 vs 1000)."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1100.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == -5

def test_comps_adjustment_exactly_115(base_ref):
    """Exactly 115% of median comps."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1150.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == -10

def test_comps_adjustment_above_115(base_ref):
    """Above 115% of median comps (e.g. 1200 vs 1000)."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1200.0,
            "comps_median_sold_aud": 1000.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == -10

def test_comps_adjustment_no_data(base_ref):
    """No usable sold-comps data."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1000.0
        } # Missing comps_median_sold_aud
    }
    assert _comps_adjustment_points(analysis, base_ref) == 0

def test_comps_adjustment_zero_division(base_ref):
    """Zero division protection."""
    analysis = {
        "metadata": {
            "listing_price_aud": 1000.0,
            "comps_median_sold_aud": 0.0
        }
    }
    assert _comps_adjustment_points(analysis, base_ref) == 0
