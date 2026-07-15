#!/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
PLAN_FILE="${1:-}"

if [[ -z "$PLAN_FILE" ]]; then
    PLAN_FILE="$(
        cd "$ROOT"
        .venv/bin/python - <<'PY'
from pathlib import Path

plans_dir = Path.home() / ".claude" / "plans"
plans = list(plans_dir.glob("*.md"))
if not plans:
    raise SystemExit(1)

latest = max(plans, key=lambda path: path.stat().st_mtime)
print(latest)
PY
    )"
fi

if [[ ! -f "$PLAN_FILE" ]]; then
    echo "ERROR: Plan file not found: $PLAN_FILE" >&2
    exit 1
fi

command -v codex >/dev/null || {
    echo "ERROR: codex CLI not found on PATH" >&2
    exit 1
}

[[ -f "$HOME/.codex/peer-review.config.toml" ]] || {
    echo "ERROR: missing ~/.codex/peer-review.config.toml" >&2
    echo "Run Codex peer-review init first." >&2
    exit 1
}

PROMPT_FILE="$(mktemp -t laptopfinder-peer-review-prompt)"
OUTPUT_FILE="$(mktemp -t laptopfinder-peer-review-output)"
LOG_FILE="$(mktemp -t laptopfinder-peer-review-log)"

trap 'rm -f "$PROMPT_FILE" "$OUTPUT_FILE" "$LOG_FILE"' EXIT

.venv/bin/python - "$PLAN_FILE" "$PROMPT_FILE" <<'PY'
from pathlib import Path
import sys

plan_path = Path(sys.argv[1])
prompt_path = Path(sys.argv[2])
plan_text = plan_path.read_text()

prompt = f"""You are an independent peer reviewer for the laptopfinder repository.

Review the implementation plan below before execution.

Focus on:
- firewall enforcement in Python
- schema-owned validation staying in JSON Schema
- SRL-owned thresholds, lists, and weights staying in static_reference_layer.json
- fixtures required for logic changes
- null-not-fabricate behavior
- flat Python and standard exceptions
- make test and relevant fixtures in verification
- hardware claim grounding
- scope creep

Return a terse verdict:
- APPROVED
or
- CHANGES_REQUESTED: <1-3 concrete fixes>

Plan:
{plan_text}
"""

prompt_path.write_text(prompt)
PY

if ! codex exec --profile peer-review --sandbox read-only -o "$OUTPUT_FILE" < "$PROMPT_FILE" >"$LOG_FILE" 2>&1; then
    cat "$LOG_FILE" >&2
    exit 1
fi

if grep -qE '(^|[^A-Z])APPROVED([^A-Z]|$)' "$OUTPUT_FILE"; then
    cat "$OUTPUT_FILE"
    exit 0
fi

cat "$OUTPUT_FILE" >&2
exit 1
