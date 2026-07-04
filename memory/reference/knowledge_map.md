---
name: canonical-knowledge-map
description: Canonical source inventory for repository knowledge domains
metadata:
  type: reference
---

# Canonical Knowledge Map

This file identifies the authoritative source for each domain in the repository.

Guiding rules:
- Prefer one governing source per domain.
- Use supporting sources for examples, history, or operational context.
- Treat archived research and sprint notes as supporting material unless they are the only surviving source.

## Inventory

| Domain | Canonical source | Supporting sources | Confidence | Notes |
|---|---|---|---|---|
| GPU reference | [config/static_reference_layer.json](/Users/okgoogle13/Projects/laptopfinder/config/static_reference_layer.json) | [prompts/comet_discovery_agent.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt) | High | Owns target GPU lists, watch list, generation hints, and pricing bands. |
| Hardware facts | [data/hardware_taxonomy.json](/Users/okgoogle13/Projects/laptopfinder/data/hardware_taxonomy.json) | [data/evidence/targets.json](/Users/okgoogle13/Projects/laptopfinder/data/evidence/targets.json) | High | Representative hardware baselines (bandwidth, VRAM, RAM, inference stack). |
| Preferences | [config/silicon_profiles.yaml](/Users/okgoogle13/Projects/laptopfinder/config/silicon_profiles.yaml) | [prompts/system_context.md](/Users/okgoogle13/Projects/laptopfinder/prompts/system_context.md) | High | Paradigm priorities, preferred inference stacks, and text-centric workload defaults. |
| Decision rules | [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md) | [memory/reference/pipeline.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/pipeline.md), [src/laptopfinder/decide.py](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/decide.py) | High | Priority order for MONITOR / SKIP / SHORTLIST and risk gate rules. |
| Search heuristics | [prompts/search_queries.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/search_queries.txt) | [prompts/comet_discovery_agent.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/comet_discovery_agent.txt), [prompts/perplexity_space_description.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/perplexity_space_description.txt) | High | Boolean discovery seed queries for eBay AU, Gumtree, and FB Marketplace. Edit here; comet prompt references this file. |
| Marketplace heuristics | [memory/reference/scrape_benchmark.md](/Users/okgoogle13/Projects/laptopfinder/memory/reference/scrape_benchmark.md) | [tests/fixtures/stage2/ebay_facts_grounded.json](/Users/okgoogle13/Projects/laptopfinder/tests/fixtures/stage2/ebay_facts_grounded.json) | High | Extractor caveats, platform pitfalls (eBay AU, Gumtree, FB Marketplace), and practical warning set. |
| Schemas | [src/laptopfinder/schemas/](/Users/okgoogle13/Projects/laptopfinder/src/laptopfinder/schemas/) | [tests/test_prompt_parity.py](/Users/okgoogle13/Projects/laptopfinder/tests/test_prompt_parity.py) | High | Authoritative JSON schema shape constraints and firewalls for stage outputs. |
| Research archive | [research/alternative_silicon_dossier_july2026.md](/Users/okgoogle13/Projects/laptopfinder/research/alternative_silicon_dossier_july2026.md) | [research/archive/](/Users/okgoogle13/Projects/laptopfinder/research/archive/) | High | Consolidated July 2026 secondary-market mapping dossier. Raw outputs in `archive/` are preserved for provenance only. |
| User preferences | [prompts/perplexity_space_description.txt](/Users/okgoogle13/Projects/laptopfinder/prompts/perplexity_space_description.txt) | [CLAUDE.md](/Users/okgoogle13/Projects/laptopfinder/CLAUDE.md) | High | Explicit home for Northcote/Melbourne location, AUD budget ceiling, and portability requirements. |
| CPU | Gap / provisional | [data/evidence/targets.json](/Users/okgoogle13/Projects/laptopfinder/data/evidence/targets.json) | Low | Current telemetry-derived baseline only. No canonical CPU reference doc exists yet. |

## Remaining Gaps

- **CPU reference:** CPU guidance is provisional and telemetry-derived; if stable CPU facts are needed later, add a small `data/cpu_taxonomy.json` rather than complicating existing files.
- **Display knowledge:** The repository stores touchscreen/digitizer handling as a field-level exception rather than a comprehensive display research corpus.
- **Marketplace heuristics:** Currently split between scraper documentation and discovery prompts, which is acceptable for now but represents our least consolidated domain.

