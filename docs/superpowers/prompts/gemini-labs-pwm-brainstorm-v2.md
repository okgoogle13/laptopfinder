# Gemini Labs PWM Brainstorm — `laptopfinder` eBay AU Sniper
**Model:** Gemini 3.1 Pro · Deep Think (High)  
**Context:** Antigravity IDE / Perplexity Labs / ChatGPT Projects  
**Date:** 2026-07-16  

---

> **Before submitting:** Enable **Deep Think**. Upload the four files listed in `<data>` as attachments. Enable **Google Search grounding** — the prompt specifies exactly where to use it. The `<thinking_protocol>` section runs first; the 7 spec blocks are the final output.

---

<context>

## Codebase

**Pipeline:** Stage 1 (discovery) → Stage 1A (handoff) → Stage 2 (grounding + fact extraction) → `decide()` → SHORTLIST / MONITOR / SKIP

**Governance layer:** `config/static_reference_layer.json`
- All scoring weights, VRAM tiers, target GPUs, watch list, exclusion regex, risk gate
- Key fields in scope: `target_gpus`, `vram_gating_logic.standard_mobile_min_gb` (16 GB), `vram_gating_logic.touchscreen_exception_min_gb` (12 GB), `uma_platforms.min_total_ram_gb_to_shortlist` (32 GB), `data_integrity.exclusion_regex`

**Active runners (two paths only):**
- `runners/ebay_sniper.py` — zero-LLM daemon; Browse API polling, iMessage alerts, offline config only; never duplicated by Labs workflows
- `runners/hunt.py` — ad-hoc Gemini-enriched sweep; produces `output/decisions/latest_decisions.json`

**Key outputs consumed by Labs workflows:**
- `output/decisions/latest_decisions.json` — SHORTLIST / MONITOR / SKIP decisions with scores
- `output/shortlist/purchase_matrix.md` — ranked shortlist for human review
- `data/pwm/lf-floor-sync/price_patches.json` — batch AU price floors (if run)

## What already exists — strictly off-limits for duplication

**Labs (built):** `lf-alert-forge`, `lf-matrix-app`, `lf-compare-studio`, `lf-sniper-rules`

**Deep Research (built):** `lf-outlet-dossier`, `lf-price-baseline`, `lf-silicon-ground`, `lf-vendor-audit`

**Deep Research (Opus Deliverable 1 — off-limits):**
- `lf-floor-sync` — batch price floor refresh across all target_gpus
- `lf-watch-grad` — watch_list graduation monitoring
- `lf-query-expand` — search query blind-spot detection
- `lf-exclusion-tune` — exclusion regex evolution from corpus
- `lf-seller-intel` — clearance seller discovery

The Opus workflows own the **research-to-config pipeline**. You own the **action layer on top**: triage, evaluation, messaging, retail coverage, negotiation, alert wiring.

</context>

<data>

Attach these files before submitting. Gemini 3.1 Pro will reference them directly — do not paste inline:

1. `config/static_reference_layer.json` — governance source of truth (VRAM gates, GPU tiers, risk rules)
2. `output/decisions/latest_decisions.json` — current pipeline decisions (SHORTLIST entries are the primary input for messaging, triage, and negotiation workflows)
3. `output/shortlist/purchase_matrix.md` — human-readable shortlist
4. `data/pwm/lf-floor-sync/price_patches.json` — price floor patches; if missing, note this in `relationship_to_opus` for any workflow that needs price anchoring

</data>

<constraints>

1. **No duplication.** Every workflow sits on top of or adjacent to an existing workflow. Name the dependency explicitly.
2. **Labs-tier justification required.** Each workflow must combine ≥2 of: live web search, code generation, interactive UI/dashboard, charts, export to ChatGPT Projects. Markdown-only = not Labs.
3. **5 of 7 must run outside Antigravity** — via uploaded files in Perplexity Labs or ChatGPT Projects.
4. **No live eBay API calls inside any workflow.** All pipeline inputs come from uploaded repo files.
5. **Every workflow produces at least one CSV or JSON** consumable by ChatGPT Projects.
6. **Karpathy constraint.** One command per Labs project. Minimum viable steps. One testable done criterion.
7. **Search grounding scope.** Use Google Search only for: AU retail price discovery (JB Hi-Fi, Scorptec, PLE, Mwave, Grays) and non-eBay endpoint structure verification for alert scaffolds. Everything else derives from the uploaded files.

</constraints>

<thinking_protocol>

Before writing any specs, work through the design space in two phases.

**Phase 1 — Diverge (generate ≥14 candidate ideas)**

For each of the six required categories, generate at least 2 candidate workflow ideas. Think broadly — consider ideas that:
- Combine categories that are naturally adjacent (e.g. spec-gap + messaging)
- Use Gemini's Search grounding to add real-time retail data unavailable in the repo
- Produce outputs that unlock further analysis in ChatGPT Projects
- Reduce the time between "shortlist exists" and "purchase decision made"

