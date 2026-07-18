# scripts/inspect_trusted_null_vram_watch.py
import json
from pathlib import Path

PATH = Path("output/shortlist/watchlist_scored_active.jsonl")

def main() -> None:
    if not PATH.exists():
        print(f"Missing file: {PATH}")
        return

    rows = [json.loads(l) for l in PATH.open(encoding="utf-8") if l.strip()]
    candidates = [
        r for r in rows
        if r.get("decision") == "WATCH"
        and r.get("decision_reason") == "trusted_gpu_null_vram_watch"
    ]

    print(f"Trusted null-VRAM WATCH items: {len(candidates)}")
    for r in candidates[:30]:
        print(
            f"- {r.get('gpu_model') or '?'} | "
            f"vram={r.get('vram_gb')} | "
            f"price=${r.get('current_price')} | "
            f"title={r.get('title','')[:90]}"
        )

if __name__ == "__main__":
    main()
