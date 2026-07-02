#!/usr/bin/env python3
"""Proactive Market Gap Scanner.

Sweeps raw feed files (data/feed_live/listing-*.txt or a fallback
feed.txt / data/feed_manual.txt) and cross-references parsed GPU names
and prices against static_reference_layer.json.

Outputs three alert types:
  [GRADUATION_ALERT]  - A watch-list GPU seen at a price below graduation criteria
  [PRICE_DRIFT_ALERT] - A target GPU seen outside its observed AU price band
  [NEW_SIGHTING_ALERT] - A GPU seen in the feed but absent from both target_gpus and watch_list
"""

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
SRL_PATH = _REPO_ROOT / "config" / "static_reference_layer.json"

# Candidate feed file locations, searched in priority order
FEED_LOCATIONS = [
    _REPO_ROOT / "data" / "feed_live",   # directory of listing-*.txt files
    _REPO_ROOT / "data" / "feed_manual.txt",
    _REPO_ROOT / "feed.txt",
]

# Minimum VRAM threshold to report a NEW_SIGHTING (only flag hardware that would matter)
NEW_SIGHTING_MIN_VRAM_GB = 12

# Regex for extracting price (AUD) from listing text — handles $1,234 and $1234 formats
PRICE_RE = re.compile(r"\$\s*([\d,]+)(?:\.\d+)?\s*(?:AUD|aud|aud\b)?")
GPU_NAME_PATTERNS: list[re.Pattern] = []  # built at runtime from SRL


def load_srl() -> dict:
    return json.loads(SRL_PATH.read_text(encoding="utf-8"))


def build_gpu_patterns(srl: dict) -> list[tuple[str, re.Pattern]]:
    """Build case-insensitive word-boundary regex for each known GPU name."""
    names = (
        list(srl.get("target_gpus", {}).keys())
        + [e["name"] for e in srl.get("watch_list", [])]
    )
    return [(name, re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)) for name in names]


def collect_feed_files() -> list[Path]:
    files: list[Path] = []
    for loc in FEED_LOCATIONS:
        p = Path(loc)
        if p.is_dir():
            files.extend(sorted(p.glob("listing-*.txt")))
        elif p.is_file():
            files.append(p)
    return files


def parse_price(text: str) -> int | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def scan_file(path: Path, srl: dict, gpu_patterns: list[tuple[str, re.Pattern]]) -> list[str]:
    alerts: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    price = parse_price(text)

    target_gpus = srl.get("target_gpus", {})
    watch_list = {e["name"]: e for e in srl.get("watch_list", [])}
    matched_names: list[str] = []

    for name, pattern in gpu_patterns:
        if pattern.search(text):
            matched_names.append(name)

    for name in matched_names:
        if name in watch_list:
            entry = watch_list[name]
            grad_condition = entry.get("graduation_condition", "")
            alerts.append(
                f"[GRADUATION_ALERT] {path.name}: '{name}' (watch-list) detected in feed. "
                f"Graduation condition: \"{grad_condition}\". "
                f"{'Price: $' + str(price) + ' AUD' if price else 'Price not found.'}"
            )
        elif name in target_gpus:
            entry = target_gpus[name]
            min_p = entry.get("observed_au_price_min_aud")
            max_p = entry.get("observed_au_price_max_aud")
            if price and min_p and max_p:
                if price < min_p:
                    alerts.append(
                        f"[PRICE_DRIFT_ALERT] {path.name}: '{name}' listed at ${price} AUD "
                        f"— BELOW observed band (${min_p}–${max_p}). Potential bargain; verify listing."
                    )
                elif price > max_p:
                    alerts.append(
                        f"[PRICE_DRIFT_ALERT] {path.name}: '{name}' listed at ${price} AUD "
                        f"— ABOVE observed band (${min_p}–${max_p}). Band may need updating."
                    )

    # NEW_SIGHTING: check for high-VRAM GPU patterns NOT in any known list
    # Heuristic: RTX/RX/Quadro/M-series tokens not matched above
    unrecognised = re.findall(
        r"\b(RTX\s+\d[\w\s]*|RX\s+\d[\w\s]*|Quadro\s+RTX\s+\d[\w\s]*|M\d\s+(?:Max|Ultra|Pro))\b",
        text,
        re.IGNORECASE,
    )
    known_names_lower = {n.lower() for n, _ in gpu_patterns}
    for raw in set(unrecognised):
        normalised = raw.strip()
        if normalised.lower() not in known_names_lower:
            alerts.append(
                f"[NEW_SIGHTING_ALERT] {path.name}: Unrecognised GPU pattern '{normalised}' "
                f"not present in SRL target_gpus or watch_list. Review for SRL addition."
            )

    return alerts


def main() -> int:
    srl = load_srl()
    gpu_patterns = build_gpu_patterns(srl)
    feed_files = collect_feed_files()

    if not feed_files:
        print(
            "[INFO] No feed files found. Drop listing text files into data/feed_live/ "
            "or create data/feed_manual.txt to scan.",
            file=sys.stderr,
        )
        return 0

    all_alerts: list[str] = []
    for path in feed_files:
        all_alerts.extend(scan_file(path, srl, gpu_patterns))

    if not all_alerts:
        print(f"[OK] Scanned {len(feed_files)} file(s). No market gaps detected.")
        return 0

    for alert in all_alerts:
        print(alert)

    print(f"\n--- {len(all_alerts)} alert(s) from {len(feed_files)} file(s) ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
