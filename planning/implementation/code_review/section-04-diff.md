diff --git a/scripts/render_matrix.py b/scripts/render_matrix.py
new file mode 100644
index 0000000..c2a5374
--- /dev/null
+++ b/scripts/render_matrix.py
@@ -0,0 +1,93 @@
+"""Render a JSONL shortlist into a sorted Markdown purchase-decision table."""
+import argparse
+import datetime
+import json
+import sys
+
+
+def load_candidates(path: str) -> list[dict]:
+    """Read JSONL file at path. Parse each line as JSON.
+    Skip malformed lines with a WARN to stderr.
+    Return list of successfully parsed dicts."""
+    results = []
+    with open(path, encoding="utf-8") as fh:
+        for i, line in enumerate(fh, 1):
+            line = line.strip()
+            if not line:
+                continue
+            try:
+                results.append(json.loads(line))
+            except json.JSONDecodeError as e:
+                print(f"WARN: skipping malformed line {i}: {e}", file=sys.stderr)
+    return results
+
+
+def sort_candidates(candidates: list[dict]) -> list[dict]:
+    """Sort by action priority group: SHORTLIST=0, MONITOR=1, SKIP=2, unknown=3.
+    Within each group, sort descending by llm_index_score.
+    Treat missing or null llm_index_score as -1 (sorts last in group).
+    Does not mutate the input list."""
+    priority = {"SHORTLIST": 0, "MONITOR": 1, "SKIP": 2}
+
+    def sort_key(c):
+        group = priority.get(c.get("recommended_action"), 3)
+        score = -(c.get("llm_index_score") or -1)
+        return (group, score)
+
+    return sorted(candidates, key=sort_key)
+
+
+def render_table(candidates: list[dict]) -> str:
+    """Return a Markdown table string for the given candidates.
+    Columns: Rank, Action, Score, Title, GPU, Price, Notes.
+    All cell values have | escaped as \\| and newlines stripped.
+    Missing keys render as — (em dash, not hyphen)."""
+
+    def cell(v) -> str:
+        if v is None:
+            return "—"
+        return str(v).replace("\n", " ").replace("|", r"\|")
+
+    header = "| Rank | Action | Score | Title | GPU | Price | Notes |"
+    separator = "|------|--------|-------|-------|-----|-------|-------|"
+    rows = [header, separator]
+
+    for rank, c in enumerate(candidates, 1):
+        rows.append(
+            f"| {rank} "
+            f"| {cell(c.get('recommended_action'))} "
+            f"| {cell(c.get('llm_index_score'))} "
+            f"| {cell(c.get('listing_title'))} "
+            f"| {cell(c.get('gpu'))} "
+            f"| {cell(c.get('price'))} "
+            f"| {cell(c.get('notes'))} |"
+        )
+
+    return "\n".join(rows)
+
+
+def main() -> None:
+    """CLI entry point.
+    Flags: --in (default: data/shortlist_candidates.jsonl), --out (default: data/purchase_matrix.md).
+    Loads candidates, sorts, renders table, prepends a heading with ISO timestamp, writes to --out.
+    Prints confirmation line to stdout."""
+    parser = argparse.ArgumentParser(description="Render JSONL shortlist to Markdown matrix")
+    parser.add_argument("--in", dest="input", default="data/shortlist_candidates.jsonl")
+    parser.add_argument("--out", default="data/purchase_matrix.md")
+    args = parser.parse_args()
+
+    candidates = load_candidates(args.input)
+    candidates = sort_candidates(candidates)
+    table = render_table(candidates)
+
+    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
+    content = f"# Purchase Decision Matrix\n\nGenerated: {timestamp}\n\n{table}\n"
+
+    with open(args.out, "w", encoding="utf-8") as fh:
+        fh.write(content)
+
+    print(f"Matrix written to {args.out} ({len(candidates)} entries)")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/tests/test_render_matrix.py b/tests/test_render_matrix.py
new file mode 100644
index 0000000..6a7fbe1
--- /dev/null
+++ b/tests/test_render_matrix.py
@@ -0,0 +1,159 @@
+"""Tests for scripts/render_matrix.py"""
+import importlib.util
+import json
+import sys
+from pathlib import Path
+
+import pytest
+
+# Load render_matrix as a module from scripts/ (not a package)
+_script = Path(__file__).parent.parent / "scripts" / "render_matrix.py"
+_spec = importlib.util.spec_from_file_location("render_matrix", _script)
+render_matrix = importlib.util.module_from_spec(_spec)
+_spec.loader.exec_module(render_matrix)
+
+load_candidates = render_matrix.load_candidates
+sort_candidates = render_matrix.sort_candidates
+render_table = render_matrix.render_table
+main = render_matrix.main
+
+
+# ── load_candidates ──────────────────────────────────────────────────────────
+
+class TestLoadCandidates:
+    def test_load_candidates_two_valid_entries(self, tmp_path):
+        f = tmp_path / "list.jsonl"
+        f.write_text(
+            '{"recommended_action": "SHORTLIST", "llm_index_score": 80}\n'
+            '{"recommended_action": "SKIP", "llm_index_score": 10}\n'
+        )
+        result = load_candidates(str(f))
+        assert len(result) == 2
+
+    def test_load_candidates_skips_bad_line(self, tmp_path, capsys):
+        f = tmp_path / "list.jsonl"
+        f.write_text(
+            '{"recommended_action": "SHORTLIST", "llm_index_score": 80}\n'
+            "this is not json\n"
+            '{"recommended_action": "SKIP", "llm_index_score": 10}\n'
+        )
+        result = load_candidates(str(f))
+        assert len(result) == 2
+        assert "WARN" in capsys.readouterr().err
+
+    def test_load_candidates_empty_file(self, tmp_path):
+        f = tmp_path / "empty.jsonl"
+        f.write_text("")
+        assert load_candidates(str(f)) == []
+
+
+# ── sort_candidates ──────────────────────────────────────────────────────────
+
+class TestSortCandidates:
+    def test_sort_group_order(self):
+        candidates = [
+            {"recommended_action": "SKIP", "llm_index_score": 20},
+            {"recommended_action": "MONITOR", "llm_index_score": 60},
+            {"recommended_action": "SHORTLIST", "llm_index_score": 85},
+        ]
+        result = sort_candidates(candidates)
+        assert [c["recommended_action"] for c in result] == ["SHORTLIST", "MONITOR", "SKIP"]
+
+    def test_sort_within_group_descending_score(self):
+        candidates = [
+            {"recommended_action": "SHORTLIST", "llm_index_score": 50},
+            {"recommended_action": "SHORTLIST", "llm_index_score": 90},
+            {"recommended_action": "SHORTLIST", "llm_index_score": 70},
+        ]
+        result = sort_candidates(candidates)
+        assert [c["llm_index_score"] for c in result] == [90, 70, 50]
+
+    def test_sort_null_score_last_in_group(self):
+        candidates = [
+            {"recommended_action": "SHORTLIST", "llm_index_score": None},
+            {"recommended_action": "SHORTLIST", "llm_index_score": 85},
+        ]
+        result = sort_candidates(candidates)
+        assert result[0]["llm_index_score"] == 85
+        assert result[1]["llm_index_score"] is None
+
+    def test_sort_missing_action_last(self):
+        candidates = [
+            {"recommended_action": "SKIP", "llm_index_score": 20},
+            {"llm_index_score": 99},  # no recommended_action
+        ]
+        result = sort_candidates(candidates)
+        assert result[0]["recommended_action"] == "SKIP"
+        assert "recommended_action" not in result[1]
+
+    def test_sort_missing_score_key_last(self):
+        candidates = [
+            {"recommended_action": "SHORTLIST"},  # no llm_index_score key
+            {"recommended_action": "SHORTLIST", "llm_index_score": 70},
+        ]
+        result = sort_candidates(candidates)
+        assert result[0]["llm_index_score"] == 70
+        assert "llm_index_score" not in result[1]
+
+
+# ── render_table ─────────────────────────────────────────────────────────────
+
+class TestRenderTable:
+    def test_render_table_header(self):
+        output = render_table([])
+        assert "| Rank |" in output
+        assert "| Action |" in output
+        assert "| Score |" in output
+        assert "| Title |" in output
+        assert "| GPU |" in output
+        assert "| Price |" in output
+        assert "| Notes |" in output
+
+    def test_render_table_pipe_escaping(self):
+        candidates = [{"listing_title": "Laptop | Bundle"}]
+        output = render_table(candidates)
+        assert r"Laptop \| Bundle" in output
+
+    def test_render_table_newline_stripped(self):
+        candidates = [{"listing_title": "Laptop\nBundle"}]
+        output = render_table(candidates)
+        assert "Laptop Bundle" in output
+        assert "\n\n" not in output.replace("\n| ", "")  # no bare newlines in cells
+
+    def test_render_table_missing_field_dash(self):
+        candidates = [{"recommended_action": "SHORTLIST"}]
+        output = render_table(candidates)
+        assert "—" in output
+
+    def test_render_table_two_rows(self):
+        candidates = [
+            {"recommended_action": "SHORTLIST", "llm_index_score": 80},
+            {"recommended_action": "SKIP", "llm_index_score": 10},
+        ]
+        output = render_table(candidates)
+        # Header + separator + 2 data rows
+        data_rows = [l for l in output.splitlines() if l.startswith("|") and "---" not in l and "Rank" not in l]
+        assert len(data_rows) == 2
+
+
+# ── main (integration) ───────────────────────────────────────────────────────
+
+class TestMain:
+    def test_main_integration(self, tmp_path, monkeypatch):
+        in_file = tmp_path / "input.jsonl"
+        out_file = tmp_path / "output.md"
+        in_file.write_text(
+            '{"recommended_action": "SKIP", "llm_index_score": 10, "listing_title": "Cheap junk"}\n'
+            '{"recommended_action": "SHORTLIST", "llm_index_score": 85, "listing_title": "RTX beast"}\n'
+        )
+        monkeypatch.setattr(
+            sys, "argv",
+            ["render_matrix.py", "--in", str(in_file), "--out", str(out_file)],
+        )
+        main()
+        content = out_file.read_text()
+        assert "RTX beast" in content
+        assert "Cheap junk" in content
+        # SHORTLIST appears before SKIP
+        assert content.index("RTX beast") < content.index("Cheap junk")
+        assert "# Purchase Decision Matrix" in content
