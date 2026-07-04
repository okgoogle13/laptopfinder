# Memory Index

## Where to Read First (Reading Order)
1. [config/static_reference_layer.json](../config/static_reference_layer.json) — policy thresholds & target GPUs
2. [data/hardware_taxonomy.json](../data/hardware_taxonomy.json) — hardware facts & representative specifications
3. [config/silicon_profiles.yaml](../config/silicon_profiles.yaml) — hardware preferences & paradigm definitions
4. [CLAUDE.md](../CLAUDE.md) — architecture, invariant rules & decision rules
5. [prompts/perplexity_space_description.txt](../prompts/perplexity_space_description.txt) — user preferences & constraints
6. [prompts/comet_discovery_agent.txt](../prompts/comet_discovery_agent.txt) — search heuristics
7. [src/laptopfinder/schemas/](../src/laptopfinder/schemas/) — data contracts & schema firewalls

## Project (active state)
- [Sprint — Pipeline Audit June 2026](project/sprint.md) — active sprint goals, phases, definition of done

## Reference (stable facts)
- [Pipeline reference](reference/pipeline.md) — terminology, data contracts, expected score ranges, decision priority order
- [Canonical knowledge map](reference/knowledge_map.md) — one-stop source inventory for domains, canonical docs, and remaining gaps
- [scrape_benchmark.py](reference/scrape_benchmark.md) — input modes, output format, CSS selector caveats per platform
- [Tooling setup and usage](reference/tooling_usage.md) — Antigravity IDE + Claude Code CLI, MCP decisions, Python env, inject-config / scrape-live / render-matrix operator commands
- [Tooling setup stub](reference/tooling.md) — legacy redirect for older links
