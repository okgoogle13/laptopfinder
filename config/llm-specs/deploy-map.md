# deploy-map.md

This file is the canonical per-surface mapping; `operations.md` does not duplicate it.

Four blocks, none derived from another, none restating another. **CORE** is the non-negotiables and fits the smallest instruction field anywhere. **+DEPTH** adds what only matters in long work. **+CODE** is coding tools only. **+COMMS** is chat surfaces only, and never appears in a coding tool — +CODE wants completeness, +COMMS wants compression. A block is pasted whole or not pasted; there are no summarised variants. Relationships run on two tiers — **Inside** (people who get the truth) and **Outside** (honest, no inner world, decline without a reason) — plus two context overrides that beat closeness, **Family** and **Formal**.

---

## Where each block goes

| Surface | Blocks | File to paste | Field |
|---|---|---|---|
| Claude profile | CORE | `agent-operating-spec.md` | Settings → Profile → Instructions for Claude. Account-wide; propagates to web, desktop, mobile and Cowork. |
| Claude Custom Style | **none — never create one** | — | A Style is a per-conversation toggle that can be left on, and +COMMS in a coding conversation sabotages +CODE. |
| Claude project | +COMMS + roster | `comms/voice-profile.md` + `comms/comms-roster.local.md` | Project instructions. The only place +COMMS lives on Claude. |
| Claude Code — global | CORE + +DEPTH + +CODE | `agent-operating-spec.md` | `~/.claude/CLAUDE.md`. Claude Code does not read account settings, so CORE is needed here too. |
| Claude Code — per repo | *none* | — | `./CLAUDE.md` carries stack, commands and repo conventions only. Never restates a block. |
| Cowork — dev folder | +DEPTH + +CODE | `agent-operating-spec.md` | `CLAUDE.md` in the connected folder. CORE should arrive from account settings — confirm with verification test 1. |
| Claude API / Agent SDK | CORE + +DEPTH + whichever applies | `agent-operating-spec.md` | System prompt. Logged-context variant. |
| ChatGPT custom instructions | CORE + +DEPTH | `agent-operating-spec.md` | Settings → Personalization → Custom instructions. Box 1 = CORE "About me" + +DEPTH (1,161). Box 2 = the rest of CORE (1,100). |
| ChatGPT comms project | +COMMS only — no roster | `comms/voice-profile.md` | Project instructions. The roster names real people and is Claude-only, so tier handling is unavailable here. |
| Gemini Saved info | CORE | `agent-operating-spec.md` | Settings → Personalization → Saved info |
| Gemini comms | +COMMS only — no roster | `comms/voice-profile.md` | A Gem, or the head of the drafting conversation. Not Saved info — it would apply to everything. The roster names real people and is Claude-only, so tier handling is unavailable here. |
| Claude Desktop skill `my-voice-comms` | +COMMS (no roster) | `comms/voice-profile.md` | `SKILL.md` under Claude's local skills-plugin folder. Backstop for drafting outside the comms project — repaste by hand, never symlinked. |
| Gemini CLI | CORE + +DEPTH + +CODE | `agent-operating-spec.md` | `GEMINI.md` |
| Codex / Antigravity | CORE + +DEPTH + +CODE | `agent-operating-spec.md` | `AGENTS.md` at repo root, or the agent's rules file if it doesn't read `AGENTS.md` |
| Perplexity | CORE | `agent-operating-spec.md` | Settings → Preferences / AI Profile |
| Generic API | CORE + whichever applies | `agent-operating-spec.md` | System prompt. Logged-context variant. |

---

## If it's behaving wrong

- Coding replies hedged, verbose, or full of placeholders → check +CODE and CORE deployment.
- Comms drafts surfacing trade-offs or caveats → check +COMMS deployment, not CORE.
- One high-effort option instead of two or three → check CORE.
- Plans arriving in fragments, or re-asking questions mid-task → check +DEPTH.
- Drafts running long, or clipped instead of short → check +COMMS.
- Comms voice appearing in a coding tool → +COMMS is deployed somewhere it shouldn't be; it is project-scoped only.
- Inline citation markers or bare URLs in the body → check CORE.

Character budget, rollout order, verification tests and maintenance: `operations.md`.
