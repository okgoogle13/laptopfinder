"""
Build a value-ranked shortlist from data/shortlist_candidates.jsonl.

Four lanes, ordered by desktop-replacement priority:
  gaming_17_18              — 17-18" discrete-GPU gaming laptops (preferred)
  workstation_16_touch_or_pro — 16-17" RTX workstations, esp. touchscreen
  uma_dev_rig               — Strix Halo / ROG Z13 / ProArt PX13 UMA outliers
  macbook_16_high_ram       — MacBook Pro / Mac Studio with high unified RAM

14" and 15" machines are accepted within their lane but sorted last (fallback).
A form-factor bonus (+0..+8 pts) is folded into adjusted_score for discrete-GPU
lanes. uma_dev_rig skips the FF bonus — compact size is acceptable there.

Classification gate for uma_dev_rig: title must match a known UMA model pattern
OR is_uma must be True (set from notes or title detection). A bare system_ram
threshold is NOT sufficient — it would misclassify high-RAM discrete-GPU rigs.

Run:
    .venv/bin/python scripts/build_shortlist_value.py
"""

import json
import re
import sys
from pathlib import Path

SHORTLIST_PATH = Path("data/shortlist_candidates.jsonl")
OUT_JSONL = Path("data/shortlist_value.jsonl")
OUT_MD = Path("data/shortlist_value.md")

TOP_N = {
    "gaming_17_18": 4,
    "workstation_16_touch_or_pro": 3,
    "uma_dev_rig": 2,
    "macbook_16_high_ram": 2,
}

# Model-name → screen size for titles that omit an explicit inch marker.
_MODEL_SIZE_HINTS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bBlade\s+18\b", re.I), 18),
    (re.compile(r"\bHelios\s+18\b", re.I), 18),
    (re.compile(r"\bVector\s+18\b", re.I), 18),
    (re.compile(r"\bStealth\s+A18\b", re.I), 18),
    (re.compile(r"\bScar\s+18\b", re.I), 18),
    (re.compile(r"\bStrix\s+SCAR\s+18\b", re.I), 18),
    (re.compile(r"\bTUF\s+(?:Gaming\s+)?A18\b", re.I), 18),
    (re.compile(r"\bRaider\s+GE[67]8\b", re.I), 17),
    (re.compile(r"\bGE[67]8\b", re.I), 17),
    (re.compile(r"\bScar\s+17\b", re.I), 17),
    (re.compile(r"\bStrix\s+SCAR\s+17\b", re.I), 17),
    (re.compile(r"\bTriton\s+17\b", re.I), 17),
    (re.compile(r"\bAorus\s+17\b", re.I), 17),
    (re.compile(r"\bPrecision\s+7[67]\d{2}\b", re.I), 17),
    (re.compile(r"\bPrecision\s+7750\b", re.I), 17),
    (re.compile(r"\bFury\s+1[67]\b", re.I), 16),
    (re.compile(r"\bThinkPad\s+P16\b", re.I), 16),
    (re.compile(r"\bThinkPad\s+P15\b", re.I), 15),
    (re.compile(r"\bBlade\s+16\b", re.I), 16),
    (re.compile(r"\bHelios\s+16\b", re.I), 16),
    (re.compile(r"\bOmen\s+MAX\b", re.I), 16),
    (re.compile(r"\bPrecision\s+7[45]\d{2}\b", re.I), 15),
    (re.compile(r"\bPrecision\s+7560\b", re.I), 15),
    (re.compile(r"\bThinkPad\s+P15\b", re.I), 15),
    (re.compile(r"\bAlienwware\s+X15\b", re.I), 15),
    (re.compile(r"\bAlienwware\s+X17\b", re.I), 17),
    (re.compile(r"\bTriton\s+14\b", re.I), 14),
]

# Title patterns that identify AMD/Intel UMA dev rigs (Strix Halo, ROG Z13, etc.).
# Used in _enrich to set is_uma=True even on raw CSV rows without pipeline notes.
# Note: "XG Mobile" means the machine SUPPORTS the dock, not that it has a discrete
# internal GPU — ROG Flow X13 + XG Mobile is still a UMA laptop with an external GPU.
_UMA_DEV_RIG_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bStrix\s+Halo\b", re.I),
    re.compile(r"\bROG\s+Z1[36]\b", re.I),
    re.compile(r"\bProArt\s+PX1[36]\b", re.I),
    re.compile(r"\bRyzen\s+AI\s+Max\b", re.I),
    re.compile(r"\bXG\s+Mobile\b", re.I),
    re.compile(r"\bHX\s*370\b", re.I),         # Ryzen AI Max 390/395 marketing name
]

