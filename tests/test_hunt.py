"""Tests for the operator-facing hunt runner (runners/hunt.py)."""

import argparse
import json
import pytest
from pathlib import Path

from laptopfinder.runners.hunt import load_config, config_to_args, _DEFAULTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_config(tmp_path) -> Path:
    p = tmp_path / "run.json"
    p.write_text(json.dumps({"label": "test run"}), encoding="utf-8")
    return p


@pytest.fixture()
def full_config(tmp_path) -> Path:
    p = tmp_path / "run.json"
    p.write_text(json.dumps({
        "label": "full run",
        "enrich_top": 10,
        "max_per_query": 50,
        "dry_run": True,
        "no_vision": True,
        "no_email": True,
    }), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_requires_label(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"enrich_top": 5}), encoding="utf-8")
    with pytest.raises(ValueError, match="label"):
        load_config(p)


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        load_config(tmp_path / "nonexistent.json")


def test_load_config_bad_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_config(p)


def test_load_config_non_object(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_config(p)


def test_load_config_minimal_fills_defaults(minimal_config):
    cfg = load_config(minimal_config)
    assert cfg["label"] == "test run"
    for key, val in _DEFAULTS.items():
        assert cfg[key] == val, f"Default for {key!r} not applied"


def test_load_config_overrides_defaults(full_config):
    cfg = load_config(full_config)
    assert cfg["enrich_top"] == 10
    assert cfg["max_per_query"] == 50
    assert cfg["dry_run"] is True
    assert cfg["no_vision"] is True
    assert cfg["no_email"] is True


def test_load_config_unknown_keys_preserved(tmp_path):
    p = tmp_path / "extra.json"
    p.write_text(json.dumps({"label": "x", "custom_note": "hello"}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg["custom_note"] == "hello"


# ---------------------------------------------------------------------------
# config_to_args
# ---------------------------------------------------------------------------

def test_config_to_args_produces_namespace(minimal_config):
    cfg = load_config(minimal_config)
    ns = config_to_args(cfg)
    assert isinstance(ns, argparse.Namespace)


def test_config_to_args_default_values(minimal_config):
    cfg = load_config(minimal_config)
    ns = config_to_args(cfg)
    assert ns.enrich_top == 25
    assert ns.max_per_query == 200
    assert ns.dry_run is False
    assert ns.no_vision is False
    assert ns.no_email is False
    assert ns.no_enrich is False
    assert ns.model is None


def test_config_to_args_overrides(full_config):
    cfg = load_config(full_config)
    ns = config_to_args(cfg)
    assert ns.enrich_top == 10
    assert ns.max_per_query == 50
    assert ns.dry_run is True
    assert ns.no_vision is True
    assert ns.no_email is True


def test_config_to_args_model_passthrough(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(json.dumps({"label": "x", "model": "gemini-pro"}), encoding="utf-8")
    cfg = load_config(p)
    ns = config_to_args(cfg)
    assert ns.model == "gemini-pro"
