"""Tests for scripts/render_matrix.py"""
import importlib.util
import sys
from pathlib import Path


# Load render_matrix as a module from scripts/ (not a package)
_script = Path(__file__).parent.parent / "scripts" / "render_matrix.py"
_spec = importlib.util.spec_from_file_location("render_matrix", _script)
render_matrix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_matrix)

load_candidates = render_matrix.load_candidates
sort_candidates = render_matrix.sort_candidates
render_table = render_matrix.render_table
main = render_matrix.main


# ── load_candidates ──────────────────────────────────────────────────────────

class TestLoadCandidates:
    def test_load_candidates_two_valid_entries(self, tmp_path):
        f = tmp_path / "list.jsonl"
        f.write_text(
            '{"recommended_action": "SHORTLIST", "llm_index_score": 80}\n'
            '{"recommended_action": "SKIP", "llm_index_score": 10}\n'
        )
        result = load_candidates(str(f))
        assert len(result) == 2

    def test_load_candidates_skips_bad_line(self, tmp_path, capsys):
        f = tmp_path / "list.jsonl"
        f.write_text(
            '{"recommended_action": "SHORTLIST", "llm_index_score": 80}\n'
            "this is not json\n"
            '{"recommended_action": "SKIP", "llm_index_score": 10}\n'
        )
        result = load_candidates(str(f))
        assert len(result) == 2
        assert "WARN" in capsys.readouterr().err

    def test_load_candidates_empty_file(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        assert load_candidates(str(f)) == []


# ── sort_candidates ──────────────────────────────────────────────────────────

class TestSortCandidates:
    def test_sort_group_order(self):
        candidates = [
            {"recommended_action": "SKIP", "llm_index_score": 20},
            {"recommended_action": "MONITOR", "llm_index_score": 60},
            {"recommended_action": "SHORTLIST", "llm_index_score": 85},
        ]
        result = sort_candidates(candidates)
        assert [c["recommended_action"] for c in result] == ["SHORTLIST", "MONITOR", "SKIP"]

    def test_sort_within_group_descending_score(self):
        candidates = [
            {"recommended_action": "SHORTLIST", "llm_index_score": 50},
            {"recommended_action": "SHORTLIST", "llm_index_score": 90},
            {"recommended_action": "SHORTLIST", "llm_index_score": 70},
        ]
        result = sort_candidates(candidates)
        assert [c["llm_index_score"] for c in result] == [90, 70, 50]

    def test_sort_null_score_last_in_group(self):
        candidates = [
            {"recommended_action": "SHORTLIST", "llm_index_score": None},
            {"recommended_action": "SHORTLIST", "llm_index_score": 85},
        ]
        result = sort_candidates(candidates)
        assert result[0]["llm_index_score"] == 85
        assert result[1]["llm_index_score"] is None

    def test_sort_missing_action_last(self):
        candidates = [
            {"recommended_action": "SKIP", "llm_index_score": 20},
            {"llm_index_score": 99},  # no recommended_action
        ]
        result = sort_candidates(candidates)
        assert result[0]["recommended_action"] == "SKIP"
        assert "recommended_action" not in result[1]

    def test_sort_zero_score_above_null(self):
        """Score of 0 is a valid score and must sort above null/missing."""
        candidates = [
            {"recommended_action": "SHORTLIST", "llm_index_score": None},
            {"recommended_action": "SHORTLIST", "llm_index_score": 0},
        ]
        result = sort_candidates(candidates)
        assert result[0]["llm_index_score"] == 0
        assert result[1]["llm_index_score"] is None

    def test_sort_missing_score_key_last(self):
        candidates = [
            {"recommended_action": "SHORTLIST"},  # no llm_index_score key
            {"recommended_action": "SHORTLIST", "llm_index_score": 70},
        ]
        result = sort_candidates(candidates)
        assert result[0]["llm_index_score"] == 70
        assert "llm_index_score" not in result[1]


# ── render_table ─────────────────────────────────────────────────────────────

class TestRenderTable:
    def test_render_table_header(self):
        output = render_table([])
        assert "| Rank |" in output
        assert "| Action |" in output
        assert "| Score |" in output
        assert "| Title |" in output
        assert "| GPU |" in output
        assert "| Price |" in output
        assert "| Notes |" in output

    def test_render_table_pipe_escaping(self):
        candidates = [{"listing_title": "Laptop | Bundle"}]
        output = render_table(candidates)
        assert r"Laptop \| Bundle" in output

    def test_render_table_newline_stripped(self):
        candidates = [{"listing_title": "Laptop\nBundle"}]
        output = render_table(candidates)
        assert "Laptop Bundle" in output

    def test_render_table_missing_field_dash(self):
        candidates = [{"recommended_action": "SHORTLIST"}]
        output = render_table(candidates)
        assert "—" in output

    def test_render_table_two_rows(self):
        candidates = [
            {"recommended_action": "SHORTLIST", "llm_index_score": 80},
            {"recommended_action": "SKIP", "llm_index_score": 10},
        ]
        output = render_table(candidates)
        # Header + separator + 2 data rows
        data_rows = [line for line in output.splitlines() if line.startswith("|") and "---" not in line and "Rank" not in line]
        assert len(data_rows) == 2


# ── main (integration) ───────────────────────────────────────────────────────

class TestMain:
    def test_main_integration(self, tmp_path, monkeypatch):
        in_file = tmp_path / "input.jsonl"
        out_file = tmp_path / "output.md"
        in_file.write_text(
            '{"recommended_action": "SKIP", "llm_index_score": 10, "listing_title": "Cheap junk"}\n'
            '{"recommended_action": "SHORTLIST", "llm_index_score": 85, "listing_title": "RTX beast"}\n'
        )
        monkeypatch.setattr(
            sys, "argv",
            ["render_matrix.py", "--in", str(in_file), "--out", str(out_file)],
        )
        main()
        content = out_file.read_text()
        assert "RTX beast" in content
        assert "Cheap junk" in content
        # SHORTLIST appears before SKIP
        assert content.index("RTX beast") < content.index("Cheap junk")
        assert "# Purchase Decision Matrix" in content
