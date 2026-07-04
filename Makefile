.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset inject-config scrape-and-live render-matrix scan-gaps process_csv

# Overrideable variables
FIRECRAWL_URLS ?= data/urls.txt

test:
	.venv/bin/python -m pytest tests/ -v

lint:
	.venv/bin/python -m ruff check src/ tests/

# Run Stage 2 analysis + decision on a single fixture.
# Usage: make decide FIXTURE=tests/fixtures/stage2/ebay_facts_grounded.json
decide:
	@test -n "$(FIXTURE)" || (echo "ERROR: Set FIXTURE=<path>" && exit 1)
	.venv/bin/python -m laptopfinder.core decide $(FIXTURE)

# Run Stage 1 then Stage 2+decide sequentially against paired fixtures.
# Usage: make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json
pipeline:
	@test -n "$(STAGE1)" || (echo "ERROR: Set STAGE1=<path>" && exit 1)
	@test -n "$(STAGE2)" || (echo "ERROR: Set STAGE2=<path>" && exit 1)
	.venv/bin/python -m laptopfinder.core pipeline $(STAGE1) $(STAGE2)

# Run the live pipeline on unstructured text using LLMs
# Usage: make live SOURCE=feed.txt
live:
	@test -n "$(SOURCE)" || (echo "ERROR: Set SOURCE=<path to raw text file>" && exit 1)
	.venv/bin/python -m laptopfinder.core run-live --source-text $(SOURCE)

evidence-run:
	@echo "Running Evidence Pipeline..."
	uv run python src/laptopfinder/runners/evidence_pipeline.py

evidence-run-dry:
	@echo "Running Evidence Pipeline (dry-run — no archiving, no handoff generation)..."
	uv run python src/laptopfinder/runners/evidence_pipeline.py --dry-run

evidence-reset:
	@echo "Resetting Evidence Pipeline (truncates aggregated.jsonl)..."
	uv run python src/laptopfinder/runners/evidence_pipeline.py --reset

# Inject config values from static_reference_layer.json into prompt sentinel markers.
# Run explicitly when SRL changes. NOT a dependency of scrape-and-live.
inject-config:
	.venv/bin/python scripts/inject_config.py

# Scrape listing URLs via Firecrawl, then run the live pipeline per listing.
# Requires FIRECRAWL_API_KEY in .env. Does NOT depend on inject-config.
# Usage: make scrape-and-live
#        make scrape-and-live FIRECRAWL_URLS=path/to/other_urls.txt
scrape-and-live:
	@rm -f data/feed_live/listing-*.txt
	@echo "=== Firecrawl fetch ==="
	.venv/bin/python -m laptopfinder.scrape_live --urls-file $(FIRECRAWL_URLS) --out-dir data/feed_live/
	@echo "=== Live pipeline (per listing) ==="
	@if ! ls data/feed_live/listing-*.txt 1>/dev/null 2>&1; then \
	    echo "ERROR: scrape produced no listing files — check FIRECRAWL_API_KEY and $(FIRECRAWL_URLS)"; \
	    exit 1; \
	fi
	@for f in data/feed_live/listing-*.txt; do \
	    echo "--- $$f ---"; \
	    $(MAKE) live SOURCE="$$f" || exit 1; \
	done

# Render JSONL shortlist into a sorted Markdown purchase-decision table.
# Input:  data/shortlist_candidates.jsonl (manually assembled by operator)
# Output: data/purchase_matrix.md
render-matrix:
	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
	@echo "Matrix written to data/purchase_matrix.md"

# Run batch CSV ingestion and update the decision matrix
# Usage: make process_csv
process_csv:
	@echo "Starting batch CSV ingestion workflow..."
	.venv/bin/python src/laptopfinder/ingest_csv.py
	$(MAKE) render-matrix
	@echo "Batch CSV ingestion completed successfully."

# Sweep feed files for price drift, watch-list graduation candidates, and unrecognised GPU sightings.
# Usage: make scan-gaps
scan-gaps:
	.venv/bin/python scripts/scan_market_gaps.py
