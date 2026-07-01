# Code Review: section-03-scrape-live

## MUST_FIX

**1. Counter numbering contract unverified by tests**
`test_main_first_fails_second_succeeds` checks `len(written) == 1` but never asserts the file is named `listing-002.txt`. The plan's explicit contract is that `n` counts *all attempted URLs*. If the counter only incremented on success, the test would still pass.

**2. `doc.markdown` None case — cryptic crash path**
Firecrawl v1 can return `doc.markdown = None` (paywall, non-HTML content). The code calls `normalise_md(strip_nav(doc.markdown))` with no None guard. The TypeError is caught by the outer `except`, but emits an opaque `"expected string or bytes-like object"` WARN instead of the clear thin-content message. No test covers this case.

## CONSIDER

**1. `cart` nav pattern is effectively dead code**
`^\s*cart\s*$` only matches a line whose *entire content* is the word "cart". Real eBay nav lines like "Add to Cart" or "Cart (0 items)" don't match. Pattern is safe against false positives but provides no actual nav suppression.

**2. File is 68 lines (plan target: 50)**
Minor overage, not a correctness issue.

## NITPICK

**1. Redundant `os.environ.pop` in test_main_missing_api_key_exits**
`patch.dict(..., clear=True)` already guarantees absence; the manual pop is redundant.

**2. `ln.rstrip()` vs `ln.strip()` inconsistency in `read_urls`**
Filter uses `ln.strip()` but return value uses `ln.rstrip()` — a URL with leading whitespace would be passed to Firecrawl with a space.
