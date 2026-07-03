# Sprint 6 — Architecture Penalty + eBay-AU Validation (laptopfinder)

## Context

The user asked to continue a "Sprint 3" deep-plan covering three follow-ups: (1) integrate
`storage_gb` from the evidence pipeline into the SRL, (2) wire the Turing-vs-Ada architecture
penalty into `decide.py`, and (3) add 8 Boolean discovery search terms + document blind spots.

Direct repo inspection (not memory) showed `TASKS.md` — the most current, authoritative
roadmap doc (2026-07-02) — already marks two of these three done under earlier sprints:

- **storage_gb → SRL**: done. `storage_floors: {min_gb: 512, recommended_gb: 1024}` exists in
  `config/static_reference_layer.json`, matches `data/evidence/targets.json`, has passing tests.
- **Discovery Boolean terms + blind spots**: done. All 8 terms from the July 2026 market
  topology report §8.1 are verbatim in `prompts/comet_discovery_agent.txt:40-47`; CLAUDE.md
  already documents 3 blind spots.
- **Architecture penalty**: genuinely outstanding. `_apply_architecture_penalty()` in
  `decide.py:315-322` is still a no-op stub. TASKS.md scopes this as its own **"Sprint 6"**
  item, not Sprint 3.

The user confirmed via AskUserQuestion: plan this session as **Sprint 6**, matching TASKS.md's
existing roadmap ID, rather than re-doing already-shipped work under a stale "Sprint 3" label.

While verifying the baseline, I also found the repo is **not currently green**:
`.venv/bin/python -m pytest tests/ -q` → **3 failed, 177 passed** (confirmed by direct run).
Root cause: commit `604d674` (today) deliberately promoted RTX 5090 from `watch_list` to
`target_gpus` in the SRL (with a reasoned note about occasional budget bargains) but didn't
re-run `make inject-config` or update two dependent tests. This must be resolved before Sprint
6 work lands on a trustworthy baseline, so it's Phase 0.

Two independent design/peer-review passes converged on the implementation approach below,
including one correction: the SRL's own `architecture_adjustments._comment`/`applies_when`
text currently describes a *pairwise* Turing-vs-Ada comparison, but the only feasible
implementation (given `decide()` scores one listing at a time) is a *single-listing heuristic*.
That policy reinterpretation must be reflected in the SRL text itself, not just the code
docstring — otherwise the config keeps describing semantics the code doesn't implement.

---

## Phase 0 — Repair pre-existing baseline regression (confirm)

**Objective:** Get `make test` green again before any Sprint 6 code lands, without silently
discarding today's deliberate RTX 5090 config decision.

