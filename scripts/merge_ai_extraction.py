"""Merge AI Studio hardware extractions into the raw scraped eBay listings.

Reads:
  data/fixtures/ebay_cleaned.csv              (raw scraped dataset — source of truth)
  data/ai_studio_responses/ebay_csv_extraction.json  (AI Studio hardware extraction)

Writes:
  data/processed/merged_listings.json         (merged, finalized dataset)

Merge strategy:
  - For each scraped record, look up matching extraction by listing_id.
  - Merge using dict unpacking: {**scraped_record, **hw_fields}.
  - If no extraction match exists, write explicit Python None (JSON null) for all
    8 target hardware fields:
      gpu_name, vram_capacity, cpu_name, total_system_ram, storage,
      egpu_model, touchscreen_digitizer, exact_model_name
"""

import csv
import json
import sys
from pathlib import Path

RAW_CSV   = Path("data/fixtures/ebay_cleaned.csv")
HW_JSON   = Path("data/ai_studio_responses/ebay_csv_extraction.json")
OUT_FILE  = Path("data/processed/merged_listings.json")

HW_FIELDS = [
    "gpu_name",
    "vram_capacity",
    "cpu_name",
    "total_system_ram",
    "storage",
    "egpu_model",
    "touchscreen_digitizer",
    "exact_model_name",
]

NULL_HW = {field: None for field in HW_FIELDS}


def load_csv(path: Path) -> list[dict]:
    with open(path, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_hw(path: Path) -> dict[str, dict]:
    """Return a dict keyed by listing_id containing only the 8 target hw fields."""
    with open(path, encoding="utf-8") as f:
        extractions = json.load(f)
    result = {}
    for item in extractions:
        lid = item.get("listing_id")
        if not lid:
            continue
        result[lid] = {field: item.get(field) for field in HW_FIELDS}
    return result


def main() -> int:
    if not RAW_CSV.exists():
        print(f"ERROR: raw CSV not found: {RAW_CSV}", file=sys.stderr)
        return 1
    if not HW_JSON.exists():
        print(f"ERROR: hw extraction not found: {HW_JSON}", file=sys.stderr)
        return 1

    scraped_rows = load_csv(RAW_CSV)
    hw_map = load_hw(HW_JSON)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    merged = []
    matches = 0
    mismatches = 0

    for row in scraped_rows:
        listing_id = row.get("listing_id", "")
        hw_fields = hw_map.get(listing_id)

        if hw_fields is not None:
            record = {**row, **hw_fields}
            matches += 1
        else:
            record = {**row, **NULL_HW}
            mismatches += 1

        merged.append(record)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    total = len(merged)
    print(f"Merge complete.")
    print(f"  Total items processed : {total}")
    print(f"  Matches (hw merged)   : {matches}")
    print(f"  Mismatches (null hw)  : {mismatches}")
    print(f"  Output                : {OUT_FILE.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
