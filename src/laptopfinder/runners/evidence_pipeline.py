import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "evidence"
RAW_DIR = DATA_DIR / "raw"
ARCHIVE_DIR = DATA_DIR / "archive"
DB_FILE = DATA_DIR / "aggregated.jsonl"
HANDOFF_FILE = DATA_DIR / "claude_handoff.txt"
PROMOTION_THRESHOLD = 5


def run_gemini_parser(file_path: Path) -> dict:
    return {
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": file_path.name,
        "data_confidence": "high",
        "observed_telemetry": {
            "memory_pressure_state": "red",
            "physical_memory_gb": 16.0,
            "app_memory_gb": 12.1,
            "wired_memory_gb": 3.2,
            "compressed_memory_gb": 1.1,
            "cached_files_gb": 0.8,
            "swap_used_gb": 4.5,
        },
        "active_processes": ["Docker", "Terminal"],
        "uncertainty_flags": ["STUB: real Gemini call not yet wired"],
    }


def generate_claude_handoff(aggregated_data: list) -> None:
    prompt_file = BASE_DIR / "prompts" / "claude_evidence_analyzer.txt"
    instructions = (
        prompt_file.read_text(encoding="utf-8")
        if prompt_file.exists()
        else "Analyze this telemetry..."
    )
    payload = (
        f"{instructions}\n\n"
        f"=== AGGREGATED TELEMETRY ===\n"
        f"{json.dumps(aggregated_data, indent=2)}\n"
    )
    HANDOFF_FILE.write_text(payload, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence Pipeline runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and append to JSONL but skip archiving and handoff generation.",
    )
    args = parser.parse_args()

    raw_files = sorted(RAW_DIR.glob("*.*"))
    if not raw_files:
        print("No new evidence in /raw. Exiting.")
        return

    print(f"Found {len(raw_files)} file(s) in /raw. dry_run={args.dry_run}")
    records_total = (
        sum(1 for line in DB_FILE.read_text(encoding="utf-8").splitlines() if line.strip())
        if DB_FILE.exists()
        else 0
    )

    with DB_FILE.open("a", encoding="utf-8") as db:
        for file in raw_files:
            print(f"  Parsing {file.name} with Gemini (stub)...")
            try:
                record = run_gemini_parser(file)
                db.write(json.dumps(record) + "\n")
                records_total += 1

                if args.dry_run:
                    print(f"  [DRY-RUN] Would archive {file.name} -> skipping move.")
                else:
                    shutil.move(str(file), ARCHIVE_DIR / file.name)
                    print(f"  Archived {file.name}.")
            except Exception as exc:
                print(f"  ERROR processing {file.name}: {exc}")

    print(f"DB now has {records_total} record(s). Threshold is {PROMOTION_THRESHOLD}.")
    if records_total >= PROMOTION_THRESHOLD:
        all_data = [
            json.loads(line)
            for line in DB_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        print("Threshold met. Generating handoff for Claude Pro...")
        if args.dry_run:
            print("  [DRY-RUN] Would generate claude_handoff.txt -> skipping.")
        else:
            generate_claude_handoff(all_data)
            print("\n=== CLAUDE PRO HANDOFF READY ===")
            print("1. Open Claude Pro web or desktop app.")
            print(f"2. Copy the contents of: {HANDOFF_FILE.relative_to(BASE_DIR)}")
            print(f"3. Paste into Claude and save the JSON response to: {(DATA_DIR / 'targets.json').relative_to(BASE_DIR)}")
            print("================================\n")
    else:
        print(f"Awaiting {PROMOTION_THRESHOLD - records_total} more record(s) before inference.")


if __name__ == "__main__":
    main()
