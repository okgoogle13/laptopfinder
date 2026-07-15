# Autonomous Agentic Deep Plan: eBay AU Sniper Setup & Implementation
**Task ID:** `laptopfinder-ebay-sniper`  
**Title:** Laptopfinder: eBay AU Sniper Setup  
**Tri-Tooling Architecture:** Antigravity IDE (Orchestration) + Claude Code CLI (Autonomous Execution) + Codex CLI (Adversarial Peer Reviewer)  
**Status:** Approved for Deep Implementation  

---

## 1. Executive Strategy & Tri-Tooling Collaboration Matrix

This deep plan operationalizes the **eBay AU Sniper Setup** across four rigorous stages using our tri-tooling agentic framework:
1. **Antigravity IDE / CLI (Orchestrator):** Maintains the high-level context, manages stage progression, monitors verification gates, and documents architectural state.
2. **Claude Code CLI (`mode: accept-edits`):** Acts as the autonomous execution engineer. Writes flat, Karpathy-style Python, implements POSIX-compliant Makefile targets, authors high-signal documentation, and executes unit/dry-run tests.
3. **Codex CLI (`scripts/deep_plan_peer_review.sh`):** Acts as the adversarial peer reviewer. Audits proposed code and plan boundaries against repository invariants (SRL ownership of thresholds, Python firewall enforcement, zero LLM token waste in sniper loop, flat functional architecture, null-not-fabricate behavior).

```
+-------------------+        Plan Review        +--------------------+
|  Antigravity IDE  | <-----------------------> |     Codex CLI      |
| (Orchestration &  |     (Adversarial Audit)   | (peer-review prof) |
|   State Control)  |                           +--------------------+
+---------+---------+
          |
          | Delivers Approved Task Scopes & Stage Transitions
          v
+-------------------+
|  Claude Code CLI  | ---> Executes Mechanical Edits (`accept-edits`)
|  (Autonomous Dev) | ---> Runs Unit Tests & Live Dry-Runs (`--once`)
+-------------------+
```

---

## 2. Stage 1: Plan & Tighten Sniper Script (`scripts/ebay_sniper.py`)

### 2.1 Code Review of Initial Draft (`Zimport json...`)
The user's initial draft snippet exhibited several critical flaws that violate repository invariants:
- **Syntax Error:** Line 1 contained `Zimport json` instead of `import json`.
- **Hardcoded Thresholds:** Static lists (`FLAGSHIP_KEYWORDS`, `LOCAL_MODELS`) and hardcoded price percentages (`price > floor_val * 1.10`) violate the invariant that `config/static_reference_layer.json` (SRL) is the single source of truth for target hardware and gating thresholds.
- **Missing CLI Control:** Lacked `argparse` flags required for safe, autonomous testing (`--dry-run`, `--once`, `--test-alert`, `--interval`).
- **Unsafe State Mutating:** Without `--dry-run`, testing the script would pollute `data/seen_sniper_items.json` and trigger unwanted iMessage spam to the buyer.

### 2.2 Corrected Architecture Specification
We will implement `scripts/ebay_sniper.py` as a lean, flat, zero-class Python module that complies with Software 2.0 and Karpathy guidelines:
- **CLI Interface:** Use `argparse` to support:
  - `--dry-run`: Log evaluated matches and mock iMessages without writing to `SEEN_FILE` or invoking `osascript`.
  - `--once`: Execute a single polling cycle over Strategy A and Strategy B, then terminate cleanly (essential for CI and verification).
  - `--test-alert`: Instantly send a synthetic test iMessage to `SNIPER_APPLE_ID` and exit.
  - `--interval <sec>`: Polling epoch duration (default 300 seconds).
- **Dynamic SRL Gating:** Load `config/static_reference_layer.json` dynamically at the start of each sweep. For Strategy B (Local Melbourne), derive acceptable price ceilings directly from `target_gpus[model].observed_au_price_min_aud` (or fallback to max observed).
- **Deterministic Firewall:** Implement `apply_firewall(title)` matching titles against `exclusion_regex` loaded from the SRL, instantly dropping parts-only/salvaged chassis listings.
- **Resilient HTTP & Token Handling:** Implement 3-attempt exponential backoff for HTTP 429 (Rate Limit Exceeded), automatic token expiration warnings on HTTP 401, and graceful `URLError` recovery.

