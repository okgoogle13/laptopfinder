.PHONY: test lint decide pipeline

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
