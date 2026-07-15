# Codex Runner Audit Report

**Generated:** 2026-07-08T01:52:27Z

---

## Overview

The runner layer is split between three different jobs that overlap too much: LLM wrappers for the old raw-text pipeline, evidence-pipeline support, and eBay acquisition utilities. The only part that clearly still earns its place in the buying workflow is the structured eBay path; the prompt wrappers are brittle and mostly legacy, and the evidence pipeline is a side channel rather than a purchase path.

---

## Runner Classification & Analysis

### 1. `comet.py`
- **Purpose:** Stage 1 discovery wrapper that sends raw text to Gemini using `prompts/comet_discovery_agent.txt` and returns a candidate list. It is invoked directly by `src/laptopfinder/core.py:78` and indirectly by `Makefile:26`.
- **Current Dependencies:** `src/laptopfinder/core.py:78`, `src/laptopfinder/core.py:173`, `Makefile:26`, prompt parity tests around the prompt file, and Stage 1 fixture tests only for the downstream firewall, not this runner itself.
- **Status:** Legacy / likely no longer needed.
- **Recommendation:** Deprecate.
- **Brittleness:** No retry/backoff, no structured error handling beyond `ValueError`/`FileNotFoundError`, prompt coupling to a mutable external file, and a direct dependency on Gemini for the first gate in the pipeline. It is also duplicative with the eBay acquisition runners and keeps the fragile raw-text live path alive.

### 2. `aistudio.py`
- **Purpose:** Stage 2 analysis wrapper that sends a handoff packet plus listing text to Gemini using `prompts/ai_studio_runtime.txt`. It is called by `src/laptopfinder/core.py:78`.
- **Current Dependencies:** `src/laptopfinder/core.py:78`, `src/laptopfinder/core.py:173`, and the live `make live` target.
- **Status:** Legacy / likely no longer needed.
- **Recommendation:** Deprecate.
- **Brittleness:** Same provider coupling as `comet.py`, no fallback strategy, no robust handling for malformed model output, and it duplicates the Stage 2 role that the repo already verifies deterministically in `src/laptopfinder/core.py:42`.

### 3. `claude_audit.py`
- **Purpose:** Optional post-decision audit pass over Stage 2 analysis plus decision output. It is only invoked when `run_live_pipeline(..., run_audit=True)` is used.
- **Current Dependencies:** `src/laptopfinder/core.py:78`, the `--audit` flag in the live CLI path, and the `make live` target by transitive invocation.
- **Status:** Secondary / optional.
- **Recommendation:** Keep but mark legacy.
- **Brittleness:** Hidden provider fallback from Anthropic to Gemini, no schema for the audit output, and no downstream enforcement. It is useful only as an after-the-fact review aid, not as a core workflow step.

### 4. `perplexity.py`
- **Purpose:** Deep research runner for long-form market research, not listing acquisition.
- **Current Dependencies:** No Makefile target or runtime path in `core.py`; it is only referenced by docs, prompt files, and historical research artifacts. There is no active production dependency.
- **Status:** Legacy / likely no longer needed.
- **Recommendation:** Deprecate.
- **Brittleness:** Hard-coded local-proxy fallback behavior, no structured output, and no integration with the buy/sell decision loop. This is research tooling, not an operational runner.

### 5. `evidence_pipeline.py`
- **Purpose:** Two-stage human-in-the-loop evidence pipeline that turns telemetry into Gemini prompts, aggregates parsed JSON, and generates a Claude handoff when enough records exist.
- **Current Dependencies:** `Makefile:32`, `Makefile:36`, `Makefile:40`, and `tests/test_evidence_pipeline.py:14`.
- **Status:** Secondary / optional.
- **Recommendation:** Keep and harden.
- **Brittleness:** Heavy manual handoff steps, sidecar hash state, multiple silent `except Exception` blocks, and prompt/file-path coupling. That said, it has a distinct purpose: deriving configuration from real telemetry, not finding a specific laptop listing. It belongs, but only as an optional research/feedback loop.

### 6. `ebay_hunter.py`
- **Purpose:** Main structured eBay acquisition runner. It fetches Browse API listings, enriches them with Gemini, reuses `core.run_stage2` and `decide`, and can email new shortlist-grade targets.
- **Current Dependencies:** `Makefile:61`, `Makefile:98`, `Makefile:119` via shared token helpers, `tests/test_ebay_hunter.py:1`, and `tests/test_ebay_hunter.py:1` indirectly.
- **Status:** Primary / still intended.
- **Recommendation:** Keep and harden.
- **Brittleness:** Large surface area, lots of moving parts, and the comments promise “no non-stdlib HTTP” while still depending on Gemini. It is also doing too much at once: search, normalization, multimodal enrichment, grounding, scoring, and alerting. Even so, it is the clearest acquisition-oriented runner in the repo and is more outcome-driven than the raw-text live pipeline.

### 7. `ebay_deals.py`
- **Purpose:** Narrow clearance-seller sweep over the eBay Browse API for dealer/refurbisher accounts in `clearance_sellers`.
- **Current Dependencies:** `Makefile:119`, `tests/test_ebay_deals.py:4`, and token helpers from `ebay_hunter.py`.
- **Status:** Secondary / optional.
- **Recommendation:** Keep but mark legacy.
- **Brittleness:** Tiny and hard-coded, with env-driven price bounds and a narrow seller list. It is useful as a niche clearance sweep, but it is not part of the smallest viable “find and buy a laptop” workflow.

### 8. `ebay_api.py`
- **Purpose:** Simplified direct eBay Browse API pipeline that builds a Stage 2-shaped dict from API item summaries and runs `decide`.
- **Current Dependencies:** `Makefile:56`, `tests/test_ebay_api.py:4`.
- **Status:** Legacy / likely no longer needed.
- **Recommendation:** Replace with a simpler path.
- **Brittleness:** Hard-coded query string, hard-coded category filter, silent recovery to empty lists on errors, and duplicate extraction logic that overlaps with `ebay_hunter.py`. It is simpler than `ebay_hunter.py`, but it is also less governed and more ad hoc. If we want a lean primary path, this should either be folded into the structured hunter or removed.

---

## Proposed Primary Workflow

1. **Unified Acquisition Path:** Use one acquisition path only—a structured eBay Browse API sweep with SRL-driven queries and filters.
2. **Deterministic Grounding:** Keep deterministic grounding in `src/laptopfinder/core.py:42` and `src/laptopfinder/core.py:140`, not in LLM wrappers.
3. **Core Entry Point:** Make the eBay acquisition runner the main operational entry point; retire the raw-text Gemini live pipeline from the default path.
4. **Research & Audit Isolation:**
   - Keep `evidence_pipeline.py` only as a separate research/config feedback loop.
   - Keep `claude_audit.py` only as an optional post-hoc check, never as a gate.
5. **Deprecations:** Deprecate the Perplexity and raw Gemini runners unless a concrete operator workflow still depends on them.