At this stage, do not filter. Generate candidates freely. For each, note:
- Which existing workflow it consumes as input
- Whether it genuinely requires Labs tier or would be sufficient as Deep Research
- Whether it can run outside Antigravity

**Phase 2 — Converge (select and pressure-test the 7 strongest)**

From your ≥14 candidates, select the 7 that best satisfy all constraints simultaneously. For each finalist:
- Confirm it does not duplicate any off-limits workflow
- Confirm it justifies Labs tier (≥2 Labs-tier requirements)
- Identify if any two candidates collapse cleanly into one tighter workflow (prefer consolidation)
- Revise any idea that, on reflection, is better suited to Deep Research than Labs
- Confirm coverage across all six required categories

Only after completing both phases, output the 7 spec blocks. Do not show the Phase 1/Phase 2 reasoning in your response — it is your internal thinking process. Output only the final 7 specs.

</thinking_protocol>

<task>

Design **7 PWM Labs workflow specs** that help me **choose and buy a laptop this sprint**. Weight toward decision-acceleration: triage, messaging, and negotiation take priority over long-term infrastructure.

Cover all six categories. One workflow may cover two adjacent categories if the combination produces a tighter, more useful tool than two separate ones.

**Category 1 — URL-based scoring**
I paste eBay AU or AU retail listing URLs. Labs fetches and parses the page, scores the listing against the uploaded SRL (VRAM gates, risk rules, exclusion regex), and outputs a SHORTLIST / SKIP verdict with spec gap flags and risk score rationale. No manual spec extraction required from me.

**Category 2 — Shortlist → seller messaging**
Labs reads `latest_decisions.json` SHORTLIST entries and generates one ready-to-send seller message per listing. Each message: condition verification questions, VRAM confirmation grounded against listing text, pickup/postage options, and a negotiation opener anchored to `lf-floor-sync` price patches.

**Category 3 — Triage & negotiation dashboard**
Interactive dashboard ranking all SHORTLIST entries by sprint fitness. Proposes offer bands derived from `lf-floor-sync` price patches. Generates a negotiation script per listing. Filterable, sortable, exportable.

**Category 4 — Retail extension beyond eBay AU**
Use Google Search grounding to discover and compare AU retail options (JB Hi-Fi, Scorptec, PLE, Mwave, Grays Online) against the eBay used-market floors and SRL VRAM tier thresholds. Output a comparative table and buy-vs-wait verdict per GPU tier.

**Category 5 — Spec gap detector & checklist**
Parses listing text or product page. Outputs: missing LLM-critical specs (VRAM, RAM, storage, condition), ambiguous fields requiring seller clarification, and a pre-purchase verification checklist. Runs on any candidate before messaging the seller.

**Category 6 — Alert setup & automation scaffold**
Maps non-eBay-API monitorable endpoints (Dell Outlet AU, Gumtree, Grays, AU retail stock pages) and emits a starter `watcher.py` with BeautifulSoup selectors. Complements `ebay_sniper.py` for non-Browse-API sources — does not duplicate it. Use Google Search grounding to verify current page structures.

</task>

<output_format>

Output exactly 7 fenced YAML spec blocks. No preamble. No closing summary. No meta-commentary. Sequential order only.

```yaml
name:           # repo-style identifier, e.g. lf-url-rubric-labs
pwm_command:    # CLI form; use --labs flag if extending an existing command
relationship_to_opus: |
  # Name the specific Opus or existing workflow this consumes or sits adjacent to.
  # Be concrete: "consumes lf-floor-sync price_patches.json as offer-band anchor"
  # "reads latest_decisions.json SHORTLIST entries produced by hunt.py"
sprint_role: evaluation | triage | negotiation | retail comparison | spec verification | alert wiring
inputs:
  repo_files:
    - # exact path + field scope, e.g.:
    - # config/static_reference_layer.json (vram_gating_logic, target_gpus, risk_gate)
    - # output/decisions/latest_decisions.json (SHORTLIST entries only)
  attachment_method:
    antigravity: # local repo file via IDE file picker
    labs:        # upload JSON / paste JSON snippet into project
    chatgpt:     # upload file into ChatGPT Project
  search_grounding: true | false   # true only for retail price discovery or endpoint verification
labs_outputs:
  reports:  # Markdown with grounded citations (filename + what it contains)
  data:     # CSV / JSON — filename, key fields, intended ChatGPT Projects use
  charts:   # PNG — axes, title, which buying decision it informs
  app:      # views, filter controls, sort options, export actions
human_interaction:
  in_labs:        # what I do inside Perplexity Labs post-run
  in_antigravity: # how output files wire into repo or downstream scripts
  in_chatgpt:     # how I load CSV/JSON for follow-on analysis or code generation
budget_justification: |
  # Why Labs tier. Name ≥2: live search | code generation | interactive UI | charts | ChatGPT export pipeline
done_criterion: |
  # One testable condition. Examples:
  # "dashboard exists with a row for every SHORTLIST entry in latest_decisions.json"
  # "watcher.py contains selector functions for ≥3 non-eBay AU endpoints"
```

</output_format>
