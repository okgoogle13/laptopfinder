<!-- PROJECT_CONFIG
runtime: python-uv
test_command: .venv/bin/python -m pytest tests/ -v
END_PROJECT_CONFIG -->

<!-- SECTION_MANIFEST
section-01-discovery-prompt-fix
section-02-egpu-interconnect-penalty
section-03-prompt-audit
END_MANIFEST -->

# Sprint 3 Implementation Sections Index

## Dependency Graph

| Section | Depends On | Blocks | Parallelizable |
|---------|------------|--------|----------------|
| section-01-discovery-prompt-fix | — | — | Yes |
| section-02-egpu-interconnect-penalty | — | — | Yes (parallel with 01) |
| section-03-prompt-audit | 01 | — | No |

## Execution Order

1. section-01 and section-02 are independent — implement in order
2. section-03 runs after section-01 (depends on S3-01 UMA fix being present)

## Sprint Context

Sprint 3 closes three gaps identified after Sprint 2 completion:
- S3-01: Discovery prompt filters UMA at 64GB+ but decision engine shortlists at 32GB — 32–48GB Apple Silicon Max machines never surfaced
- S3-02: egpu_interconnect_penalty defined in SRL but not wired into decide.py
- S3-03: Prompt audit — document hardcoded thresholds, fix anything cleanly fixable
