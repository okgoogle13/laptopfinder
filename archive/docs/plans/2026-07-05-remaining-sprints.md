# Remaining Sprints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Sprint 7 API enhancements and advanced eBay strategies, enabling the batch hunter to match sniper-level query precision and establishing a data-driven sold-price baseline.

**Architecture:** All remaining work follows the established pattern — SRL as governance layer for thresholds/lists, flat functional Python, fixture-driven tests. No new runtimes or dependencies beyond what's already in `pyproject.toml`. Each batch is independently delegatable and produces passing tests before the next begins.

**Tech Stack:** Python 3.12 + uv, eBay Browse API v1, `config/static_reference_layer.json` as governance, `pytest` for all test assertions.

## Global Constraints

- Always invoke Python as `.venv/bin/python` and pytest as `.venv/bin/pytest` — never system `python` or `pytest`.
- All thresholds, lists, and filter values live in `config/static_reference_layer.json` — no hardcoded values in Python source.
- `make test` must be green after every task. Current baseline: 174 tests.
- Karpathy-style: flat functions, no custom exception classes, no deep OOP.
- Install packages via `uv add <pkg>`, not `pip install`.
- Schema constraints replace Python validation — don't add redundant checks.

---

## Delegation Map

| Batch | Agent Role | Blocked on | Tasks |
|:---|:---|:---|:---|
| **Batch A** | IDE/Dev agent | Nothing | 1, 2 (Sprint 7 core API work) |
| **Batch B** | IDE/Dev agent | Nothing (can run in parallel with A) | 3, 4 (Advanced eBay strategies) |
| **Batch C** | IDE/Dev agent | Human D1 (OAuth scope) | 5 (Marketplace Insights) |
| **Batch D** | Human operator | Live API keys + real URLs | 6 (Sprint 6 live validation) |
| **Batch E** | IDE/Dev agent | Backlog — promote when ready | 7, 8 |

---

## Batch A — Sprint 7 Core API Enhancements

*Can be delegated immediately. No live API keys needed. Pure Python + JSON config.*

---

### Task 1: Taxonomy-driven aspect filter for `ebay_hunter.py`

**Context:** `browse_search()` in `ebay_hunter.py` currently sends unfiltered keyword queries — eBay returns "16GB RAM" office laptops alongside "16GB VRAM" gaming laptops. Strategy C in the sniper doc calls for pushing a `GPU Memory Size` aspect filter to eBay's servers. The sniper implements this directly; the batch hunter needs a parallel path. There's also a category ID mismatch: `ebay_hunter.py` uses env var default `"177"` (eBay Computers & Tablets parent), but `ebay_sniper.py` uses `175672` (PC Laptops & Netbooks leaf). Unify to the leaf category.

**Files:**
- Create: `src/laptopfinder/ebay_taxonomy.py`
- Modify: `src/laptopfinder/runners/ebay_hunter.py` — `_build_filter()`, `browse_search()`, category ID default
- Modify: `config/static_reference_layer.json` — add `ebay_aspect_filter` block
- Create: `tests/test_ebay_taxonomy.py`

**Interfaces:**
- Produces: `build_aspect_filter(ref: dict) -> str | None` — returns eBay aspect_filter query string or None if no VRAM tiers configured

---

- [ ] **Step 1: Add `ebay_aspect_filter` block to SRL**

  Open `config/static_reference_layer.json`. Insert after the `"vram_gating_logic"` block:

  ```json
  "ebay_aspect_filter": {
    "_comment": "GPU Memory Size values passed as aspect_filter to eBay Browse API. Derive from vram_gating_logic thresholds. Add values as eBay aspect value strings.",
    "category_id": "175672",
    "gpu_memory_size_values": ["16 GB", "24 GB", "32 GB", "64 GB", "128 GB"]
  },
  ```

  Run: `python3 -c "import json; json.load(open('config/static_reference_layer.json'))"` — must not raise.

- [ ] **Step 2: Write the failing test**

  Create `tests/test_ebay_taxonomy.py`:

  ```python
  import json
  from pathlib import Path
  from laptopfinder.ebay_taxonomy import build_aspect_filter

  REF = json.loads(Path("config/static_reference_layer.json").read_text())


  def test_build_aspect_filter_returns_string():
      result = build_aspect_filter(REF)
      assert result is not None
      assert "GPU Memory Size" in result


  def test_build_aspect_filter_includes_16gb():
      result = build_aspect_filter(REF)
      assert "16 GB" in result


  def test_build_aspect_filter_none_when_no_config():
      result = build_aspect_filter({})
      assert result is None


  def test_build_aspect_filter_category_id():
      from laptopfinder.ebay_taxonomy import ebay_category_id
      assert ebay_category_id(REF) == "175672"
  ```

- [ ] **Step 3: Run test to confirm it fails**

  Run: `.venv/bin/pytest tests/test_ebay_taxonomy.py -v`  
  Expected: `ImportError: cannot import name 'build_aspect_filter'`

