# Model Council & Multi-Model Consensus Concepts for Laptopfinder

This document captures conceptual `pwm` workflows that use multi-model consensus (council-like behaviour) for high-stakes, subjective decisions and scoring governance. These are intentionally more expensive in Pro terms and should be used sparingly. [web:2][web:5][web:6][web:9]

> Note: This file records design ideas; actual wiring to Perplexity’s multi-model features and your `pwm` CLI may be implemented later.

---

## 1. Role of Model Council in the Stack

- Council / multi-model is reserved for:
  - High-stakes capital decisions (~AUD 1,500–4,000+).
  - Changes to scoring weights and global governance.
  - Ambiguous natural language risk parsing and edge-case interpretation.
- It complements Deep Research (data + analysis) and Labs (code + dashboards), not replace them. [web:17][web:20][web:2][web:22][web:29]

---

## 2. Concept: `pwm lf-council-audit` — SRL Scoring Weights Audit

**Purpose**

- Multi-model adversarial audit of `static_reference_layer.json` and `scoring_weights.yaml` to detect biases in Laptopfinder scoring.

**Inputs**

- `config/static_reference_layer.json`
- `config/scoring_weights.yaml`
- `data/hardware_taxonomy.json`

**Outputs**

- `planning/reviews/srl_council_audit.md` — council-backed critique of scoring weights and tiers.
- `planning/patches/srl_weights_patch.json` — proposed changes:
  - Entries like `{path, old_value, new_value, rationale}`.

**Use Cases**

- Run occasionally before major scoring changes.
- Helps avoid over‑rewarding discrete CUDA rigs or under‑valuing UMA/Strix Halo for text-centric workloads.

---

## 3. Concept: `pwm lf-buy-jury` — High-Stakes Listing Jury

**Purpose**

- Multi-model verdict on complex, high-cost second-hand listings: `BUY`, `NEGOTIATE`, or `PASS`.

**Inputs**

- `data/evidence/listing_<id>.json`:
  - `id`, `url`, `title`, `description`, `price_aud`, `vendor_type`, `condition`, baseline price info, current Laptopfinder score.

**Outputs**

- `data/evidence/jury_verdict_<id>.json`:
  - `verdict`, `max_price_aud`, `risk_score`, `confidence`, `notes`.
- `data/evidence/jury_verdict_<id>.md` — human-readable breakdown.

**Use Cases**

- Invoked when you are on the brink of a large AU purchase and want multi-model sanity-checking of risk and value.

---

## 4. Concept: `pwm lf-paradigm-debate` — UMA vs Discrete vs Strix Halo

**Purpose**

- Multi-model debate and synthesis on architecture paradigms for selected LLM workloads (e.g., Llama 3 70B Q4, multi-user 8B serving).

**Inputs**

- `config/workloads/<name>.json` — workload spec (model size, context, concurrency).
- `data/hardware_taxonomy.json` — candidate hardware entries.

**Outputs**

- `research/paradigm_debates/<workload>.md` — debate transcript and synthesis.
- `planning/paradigm_matrix_<workload>.json` — recommended paradigms and tiers per workload.

**Use Cases**

- Used to justify scoring weights and guidance in Laptopfinder docs and dashboards.

---

## 5. Concept: `pwm lf-risk-calibrator` — Edge-Case Risk Gate Tuning

**Purpose**

- Multi-model cross-examination of ambiguous seller descriptions, refining exclusion rules and risk scores.

**Inputs**

- `data/evidence/edge_cases.json` — phrases and current flags/scores.

**Outputs**

- `planning/risk_rules_patch.json` — proposed regex and keyword modifications with examples.
- `data/risk_regression_log.csv` — mapping of phrases to council consensus risk scores and include/exclude decisions.

**Use Cases**

- Run when you notice repeated false positives or false negatives in your Stage 2 firewalls around tricky language.

---

## 6. Concept: `pwm lf-playbook-synth` — AU Procurement & Negotiation Playbooks

**Purpose**

- Council-synthesised procurement and negotiation playbooks tailored to AU markets and specific vendors/tiers.

**Inputs**

- Dossiers from:
  - `research/baselines/*.md`
  - `research/outlet_dossier_*.md`
  - `research/vendor_audit/*.md`
- Example listing scenarios.

**Outputs**

- `planning/playbooks/negotiation_<target>.md`:
  - Message templates (short copy-paste scripts).
  - Pre-purchase checklists.
  - "Walk away if…" criteria.

**Use Cases**

- Bridge between Laptopfinder analytics (scores, baselines, vendor risk) and your actual negotiation tactics.

---

## 7. Routing Guidance: Council vs Deep Research vs Labs

**Use Council**

- High-stakes, subjective, ambiguous tasks:
  - Architectural governance (`lf-council-audit`, `lf-paradigm-debate`).
  - Expensive listing decisions (`lf-buy-jury`).
  - Edge-case language interpretation (`lf-risk-calibrator`). [web:2][web:5][web:6][web:9]

**Use Deep Research**

- Data-heavy, citation-rich tasks:
  - Market scans, pricing baselines, silicon facts, vendor audits. [web:17][web:20][web:26][web:28]

**Use Labs**

- Project/code/app generation:
  - Daemons, dashboards, scraper rules, test suites. [web:2][web:22][web:29]
