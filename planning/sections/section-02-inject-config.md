Now I have all the context needed. Let me write the section content.

# Section 02: Config Injection (`scripts/inject_config.py`)

## Overview

This section covers the implementation of `scripts/inject_config.py` and its test suite `tests/test_inject_config.py`. The script keeps prompt files in sync with `config/static_reference_layer.json` (the SRL) via marker-based, idempotent substitution. It is invoked explicitly via `make inject-config` — it is not a dependency of any scrape target.

**Dependencies:** Section 01 (prerequisites) must be complete. The `scripts/` directory must exist. Sentinel marker pairs must already be present in the three target prompt files (one-time manual edit — see below).

---

## Background and Problem

`prompts/comet_discovery_agent.txt` currently contains a bare `[INJECT_TARGETS_HERE]` placeholder at line 8. This placeholder requires manual updates when `target_gpus` or `watch_list` changes in the SRL. The alternative silicon prompts (`prompts/alternative_silicon_gemini.txt`, `prompts/alternative_silicon_perplexity.txt`) are entirely disconnected from config.

A simple token-replace approach fails the idempotency requirement: run it twice and the second run has no marker to find. The solution is paired sentinel comments that survive each injection run. Content between the sentinels is replaced; the sentinels themselves remain.

---

## One-Time Manual Edit (Prerequisite)

Before the script can run, sentinel marker pairs must be added to the three target prompt files. This is a human/implementer task, not automated by the script.

**`prompts/comet_discovery_agent.txt`** — replace the existing `[INJECT_TARGETS_HERE]` line (currently line 8) with:

```
<!-- BEGIN_INJECT:TARGETS -->
<!-- END_INJECT:TARGETS -->
```

**`prompts/alternative_silicon_gemini.txt`** and **`prompts/alternative_silicon_perplexity.txt`** — add marker pairs at appropriate locations in each file:

```
<!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->
<!-- END_INJECT:UMA_MIN_RAM_GB -->

<!-- BEGIN_INJECT:UMA_CHIP_PATTERNS -->
<!-- END_INJECT:UMA_CHIP_PATTERNS -->

<!-- BEGIN_INJECT:TARGET_GPU_LIST -->
<!-- END_INJECT:TARGET_GPU_LIST -->
```

These sentinel pairs are committed to version control. The content between them is what `inject_config.py` manages.

---

## Sentinel Format

```
<!-- BEGIN_INJECT:TARGETS -->
...rendered content written here by inject_config.py...
<!-- END_INJECT:TARGETS -->
```

The four marker names used in v1:

| Marker Name | Content |
|---|---|
| `TARGETS` | Formatted block of target GPU names and watch-list GPUs |
| `UMA_MIN_RAM_GB` | Integer value of `uma_platforms.min_total_ram_gb_to_shortlist` |
| `UMA_CHIP_PATTERNS` | Comma-separated chip pattern list |
| `TARGET_GPU_LIST` | Same GPU list as TARGETS, usable in alt-silicon prompts |

---

## Config Source

Only `config/static_reference_layer.json` is loaded. Key SRL fields used:

- `target_gpus` — a **dict** where keys are GPU names (e.g. `"RTX 3080"`, `"RTX 4090"`). Currently contains: RTX 3080, RTX 3080 Ti, RTX 4080, RTX 4090, RTX 5070, RTX 5080, RTX A5000, and others.
- `watch_list` — a **list** of dicts, each with a `"name"` key (e.g. `{"name": "RTX 5090", ...}`). Currently contains: RTX 5090, RTX 5000 Ada Mobile, RTX PRO 5000 Blackwell Mobile, GB200, B200.
- `uma_platforms` — dict with `"min_total_ram_gb_to_shortlist": 32` and `"chip_patterns": ["M1 Max", "M1 Ultra", ..., "Strix Halo"]`.

`silicon_profiles.yaml` is **not** loaded in v1. No ecosystem maturity tokens are injected.

---

## File to Create

**`/Users/okgoogle13/Projects/laptopfinder/scripts/inject_config.py`**

### Function Signatures

