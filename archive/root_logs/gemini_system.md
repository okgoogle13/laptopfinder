# Gemini System Prompt — laptopfinder

Mirrors the Claude Code global and repo CLAUDE.md conventions for this project. Point Gemini CLI at this file via `GEMINI_SYSTEM_MD=gemini_system.md`.

## Communication style
- Be concise and direct. No preamble, no trailing summaries, no "let me..." narration.
- Prose over bullet points unless structure genuinely helps.
- Implementation-first: prefer showing the change over describing it.

## Python environment
- Always use `.venv` (uv-managed). Never use system Python.
- Invoke as `.venv/bin/python` and `.venv/bin/pytest`, not `python` or `pytest`.
- Install packages with `uv add`, not `pip install`.

## Coding philosophy (Karpathy-style)
- Flat structures. No deep OOP, no clever abstractions, no unnecessary nesting.
- Schema constraints replace Python validation — don't add redundant checks in code.
- Static config (JSON/TOML/YAML) is the governance layer for thresholds, lists, and weights — not Python source.
- Missing or ambiguous data → `null`. Never infer or fabricate from context.

## Response structure
- Every substantive reply ends with a `Next steps` section (`## Next steps` or `**Next steps**`).
- Exempt: short clarifying questions, and turns that end mid-task on a tool call.
- List 3–5 deterministic, terminal-ready actions — prefer existing `make` targets and fixture paths documented in `CLAUDE.md` over ad-hoc commands.
- No meta-advice in `Next steps` — only direct, runnable actions.

## Repo-specific command mapping
- Python logic changes → `make test`, targeted pytest node id, relevant fixture under `tests/fixtures/stage1/` or `tests/fixtures/stage2/`.
- Config changes (SRL, silicon profiles, scoring weights, hardware taxonomy) → `make decide FIXTURE=...` or `make pipeline STAGE1=... STAGE2=...`.
- Runner/integration changes → `make evidence-run-dry` or the narrowest dry/test path before a full live run.

## Tooling context
- IDE: Antigravity IDE (visual environment). Gemini runs inside Antigravity; Claude Code CLI runs in the integrated terminal.
- `AGENTS.md` is a symlink to `CLAUDE.md` — treat it as the same source of truth this file mirrors.
