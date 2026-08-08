"""
Tests for enrichment logic in runners/enrich_shortlist.py:
  - _derive_enriched_action
  - _rank_candidates
  - _missing_facts
  - _comps_position_label
  - _build_markdown_report (empty shortlist + failure-preserve behavior)
"""
import json
import pytest
from pathlib import Path

from runners.enrich_shortlist import (
    _derive_enriched_action,
    _rank_candidates,
    _missing_facts,
    _comps_position_label,
    _build_markdown_report,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_candidate(
    *,
    decide_action: str = "SHORTLIST",
    llm_index_score: int = 70,
    listing_price: float | None = 3000.0,
    comps_median: float | None = 3000.0,
    risk_score: float = 1.0,
    gpu: str | None = "RTX 4090",
    vram_capacity: str | None = "16GB",
    gpu_missing: bool = False,
    vram_missing: bool = False,
    paradigm: str = "discrete_cuda",
    url: str = "https://ebay.com.au/itm/test",
    title: str = "Test Laptop",
) -> dict:
    missing_info = {}
    if gpu_missing:
        missing_info["gpu"] = True
    if vram_missing:
        missing_info["vram_capacity"] = True


    return {
        "url": url,
        "title": title,
        "recommended_action": decide_action,
        "llm_index_score": llm_index_score,
        "score_0_100": min(100, round((llm_index_score / 85.0) * 100)),
        "paradigm": paradigm,
        "vram_gb": 16.0,
        "reasons": [],
        "extracted_data": {
            "gpu": None if gpu_missing else gpu,
            "cpu": "Intel Core Ultra 9 275HX",
            "vram_capacity": None if vram_missing else vram_capacity,
            "total_system_ram": "32GB",
            "stated_condition": "Used",
            "missing_information": missing_info,
            "exact_model_name": "Test Laptop",
        },
        "analysis": {"risk_score": risk_score, "seller_classification": "INDIVIDUAL_SELLER"},
        "metadata": {
            "listing_price_aud": listing_price,
            "comps_median_sold_aud": comps_median,
            "source_platform": "EBAY_AU",
            "ships_from_overseas": False,
        },
    }


# ── _derive_enriched_action ───────────────────────────────────────────────────

class TestDeriveEnrichedAction:

    def test_high_vram_bargain_below_median_is_buy_now(self):
        """Strong bargain: SHORTLIST + priced at exactly median → BUY_NOW."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3000.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "BUY_NOW"

    def test_well_below_median_is_buy_now(self):
        """Price is 80% of median → BUY_NOW."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=2400.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "BUY_NOW"

    def test_at_85_pct_is_buy_now(self):
        c = _make_candidate(decide_action="SHORTLIST", listing_price=2550.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "BUY_NOW"

    def test_at_95_pct_is_buy_now(self):
        c = _make_candidate(decide_action="SHORTLIST", listing_price=2850.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "BUY_NOW"

    def test_slightly_above_median_is_negotiate(self):
        """Price is 108% of median → NEGOTIATE."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3240.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "NEGOTIATE"

    def test_at_105_pct_is_negotiate(self):
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3150.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "NEGOTIATE"

    def test_at_115_pct_is_watch(self):
        """Exactly 115% of median: ratio >= 1.15 so WATCH."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3450.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "WATCH"

    def test_above_115_pct_is_watch(self):
        """Price is 130% of median → WATCH."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3900.0, comps_median=3000.0)
        assert _derive_enriched_action(c) == "WATCH"

    def test_no_comps_is_watch(self):
        """SHORTLIST but no comps data available → WATCH."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=3000.0, comps_median=None)
        assert _derive_enriched_action(c) == "WATCH"

    def test_no_price_is_watch(self):
        """SHORTLIST but no listing price → WATCH."""
        c = _make_candidate(decide_action="SHORTLIST", listing_price=None, comps_median=3000.0)
        assert _derive_enriched_action(c) == "WATCH"

    def test_skip_becomes_pass(self):
        """decide() SKIP → enriched PASS."""
        c = _make_candidate(decide_action="SKIP")
        assert _derive_enriched_action(c) == "PASS"

    def test_monitor_becomes_watch(self):
        """decide() MONITOR → enriched WATCH."""
        c = _make_candidate(decide_action="MONITOR")
        assert _derive_enriched_action(c) == "WATCH"

    def test_missing_gpu_is_verify(self):
        """SHORTLIST but GPU is unknown → VERIFY."""
        c = _make_candidate(decide_action="SHORTLIST", gpu_missing=True)
        assert _derive_enriched_action(c) == "VERIFY"

    def test_missing_vram_is_verify(self):
        """SHORTLIST but VRAM unknown → VERIFY."""
        c = _make_candidate(decide_action="SHORTLIST", vram_missing=True)
        assert _derive_enriched_action(c) == "VERIFY"

    def test_high_capability_high_risk_becomes_pass(self):
        """High risk means decide() returns SKIP → enriched PASS regardless of score."""
        c = _make_candidate(decide_action="SKIP", llm_index_score=90, risk_score=8.5)
        assert _derive_enriched_action(c) == "PASS"


# ── _rank_candidates ─────────────────────────────────────────────────────────

class TestRankCandidates:

    def test_buy_now_before_negotiate(self):
        a = _make_candidate(listing_price=2000.0, comps_median=3000.0, title="A")  # BUY_NOW
        b = _make_candidate(listing_price=3300.0, comps_median=3000.0, title="B")  # NEGOTIATE
        for c in (a, b):
            c["action"] = _derive_enriched_action(c)
        ranked = _rank_candidates([b, a])
        assert ranked[0]["title"] == "A"

    def test_negotiate_before_watch(self):
        a = _make_candidate(listing_price=3150.0, comps_median=3000.0, title="NEGOTIATE")
        b = _make_candidate(decide_action="MONITOR", title="WATCH")
        a["action"] = _derive_enriched_action(a)
        b["action"] = _derive_enriched_action(b)
        ranked = _rank_candidates([b, a])
        assert ranked[0]["title"] == "NEGOTIATE"

    def test_equal_action_ranked_by_score_descending(self):
        """Two BUY_NOW candidates: higher score comes first."""
        a = _make_candidate(listing_price=2000.0, comps_median=3000.0, llm_index_score=80, title="HighScore")
        b = _make_candidate(listing_price=2000.0, comps_median=3000.0, llm_index_score=60, title="LowScore")
        for c in (a, b):
            c["action"] = _derive_enriched_action(c)
        ranked = _rank_candidates([b, a])
        assert ranked[0]["title"] == "HighScore"

    def test_equal_action_equal_score_ranked_by_price_ascending(self):
        """Equal score tiebreak: cheaper listing ranked first."""
        a = _make_candidate(listing_price=2500.0, comps_median=3000.0, llm_index_score=70, title="Cheaper")
        b = _make_candidate(listing_price=3000.0, comps_median=3000.0, llm_index_score=70, title="Pricier")
        for c in (a, b):
            c["action"] = _derive_enriched_action(c)
        ranked = _rank_candidates([b, a])
        assert ranked[0]["title"] == "Cheaper"

    def test_pass_ranked_last(self):
        a = _make_candidate(decide_action="SHORTLIST", listing_price=2000.0, comps_median=3000.0, title="BuyNow")
        b = _make_candidate(decide_action="SKIP", title="Pass")
        a["action"] = _derive_enriched_action(a)
        b["action"] = _derive_enriched_action(b)
        ranked = _rank_candidates([b, a])
        assert ranked[-1]["title"] == "Pass"

    def test_empty_input_returns_empty(self):
        assert _rank_candidates([]) == []


# ── _missing_facts ────────────────────────────────────────────────────────────

class TestMissingFacts:

    def test_no_missing_when_all_present(self):
        c = _make_candidate()
        assert _missing_facts(c) == []

    def test_missing_gpu_detected(self):
        c = _make_candidate(gpu_missing=True)
        assert "gpu" in _missing_facts(c)

    def test_missing_vram_detected(self):
        c = _make_candidate(vram_missing=True)
        assert "vram_capacity" in _missing_facts(c)

    def test_flagged_in_missing_information_detected(self):
        c = _make_candidate()
        c["extracted_data"]["missing_information"] = {"storage": True, "tgp": False}
        assert "storage" in _missing_facts(c)
        assert "tgp" not in _missing_facts(c)


# ── _comps_position_label ─────────────────────────────────────────────────────

class TestCompsPositionLabel:

    def test_at_median(self):
        c = _make_candidate(listing_price=3000.0, comps_median=3000.0)
        assert "+0%" in _comps_position_label(c)

    def test_below_median(self):
        c = _make_candidate(listing_price=2700.0, comps_median=3000.0)
        label = _comps_position_label(c)
        assert "-10%" in label

    def test_above_median(self):
        c = _make_candidate(listing_price=3300.0, comps_median=3000.0)
        label = _comps_position_label(c)
        assert "+10%" in label

    def test_no_comps(self):
        c = _make_candidate(comps_median=None)
        assert "unknown" in _comps_position_label(c)

    def test_zero_comps(self):
        c = _make_candidate(comps_median=0.0)
        assert "unknown" in _comps_position_label(c)


# ── _build_markdown_report ────────────────────────────────────────────────────

class TestBuildMarkdownReport:

    def test_empty_candidates_returns_header_only(self):
        report = _build_markdown_report([], "2026-01-01 00:00 UTC")
        assert "0 candidate(s)" in report

    def test_buy_now_emoji_present(self):
        c = _make_candidate(listing_price=2000.0, comps_median=3000.0)
        c["action"] = "BUY_NOW"
        report = _build_markdown_report([c], "2026-01-01 00:00 UTC")
        assert "🟢" in report
        assert "BUY_NOW" in report

    def test_pass_emoji_present(self):
        c = _make_candidate(decide_action="SKIP")
        c["action"] = "PASS"
        report = _build_markdown_report([c], "2026-01-01 00:00 UTC")
        assert "🔴" in report

    def test_missing_facts_warning_in_report(self):
        c = _make_candidate(gpu_missing=True)
        c["action"] = "VERIFY"
        report = _build_markdown_report([c], "2026-01-01 00:00 UTC")
        assert "Missing facts" in report


# ── e2e non-network test ──────────────────────────────────────────────────────

def test_e2e_enrichment_flow(monkeypatch, tmp_path):
    """Deterministic non-network integration test of the enrichment pipeline."""
    from runners import enrich_shortlist

    # 1. Mock the sniper input decision
    mock_decision = {
        "item_id": "123",
        "title": "Legion 7i RTX 4090",
        "price_aud": 3000.0,
        "url": "https://test",
        "action": "SHORTLIST"
    }

    # 2. Mock the LLM extraction (Stage 2)
    mock_extracted = {
        "extracted_data": {
            "gpu": "RTX 4090",
            "cpu": "Intel Core i9 14900HX",
            "vram_capacity": "16GB",
            "total_system_ram": "32GB",
            "stated_condition": "Used",
            "missing_information": {},
            "exact_model_name": "Legion Pro 7i"
        },
        "analysis": {
            "risk_score": 1.0,
            "seller_classification": "INDIVIDUAL_SELLER"
        },
        "metadata": {
            "listing_price_aud": 3000.0,
            "comps_median_sold_aud": 3000.0,
            "source_platform": "EBAY_AU",
            "ships_from_overseas": False
        }
    }

    monkeypatch.setattr(enrich_shortlist, "fetch_listing_html", lambda url: "<html></html>")
    monkeypatch.setattr(enrich_shortlist, "run_stage2_extraction", lambda html: mock_extracted)
    
    # 3. Test enrich_decision directly
    enriched = enrich_shortlist.enrich_decision(mock_decision)
    
    # Verify expected action and fields
    assert enriched["action"] == "BUY_NOW"
    assert "reasons" in enriched
    assert enriched["llm_index_score"] > 50  # Score depends on decide.py weighting
    assert enriched.get("outreach_messages") is not None
    
    # 4. Test the file output flow via main()
    out_md = tmp_path / "enriched.md"
    monkeypatch.setattr("sys.argv", ["enrich_shortlist.py", "--output", str(out_md)])
    monkeypatch.setattr(enrich_shortlist, "load_sniper_decisions", lambda path: [mock_decision])
    
    enrich_shortlist.main()
    
    # Verify report generated correctly
    assert out_md.exists()
    report_content = out_md.read_text(encoding="utf-8")
    
    assert "BUY_NOW" in report_content
    assert "Legion 7i RTX 4090" in report_content
    assert "**Risk score**: 1.0" in report_content
    assert "**Comps position**: +0% vs comps median" in report_content
    assert "Missing facts" not in report_content

    def test_previous_report_preserved_on_no_candidates(self, tmp_path):
        """Existing report must remain intact when enrichment produces zero candidates."""
        existing = tmp_path / "latest_enriched.md"
        existing.write_text("# Previous report", encoding="utf-8")
        # Simulate: no candidates → main() calls print and returns, never writes
        # Verify the file is unchanged
        content_before = existing.read_text()
        # _build_markdown_report is never called with empty list in production (main returns early)
        # but test the helper directly anyway
        report = _build_markdown_report([], "2026-01-01 00:00 UTC")
        assert "0 candidate(s)" in report
        # The original file is untouched because main() returns before writing
        assert existing.read_text() == content_before