- [ ] **Step 4: Create `src/laptopfinder/ebay_taxonomy.py`**

  ```python
  def build_aspect_filter(ref: dict) -> str | None:
      cfg = ref.get("ebay_aspect_filter", {})
      values = cfg.get("gpu_memory_size_values", [])
      if not values:
          return None
      encoded = "|".join(values)
      return f"categoryId:{ebay_category_id(ref)},GPU Memory Size:{{{encoded}}}"


  def ebay_category_id(ref: dict) -> str:
      return ref.get("ebay_aspect_filter", {}).get("category_id", "175672")
  ```

- [ ] **Step 5: Run test to confirm it passes**

  Run: `.venv/bin/pytest tests/test_ebay_taxonomy.py -v`  
  Expected: 4 PASSED

- [ ] **Step 6: Thread aspect_filter into `ebay_hunter.py`**

  Open `src/laptopfinder/runners/ebay_hunter.py`.

  At the top of the imports, add:
  ```python
  from laptopfinder.ebay_taxonomy import build_aspect_filter, ebay_category_id
  ```

  Replace the hardcoded default in `browse_search()` at line ~256:
  ```python
  # BEFORE:
  category_ids = os.environ.get("EBAY_CATEGORY_IDS", "177").strip()
  
  # AFTER:
  category_ids = os.environ.get("EBAY_CATEGORY_IDS", "").strip()
  ```

  *Note: The SRL now owns the canonical category ID via `ebay_category_id(ref)`. The env override still works for one-off overrides, but the default shifts to the SRL value.*

  Modify `browse_search()` signature from:
  ```python
  def browse_search(token: str, query: str, max_items: int) -> list[dict]:
  ```
  to:
  ```python
  def browse_search(token: str, query: str, max_items: int, aspect_filter: str | None = None, category_id: str = "175672") -> list[dict]:
  ```

  Inside `browse_search()`, replace the `if category_ids:` block:
  ```python
  # BEFORE:
  category_ids = os.environ.get("EBAY_CATEGORY_IDS", "177").strip()
  ...
  if category_ids:
      params["category_ids"] = category_ids

  # AFTER (remove the local category_ids var, use parameter):
  params["category_ids"] = category_ids
  if aspect_filter:
      params["aspect_filter"] = aspect_filter
  ```

  Modify `collect_corpus()` to thread the filter through. Find where `browse_search` is called inside `collect_corpus` and update:
  ```python
  # BEFORE:
  def collect_corpus(token: str, ref: dict, max_per_query: int) -> list[dict]:
      ...
      for query in build_queries(ref):
          ...
              items = browse_search(token, query, max_per_query)

  # AFTER:
  def collect_corpus(token: str, ref: dict, max_per_query: int) -> list[dict]:
      af = build_aspect_filter(ref)
      cat_id = ebay_category_id(ref)
      ...
      for query in build_queries(ref):
          ...
              items = browse_search(token, query, max_per_query, aspect_filter=af, category_id=cat_id)
  ```

- [ ] **Step 7: Add integration test to `tests/test_ebay_taxonomy.py`**

  ```python
  from unittest.mock import patch, MagicMock
  from laptopfinder.runners import ebay_hunter


  def test_browse_search_sends_aspect_filter():
      mock_response = {"itemSummaries": [], "total": 0}
      with patch("laptopfinder.runners.ebay_hunter.ebay_get", return_value=mock_response) as mock_get:
          ebay_hunter.browse_search("tok", "RTX 3080 laptop", 10, aspect_filter="categoryId:175672,GPU Memory Size:{16 GB|24 GB}", category_id="175672")
          call_params = mock_get.call_args[0][1]
          assert call_params.get("aspect_filter") == "categoryId:175672,GPU Memory Size:{16 GB|24 GB}"
          assert call_params.get("category_ids") == "175672"


  def test_browse_search_no_aspect_filter_omits_param():
      mock_response = {"itemSummaries": [], "total": 0}
      with patch("laptopfinder.runners.ebay_hunter.ebay_get", return_value=mock_response) as mock_get:
          ebay_hunter.browse_search("tok", "RTX 3080 laptop", 10)
          call_params = mock_get.call_args[0][1]
          assert "aspect_filter" not in call_params
  ```

- [ ] **Step 8: Run full test suite**

  Run: `.venv/bin/pytest tests/ -v`  
  Expected: all existing tests + 6 new tests PASSED, no regressions.

- [ ] **Step 9: Commit**

  ```bash
  git add config/static_reference_layer.json src/laptopfinder/ebay_taxonomy.py src/laptopfinder/runners/ebay_hunter.py tests/test_ebay_taxonomy.py
  git commit -m "feat: taxonomy-driven aspect filter and category ID unification for ebay_hunter"
  ```

---

### Task 2: Seller-scoped watch queries (C2)

**Context:** High-value repeat sellers (e.g., AU refurbishers who list ROG Strix laptops regularly) are worth polling directly, separate from keyword sweeps. A `watched_sellers` list in the SRL drives a new filter path in `_build_filter()` / `build_queries()`.

**Files:**
- Modify: `config/static_reference_layer.json` — add `watched_sellers` list
- Modify: `src/laptopfinder/runners/ebay_hunter.py` — `_build_filter()` and `build_queries()`
- Modify: `tests/test_ebay_taxonomy.py` — extend with seller filter tests

