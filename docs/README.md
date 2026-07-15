# Laptopfinder Documentation Index

Welcome to the Laptopfinder documentation. This directory contains guides and conceptual designs for different runners, daemons, and Perplexity workflows in the procurement pipeline.

## Active vs. Proposed Comma
*   **Active Commands:** Implemented in your shell configuration at [~/.config/pwm/workflows.zsh](file:///Users/okgoogle13/.config/pwm/workflows.zsh). Sourcing this file loads the CLI tools shown in `pwmh` (e.g., `lf-score`, `lf-watchlist`, `lf-price-sweep`, `compare`).
*   **Proposed/Conceptual Workflows:** The newly added `pwm_*.md` files detail proposed integrations (e.g., `pwm lf-outlet-dossier`, `pwm lf-alert-forge`, `pwm lf-buy-jury`). These are design blueprints and are not yet defined as commands in `workflows.zsh`.

## Active System Documentation

*   [eBay Sniper Daemon](file:///Users/okgoogle13/Projects/laptopfinder/docs/ebay_sniper.md) — Guide to running the background sniper daemon (`scripts/ebay_sniper.py`), configuring alerts, and monitoring local/national eBay listings.

## Perplexity `pwm` Integration Workflows

We use custom `pwm` workflows to leverage Perplexity Deep Research, Perplexity Labs, and conceptual Model Council environments. Refer to these files for details on data schemas, inputs, outputs, and routing guidelines:

*   [Deep Research Workflows](file:///Users/okgoogle13/Projects/laptopfinder/docs/pwm_deep_research.md) — For data-heavy sweeps, pricing baselines, silicon gap-grounding, and vendor risk profiles.
*   [Labs Workflows](file:///Users/okgoogle13/Projects/laptopfinder/docs/pwm_labs_workflows.md) — For local tool/code creation, dashboards, and sandboxes (e.g., alert-forge, compare-studio, matrix-app).
*   [Model Council & Consensus Concepts](file:///Users/okgoogle13/Projects/laptopfinder/docs/pwm_council_concepts.md) — Conceptual architectures for multi-model jury decisions, risk calibrators, and adversarial weights audits.

---

### Routing Cheat-Sheet

| Workflow Mode | Use Case | Token Category / Cost | Output Types |
| :--- | :--- | :--- | :--- |
| **Deep Research** | High-density multi-source searches, baselines, audits | Deep Research (1 research token per run; 20 remaining) | MD Dossier, JSON Data |
| **Labs (Create Files & Apps)** | Script/HTML dashboard generation, regex helpers | Labs / Create Files & Apps (1 Labs run; 25 remaining) | Ready-to-run Local Code |
| **Model Council** | Subjective, subjective risk, high-value buy/pass jury | Multi-Model / Pro (e.g., 4 Pro Search tokens per run) | Verdict, Patch Config |

