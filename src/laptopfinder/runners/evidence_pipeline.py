import argparse
import hashlib
import json
import shutil
from pathlib import Path

from dotenv import load_dotenv
from laptopfinder.core import validate

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "evidence"
RAW_DIR = DATA_DIR / "raw"
ARCHIVE_DIR = DATA_DIR / "archive"
DB_FILE = DATA_DIR / "aggregated.jsonl"
HANDOFF_FILE = DATA_DIR / "claude_handoff.txt"
PROMPTS_DIR = DATA_DIR / "prompts_for_gemini"
PARSED_DIR = DATA_DIR / "parsed"
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
                "swap_used_gb":         {"type": "number", "nullable": True},
                "cpu_telemetry": {
                    "type": "object", "nullable": True,
                    "properties": {
                        "cpu_user_pct":     {"type": "number",  "nullable": True},
                        "cpu_sys_pct":      {"type": "number",  "nullable": True},
                        "cpu_idle_pct":     {"type": "number",  "nullable": True},
                        "cpu_cores_active": {"type": "number",  "nullable": True},
                        "load_pattern":     {"type": "string",  "nullable": True,
                                             "enum": ["spiky", "sustained", "idle"]}
                    }
                },
                "gpu_telemetry": {
                    "type": "object", "nullable": True,
                    "properties": {
                        "gpu_residency_pct": {"type": "number",  "nullable": True},
                        "gpu_freq_mhz":      {"type": "number",  "nullable": True},
                        "gpu_power_mw":      {"type": "number",  "nullable": True},
                        "cpu_die_temp_c":    {"type": "number",  "nullable": True},
                        "fan_rpm":           {"type": "number",  "nullable": True},
                        "throttle_observed": {"type": "boolean", "nullable": True}
                    }
                },
                "inference_telemetry": {
                    "type": "object", "nullable": True,
                    "properties": {
                        "model_name":               {"type": "string",  "nullable": True},
                        "model_params_b":           {"type": "number",  "nullable": True},
                        "model_quant":              {"type": "string",  "nullable": True},
                        "context_length":           {"type": "integer", "nullable": True},
                        "tokens_per_sec_short_ctx": {"type": "number",  "nullable": True},
                        "tokens_per_sec_long_ctx":  {"type": "number",  "nullable": True},
                        "model_peak_rss_gb":        {"type": "number",  "nullable": True},
                        "gpu_used_for_inference":   {"type": "boolean", "nullable": True}
                    }
                }
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


def validate_evidence_record(record: dict) -> dict:
    validate(record, "evidence_normalized.schema.json")
    return record

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

def generate_gemini_prompt(
    file_path: Path,
    scenario_label: str | None = None,
    source_kind: str | None = None,
    collection_notes: str | None = None,
) -> None:
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
    
    out_name = f"{file_path.stem}_prompt.txt"
    out_file = PROMPTS_DIR / out_name
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("=== SYSTEM INSTRUCTIONS ===\n")
        f.write(system_prompt)
        f.write("\n\n=== USER MESSAGE ===\n")
        f.write(artifact_text)

def _prompt_hash(prompt_path: Path) -> str:
    """SHA-256 of the prompt file, hex-encoded."""
    return hashlib.sha256(prompt_path.read_bytes()).hexdigest()


