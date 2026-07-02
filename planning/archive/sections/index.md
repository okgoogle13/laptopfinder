<!-- PROJECT_CONFIG
runtime: python-uv
test_command: uv run pytest
END_PROJECT_CONFIG -->

<!-- SECTION_MANIFEST
section-01-prerequisites
section-02-inject-config
section-03-scrape-live
section-04-render-matrix
section-05-makefile-and-integration
END_MANIFEST -->

# Implementation Sections Index

## Dependency Graph

| Section | Depends On | Blocks | Parallelizable |
|---------|------------|--------|----------------|
| section-01-prerequisites | — | all | Yes |
| section-02-inject-config | 01 | 05 | No |
| section-03-scrape-live | 01 | 05 | Yes (parallel with 02, 04) |
| section-04-render-matrix | 01 | 05 | Yes (parallel with 02, 03) |
| section-05-makefile-and-integration | 02, 03, 04 | — | No |

## Execution Order

1. section-01-prerequisites (no dependencies — setup only)
2. section-02-inject-config, section-03-scrape-live, section-04-render-matrix (parallel after 01)
3. section-05-makefile-and-integration (after 02, 03, AND 04)

## Section Summaries

### section-01-prerequisites
Create `scripts/` directory, add `firecrawl-py` to `pyproject.toml` (pinned version), add `FIRECRAWL_API_KEY` to `.env.example`, update `.gitignore` with generated artifact paths, and manually add `<!-- BEGIN_INJECT:X --> ... <!-- END_INJECT:X -->` sentinel marker pairs to the three target prompt files.

### section-02-inject-config
Write `scripts/inject_config.py` with `load_srl`, `build_substitutions`, `inject_file`, and `main`. Write `tests/test_inject_config.py` with idempotency, shape-correctness, and edge-case tests. All logic is Karpathy-style: flat functions, no classes, SRL-only config source in v1.

### section-03-scrape-live
Write `src/laptopfinder/scrape_live.py` (under 50 lines) with `read_urls`, `strip_nav`, `normalise_md`, `fetch_markdown`, and `main`. Uses Firecrawl v1 client (`from firecrawl import Firecrawl`), `fc.scrape(url, formats=["markdown"], wait_for=3000)`, `doc.markdown`. Per-listing output to `data/feed_live/`. Write `tests/test_scrape_live.py` with mocked client — no live HTTP.

### section-04-render-matrix
Write `scripts/render_matrix.py` with `load_candidates`, `sort_candidates`, `render_table`, and `main`. Handles missing fields, null scores, pipe escaping, malformed JSONL lines. Write `tests/test_render_matrix.py`. No external dependencies beyond stdlib.

### section-05-makefile-and-integration
Add `inject-config`, `scrape-and-live`, and `render-matrix` targets to the Makefile. Create `data/urls.txt` sample file. Run `make test` to confirm all new and existing tests pass. Run `make inject-config` against real prompt files and verify git diff shows expected content between markers.