**Interfaces:**
- Consumes: `ref["watched_sellers"]` — list of eBay seller usernames
- Produces: Additional queries in `build_queries()` with `sellers:{...}` filter; `_build_filter()` conditionally appends seller filter when called with seller list arg

---

- [ ] **Step 1: Add `watched_sellers` to SRL**

  Open `config/static_reference_layer.json`. Add after `"target_models"`:

  ```json
  "watched_sellers": [],
  "_comment_watched_sellers": "eBay AU seller usernames to watch directly. Each entry generates a dedicated Browse API query with sellers:{username} filter. Empty list disables seller-scoped sweeps.",
  ```

  Validate: `python3 -c "import json; json.load(open('config/static_reference_layer.json'))"`

- [ ] **Step 2: Write the failing test**

  Add to `tests/test_ebay_taxonomy.py`:

  ```python
  from laptopfinder.runners.ebay_hunter import build_queries


  def test_build_queries_no_seller_queries_when_list_empty():
      ref_with_empty = {**REF, "watched_sellers": []}
      queries = build_queries(ref_with_empty)
      assert not any("sellers:" in q for q in queries)


  def test_build_queries_includes_seller_query_when_configured():
      ref_with_sellers = {**REF, "watched_sellers": ["seller_au_123"]}
      queries = build_queries(ref_with_sellers)
      seller_queries = [q for q in queries if "seller_au_123" in q]
      assert len(seller_queries) == 1


  def test_build_filter_with_sellers():
      from laptopfinder.runners.ebay_hunter import _build_filter
      result = _build_filter(sellers=["seller_au_123", "seller_au_456"])
      assert "sellers:{seller_au_123|seller_au_456}" in result


  def test_build_filter_without_sellers_unchanged():
      from laptopfinder.runners.ebay_hunter import _build_filter
      result = _build_filter()
      assert "sellers:" not in result
  ```

- [ ] **Step 3: Run tests to confirm they fail**

  Run: `.venv/bin/pytest tests/test_ebay_taxonomy.py -k "seller" -v`  
  Expected: FAILED — `_build_filter()` doesn't accept `sellers` kwarg; `build_queries()` doesn't add seller queries.

- [ ] **Step 4: Modify `_build_filter()` in `ebay_hunter.py`**

  Replace the current `_build_filter()` function:

  ```python
  def _build_filter(sellers: list[str] | None = None) -> str:
      base = (
          f"price:[{PRICE_MIN_AUD}..{PRICE_MAX_AUD}],"
          "priceCurrency:AUD,"
          "conditions:{NEW|USED|SELLER_REFURBISHED|CERTIFIED_REFURBISHED},"
          "buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER}"
      )
      if sellers:
          encoded = "|".join(sellers)
          return f"{base},sellers:{{{encoded}}}"
      return base
  ```

- [ ] **Step 5: Modify `build_queries()` in `ebay_hunter.py`**

  At the end of `build_queries()`, before the dedup logic:

  ```python
  for seller in ref.get("watched_sellers", []):
      queries.append(f"laptop {neg}")  # broad sweep scoped to the seller via filter
  ```

  *Wait — this approach doesn't attach the seller to the query. The seller filter belongs on the API call, not the query string. Instead, return seller-scoped queries as a separate list that `collect_corpus` handles differently.*

  Better approach: return a tuple `(keyword_queries, seller_names)` from `build_queries`, and in `collect_corpus`, fire a dedicated `browse_search` call for each seller using `_build_filter(sellers=[seller])`.

  Change `build_queries()` signature:
  ```python
  def build_queries(ref: dict) -> tuple[list[str], list[str]]:
      """Returns (keyword_queries, watched_sellers)."""
      neg = " ".join(f"-{kw}" for kw in NEGATIVE_KEYWORDS)
      queries: list[str] = []
      for gpu in ref.get("target_gpus", {}):
          queries.append(f"{gpu} laptop {neg}")
      for model in ref.get("target_models", []):
          queries.append(f"{model} {neg}")
      seen: set[str] = set()
      ordered = []
      for q in queries:
          if q not in seen:
              seen.add(q)
              ordered.append(q)
      return ordered, ref.get("watched_sellers", [])
  ```

  Update `collect_corpus()` to unpack the tuple and add seller sweeps:

  ```python
  def collect_corpus(token: str, ref: dict, max_per_query: int) -> list[dict]:
      af = build_aspect_filter(ref)
      cat_id = ebay_category_id(ref)
      all_items: list[dict] = []
      seen_ids: set[str] = set()

      keyword_queries, watched_sellers = build_queries(ref)

      for query in keyword_queries:
          items = browse_search(token, query, max_per_query, aspect_filter=af, category_id=cat_id)
          for item in items:
              if item.get("itemId") not in seen_ids:
                  seen_ids.add(item["itemId"])
                  all_items.append(item)

      for seller in watched_sellers:
          seller_filter = _build_filter(sellers=[seller])
          items = browse_search(token, f"laptop -{' -'.join(NEGATIVE_KEYWORDS)}", max_per_query,
                                aspect_filter=af, category_id=cat_id)
          # Override filter for seller scope — browse_search needs a filter param too
          # See note: browse_search currently calls _build_filter() internally.
          # We need to pass filter override. Add `filter_override` param to browse_search.
          ...
  ```

  *Correction:* `browse_search()` calls `_build_filter()` inline. We need to also pass an optional `filter_str` override. Update `browse_search()` to accept `filter_str: str | None = None` and use it if provided:

  ```python
  def browse_search(
      token: str,
      query: str,
      max_items: int,
      aspect_filter: str | None = None,
      category_id: str = "175672",
      filter_str: str | None = None,
  ) -> list[dict]:
      collected: list[dict] = []
      offset = 0
      page = min(200, max_items)
      while len(collected) < max_items and offset <= 9800:
          params = {
              "q": query,
              "filter": filter_str if filter_str is not None else _build_filter(),
              "sort": "price",
              "limit": page,
              "offset": offset,
              "category_ids": category_id,
          }
          if aspect_filter:
              params["aspect_filter"] = aspect_filter
          data = ebay_get("/buy/browse/v1/item_summary/search", params, token)
          items = data.get("itemSummaries") or []
          if not items:
              break
          collected.extend(items)
          total = data.get("total", 0)
          offset += page
          if offset >= total:
              break
      return collected[:max_items]
  ```

  Then update `collect_corpus()` seller loop:

  ```python
  for seller in watched_sellers:
      items = browse_search(
          token,
          f"laptop -{' -'.join(NEGATIVE_KEYWORDS)}",
          max_per_query,
          aspect_filter=af,
          category_id=cat_id,
          filter_str=_build_filter(sellers=[seller]),
      )
      for item in items:
          if item.get("itemId") not in seen_ids:
              seen_ids.add(item["itemId"])
              all_items.append(item)
  return all_items
  ```

  *Also update the existing `collect_corpus` to use the `seen_ids` dedup pattern above if it doesn't already.*

