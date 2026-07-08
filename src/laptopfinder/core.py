"""laptopfinder - thin-slice extraction/analysis harness."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
import jsonschema

_FORBIDDEN_FACT_KEYS = {"exact_model_name", "cpu", "gpu", "ram", "storage", "vram_capacity", "stated_condition", "total_system_ram", "egpu_model", "touchscreen_digitizer"}
_FACT_KEYS = ("exact_model_name", "cpu", "gpu", "ram", "storage", "vram_capacity", "stated_condition", "total_system_ram", "egpu_model", "touchscreen_digitizer")

def load_schema(name: str) -> dict[str, Any]:
    with (Path(__file__).parent / "schemas" / name).open("r", encoding="utf-8") as f:
        return json.load(f)

def validate(payload: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema validation failed for {schema_name}: {e.message}") from e

def run_stage1(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(candidates, list):
        raise TypeError("Stage 1 output must be a JSON array")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise TypeError("Each candidate must be a dict")
        forbidden = _FORBIDDEN_FACT_KEYS.intersection(candidate.keys())
        if forbidden:
            raise ValueError(f"Stage 1 firewall violation. Fact keys found: {forbidden}")
    
    validate(candidates, "stage1.discovery.schema.json")
    return candidates

def run_stage1_from_fixture(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return run_stage1(json.load(f))

def run_stage2(handoff: dict[str, Any], text: str, analysis: dict[str, Any]) -> dict[str, Any]:
    validate(handoff, "stage1a.handoff.schema.json")
    validate(analysis, "stage2.analysis.schema.json")
    
    # 1. Data Integrity: Salvaged hardware chassis check (parts only, missing motherboard etc.)
    from .decide import load_ref
    ref = load_ref()
    exclusion_pattern = ref.get("data_integrity", {}).get("exclusion_regex")
    if exclusion_pattern:
        title = analysis.get("metadata", {}).get("listing_title", "")
        # Check both title and full listing text
        if re.search(exclusion_pattern, title) or re.search(exclusion_pattern, text):
            raise ValueError("Data integrity violation: salvaged hardware or parts-only listing detected")

    extracted = analysis.get("extracted_data", {})
    text_lower = text.lower()

    violations = []
    for key in _FACT_KEYS:
        value = extracted.get(key)
        if not value or not isinstance(value, str):
            continue
        pattern = r'\b' + re.escape(value.lower().strip()) + r'\b'
        if not re.search(pattern, text_lower):
            violations.append((key, value))

    if violations:
        raise ValueError(f"Stage 2 firewall violation. Facts not explicitly in text: {violations}")
        
    return analysis

def run_stage2_from_fixture(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return run_stage2(payload["handoff_packet"], payload["full_listing_text"], payload["analysis_output"])


def run_pipeline(stage1_fixture: str | Path, stage2_fixture: str | Path) -> dict[str, Any]:
    """Run Stage 1 (discovery) then Stage 2 (analysis + decision) in sequence.

    Stage 1 and Stage 2 use separate fixtures because Stage 1 only ever sees
    raw listing text/candidates, while Stage 2 expects the Stage 1A handoff
    packet plus full listing text bundled together. This mirrors the real
    pipeline: Stage 1 output is never passed directly into Stage 2 code,
    only into the handoff packet a human/agent assembles in between.
    """
    from .decide import decide

    stage1_result = run_stage1_from_fixture(stage1_fixture)
    analysis = run_stage2_from_fixture(stage2_fixture)
    decision = decide(analysis)
    return {
        "stage1_candidates": stage1_result,
        "stage2_analysis": analysis,
        "decision": decision,
    }

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m laptopfinder.core",
        description="laptopfinder Stage 1 / Stage 2 / decision CLI",
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    p_stage1 = subparsers.add_parser("stage1", help="Run Stage 1 discovery on a fixture")
    p_stage1.add_argument("fixture", help="Path to a Stage 1 fixture JSON file")

    p_stage2 = subparsers.add_parser("stage2", help="Run Stage 2 analysis on a fixture")
    p_stage2.add_argument("fixture", help="Path to a Stage 2 fixture JSON file")

    p_decide = subparsers.add_parser("decide", help="Run Stage 2 analysis and produce a decision")
    p_decide.add_argument("fixture", help="Path to a Stage 2 fixture JSON file")

    p_pipeline = subparsers.add_parser(
        "pipeline", help="Run Stage 1 then Stage 2+decide sequentially"
    )
    p_pipeline.add_argument("stage1_fixture", help="Path to a Stage 1 fixture JSON file")
    p_pipeline.add_argument("stage2_fixture", help="Path to a Stage 2 fixture JSON file")

    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        if args.mode == "stage1":
            result = run_stage1_from_fixture(args.fixture)
        elif args.mode == "stage2":
            result = run_stage2_from_fixture(args.fixture)
        elif args.mode == "decide":
            from .decide import decide
            analysis = run_stage2_from_fixture(args.fixture)
            result = {"analysis": analysis, "decision": decide(analysis)}

        else:
            result = run_pipeline(args.stage1_fixture, args.stage2_fixture)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