**Root cause (verified):** `git show 604d674 -- config/static_reference_layer.json` confirms
RTX 5090 moved from `watch_list` into `target_gpus` (`market_verdict: HOLD`, note: "Kept as
target because bargains occasionally drop into the budget window despite standard retail
pricing"). This is a deliberate, reasoned edit — treat the config as authoritative and fix the
drift, not revert it.

**Failing tests (confirmed by direct run):**
- `tests/test_decide.py::TestIsWatch::test_watch_gpu` — asserts `_is_watch("RTX 5090", REF) is True`; now `False`.
- `tests/test_decide.py::TestDecide::test_watch_list_routes_to_monitor` — fixture GPU `"RTX 5090 GPU"` no longer routes to MONITOR.
- `tests/test_prompt_parity.py::test_prompt_injection_sync` — injected `TARGETS` block in `prompts/comet_discovery_agent.txt` (and the other two sentinel-marked prompt files) is out of sync with the SRL.

**Files to touch:**
- `prompts/comet_discovery_agent.txt`, `prompts/alternative_silicon_gemini.txt`, `prompts/alternative_silicon_perplexity.txt` — regenerated via `make inject-config`, not hand-edited.
- `tests/test_decide.py` — `TestIsWatch::test_watch_gpu` and `TestDecide::test_watch_list_routes_to_monitor`: swap the GPU string from `"RTX 5090"` to `"GB200"` (confirmed still in `watch_list`, not yet promoted).

**Commands:**
```
make inject-config
.venv/bin/python -m pytest tests/test_decide.py tests/test_prompt_parity.py -v
```

**Checkpoint: confirm** — changes two test assertions and regenerates 3 prompt files; not part of the original three tasks, so surface the diff before proceeding.

---

## Phase 1 — Implement `_apply_architecture_penalty()` (confirm)

**Objective:** Replace the no-op stub with real logic, reusing existing SRL data rather than
introducing a new runtime file load.

**Design (validated by two review passes):** Extract a small shared helper
`_resolve_gpu_generation(gpu, ref) -> str | None` from the substring-match loop currently
inlined in `_gpu_generation_points()` (`decide.py:225-245`), which resolves a GPU name to its
generation string via `ref["llm_index_score"]["gpu_generation_by_name"]` (using the
precomputed `_gen_by_name_lower` cache from `_precompute_ref`). Both `_gpu_generation_points`
and the new `_apply_architecture_penalty` call this helper — reuse, not duplication, of a loop
that already has a documented perf rationale (avoids the two copies drifting).

```python
def _resolve_gpu_generation(gpu: str | None, ref: dict) -> str | None:
    if not gpu:
        return None
    cfg = ref.get("llm_index_score", {})
    gpu_lower = gpu.lower()
    gen_by_name_lower = ref.get("_gen_by_name_lower") or {
        k.lower(): v for k, v in cfg.get("gpu_generation_by_name", {}).items()
    }
    for name_lower, generation in gen_by_name_lower.items():
        if name_lower in gpu_lower:
            return generation
    return None
```

`_gpu_generation_points` shrinks to delegate to it; `_apply_architecture_penalty` becomes:

```python
def _apply_architecture_penalty(gpu: str | None, tier: str | None, ref: dict) -> int:
    if tier is None:
        return 0
    if _resolve_gpu_generation(gpu, ref) != "Turing":
        return 0
    return ref.get("architecture_adjustments", {}).get("turing_vs_ada_same_vram_penalty_pts", 0)
```

No change to the call site (`decide.py:383`).

**Deliberate deviation from TASKS.md's literal Sprint 6 text:** TASKS.md says to read Turing
GPU names from `config/silicon_profiles.yaml`'s `discrete_cuda.architecture_tiers.turing.gpus`
— verified this key path doesn't exist (the real structure is `turing_sm75`/`ada_sm89` with
capability flags only, no GPU list), and CLAUDE.md documents that `silicon_profiles.yaml` is
"not loaded at runtime by decide.py." Sourcing from the SRL's existing `gpu_generation_by_name`
avoids violating that invariant.

**Policy-text sync (peer-review finding — do this in the same phase, not deferred to Phase 4):**
The SRL's `architecture_adjustments` block currently reads:
```json
"applies_when": "vram_tier_equal AND generation_A == 'Turing' AND generation_B == 'Ada Lovelace'",
"_comment": "Reserved for future pairwise comparison logic. Penalty is additive to the existing gen-points gap (Turing=5 vs Ada=20)."
```
Update both fields in `config/static_reference_layer.json` to describe the actual implemented
behavior (single-listing heuristic — penalty applies whenever a listing's GPU resolves to
Turing generation with a known VRAM tier, regardless of whether an Ada comparator is present in
the same batch; true pairwise resolution remains a BACKLOG item). This is text-only — no
threshold/weight values change — but it's part of "wiring" the penalty, since the config should
not keep describing semantics the code doesn't implement.

**Files to touch:**
- `src/laptopfinder/decide.py` (lines 225-245, 315-322)
- `config/static_reference_layer.json` (`architecture_adjustments.applies_when` / `_comment` text only)

**Commands:**
```
.venv/bin/python -m py_compile src/laptopfinder/decide.py
.venv/bin/python -m pytest tests/test_decide.py -v
```

**Checkpoint: confirm** — changes production scoring: every Turing-GPU listing's `llm_index_score` drops by 2 points from now on.

---

## Phase 2 — Tests: rewrite unit tests + add integration coverage (confirm)

**2a. Rewrite `TestApplyArchitecturePenalty`** (`tests/test_decide.py:731-739`) — currently
hardcodes `== 0` for a Turing GPU input; that assertion is stub-era and must flip:

```python
class TestApplyArchitecturePenalty:
    def test_turing_gpu_receives_architecture_penalty(self):
        expected = REF["architecture_adjustments"]["turing_vs_ada_same_vram_penalty_pts"]
        assert _apply_architecture_penalty("Quadro RTX 5000", "mid", REF) == expected

    def test_ada_gpu_receives_no_architecture_penalty(self):
        assert _apply_architecture_penalty("RTX 4090", "mid", REF) == 0

    def test_none_gpu_returns_zero(self):
        assert _apply_architecture_penalty(None, "mid", REF) == 0

    def test_none_tier_returns_zero_even_for_turing_gpu(self):
        assert _apply_architecture_penalty("Quadro RTX 5000", None, REF) == 0

    def test_unrecognized_gpu_returns_zero(self):
        assert _apply_architecture_penalty("Some Unknown GPU 9999", "mid", REF) == 0
```

Asserting against `REF["architecture_adjustments"][...]` rather than a hardcoded `-2` avoids a
magic number. Confirmed via grep: no other test/fixture references "Quadro" GPUs, so no other
existing test's expected score shifts.

**2b. Integration fixture.** Add `tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json`,
mirroring the existing `tests/fixtures/stage2/ebay_rtx4090_laptop.json` structure exactly (same
16GB VRAM → `mid` tier) but with GPU/model/title swapped to a Turing part (e.g. Dell Precision
7760 / Quadro RTX 5000), so the only scoring delta between the two fixtures is the
generation-points gap plus the new architecture penalty.

Add a test (verified safe: `decide.py:389-507` calls `calculate_llm_index_score()`
unconditionally — no DEFER/market_verdict short-circuit exists — so comparing `llm_index_score`
via the full `decide()` wrapper is valid):

```python
class TestArchitecturePenaltyIntegration:
    def test_turing_gpu_scores_lower_than_equivalent_ada_gpu(self):
        ada = load_fixture("ebay_rtx4090_laptop.json")["analysis_output"]
        turing = load_fixture("ebay_quadro_rtx5000_turing.json")["analysis_output"]
        assert decide(turing, REF)["llm_index_score"] < decide(ada, REF)["llm_index_score"]
```

**Files to touch:** `tests/test_decide.py`, `tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json` (new).

**Commands:**
```
.venv/bin/python -m pytest tests/test_decide.py -v
.venv/bin/python -m pytest tests/ -q
```

**Checkpoint: confirm** — test+implementation are one logical change; review together.

---

## Phase 3 — Regression check: Tasks 1 & 3 already-shipped work (auto)

No production code changes.

**storage_gb (Task 1):** already covered by `TestSrlStorageFloors::test_storage_floors_min_gb`
/ `test_storage_floors_recommended_gb`. No new test needed — just re-run as part of the full
suite.

**Discovery prompt (Task 3):** confirmed the 8 Boolean terms are verbatim in
`prompts/comet_discovery_agent.txt:40-47`, but no existing test asserts their presence — they
sit outside the sentinel-injected blocks that `test_prompt_parity.py`/`test_prompt_markers.py`
cover. Close this gap with one small regression test in `tests/test_prompts.py` (match its
existing path-resolution convention) asserting each of the 8 literal Boolean strings is present
in the file. Optionally, one more assertion that CLAUDE.md still contains a "Discovery Blind
Spots" section with "RAM/VRAM conflation" — low priority, skip if reviewer prefers minimal.

**Files to touch:** `tests/test_prompts.py` (new test function(s) only).

**Commands:**
```
.venv/bin/python -m pytest tests/test_decide.py::TestSrlStorageFloors tests/test_prompts.py -v
```

**Checkpoint: auto** — purely additive, no existing test or production code touched.

---

## Phase 4 — Documentation sync (auto)

**CLAUDE.md** — add one bullet to "Key invariants" (after the existing UMA-ceiling bullet)
documenting that `_apply_architecture_penalty()` is a per-listing Turing heuristic, not a
pairwise comparator, and why (mirrors the SRL text updated in Phase 1).

**TASKS.md** — flip `[IDE/DEV]` checklist items under "Sprint 6 — Architecture Penalty +
eBay-First End-to-End Validation" to `[x]` for what actually lands in Phases 0-3; leave
`[HUMAN]` items (live scraping, real URLs, `make scrape-and-live`, matrix rendering,
`make scan-gaps`) unchecked pending human execution. Correct the inaccurate
`silicon_profiles.yaml` key-path claim in the "Architecture Penalty" checklist item to describe
what was actually implemented (SRL `gpu_generation_by_name` via `_resolve_gpu_generation()`).
Do **not** mark the whole Sprint 6 header `## COMPLETE:` while `[HUMAN]` live-validation items
remain open — that's exactly the "marked done, wasn't" drift Phase 0 just fixed. Replace the
stale "≥111 tests expected" figure with the real post-Sprint-6 count (get via
`pytest --collect-only -q` after Phases 0-3 land).

