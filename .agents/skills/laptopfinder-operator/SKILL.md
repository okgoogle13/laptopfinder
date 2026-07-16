---
name: laptopfinder-operator
description: >
  Runs the laptopfinder eBay-AU operator pipeline as far as it can safely be
  automated: precondition checks, fixture regression, a gated live scrape, and
  shortlist/matrix/gap-scan reporting. Stops at explicit checkpoints for any
  step that is a market, money, or shared-document decision. Invoke when asked
  to "run the laptopfinder operator", "check laptopfinder preconditions",
  "run the eBay pipeline", "run the Sprint 6 operator guide", or via
  /laptopfinder-operator.
---

# Laptopfinder Operator Skill

## Purpose

Drive the laptopfinder eBay-AU decision pipeline (precondition checks →
fixture regression → live scrape → shortlist → purchase matrix → gap scan)
as far as it can go without a human making a market, money, or shared-document
decision. This skill defines a runtime-neutral contract: it names the
operations it needs, not a specific tool API. Whatever runtime hosts this
skill supplies concrete implementations of the four primitives below.

## Inputs

- `run_mode`: `fixtures_only` (default) | `live`
  - `fixtures_only` → Phase 0-1 only. Zero network, zero cost.
  - `live` → full Phase 0-5, pausing at the checkpoints below.
- `feed_source`: path, default `data/urls.txt` (mirrors the `FIRECRAWL_URLS`
  Makefile override).

## Tool primitives required from the host runtime

This skill only assumes four operations exist. It does not name or depend on
any specific tool implementation — the host runtime supplies these:

- `run_command(cmd) -> {stdout, stderr, exit_code}` — execute a shell command
  in the repo root and return its output.
- `read_file(path) -> content` — read a file's contents.
- `write_file(path, content)` — write or create a file. Gated by the
  filesystem contract below; the host runtime is responsible for enforcing
  the allow/deny lists before actually writing.
- `ask_human(prompt, payload) -> approval | edited_payload` — present
  `payload` to the human and block until they approve, reject, or edit it.
  How this is surfaced (a chat question, a CLI prompt, a UI dialog, an
  approval-mode gate) is entirely up to the host runtime.

## Filesystem contract

**read_allow:**
- `Makefile`, `CLAUDE.md`, `TASKS.md`
- `config/static_reference_layer.json`
- `data/urls.txt`, `data/feed_live/**`, `data/shortlist_candidates.jsonl`
- `data/evidence/undiscovered_hardware.jsonl`
- `tests/fixtures/stage1/**`, `tests/fixtures/stage2/**`
- `.env` — presence and placeholder-pattern check only; contents are never
  read into output, logged, or echoed anywhere.

**write_allow_auto** (no human gate required):
- `prompts/*.txt` — only as the output of running the config-sync command,
  never hand-edited directly.
- `tests/fixtures/stage2/*_failing.json` — new files only, draft failure
  reproductions.

**write_allow_confirm** (draft first, human approves via `ask_human`, then write):
- `data/shortlist_candidates.jsonl`
- `TASKS.md`

**write_deny** (never, under any run_mode):
- `.env`
- `config/static_reference_layer.json`
- `src/**`
- `.git/**`

## Checkpoints

Each of these is a blocking `ask_human` call. The skill must not proceed past
one until it receives an explicit approval.

1. **pre_live_scrape** — before initiating the live scrape. Show: how many
   URLs are queued, which paid APIs will be invoked as a result (the
   scrape-and-live path calls a fetch API and then the per-listing analysis
   pipeline, which in turn calls at least one paid LLM API per listing).
2. **pre_shortlist_write** — before writing the shortlist candidates file.
   Show: every proposed line, paired with the console/log excerpt it was
   derived from, for line-by-line approval or edit.
3. **pre_tasks_md_write** — before writing to the shared task-tracking
   document. Show: the full diff.

## Execution flow (phases)

