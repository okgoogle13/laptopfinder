#!/usr/bin/env python3
"""Zero-LLM snapshot of runner/evidence state and the NEXT_TASK queue.

Reads only files that runners already write (or STATUS.md) — no API calls,
no LLM calls. Run via `make status`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def age(path: Path) -> str:
    if not path.exists():
        return "never run"
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    hours = (datetime.now(tz=timezone.utc) - mtime).total_seconds() / 3600
    return f"{mtime:%Y-%m-%d %H:%M UTC} ({hours:.1f}h ago)"


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def next_task_block() -> str:
    status_path = ROOT / "STATUS.md"
    if not status_path.exists():
        return "STATUS.md not found"
    lines = status_path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## NEXT_TASK":
            start = i
            break
    if start is None:
        return "no ## NEXT_TASK section"
    block = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip():
            block.append(line)
    return "\n".join(block) if block else "(empty — nothing queued)"


def main() -> None:
    print("=== NEXT_TASK (STATUS.md) ===")
    print(next_task_block())

    print("\n=== Runner state ===")
    print(f"sniper last run       : {age(ROOT / 'data/seen_sniper_items.json')}")
    print(f"hunt/sniper decisions : {age(ROOT / 'output/decisions/latest_decisions.json')}")
    print(f"shortlist output      : {age(ROOT / 'output/shortlist/latest_shortlist.md')}")
    print(f"purchase matrix       : {age(ROOT / 'output/shortlist/purchase_matrix.md')}")

    evidence_path = ROOT / "data/evidence/aggregated.jsonl"
    n = count_lines(evidence_path)
    print("\n=== Evidence pipeline ===")
    print(f"aggregated records : {n} (handoff regenerates at >=5)")
    print(f"last updated       : {age(evidence_path)}")


if __name__ == "__main__":
    main()
