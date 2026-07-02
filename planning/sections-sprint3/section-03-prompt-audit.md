# Section 03: Prompt Audit

## Goal

Audit all `prompts/` files for hardcoded VRAM/RAM/storage thresholds that duplicate SRL config keys. Document disposition of each finding. Fix any that are cleanly fixable (not already addressed by S3-01).

This section runs after S3-01 is committed (UMA threshold already fixed).

## Files to Audit

```
prompts/comet_discovery_agent.txt         (S3-01 fixed UMA line — verify no residual 64GB+)
prompts/alternative_silicon_gemini.txt
prompts/alternative_silicon_perplexity.txt
prompts/ai_studio_runtime.txt
prompts/claude_evidence_analyzer.txt
prompts/gemini_evidence_parser.txt
prompts/system_context.md
prompts/bias_guard_prompt.md
```

## Audit Method

```bash
grep -n "16\|12\|32\|64\|512\|1024\|GB\b" prompts/*.txt prompts/*.md 2>/dev/null
```

## Expected Disposition Table

| File | Hardcoded values | Action |
|------|-----------------|--------|
| `comet_discovery_agent.txt` | `16GB`, `12GB`, `64GB RAM`, `32GB RAM` in Boolean heuristics | **PROSE** — eBay query templates; cannot sentinel without breaking format |
| `alternative_silicon_gemini.txt` | via sentinel pairs | **DONE** — already injected |
| `alternative_silicon_perplexity.txt` | via sentinel pairs | **DONE** — already injected |
| `ai_studio_runtime.txt` | unknown — audit | check and document |
| `claude_evidence_analyzer.txt` | telemetry-derived values | **TELEMETRY** — separate from SRL config; intentionally prose |
| `gemini_evidence_parser.txt` | telemetry-derived values | **TELEMETRY** — separate from SRL config; intentionally prose |
| `system_context.md` | unknown — audit | check and document |
| `bias_guard_prompt.md` | unknown — audit | check and document |

## Implementation Steps

1. Run the grep command above
2. For each finding, classify as: DONE (already sentineled), PROSE (query template — can't sentinel), TELEMETRY (evidence pipeline — intentionally separate from SRL), or FIX (duplicates SRL key and can be sentineled cleanly)
3. Apply any FIX items (add sentinel pairs + update `inject_config.py` `build_substitutions` if a new key is needed)
4. Append findings to this section file as an "Actual Findings" section below

## Disposition Criteria

**PROSE:** The value appears inside a search query string, Boolean expression, or human-readable example where injecting a raw number would break the surrounding format.

**TELEMETRY:** The value comes from the evidence pipeline (`data/evidence/`) and reflects observed workload measurements, not SRL config thresholds. These two governance layers are intentionally separate.

**FIX:** The value duplicates a specific SRL key (e.g. `vram_gating_logic.standard_mobile_min_gb`), appears standalone or in a clearly injectable context, and has no format constraint preventing a sentinel.

## Verification

1. `make test` — green after any prompt edits
2. `make inject-config` — runs without error
3. `make lint` — clean

---

## Actual Findings

**Audit run:** 2026-07-02

### `comet_discovery_agent.txt`
**PROSE** — Boolean eBay query strings contain `16GB`, `12GB`, `32GB`, `64GB`. Values are embedded inside quoted search operator expressions; injecting raw numbers would break the surrounding `(16GB OR 16 GB)` format. S3-01 already fixed the UMA gate line from `64GB+` to `32GB+`.

### `alternative_silicon_gemini.txt`
**DONE** — `UMA_MIN_RAM_GB` sentinel pair present and injected.

### `alternative_silicon_perplexity.txt`
**DONE** — `UMA_MIN_RAM_GB` sentinel pair present and injected. Remaining prose references to `64GB` are the recommended comfort tier (not the gated threshold), appearing in model-config enumeration lists.

### `ai_studio_runtime.txt`
**CLEAN** — No numeric threshold hits. No action needed.

### `claude_evidence_analyzer.txt`
**TELEMETRY** — Values (`32GB`, `64GB`, `512GB`) come from the evidence pipeline (observed workload telemetry), not SRL config keys. Intentionally separate governance layer.

### `gemini_evidence_parser.txt`
**TELEMETRY** — Same rationale as `claude_evidence_analyzer.txt`.

### `system_context.md`
**PROSE** — `≥64GB` appears in a bias-diversity check hint ("ensure at least one UMA candidate at 64GB+"). This is a recommended comfort tier description, not a hard gate threshold. The gated threshold (`uma_unified_min_gb: 32`) is enforced in `decide.py`, not here.

### `bias_guard_prompt.md`
**PROSE** — Same as `system_context.md`. The `≥64GB` lines describe the recommended tier for bias-check sampling diversity, not a config-governed gate.

### Summary

| File | Disposition | Notes |
|------|-------------|-------|
| `comet_discovery_agent.txt` | PROSE | eBay Boolean query strings; S3-01 already fixed UMA gate line |
| `alternative_silicon_gemini.txt` | DONE | Sentinel injected |
| `alternative_silicon_perplexity.txt` | DONE | Sentinel injected |
| `ai_studio_runtime.txt` | CLEAN | No hits |
| `claude_evidence_analyzer.txt` | TELEMETRY | Evidence pipeline — intentionally separate from SRL |
| `gemini_evidence_parser.txt` | TELEMETRY | Evidence pipeline — intentionally separate from SRL |
| `system_context.md` | PROSE | Recommended comfort tier hint, not a gate threshold |
| `bias_guard_prompt.md` | PROSE | Recommended comfort tier hint, not a gate threshold |

**No FIX items found.** All threshold references in prompts are either already sentineled, embedded in prose/query context that cannot be injected, or belong to the separate evidence pipeline governance layer.

`make test` — 178 passed. `make inject-config` — no errors. `make lint` — clean.