_MAC_GPU_PATTERNS = [
    "M1 Max", "M1 Ultra", "M2 Max", "M2 Ultra",
    "M3 Max", "M3 Ultra", "M4 Max", "M4 Ultra",
]
_MAC_TITLE_KEYWORDS = ["macbook pro", "mac studio", "mac mini"]
_WORKSTATION_KEYWORDS = ["precision", "thinkpad p", "zbook", "proart", "creator"]

# --- screen size extraction ---

def _extract_screen_inches(title: str) -> int | None:
    # Explicit inch marker: 18" / 17" / 16" / 15" / 14"
    m = re.search(r'\b(14|15|16|17|18)\s*["""′″]', title)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(14|15|16|17|18)\s*-?\s*inch', title, re.I)
    if m:
        return int(m.group(1))
    # Model-name heuristics
    for pattern, inches in _MODEL_SIZE_HINTS:
        if pattern.search(title):
            return inches
    # Alienware X15 / X17 from the "X<size>" suffix
    m = re.search(r'\bX(15|17)\b', title)
    if m:
        return int(m.group(1))
    return None


# --- fallback extraction from legacy JSONL fields ---

def _extract_vram_from_notes(notes: str) -> float | None:
    m = re.search(
        r"VRAM (?:tier: \w+ \(|touchscreen exception: )(\d+\.?\d*)GB", notes
    )
    return float(m.group(1)) if m else None


def _extract_ram_from_title(title: str, vram_gb: float | None) -> float | None:
    # 1. Explicit label: "64GB DDR5" / "32GB RAM" / "16gb Ddr5"
    m = re.search(r"\b(\d+)\s*G[Bb]\s+(?:DDR\d*|LPDDR\d*|RAM\b)", title, re.I)
    if m:
        v = float(m.group(1))
        if v <= 192:
            return v
    # 2. "<N>GB <M>TB" pattern — GB is system RAM, TB is storage
    m = re.search(r"\b(\d+)\s*G[Bb]?\s+\d+\s*T[Bb]\b", title, re.I)
    if m:
        v = float(m.group(1))
        if v <= 192:
            return v
    # 3. Largest GB-ish number ≤192 that isn't VRAM
    all_gb = [float(x) for x in re.findall(r"\b(\d+)\s*G[Bb]?\b", title, re.I)]
    candidates = [x for x in all_gb if x != vram_gb and 8 <= x <= 192]
    return max(candidates) if candidates else None


def _enrich(r: dict) -> dict:
    """Fill missing structured fields from notes / listing_title."""
    notes = r.get("notes", "")
    title = r.get("listing_title", "")

    vram_gb = r.get("vram_gb") or _extract_vram_from_notes(notes)
    has_touchscreen = r.get("has_touchscreen") or (
        "touchscreen" in notes.lower() or "touch" in title.lower()
    )
    is_uma = "UMA platform" in notes or any(
        p.search(title) for p in _UMA_DEV_RIG_PATTERNS
    )

    if is_uma:
        vram_gb = None

    system_ram_gb = r.get("system_ram_gb") or _extract_ram_from_title(title, vram_gb)

    price_aud = r.get("price_aud")
    if price_aud is None:
        raw = r.get("price", "")
        m = re.search(r"[\d,]+\.?\d*", raw.replace(",", ""))
        if m:
            price_aud = float(m.group(0))

    screen_inches = r.get("screen_inches") or _extract_screen_inches(title)

    return {**r, "vram_gb": vram_gb, "system_ram_gb": system_ram_gb,
            "price_aud": price_aud, "has_touchscreen": has_touchscreen,
            "is_uma": is_uma, "screen_inches": screen_inches}


# --- classification ---

