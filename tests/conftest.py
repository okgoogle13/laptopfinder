"""Ensure src/ is importable for tests without requiring a prior
`pip install -e .` step. This keeps the thin-slice harness runnable
with a bare `pytest` invocation from the repo root."""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