def generate_claude_handoff(aggregated_data: list) -> None:
    prompt_file = BASE_DIR / "prompts" / "claude_evidence_analyzer.txt"
    instructions = (
        prompt_file.read_text(encoding="utf-8")
        if prompt_file.exists()
        else "Analyze this telemetry..."
    )

    # Staleness check: compare current prompt hash against the hash recorded
    # at the last handoff generation.  Warn if they differ so the caller knows
    # to regenerate rather than re-use a cached handoff.txt.
    hash_file = DATA_DIR / ".claude_prompt.hash"
    current_hash = _prompt_hash(prompt_file) if prompt_file.exists() else ""
    if hash_file.exists():
        recorded_hash = hash_file.read_text(encoding="utf-8").strip()
        if recorded_hash and recorded_hash != current_hash:
            print(
                "  WARNING: claude_evidence_analyzer.txt has changed since the last "
                "handoff was generated.  The new handoff will embed the updated prompt."
            )
    hash_file.write_text(current_hash, encoding="utf-8")

    # Context Compaction:
    # 1. Keep all high/medium confidence records
    high_med = [r for r in aggregated_data if r.get("data_confidence") in ("high", "medium")]
    # 2. Keep up to 4 sparse/low confidence records to show the pattern
    low_sparse = [r for r in aggregated_data if r.get("data_confidence") not in ("high", "medium")]
    compacted_data = high_med + low_sparse[:4]

    # Serialize compactly (no unnecessary whitespace)
    compact_json = json.dumps(compacted_data, separators=(',', ':'))

    # Check for previous targets.json
    targets_file = DATA_DIR / "targets.json"
    previous_targets_block = ""
    if targets_file.exists():
        try:
            prev_targets = json.loads(targets_file.read_text(encoding="utf-8"))
            prev_targets_compact = json.dumps(prev_targets, separators=(',', ':'))
            previous_targets_block = f"=== PREVIOUS TARGETS ===\n{prev_targets_compact}\n\n"
        except Exception:
            pass

    payload = (
        f"{instructions}\n\n"
        f"{previous_targets_block}"
        f"=== AGGREGATED TELEMETRY ===\n"
        f"{compact_json}\n"
    )
    HANDOFF_FILE.write_text(payload, encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence Pipeline runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip archiving and handoff generation.",
    )
    parser.add_argument(
        "--force-handoff",
        action="store_true",
        help="Generate claude_handoff.txt from all aggregated records regardless of PROMOTION_THRESHOLD.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate aggregated.jsonl and remove the prompt hash sidecar, then exit.  "
             "Use this to start a fresh pipeline run without historical records.",
    )
    args = parser.parse_args()

    # --reset: wipe the DB and hash sidecar so the next run starts clean.
    if args.reset:
        if DB_FILE.exists():
            DB_FILE.unlink()
            DB_FILE.touch()
            print(f"Reset: truncated {DB_FILE.relative_to(BASE_DIR)}")
        else:
            print(f"Reset: {DB_FILE.relative_to(BASE_DIR)} did not exist — nothing to truncate.")
        hash_file = DATA_DIR / ".claude_prompt.hash"
        if hash_file.exists():
            hash_file.unlink()
            print(f"Reset: removed prompt hash sidecar {hash_file.name}")
        print("Done. Run `make evidence-run` to restart the pipeline.")
        return

    # Step 1: Generate Gemini Prompts for any raw files
    raw_files = sorted(RAW_DIR.glob("*.*"))
    if raw_files:
        print(f"Found {len(raw_files)} new file(s) in /raw. Generating Gemini prompts...")
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        for file in raw_files:
            try:
                generate_gemini_prompt(file)
                print(f"  Generated prompt: {PROMPTS_DIR / (file.stem + '_prompt.txt')}")
                if not args.dry_run:
                    shutil.move(str(file), ARCHIVE_DIR / file.name)
            except Exception as exc:
                print(f"  ERROR processing {file.name}: {exc}")
        
        print("\n=== GEMINI PROMPTS READY ===")
        print("1. Open the Gemini web UI.")
        print(f"2. Paste the contents of each file in {PROMPTS_DIR.relative_to(BASE_DIR)}.")
        print(f"3. Save the resulting JSON responses into {PARSED_DIR.relative_to(BASE_DIR)}.")
        print("4. Re-run `make evidence-run` to aggregate the parsed records.")
        print("============================\n")
        return # Halt pipeline to wait for user's manual parsing
    
    # Step 2: Aggregate parsed JSON outputs from Gemini
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    parsed_files = sorted(PARSED_DIR.glob("*.json"))
    records_total = (
        sum(1 for line in DB_FILE.read_text(encoding="utf-8").splitlines() if line.strip())
        if DB_FILE.exists()
        else 0
    )

    if parsed_files:
        print(f"Found {len(parsed_files)} parsed file(s) in /parsed. Aggregating...")
        with DB_FILE.open("a", encoding="utf-8") as db:
            for file in parsed_files:
                try:
                    record = validate_evidence_record(
                        json.loads(file.read_text(encoding="utf-8"))
                    )
                    db.write(json.dumps(record) + "\n")
                    records_total += 1
                    if not args.dry_run:
                        shutil.move(str(file), ARCHIVE_DIR / file.name)
                        print(f"  Aggregated & Archived {file.name}.")
                    else:
                        print(f"  [DRY-RUN] Would aggregate & archive {file.name}.")
                except Exception as exc:
                    print(f"  ERROR processing {file.name}: {exc}")

    print(f"DB now has {records_total} record(s). Threshold is {PROMOTION_THRESHOLD}.")
    if args.force_handoff or records_total >= PROMOTION_THRESHOLD:
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
