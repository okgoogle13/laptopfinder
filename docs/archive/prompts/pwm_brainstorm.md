# PWM Workflow Enhancement — Brainstorm
# Claude Opus 4.8 · High Effort · Planning + design only · No code changes this session
# Run from: /Users/okgoogle13/Projects/laptopfinder

---

## Grounding — read these files before writing anything

```
CLAUDE.md                                        # pipeline contract, invariants, architecture
STATUS.md                                        # active sprint, NEXT_TASK queue
memory/project/sprint.md                         # sprint phase detail (Sprint 8 Hardening)
config/static_reference_layer.json               # GPU lists, VRAM tiers, scoring weights, exclusion_regex
config/silicon_profiles.yaml                     # paradigm definitions (UMA, CUDA, ROCm) — reference only, not loaded at runtime
config/scoring_weights.yaml                      # per-workload weight profiles
research/alternative_silicon_dossier_july2026.md  # canonical AU silicon findings, July 2026
prompts/search_queries.txt                       # eBay AU query library (39 queries, Browse API format)
src/laptopfinder/runners/ebay_sniper.py          # live sniper daemon — zero-LLM, Browse API, iMessage alerting
src/laptopfinder/runners/hunt.py                 # ad hoc config-driven sweep (delegates to ebay_hunter.py)
src/laptopfinder/decide.py                       # decision engine — SHORTLIST / MONITOR / SKIP routing
docs/pwm_deep_research.md                        # existing Deep Research workflow catalogue
docs/pwm_council_concepts.md                     # existing Council workflow catalogue
docs/pwm_labs_workflows.md                       # existing Labs (Create Files & Apps) catalogue
docs/ebay_sniper.md                              # sniper usage docs (Sprint 8 fixup target)
```

If any file is missing or inaccessible, stop and say so. Do not infer contents.

---

## Role and scope

You are the **workflow architect** for the **Perplexity Workflow Manager (PWM)** serving the
**laptopfinder** project — specifically the **eBay AU sniper pipeline**.

PWM has three operating tiers — learn the distinction before proposing anything:

| Tier | Tool / Mode | Best for | Budget |
|---|---|---|---|
| **Deep Research** | `pwm lf-*` via Perplexity Deep Research | Exhaustive market/silicon/vendor analysis; citation-rich markdown + JSON artefacts | ~20 tokens |
| **Council** | Multi-model consensus via `pwm council` | High-stakes subjective decisions; scoring governance; edge-case risk interpretation | 3 Pro queries per call |
| **Labs** | Perplexity "Create Files & Apps" | Generating durable local code: daemons, dashboards, scraper modules, test suites | ~25 tokens |

The existing workflow catalogue (in `docs/pwm_*.md`) already defines:

| Workflow | Tier | Status |
|---|---|---|
| `lf-outlet-dossier` | Deep Research | defined |
| `lf-price-baseline` | Deep Research | defined |
| `lf-silicon-ground` | Deep Research | defined |
| `lf-vendor-audit` | Deep Research | defined |
| `lf-buy-jury` | Council | concept |
| `lf-council-audit` | Council | concept |
| `lf-paradigm-debate` | Council | concept |
| `lf-risk-calibrator` | Council | concept |
| `lf-playbook-synth` | Council | concept |
| `lf-alert-forge` | Labs | defined |
| `lf-matrix-app` | Labs | defined |
| `lf-compare-studio` | Labs | defined |
| `lf-sniper-rules` | Labs | defined |

Your task: **identify gaps, propose new workflows, and suggest enhancements** that maximise
value for the eBay sniper workflow and Sprint 8 hardening goals — specifically workflows that
front-load Perplexity research to produce offline artefacts the sniper consumes at zero
runtime API cost.

---

## The core design constraint

**Gemini API calls are finite and cost money. Perplexity subscription is pre-paid.**

The sniper (`ebay_sniper.py`) is token-free by design — it never calls an LLM. Its intelligence
comes entirely from offline config:
- `config/static_reference_layer.json` — GPU lists, VRAM tiers, price floors, exclusion regex
- `prompts/search_queries.txt` — Browse API query strings
- `data/seen_sniper_items.json` — dedup state

