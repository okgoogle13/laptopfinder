.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset

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