Behavior by `run_mode`: `fixtures_only` runs Phase 0-1 only. `live` runs
Phase 0-5, pausing at the three checkpoints above.

**Phase 0 — Preconditions (auto)**
- Confirm the commands this skill is about to rely on actually exist before
  running them (dry-run/list known targets; check that any script paths
  referenced by documentation are real files on disk — repo history has
  shown documentation drift ahead of the real command surface, so this check
  is load-bearing, not decorative).
- Before creating any new script, Makefile target, or data file for a named
  workflow, grep the Makefile and `scripts/` for that workflow's name first.
  A same-named workflow with an incompatible design can already be live —
  repo history has produced exactly this (a working `pwm-floor-sync-prep`/
  `pwm-floor-sync-check` Makefile system, gating `make live`, existed before
  a same-named script was independently built from a stale planning doc
  without this check, producing two conflicting implementations of
  "lf-floor-sync"). A hit means stop and surface it to the human before
  writing anything, not proceed and reconcile later.
- Run the test suite; record pass/fail counts.
- Check for the presence of each required API key name in the environment
  config and flag any that still hold placeholder values.
- Check the feed source for a minimum number of real (non-comment,
  non-example) URL lines.
- Check whether the scoring config has changed more recently than the
  generated prompt files; if so, run the config-sync command automatically
  (pure regeneration from already-approved config — reversible, diffable).
- Output: a go/no-go report covering all of the above, plus whether `live`
  mode is currently viable.

**Phase 1 — Fixture sanity (auto, runs in both modes)**
- Run the single-fixture decision command against the known reference
  fixtures (including the Turing/Ada architecture-penalty pair).
- Run the paired-fixture full-pipeline command.
- Run the full test suite.
- Output: scores/actions for each fixture and confirmation the suite is
  still green — a zero-cost, zero-network regression check before touching
  live data.

**Phase 2 — Live scrape (confirm: pre_live_scrape, `live` mode only)**
- Run the live scrape command, which fetches each queued URL and pushes it
  through the analysis pipeline.
- Capture full console output and any generated listing text files.
- Any listing that crashes or is rejected gets an auto-drafted failing-case
  fixture (write_allow_auto) — this skill captures the repro but does not
  attempt to diagnose or patch the underlying code; that is out of scope
  here and gets logged as a follow-up item instead.

**Phase 3 — Shortlist draft (confirm: pre_shortlist_write)**
- Parse Phase 2's output for every decision whose recommended action is
  "shortlist."
- Assemble a proposed set of JSONL lines (title, GPU, price, score) without
  writing them.
- Present the draft via `ask_human` for line-by-line approval or edit before
  any write occurs.

**Phase 4 — Matrix + gap scan (auto)**
- Run the matrix-rendering command against the (now-approved) shortlist file.
- Run the market-gap scan command against the live feed files.
- Summarize the top-ranked candidates and any alerts.
- Run one automated sanity check based on the project's own invariant: for
  otherwise comparable listings, a 16GB RTX 3080 or 3080 Ti priced
  meaningfully below a 16GB RTX 4090 should be ranked higher on
  price-to-VRAM; if the matrix consistently reverses this (RTX 4090 above a
  cheaper 3080/3080 Ti at the same VRAM tier), treat it as a regression
  signal worth human attention, not a hard failure.

**Phase 5 — Reporting (confirm: pre_tasks_md_write)**
- Assemble an end-of-run report summarizing everything Phases 0-4 did.
- Draft proposed checklist/backlog updates to the shared task-tracking
  document reflecting what actually happened.
- Present the diff via `ask_human`; write only on approval. Committing that
  change to version control is a separate, explicit action this skill never
  takes on its own.

## Non-goals

- Never introduces a new scraping or browser-automation tool without a human
  first revisiting the project's tool-assessment document and citing a
  specific blocker from it.
- Never patches scoring logic or configuration inline in response to a bad
  result — captures the failing case and stops.
- Never commits or pushes version-control state.
- Never reads, logs, or echoes secret values, even when checking for their
  presence.
