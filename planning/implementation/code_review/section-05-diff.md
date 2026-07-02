diff --git a/Makefile b/Makefile
index 669ca45..aadbc31 100644
--- a/Makefile
+++ b/Makefile
@@ -1,4 +1,4 @@
-.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset
+.PHONY: test lint decide pipeline live evidence-run evidence-run-dry evidence-reset inject-config scrape-and-live render-matrix
 
 test:
 	.venv/bin/python -m pytest tests/ -v
@@ -36,3 +36,34 @@ evidence-run-dry:
 evidence-reset:
 	@echo "Resetting Evidence Pipeline (truncates aggregated.jsonl)..."
 	uv run python src/laptopfinder/runners/evidence_pipeline.py --reset
+
+# Inject config values from static_reference_layer.json into prompt sentinel markers.
+# Run explicitly when SRL changes. NOT a dependency of scrape-and-live.
+inject-config:
+	.venv/bin/python scripts/inject_config.py
+
+# Scrape listing URLs via Firecrawl, then run the live pipeline per listing.
+# Requires FIRECRAWL_API_KEY in .env. Does NOT depend on inject-config.
+# Usage: make scrape-and-live
+#        make scrape-and-live FIRECRAWL_URLS=path/to/other_urls.txt
+FIRECRAWL_URLS ?= data/urls.txt
+
+scrape-and-live:
+	@echo "=== Firecrawl fetch ==="
+	.venv/bin/python -m laptopfinder.scrape_live --urls-file $(FIRECRAWL_URLS) --out-dir data/feed_live/
+	@echo "=== Live pipeline (per listing) ==="
+	@if ! ls data/feed_live/listing-*.txt 1>/dev/null 2>&1; then \
+	    echo "ERROR: scrape produced no listing files — check FIRECRAWL_API_KEY and $(FIRECRAWL_URLS)"; \
+	    exit 1; \
+	fi
+	@for f in data/feed_live/listing-*.txt; do \
+	    echo "--- $$f ---"; \
+	    $(MAKE) live SOURCE=$$f; \
+	done
+
+# Render JSONL shortlist into a sorted Markdown purchase-decision table.
+# Input:  data/shortlist_candidates.jsonl (manually assembled by operator)
+# Output: data/purchase_matrix.md
+render-matrix:
+	.venv/bin/python scripts/render_matrix.py --in data/shortlist_candidates.jsonl --out data/purchase_matrix.md
+	@echo "Matrix written to data/purchase_matrix.md"
diff --git a/data/urls.txt b/data/urls.txt
index c768573..04663fd 100644
--- a/data/urls.txt
+++ b/data/urls.txt
@@ -1,6 +1,10 @@
-# URLs to scrape for the live pipeline.
-# One URL per line. Blank lines and lines starting with # are ignored.
-# Run: make scrape-and-live
+# One listing URL per line.
+# Lines starting with # are ignored.
+# Blank lines are ignored.
+# Override with: make scrape-and-live FIRECRAWL_URLS=path/to/other.txt
 #
-# https://www.ebay.com.au/itm/example-listing-1
-# https://www.ebay.com.au/itm/example-listing-2
+# Example eBay AU listing:
+# https://www.ebay.com.au/itm/123456789012
+#
+# Example Gumtree listing:
+# https://www.gumtree.com.au/s-ad/sydney/laptops-computers/...