The batch runner (`make hunt CONFIG=...`) uses Gemini for enrichment/grounding but is secondary.

**Every new PWM workflow must answer:** *"What offline artefact does this produce that makes
the sniper or decide.py smarter without adding a runtime API call?"*

Concrete sniper-value examples:
- New entries in `target_gpus` or `watch_list` → sniper keyword expansion
- Updated `observed_au_price_min_aud` floors → tighter local pricing sweep
- New `exclusion_regex` patterns → fewer junk matches
- New `search_queries.txt` entries → broader discovery coverage
- Updated `egpu_enclosures` or `uma_platforms.chip_patterns` → wider hardware recognition

Artefacts produced by PWM workflows are consumed **offline** by the local pipeline
(SRL, `decide.py`, `data/`, `config/`). They must require zero further API calls once written.

---

## Hard constraints

- **Karpathy-style:** flat scripts, config over code, no deep OOP, no custom exception hierarchies.
- **Sniper-first:** every proposed workflow must state which sniper config path it feeds
  (SRL key, search query, exclusion regex, or "none — batch runner only").
- **eBay-first data:** listing data comes from existing runners (`make live`, `make hunt`,
  `ebay_sniper.py`). New workflows treat runner outputs as their entry point.
- **Offline artefacts:** every workflow produces static files (markdown, JSON, CSV, shell scripts)
  under `data/pwm/<workflow-name>/` or the paths already established in `docs/pwm_*.md`.
- **Scope discipline:** if an idea requires a new Python package, a new schema, or a new Makefile
  target, flag it explicitly as **[optional]** and note the cost.
- **Burst/sprint mindset:** each workflow fits in one sitting and has a binary done criterion.
- **LLM boundary (strict):** PWM workflows produce *reference data and qualitative analysis only*.
  They never write scores, thresholds, or routing decisions into `decide.py` or the SRL.
  A human or agent reviews PWM output and manually propagates approved changes.
- **eBay API reality:** the Browse API supports `q=` keyword, `filter=`, `sort=`, `aspect_filter=`,
  `category_ids=`, and `limit=`. It does **not** support Boolean operators (AND/OR/NOT) in the
  `q=` parameter. Do not propose workflows that assume capabilities the Browse API lacks.
- **No daemon duplication:** `lf-alert-forge` (Labs) overlaps with the shipped `ebay_sniper.py`.
  Proposals must acknowledge this overlap and specify whether they augment, replace, or
  complement the existing sniper.

---

## Sprint 8 context — what matters now

The current sprint (S8 Hardening) has these open tasks. Weight proposals toward these:

| Task | File(s) | Sniper relevance |
|---|---|---|
| S8-01: Fix `docs/ebay_sniper.md` | docs/ebay_sniper.md | direct |
| S8-02: Pick unattended-run method | docs/ebay_sniper.md, Makefile | direct |
| S8-03: `ingest_csv.py` column validation | src/laptopfinder/ingest_csv.py | indirect (CSV→SHORTLIST) |
| S8-05: Screen-size regex fallback | scripts/build_shortlist_value.py | indirect (matrix ranking) |
| S8-08: `risk_score == 3.0` boundary test | tests/test_decide.py | indirect (decision gate) |

Sprint 7 backlog items still open:
- `batch_decide()` implementation
- Feed API gzip TSV rework (blocked on `buy.feed` scope)
- Marketplace Insights (blocked on restricted API scope)

---

## Deliverable 1 — New and enhanced workflows

Identify **gaps in the existing catalogue** and propose **3–5 new or significantly enhanced workflows**.
Do not re-describe existing workflows unless proposing a material change.

For each, use this exact format:

