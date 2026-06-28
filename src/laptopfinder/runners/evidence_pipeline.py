import argparse
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "evidence"
RAW_DIR = DATA_DIR / "raw"
ARCHIVE_DIR = DATA_DIR / "archive"
DB_FILE = DATA_DIR / "aggregated.jsonl"
HANDOFF_FILE = DATA_DIR / "claude_handoff.txt"
PROMOTION_THRESHOLD = 5


# Gemini-specific projection of evidence_normalized.schema.json.
# Uses {"nullable": true} instead of JSON Schema's {"type": ["string", "null"]}
# because Gemini's response_schema does not support type-array nullability.
# Keys are kept in sync via test_gemini_schema_keys_match_canonical().
GEMINI_EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "event_timestamp":   {"type": "string",  "nullable": True},
        "source_file":       {"type": "string",  "nullable": True},
        "scenario_label":    {"type": "string",  "nullable": True},
        "source_kind": {
            "type": "string",
            "enum": ["terminal_log", "screenshot_ocr", "mixed"]
        },
        "collection_notes":  {"type": "string",  "nullable": True},
        "data_confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"]
        },
        "observed_telemetry": {
            "type": "object",
            "properties": {
                "memory_pressure_state": {
                    "type": "string",
                    "enum": ["Normal", "Warning", "Critical", "Unknown"]
                },
                "physical_memory_gb":   {"type": "number", "nullable": True},
                "app_memory_gb":        {"type": "number", "nullable": True},
                "wired_memory_gb":      {"type": "number", "nullable": True},
                "compressed_memory_gb": {"type": "number", "nullable": True},
                "cached_files_gb":      {"type": "number", "nullable": True},
                "swap_used_gb":         {"type": "number", "nullable": True}
            },
            "required": [
                "memory_pressure_state",
                "physical_memory_gb",
                "app_memory_gb",
                "wired_memory_gb",
                "compressed_memory_gb",
                "cached_files_gb",
                "swap_used_gb"
            ]
        },
        "active_processes":   {"type": "array", "items": {"type": "string"}},
        "uncertainty_flags":  {"type": "array", "items": {"type": "string"}}
    },
    "required": [
        "event_timestamp",
        "source_file",
        "scenario_label",
        "source_kind",
        "collection_notes",
        "data_confidence",
        "observed_telemetry",
        "active_processes",
        "uncertainty_flags"
    ]
}

def build_telemetry_prompt(
    file_path: Path,
    scenario_label: str | None = None,
    source_kind: str = "terminal_log",
    collection_notes: str | None = None,
) -> str:
    header = "\n".join([
        f"SCENARIO: {scenario_label or ''}",
        f"SOURCE_FILE: {file_path.name}",
        f"SOURCE_KIND: {source_kind}",
        f"COLLECTION_NOTES: {collection_notes or ''}",
    ])
    suffix = file_path.suffix.lower()
    if suffix in ['.png', '.jpg', '.jpeg', '.webp']:
        return f"{header}\n\n--- BEGIN RAW ARTIFACT ---\n[IMAGE ATTACHED]\n--- END RAW ARTIFACT ---"
        
    raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    return (
        f"{header}\n\n"
        "--- BEGIN RAW ARTIFACT ---\n"
        f"{raw_text}\n"
        "--- END RAW ARTIFACT ---"
    )

def run_gemini_parser(
    file_path: Path,
    scenario_label: str | None = None,
    source_kind: str | None = None,
    collection_notes: str | None = None,
) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")
        
    client = genai.Client(api_key=api_key)
    
    prompt_path = BASE_DIR / "prompts" / "gemini_evidence_parser.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    suffix = file_path.suffix.lower()
    if source_kind is None:
        source_kind = "screenshot_ocr" if suffix in ['.png', '.jpg', '.jpeg', '.webp'] else "terminal_log"
        
    artifact_text = build_telemetry_prompt(
        file_path=file_path,
        scenario_label=scenario_label,
        source_kind=source_kind,
        collection_notes=collection_notes,
    )
    
    parts = [types.Part.from_text(text=artifact_text)]
    
    if suffix in ['.png', '.jpg', '.jpeg', '.webp']:
        mime_type = "image/png"
        if suffix in ['.jpg', '.jpeg']:
            mime_type = "image/jpeg"
        elif suffix == '.webp':
            mime_type = "image/webp"
            
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        parts.append(
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        )
        
    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=[
            types.Content(role="user", parts=parts)
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=GEMINI_EVIDENCE_SCHEMA,
            temperature=0.0
        )
    )
    
    record = json.loads(response.text)
    return record

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
            print(f"  Parsing {file.name} with Gemini...")
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