```python
def load_srl(path: str) -> dict:
    """Load and return static_reference_layer.json as a dict.

    Raises FileNotFoundError if path does not exist.
    """

def build_substitutions(srl: dict) -> dict[str, str]:
    """Return mapping of marker name to rendered content string.

    Keys: "TARGETS", "UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"

    - TARGETS / TARGET_GPU_LIST: format target GPU names from srl["target_gpus"].keys()
      plus watch-list names from srl["watch_list"] (each entry["name"]).
    - UMA_MIN_RAM_GB: str(srl["uma_platforms"]["min_total_ram_gb_to_shortlist"])
    - UMA_CHIP_PATTERNS: ", ".join(srl["uma_platforms"]["chip_patterns"])

    No silicon_profiles.yaml in v1.
    """

def inject_file(path: str, substitutions: dict[str, str]) -> int:
    """Replace content between BEGIN_INJECT/END_INJECT marker pairs in a file.

    - Reads the file.
    - For each key in substitutions, replaces the block between
      <!-- BEGIN_INJECT:{key} --> and <!-- END_INJECT:{key} --> with the value.
    - Writes the file in-place.
    - Markers remain present in the output.
    - Idempotent: calling twice produces identical content.
    - Returns count of marker pairs successfully replaced.
    - Raises FileNotFoundError if path does not exist.
    """

def main() -> None:
    """Load SRL from config/static_reference_layer.json, build substitutions,
    inject into the three target prompt files:
      - prompts/comet_discovery_agent.txt
      - prompts/alternative_silicon_gemini.txt
      - prompts/alternative_silicon_perplexity.txt

    Prints one summary line per file: "<filename>: <n> block(s) replaced"
    """
```

### Implementation Notes

- Use `re.sub` with a pattern like `r'(<!-- BEGIN_INJECT:{key} -->).*?(<!-- END_INJECT:{key} -->)'` with `re.DOTALL` to replace the content between markers. The replacement string keeps both marker tags with the new content in between.
- Read/write files with UTF-8 encoding.
- The script resolves paths relative to the repo root. Use `pathlib.Path(__file__).parent.parent` to find the repo root from `scripts/inject_config.py`.
- No `argparse` needed in v1 — paths are hardcoded in `main()`.
- No `if __name__ == "__main__"` guard is strictly required but is conventional.

---

## Tests to Write First

**`/Users/okgoogle13/Projects/laptopfinder/tests/test_inject_config.py`**

Write these tests before implementing the script. All tests must be runnable with `.venv/bin/pytest tests/test_inject_config.py -v`.

### `load_srl` tests

```python
def test_load_srl_returns_expected_keys(tmp_path):
    """Write a minimal SRL JSON to tmp_path; assert load_srl returns dict
    containing keys: target_gpus, watch_list, uma_platforms, vram_gating_logic."""

def test_load_srl_raises_on_missing_file():
    """Assert load_srl raises FileNotFoundError for a non-existent path."""
```

### `build_substitutions` tests

Construct a mock SRL in each test — do not load the real SRL. Use a minimal structure:

```python
MOCK_SRL = {
    "target_gpus": {"RTX 3080": {}, "RTX 4090": {}},
    "watch_list": [{"name": "RTX 5090"}, {"name": "GB200"}],
    "uma_platforms": {
        "min_total_ram_gb_to_shortlist": 64,
        "chip_patterns": ["M3 Max", "M4 Ultra"]
    },
    "vram_gating_logic": {}
}
```

```python
def test_build_substitutions_returns_all_four_keys():
    """Assert result contains keys: TARGETS, UMA_MIN_RAM_GB, UMA_CHIP_PATTERNS, TARGET_GPU_LIST."""

def test_target_gpu_list_contains_gpu_names():
    """Assert "RTX 3080" and "RTX 4090" appear in TARGET_GPU_LIST value."""

def test_targets_includes_watch_list_names():
    """Assert "RTX 5090" and "GB200" appear in TARGETS value."""

def test_uma_min_ram_gb_is_string_of_value():
    """Assert UMA_MIN_RAM_GB == "64"."""

def test_uma_chip_patterns_comma_separated():
    """Assert UMA_CHIP_PATTERNS == "M3 Max, M4 Ultra"."""
```

### `inject_file` tests

