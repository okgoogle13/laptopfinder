---
name: ebay-market-analyzer (Archived)
description: >
  [ARCHIVED REFERENCE DESIGN] Evaluates second-hand computer hardware listings on eBay. Extracts specs, analyzes comps, and recommends pricing/offers.
---
# eBay Market Analyzer Skill (Archived Reference)

*Note: This is an archived reference design. Active logic has been ported to `enrich_shortlist.py` and `decide.py`.*

## High-Value Patterns

**1. Sold-Comps Analysis (Ported to decide.py)**
- Prioritizing actual completed/sold listings over active listings.
- Using median sold price to anchor fair value.
- Deriving a `comps_adjustment_factor` based on listing price vs. median comp.

**2. Outreach Drafts (Ported to enrich_shortlist.py / qna_filter)**
- Generating seller messages (Message A: clarifying questions, Message B: follow-up offer).
- Using `qna_filter` to dynamically strip out questions the seller has already answered in the listing description.
