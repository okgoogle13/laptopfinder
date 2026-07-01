#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "config" / "agent_hooks.json"
CLAUDE_SETTINGS_PATH = ROOT / ".claude" / "settings.json"
CLAUDE_LOCAL_SETTINGS_PATH = ROOT / ".claude" / "settings.local.json"
CODEX_HOOKS_PATH = ROOT / ".codex" / "hooks.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def dump_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def merge_hooks(*hook_maps: dict) -> dict:
    merged: dict[str, list] = {}
    for hook_map in hook_maps:
        for event_name, entries in hook_map.items():
            merged.setdefault(event_name, []).extend(entries)
    return merged


def render_targets(spec: dict) -> dict[Path, str]:
    shared_hooks = spec["shared_hooks"]
    local_hooks = spec["local_hooks"]
    return {
        CLAUDE_SETTINGS_PATH: dump_json(
            {
                "enabledPlugins": spec["claude_enabled_plugins"],
                "hooks": shared_hooks,
            }
        ),
        CLAUDE_LOCAL_SETTINGS_PATH: dump_json(
            {
                "permissions": spec["claude_permissions"],
                "hooks": local_hooks,
            }
        ),
        CODEX_HOOKS_PATH: dump_json(
            {
                "hooks": merge_hooks(shared_hooks, local_hooks),
            }
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Claude/Codex hook config from a single canonical spec."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if generated files are out of sync.",
    )
    args = parser.parse_args()

    spec = load_json(SPEC_PATH)
    rendered_targets = render_targets(spec)
    mismatches: list[Path] = []

    for path, expected in rendered_targets.items():
        actual = path.read_text() if path.exists() else None
        if actual != expected:
            mismatches.append(path)
            if not args.check:
                path.write_text(expected)

    if args.check and mismatches:
        for path in mismatches:
            print(f"Out of sync: {path.relative_to(ROOT)}", file=sys.stderr)
        return 1

    if not args.check:
        for path in rendered_targets:
            print(f"Synced {path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
