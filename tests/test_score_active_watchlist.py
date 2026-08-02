"""Tests for scripts/score_active_watchlist.py decision engine and value candidate logic."""
from __future__ import annotations

import importlib.util
from pathlib import Path

# Load score_active_watchlist as a module from scripts/ (not a package)
_script = Path(__file__).parent.parent / "scripts" / "score_active_watchlist.py"
_spec = importlib.util.spec_from_file_location("score_active_watchlist", _script)
score_active_watchlist = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_active_watchlist)

is_value_candidate = score_active_watchlist.is_value_candidate
decide_watchlist_item = score_active_watchlist.decide_watchlist_item


class TestValueCandidateAndDecisionRouting:
    def test_value_shortlist_routing(self):
        """Creates a fake item with scope_ok=True, llm_hw_score=0.52, vram_gb=16, system_ram_gb=32,

        value_per_dollar clearly high, and price_band_tag='VALUE_ZONE'.
        Verifies it routes to 'VALUE_SHORTLIST' (and not 'SHORTLIST').
        """
        fake_item = {
            "scope_ok": True,
            "llm_hw_score": 0.52,
            "vram_gb": 16,
            "system_ram_gb": 32,
            "value_per_dollar": 0.020,
            "price_band_tag": "VALUE_ZONE",
        }
        assert is_value_candidate(fake_item) is True
        decision, decision_reason, val_candidate = decide_watchlist_item(fake_item)
        assert val_candidate is True
        assert decision == "VALUE_SHORTLIST"
        assert decision != "SHORTLIST"
        assert decision_reason == "value_shortlist_candidate"

    def test_shortlist_routing_overrides_value_shortlist(self):
        """Creates another item with llm_hw_score=0.60, value_per_dollar >= 0.015, and correct price_band,

        verifying it goes to 'SHORTLIST', not 'VALUE_SHORTLIST'.
        """
        fake_item = {
            "scope_ok": True,
            "llm_hw_score": 0.60,
            "vram_gb": 16,
            "system_ram_gb": 32,
            "value_per_dollar": 0.016,
            "price_band_tag": "VALUE_ZONE",
        }
        # It meets SHORTLIST criteria (llm_hw_score >= 0.57, value_per_dollar >= 0.015, price_band in VALUE_ZONE/FAIR_MARKET)
        decision, decision_reason, val_candidate = decide_watchlist_item(fake_item)
        assert decision == "SHORTLIST"
        assert decision != "VALUE_SHORTLIST"
        assert decision_reason == "shortlist_criteria"

    def test_is_value_candidate_guardrails(self):
        """Verify that capability guardrails block items below thresholds."""
        base_item = {
            "scope_ok": True,
            "llm_hw_score": 0.52,
            "vram_gb": 16,
            "system_ram_gb": 32,
            "value_per_dollar": 0.020,
            "price_band_tag": "VALUE_ZONE",
        }
        # Fails scope_ok
        assert is_value_candidate({**base_item, "scope_ok": False}) is False
        # Fails vram_gb < 12
        assert is_value_candidate({**base_item, "vram_gb": 8}) is False
        # Fails system_ram_gb < 32
        assert is_value_candidate({**base_item, "system_ram_gb": 16}) is False
        # Fails llm_hw_score < 0.50
        assert is_value_candidate({**base_item, "llm_hw_score": 0.49}) is False

    def test_is_value_candidate_unicorn_clause(self):
        """Verify the non-standard unicorn clause (e.g., 14\" Razer with 16 GB VRAM)."""
        unicorn_item = {
            "scope_ok": True,
            "llm_hw_score": 0.51,
            "vram_gb": 16,
            "system_ram_gb": 32,
            "value_per_dollar": 0.015,
            "price_band_tag": "OVERPRICED",  # Not in VALUE_ZONE/FAIR_MARKET, but meets unicorn rule
            "screen_inches": 14,
        }
        assert is_value_candidate(unicorn_item) is True
        decision, _, val_candidate = decide_watchlist_item(unicorn_item)
        assert val_candidate is True
        assert decision == "VALUE_SHORTLIST"
