#!/usr/bin/env bash
# Stop hook: enforce a "Next steps" section on substantive assistant replies.
# Reads Stop hook JSON on stdin, inspects the last assistant message in the
# transcript, and blocks (exit 2) if the reply is substantive but missing
# a Next steps section.

INPUT=$(cat)

python3 - "$INPUT" <<'PYEOF'
import json
import sys

raw = sys.argv[1]
payload = json.loads(raw)
transcript_path = payload.get("transcript_path", "")

try:
    with open(transcript_path, "r") as f:
        lines = f.readlines()
except (FileNotFoundError, OSError):
    sys.exit(0)

last_assistant_text = None
last_entry_was_tool_use = False

for line in reversed(lines):
    line = line.strip()
    if not line:
        continue
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue

    message = entry.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        continue

    content = message.get("content")
    if not isinstance(content, list):
        continue

    text_blocks = [b.get("text", "") for b in content if b.get("type") == "text"]
    tool_blocks = [b for b in content if b.get("type") == "tool_use"]

    if text_blocks:
        last_assistant_text = "\n".join(text_blocks).strip()
    elif tool_blocks:
        last_entry_was_tool_use = True
    break

if last_assistant_text is None:
    sys.exit(0)

if last_entry_was_tool_use:
    sys.exit(0)

word_count = len(last_assistant_text.split())
is_clarifying_question = word_count < 40 and last_assistant_text.rstrip().endswith("?")

if is_clarifying_question:
    sys.exit(0)

lowered = last_assistant_text.lower()
has_next_steps = "## next steps" in lowered or "**next steps**" in lowered

if has_next_steps:
    sys.exit(0)

print(json.dumps({
    "decision": "block",
    "reason": "Reply is missing a required 'Next steps' section (## Next steps or **Next steps**) with 3-5 deterministic terminal-ready actions. Add one before stopping.",
}))
sys.exit(2)
PYEOF
