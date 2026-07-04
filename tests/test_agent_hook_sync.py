import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agent_hook_configs_are_synced() -> None:
    script = ROOT / "scripts" / "sync_agent_hooks.py"
    exit_code = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=ROOT,
        check=False,
    ).returncode
    assert exit_code == 0
