# Interview Transcript — Sprint 2

## Q1: Placeholder scope for inject_config.py

**Q:** inject_config.py needs to replace placeholders in prompts. Right now only one exists: `[INJECT_TARGETS_HERE]` in `comet_discovery_agent.txt`. Should we only replace that existing token, or also add new placeholder tokens to the alternative_silicon prompts?

**A:** Add new tokens to alternative_silicon prompts too. Define new placeholders and inject them as well.

## Q2: scrape_live.py error handling

**Q:** What should happen when Firecrawl returns an error for one URL (rate limit, timeout, 404)?

**A:** Skip and log to stderr, continue with remaining URLs. Best-effort — failed URLs are noted but don't abort the run.

## Q3: Day 7 Purchase Decision Matrix — input source

**Q:** Is `data/shortlist_candidates.jsonl` produced by running batch `decide()` over scraped listings, or assembled manually from SHORTLIST decisions?

**A:** Manually assembled. We just need the Markdown renderer — no batch pipeline script required for Day 7.

## Q4: Which config values to inject into alternative_silicon prompts

**Q:** Which specific values from config should be injected into the alternative_silicon prompts?

**A:** 
- UMA min RAM (32GB) and chip patterns list
- Target GPU list (15 entries)

(VRAM thresholds and watch list not needed in alternative_silicon prompts.)

## Q5: feed_manual.txt pipeline path

**Q:** Does `data/feed_manual.txt` feed into the same `make live` pipeline, or is it handled separately?

**A:** Separate flow with different prompts or logic. Not covered by the `scrape-and-live` Make target.
