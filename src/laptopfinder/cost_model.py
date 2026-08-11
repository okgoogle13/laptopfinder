"""Landed cost modelling for laptopfinder.

Handles complex scenarios for international purchases, including VAT/GST boundaries
and hand-carry rules.
"""

from typing import Any, Optional


def _get_rate(currency: str, ref: dict) -> float:
    rates = ref.get("currency_normalization", {}).get("exchange_rates_to_aud", {})
    return float(rates.get(currency.upper(), 1.0))


def calculate_landed_cost_scenarios(
    listing_price_local: float,
    currency: str,
    source_country: str,
    delivery_feasibility: Optional[str],
    ref: dict
) -> list[dict[str, Any]]:
    """Calculate all relevant landed cost scenarios based on the item's location."""
    
    currency_upper = currency.upper()
    rate = _get_rate(currency_upper, ref)
    base_price_aud = listing_price_local * rate
    
    scenarios: list[dict[str, Any]] = []
    
    cn = ref.get("currency_normalization", {})
    au_gst_rate = cn.get("au_gst_rate", 0.10)
    apply_uk_vat_refund = cn.get("apply_uk_vat_refund_on_hand_carry", False)
    uk_vat_rate = cn.get("uk_vat_rate", 0.20)
    
    if source_country.upper() == "AU":
        scenarios.append({
            "scenario_name": "Australian purchase",
            "base_price_local": listing_price_local,
            "currency": currency_upper,
            "exchange_rate": rate,
            "base_price_aud": base_price_aud,
            "shipping_cost_aud": 0.0,  # Assumption or pass in
            "tax_cost_aud": 0.0,       # Already included in local AU price
            "total_landed_cost_aud": base_price_aud,
            "delivery_feasibility": delivery_feasibility,
            "notes": ["Standard domestic purchase."]
        })
    elif source_country.upper() == "UK":
        # 1. UK purchase delivered to parents
        scenarios.append({
            "scenario_name": "UK purchase delivered to parents",
            "base_price_local": listing_price_local,
            "currency": currency_upper,
            "exchange_rate": rate,
            "base_price_aud": base_price_aud,
            "shipping_cost_aud": 0.0, 
            "tax_cost_aud": 0.0, # VAT already in UK price, no AU GST
            "total_landed_cost_aud": base_price_aud,
            "delivery_feasibility": delivery_feasibility,
            "notes": ["Delivered to UK address.", "No AU GST applied."]
        })
        
        # 2. UK purchase hand-carried to Australia
        tax_deduction_aud = 0.0
        if apply_uk_vat_refund:
            # Assumes the listing price includes 20% VAT which can be fully reclaimed.
            # Base price * (0.20 / 1.20)
            vat_portion_local = listing_price_local * (uk_vat_rate / (1 + uk_vat_rate))
            tax_deduction_aud = -(vat_portion_local * rate)
            
        scenarios.append({
            "scenario_name": "UK purchase hand-carried to Australia",
            "base_price_local": listing_price_local,
            "currency": currency_upper,
            "exchange_rate": rate,
            "base_price_aud": base_price_aud,
            "shipping_cost_aud": 0.0,
            "tax_cost_aud": tax_deduction_aud,
            "total_landed_cost_aud": base_price_aud + tax_deduction_aud,
            "delivery_feasibility": delivery_feasibility,
            "notes": [
                "Hand-carried as personal item.",
                "Assumes VAT reclaim at border." if apply_uk_vat_refund else "Conservative: no VAT reclaim assumed (VAT margin scheme)."
            ]
        })
        
        # 3. UK seller shipping directly to Australia
        # GST applied if > 1000 AUD (historically, though now it's often collected at POS by eBay)
        # We will apply it to the base price for comparison.
        shipping_est_aud = 150.0  # Rough estimate for international shipping
        subtotal_aud = base_price_aud + shipping_est_aud
        
        gst_aud = 0.0
        if cn.get("apply_au_gst_on_imports_over_1000_aud", True) and subtotal_aud > 1000.0:
            gst_aud = subtotal_aud * au_gst_rate
            
        scenarios.append({
            "scenario_name": "UK seller shipping directly to Australia",
            "base_price_local": listing_price_local,
            "currency": currency_upper,
            "exchange_rate": rate,
            "base_price_aud": base_price_aud,
            "shipping_cost_aud": shipping_est_aud,
            "tax_cost_aud": gst_aud,
            "total_landed_cost_aud": subtotal_aud + gst_aud,
            "delivery_feasibility": "Requires international shipping",
            "notes": ["Includes estimated shipping ($150 AUD).", "AU GST applied if over $1000."]
        })
    else:
        # Generic fallback
        scenarios.append({
            "scenario_name": "Standard purchase",
            "base_price_local": listing_price_local,
            "currency": currency_upper,
            "exchange_rate": rate,
            "base_price_aud": base_price_aud,
            "shipping_cost_aud": 0.0,
            "tax_cost_aud": 0.0,
            "total_landed_cost_aud": base_price_aud,
            "delivery_feasibility": delivery_feasibility,
            "notes": ["Fallback scenario for unknown location."]
        })
        
    return scenarios