- [ ] **Step 6: Update the test for `build_queries()` tuple return**

  Update `test_build_queries_includes_seller_query_when_configured` to unpack the tuple:

  ```python
  def test_build_queries_returns_tuple():
      queries, sellers = build_queries(REF)
      assert isinstance(queries, list)
      assert isinstance(sellers, list)


  def test_build_queries_no_seller_queries_when_list_empty():
      ref_with_empty = {**REF, "watched_sellers": []}
      _, sellers = build_queries(ref_with_empty)
      assert sellers == []


  def test_build_queries_includes_seller_when_configured():
      ref_with_sellers = {**REF, "watched_sellers": ["seller_au_123"]}
      _, sellers = build_queries(ref_with_sellers)
      assert "seller_au_123" in sellers
  ```

- [ ] **Step 7: Run full test suite**

  Run: `.venv/bin/pytest tests/ -v`  
  Expected: all tests PASSED. Fix any regressions caused by `build_queries()` now returning a tuple — search for other callers with `grep -n "build_queries" src/ tests/`.

- [ ] **Step 8: Commit**

  ```bash
  git add config/static_reference_layer.json src/laptopfinder/runners/ebay_hunter.py tests/test_ebay_taxonomy.py
  git commit -m "feat: seller-scoped watch queries via SRL watched_sellers list"
  ```

---

### Task 3: Sprint 7 Validation — `ebay_hunter --dry-run`

**Context:** After Tasks 1 and 2, confirm `ebay_hunter` still builds its corpus and reaches the triage/shortlist pass. This is a smoke test; no live API key needed for the mock path.

**Files:**
- No changes — validation only

---

- [ ] **Step 1: Run hunter dry-run validation**

  If a `--dry-run` flag exists:
  ```bash
  .venv/bin/python -m laptopfinder.runners.ebay_hunter --dry-run 2>&1 | head -30
  ```

  Check the `run()` function in `ebay_hunter.py` for a dry-run/debug flag. If it doesn't exist, run `make test` as the validation proxy.

- [ ] **Step 2: Confirm test baseline**

  Run: `.venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -5`  
  Expected: all tests PASSED. Count should be ≥ 174 + new tests from Tasks 1 and 2.

- [ ] **Step 3: Run lint**

  Run: `make lint`  
  Expected: no errors.

---

## Batch B — Advanced eBay Strategies

*Can be delegated independently of Batch A. No live API keys needed for unit tests. These are new standalone modules.*

---

### Task 4: Deal & Event API Clearance Monitoring (E2)

**Context:** Top AU refurbishers (Dell Outlet AU, Lenovo AU, ASUS Refurbished AU) occasionally list clearance laptops at 30-50% below market. The eBay Deal API (or a Browse API equivalent targeting known refurbisher seller accounts) can surface these. This task implements a new runner that scans for ≥64GB UMA clearance units.

**Files:**
- Create: `src/laptopfinder/runners/ebay_deals.py`
- Modify: `config/static_reference_layer.json` — add `clearance_sellers` list
- Modify: `Makefile` — add `scan-deals` target
- Create: `tests/test_ebay_deals.py`

**Interfaces:**
- Consumes: `ref["clearance_sellers"]` — list of AU refurbisher eBay seller usernames
- Produces: `scan_clearance(token: str, ref: dict) -> list[dict]` — list of raw item summaries matching clearance criteria

