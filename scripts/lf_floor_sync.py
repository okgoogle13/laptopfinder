"""
S9-01: normalize data/hunt_results.jsonl (from `make hunt CONFIG=...`) into a
flat floor/ceiling pricing CSV for the PWM lf-floor-sync research workflow
(see docs/pwm_workflow_catalog.md).

Run:
    .venv/bin/python scripts/lf_floor_sync.py
"""

import csv
import json
import sys
from pathlib import Path

RESULTS_PATH = Path("data/hunt_results.jsonl")
OUT_CSV = Path("data/lf-floor-listings.csv")

FIELDS = [
    "item_id",
    "item_web_url",
    "canonical_model",
    "price_aud",
    "gpu",
    "vram_gb",
    "recommended_action",
    "llm_index_score",
]


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(row: dict) -> dict:
    extracted = row.get("analysis", {}).get("extracted_data", {})
    vram = extracted.get("vram_capacity")
    vram_gb = vram["semantic_value"] if isinstance(vram, dict) else None
    decision = row.get("decision", {})
    return {
        "item_id": row.get("item_id"),
        "item_web_url": row.get("item_web_url"),
        "canonical_model": row.get("canonical_model"),
        "price_aud": row.get("price_aud"),
        "gpu": extracted.get("gpu"),
        "vram_gb": vram_gb,
        "recommended_action": decision.get("recommended_action"),
        "llm_index_score": decision.get("llm_index_score"),
    }


def main() -> int:
    rows = load_rows(RESULTS_PATH)
    if not rows:
        print(f"No rows found in {RESULTS_PATH} — run `make hunt CONFIG=...` first.")
        return 0

    normalized = [normalize(r) for r in rows]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(normalized)

    print(f"Wrote {len(normalized)} rows → {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
