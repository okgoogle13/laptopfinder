---
name: canonical-knowledge-map
description: Canonical source inventory for repository knowledge domains
metadata:
  type: reference
---

# Canonical Knowledge Map

This file identifies the best source for each knowledge domain in the repository.

Guiding rule:
- Prefer one governing source per domain.
- Use supporting sources for examples, history, or operational context.
- Treat archived research and sprint notes as supporting material unless they are the only surviving source.

## Inventory

| Domain | Canonical source | Supporting sources | Confidence | Notes |
|---|---|---|---|---|
| Hardware preferences | [config/silicon_profiles.yaml](/Users/okgoogle13/Projects/laptopfinder/config/silicon_profiles.yaml) | [data/hardware_taxonomy.json](/Users/okgoogle13/Projects/laptopfinder/data/hardware_taxonomy.json), [prompts/system_context.md](/Users/okgoogle13/Projects/laptopfinder/prompts/system_context.md), [prompts/bias_guard_prompt.md](/Users/okgoogle13/Projects/laptopfinder/prompts/bias_guard_prompt.md) | High | Owns paradigm priority, preferred inference stacks, and text-centric workload defaults. |
| GPU reference | [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json) | [data/hardware_taxonomy.json](/Users/okgoogle13/Projects/laptopfinder/data/hardware_taxonomy.json), [prompts/comet_discovery_agent.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt), [memory/project/sprint.md](/Users/okgoogle13/Projects/laptopfinder/memory/project/sprint.md) | High | Owns target GPU lists, watch list, generation hints, and pricing bands. |
| CPU reference | [data/evidence/targets.json](/Users/okgoogle13/Projects/laptopfinder/data/evidence/targets.json) | [src/laptopfinder/schemas/evidence_targets.schema.json](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/schemas/evidence_targets.schema.json), [memory/project/sprint.md](/Users/okgoogle13/Projects/laptopfinder/memory/project/sprint.md) | Medium-Low | Provisional telemetry-derived CPU tier only. There is no separate CPU knowledge doc yet; this is the narrowest current source of truth. |
| Display knowledge | [src/laptopfinder/schemas/stage2.analysis.schema.json](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/schemas/stage2.analysis.schema.json) | [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json), [tests/fixtures/stage2/gumtree_zbook_touchscreen.json](/Users/okgoogle13/Projects/laptopfinder/tests/fixtures/stage2/gumtree_zbook_touchscreen.json), [prompts/claude_code_audit.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/claude_code_audit.txt) | Medium | In this repo, display knowledge is mostly encoded as the touchscreen/digitizer exception and the grounding schema for that field. |
| Search heuristics | [prompts/comet_discovery_agent.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt) | [prompts/perplexity_space_description.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/perplexity_space_description.txt), [memory/reference/scrape_benchmark.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/scrape_benchmark.md) | High | Owns discovery seed terms, injected target lists, and ordering bias toward portable/mobile listings. |
| Pricing guidance | [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json) | [research/alternative_silicon_dossier_july2026.md](/Users/okgoogle13/Projects/laptopfinder/research/alternative_silicon_dossier_july2026.md), [memory/project/sprint.md](/Users/okgoogle13/Projects/laptopfinder/memory/project/sprint.md), [data/hardware_taxonomy.json](/Users/okgoogle13/Projects/laptopfinder/data/hardware_taxonomy.json) | High | Owns budget bands, observed AU price ranges, thresholds, and watch-list pricing context. |
| Marketplace heuristics | [memory/reference/scrape_benchmark.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/scrape_benchmark.md) | [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md), [tests/fixtures/stage2/ebay_facts_grounded.json](/Users/okgoogle13/Projects/laptopfinder/tests/fixtures/stage2/ebay_facts_grounded.json), [tests/fixtures/stage2/gumtree_hint_not_promoted.json](/Users/okgoogle13/Projects/laptopfinder/tests/fixtures/stage2/gumtree_hint_not_promoted.json) | High | Owns extractor caveats, seller/platform pitfalls, and the practical warning set for AU listings. |
| User preferences | [prompts/perplexity_space_description.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/perplexity_space_description.txt) | [prompts/system_context.md](/Users/okgoogle13/Projects/laptopfinder/prompts/system_context.md), [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md), [memory/project/sprint.md](/Users/okgoogle13/Projects/laptopfinder/memory/project/sprint.md) | High | Best explicit home for Northcote, budget, platform, and portability preferences. |
| Decision rules | [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md) | [memory/reference/pipeline.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/pipeline.md), [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json) | High | Human-readable priority order for MONITOR / SKIP / SHORTLIST and threshold notes. |
| Evaluation logic | [src/laptopfinder/decide.py](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/decide.py) | [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md), [memory/reference/pipeline.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/pipeline.md), [tests/test_decide.py](/Users/okgoogle13/Projects/laptopfinder/tests/test_decide.py) | High | Runtime authority for routing, scoring, penalties, and workload-specific behavior. |
| Configuration | [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json) | [config/silicon_profiles.yaml](/Users/okgoogle13/Projects/laptopfinder/config/silicon_profiles.yaml), [config/scoring_weights.yaml](/Users/okgoogle13/Projects/laptopfinder/config/scoring_weights.yaml), [data/hardware_taxonomy.json](/Users/okgoogle13/Projects/laptopfinder/data/hardware_taxonomy.json), [data/evidence/targets.json](/Users/okgoogle13/Projects/laptopfinder/data/evidence/targets.json) | High | Owns thresholds, target lists, watch lists, penalties, and runtime policy. |
| Schemas | [src/laptopfinder/schemas/](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/schemas/) | [tests/test_prompt_parity.py](/Users/okgoogle13/Projects/laptopfinder/tests/test_prompt_parity.py), [tests/test_stage1_fixtures.py](/Users/okgoogle13/Projects/laptopfinder/tests/test_stage1_fixtures.py), [tests/test_stage2_fixtures.py](/Users/okgoogle13/Projects/laptopfinder/tests/test_stage2_fixtures.py) | High | The JSON schemas are the authoritative shape constraints for stage outputs and telemetry targets. |
| Hardware research archive | [research/alternative_silicon_dossier_july2026.md](/Users/okgoogle13/Projects/laptopfinder/research/alternative_silicon_dossier_july2026.md) | [research/archive/Gemini Deep Research - Comprehensive Analysis of Australian Secondary-Market Hardware for Local LLMs (July 2026).md](/Users/okgoogle13/Projects/laptopfinder/research/archive/Gemini%20Deep%20Research%20-%20Comprehensive%20Analysis%20of%20Australian%20Secondary-Market%20Hardware%20for%20Local%20LLMs%20(July%202026).md), [research/archive/Perplexity Deep Research  AU Secondary Laptop & eGPU Market Mapping for Local LLMs (July 2026).md](/Users/okgoogle13/Projects/laptopfinder/research/archive/Perplexity%20Deep%20Research%20%20AU%20Secondary%20Laptop%20%26%20eGPU%20Market%20Mapping%20for%20Local%20LLMs%20(July%202026).md) | High | Consolidated July knowledge base. Raw model outputs are archived, not authoritative. |

## Remaining Gaps

- CPU guidance is still provisional and telemetry-derived. There is no dedicated CPU reference document yet.
- Display knowledge is narrow: the repository mostly stores touchscreen/digitizer handling as a field-level exception, not as a full display research corpus.
- Marketplace heuristics are split between extractor caveats and discovery prompts. That is acceptable for now, but it is the least consolidated part of the knowledge base.
- `memory/project/sprint.md` and `TASKS.md` are useful history, but they should not be treated as canonical policy.

## Reading Order

1. [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json)
2. [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md)
3. [prompts/perplexity_space_description.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/perplexity_space_description.txt)
4. [prompts/comet_discovery_agent.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt)
5. [memory/reference/pipeline.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/pipeline.md)
6. [src/laptopfinder/schemas/](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/schemas/)