**memory/project/sprint.md** — update frontmatter `description` (currently describes a stale
"Active sprint — June 2026..." state) and replace the trailing `## Sprint 3 (pending)` block
(which lists these same three tasks as still-pending) with a `## Sprint 6` summary of what
actually shipped, following the file's existing "Why / Status / Changes shipped" structure used
elsewhere in the same doc.

**memory/MEMORY.md** — update the one stale link description currently reading "Sprint —
Pipeline Audit June 2026... active sprint goals" to reflect Sprint 6.

**Files to touch:** `CLAUDE.md`, `TASKS.md`, `memory/project/sprint.md`, `memory/MEMORY.md`.

**Commands:** none required (doc-only); optionally re-run `make test` as a final sanity check.

**Checkpoint: auto** — doc-only, reversible via git diff review. The one judgment call (TASKS.md
Sprint 6 header status) still deserves a quick glance before committing.

---

## Phase 5 — eBay-AU-only end-to-end smoke test

**Reality check:** `data/urls.txt` currently contains only placeholder comments, no real
listing URLs — confirmed via grep. True live validation needs a human with real URLs and valid
API keys; it cannot be completed inside this automated session.

**5a. Fixture-driven fallback (automatable — auto):**
```
make decide FIXTURE=tests/fixtures/stage2/ebay_rtx4090_laptop.json
make decide FIXTURE=tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json
make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json
make test
```
Confirms the wired penalty is visible end-to-end at the `decide()` layer without live network
access. Note: `make test` runs append to the git-tracked
`data/evidence/undiscovered_hardware.jsonl` log as a side effect — expect `git status` to show
it dirty after any test run; this is a pre-existing hygiene quirk, out of scope to fix here.

**5b. Human live-validation checklist (confirm, human-in-loop — cannot be automated this session):**
1. Populate `data/urls.txt` with ≥3 real eBay AU laptop listing URLs.
2. Confirm `FIRECRAWL_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY` are valid in `.env`.
3. Run `make inject-config` (if not already fresh from Phase 0) then `make scrape-and-live`; capture any crashing/rejected listing as a new `_failing`-suffixed fixture in `tests/fixtures/stage2/` and route it back through Phase 1-2's pattern (isolate, patch, add regression test).
4. Assemble `data/shortlist_candidates.jsonl` from console SHORTLIST output, run `make render-matrix`, and sanity-check ranking (RTX 3080/3080 Ti 16GB should rank above RTX 4090 16GB on price-to-VRAM ratio).
5. Run `make scan-gaps` on live feed files; log any actionable alerts as new `BACKLOG` entries in `TASKS.md`.

**Checkpoint:** 5a auto, 5b confirm/human-in-loop — present 5a's fixture-driven proof as the
completion criterion for the automatable portion of Sprint 6, with 5b tracked as a separate
human follow-up.

---

## Verification

- `make test` green after every confirm-checkpoint phase (0, 1, 2), with the final count
  recorded for Phase 4's doc sync.
- `make decide FIXTURE=tests/fixtures/stage2/ebay_quadro_rtx5000_turing.json` shows a non-zero,
  negative architecture-penalty contribution and a lower `llm_index_score` than the equivalent
  RTX 4090 fixture.
- `git diff` review of `config/static_reference_layer.json` (Phase 1's `_comment`/`applies_when`
  text edit) confirms no threshold/weight values changed, only descriptive text.
- Phase 5a's fixture-driven commands run clean with no traceback; Phase 5b remains an explicit
  human handoff, not silently marked complete in TASKS.md.

## Open assumptions

- **Phase 0:** RTX 5090's promotion to `target_gpus` (commit `604d674`) is treated as
  intentional and correct; tests/prompts are resynced to match it rather than reverting the SRL
  change. Confirmed reasonable via the commit's own rationale note, but flagged for a final
  glance before landing.
- **Phase 1/4:** the "flat per-listing Turing penalty" is a deliberate, disclosed
  reinterpretation of the SRL's originally-pairwise `applies_when` condition — accepted by two
  independent design passes as the only feasible option given `decide()`'s single-listing scope,
  with true pairwise resolution left in TASKS.md's BACKLOG for a future batch-ranking pass.
