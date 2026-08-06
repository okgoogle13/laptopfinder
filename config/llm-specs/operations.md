# operations.md

Budgets, rollout order, verification and maintenance. **This file never gets pasted anywhere** — it's the operating manual, not the payload.

Payload lives in `agent-operating-spec.md` (CORE, +DEPTH, +CODE) and `comms/voice-profile.md` (+COMMS). Why the system is shaped this way: `README.md` and `_archive/2026-07-31_migration-memo.md`.

---

## The four blocks

| Block | Lives in | Job | Where |
|---|---|---|---|
| **CORE** | `agent-operating-spec.md` | How to reason and reply | Everywhere, no exceptions |
| **+DEPTH** | `agent-operating-spec.md` | Reasoning depth, clarification protocol, planning | Anywhere with room |
| **+CODE** | `agent-operating-spec.md` | Coding, prompts, configs | Coding tools only |
| **+COMMS** | `comms/voice-profile.md` | Writing messages as me | Chat surfaces only |

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

See `deploy-map.md` for current per-surface mapping (blocks, file, field).

---

## Character budget

ChatGPT raised custom instructions to 5,000 characters on 15 July 2026 for Pro, Enterprise, Business and Education; Free and Go stay at 1,500 per box. Other surfaces publish no limit or a soft one.

| Block | Chars | Words |
|---|---|---|
| CORE | 1,196 | 201 |
| +DEPTH | 1,065 | 168 |
| +CODE | 919 | 146 |
| +COMMS | 2,972 | ~500 |
| CORE + COMMS | 4,170 | — |
| CORE + DEPTH + CODE | 3,184 | — |

Re-run `ops/build-project-instructions.sh --count` after any +COMMS edit and update this row by hand — it's the one number this table can't verify itself, since +COMMS lives in `comms/voice-profile.md` plus the roster file, not in this repo's counted blocks alone.

Counted **as pasted**: Unicode codepoints, including the blank line between paragraphs and the two-character join between stacked blocks — not bytes. `ops/check.sh` recomputes this way; `wc -m` does not, unless the locale is UTF-8.

**Design constraint: CORE alone stays under 1,500 characters**, so it deploys to the tightest field anywhere without an edit. Re-check after any CORE change. If it won't fit, cut a rule — don't abbreviate per surface, because that's how derived text gets reinvented.

---

## Fallback

If a project instruction field rejects the full +COMMS, see `_archive/2026-07-31_comms-go-fallback.md`. It is a contingency, not part of the deploy map — and it is the one derived variant that exists anywhere in this system, so it stays archived and unused unless a field actually refuses.

---

## Rollout order

Don't deploy everywhere at once. A bad clause landing in nine places is unattributable.

1. **claude.ai account instructions** — CORE. Three days.
2. **Comms project** — +COMMS + `comms/comms-roster-rules.local.md`. Draft five real messages through it.
3. **Claude Code / Cowork** — CORE + +DEPTH + +CODE in `~/.claude/CLAUDE.md`. One week.
4. **ChatGPT and Gemini** — only after 1–2 have held.
5. **Codex, Antigravity, Perplexity, API** — last.
6. **Delete the `portable-profiles.md` tombstone** once every surface it fed has been repasted.
7. **On Go cancellation:** drop ChatGPT from `deploy-map.md`, or repaste on the new plan. Nothing needs regenerating — no ChatGPT surface carries a derived block.

---

## Verification

| Test | Pass looks like | Targets |
|---|---|---|
| Ask something with a weak premise | Pushback lands before the answer | CORE |
| Ask a question needing sources | No inline markers, links at the end only | CORE |
| Ask for a decision with no context | At most three questions, then it proceeds on a stated assumption | CORE |
| Ask for something emotionally heavy | Named plainly, then options — not analysis | CORE |
| Ask for a plan | One implementation-ready pass, no invented side projects | +DEPTH |
| Ask for a draft declining an Inside friend's invite | Refusal in the first clause; if a reason appears it comes after, and only one | +COMMS |
| Ask for a draft declining an Outside invite | Refusal in the first clause, no reason at all | +COMMS |
| Ask for a draft to a parent | Boundary once, alternative in the same message, no re-litigating | +COMMS |
| Ask for a draft to your manager | Outcome first, no apology opener, no emoji | +COMMS |
| Claude comms project, ask for any message draft | The patterns `comms-roster-rules.local.md` maps to that scenario, labelled, no commentary | +COMMS + roster |
| Chat surface with no project-defined set, ask for any draft | Three genuinely different angles, labelled, no commentary | +COMMS |
| Coding tool, edit a 100-line file | Whole updated file, how to verify, what wasn't tested | +CODE |
| Coding tool, ask for a Slack message | Comms voice should *not* appear — not a chat surface | Block separation |

Failing test → fix the block in this repo, then re-paste. Never patch a deployed copy.

---

## Approval gate and stop conditions

Any deployed operator prompt that can trigger an irreversible action (sending, posting, deleting) must encode these as literal rules, not leave them implicit.

**Approval gate.** Before any send-like action, require all of the following:
- The recipient matches the roster exactly.
- The immediately previous turn contains unambiguous approval.
- The draft to be sent is byte-identical to the last shown draft, or to the operator's verbatim edit of it.
- Approval is single-use and is consumed once acted on.

**Edge-case judgment:**
- Multiple inbounds from the same contact count as one re-entry event, not separate replies.
- Refuse any group send if any participant is not in the roster.
- If a send action errors, report the error verbatim and do not assume delivery.

**Stop conditions.** A turn ends only when one of these is true:
- Drafts have been presented and are awaiting a pick.
- Approval was ambiguous and had to be re-asked.
- A send completed, whether success or failure.
- The operator explicitly signals done.

Do not end a workflow with a passive hand-off like "let me know if you want anything else."

**Fail-closed behavior.** If drafting fails, the queue still advances and the item is flagged as draft unavailable. Do not silently drop the item or block the whole workflow because one step failed. The same default applies to any check that's unclear or unverifiable — refuse/stop, never proceed on a best guess.

Source pattern: an operator-directives spec kept outside this repo (it carries real names and handles, so it belongs to its own project, not here).

---

## Maintenance

Changes flow one direction: out of these files. **Never edit a deployed copy** — a copy you edited in place is a fork you'll forget about.

| Change to | Re-paste to | Expected frequency |
|---|---|---|
| CORE | Every surface in `deploy-map.md` | Twice a year |
| +DEPTH | Every surface in `deploy-map.md` carrying +DEPTH | Rarely |
| +CODE | Every coding surface in `deploy-map.md` | Rarely |
| +COMMS | Every surface in `deploy-map.md` carrying +COMMS | When a tier rule proves wrong |

**Quarterly drift check:** run every test in the table above against every deployed surface. Log which failed. If the same clause fails on two surfaces, the clause is the problem, not the platform.

What travels and what never does: see the Live files table in `README.md`.

Sources: [OpenAI raises ChatGPT custom instructions limit to 5,000 characters](https://cryptobriefing.com/openai-chatgpt-custom-instructions-5000-characters/), [ChatGPT Changelog — 15 July 2026](https://reconn-ai.com/chatgpt-july-15-2026-increased-custom-instructions-limit)
