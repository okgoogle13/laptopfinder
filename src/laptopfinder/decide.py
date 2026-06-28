"""laptopfinder decision engine.

Reads a validated Stage 2 analysis and returns SHORTLIST / MONITOR / SKIP.
"""

import json
import re
from pathlib import Path
from typing import Any

_REF_PATH = Path(__file__).resolve().parents[2] / "config" / "static_reference_layer.json"


def load_ref(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else _REF_PATH
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _vram_gb(vram_val: "str | dict | None") -> float | None:
    """Extract VRAM capacity in GB from a vram_capacity field.

    Accepts the new discriminated-object schema {"semantic_value": 16.0, ...}
    or a legacy flat string '16GB GDDR6' (for backward compat with old fixtures).
    Returns None if the value is absent or unparseable.
    """
    if not vram_val:
        return None
    # New schema: {"semantic_value": <number>, "verbatim_quote": <str>}
    if isinstance(vram_val, dict):
        val = vram_val.get("semantic_value")
        return float(val) if val is not None else None
    # Legacy string fallback (e.g. '16GB GDDR6')
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", str(vram_val), re.IGNORECASE)
    return float(m.group(1)) if m else None


def _vram_tier(vram_gb: float | None, ref: dict) -> str | None:
    """Map a VRAM amount to a tier name (entry / mid / high / extreme)."""
    if vram_gb is None:
        return None
    for name, tier in ref["vram_tiers"].items():
        if tier["min_gb"] <= vram_gb <= tier["max_gb"]:
            return name
    return None


def _is_target(model: str | None, gpu: str | None, ref: dict) -> bool:
    """True if the GPU or model name matches our target lists."""
    if gpu and gpu in ref.get("target_gpus", {}):
        return True
    if model:
        model_lower = model.lower()
        for pattern in ref.get("target_models", []):
            if pattern.lower() in model_lower:
                return True
    return False


def _is_watch(gpu: str | None, ref: dict) -> bool:
    """True if the GPU is on the watch list (too new, just monitor).

    watch_list entries may be plain strings (legacy) or dicts with a "name" key.
    """
    if not gpu:
        return False
    gpu_upper = gpu.upper()
    for w in ref.get("watch_list", []):
        name = w.get("name") if isinstance(w, dict) else w
        if name and name.upper() in gpu_upper:
            return True
    return False


def _ram_gb(ram_str: str | None) -> float | None:
    """Parse '128GB' / '128GB LPDDR5' → 128.0. Returns None if unparseable."""
    if not ram_str:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", ram_str, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _is_uma_platform(model: str | None, cpu: str | None, ref: dict) -> bool:
    """True if the model/cpu name matches a unified-memory chip (Apple Silicon Max/Ultra, Strix Halo).

    UMA platforms have no discrete VRAM — total_system_ram is the relevant capacity signal instead.
    """
    cfg = ref.get("uma_platforms", {})
    haystack = " ".join(filter(None, [model, cpu])).lower()
    if not haystack:
        return False
    return any(pattern.lower() in haystack for pattern in cfg.get("chip_patterns", []))


def _is_radeon_mobile(gpu: str | None, ref: dict) -> str | None:
    """Return the matching Radeon mobile/workstation GPU name if gpu is on the list, else None."""
    if not gpu:
        return None
    for name in ref.get("radeon_mobile_gpus", {}):
        if name.lower() in gpu.lower():
            return name
    return None


def _has_egpu_bundle(model: str | None, egpu_model: str | None, ref: dict) -> bool:
    """True if the listing explicitly states a bundled eGPU enclosure.

    When true, the base laptop's weak internal GPU should not trigger a rejection —
    the eGPU's own VRAM (parsed from vram_capacity, same as any discrete GPU) governs the decision.
    """
    haystack = " ".join(filter(None, [model, egpu_model])).lower()
    if not haystack:
        return False
    return any(enclosure.lower() in haystack for enclosure in ref.get("egpu_enclosures", []))


def _passes_risk_gate(analysis: dict, ref: dict, risk_penalty: float = 0.0) -> bool:
    """True if risk score (plus any ecosystem penalty) and missing fields are within limits."""
    cfg = ref.get("shortlist_override", {})
    max_risk = cfg.get("requires_risk_score_max", 3.0)
    max_missing = cfg.get("requires_missing_fields_max", 1)

    risk_score = analysis.get("analysis", {}).get("risk_score", 10.0) + risk_penalty
    mi = analysis.get("extracted_data", {}).get("missing_information", {})
    missing = sum(mi.values()) if isinstance(mi, dict) else len(mi)

    return risk_score <= max_risk and missing <= max_missing


def _capacity_points(tier: str | None, ref: dict) -> int:
    """Points for VRAM tier (or UMA RAM tier, using the same tier names). Max 60."""
    cfg = ref.get("llm_index_score", {}).get("capacity_points_by_tier", {})
    return cfg.get(tier, 0) if tier else 0


def _gpu_generation_points(gpu: str | None, is_uma: bool, ref: dict) -> int:
    """Points for GPU architecture generation. Max 25.

    UMA platforms (Apple Silicon, Strix Halo) score under "Apple Silicon" /
    treated as top-tier for inference since they're not on the discrete-GPU
    generational ladder. Unrecognized GPUs score 0, not a penalty.
    """
    cfg = ref.get("llm_index_score", {})
    points_by_gen = cfg.get("gpu_generation_points", {})
    if is_uma:
        return points_by_gen.get("Apple Silicon", 0)
    if not gpu:
        return 0
    gen_by_name = cfg.get("gpu_generation_by_name", {})
    for name, generation in gen_by_name.items():
        if name.lower() in gpu.lower():
            return points_by_gen.get(generation, 0)
    return 0


def _seller_reward_points(analysis: dict, ref: dict) -> int:
    """Seller risk/reward modifier: classification points + platform modifier. Range roughly -20 to +20."""
    cfg = ref.get("llm_index_score", {})
    classification = analysis.get("analysis", {}).get("seller_classification")
    platform = analysis.get("metadata", {}).get("source_platform")

    classification_points = cfg.get("seller_classification_points", {}).get(classification, 0)
    platform_points = cfg.get("platform_modifier_points", {}).get(platform, 0)
    
    # Check for overseas import flag
    overseas_penalty = 0
    ships_from_overseas = analysis.get("metadata", {}).get("ships_from_overseas", False)
    if ships_from_overseas:
        overseas_penalty = cfg.get("platform_modifier_points", {}).get("OVERSEAS_IMPORT", -10)

    return classification_points + platform_points + overseas_penalty


def _deduction_points(analysis: dict, ref: dict) -> int:
    """Deductions for missing fields and risk score. Uncapped downside — a sufficiently
    risky/incomplete listing can drive the overall score negative."""
    cfg = ref.get("llm_index_score", {})
    mi = analysis.get("extracted_data", {}).get("missing_information", {})
    n_missing = sum(mi.values()) if isinstance(mi, dict) else len(mi)
    risk_score = analysis.get("analysis", {}).get("risk_score", 0.0)

    missing_deduction = n_missing * cfg.get("deduction_per_missing_field", 0)
    risk_deduction = risk_score * cfg.get("deduction_per_risk_point", 0)
    return round(missing_deduction + risk_deduction)


def calculate_llm_index_score(
    analysis: dict,
    tier: str | None,
    gpu: str | None,
    is_uma: bool,
    ref: dict,
) -> int:
    """Local_LLM_Index_Score (0-100): capacity (60) + GPU generation (25) + seller
    risk/reward (~±20) + target hint bonuses (+5 GPU, +3 model) − deductions (uncapped).

    target_gpus/target_models membership adds a small bonus but never gates routing.
    UMA platforms are capped at apple_silicon.score_ceiling (default 75).
    Clamped to [0, 100] after all adjustments.
    """
    capacity = _capacity_points(tier, ref)
    generation = _gpu_generation_points(gpu, is_uma, ref)
    seller = _seller_reward_points(analysis, ref)
    deductions = _deduction_points(analysis, ref)

    raw = capacity + generation + seller - deductions

    # Target scoring hints — informational bonuses, not routing gates.
    extracted = analysis.get("extracted_data", {})
    gpu_name = extracted.get("gpu")
    model_name = extracted.get("exact_model_name")

    if gpu_name and gpu_name in ref.get("target_gpus", {}):
        raw += 5
    if model_name:
        model_lower = model_name.lower()
        for pattern in ref.get("target_models", []):
            if pattern.lower() in model_lower:
                raw += 3
                break

    score = max(0, min(100, raw))

    # UMA score ceiling — reflects UMA bandwidth constraints vs discrete VRAM.
    if is_uma:
        ceiling = ref.get("apple_silicon", {}).get("score_ceiling")
        if ceiling is not None:
            score = min(score, ceiling)

    return score


def decide(analysis: dict, ref: dict | None = None) -> dict:
    """Return a decision dict for a validated Stage 2 analysis."""
    if ref is None:
        ref = load_ref()

    extracted = analysis.get("extracted_data", {})
    gpu = extracted.get("gpu")
    cpu = extracted.get("cpu")
    model = extracted.get("exact_model_name")
    vram_str = extracted.get("vram_capacity")
    ram_str = extracted.get("total_system_ram")
    egpu_model = extracted.get("egpu_model")
    touchscreen_digitizer = extracted.get("touchscreen_digitizer")

    vram = _vram_gb(vram_str)
    tier = _vram_tier(vram, ref)
    is_target = _is_target(model, gpu, ref)
    is_watch = _is_watch(gpu, ref)

    is_uma = _is_uma_platform(model, cpu, ref)
    uma_ram = _ram_gb(ram_str) if is_uma else None
    uma_tier = _vram_tier(uma_ram, ref) if is_uma else None
    radeon_match = _is_radeon_mobile(gpu, ref)
    has_egpu = _has_egpu_bundle(model, egpu_model, ref)

    capacity_tier = uma_tier if is_uma else tier
    llm_index_score = calculate_llm_index_score(analysis, capacity_tier, gpu, is_uma, ref)

    # Radeon ecosystem risk is surfaced as a buyer disclosure note, not added to risk_score.
    low_risk = _passes_risk_gate(analysis, ref, 0.0)

    gating = ref.get("vram_gating_logic", {})
    min_vram = gating.get("standard_mobile_min_gb", 16)
    min_uma_ram = gating.get("uma_unified_min_gb", 64)
    min_touchscreen_vram = gating.get("touchscreen_exception_min_gb", 12)
    reasons: list[str] = []

    # eGPU bundle: the base laptop's own (possibly weak) GPU is irrelevant. The bundled
    # eGPU's VRAM (already parsed into `vram` from vram_capacity) is what's evaluated.
    if has_egpu:
        reasons.append(f"eGPU bundle detected ('{egpu_model}') — internal GPU ignored")

    # Touchscreen exception: relaxed threshold (12GB) if touchscreen feature is detected
    has_touchscreen_exception = (
        vram is not None 
        and vram >= min_touchscreen_vram 
        and touchscreen_digitizer is not None
    )

    if is_watch:
        action = "MONITOR"
        reasons.append(f"'{gpu}' is on the watch list — too new, check back later")
    elif not low_risk:
        action = "SKIP"
        risk = analysis.get("analysis", {}).get("risk_score", "?")
        mi = extracted.get("missing_information", {})
        n_missing = sum(mi.values()) if isinstance(mi, dict) else len(mi)
        reasons.append(f"Too risky to shortlist (risk={risk}, missing fields={n_missing})")
    elif is_uma and uma_ram is not None and uma_ram >= min_uma_ram:
        action = "SHORTLIST"
        reasons.append(f"UMA platform, system RAM {uma_ram}GB >= {min_uma_ram}GB threshold")
    elif has_egpu or (vram is not None and vram >= min_vram) or has_touchscreen_exception:
        action = "SHORTLIST"
        if has_touchscreen_exception:
            reasons.append(f"VRAM touchscreen exception: {vram}GB with touchscreen ('{touchscreen_digitizer}')")
        if is_target:
            reasons.append("Matches target GPU or model list (scoring hint)")
        if radeon_match:
            reasons.append(f"Radeon mobile GPU '{radeon_match}' — passes risk gate; see radeon_ecosystem_disclosure for buyer notes")
        if tier and not has_touchscreen_exception:
            reasons.append(f"VRAM tier: {tier} ({vram}GB)")
    elif is_uma:
        action = "SKIP"
        reasons.append(f"UMA platform but system RAM too low or unknown (got {uma_ram}GB, need {min_uma_ram}GB+)")
    else:
        action = "SKIP"
        if vram is not None and vram >= min_touchscreen_vram and touchscreen_digitizer is None:
            reasons.append(f"VRAM is {vram}GB, which requires touchscreen exception support but touchscreen_digitizer is null")
        else:
            reasons.append(f"VRAM too low or unknown (got {vram}GB, need {min_vram}GB+)")

    return {
        "vram_gb": vram,
        "vram_tier": tier,
        "is_target": is_target,
        "is_watch_only": is_watch,
        "risk_gate_passed": low_risk,
        "recommended_action": action,
        "reasons": reasons,
        "is_uma_platform": is_uma,
        "uma_ram_gb": uma_ram,
        "is_radeon_mobile": radeon_match,
        "has_egpu_bundle": has_egpu,
        "llm_index_score": llm_index_score,
    }
