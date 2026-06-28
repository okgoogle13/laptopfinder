"""Smoke tests for the Evidence Pipeline Runner.

Validates that:
  - run_gemini_parser makes the expected Google GenAI Client calls.
  - The schema sent to Gemini is the hardcoded GEMINI_EVIDENCE_SCHEMA containing event_timestamp and source_file.
  - The record returned perfectly matches the JSON parsed from the model output.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import json

from laptopfinder.runners.evidence_pipeline import run_gemini_parser, GEMINI_EVIDENCE_SCHEMA


@pytest.fixture
def mock_genai_client():
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Mock response from generate_content, simulating the new model output with timestamps and files
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "event_timestamp": "2026-06-28T12:00:00Z",
            "source_file": "telemetry_test.log",
            "scenario_label": "antigravity_gemini_coding",
            "source_kind": "terminal_log",
            "collection_notes": "Test run",
            "data_confidence": "high",
            "observed_telemetry": {
                "memory_pressure_state": "Normal",
                "physical_memory_gb": 16.0,
                "app_memory_gb": 8.0,
                "wired_memory_gb": 4.0,
                "compressed_memory_gb": 1.0,
                "cached_files_gb": 2.0,
                "swap_used_gb": 0.0
            },
            "active_processes": ["Docker"],
            "uncertainty_flags": []
        })
        mock_client.models.generate_content.return_value = mock_response
        
        yield mock_client


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key_for_testing"})
def test_run_gemini_parser_success(mock_genai_client, tmp_path):
    # Create a dummy telemetry file
    dummy_file = tmp_path / "telemetry_test.log"
    dummy_file.write_text("dummy log content")
    
    # Run the parser
    record = run_gemini_parser(dummy_file)
    
    # Check that client was called
    mock_genai_client.models.generate_content.assert_called_once()
    
    # Assert timestamp and source file are present from the model
    assert record.get("event_timestamp") == "2026-06-28T12:00:00Z"
    assert record.get("source_file") == "telemetry_test.log"
    assert record.get("data_confidence") == "high"
    
    # Check that schema matches GEMINI_EVIDENCE_SCHEMA exactly
    call_args = mock_genai_client.models.generate_content.call_args[1]
    config = call_args.get("config")
    assert config is not None
    response_schema = config.response_schema if hasattr(config, "response_schema") else config.get("response_schema")
    assert "event_timestamp" in response_schema.get("properties", {})
    assert "source_file" in response_schema.get("properties", {})
    assert response_schema == GEMINI_EVIDENCE_SCHEMA


@patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key_for_testing"})
@pytest.mark.parametrize(
    "flags,expected_confidence",
    [
        ([], "high"),
        (["Flag 1"], "medium"),
        (["Flag 1", "Flag 2"], "medium"),
        (["Flag 1", "Flag 2", "Flag 3"], "low"),
    ],
)
def test_data_confidence_passthrough(mock_genai_client, tmp_path, flags, expected_confidence):
    """
    Tests that the data_confidence returned by the model is passed through unmodified.
    The new pipeline no longer recalculates it in python.
    """
    # Override response with specific confidence and flags
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "event_timestamp": "2026-06-28T12:00:00Z",
        "source_file": "telemetry_test.log",
        "scenario_label": "antigravity_gemini_coding",
        "source_kind": "terminal_log",
        "collection_notes": "Test run",
        "data_confidence": expected_confidence,
        "observed_telemetry": {
            "memory_pressure_state": "Normal",
            "physical_memory_gb": 16.0,
            "app_memory_gb": 8.0,
            "wired_memory_gb": 4.0,
            "compressed_memory_gb": 1.0,
            "cached_files_gb": 2.0,
            "swap_used_gb": 0.0
        },
        "active_processes": ["Docker"],
        "uncertainty_flags": flags
    })
    mock_genai_client.models.generate_content.return_value = mock_response
    
    dummy_file = tmp_path / "telemetry_test.log"
    dummy_file.write_text("dummy")
    
    record = run_gemini_parser(dummy_file)
    assert record["data_confidence"] == expected_confidence
    assert record["uncertainty_flags"] == flags


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
