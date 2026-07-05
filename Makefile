.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset inject-config render-matrix scan-gaps process_csv ebay-auth start-sniper stop-sniper status-sniper test-sniper-alert scan-deals cache-feed

# Overrideable variables
SCRAPER ?= .venv/bin/python -m laptopfinder.runners.ebay_api

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

# Render JSONL shortlist into a sorted Markdown purchase-decision table.
# Input:  data/shortlist_candidates.jsonl (manually assembled by operator)
# Output: data/purchase_matrix.md
render-matrix:
	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
	@echo "Matrix written to data/purchase_matrix.md"

# Run the new live API pipeline that bypasses scraping
# Usage: make live-api
live-api:
	.venv/bin/python -m laptopfinder.runners.ebay_api

# Run the eBay OAuth flow, export the token to the shell environment, and launch the scraper.
# Usage: make ebay-auth
#        make ebay-auth SCRAPER="python -m laptopfinder.runners.ebay_hunter"
ebay-auth:
	@set -a; [ -f .env ] && . .env; set +a; \
	API_BASE="https://api.ebay.com"; \
	if [ "$$EBAY_ENVIRONMENT" = "sandbox" ]; then API_BASE="https://api.sandbox.ebay.com"; fi; \
	TOKEN_URL="$${API_BASE}/identity/v1/oauth2/token"; \
	CREDENTIALS=$$(printf "%s:%s" "$$EBAY_CLIENT_ID" "$$EBAY_CLIENT_SECRET" | base64 | tr -d '\n\r'); \
	RESPONSE=$$(curl -s -X POST "$$TOKEN_URL" \
	  -H 'Content-Type: application/x-www-form-urlencoded' \
	  -H "Authorization: Basic $$CREDENTIALS" \
	  -d 'grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope'); \
	TOKEN=$$(echo "$$RESPONSE" | jq -r .access_token); \
	if [ "$$TOKEN" != "null" ] && [ -n "$$TOKEN" ]; then \
	  echo "$$TOKEN" > .ebay_access_token; \
	  export EBAY_ACCESS_TOKEN=$$TOKEN; \
	  echo "export EBAY_ACCESS_TOKEN=$$TOKEN"; \
	  $(SCRAPER); \
	else \
	  echo "Authentication failed!"; \
	  echo "$$RESPONSE"; \
	  exit 1; \
	fi

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

# Start eBay AU sniper as a background daemon
start-sniper:
	@mkdir -p data/logs
	@nohup .venv/bin/python -u scripts/ebay_sniper.py > data/logs/sniper.log 2>&1 & echo $$! > data/sniper.pid
	@echo "Sniper running in background (PID: $$(cat data/sniper.pid)). Logs at data/logs/sniper.log"

# Stop eBay AU sniper background daemon
stop-sniper:
	@test -f data/sniper.pid || (echo "Sniper not running (no PID file)." && exit 1)
	@kill -15 $$(cat data/sniper.pid) && rm -f data/sniper.pid
	@echo "Sniper daemon stopped."

# Check status of eBay AU sniper daemon
status-sniper:
	@if [ -f data/sniper.pid ] && ps -p $$(cat data/sniper.pid) > /dev/null; then \
		echo "🟢 Sniper running (PID: $$(cat data/sniper.pid))"; \
		tail -n 5 data/logs/sniper.log; \
	else \
		echo "🔴 Sniper stopped."; \
	fi

# Send a test iMessage alert
test-sniper-alert:
	.venv/bin/python scripts/ebay_sniper.py --test-alert

cache-feed:
	.venv/bin/python scripts/ebay_feed_cache.py --category 175672 --cache-dir data/feed_cache

scan-deals:
	.venv/bin/python -c "
import json, os
from dotenv import load_dotenv
load_dotenv()
from laptopfinder.runners.ebay_hunter import get_ebay_token
from laptopfinder.runners.ebay_deals import scan_clearance
ref = json.load(open('config/static_reference_layer.json'))
token = get_ebay_token()
hits = scan_clearance(token, ref)
print(f'[DEALS] {len(hits)} clearance listings found')
for h in hits: print(' -', h.get('title','?'), h.get('price',{}).get('value','?'))
"
