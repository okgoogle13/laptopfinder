"""force_skip_patch.py — Force-SKIP Category D records (confirmed below-threshold).

These listings have confirmed VRAM values below the minimum threshold (16GB, or 12GB
with touchscreen exception). They should be SKIP, not occupy MANUAL_REVIEW slots.

Operates directly on data/shortlist_candidates.jsonl.
Does NOT modify ebay_csv_extraction.json — this is a post-decision override.

NOTE: shortlist_candidates.jsonl has no listing_id field — records are matched
by listing_title via CSV lookup.
"""
import csv as csv_mod
import json
import sys
from collections import Counter
from pathlib import Path

SHORTLIST_PATH = Path("data/shortlist_candidates.jsonl")
CSV_PATH = Path("data/fixtures/ebay_cleaned.csv")

# Category D — confirmed below-threshold listing IDs
FORCE_SKIP_IDS = {
    "ebay_au:117267040798",  # Quadro RTX 3000, 6GB
    "ebay_au:236740339258",  # RTX 3070 Ti, 8GB
    "ebay_au:278082458240",  # RTX A4000, 8GB
    "ebay_au:198363360068",  # RTX 4060, 8GB
    "ebay_au:358135333685",  # RTX 4060, 8GB
    "ebay_au:389927241205",  # RTX A2000, 4GB
    "ebay_au:187687118880",  # RTX A4000, 8GB
    "ebay_au:127783573861",  # RTX 500 Ada, 8GB
    "ebay_au:366491967195",  # No GPU
    "ebay_au:188023133892",  # No GPU
}


def main() -> int:
    if not SHORTLIST_PATH.exists():
        print(f"ERROR: {SHORTLIST_PATH} not found", file=sys.stderr)
        return 1

    records: list[dict] = []
    with open(SHORTLIST_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records from {SHORTLIST_PATH}")
    print(f"Note: shortlist_candidates.jsonl has no listing_id field — matching via listing_title from CSV.")
    print()

    # Build listing_id → title mapping from CSV
    id_to_title: dict[str, str] = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv_mod.DictReader(f):
                id_to_title[row["listing_id"]] = row["title"]
    else:
        print(f"ERROR: {CSV_PATH} not found", file=sys.stderr)
        return 1

    # Build set of listing_titles that correspond to force-SKIP IDs
    skip_titles: set[str] = set()
    for lid in sorted(FORCE_SKIP_IDS):
        title = id_to_title.get(lid)
        if title:
            skip_titles.add(title)
            print(f"  ID→title: {lid} → {title!r}")
        else:
            print(f"  WARNING: {lid} not found in CSV")

    print()
    updated = 0
    for r in records:
        title = r.get("listing_title", "")
        if title in skip_titles:
            old_action = r.get("recommended_action", "")
            r["recommended_action"] = "SKIP"
            r["skip_reason"] = "vram_below_threshold"
            print(f"  PATCHED {old_action!r} → 'SKIP': {title[:70]!r}")
            updated += 1

    print(f"\nTotal records updated: {updated}")

    # Warn if any titles were not found in shortlist
    shortlist_titles = {r.get("listing_title", "") for r in records}
    not_found = skip_titles - shortlist_titles
    if not_found:
        print(f"\nWARNING: {len(not_found)} target titles not in shortlist (may already be absent):")
        for t in sorted(not_found):
            print(f"  {t!r}")

    # Write back
    with open(SHORTLIST_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nWritten: {SHORTLIST_PATH}")

    counts = Counter(r.get("recommended_action") for r in records)
    print("\nAction counts after patch:")
    for action, count in sorted(counts.items()):
        print(f"  {action}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