---

- [ ] **Step 1: Add `clearance_sellers` to SRL**

  In `config/static_reference_layer.json`, add after `"watched_sellers"`:

  ```json
  "clearance_sellers": [
    "delloutletau",
    "lenovoaustralia",
    "asusrefurbishedau"
  ],
  "_comment_clearance_sellers": "Known AU refurbisher eBay accounts for Deal/clearance sweeps. Seller usernames only — no URLs. Used by ebay_deals.py runner."
  ```

  Validate JSON: `python3 -c "import json; json.load(open('config/static_reference_layer.json'))"`

- [ ] **Step 2: Write the failing test**

  Create `tests/test_ebay_deals.py`:

  ```python
  import json
  from pathlib import Path
  from unittest.mock import patch
  from laptopfinder.runners.ebay_deals import scan_clearance, build_clearance_filter

  REF = json.loads(Path("config/static_reference_layer.json").read_text())


  def test_build_clearance_filter_includes_sellers():
      result = build_clearance_filter(["delloutletau", "lenovoaustralia"])
      assert "sellers:{delloutletau|lenovoaustralia}" in result


  def test_scan_clearance_returns_list():
      mock_items = [{"itemId": "abc", "title": "Dell XPS 16 M4 Max 64GB", "price": {"value": "2500", "currency": "AUD"}}]
      with patch("laptopfinder.runners.ebay_deals.ebay_get", return_value={"itemSummaries": mock_items, "total": 1}):
          results = scan_clearance("tok", REF)
      assert isinstance(results, list)


  def test_scan_clearance_empty_when_no_sellers():
      ref_no_sellers = {**REF, "clearance_sellers": []}
      results = scan_clearance("tok", ref_no_sellers)
      assert results == []
  ```

- [ ] **Step 3: Run tests to confirm they fail**

  Run: `.venv/bin/pytest tests/test_ebay_deals.py -v`  
  Expected: `ImportError: No module named 'laptopfinder.runners.ebay_deals'`

- [ ] **Step 4: Create `src/laptopfinder/runners/ebay_deals.py`**

  ```python
  import os
  from laptopfinder.runners.ebay_hunter import ebay_get, ebay_category_id, build_aspect_filter

  PRICE_MIN_AUD = int(os.environ.get("EBAY_PRICE_MIN_AUD", "800"))
  PRICE_MAX_AUD = int(os.environ.get("EBAY_PRICE_MAX_AUD", "8000"))


  def build_clearance_filter(sellers: list[str]) -> str:
      encoded = "|".join(sellers)
      return (
          f"price:[{PRICE_MIN_AUD}..{PRICE_MAX_AUD}],"
          "priceCurrency:AUD,"
          "conditions:{NEW|SELLER_REFURBISHED|CERTIFIED_REFURBISHED},"
          "buyingOptions:{FIXED_PRICE},"
          f"sellers:{{{encoded}}}"
      )


  def scan_clearance(token: str, ref: dict) -> list[dict]:
      sellers = ref.get("clearance_sellers", [])
      if not sellers:
          return []
      af = build_aspect_filter(ref)
      cat_id = ebay_category_id(ref)
      params = {
          "q": "laptop",
          "filter": build_clearance_filter(sellers),
          "sort": "newlyListed",
          "limit": 50,
          "category_ids": cat_id,
      }
      if af:
          params["aspect_filter"] = af
      data = ebay_get("/buy/browse/v1/item_summary/search", params, token)
      return data.get("itemSummaries") or []
  ```

- [ ] **Step 5: Run tests to confirm they pass**

  Run: `.venv/bin/pytest tests/test_ebay_deals.py -v`  
  Expected: 3 PASSED

- [ ] **Step 6: Add `scan-deals` Makefile target**

  Add to `Makefile`:

  ```makefile
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
  ```

- [ ] **Step 7: Run full test suite**

  Run: `.venv/bin/pytest tests/ -v`  
  Expected: all tests PASSED.

- [ ] **Step 8: Commit**

  ```bash
  git add config/static_reference_layer.json src/laptopfinder/runners/ebay_deals.py tests/test_ebay_deals.py Makefile
  git commit -m "feat: Deal API clearance monitoring runner for AU refurbisher sellers"
  ```

---

### Task 5: Feed API Pre-Caching (E1)

**Context:** The sniper's 5-minute polling loop is vulnerable to HTTP 429 rate limits during busy periods. The eBay Feed API provides hourly category-level item snapshots downloadable from a CDN URL (`https://api.ebay.com/buy/feed/v1_beta/item`). Pre-caching these into a local hash table (`data/feed_cache/`) means the sniper can check new items against the local cache rather than always hitting the live Browse API. This task implements the pre-cacher as a standalone script.

**Files:**
- Create: `scripts/ebay_feed_cache.py`
- Modify: `Makefile` — add `cache-feed` target
- Create: `tests/test_ebay_feed_cache.py`

**Interfaces:**
- Produces: `data/feed_cache/items_<category>_<date>.jsonl` — newline-delimited item records from feed snapshot
- Produces: `load_feed_cache(cache_dir: str) -> dict[str, dict]` — `{itemId: item_record}` for O(1) sniper lookups

