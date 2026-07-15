.PHONY: test lint pipeline live hunt status

OP_RUN ?= op run --env-file=.env --

test:
	.venv/bin/python -m pytest tests/ -v

# Zero-LLM snapshot of runner/evidence state + NEXT_TASK queue (reads existing files only).
status:
	.venv/bin/python scripts/status_snapshot.py

lint:
	.venv/bin/python -m ruff check src/ tests/

# Run Stage 1 then Stage 2+decide sequentially against paired fixtures.
# Usage: make pipeline STAGE1=tests/fixtures/stage1/ebay_rtx4090_laptop.json STAGE2=tests/fixtures/stage2/ebay_facts_grounded.json
pipeline:
	@test -n "$(STAGE1)" || (echo "ERROR: Set STAGE1=<path>" && exit 1)
	@test -n "$(STAGE2)" || (echo "ERROR: Set STAGE2=<path>" && exit 1)
	.venv/bin/python -m laptopfinder.core pipeline $(STAGE1) $(STAGE2)

# Run the AU sniper live (requires credentials via 1Password).
live:
	$(OP_RUN) .venv/bin/python -m laptopfinder.runners.ebay_sniper

# Run a target JSON-driven ad hoc discovery sweep.
# Usage: make hunt CONFIG=config/runs/desktop_replacement.json
# Add DRY_RUN=1 to suppress email and state writes regardless of config.
hunt:
	@test -n "$(CONFIG)" || (echo "ERROR: Set CONFIG=<path to operator run config JSON>" && exit 1)
	$(OP_RUN) .venv/bin/python -m laptopfinder.runners.hunt \
	  --config $(CONFIG) \
	  $(if $(DRY_RUN),--dry-run)
