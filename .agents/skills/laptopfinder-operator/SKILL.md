---
name: laptopfinder-operator (Archived)
description: >
  [ARCHIVED REFERENCE DESIGN] Runs the laptopfinder eBay-AU operator pipeline. Precondition checks, fixture regression, a gated live scrape, and reporting. 
---
# Laptopfinder Operator Skill (Archived Reference)

*Note: This is a reference design document, not an active configuration. Retained for its high-value patterns in Preconditions and Fixture Sanity.*

## High-Value Patterns

**Phase 0: Preconditions**
- Check tool availability (`make check-operator-surface`).
- Check test suite status, environment keys, and feed source valid lines.
- Report go/no-go status before any external network activity.

**Phase 1: Fixture Sanity**
- Run single and paired fixture regression tests. Verify green suite.
- Serves as a zero-cost, zero-network regression check before touching live data.

*(Phases 2-5 are deferred until the pipeline reaches production volume and requires multi-agent orchestration.)*
