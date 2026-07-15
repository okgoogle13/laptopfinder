import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

SRL_PATH = str(_REPO_ROOT / "config" / "static_reference_layer.json")

PROMPT_FILES = [
    str(_REPO_ROOT / "prompts" / "comet_discovery_agent.txt"),
    str(_REPO_ROOT / "archive" / "prompts" / "alternative_silicon_gemini.txt"),
    str(_REPO_ROOT / "archive" / "prompts" / "alternative_silicon_perplexity.txt"),
]


def load_srl(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SRL not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def build_substitutions(srl: dict) -> dict[str, str]:
    # target_gpus is a dict keyed by GPU name; watch_list is a list of dicts with a "name" key
    gpu_names = list(srl.get("target_gpus", {}).keys())
    watch_names = [
        entry["name"]
        for entry in srl.get("watch_list", [])
        if isinstance(entry, dict) and "name" in entry
    ]
    targets_block = "\n".join(f"- {name}" for name in gpu_names + watch_names)
    gpu_list_block = "\n".join(f"- {name}" for name in gpu_names)

    uma = srl.get("uma_platforms", {})
    return {
        "TARGETS": targets_block,
        "TARGET_GPU_LIST": gpu_list_block,
        "UMA_MIN_RAM_GB": str(uma.get("min_total_ram_gb_to_shortlist", "")),
        "UMA_CHIP_PATTERNS": ", ".join(uma.get("chip_patterns", [])),
    }


def inject_file(path: str, substitutions: dict[str, str], *, out_path: str | None = None) -> int:
    """Replace content between BEGIN/END_INJECT sentinel pairs.

    Uses lookbehind/lookahead so the BEGIN/END markers are never consumed.
    Uses a repl callable so value strings are never interpreted as regex
    backreferences — safe for any GPU name content.
    Only writes when content actually changes (idempotent from git's perspective).

    out_path: write rendered output here instead of mutating the source file.
    Returns the number of blocks replaced.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    original = p.read_text(encoding="utf-8")
    content = original
    count = 0

    for key, value in substitutions.items():
        sentinel_begin = f"<!-- BEGIN_INJECT:{key} -->"
        sentinel_end = f"<!-- END_INJECT:{key} -->"

        if sentinel_begin not in content:
            continue

        pattern = (
            rf"(?<={re.escape(sentinel_begin)})"
            rf".*?"
            rf"(?={re.escape(sentinel_end)})"
        )
        body = f"\n{value}\n"
        new_content, n = re.subn(pattern, lambda _: body, content, flags=re.DOTALL)
        if n:
            content = new_content
            count += n

    dest = Path(out_path) if out_path else p
    dest.parent.mkdir(parents=True, exist_ok=True)
    if content != original or (out_path and not dest.exists()):
        dest.write_text(content, encoding="utf-8")

    return count


def _missing_sentinels(path: str, substitutions: dict[str, str]) -> list[str]:
    """Return keys whose BEGIN_INJECT sentinel is absent from the file."""
    p = Path(path)
    if not p.exists():
        return list(substitutions.keys())
    content = p.read_text(encoding="utf-8")
    return [k for k in substitutions if f"<!-- BEGIN_INJECT:{k} -->" not in content]


def main(out_dir: str | None = None, check: bool = False) -> None:
    """Inject SRL values into prompt sentinel pairs.

    out_dir: write rendered files here instead of mutating tracked source files.
    check:   exit 1 if any file would change (dry-run for CI).
    """
    srl = load_srl(SRL_PATH)
    substitutions = build_substitutions(srl)

    any_would_change = False

    for src_path in PROMPT_FILES:
        # Report missing sentinels before touching the file so the warning
        # always surfaces even if the replacement count is zero.
        missing = _missing_sentinels(src_path, substitutions)
        for key in missing:
            print(
                f"WARN: {Path(src_path).name}: sentinel '{key}' not found — value not injected",
                file=sys.stderr,
            )

        if check:
            # Simulate without writing: read file, apply in memory, compare
            p = Path(src_path)
            content = p.read_text(encoding="utf-8") if p.exists() else ""
            from io import StringIO
            # Re-use inject_file via a temp file approach would mutate; use manual check
            _, count, _ = _simulate(content, substitutions)
            if count:
                any_would_change = True
                print(f"WOULD CHANGE: {Path(src_path).name} ({count} block(s))")
            else:
                print(f"UP TO DATE:   {Path(src_path).name}")
            continue

        out_path = str(Path(out_dir) / Path(src_path).name) if out_dir else None
        n = inject_file(src_path, substitutions, out_path=out_path)
        dest_name = Path(out_path).name if out_path else Path(src_path).name
        print(f"{dest_name}: {n} block(s) updated")

    if check and any_would_change:
        sys.exit(1)


def _simulate(content: str, substitutions: dict[str, str]) -> tuple[str, int, list[str]]:
    """Apply substitutions in memory only — no I/O. Returns (new_content, count, missing)."""
    count = 0
    missing: list[str] = []
    for key, value in substitutions.items():
        sentinel_begin = f"<!-- BEGIN_INJECT:{key} -->"
        sentinel_end = f"<!-- END_INJECT:{key} -->"
        if sentinel_begin not in content:
            missing.append(key)
            continue
        pattern = (
            rf"(?<={re.escape(sentinel_begin)})"
            rf".*?"
            rf"(?={re.escape(sentinel_end)})"
        )
        body = f"\n{value}\n"
        new_content, n = re.subn(pattern, lambda _: body, content, flags=re.DOTALL)
        if n:
            content = new_content
            count += n
    return content, count, missing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject SRL values into prompt sentinel pairs")
    parser.add_argument(
        "--out-dir",
        default=None,
        help=(
            "Write rendered files to this directory instead of mutating the tracked "
            "source files. Useful for separating generated artifacts from templates."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any file would change (dry-run for CI). Does not write.",
    )
    args = parser.parse_args()
    main(out_dir=args.out_dir, check=args.check)
