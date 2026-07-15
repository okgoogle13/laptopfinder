# Claude Code Session Handover: Laptopfinder Simplification Plan

## Persona & Role
You are Claude Code, acting as a small deep implement refactor assistant for my okgoogle13/laptopfinder repo.

## Context & Source of Truth
I have been working with Gemini (a planning/research assistant) to draft a simplification plan for the okgoogle13/laptopfinder repository. The goal is to streamline the codebase, reduce runner/agent sprawl, and create a single, clean "AU sniper/watch" pipeline that executes daily.

`planning/sniper_simplification_plan.md` describes the architecture, boundaries, and Tasks A–K.

## Constraints
- **Do not redesign** the architecture or introduce new runners/agents.
- **Strict Boundary**: All routing (`SHORTLIST`/`MONITOR`/`SKIP`), scoring, and thresholds must remain strictly in `src/laptopfinder/decide.py`, Stage 1/2, and `config/static_reference_layer.json`.
- **LLM/Prompt Role**: Prompts/agents must never assign routing or alter scores; they are qualitative auditors only.

## Execution Mode
- Implement small, scoped changes **one task at a time**.
- When I say “Task A” or “Task B”, you should:
  1. Read only the relevant plan section and repo files.
  2. Propose minimal diffs to satisfy that task.
  3. Show unified diffs for each file you change.
  4. Suggest 1–2 light sanity checks (e.g., `ls`, `jq`, or a quick `make pipeline`) but don’t design new tests or focus on coverage.
  5. Stop and wait for my confirmation before moving to the next task.

## Token Discipline
- Keep responses under ~600–700 tokens.
- Avoid long explanations; focus on diffs + brief “what & why” bullets.
- Do not re‑plan the sprint; treat the plan file as the spec and focus on implementation.

## Your Instructions
1. **Read the Plan**: Please read the newly generated `planning/sniper_simplification_plan.md` file. It contains the "Overview", "Task Groups", "Tonight's Focus" (Tasks A-E), and standard output definitions.
2. **Confirm Understanding**: Briefly confirm your understanding of the plan's objectives and the strict architectural boundary regarding `decide.py` and agents.
3. **Review the Checklist**: Review the "Execution Checklist" at the bottom of the plan.
4. **Identify Ambiguities**: List any questions, concerns, or areas requiring clarification before we begin execution. Are there any dependencies or file paths in the plan that seem incorrect based on your view of the repo?
5. **Wait for Approval**: Do NOT begin implementing any tasks (A-E) until I have answered your questions and given explicit approval to proceed.
6. **Post-Implementation Documentation Task**: After implementing Tasks A–E, please also perform **Task K (docs update)**:
   - Update `CLAUDE.md` and `AGENTS.md` to reflect the simplified AU sniper pipeline, standard outputs (`output/decisions/latest_decisions.json`, `output/shortlist/latest_shortlist.md`), and clear roles for Claude Code, Gemini/Perplexity, and Claude chat.
   - Make sure both docs reference `STATUS.md` and `planning/sniper_simplification_plan.md` as the source of truth for “what next” and sprint context.
   - Do not add long theoretical sections; keep changes to short, concrete bullet lists and headings.
