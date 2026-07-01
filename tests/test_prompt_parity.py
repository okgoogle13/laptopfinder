import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
SRL_PATH = _REPO_ROOT / "config" / "static_reference_layer.json"
AUDIT_PROMPT_PATH = _REPO_ROOT / "prompts" / "claude_code_audit.txt"
CLAUDE_MD_PATH = _REPO_ROOT / "CLAUDE.md"


def load_srl() -> dict:
    if not SRL_PATH.exists():
        raise FileNotFoundError(f"SRL not found: {SRL_PATH}")
    return json.loads(SRL_PATH.read_text(encoding="utf-8"))


def test_audit_prompt_threshold_parity():
    """Verify that the thresholds hardcoded in prompts/claude_code_audit.txt match config."""
    srl = load_srl()
    gating = srl.get("vram_gating_logic", {})
    
    std_vram = gating.get("standard_mobile_min_gb")
    touch_vram = gating.get("touchscreen_exception_min_gb")
    uma_ram = gating.get("uma_unified_min_gb")
    
    assert std_vram is not None
    assert touch_vram is not None
    assert uma_ram is not None

    audit_text = AUDIT_PROMPT_PATH.read_text(encoding="utf-8")

    # Parse Rule 4.c: is_uma_platform ... uma_ram_gb >= \d+
    uma_match = re.search(r"uma_ram_gb\s*>=\s*(\d+)", audit_text)
    assert uma_match, "Could not find UMA RAM rule in prompts/claude_code_audit.txt"
    assert int(uma_match.group(1)) == uma_ram, f"Audit prompt UMA RAM threshold ({uma_match.group(1)}) does not match SRL ({uma_ram})"

    # Parse Rule 4.d: vram_gb >= \d+
    vram_match = re.search(r"vram_gb\s*>=\s*(\d+)", audit_text)
    assert vram_match, "Could not find standard VRAM rule in prompts/claude_code_audit.txt"
    assert int(vram_match.group(1)) == std_vram, f"Audit prompt standard VRAM threshold ({vram_match.group(1)}) does not match SRL ({std_vram})"

    # Parse Rule 4.e: vram_gb >= \d+ and touchscreen_digitizer
    touch_match = re.search(r"vram_gb\s*>=\s*(\d+)\s+and\s+touchscreen_digitizer", audit_text)
    assert touch_match, "Could not find touchscreen exception VRAM rule in prompts/claude_code_audit.txt"
    assert int(touch_match.group(1)) == touch_vram, f"Audit prompt touchscreen VRAM threshold ({touch_match.group(1)}) does not match SRL ({touch_vram})"


def test_claude_md_threshold_parity():
    """Verify that thresholds documented in CLAUDE.md match config."""
    srl = load_srl()
    gating = srl.get("vram_gating_logic", {})
    
    std_vram = gating.get("standard_mobile_min_gb")
    touch_vram = gating.get("touchscreen_exception_min_gb")
    uma_ram = gating.get("uma_unified_min_gb")

    claude_text = CLAUDE_MD_PATH.read_text(encoding="utf-8")

    # Parse Rule 3: UMA platform ... system RAM ≥ \d+GB
    uma_match = re.search(r"system RAM\s*[≥>=]\s*(\d+)GB", claude_text)
    assert uma_match, "Could not find UMA RAM rule in CLAUDE.md"
    assert int(uma_match.group(1)) == uma_ram, f"CLAUDE.md UMA RAM threshold ({uma_match.group(1)}) does not match SRL ({uma_ram})"

    # Parse Rule 4 (Standard VRAM): VRAM ≥ \d+GB
    std_match = re.search(r"VRAM\s*[≥>=]\s*(\d+)GB\s*,", claude_text)
    assert std_match, "Could not find standard VRAM rule in CLAUDE.md"
    assert int(std_match.group(1)) == std_vram, f"CLAUDE.md standard VRAM threshold ({std_match.group(1)}) does not match SRL ({std_vram})"

    # Parse Rule 4 (Touchscreen VRAM): VRAM ≥ \d+GB + `touchscreen_digitizer`
    touch_match = re.search(r"VRAM\s*[≥>=]\s*(\d+)GB\s*\+\s*`touchscreen_digitizer`", claude_text)
    assert touch_match, "Could not find touchscreen VRAM rule in CLAUDE.md"
    assert int(touch_match.group(1)) == touch_vram, f"CLAUDE.md touchscreen VRAM threshold ({touch_match.group(1)}) does not match SRL ({touch_vram})"