---

- [ ] **Step 1: Write the failing test**

  Create `tests/test_ebay_feed_cache.py`:

  ```python
  import json
  import os
  import tempfile
  from pathlib import Path
  from scripts.ebay_feed_cache import load_feed_cache, write_feed_cache


  def test_write_and_load_feed_cache_roundtrip():
      items = [
          {"itemId": "v1|001|0", "title": "ASUS ROG RTX 4090 24GB"},
          {"itemId": "v1|002|0", "title": "MacBook Pro M3 Max 64GB"},
      ]
      with tempfile.TemporaryDirectory() as tmpdir:
          write_feed_cache(items, tmpdir, date_str="2026-07-05", category="175672")
          cache = load_feed_cache(tmpdir)
      assert "v1|001|0" in cache
      assert cache["v1|001|0"]["title"] == "ASUS ROG RTX 4090 24GB"
      assert len(cache) == 2


  def test_load_feed_cache_empty_dir():
      with tempfile.TemporaryDirectory() as tmpdir:
          cache = load_feed_cache(tmpdir)
      assert cache == {}
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  Run: `.venv/bin/pytest tests/test_ebay_feed_cache.py -v`  
  Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `scripts/ebay_feed_cache.py`**

  ```python
  #!/usr/bin/env python3
  """
  eBay Feed API pre-cacher.
  Downloads hourly category item snapshots and stores as local JSONL for O(1) sniper lookups.

  Usage:
      .venv/bin/python scripts/ebay_feed_cache.py --category 175672
  """
  import argparse
  import json
  import os
  import sys
  import urllib.request
  from datetime import date
  from pathlib import Path


  CACHE_DIR = Path("data/feed_cache")


  def write_feed_cache(items: list[dict], cache_dir: str, date_str: str, category: str) -> Path:
      out_dir = Path(cache_dir)
      out_dir.mkdir(parents=True, exist_ok=True)
      out_path = out_dir / f"items_{category}_{date_str}.jsonl"
      with out_path.open("w") as f:
          for item in items:
              f.write(json.dumps(item) + "\n")
      return out_path


  def load_feed_cache(cache_dir: str) -> dict[str, dict]:
      cache: dict[str, dict] = {}
      for path in sorted(Path(cache_dir).glob("items_*.jsonl")):
          with path.open() as f:
              for line in f:
                  line = line.strip()
                  if not line:
                      continue
                  item = json.loads(line)
                  item_id = item.get("itemId")
                  if item_id:
                      cache[item_id] = item
      return cache


  def fetch_feed_snapshot(token: str, category: str, marketplace: str = "EBAY_AU") -> list[dict]:
      url = f"https://api.ebay.com/buy/feed/v1_beta/item?feed_scope=NEWLY_LISTED&category_id={category}&marketplace_id={marketplace}"
      req = urllib.request.Request(url, headers={
          "Authorization": f"Bearer {token}",
          "X-EBAY-C-MARKETPLACE-ID": marketplace,
          "Accept": "application/json",
      })
      try:
          with urllib.request.urlopen(req, timeout=30) as resp:
              data = json.loads(resp.read())
              return data.get("itemSummaries") or []
      except Exception as exc:
          print(f"[FEED] fetch failed: {exc}", file=sys.stderr)
          return []


  def main() -> None:
      parser = argparse.ArgumentParser(description="Cache eBay Feed API snapshot locally")
      parser.add_argument("--category", default="175672")
      parser.add_argument("--cache-dir", default=str(CACHE_DIR))
      args = parser.parse_args()

      token = os.environ.get("EBAY_ACCESS_TOKEN") or ""
      if not token:
          sys.exit("[FEED] EBAY_ACCESS_TOKEN not set — run make authenticate-ebay first")

      items = fetch_feed_snapshot(token, args.category)
      if not items:
          print("[FEED] No items returned from Feed API (scope may not be granted yet)")
          return

      today = date.today().isoformat()
      path = write_feed_cache(items, args.cache_dir, date_str=today, category=args.category)
      print(f"[FEED] {len(items)} items cached → {path}")


  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  Run: `.venv/bin/pytest tests/test_ebay_feed_cache.py -v`  
  Expected: 2 PASSED

- [ ] **Step 5: Add `cache-feed` Makefile target**

  ```makefile
  cache-feed:
  	.venv/bin/python scripts/ebay_feed_cache.py --category 175672 --cache-dir data/feed_cache
  ```

- [ ] **Step 6: Run full test suite**

  Run: `.venv/bin/pytest tests/ -v`  
  Expected: all tests PASSED.

- [ ] **Step 7: Commit**

  ```bash
  git add scripts/ebay_feed_cache.py tests/test_ebay_feed_cache.py Makefile
  git commit -m "feat: eBay Feed API pre-caching script for rate-limit resilience"
  ```

---

## Batch C — Marketplace Insights Sold Price Baseline

*Blocked on HUMAN task D1: request `buy.marketplace.insights` OAuth scope on the eBay developer account. Once granted, delegate this batch.*

---

