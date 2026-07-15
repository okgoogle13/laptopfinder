"""Operator-facing ad hoc discovery runner.

Loads a JSON operator config, merges with defaults, then drives the structured
eBay discovery workflow (ebay_hunter) end-to-end.

Usage:
    .venv/bin/python -m laptopfinder.runners.hunt --config config/runs/desktop_replacement.json
    .venv/bin/python -m laptopfinder.runners.hunt --config config/runs/desktop_replacement.json --dry-run

Config file format (JSON object, all keys except `label` are optional):
    label           : human-readable description of this run (required)
    enrich_top      : how many candidates to deep-enrich via Gemini (default 25)
    max_per_query   : Browse API result cap per search query (default 200)
    dry_run         : if true, skip email and state writes (default false)
    no_vision       : if true, disable multimodal VRAM image recovery (default false)
    no_email        : if true, score and persist but never send email (default false)

Required environment (via .env):
    EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, GEMINI_API_KEY
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_DEFAULTS: dict = {
    "enrich_top": 25,
    "max_per_query": 200,
    "dry_run": False,
    "no_vision": False,
    "no_email": False,
}


def load_config(path: Path) -> dict:
    """Read and validate an operator run config JSON file.

    Returns a config dict with all optional keys filled from defaults.
    Raises ValueError on missing file, bad JSON, or missing `label`.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Config must be a JSON object")
    if "label" not in raw:
        raise ValueError("Config missing required key: 'label'")
    return {**_DEFAULTS, **raw}


def config_to_args(cfg: dict) -> argparse.Namespace:
    """Translate a loaded config dict into the Namespace expected by ebay_hunter.run()."""
    return argparse.Namespace(
        max_per_query=int(cfg["max_per_query"]),
        enrich_top=int(cfg["enrich_top"]),
        model=cfg.get("model"),
        no_vision=bool(cfg["no_vision"]),
        no_email=bool(cfg["no_email"]),
        dry_run=bool(cfg["dry_run"]),
        no_enrich=False,
    )


def run(config_path: Path, dry_run_override: bool = False) -> int:
    cfg = load_config(config_path)
    if dry_run_override:
        cfg["dry_run"] = True

    print(f"[hunt] Run: {cfg['label']}", flush=True)
    if cfg["dry_run"]:
        print("[hunt] dry-run — no email, no state write", flush=True)

    from laptopfinder.runners.ebay_hunter import run as _hunter_run

    return _hunter_run(config_to_args(cfg))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m laptopfinder.runners.hunt",
        description="Target JSON-driven ad hoc eBay AU discovery run.",
    )
    p.add_argument("--config", required=True, metavar="PATH",
                   help="Path to operator run config JSON file")
    p.add_argument("--dry-run", action="store_true",
                   help="Override: skip email and state write regardless of config")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return run(Path(args.config), dry_run_override=args.dry_run)
    except ValueError as exc:
        print(f"[hunt] ERROR: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