def classify_lane(r: dict) -> str:
    title = r["listing_title"].lower()
    gpu = (r.get("gpu") or "").lower()

    # Mac brand/chip check must come first so Apple UMA goes to macbook_16_high_ram.
    if any(kw in title for kw in _MAC_TITLE_KEYWORDS) or any(
        pat.lower() in gpu for pat in _MAC_GPU_PATTERNS
    ):
        return "macbook_16_high_ram"

    # AMD/Intel UMA dev rigs — must precede workstation check so ProArt PX13
    # (which also matches "proart" workstation keyword) routes here instead.
    if r.get("is_uma"):
        return "uma_dev_rig"

    if any(kw in title for kw in _WORKSTATION_KEYWORDS) or r.get("has_touchscreen"):
        return "workstation_16_touch_or_pro"

    return "gaming_17_18"


def classify_tier(r: dict, lane: str) -> str | None:
    vram = r.get("vram_gb")
    ram = r.get("system_ram_gb")

    if lane in ("macbook_16_high_ram", "uma_dev_rig"):
        if ram and ram >= 96:
            return "A"
        if ram and ram >= 64:
            return "B"
        if ram and ram >= 32:
            return "C"
        return None

    if vram and vram >= 16 and ram and ram >= 64:
        return "A"
    if vram and vram >= 12 and ram and ram >= 32:
        return "B"
    if vram and vram >= 8 and ram and ram >= 32:
        return "C"
    return None


def balance_penalty(r: dict, lane: str) -> int:
    if lane in ("macbook_16_high_ram", "uma_dev_rig"):
        return 0
    vram = r.get("vram_gb")
    ram = r.get("system_ram_gb")
    if vram is None or ram is None:
        return 0
    if ram < vram:
        return -5
    if ram >= vram * 1.25:
        return 3
    return 0


def form_factor_bonus(r: dict) -> int:
    """Screen-size bonus folded into adjusted_score before value_index is computed."""
    inches = r.get("screen_inches")
    if inches is None:
        return 0
    if inches >= 18:
        return 8
    if inches == 17:
        return 6
    if inches == 16 and r.get("has_touchscreen"):
        return 5
    if inches == 16:
        return 3
    # 14/15" — no bonus (fallback class)
    return 0


def value_index(adjusted: int, price: float | None) -> float | None:
    if not price:
        return None
    return round(adjusted / price, 5)


def _is_fallback(r: dict) -> bool:
    inches = r.get("screen_inches")
    return inches is not None and inches < 16


def _qualify_reason(r: dict) -> str:
    lane = r.get("lane", "")
    inches = r.get("screen_inches")
    touch = r.get("has_touchscreen", False)
    ram = r.get("system_ram_gb")

    if lane in ("macbook_16_high_ram", "uma_dev_rig"):
        return f"UMA {ram:.0f}GB unified RAM" if ram else "UMA platform"

    if inches is None:
        return "size unknown"
    if inches >= 18:
        return "18\" desktop replacement"
    if inches == 17:
        return "17\" desktop replacement"
    if inches == 16 and touch:
        return "16\" + touchscreen"
    if inches == 16:
        return "16\" form factor"
    if inches == 15:
        return "15\" fallback"
    return "14\" fallback"


def sort_key(r: dict):
    vi = r["value_index"]
    if r.get("lane") == "uma_dev_rig":
        score = r.get("llm_index_score") or 0
        ram = r.get("system_ram_gb") or 0
        # Blend capability (70%) with value (30%) so an overpriced outlier can't
        # silently dominate on raw score alone. vi scaled to match score magnitude.
        vi_scaled = (vi or 0.0) * 10_000
        return (-(score * 0.7 + vi_scaled * 0.3), -ram, vi is None)
    fallback = 1 if _is_fallback(r) else 0
    return (fallback, vi is None, -(vi or 0.0), -r["adjusted_score"])


def format_md_line(r: dict) -> str:
    price = f"AU ${r['price_aud']:.0f}" if r["price_aud"] else "price unknown"
    vi = f"{r['value_index']:.5f}" if r["value_index"] else "n/a"
    vram = f"{r['vram_gb']:.0f}GB VRAM" if r.get("vram_gb") else ""
    ram = f"{r['system_ram_gb']:.0f}GB RAM" if r.get("system_ram_gb") else ""
    specs = ", ".join(x for x in [vram, ram] if x)
    size = f" [{r['screen_inches']}″]" if r.get("screen_inches") else ""
    reason = f" _{_qualify_reason(r)}_"
    penalty = r["adjusted_score"] - r.get("llm_index_score", 0)
    penalty_str = f" (adj {penalty:+d})" if penalty else ""
    fallback_flag = " ⚠ fallback" if _is_fallback(r) else ""
    return (
        f"- **[Tier {r['tier']}]** {r['listing_title']}{size}{reason}{fallback_flag}  \n"
        f"  {price} | score {r['adjusted_score']}{penalty_str} | value/$ {vi}"
        + (f" | {specs}" if specs else "")
    )