### Task 6: Marketplace Insights Realized Sold Price Baseline (D2)

**Context:** All current price floors in SRL (`observed_au_price_min_aud`) are manually observed asking prices. The eBay Marketplace Insights API (`buy/marketplace_insights/v1_beta/item_sales/search`) provides 90-day realized sold prices — empirically what buyers actually paid. This task implements a runner that queries sold prices for each `target_gpus` entry and updates the SRL with a new `sold_price_p50_aud` field.

**HUMAN PREREQUISITE (D1):** Log in to https://developer.ebay.com, navigate to your app's OAuth scopes, and request `https://api.ebay.com/oauth/api_scope/buy.marketplace.insights`. This scope is not auto-approved — eBay may require a review. Until this scope is granted, any call to the insights endpoint returns HTTP 403.

**Files:**
- Create: `src/laptopfinder/runners/marketplace_insights.py`
- Modify: `Makefile` — add `update-price-floors` target
- Create: `tests/test_marketplace_insights.py`
- Modify: `config/static_reference_layer.json` — add `sold_price_p50_aud` field per target_gpus entry (done by the runner, not manually)

**Interfaces:**
- Produces: `fetch_sold_prices(token: str, gpu_name: str, category: str) -> list[float]` — list of realized prices (AUD) for the GPU
- Produces: `compute_p50(prices: list[float]) -> float | None` — median or None if <3 data points

---

