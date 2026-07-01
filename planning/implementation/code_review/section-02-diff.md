diff --git a/scripts/inject_config.py b/scripts/inject_config.py
new file mode 100644
index 0000000..ee8de56
--- /dev/null
+++ b/scripts/inject_config.py
@@ -0,0 +1,70 @@
+import json
+import re
+from pathlib import Path
+
+_REPO_ROOT = Path(__file__).parent.parent
+
+SRL_PATH = str(_REPO_ROOT / "config" / "static_reference_layer.json")
+
+PROMPT_FILES = [
+    str(_REPO_ROOT / "prompts" / "comet_discovery_agent.txt"),
+    str(_REPO_ROOT / "prompts" / "alternative_silicon_gemini.txt"),
+    str(_REPO_ROOT / "prompts" / "alternative_silicon_perplexity.txt"),
+]
+
+
+def load_srl(path: str) -> dict:
+    p = Path(path)
+    if not p.exists():
+        raise FileNotFoundError(f"SRL not found: {path}")
+    return json.loads(p.read_text(encoding="utf-8"))
+
+
+def build_substitutions(srl: dict) -> dict[str, str]:
+    gpu_names = list(srl["target_gpus"].keys())
+    watch_names = [entry["name"] for entry in srl["watch_list"]]
+    all_names = gpu_names + watch_names
+    formatted_list = "\n".join(f"- {name}" for name in all_names)
+
+    uma = srl["uma_platforms"]
+    return {
+        "TARGETS": formatted_list,
+        "TARGET_GPU_LIST": formatted_list,
+        "UMA_MIN_RAM_GB": str(uma["min_total_ram_gb_to_shortlist"]),
+        "UMA_CHIP_PATTERNS": ", ".join(uma["chip_patterns"]),
+    }
+
+
+def inject_file(path: str, substitutions: dict[str, str]) -> int:
+    p = Path(path)
+    if not p.exists():
+        raise FileNotFoundError(f"Prompt file not found: {path}")
+
+    content = p.read_text(encoding="utf-8")
+    count = 0
+    for key, value in substitutions.items():
+        pattern = (
+            rf"(<!-- BEGIN_INJECT:{re.escape(key)} -->)"
+            rf".*?"
+            rf"(<!-- END_INJECT:{re.escape(key)} -->)"
+        )
+        replacement = rf"\1\n{value}\n\2"
+        new_content, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
+        if n:
+            content = new_content
+            count += n
+
+    p.write_text(content, encoding="utf-8")
+    return count
+
+
+def main() -> None:
+    srl = load_srl(SRL_PATH)
+    substitutions = build_substitutions(srl)
+    for path in PROMPT_FILES:
+        n = inject_file(path, substitutions)
+        print(f"{Path(path).name}: {n} block(s) replaced")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/tests/test_inject_config.py b/tests/test_inject_config.py
new file mode 100644
index 0000000..e18f771
--- /dev/null
+++ b/tests/test_inject_config.py
@@ -0,0 +1,158 @@
+import json
+import sys
+from pathlib import Path
+
+import pytest
+
+sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
+from inject_config import build_substitutions, inject_file, load_srl
+
+MOCK_SRL = {
+    "target_gpus": {"RTX 3080": {}, "RTX 4090": {}},
+    "watch_list": [{"name": "RTX 5090"}, {"name": "GB200"}],
+    "uma_platforms": {
+        "min_total_ram_gb_to_shortlist": 64,
+        "chip_patterns": ["M3 Max", "M4 Ultra"],
+    },
+    "vram_gating_logic": {},
+}
+
+
+# --- load_srl ---
+
+
+def test_load_srl_returns_expected_keys(tmp_path):
+    srl_file = tmp_path / "srl.json"
+    srl_file.write_text(json.dumps(MOCK_SRL))
+    result = load_srl(str(srl_file))
+    for key in ("target_gpus", "watch_list", "uma_platforms", "vram_gating_logic"):
+        assert key in result
+
+
+def test_load_srl_raises_on_missing_file():
+    with pytest.raises(FileNotFoundError):
+        load_srl("/nonexistent/path/srl.json")
+
+
+# --- build_substitutions ---
+
+
+def test_build_substitutions_returns_all_four_keys():
+    result = build_substitutions(MOCK_SRL)
+    for key in ("TARGETS", "UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"):
+        assert key in result
+
+
+def test_target_gpu_list_contains_gpu_names():
+    result = build_substitutions(MOCK_SRL)
+    assert "RTX 3080" in result["TARGET_GPU_LIST"]
+    assert "RTX 4090" in result["TARGET_GPU_LIST"]
+
+
+def test_targets_includes_watch_list_names():
+    result = build_substitutions(MOCK_SRL)
+    assert "RTX 5090" in result["TARGETS"]
+    assert "GB200" in result["TARGETS"]
+
+
+def test_uma_min_ram_gb_is_string_of_value():
+    result = build_substitutions(MOCK_SRL)
+    assert result["UMA_MIN_RAM_GB"] == "64"
+
+
+def test_uma_chip_patterns_comma_separated():
+    result = build_substitutions(MOCK_SRL)
+    assert result["UMA_CHIP_PATTERNS"] == "M3 Max, M4 Ultra"
+
+
+# --- inject_file ---
+
+
+def test_inject_file_replaces_content_between_markers(tmp_path):
+    f = tmp_path / "prompt.txt"
+    f.write_text(
+        "before\n<!-- BEGIN_INJECT:TARGETS -->\nstale content\n<!-- END_INJECT:TARGETS -->\nafter\n",
+        encoding="utf-8",
+    )
+    count = inject_file(str(f), {"TARGETS": "fresh content"})
+    content = f.read_text(encoding="utf-8")
+    assert "fresh content" in content
+    assert "<!-- BEGIN_INJECT:TARGETS -->" in content
+    assert "<!-- END_INJECT:TARGETS -->" in content
+    assert "stale content" not in content
+    assert count == 1
+
+
+def test_inject_file_is_idempotent(tmp_path):
+    f = tmp_path / "prompt.txt"
+    f.write_text(
+        "<!-- BEGIN_INJECT:TARGETS -->\nold\n<!-- END_INJECT:TARGETS -->\n",
+        encoding="utf-8",
+    )
+    inject_file(str(f), {"TARGETS": "value"})
+    after_first = f.read_text(encoding="utf-8")
+    count2 = inject_file(str(f), {"TARGETS": "value"})
+    after_second = f.read_text(encoding="utf-8")
+    assert after_first == after_second
+    assert count2 >= 1
+
+
+def test_inject_file_no_markers_returns_zero(tmp_path):
+    f = tmp_path / "prompt.txt"
+    original = "no markers here\n"
+    f.write_text(original, encoding="utf-8")
+    count = inject_file(str(f), {"TARGETS": "value"})
+    assert count == 0
+    assert f.read_text(encoding="utf-8") == original
+
+
+def test_inject_file_raises_on_missing_file():
+    with pytest.raises(FileNotFoundError):
+        inject_file("/nonexistent/prompt.txt", {"TARGETS": "v"})
+
+
+def test_inject_file_replacement_count(tmp_path):
+    f = tmp_path / "prompt.txt"
+    f.write_text(
+        "<!-- BEGIN_INJECT:TARGETS -->\nold\n<!-- END_INJECT:TARGETS -->\n"
+        "<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->\nold\n<!-- END_INJECT:UMA_MIN_RAM_GB -->\n",
+        encoding="utf-8",
+    )
+    count = inject_file(str(f), {"TARGETS": "t", "UMA_MIN_RAM_GB": "64"})
+    assert count == 2
+
+
+# --- main integration ---
+
+
+def test_main_injects_all_three_prompt_files(tmp_path, monkeypatch):
+    srl = {
+        **MOCK_SRL,
+        "target_gpus": {"RTX 4090": {}},
+        "watch_list": [{"name": "RTX 5090"}],
+    }
+    srl_file = tmp_path / "srl.json"
+    srl_file.write_text(json.dumps(srl))
+
+    prompts = {}
+    for name in ("comet_discovery_agent.txt", "alternative_silicon_gemini.txt", "alternative_silicon_perplexity.txt"):
+        p = tmp_path / name
+        p.write_text(
+            "<!-- BEGIN_INJECT:TARGETS -->\nold\n<!-- END_INJECT:TARGETS -->\n"
+            "<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->\nold\n<!-- END_INJECT:UMA_MIN_RAM_GB -->\n",
+            encoding="utf-8",
+        )
+        prompts[name] = p
+
+    import inject_config
+
+    monkeypatch.setattr(inject_config, "SRL_PATH", str(srl_file))
+    monkeypatch.setattr(inject_config, "PROMPT_FILES", [str(p) for p in prompts.values()])
+
+    inject_config.main()
+
+    for p in prompts.values():
+        content = p.read_text(encoding="utf-8")
+        assert "<!-- BEGIN_INJECT:TARGETS -->" in content
+        assert "<!-- END_INJECT:TARGETS -->" in content
+        assert "RTX 4090" in content
diff --git a/tests/test_prompt_markers.py b/tests/test_prompt_markers.py
new file mode 100644
index 0000000..5ebc089
--- /dev/null
+++ b/tests/test_prompt_markers.py
@@ -0,0 +1,15 @@
+from pathlib import Path
+
+
+def test_prompt_files_have_sentinel_markers():
+    prompt_dir = Path(__file__).parent.parent / "prompts"
+    expected = {
+        "comet_discovery_agent.txt": ["TARGETS"],
+        "alternative_silicon_gemini.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
+        "alternative_silicon_perplexity.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
+    }
+    for filename, markers in expected.items():
+        content = (prompt_dir / filename).read_text()
+        for name in markers:
+            assert f"<!-- BEGIN_INJECT:{name} -->" in content, f"{filename} missing BEGIN_INJECT:{name}"
+            assert f"<!-- END_INJECT:{name} -->" in content, f"{filename} missing END_INJECT:{name}"
