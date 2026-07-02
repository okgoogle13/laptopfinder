"""Smoke tests for the Evidence Pipeline Runner.

Validates that:
  - generate_gemini_prompt correctly reads instructions and writes prompt files.
  - generate_claude_handoff compacts data and serializes targets.
  - The schema for Gemini matches the canonical schema keys.
"""
from pathlib import Path
from unittest.mock import patch
import json

from laptopfinder.runners.evidence_pipeline import (
    generate_gemini_prompt,
    generate_claude_handoff,
    GEMINI_EVIDENCE_SCHEMA,
)


def test_generate_gemini_prompt_success(tmp_path):
    temp_prompts_dir = tmp_path / "prompts_for_gemini"
    temp_prompts_dir.mkdir()
    
    with patch("laptopfinder.runners.evidence_pipeline.PROMPTS_DIR", temp_prompts_dir):
        dummy_file = tmp_path / "telemetry_test.log"
        dummy_file.write_text("my raw log text content")
        
        generate_gemini_prompt(
            dummy_file,
            scenario_label="test_scenario",
            source_kind="terminal_log",
            collection_notes="Test notes"
        )
        
        expected_prompt_file = temp_prompts_dir / "telemetry_test_prompt.txt"
        assert expected_prompt_file.exists()
        content = expected_prompt_file.read_text(encoding="utf-8")
        assert "=== SYSTEM INSTRUCTIONS ===" in content
        assert "=== USER MESSAGE ===" in content
        assert "SCENARIO: test_scenario" in content
        assert "SOURCE_FILE: telemetry_test.log" in content
        assert "SOURCE_KIND: terminal_log" in content
        assert "COLLECTION_NOTES: Test notes" in content
        assert "my raw log text content" in content


def test_generate_claude_handoff(tmp_path):
    temp_handoff = tmp_path / "claude_handoff.txt"
    temp_targets = tmp_path / "targets.json"
    
    # Write a dummy targets.json
    dummy_targets = {"system_memory_gb": {"min": 16}}
    temp_targets.write_text(json.dumps(dummy_targets))
    
    # Mock data with different confidence levels
    aggregated_data = [
        {"data_confidence": "high", "scenario_label": "h1"},
        {"data_confidence": "medium", "scenario_label": "m1"},
        {"data_confidence": "low", "scenario_label": "l1"},
        {"data_confidence": "low", "scenario_label": "l2"},
        {"data_confidence": "low", "scenario_label": "l3"},
        {"data_confidence": "low", "scenario_label": "l4"},
        {"data_confidence": "low", "scenario_label": "l5"}, # should be dropped since we only keep up to 4 low confidence records
    ]
    
    with patch("laptopfinder.runners.evidence_pipeline.HANDOFF_FILE", temp_handoff), \
         patch("laptopfinder.runners.evidence_pipeline.DATA_DIR", tmp_path):
        
        generate_claude_handoff(aggregated_data)
        
        assert temp_handoff.exists()
        content = temp_handoff.read_text(encoding="utf-8")
        
        # Verify instructions are loaded
        assert "You are an evidence-based hardware planning assistant" in content
        
        # Verify previous targets are included
        assert "=== PREVIOUS TARGETS ===" in content
        assert '{"system_memory_gb":{"min":16}}' in content
        
        # Verify telemetry is compacted (only 4 low confidence records)
        assert "=== AGGREGATED TELEMETRY ===" in content
        # Parse the JSON part
        telemetry_part = content.split("=== AGGREGATED TELEMETRY ===\n")[1].strip()
        parsed_telemetry = json.loads(telemetry_part)
        
        # Should have high, medium, and 4 low confidence records (total 6)
        assert len(parsed_telemetry) == 6
        scenarios = [r["scenario_label"] for r in parsed_telemetry]
        assert "h1" in scenarios
        assert "m1" in scenarios
        assert "l1" in scenarios
        assert "l4" in scenarios
        assert "l5" not in scenarios  # Dropped due to context compaction


def test_gemini_schema_keys_match_canonical():
    """GEMINI_EVIDENCE_SCHEMA is a Gemini-specific projection (uses 'nullable'
    instead of JSON Schema's '"type": ["string", "null"]'). This test ensures
    its top-level and nested property keys stay in sync with the canonical
    evidence_normalized.schema.json file."""
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "src" / "laptopfinder" / "schemas" / "evidence_normalized.schema.json"
    )
    canonical = json.loads(schema_path.read_text(encoding="utf-8"))

    assert set(GEMINI_EVIDENCE_SCHEMA["properties"].keys()) == set(
        canonical["properties"].keys()
    ), "Top-level property keys drifted between inline schema and JSON file"

    assert set(
        GEMINI_EVIDENCE_SCHEMA["properties"]["observed_telemetry"]["properties"].keys()
    ) == set(
        canonical["properties"]["observed_telemetry"]["properties"].keys()
    ), "observed_telemetry property keys drifted between inline schema and JSON file"
