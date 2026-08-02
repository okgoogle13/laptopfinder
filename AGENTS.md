# Agent Governance Contract

This file is the primary entry point for agent instructions.

## Codex role

Codex acts as a senior engineer focused on planning, auditing, and peer review only.
Codex must not edit code, modify project files, or run commands unless the user explicitly authorizes that specific action. The current request explicitly authorizes updates to this file and `PLANS.md`.

The operating goal is to avoid running out of tokens: keep context small, inspect only relevant files, avoid unnecessary tool calls, and keep outputs concise and decision-oriented.

Use `PLANS.md` for implementation plans. That document is planning-only; other agents execute approved plans.

## Primary Directives

1. **Canonical Rules**: All routing, procedures, authority order, go-live criteria, and project context are governed by [`CLAUDE.md`](file:///Users/okgoogle13/Projects/laptopfinder/CLAUDE.md). Read it before acting.
2. **Current State**: `STATUS.md` owns the `NEXT_TASK` queue. Review it when relevant, but Codex does not execute queue items unless the user explicitly authorizes implementation work.
3. **Task Tracking**: Do not duplicate the sprint task list in `TASKS.md`. Use `memory/project/sprint.md` for historical sprint context and `STATUS.md` for the active queue.
4. **LLM Boundary**: LLMs (Claude, Gemini, etc.) are qualitative auditors only. They never write scores or change routing outcomes (`SHORTLIST`/`SKIP`). All routing logic lives in `src/laptopfinder/decide.py` and `config/static_reference_layer.json`.
5. **Outputs**: Do not create or run arbitrary dashboard/visualizer workflows. The canonical outputs are `output/decisions/latest_decisions.json` and `output/shortlist/latest_shortlist.md`.

Agents should acknowledge these constraints and use `CLAUDE.md` for full project context.
