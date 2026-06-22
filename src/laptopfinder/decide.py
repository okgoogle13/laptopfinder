"""laptopfinder downstream decision engine.

Applies static reference layer rules to validated Stage 2 analysis output
to produce actionable SHORTLIST / MONITOR / SKIP recommendations.
"""

import json
import re
from pathlib import Path
from typing import Any

_DEFAULT_REF_LAYER_PATH = Path(__file__).resolve().parents[2] / "config" / "static_reference_layer.json"


def load_reference_layer(path: str | Path | None = None) -> dict[str, Any]:
    """Load the static reference layer JSON."""
    p = Path(path) if path else _DEFAULT_REF_LAYER_PATH
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_vram_gb(vram_str: str | None) -> float | None:
    """Extract numeric GB value from a VRAM string like '16GB GDDR6' or '24GB'.

    Returns None if unparseable.
    """
    if not vram_str:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", vram_str, re.IGNORECASE)
    return float(m.group(1)) if m else None


def classify_capability_band(vram_gb: float | None, ref: dict[str, Any]) -> str | None:
    """Match a VRAM amount to a capability band from the reference layer."""
    if vram_gb is None:
        return None
    for band_name, band_def in ref["capability_bands"].items():
        lo, hi = band_def["vram_range_gb"]
        if lo <= vram_gb <= hi:
            return band_name
    return None


def check_unicorn(model: str | None, gpu: str | None, ref: dict[str, Any]) -> bool:
    """Check if the hardware matches the unicorn dictionary."""
    if gpu and gpu in ref.get("unicorn_gpus", {}):
        return True
    if model:
        model_lower = model.lower()
        for pattern in ref.get("unicorn_models", []):
            if pattern.lower() in model_lower:
                return True
    return False


def check_monitor_list(gpu: str | None, ref: dict[str, Any]) -> bool:
    """Check if the GPU is on the aspirational monitor-only list."""
    if not gpu:
        return False
    gpu_upper = gpu.upper()
    return any(m.upper() in gpu_upper for m in ref.get("aspirational_monitor_list", []))


def check_low_risk_gate(analysis: dict[str, Any], ref: dict[str, Any]) -> bool:
    """Evaluate the low-risk safety gate."""
    gate = ref.get("override_rules", {}).get("low_risk_gate", {})
    max_risk = gate.get("max_risk_score", 3.0)
    max_missing = gate.get("max_missing_core_fields", 1)

    risk_score = analysis.get("analysis", {}).get("risk_score", 10.0)
    missing_count = len(analysis.get("extracted_data", {}).get("missing_information", []))

    return risk_score <= max_risk and missing_count <= max_missing


def decide(analysis: dict[str, Any], ref: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply reference layer rules to a validated Stage 2 analysis.

    Args:
        analysis: Validated Stage 2 analysis output dict.
        ref: Static reference layer dict. Loaded from default path if None.

    Returns:
        Decision dict with recommended_action and reasoning.
    """
    if ref is None:
        ref = load_reference_layer()

    extracted = analysis.get("extracted_data", {})
    gpu = extracted.get("gpu")
    model = extracted.get("exact_model_name")
    vram_str = extracted.get("vram_capacity")

    vram_gb = _parse_vram_gb(vram_str)
    band = classify_capability_band(vram_gb, ref)
    is_unicorn = check_unicorn(model, gpu, ref)
    is_monitor = check_monitor_list(gpu, ref)
    low_risk = check_low_risk_gate(analysis, ref)

    # A category jump means the listing appears to offer a higher capability
    # band than its pricing tier implies. Simplified heuristic: any band
    # above ENTRY_LOCAL_LLM qualifies as a potential jump.
    category_jump = band in {"STRONG_8B_14B", "POSSIBLE_70B_QUANTIZED"}

    # Exceptional distance override: (category_jump OR unicorn) AND low_risk
    override = (category_jump or is_unicorn) and low_risk

    # Build decision
    reasons: list[str] = []

    if is_monitor:
        action = "MONITOR"
        reasons.append(f"GPU '{gpu}' is on the aspirational monitor list")
    elif not low_risk:
        action = "SKIP"
        risk_score = analysis.get("analysis", {}).get("risk_score", "?")
        missing = extracted.get("missing_information", [])
        reasons.append(f"Failed low-risk gate (risk_score={risk_score}, missing_fields={len(missing)})")
    elif is_unicorn or band in {"STRONG_8B_14B", "POSSIBLE_70B_QUANTIZED", "MID_TIER_LOCAL_LLM"}:
        action = "SHORTLIST"
        if is_unicorn:
            reasons.append("Matches unicorn hardware dictionary")
        if band:
            reasons.append(f"Capability band: {band}")
    elif band == "ENTRY_LOCAL_LLM":
        action = "SHORTLIST"
        reasons.append(f"Capability band: {band}")
    else:
        action = "SKIP"
        reasons.append("No VRAM data or below minimum capability band")

    if override:
        reasons.append("Exceptional distance override: ELIGIBLE")

    return {
        "capability_band": band,
        "vram_gb": vram_gb,
        "is_unicorn": is_unicorn,
        "is_monitor_only": is_monitor,
        "low_risk_gate_passed": low_risk,
        "exceptional_distance_override": override,
        "recommended_action": action,
        "decision_reasons": reasons,
    }
