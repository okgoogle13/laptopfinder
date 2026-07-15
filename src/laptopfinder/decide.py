"""laptopfinder decision engine.

Reads a validated Stage 2 analysis and returns SHORTLIST / MONITOR / SKIP.
"""

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml

Paradigm = Literal["apple_silicon_uma", "amd_uma", "discrete_cuda", "discrete_rocm"]

_SCORING_WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "config" / "scoring_weights.yaml"

_REF_PATH = Path(__file__).resolve().parents[2] / "config" / "static_reference_layer.json"
_UNDISCOVERED_HARDWARE_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "evidence" / "undiscovered_hardware.jsonl"


def load_ref(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else _REF_PATH
    with p.open("r", encoding="utf-8") as f:
        ref = json.load(f)
    _precompute_ref(ref)
    return ref


def _precompute_ref(ref: dict) -> None:
    """Mutate ref in-place to add pre-lowercased lookup structures.

    Avoids repeated .lower() calls inside hot loops in decide().
    Added keys are prefixed with '_' to distinguish from source data.
    """
    uma = ref.get("uma_platforms", {})
    ref["_chip_patterns_lower"] = [p.lower() for p in uma.get("chip_patterns", [])]
    ref["_amd_chip_patterns_lower"] = [p.lower() for p in uma.get("amd_chip_patterns", [])]

    ref["_watch_names_upper"] = [
        (w.get("name") if isinstance(w, dict) else w).upper()
        for w in ref.get("watch_list", [])
        if (w.get("name") if isinstance(w, dict) else w)
    ]

    ref["_radeon_names_lower"] = [n.lower() for n in ref.get("radeon_mobile_gpus", {})]

    ref["_egpu_enclosures_lower"] = [e.lower() for e in ref.get("egpu_enclosures", [])]

    score_cfg = ref.get("llm_index_score", {})
    ref["_gen_by_name_lower"] = {
        name.lower(): gen
        for name, gen in score_cfg.get("gpu_generation_by_name", {}).items()
    }

    ref["_uma_soc_by_name_lower"] = {
        name.lower(): tier
        for name, tier in ref.get("uma_soc_by_name", {}).items()
    }

    ref["_target_models_lower"] = [m.lower() for m in ref.get("target_models", [])]


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
        patterns = ref.get("_target_models_lower") or [m.lower() for m in ref.get("target_models", [])]
        return any(pattern in model_lower for pattern in patterns)
    return False


def _is_watch(gpu: str | None, ref: dict) -> bool:
    """True if the GPU is on the watch list (too new, just monitor).

    watch_list entries may be plain strings (legacy) or dicts with a "name" key.
    """
    if not gpu:
        return False
    gpu_upper = gpu.upper()
    watch_names = ref.get("_watch_names_upper") or [
        (w.get("name") if isinstance(w, dict) else w).upper()
        for w in ref.get("watch_list", [])
        if (w.get("name") if isinstance(w, dict) else w)
    ]
    return any(name in gpu_upper for name in watch_names)


def _ram_gb(ram_val: "str | dict | None") -> float | None:
    """Parse RAM capacity in GB.
    
    Accepts the new discriminated-object schema {"semantic_value": 128.0, ...}
    or a legacy flat string '128GB LPDDR5'. Returns None if unparseable.
    """
    if not ram_val:
        return None
    if isinstance(ram_val, dict):
        val = ram_val.get("semantic_value")
        return float(val) if val is not None else None
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", str(ram_val), re.IGNORECASE)
    return float(m.group(1)) if m else None


def _is_uma_platform(model: str | None, cpu: str | None, ref: dict) -> bool:
    """True if the model/cpu name matches a unified-memory chip (Apple Silicon Max/Ultra, Strix Halo).

    UMA platforms have no discrete VRAM — total_system_ram is the relevant capacity signal instead.
    """
    haystack = " ".join(filter(None, [model, cpu])).lower()
    if not haystack:
        return False
    patterns = ref.get("_chip_patterns_lower") or [
        p.lower() for p in ref.get("uma_platforms", {}).get("chip_patterns", [])
    ]
    return any(pattern in haystack for pattern in patterns)


def _is_radeon_mobile(gpu: str | None, ref: dict) -> str | None:
    """Return the matching Radeon mobile/workstation GPU name if gpu is on the list, else None."""
    if not gpu:
        return None
    gpu_lower = gpu.lower()
    names = list(ref.get("radeon_mobile_gpus", {}))
    names_lower = ref.get("_radeon_names_lower", [])
    for orig, lower in zip(names, names_lower):
        if lower in gpu_lower:
            return orig
    return None


def _has_egpu_bundle(model: str | None, egpu_model: str | None, ref: dict) -> bool:
    """True if the listing explicitly states a bundled eGPU enclosure.

    When true, the base laptop's weak internal GPU should not trigger a rejection —
    the eGPU's own VRAM (parsed from vram_capacity, same as any discrete GPU) governs the decision.
    """
    haystack = " ".join(filter(None, [model, egpu_model])).lower()
    if not haystack:
        return False
    enclosures = ref.get("_egpu_enclosures_lower", [])
    return any(enclosure in haystack for enclosure in enclosures)


def _classify_paradigm(analysis: dict, ref: dict, is_uma: bool | None = None, radeon_match: str | None = ...) -> Paradigm:  # type: ignore[assignment]
    extracted = analysis.get("extracted_data") or {}
    gpu = extracted.get("gpu") or ""
    model = extracted.get("exact_model_name") or ""
    cpu = extracted.get("cpu") or ""
    if is_uma is None:
        is_uma = _is_uma_platform(model, cpu, ref)
    if is_uma:
        haystack = " ".join(filter(None, [model, cpu])).lower()
        if any(kw in haystack for kw in ref.get("_amd_chip_patterns_lower", [])):
            return "amd_uma"
        return "apple_silicon_uma"
    if radeon_match is ...:
        radeon_match = _is_radeon_mobile(gpu, ref)
    if radeon_match:
        return "discrete_rocm"
    return "discrete_cuda"


def load_scoring_weights(profile: str = "text_llm_default") -> dict:
    with _SCORING_WEIGHTS_PATH.open() as f:
        return yaml.safe_load(f)["profiles"][profile]


def score_text_llm_candidate(candidate: dict, weights: dict) -> float:
    """Score a hardware_taxonomy.json entry for text-centric LLM inference.

    candidate keys: paradigm, bandwidth_gbps, ram_gb
    weights: loaded from scoring_weights.yaml profile
    """
    bw_score = min(candidate["bandwidth_gbps"] / weights.get("bw_baseline_gbps", 400.0), 1.0)
    ram_score = min(candidate["ram_gb"] / weights.get("ram_baseline_gb", 128.0), 1.0)
    paradigm = candidate["paradigm"]
    ecosystem = weights["paradigm_ecosystem_scores"][paradigm]
    thermals = weights["paradigm_thermals_scores"][paradigm]
    penalty = weights.get("discrete_text_llm_penalty", 1.0)
    raw = (
        bw_score * weights["memory_bandwidth_weight"]
        + ram_score * weights["total_memory_capacity_weight"]
        + ecosystem * weights["software_ecosystem_weight"]
        + thermals * weights["thermals_noise_power_weight"]
    ) * 100.0
    if paradigm in ("discrete_cuda", "discrete_rocm"):
        raw *= penalty
    return round(raw, 2)


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


def _resolve_gpu_generation(gpu: str | None, ref: dict) -> str | None:
    """Return the matched GPU's architecture generation name (e.g. 'Turing', 'Ada Lovelace'),
    or None if gpu is absent or unrecognized. Case-insensitive substring match against
    llm_index_score.gpu_generation_by_name."""
    if not gpu:
        return None
    gpu_lower = gpu.lower()
    gen_by_name_lower = ref.get("_gen_by_name_lower", {})
    for name_lower, generation in gen_by_name_lower.items():
        if name_lower in gpu_lower:
            return generation
    return None


def _gpu_generation_points(gpu: str | None, is_uma: bool, ref: dict) -> int:
    """Points for GPU architecture generation. Max 25.

    UMA platforms (Apple Silicon, Strix Halo) score under "UMA_Architecture" /
    treated as top-tier for inference since they're not on the discrete-GPU
    generational ladder. Unrecognized GPUs score 0, not a penalty.
    """
    cfg = ref.get("llm_index_score", {})
    points_by_gen = cfg.get("gpu_generation_points", {})
    if is_uma:
        return points_by_gen.get("UMA_Architecture", 0)
    generation = _resolve_gpu_generation(gpu, ref)
    if generation is None:
        return 0
    return points_by_gen.get(generation, 0)


def _uma_soc_points(cpu: str | None, model: str | None, ref: dict) -> int:
    """Points for UMA SoC bandwidth tier.
    
    If the SoC is not in uma_soc_by_name, falls back to the flat UMA_Architecture value.
    """
    haystack = " ".join(filter(None, [model, cpu])).lower()
    if not haystack:
        return ref.get("llm_index_score", {}).get("gpu_generation_points", {}).get("UMA_Architecture", 0)
        
    uma_soc_by_name_lower = ref.get("_uma_soc_by_name_lower", {})
    
    matched_tier = None
    for name_lower, tier in uma_soc_by_name_lower.items():
        if name_lower in haystack:
            matched_tier = tier
            break
            
    if matched_tier is not None:
        return ref.get("uma_soc_bandwidth_points", {}).get(matched_tier, 0)
        
    # Mandatory fallback
    return ref.get("llm_index_score", {}).get("gpu_generation_points", {}).get("UMA_Architecture", 0)


def _log_undiscovered_hardware(
    analysis: dict,
    gpu: str | None,
    vram_gb: float | None,
    system_ram_gb: float | None,
    generation_points: int,
    is_target: bool,
    is_uma: bool,
    is_radeon_mobile: bool,
) -> None:
    if generation_points != 0:
        return
    if is_target or is_uma or is_radeon_mobile:
        return
    if (vram_gb is None or vram_gb < 12) and (system_ram_gb is None or system_ram_gb < 64):
        return

    metadata = analysis.get("metadata", {})
    record = {
        "title": metadata.get("listing_title"),
        "price_aud": metadata.get("listing_price_aud"),
        "gpu_string": gpu,
        "vram_gb": vram_gb,
        "system_ram_gb": system_ram_gb,
        "listing_url_or_identifier": metadata.get("listing_url_or_identifier"),
    }

    try:
        _UNDISCOVERED_HARDWARE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _UNDISCOVERED_HARDWARE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        print(f"[UNKNOWN_HIGH_CAPACITY_TARGET] queued {record['gpu_string'] or record['title']}")
    except OSError as exc:
        print(f"[UNKNOWN_HIGH_CAPACITY_TARGET] failed to queue diagnostic: {exc}")


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


def _apply_architecture_penalty(gpu: str | None, tier: str | None, ref: dict) -> int:
    """Single-listing heuristic — cannot resolve Turing vs Ada for a same-VRAM pairwise
    comparison in the per-listing scoring path (decide() scores one listing at a time).
    Turing is identified via the same llm_index_score.gpu_generation_by_name lookup
    _gpu_generation_points uses (not config/silicon_profiles.yaml — decide.py does not
    load that file at runtime; see CLAUDE.md Architecture: Silicon Profiles). If the GPU
    resolves to Turing and a VRAM tier is present, apply the SRL's
    turing_vs_ada_same_vram_penalty_pts. Otherwise 0.
    """
    if tier is None:
        return 0
    if _resolve_gpu_generation(gpu, ref) != "Turing":
        return 0
    return ref.get("architecture_adjustments", {}).get("turing_vs_ada_same_vram_penalty_pts", 0)


def _apply_egpu_interconnect_penalty(analysis: dict, ref: dict) -> int:
    """Return TB3/4 interconnect penalty for eGPU bundles; 0 otherwise.

    Interconnect type is inferred from egpu_model keywords (no schema field exists).
    zero_penalty_condition: system_ram_gb >= 32 waives penalty regardless of interconnect.
    """
    extracted = analysis.get("extracted_data", {})
    model = extracted.get("exact_model_name")
    egpu_model = extracted.get("egpu_model")
    if not _has_egpu_bundle(model, egpu_model, ref):
        return 0
    system_ram = extracted.get("total_system_ram")
    if system_ram is not None and system_ram >= 32:
        return 0
    cfg = ref.get("egpu_interconnect_penalty", {})
    egpu_lower = (egpu_model or "").lower()
    oculink_enclosures = [e.lower() for e in cfg.get("oculink_enclosures", [])]
    is_oculink = "oculink" in egpu_lower or any(enc in egpu_lower for enc in oculink_enclosures)
    if is_oculink:
        return cfg.get("oculink_pts", 0)
    if "thunderbolt 5" in egpu_lower or "tb5" in egpu_lower:
        return cfg.get("thunderbolt_5_pts", 0)
    return cfg.get("thunderbolt_3_4_pts", -3)


def calculate_llm_index_score(
    analysis: dict,
    tier: str | None,
    gpu: str | None,
    cpu: str | None,
    model: str | None,
    is_uma: bool,
    ref: dict,
) -> int:
    """Local_LLM_Index_Score (0-100): capacity (60) + GPU generation (25) + seller
    risk/reward (~±20) + target hint bonuses (+5 GPU, +3 model) − deductions (uncapped).

    target_gpus/target_models membership adds a small bonus but never gates routing.
    Clamped to [0, 100] after all adjustments.
    """
    capacity = _capacity_points(tier, ref)
    generation = _uma_soc_points(cpu, model, ref) if is_uma else _gpu_generation_points(gpu, is_uma, ref)
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
        patterns = ref.get("_target_models_lower") or [m.lower() for m in ref.get("target_models", [])]
        if any(pattern in model_lower for pattern in patterns):
            raw += 3

    raw += _apply_architecture_penalty(gpu, tier, ref)
    raw += _apply_egpu_interconnect_penalty(analysis, ref)

    return max(0, min(100, raw))


def decide(analysis: dict, ref: dict | None = None, workload: str | None = None) -> dict:
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
    system_ram = _ram_gb(ram_str)
    uma_ram = system_ram if is_uma else None
    uma_tier = _vram_tier(uma_ram, ref) if is_uma else None
    radeon_match = _is_radeon_mobile(gpu, ref)
    has_egpu = _has_egpu_bundle(model, egpu_model, ref)
    generation_points = _uma_soc_points(cpu, model, ref) if is_uma else _gpu_generation_points(gpu, is_uma, ref)
    _log_undiscovered_hardware(
        analysis,
        gpu,
        vram,
        system_ram,
        generation_points,
        is_target,
        is_uma,
        bool(radeon_match),
    )

    capacity_tier = uma_tier if is_uma else tier
    llm_index_score = calculate_llm_index_score(analysis, capacity_tier, gpu, cpu, model, is_uma, ref)

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

    paradigm = _classify_paradigm(analysis, ref, is_uma=is_uma, radeon_match=radeon_match)
    paradigm_note = None
    if workload == "text_llm" and paradigm in ("discrete_cuda", "discrete_rocm") and action == "SHORTLIST":
        action = "SKIP"
        paradigm_note = (
            f"Paradigm '{paradigm}' is not recommended for text-centric inference "
            "(VRAM cap limits context size vs UMA alternatives). "
            "Evaluate Apple Silicon UMA or Strix Halo UMA instead."
        )

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
        "paradigm": paradigm,
        "paradigm_note": paradigm_note,
    }