```python
def test_inject_file_replaces_content_between_markers(tmp_path):
    """Write a file with:
      <!-- BEGIN_INJECT:TARGETS -->
      stale content
      <!-- END_INJECT:TARGETS -->
    Call inject_file with substitutions={"TARGETS": "fresh content"}.
    Assert the file now contains "fresh content" between the markers.
    Assert both marker lines are still present.
    Assert return value is 1."""

def test_inject_file_is_idempotent(tmp_path):
    """Call inject_file twice with same substitutions.
    Assert file content after second call == file content after first call.
    Assert both calls return non-zero replacement count."""

def test_inject_file_no_markers_returns_zero(tmp_path):
    """Write a file with no sentinel markers.
    Assert inject_file returns 0 and file content is unchanged."""

def test_inject_file_raises_on_missing_file():
    """Assert inject_file raises FileNotFoundError for a non-existent path."""

def test_inject_file_replacement_count(tmp_path):
    """Write a file with two different marker pairs (TARGETS and UMA_MIN_RAM_GB).
    Call inject_file with both in substitutions.
    Assert return value is 2."""
```

### `main` integration test

```python
def test_main_injects_all_three_prompt_files(tmp_path, monkeypatch):
    """Copy or create stub versions of all three prompt files in tmp_path,
    each containing at least one sentinel marker pair.
    Monkeypatch the script's resolved prompt paths to point to tmp_path copies.
    Call main().
    Assert all three files have updated content between their markers.
    Assert no marker lines were destroyed."""
```

### Prompt marker test (`tests/test_prompt_markers.py`)

```python
def test_prompt_files_have_sentinel_markers():
    """Read the three real prompts/*.txt files and assert every expected
    BEGIN_INJECT/END_INJECT sentinel pair is present.

    Fails loudly when a one-time manual prerequisite (section 01, step 5)
    has not been completed, before any scrape run can discover the gap."""
    prompt_dir = Path(__file__).parent.parent / "prompts"
    expected = {
        "comet_discovery_agent.txt": ["TARGETS"],
        "alternative_silicon_gemini.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
        "alternative_silicon_perplexity.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
    }
    for filename, markers in expected.items():
        content = (prompt_dir / filename).read_text()
        for name in markers:
            assert f"<!-- BEGIN_INJECT:{name} -->" in content
            assert f"<!-- END_INJECT:{name} -->" in content
```

---

## Makefile Target

This target belongs in the main `Makefile` (added in section 05, but noted here for reference):

```makefile
inject-config:
	.venv/bin/python scripts/inject_config.py
```

`scrape-and-live` does NOT depend on `inject-config`. Run separately when the SRL changes.

---

## Verification Steps

After implementation:

1. Run `make test` — all new and existing tests must pass.
2. Run `make inject-config` against the real prompt files.
3. Run `git diff prompts/` — verify that content between the sentinel marker pairs has been updated, and that the marker lines themselves are intact.
4. Run `make inject-config` a second time — `git diff` should show no new changes (idempotency confirmed).

---

## Implementation Notes

**Files created:**
- `scripts/inject_config.py` — 70 lines; `load_srl`, `build_substitutions`, `inject_file`, `main`
- `tests/test_inject_config.py` — 16 tests covering all four functions
- `tests/test_prompt_markers.py` — smoke test asserting sentinel markers exist in real prompt files

**Deviations from plan:**

- `TARGET_GPU_LIST` ≠ `TARGETS`: plan implied identical content for both tokens. After code review, `TARGET_GPU_LIST` (injected into alt-silicon prompts) contains only `target_gpus` keys. `TARGETS` (comet discovery) also includes `watch_list` names as awareness context. This prevents watch-list GPUs (MONITOR-routed) from leaking into alt-silicon prompts as discovery targets.
- `inject_file` write gated on `count > 0` (not in plan) — avoids unnecessary mtime changes for files with no matching markers.
- Partial marker corruption test added (`test_inject_file_partial_marker_returns_zero`) — not in original spec.
- 16 tests total (plan specified 13 + 1 integration = 14; added `test_target_gpu_list_excludes_watch_list_names` and `test_inject_file_partial_marker_returns_zero`).