import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agent_hook_configs_are_synced() -> None:
    script = ROOT / "scripts" / "sync_agent_hooks.py"
    exit_code = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), str(script), "--check"],
        cwd=ROOT,
        check=False,
    ).returncode
    assert exit_code == 0
