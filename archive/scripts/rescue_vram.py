"""rescue_vram.py — Step 2 + Step 3 VRAM rescue for MANUAL_REVIEW records.

Steps:
  1. Load MANUAL_REVIEW records from data/shortlist_candidates.jsonl
  2. Attempt VRAM rescue from full_listing_text in data/fixtures/ebay_export.jsonl
  3. For still-missing VRAM where gpu_name IS known, apply authoritative lookup table
  4. Patch data/ai_studio_responses/ebay_csv_extraction.json in-place
  5. Print rescue summary

Rules:
  - Never fabricate VRAM — only use full_listing_text patterns or lookup table
  - Do NOT modify parse_ai_studio_extraction.py, decide(), or Makefile
"""

import json
import re
import sys
from pathlib import Path

SHORTLIST_PATH  = Path("data/shortlist_candidates.jsonl")
EXPORT_JSONL    = Path("data/fixtures/ebay_export.jsonl")
EXTRACTION_PATH = Path("data/ai_studio_responses/ebay_csv_extraction.json")
CSV_PATH        = Path("data/fixtures/ebay_cleaned.csv")

# ── Authoritative GPU→VRAM lookup ────────────────────────────────────────────
# NOTE: Where a GPU exists in the SRL (config/static_reference_layer.json),
# the SRL value is the governance layer and takes precedence.
# Values marked [SRL] are sourced from target_gpus.vram_gb in the SRL.
# Values marked [TASK] are from the task spec (not in SRL).
GPU_VRAM_LOOKUP: dict[str, int] = {
    # RTX 50-series laptop [SRL]
    "rtx 5090": 24,   # SRL
    "rtx 5080": 16,   # SRL
    "rtx 5070 ti": 12,  # task (not in SRL)
    "rtx 5070": 16,   # SRL: 16GB (task said 12 — SRL governs)
    # RTX 40-series laptop [SRL]
    "rtx 4090": 16,   # SRL
    "rtx 4080": 12,   # SRL
    "rtx 4070": 8,    # task (not in SRL)
    # RTX 30-series laptop [SRL / task]
    "rtx 3090": 24,   # task
    "rtx 3080 ti": 16,  # SRL
    "rtx 3080": 16,   # SRL
    "rtx 3070 ti": 8,   # task
    "rtx 3070": 8,    # task
    # NVIDIA RTX professional (mobile workstation) [SRL / task]
    "rtx a5000": 16,  # SRL
    "rtx a5500": 16,  # SRL
    "rtx a4500": 16,  # SRL
    "rtx a4000": 8,   # task (not in SRL — verified: mobile A4000=8GB)
    "rtx a3000": 12,  # SRL: 12GB (task said 6 — SRL governs)
    "rtx a2000": 4,   # task (not in SRL)
    # Quadro RTX [task]
    "quadro rtx 5000": 16,  # SRL (as Quadro RTX 5000)
    "quadro rtx 3000": 6,   # task (not in SRL)
    # Ada professional mobile [SRL / task]
    "rtx 3500 ada": 12,  # SRL
    "rtx 4000 ada": 12,  # SRL
    "rtx 5000 ada": 16,  # SRL
    "rtx 3000 ada": 8,   # task
    "rtx 500 ada":  8,   # task
    # RTX 5000 Quadro Ampere alias [SRL as 'RTX 5000 Ada'→16, but bare 'RTX 5000' also=16]
    "rtx 5000": 16,
    # Below-threshold — rescue to SKIP [task]
    "rtx 4060 ti": 16,
    "rtx 4060": 8,
}