---

## 3. Stage 2: Makefile Wiring & Documentation (`docs/ebay_sniper.md`)

### 3.1 POSIX-Compatible Makefile Targets
We will append four clean, POSIX-compliant targets to `Makefile`:
```makefile
start-sniper:
	@echo "Starting eBay Sniper Daemon..."
	@mkdir -p data/logs
	@nohup .venv/bin/python scripts/ebay_sniper.py > data/logs/sniper.log 2>&1 & echo $$! > data/sniper.pid
	@echo "Sniper running in background (PID: $$(cat data/sniper.pid)). Logs at data/logs/sniper.log"

stop-sniper:
	@test -f data/sniper.pid || (echo "Sniper not running (no PID file)." && exit 1)
	@kill -15 $$(cat data/sniper.pid) && rm -f data/sniper.pid
	@echo "Sniper daemon stopped."

status-sniper:
	@if [ -f data/sniper.pid ] && ps -p $$(cat data/sniper.pid) > /dev/null; then \
		echo "🟢 Sniper running (PID: $$(cat data/sniper.pid))"; \
		tail -n 5 data/logs/sniper.log; \
	else \
		echo "🔴 Sniper stopped."; \
	fi

test-sniper-alert:
	@echo "Sending test iMessage alert to configured target..."
	.venv/bin/python scripts/ebay_sniper.py --test-alert
```

### 3.2 Documentation Specification (`docs/ebay_sniper.md`)
Create a high-signal, bulleted technical reference document containing:
- **Overview:** Explanation of the two sniper strategies (National Flagship Unicorn Sweep vs. Melbourne Local Algorithmic Sniper).
- **Quickstart & Daemon Commands:** Usage instructions for `make start-sniper`, `make status-sniper`, `make stop-sniper`, and `make test-sniper-alert`.
- **Environment & Configuration:** Explaining `.env` variables (`EBAY_ACCESS_TOKEN`, `SNIPER_APPLE_ID`) and state file tracking (`data/seen_sniper_items.json`).
- **Verification Log Section:** A designated section at the bottom (`## Dry-Run Verification`) where automated dry-run outputs and heartbeat status entries are appended.

---

## 4. Stage 3: Tests & Dry-Run Verification

### 4.1 Unit Test Suite (`tests/test_ebay_sniper.py`)
To guarantee zero regression and invariant adherence, write unit tests covering:
- `test_normalize()`: Verifies whitespace stripping and uppercase conversion.
- `test_apply_firewall()`: Asserts that valid gaming laptop titles pass while titles containing "Bare Shell", "Missing Motherboard", "Parts Only", or "Screen Only" return `False`.
- `test_price_floor_logic()`: Uses a mocked SRL dictionary and synthetic item payloads to verify that listings priced above the SRL floor threshold are rejected, while underpriced hits trigger alerts.

### 4.2 Live Dry-Run Execution Protocol
1. Execute `.venv/bin/pytest tests/test_ebay_sniper.py -v` to validate unit logic.
2. Execute `.venv/bin/python scripts/ebay_sniper.py --dry-run --once` against live eBay endpoints.
3. Verify that the script successfully queries eBay AU, filters summaries, outputs formatted logs, and **makes zero mutations** to `SEEN_FILE` while sending **zero real iMessages**.
4. Append the dry-run summary into `docs/ebay_sniper.md`.

---

## 5. Stage 4: Start Sniper Daemon (Gated)

### 5.1 Pre-Daemon Summary Checkpoint
Before launching a background daemon, the agent must output a comprehensive status report:
- Syntax and unit test test suite status (`PASSED`).
- Dry-run verification summary (number of items evaluated, hits discovered, firewall discards).
- Makefile target readiness.

### 5.2 Explicit User Sign-Off Gate
In strict compliance with our data protection and daemon management rules, **the background daemon (`make start-sniper`) will NOT be started autonomously**. The agent will pause and request explicit user confirmation before executing Stage 4. Once confirmed, it will start the daemon, check `make status-sniper`, append a heartbeat timestamp to `docs/ebay_sniper.md`, and conclude the task.
