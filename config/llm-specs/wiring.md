# wiring.md

Budgets, rollout order, verification and maintenance. **This file never gets pasted anywhere** — it's the operating manual, not the payload.

Payload lives in `agent-operating-spec.md` (CORE, +DEPTH, +CODE) and `voice-profile.md` (+COMMS). Why the system is shaped this way: `README.md` and `_archive/2026-07-31_migration-memo.md`.

---

## The four blocks

| Block | Lives in | Job | Where |
|---|---|---|---|
| **CORE** | `agent-operating-spec.md` | How to reason and reply | Everywhere, no exceptions |
| **+DEPTH** | `agent-operating-spec.md` | Reasoning depth, clarification protocol, planning | Anywhere with room |
| **+CODE** | `agent-operating-spec.md` | Coding, prompts, configs | Coding tools only |
| **+COMMS** | `voice-profile.md` | Writing messages as me | Chat surfaces only |

+CODE and +COMMS never appear together.

---

## Why no repo carries voice

+COMMS can only be delivered by paste. Code has exactly two options and both are barred:

- **Embed the text** — a derived variant. Banned, and it drifts. This is what `voice_rules.md` was, and it contradicted canonical on emoji and sign-offs within one generation.
- **Read it from a path** — machine-specific, and it fails the moment a second application or a second machine wants the same voice.

Therefore **any component that needs voice must live inside a surface where +COMMS is already pasted.** An application cannot consume voice; it can only hand the job to a session that already carries it. This is why `targets.conf` has no profile containing `voice-profile.md` — a structural consequence, not a policy choice.

Corollary for artifacts and sub-agents: a surface that reaches a model *without* project instructions (a quick inline call, a fresh worker) has no +COMMS and must not draft.

---

## Deploy map

See `CHEATSHEET.md` for current per-surface mapping (blocks, file, field).

---

## Character budget

ChatGPT raised custom instructions to 5,000 characters on 15 July 2026 for Pro, Enterprise, Business and Education; Free and Go stay at 1,500 per box. Other surfaces publish no limit or a soft one.

| Block | Chars | Words |
|---|---|---|
| CORE | 1,196 | 201 |
| +DEPTH | 1,065 | 168 |
| +CODE | 919 | 146 |
| +COMMS | 3,035 | 507 |
| CORE + COMMS | 4,233 | — |
| CORE + DEPTH + CODE | 3,184 | — |

**Design constraint: CORE alone stays under 1,500 characters**, so it deploys to the tightest field anywhere without an edit. Re-check after any CORE change. If it won't fit, cut a rule — don't abbreviate per surface, because that's how derived text gets reinvented.

---

## Fallback

If a project instruction field rejects the full 3,035-character +COMMS, see `_archive/2026-07-31_comms-go-fallback.md`. It is a contingency, not part of the deploy map.

---

## Rollout order

Don't deploy everywhere at once. A bad clause landing in nine places is unattributable.

1. **claude.ai account instructions** — CORE. Three days.
2. **Comms project** — +COMMS + `comms-project.md`. Draft five real messages through it.
3. **Claude Code / Cowork** — CORE + +DEPTH + +CODE in `~/.claude/CLAUDE.md`. One week.
4. **ChatGPT and Gemini** — only after 1–2 have held.
5. **Codex, Antigravity, Perplexity, API** — last.
6. **Delete the `portable-profiles.md` tombstone** once every surface it fed has been repasted.
7. **On Go cancellation:** drop ChatGPT from `CHEATSHEET.md`, or repaste on the new plan. Nothing needs regenerating — no ChatGPT surface carries a derived block.

---

## Verification

| Test | Pass looks like | Targets |
|---|---|---|
| Ask something with a weak premise | Pushback lands before the answer | CORE |
| Ask a question needing sources | No inline markers, links at the end only | CORE |
| Ask for a decision with no context | At most three questions, then it proceeds on a stated assumption | CORE |
| Ask for something emotionally heavy | Named plainly, then options — not analysis | CORE |
| Ask for a plan | One implementation-ready pass, no invented side projects | +DEPTH |
| Ask for a draft declining a friend's invite | Refusal in the first clause, reason after, one reason | +COMMS |
| Ask for a draft to a parent | Boundary once, alternative in the same message, no re-litigating | +COMMS |
| Ask for a draft to your manager | Outcome first, no apology opener, no emoji | +COMMS |
| Ask for any message draft | Three genuinely different angles, labelled, no commentary | +COMMS |
| Coding tool, edit a 100-line file | Whole updated file, how to verify, what wasn't tested | +CODE |
| Coding tool, ask for a Slack message | Comms voice should *not* appear — not a chat surface | Block separation |

Failing test → fix the block in this repo, then re-paste. Never patch a deployed copy.

---

## Maintenance

Changes flow one direction: out of these files. **Never edit a deployed copy** — a copy you edited in place is a fork you'll forget about.

| Change to | Re-paste to | Expected frequency |
|---|---|---|
| CORE | Every surface — 12 fields | Twice a year |
| +DEPTH | 7 fields | Rarely |
| +CODE | Coding surfaces — 5 fields | Rarely |
| +COMMS | Comms project on Claude, ChatGPT and Gemini, and the `my-voice-comms` Claude Desktop skill — 4 fields | When a tier rule proves wrong |

**Quarterly drift check:** run the eleven verification tests against every deployed surface. Log which failed. If the same clause fails on two surfaces, the clause is the problem, not the platform.

What travels and what never does: see the Live files table in `README.md`.

Sources: [OpenAI raises ChatGPT custom instructions limit to 5,000 characters](https://cryptobriefing.com/openai-chatgpt-custom-instructions-5000-characters/), [ChatGPT Changelog — 15 July 2026](https://reconn-ai.com/chatgpt-july-15-2026-increased-custom-instructions-limit)
