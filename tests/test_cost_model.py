import pytest
from laptopfinder.cost_model import calculate_landed_cost_scenarios

@pytest.fixture
def mock_ref():
    return {
        "currency_normalization": {
            "exchange_rates_to_aud": {
                "AUD": 1.0,
                "GBP": 1.98,
                "USD": 1.55
            },
            "apply_au_gst_on_imports_over_1000_aud": True,
            "au_gst_rate": 0.10,
            "uk_vat_rate": 0.20,
            "apply_uk_vat_refund_on_hand_carry": False
        }
    }

def test_au_purchase(mock_ref):
    scenarios = calculate_landed_cost_scenarios(
        listing_price_local=3000.0,
        currency="AUD",
        source_country="AU",
        delivery_feasibility="Available",
        ref=mock_ref
    )
    
    assert len(scenarios) == 1
    s = scenarios[0]
    assert s["scenario_name"] == "Australian purchase"
    assert s["base_price_aud"] == 3000.0
    assert s["total_landed_cost_aud"] == 3000.0

def test_uk_purchase_no_vat_refund(mock_ref):
    # £1500 * 1.98 = $2970 AUD
    scenarios = calculate_landed_cost_scenarios(
        listing_price_local=1500.0,
        currency="GBP",
        source_country="UK",
        delivery_feasibility="Available",
        ref=mock_ref
    )
    
    assert len(scenarios) == 3
    
    # 1. Parents
    s_parents = scenarios[0]
    assert s_parents["scenario_name"] == "UK purchase delivered to parents"
    assert s_parents["total_landed_cost_aud"] == 2970.0
    
    # 2. Hand carry
    s_carry = scenarios[1]
    assert s_carry["scenario_name"] == "UK purchase hand-carried to Australia"
    assert s_carry["tax_cost_aud"] == 0.0
    assert s_carry["total_landed_cost_aud"] == 2970.0
    
    # 3. Ship direct
    s_ship = scenarios[2]
    assert s_ship["scenario_name"] == "UK seller shipping directly to Australia"
    subtotal = 2970.0 + 150.0  # shipping_est_aud
    assert s_ship["tax_cost_aud"] == pytest.approx(subtotal * 0.10)
    assert s_ship["total_landed_cost_aud"] == pytest.approx(subtotal * 1.10)

def test_uk_purchase_with_vat_refund(mock_ref):
    mock_ref["currency_normalization"]["apply_uk_vat_refund_on_hand_carry"] = True
    
    # £1200 * 1.98 = $2376 AUD
    # VAT portion: £1200 * (0.20/1.20) = £200 = $396 AUD
    scenarios = calculate_landed_cost_scenarios(
        listing_price_local=1200.0,
        currency="GBP",
        source_country="UK",
        delivery_feasibility="Available",
        ref=mock_ref
    )
    
    s_carry = scenarios[1]
    assert s_carry["scenario_name"] == "UK purchase hand-carried to Australia"
    assert s_carry["tax_cost_aud"] == pytest.approx(-396.0)
    assert s_carry["total_landed_cost_aud"] == pytest.approx(2376.0 - 396.0)
