---
name: market-gap-scanner
description: Runs proactive market gap analysis against feed files to flag graduation candidates, price drift, and unrecognised GPU sightings. Trigger when you have new feed data or after a scraping run.
---

# Market Gap Scanner

You are running a proactive discovery sweep against raw listing feed files to surface market intelligence before launching a full pipeline run.

## Triggers
- After a `make scrape-and-live` run produces new files in `data/feed_live/`.
- When the user pastes new listing text into `data/feed_manual.txt`.
- When the user asks to "scan for new hardware", "check watch list", or "look for price drops".

## Action Plan

Run the deterministic market gap scanner:
```bash
make scan-gaps
```

Then interpret the three alert types:

| Alert | Meaning | Recommended Action |
| :--- | :--- | :--- |
| `[GRADUATION_ALERT]` | A watch-list GPU was sighted in the feed | Check the listing price against the graduation condition in `watch_list`. If price is within budget, flag for manual review and SRL promotion. |
| `[PRICE_DRIFT_ALERT]` | A target GPU is priced outside its SRL price band | If price is significantly BELOW band, shortlist immediately. If ABOVE, update `observed_au_price_max_aud` in SRL. |
| `[NEW_SIGHTING_ALERT]` | A GPU was seen in feed that is not in SRL | Research the GPU's VRAM spec. If VRAM ≥ 12GB, propose adding it to `target_gpus` or `watch_list` via `srl-config-guard` review. |

## Critical Constraints
- Do NOT auto-promote a watch-list GPU to `target_gpus`. Graduation requires explicit manual review and must go through the `srl-config-guard` peer review workflow.
- Do NOT fabricate VRAM specs for `[NEW_SIGHTING_ALERT]` GPUs. Research the spec from the listing text first. If not present, it stays as a sighting candidate only.