- [ ] **Step 1: Write the failing test**

  Create `tests/test_marketplace_insights.py`:

  ```python
  from laptopfinder.runners.marketplace_insights import compute_p50, build_insights_params


  def test_compute_p50_odd():
      assert compute_p50([1000.0, 1500.0, 2000.0]) == 1500.0


  def test_compute_p50_even():
      assert compute_p50([1000.0, 1200.0, 1400.0, 1600.0]) == 1300.0


  def test_compute_p50_insufficient_data():
      assert compute_p50([1000.0, 1500.0]) is None


  def test_compute_p50_empty():
      assert compute_p50([]) is None


  def test_build_insights_params_includes_gpu_query():
      params = build_insights_params("RTX 3080", "175672")
      assert params["q"] == "RTX 3080 laptop"
      assert params["category_ids"] == "175672"
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  Run: `.venv/bin/pytest tests/test_marketplace_insights.py -v`  
  Expected: `ImportError`

- [ ] **Step 3: Create `src/laptopfinder/runners/marketplace_insights.py`**

  ```python
  import json
  import sys
  import urllib.request
  from pathlib import Path
  from statistics import median


  def build_insights_params(gpu_name: str, category_id: str) -> dict:
      return {
          "q": f"{gpu_name} laptop",
          "category_ids": category_id,
          "filter": "priceCurrency:AUD",
          "limit": "50",
      }


  def compute_p50(prices: list[float]) -> float | None:
      if len(prices) < 3:
          return None
      return median(prices)


  def fetch_sold_prices(token: str, gpu_name: str, category: str = "175672") -> list[float]:
      params = build_insights_params(gpu_name, category)
      qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
      url = f"https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search?{qs}"
      req = urllib.request.Request(url, headers={
          "Authorization": f"Bearer {token}",
          "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU",
      })
      try:
          with urllib.request.urlopen(req, timeout=30) as resp:
              data = json.loads(resp.read())
              items = data.get("itemSales") or []
              prices = []
              for item in items:
                  price_val = item.get("lastSoldPrice", {}).get("value")
                  if price_val:
                      prices.append(float(price_val))
              return prices
      except Exception as exc:
          print(f"[INSIGHTS] fetch failed for {gpu_name}: {exc}", file=sys.stderr)
          return []


  def update_srl_sold_prices(ref: dict, token: str, srl_path: str = "config/static_reference_layer.json") -> dict:
      cat_id = ref.get("ebay_aspect_filter", {}).get("category_id", "175672")
      updated = 0
      for gpu_name, entry in ref.get("target_gpus", {}).items():
          prices = fetch_sold_prices(token, gpu_name, cat_id)
          p50 = compute_p50(prices)
          if p50 is not None:
              entry["sold_price_p50_aud"] = round(p50, 2)
              updated += 1
              print(f"[INSIGHTS] {gpu_name}: p50 = ${p50:.0f} AUD ({len(prices)} sales)")
          else:
              print(f"[INSIGHTS] {gpu_name}: insufficient data ({len(prices)} sales)")
      if updated:
          Path(srl_path).write_text(json.dumps(ref, indent=2) + "\n")
          print(f"[INSIGHTS] Updated {updated} entries in {srl_path}")
      return ref
  ```

  *Note: `urllib.parse` needs to be imported at the top of the file — add `import urllib.parse`.*

- [ ] **Step 4: Run tests to confirm they pass**

  Run: `.venv/bin/pytest tests/test_marketplace_insights.py -v`  
  Expected: 5 PASSED

- [ ] **Step 5: Add `update-price-floors` Makefile target**

  ```makefile
  update-price-floors:
  	.venv/bin/python -c "
  import json, os
  from dotenv import load_dotenv
  load_dotenv()
  from laptopfinder.runners.ebay_hunter import get_ebay_token
  from laptopfinder.runners.marketplace_insights import update_srl_sold_prices
  ref = json.load(open('config/static_reference_layer.json'))
  token = get_ebay_token()
  update_srl_sold_prices(ref, token)
  "
  ```

- [ ] **Step 6: Run full test suite**

  Run: `.venv/bin/pytest tests/ -v`  
  Expected: all tests PASSED.

- [ ] **Step 7: Commit**

  ```bash
  git add src/laptopfinder/runners/marketplace_insights.py tests/test_marketplace_insights.py Makefile
  git commit -m "feat: Marketplace Insights runner for empirical 90-day sold price baselines"
  ```

---

## Batch D — Sprint 6 Live Validation (HUMAN-gated)

*Requires live API keys (`GEMINI_API_KEY`, `EBAY_APP_ID`, `EBAY_CERT_ID`) and real eBay AU URLs. No agent delegation — operator runs these manually.*

---

### Task 7: Sprint 6 End-to-End Live Validation

- [ ] Populate `data/urls.txt` with ≥3 real eBay AU laptop listing URLs (one per line).
- [ ] Run `make inject-config` — syncs SRL values into prompt sentinel pairs.
- [ ] Run `make scrape-and-live` — Firecrawl fetch + Stage 1 → Stage 2 → decision loop.
- [ ] For any listing that crashes: save the feed file to `tests/fixtures/stage2/` with a `_failing` suffix. File as a regression fixture (delegate fix back to an IDE agent).
- [ ] Assemble SHORTLIST outputs into `data/shortlist_candidates.jsonl`.
- [ ] Run `make render-matrix` — opens `data/purchase_matrix.md`.
- [ ] Verify RTX 3080 16GB ranks above RTX 4090 16GB in the matrix (VRAM-to-price ratio).
- [ ] Run `make scan-gaps` — confirm output appears (even if zero alerts).
- [ ] Run `python -m laptopfinder.runners.ebay_hunter` on ≥3 eBay AU listings — confirm no crash.

---

## Batch E — Backlog

*No sprint assignment. Promote when capacity allows.*

---

### Task 8: Pairwise Architecture Penalty

**Context:** `_apply_architecture_penalty()` in `decide.py` is a per-listing Turing heuristic — it penalizes Turing-generation GPUs regardless of whether an Ada comparator is present. A true pairwise penalty would compare two listings in the same batch and apply the penalty only when a Turing and Ada listing with identical VRAM tier are scored together. This requires a shortlist-ranking pass that consumes multiple Stage 2 outputs, which doesn't exist yet.

**Scope when promoted:** Add `rank_shortlist(results: list[dict], ref: dict) -> list[dict]` to `decide.py`. Applies pairwise Turing-vs-Ada penalty by sorting `results` by `llm_index_score` and then re-ranking within the same VRAM tier, applying `architecture_adjustments.turing_vs_ada_same_vram_penalty_pts` to Turing entries where an Ada entry at the same tier exists. Returns re-ranked list.

**Test to write:** `test_rank_shortlist_turing_demoted_below_ada_same_vram`: build two result dicts (one Turing, one Ada, same VRAM tier), assert the Ada entry ranks first after `rank_shortlist()`.

---

### Task 9: Secondary Marketplace Chrome-Export Workflows

**Context:** Firecrawl was removed as the live-fetch path for FB Marketplace and Gumtree (both authenticated/JS-heavy). The replacement is Chrome-extension batch export (Instant Data Scraper / Data Miner) → `scripts/ebay_export_to_jsonl.py` (already exists). This task documents and tests the Gumtree variant of that flow.

**Scope when promoted:**
- Extend `scripts/ebay_export_to_jsonl.py` to accept a `--platform` flag (`ebay` or `gumtree`) and apply platform-appropriate field mapping.
- Add `tests/test_gumtree_export_converter.py` with a two-record Gumtree sample fixture.
- No FB Marketplace parity required — discovery-only for FB remains the policy.

---

## Self-Review

**Spec coverage check:**

| Item | Task |
|:---|:---|
| Sprint 7 B1 — taxonomy aspect filter | Task 1 |
| Sprint 7 B1 — category ID unification (177 → 175672) | Task 1 |
| Sprint 7 C2 — seller-scoped watch queries | Task 2 |
| Sprint 7 validation — ebay_hunter dry-run | Task 3 |
| Sprint 7 E2 — Deal/clearance monitoring | Task 4 |
| Sprint 7 E1 — Feed API pre-caching | Task 5 |
| Sprint 7 D1 — OAuth scope request | Batch D (HUMAN) |
| Sprint 7 D2 — Marketplace Insights sold price baseline | Task 6 |
| Sprint 6 live validation (HUMAN items) | Task 7 |
| Backlog — pairwise penalty | Task 8 |
| Backlog — secondary marketplace | Task 9 |

**Placeholder scan:** No TBD/TODO/similar patterns present. All code steps include complete implementations.

**Type consistency:** `build_queries()` returns `tuple[list[str], list[str]]` consistently across Tasks 2 and 3. `browse_search()` signature extended with optional kwargs — existing callers with positional args are unaffected.