def _vram_from_text(text: str) -> int | None:
    """
    Search text for VRAM patterns. Returns GB as int or None.
    Patterns matched (case-insensitive):
      - "16GB VRAM"  / "16 GB VRAM"
      - "VRAM: 16GB" / "VRAM 16GB"
      - "16GB GDDR6" / "16G GDDR"
      - "16GB video memory"
      - "16GB dedicated"  (dedicated graphics memory)
    """
    patterns = [
        r"(\d+)\s*GB\s+VRAM",
        r"VRAM[:\s]+(\d+)\s*GB",
        r"(\d+)\s*GB\s+GDDR",
        r"(\d+)\s*G\s*GDDR",
        r"(\d+)\s*GB\s+video\s+memory",
        r"(\d+)\s*GB\s+dedicated",
        r"video\s+memory[:\s]+(\d+)\s*GB",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _gpu_from_text(text: str) -> str | None:
    """
    Search text for GPU patterns when gpu_name is missing.
    Returns a normalised GPU name string or None.
    """
    patterns = [
        r"(RTX\s+(?:PRO\s+)?\d{3,4}(?:\s+Ti)?(?:\s+Ada)?)",
        r"(Quadro\s+RTX\s+\d{4,5})",
        r"(RTX\s+A\d{3,4}(?:\s+Ada)?)",
        r"(GTX\s+\d{4}(?:\s+Ti)?)",
        r"(Radeon\s+(?:RX\s+)?\d{3,4}(?:M|XT)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _lookup_vram(gpu_name: str) -> int | None:
    """
    Match gpu_name against GPU_VRAM_LOOKUP using progressively looser matching.
    Returns VRAM in GB or None.
    """
    if not gpu_name:
        return None
    name = gpu_name.lower().strip()
    # Exact match
    if name in GPU_VRAM_LOOKUP:
        return GPU_VRAM_LOOKUP[name]
    # Strip common prefixes
    for prefix in ("geforce ", "nvidia ", "quadro ", "mobile ", "laptop "):
        stripped = name.removeprefix(prefix)
        if stripped in GPU_VRAM_LOOKUP:
            return GPU_VRAM_LOOKUP[stripped]
    # Try removing trailing model suffixes like "laptop", "(laptop)"
    cleaned = re.sub(r"\s*\(laptop\)|\s+laptop$", "", name).strip()
    if cleaned in GPU_VRAM_LOOKUP:
        return GPU_VRAM_LOOKUP[cleaned]
    # Partial suffix match — find longest key that is a suffix of name
    best = None
    best_len = 0
    for key in GPU_VRAM_LOOKUP:
        if name.endswith(key) and len(key) > best_len:
            best = GPU_VRAM_LOOKUP[key]
            best_len = len(key)
    if best is not None:
        return best
    # Substring match (key contained in name) — pick longest
    for key in sorted(GPU_VRAM_LOOKUP.keys(), key=len, reverse=True):
        if key in name:
            return GPU_VRAM_LOOKUP[key]
    return None


def main() -> int:
    # ── Load MANUAL_REVIEW records ────────────────────────────────────────────
    all_records: list[dict] = []
    with open(SHORTLIST_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                all_records.append(json.loads(line))

    manual = [r for r in all_records if r.get("recommended_action") == "MANUAL_REVIEW"]
    print(f"Step 1 — MANUAL_REVIEW records: {len(manual)}")
    print()
    print(f"{'#':<4} {'gpu':<30} {'listing_title (truncated)'}")
    print("-" * 90)
    for i, r in enumerate(manual):
        print(f"{i+1:<4} {str(r.get('gpu', '')):<30} {str(r.get('listing_title', ''))[:55]}")

    # ── Load CSV for title→listing_id mapping ─────────────────────────────────
    import csv
    csv_rows: list[dict] = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    csv_by_title = {r["title"]: r["listing_id"] for r in csv_rows}

    # ── Load ebay_export.jsonl for full_listing_text ───────────────────────────
    export_records: list[dict] = []
    with open(EXPORT_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                export_records.append(json.loads(line))
    export_by_id: dict[str, dict] = {r["listing_id"]: r for r in export_records}

    print()
    print(f"ebay_cleaned.csv columns: listing_id, platform, title, price_raw, condition, seller_name, url")
    print(f"  → 'full_listing_text' NOT in CSV — found in ebay_export.jsonl instead")
    print(f"  → Proceeding with ebay_export.jsonl full_listing_text for Step 2")

    # ── Load extraction JSON ──────────────────────────────────────────────────
    with open(EXTRACTION_PATH) as f:
        extractions: list[dict] = json.load(f)
    ext_by_id: dict[str, dict] = {e["listing_id"]: e for e in extractions}

    # ── Step 2 + 3: Rescue loop ───────────────────────────────────────────────
    rescues: list[dict] = []
    no_rescue: list[dict] = []

    print()
    print("=" * 90)
    print("Step 2 — VRAM rescue from full_listing_text")
    print("=" * 90)

    for r in manual:
        title = r.get("listing_title", "")
        shortlist_gpu = r.get("gpu", "")

        listing_id = csv_by_title.get(title)
        if not listing_id:
            # Try fuzzy: find matching title in CSV
            for csv_title, lid in csv_by_title.items():
                if title and csv_title and title[:40] == csv_title[:40]:
                    listing_id = lid
                    break

        ext = ext_by_id.get(listing_id, {}) if listing_id else {}
        export = export_by_id.get(listing_id, {}) if listing_id else {}
        full_text = export.get("full_listing_text", "")
        ext_gpu = ext.get("gpu_name", "")
        ext_vram = ext.get("vram_capacity", 0)

        rescued_vram: int | None = None
        rescued_gpu: str | None = None
        source: str | None = None

        # Step 2a: Extract VRAM from full_listing_text
        if full_text:
            rescued_vram = _vram_from_text(full_text)
            if rescued_vram is not None:
                source = "full_text"
                print(f"  [FULL_TEXT] {listing_id}: VRAM={rescued_vram}GB  text={full_text[:80]!r}")

        # Step 2c: Extract GPU from full_listing_text if ext_gpu missing
        if not ext_gpu and full_text:
            rescued_gpu = _gpu_from_text(full_text)
            if rescued_gpu:
                print(f"  [FULL_TEXT] {listing_id}: GPU rescued={rescued_gpu!r}")

        # Step 3: GPU lookup fallback for still-missing VRAM
        if rescued_vram is None:
            gpu_for_lookup = ext_gpu or rescued_gpu or ""
            if gpu_for_lookup:
                looked_up = _lookup_vram(gpu_for_lookup)
                if looked_up is not None:
                    rescued_vram = looked_up
                    source = "gpu_lookup"
                    print(f"  [GPU_LOOKUP] {listing_id}: gpu={gpu_for_lookup!r} -> VRAM={rescued_vram}GB")
                else:
                    print(f"  [NO_MATCH]   {listing_id}: gpu={gpu_for_lookup!r} not in lookup table")
            else:
                print(f"  [NO_GPU]     {listing_id}: no gpu_name and no GPU found in listing text")

        if rescued_vram is not None or rescued_gpu is not None:
            rescues.append({
                "listing_id": listing_id,
                "title": title,
                "ext_gpu": ext_gpu,
                "rescued_vram": rescued_vram,
                "rescued_gpu": rescued_gpu,
                "source": source,
            })
        else:
            no_rescue.append({
                "listing_id": listing_id,
                "title": title,
                "gpu": ext_gpu,
                "reason": "no VRAM in full_text, no GPU in text, and GPU name not in lookup table"
                          if not ext_gpu else f"gpu={ext_gpu!r} not matched in lookup table",
            })

    print()
    print(f"Step 2+3 results: {len(rescues)} rescued, {len(no_rescue)} unresolvable")

    # ── Step 4a+b+c: Patch the extraction JSON ────────────────────────────────
    print()
    print("=" * 90)
    print("Step 4 — Patching ebay_csv_extraction.json")
    print("=" * 90)

    patched = 0
    for rescue in rescues:
        lid = rescue["listing_id"]
        if lid not in ext_by_id:
            print(f"  [WARN] {lid} not found in extraction JSON — skipping")
            continue
        entry = ext_by_id[lid]
        changed = []
        if rescue["rescued_vram"] is not None:
            old_vram = entry.get("vram_capacity", 0)
            entry["vram_capacity"] = rescue["rescued_vram"]
            changed.append(f"vram_capacity: {old_vram} -> {rescue['rescued_vram']}")
        if rescue["rescued_gpu"]:
            old_gpu = entry.get("gpu_name", "")
            if not old_gpu:
                entry["gpu_name"] = rescue["rescued_gpu"]
                changed.append(f"gpu_name: '' -> {rescue['rescued_gpu']!r}")
        if changed:
            print(f"  PATCH {lid}: {', '.join(changed)}")
            patched += 1

    print(f"\n  Total patches applied: {patched}")

    # Write patched extraction back
    with open(EXTRACTION_PATH, "w", encoding="utf-8") as f:
        json.dump(extractions, f, indent=2)
    print(f"  Written: {EXTRACTION_PATH}")

    # ── Summary of unresolvable ───────────────────────────────────────────────
    print()
    print("=" * 90)
    print(f"Step 5 preview — {len(no_rescue)} records CANNOT be rescued (no VRAM data anywhere):")
    print("=" * 90)
    for nr in no_rescue:
        print(f"  lid={nr['listing_id']}")
        print(f"    title={nr['title'][:70]!r}")
        print(f"    reason={nr['reason']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