_SECTION_HEADINGS = {
    "gaming_17_18": "Gaming — 17-18\" Desktop Replacements",
    "workstation_16_touch_or_pro": "RTX Workstations — 16-17\" (incl. Touch)",
    "uma_dev_rig": "UMA Dev Rigs — Strix Halo / ROG Z13 / ProArt",
    "macbook_16_high_ram": "MacBook Pro — High Unified RAM",
}


def main() -> int:
    if not SHORTLIST_PATH.exists():
        print(f"ERROR: {SHORTLIST_PATH} not found.", file=sys.stderr)
        return 1

    records = [json.loads(l) for l in SHORTLIST_PATH.read_text().splitlines() if l.strip()]
    candidates = [r for r in records if r.get("recommended_action") == "SHORTLIST"]
    candidates = [_enrich(r) for r in candidates]

    enriched = []
    for r in candidates:
        lane = classify_lane(r)
        tier = classify_tier(r, lane)
        penalty = balance_penalty(r, lane)
        ff_bonus = 0 if lane == "uma_dev_rig" else form_factor_bonus(r)
        adjusted = (r.get("llm_index_score") or 0) + penalty + ff_bonus
        vi = value_index(adjusted, r.get("price_aud"))
        enriched.append({**r, "lane": lane, "tier": tier,
                          "adjusted_score": adjusted, "value_index": vi})

    core = [r for r in enriched if r["tier"] in ("A", "B")]
    fringe = [r for r in enriched if r["tier"] == "C"]
    no_tier = [r for r in enriched if r["tier"] is None]

    selected = []
    lane_order = ("gaming_17_18", "workstation_16_touch_or_pro", "uma_dev_rig", "macbook_16_high_ram")
    for lane in lane_order:
        group = sorted([r for r in core if r["lane"] == lane], key=sort_key)
        selected.extend(group[: TOP_N[lane]])

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w") as f:
        for r in selected:
            f.write(json.dumps(r) + "\n")

    md_lines = ["# Laptop Shortlist — Desktop-Replacement First\n"]
    md_lines.append(
        "_Ranked by value/$ within each lane. Form-factor bonus (+3..+8 pts) "
        "is folded into score before ranking. 14-15\" machines are fallback only._\n"
    )

    for lane in lane_order:
        heading = _SECTION_HEADINGS[lane]
        group = [r for r in selected if r["lane"] == lane]
        md_lines.append(f"## {heading}\n")
        if group:
            for r in group:
                md_lines.append(format_md_line(r))
        else:
            md_lines.append("_No qualifying candidates._")
        md_lines.append("")

    if fringe:
        md_lines.append("## Tier C — Fringe (budget curiosity)\n")
        for r in sorted(fringe, key=sort_key):
            md_lines.append(format_md_line(r))
        md_lines.append("")

    if no_tier:
        md_lines.append(
            f"__{len(no_tier)} SHORTLIST record(s) excluded — "
            "could not determine VRAM/RAM tier.__\n"
        )
        for r in no_tier:
            vram = r.get("vram_gb")
            ram = r.get("system_ram_gb")
            md_lines.append(f"- {r['listing_title']} (vram={vram}, ram={ram})")
        md_lines.append("")

    OUT_MD.write_text("\n".join(md_lines))

    print(f"Wrote {len(selected)} records → {OUT_JSONL}")
    print(f"Wrote {OUT_MD}")
    for lane in lane_order:
        count = sum(1 for r in selected if r["lane"] == lane)
        label = _SECTION_HEADINGS[lane]
        print(f"  {label}: {count}")
    if fringe:
        print(f"  Tier C (fringe): {len(fringe)} — listed in MD but not in top-N")
    if no_tier:
        print(f"  No tier        : {len(no_tier)} — see MD for details")
    return 0


if __name__ == "__main__":
    sys.exit(main())
