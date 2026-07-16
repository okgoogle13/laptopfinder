# PVM & MCP Execution Audit: Plan vs. Reality

## Goal
Hold all agents (Claude, Gemini, Perplexity) accountable for the actual state of the codebase. Eliminate hallucinated progress regarding the PVM-first recommendation engine, Perplexity MCP workflows, and Gemini API integration.

## 1. Current PVM + MCP State Snapshot
*(Grounded strictly in observable repo files)*

- **Routing Logic:** Centralised in `src/laptopfinder/decide.py` and `config/static_reference_layer.json` (Confirmed via recent simplification).
- **Perplexity Integration:** A script was previously noted alongside prompts (`prompts/perplexity_research_prompt_refined.md`), but a formal, standard MCP server manifest/configuration linking it directly to Claude's tool context is missing or undocumented in the repo root. *(Reality Check: `src/laptopfinder/runners/perplexity.py` was deleted/folded into `ebay_hunter.py` per GitHub issues #13–14).*
- **Gemini Integration:** A runner (`src/laptopfinder/runners/aistudio.py`) was previously noted alongside parsing prompts (`prompts/gemini_evidence_parser.txt`), but the automated handoff from Perplexity-enriched data to Gemini is not verifiably codified in a single orchestration script. *(Reality Check: `aistudio.py` was also deleted/folded into `ebay_hunter.py` per GitHub issues #13–14).*
- **PVM Artifacts:** Schemas exist (`src/laptopfinder/schemas/stage2.analysis.schema.json`), but the final enriched recommendation rendering (combining pipeline decisions + MCP research + Gemini synthesis) into `output/shortlist/latest_shortlist.md` lacks a unified integration test.

## 2. Plan vs Reality: PVM + MCP + Gemini

| Work Area | Expected Plan | Actual Repo Reality | Verdict |
| :--- | :--- | :--- | :--- |
| **Core Decision Engine** | `decide.py` governs all scoring and `SKIP`/`MONITOR`/`SHORTLIST` states. | `src/laptopfinder/decide.py` exists and is the designated routing source of truth. | Done |
| **Perplexity MCP Workflow** | Claude uses Perplexity via an MCP server for real-time AU market context/enrichment. | Python runner `perplexity.py` has been deleted/deprecated (`CLAUDE.md`/`AGENTS.md`), and explicit MCP server definition/manifest (`mcp_server.json` / `claude_desktop_config.json`) is missing. Claude may be hallucinating tool availability. | Needs Verification / Diverged |
| **PVM Recommendation Logic** | Enriched candidates are audited by Claude/Gemini to form a purchasing narrative. | Prompts exist (`claude_audit.txt`), but no strict code pipeline enforces this step post-Stage 2 without human intervention. | Partially Done |
| **Gemini API Layer** | Gemini API is called for final qualitative synthesis. | Runner `aistudio.py` deleted/deprecated (`CLAUDE.md`/`AGENTS.md`); orchestration pipeline linking it sequentially after Perplexity is undocumented. | Partially Done |

## 3. Complete Remaining Work: Sprints and Tasks
Every gap between plan and reality is defined below. If a task is not here, it is not part of the current verified workflow.

### Sprint 1: Verify & Lock the MCP Integration
**Goal:** Prove the Perplexity MCP integration is real, codified, and reproducible.

- **Task 1.1: Formalise MCP Server Configuration**
  - **Description:** Locate or create the formal MCP server manifest (e.g., `claude_desktop_config.json` snippet or `mcp_server.json`) required for Claude to access Perplexity tools natively.
  - **Files:** `config/mcp_integration.json` (To be created/verified).
  - **Change:** Document the exact env vars and command to boot the Perplexity MCP server.
  - **Validation:** Run the MCP server locally; verify Claude can read the tools via `mcp list`.

- **Task 1.2: Wire Perplexity / Market Enrichment to Standard Outputs**
  - **Description:** Ensure the market enrichment runner strictly reads from `output/decisions/latest_decisions.json` and writes its enriched context to a defined evidence path.
  - **Files:** `src/laptopfinder/runners/` enrichment workflow.
  - **Change:** Remove any ad-hoc data pathing. Route outputs to `data/evidence/` or append to the shortlist markdown directly.
  - **Validation:** `pytest tests/test_perplexity_runner.py` (needs to be created if missing).

### Sprint 2: Gemini Synthesis & PVM Pipeline Orchestration
**Goal:** Connect the output of the core pipeline + Perplexity research into the Gemini API for final recommendation synthesis.

- **Task 2.1: Enforce Strict Gemini Guardrails**
  - **Description:** Update qualitative review prompts/helpers to ensure they only read shortlisted candidates. They must not have the ability to change `decide.py` scores.
  - **Files:** `prompts/system_context.md` and related qualitative auditors.
  - **Change:** Inject system prompts explicitly stating Gemini/Claude is a qualitative reviewer, not a quantitative router.
  - **Validation:** Grep runner code for any logic that modifies `candidate["status"]`. Ensure it is read-only.

- **Task 2.2: Codify the Enriched Shortlist Render**
  - **Description:** Create a distinct script or Makefile target that triggers the qualitative audit on the shortlist.
  - **Files:** `scripts/render_pvm_shortlist.py` (or update `scripts/render_matrix.py`), `Makefile`.
  - **Change:** Add a `make enrich` target that executes qualitative enrichment over `output/shortlist/latest_shortlist.md`.
  - **Validation:** Run `make enrich` and confirm a human-readable narrative is appended to the shortlist.

### Sprint 3: End-to-End PVM Pipeline Testing
**Goal:** Prove the entire stack works without agent intervention.

- **Task 3.1: End-to-End Dry Run**
  - **Description:** Execute Stage 1 -> Stage 2 -> Enrichment -> Qualitative Audit in a single automated flow.
  - **Files:** `Makefile`, `scripts/ebay_sniper.py`.
  - **Change:** Chain the runners in a single shell script or Makefile target (`make sniper-full`).
  - **Validation:** Run `make sniper-full`. Verify `output/shortlist/latest_shortlist.md` contains both data matrix AND AI synthesis.

## 4. Issues, Risks, and Clarifications
- **Risk - Phantom MCP Setup:** `perplexity.py` was deleted/deprecated, and no native MCP configuration files exist in the repository. **Question for User/Claude:** Is Perplexity being called via standard REST API within Python runners (`ebay_hunter.py`), or is Claude literally supposed to use an MCP server? If REST API, we must rename tasks to reflect standard API usage, not MCP. *(Provisional Task: Audit and confirm connection method).*
- **Risk - Orchestration Gap:** Currently, runners seem disconnected. E.g., `ebay_sniper.py` runs, then how does enrichment know to start? Are we relying on human/Claude prompting to string them together? *(Action: Task 3.1 is critical to fix this).*

## 5. Handover to Claude + Perplexity + Gemini
**Instructions for Claude Code (Local Execution):**
- **Enforce Spec-to-Task Bridge (Strict):** Do not treat this audit as a passive design document. Per `CLAUDE.md` / `AGENTS.md`, you MUST immediately bridge this spec to tracked tasks by extracting Sprints 1, 2, and 3 into `TASKS.md` and `sprint.md`, and queueing Task 1.1 in `STATUS.md` (`NEXT_TASK`) before implementing. Never leave newly specified workflows un-tracked.
- **Do not assume work is done:** You are strictly accountable for completing the following top tasks and updating `TASKS.md` and `STATUS.md` with explicit proof (commit hashes or file checks).
- **Execute Task 1.1:** Locate and formalise the exact Perplexity MCP integration config. If it does not exist, explicitly state: "MCP config missing, building REST API fallback or creating MCP manifest."
- **Execute Task 1.2:** Audit enrichment outputs to ensure they only read `latest_decisions.json`.
- **Execute Task 2.1:** Audit synthesis logic to ensure strict read-only boundaries are enforced regarding pipeline states.
- **Execute Task 2.2:** Update `Makefile` to include a `make enrich` target that chains the enrichment runners.
- **Claude:** You must answer the "Phantom MCP Setup" risk question before proceeding to Sprint 2.
