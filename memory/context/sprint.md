---
name: final-sprint-plan
description: Implementation plan for the benchmark pipeline final sprint
metadata:
  type: project
---

# Final Sprint — Benchmark Pipeline

**Why:** The decision engine and scoring logic exist but have never been validated against real listings. This sprint builds the ground-truth benchmark dataset and uses it to verify the pipeline routes known-good listings to SHORTLIST with accurate scores.

## Sequence

### 1. Collect saved HTML pages
Save one listing per platform manually using browser "Save Page As":
- eBay AU: target RTX 4090 / 4080 laptops, MSI Titan, Alienware m18, ASUS ROG
- FB Marketplace: same targets — save as HTML (FB is client-rendered; JSON-LD in saved page is the reliable surface)
- Gumtree: high-VRAM laptops in AU

Name files with platform prefix: `ebay_msi_titan.html`, `fb_alienware_m18.html`, `gumtree_rtx4080.html`

Place in `saved_pages/` directory.

### 2. Run scraper
```bash
python -m laptopfinder.scrape_benchmark --html-dir saved_pages/ --out benchmark.jsonl
```

**Inspect output carefully:**
- Is `full_listing_text` the actual listing body, or nav/boilerplate?
- Are title and price captured correctly?
- Tune CSS selectors in `scrape_benchmark.py` if needed (eBay selectors most likely to need adjustment)

**Known risks:**
- eBay: specifics table uses obfuscated class names that change — `x-item-description` and `ux-layout-section--features` may need updating
- FB: JSON-LD only present in some saved pages; `og:description` fallback is truncated
- Gumtree: `price-amount` selector is a best-guess against real DOM

### 3. Run Stage 1 LLM pass
Feed each `full_listing_text` through the comet.py Stage 1 runner to populate `inferred_*` fields.

Or: manually populate `inferred_*` in `handoff_packet` for speed (acceptable for benchmark fixtures).

### 4. Assemble Stage 2 fixtures
For each listing, create a Stage 2 fixture file in `tests/fixtures/stage2/`:
```json
{
  "handoff_packet": { ... },
  "full_listing_text": "...",
  "analysis_output": { ... }
}
```
Run through `aistudio.py` Stage 2 runner to generate `analysis_output`, or author manually.

### 5. Validate with decision engine
```bash
make decide FIXTURE=tests/fixtures/stage2/ebay_msi_titan.json
```
Expected: `SHORTLIST` for all ground-truth high-VRAM listings.

Check `llm_index_score` is plausible:
- RTX 4090 16GB laptop should score ~75–85
- RTX 4080 16GB laptop should score ~65–75
- Apple Silicon Max 64GB+ should score ~60–70

### 6. Add to test suite
Add benchmark fixtures to `test_stage2_fixtures.py`. Run `make test` — all green.

Add at least one negative fixture per platform (should route SKIP): low VRAM, high risk score, missing fields.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| eBay HTML selectors stale | Inspect one saved page in browser DevTools before running at scale |
| FB Marketplace JSON-LD absent | Use browser DevTools Network tab to intercept the API JSON payload instead |
| Grounding firewall rejects benchmark fixtures | Check that `full_listing_text` contains the verbatim strings the LLM extracts as facts |
| Score not matching expectations | Adjust SRL tier thresholds — never touch Python scoring logic directly |

## Definition of Done
- [ ] ≥3 benchmark fixtures per platform in `tests/fixtures/stage2/`
- [ ] All route to SHORTLIST via `make decide`
- [ ] `make test` fully green including new fixtures
- [ ] At least one SKIP fixture per platform

---

## Tooling Setup

**Primary workflow:** Antigravity IDE (VS Code fork) as the visual environment + Claude Code CLI in the integrated terminal. Both tools point at the same project directory and share `CLAUDE.md` / `AGENTS.md`.

**Why this setup:**
- Antigravity provides the file explorer, git panel, and integrated terminal without changing the existing Claude Code CLI workflow
- Claude Code CLI runs in Antigravity's integrated terminal (`claude` command) — no extension installation needed
- `CLAUDE.md` is read by Claude Code automatically; `AGENTS.md` is read by Antigravity's Gemini agent
- Both files are kept in sync — they contain the same project rules, phrased for their respective agents

**Extension note:** Claude Code extension is available in Antigravity via Open VSX (older v2.0.13) or via manual `.vsix` install from the VS Code Marketplace (current version). The CLI-in-terminal approach is preferred — no version juggling, no workarounds.

**MCP:** Desktop Commander and Filesystem MCP are both redundant here — Claude Code has native file access and shell execution built in. No MCP servers needed for this project.
