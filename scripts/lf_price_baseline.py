"""
S9-02: merge current `make hunt` candidate listings with historical shortlist
data into a single baseline CSV for the PWM lf-price-baseline research
workflow (see docs/pwm_workflow_catalog.md).

Run:
    .venv/bin/python scripts/lf_price_baseline.py
"""

import csv
import json
import re
import sys
from pathlib import Path

from scripts.lf_floor_sync import RESULTS_PATH, load_rows, normalize as normalize_hunt_row

HISTORICAL_PATH = Path("data/shortlist_candidates.jsonl")
OUT_CSV = Path("data/lf-price-baseline.csv")

FIELDS = ["source", "gpu", "price_aud", "recommended_action", "llm_index_score", "title_or_model"]

_PRICE_RE = re.compile(r"[\d,]+\.?\d*")


def parse_price_aud(text: str | None) -> float | None:
    """Parse strings like 'AU $7324.68' or '—' into a float, or None."""
    if not text:
        return None
    match = _PRICE_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def load_historical(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_historical_row(row: dict) -> dict:
    return {
        "source": "shortlist_historical",
        "gpu": row.get("gpu"),
        "price_aud": parse_price_aud(row.get("price")),
        "recommended_action": row.get("recommended_action"),
        "llm_index_score": row.get("llm_index_score"),
        "title_or_model": row.get("listing_title"),
    }


def normalize_current_row(row: dict) -> dict:
    n = normalize_hunt_row(row)
    return {
        "source": "hunt_current",
        "gpu": n["gpu"],
        "price_aud": n["price_aud"],
        "recommended_action": n["recommended_action"],
        "llm_index_score": n["llm_index_score"],
        "title_or_model": n["canonical_model"],
    }


def main() -> int:
    current = [normalize_current_row(r) for r in load_rows(RESULTS_PATH)]
    historical = [normalize_historical_row(r) for r in load_historical(HISTORICAL_PATH)]
    merged = current + historical

    if not merged:
        print("No current or historical candidates found — nothing to merge.")
        return 0

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged)

    print(f"Wrote {len(merged)} rows ({len(current)} current + {len(historical)} historical) → {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
