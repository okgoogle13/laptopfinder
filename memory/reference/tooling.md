---
name: tooling-setup
description: IDE, agent, and MCP tooling decisions for this project
metadata:
  type: reference
---

# Tooling Setup

**Primary workflow:** Antigravity IDE (VS Code fork) + Claude Code CLI in the integrated terminal.

- Antigravity provides file explorer, git panel, and integrated terminal
- Claude Code CLI runs in Antigravity's terminal via `claude` command — no extension needed
- `CLAUDE.md` → read by Claude Code automatically
- `AGENTS.md` → symlink to `CLAUDE.md`, read by Antigravity's Gemini agent
- Both tools share the same project rules from one source file

**MCP:** Desktop Commander and Filesystem MCP are redundant — Claude Code has native file access and shell execution. No MCP servers needed for this project.

**Python environment:** uv-managed `.venv`. Always invoke as `.venv/bin/python` or `.venv/bin/pytest`, never system Python.