```
### pwm lf-<name>

Tier: Deep Research | Council | Labs | (hybrid: specify)
Purpose: one sentence.
Gap it fills: what the existing catalogue is missing that this addresses.
Sniper feed: which SRL key, search query file, or config path this ultimately updates.
         If none, state "batch runner only" or "decision-support only".
When to run: sprint phase / trigger / frequency.
Reduces Gemini calls: which specific step (run_stage2 / ingest_csv / ebay_hunter enrichment / none)?

Inputs:
  - exact file path or runner output (e.g. output/decisions/latest_decisions.json)

Outputs:
  - exact file path + format (e.g. data/pwm/lf-<name>/report.md)
  - note: must be consumable offline with zero further API calls

Steps:
  1. [Tier / cost] — what query or Labs prompt; exact artefact produced
  2. [Tier / cost] — ...
  3. [optional, higher cost] — council call or second Deep Research pass, only if X condition

Done criterion: one binary statement, verifiable with `make test` or file existence check.

PWM command: pwm lf-<name> [--args]
```

Cost labels (from PWM manifest conventions):
- `free` — local script / Make target, no API
- `1-pro` — one Perplexity Pro Search query
- `deep` — one Deep Research token (~20 available)
- `labs` — one Labs "Create" run (~25 tokens available)
- `council-3` — three-model council (3 Pro queries + synthesis)

**Budget ceiling for this brainstorm:** propose workflows that collectively consume ≤ 5 deep +
2 labs + 1 council-3 tokens. Exceeding this requires explicit justification.

---

## Deliverable 2 — Manifest and config additions

For each proposed workflow:

- **Manifest entry** — the addition to `docs/pwm_*.md` (which file it belongs in, naming convention,
  cost tag, output dir, done-check path).
- **Shell one-liner** — a `make` target or alias that chains: runner output → PWM workflow → write
  artefacts. Must follow existing Makefile patterns (`.venv/bin/python`, `op run --env-file=.env --`
  where live credentials are needed).

Additionally propose:

- Any **naming convention gaps** across `lf-*` commands (e.g. inconsistent output dir structure
  between Deep Research and Labs workflows).
- One **sniper-preflight bundle** — a single `make pwm-preflight` target that:
  1. Runs `make test` (zero API cost).
  2. Validates SRL JSON schema (`python -m json.tool config/static_reference_layer.json`).
  3. Confirms `prompts/search_queries.txt` has ≥ 25 non-comment, non-blank lines.
  4. Confirms `.ebay_access_token` exists and is < 2 hours old.
  5. Prints a checklist of which PWM workflows are due before starting `make live`.

---

## Deliverable 3 — Integration map

Produce this table for **all workflows** (existing + proposed):

| PWM workflow | Tier | Cost | Replaces / reduces | Pipeline file it feeds | Sniper config path | Cadence |
|---|---|---|---|---|---|---|

Include existing catalogue entries. Mark proposed new ones with `[NEW]`.

The "Sniper config path" column must contain the exact SRL key path, search query file,
or `—` if the workflow does not feed the sniper directly.

---

## Deliverable 4 — Next steps

Exactly 4 terminal-ready actions. Follow the `AGENTS.md` Next steps convention:
- Prefer existing `make` targets and `.venv/bin/python -m ...` invocations.
- At least one must be a pure local run (no API at all).
- At least one must specifically exercise a newly proposed workflow.
- At least one must directly support Sprint 8 hardening (S8-01 through S8-09).

---

## Output rules

- No narrative padding ("In summary…", "Overall…", "Great question…").
- Section headers exactly as labelled.
- File paths from repo root (no `~/`, no relative `./`).
- No placeholders — if unknown, write `TBD: <reason>`.
- Do not touch `decide.py` or SRL scoring logic — propose reference data files only.
- Do not suggest new Python packages without flagging `[optional: pip install <pkg>]`.
- Do not assume eBay Browse API capabilities beyond what is documented in `prompts/search_queries.txt`
  and `src/laptopfinder/runners/ebay_sniper.py`. If unsure, state the assumption explicitly.
- When referencing SRL keys, use the exact JSON path (e.g. `vram_gating_logic.standard_mobile_min_gb`),
  not a paraphrase.
