# eBay AU Discovery & Sniper Plan — High-VRAM & UMA Hardware Acquisition
**Status:** Proposed Implementation Plan (Refined & Enhanced)  
**Target Architecture:** Token-Free Local Sniper (`scripts/ebay_sniper.py`) vs. Deep Multimodal Hunter (`src/laptopfinder/runners/ebay_hunter.py`)

---

## 1. Executive Summary & Architecture Topology

### 1.1 The Strategic Problem & Why Two Tools
The repository currently implements `ebay_hunter.py` as a deep, scheduled batch intelligence pipeline: it ingests listings, runs Gemini reasoning and vision across DOM and box photos, applies the Stage 1/Stage 2 grounding firewall, and emails comprehensive multi-target reports. While powerful for weekly market intelligence, **it is architecturally unsuited for real-time sniper acquisition of underpriced flagship hardware**:
- **Latency:** Email gateways (`smtplib`) and multi-pass LLM evaluations introduce delays (minutes to hours) during which private "Buy It Now" mispricings are sniped by competitors.
- **Token Economy:** Running LLM vision and reasoning loops on high-frequency 5-minute polling sweeps wastes API tokens on repetitive market noise.

To solve this, we introduce **`scripts/ebay_sniper.py`**: an ultra-low-latency, token-free, deterministic local sniper designed for immediate acquisition. It runs as a detached background loop, pushes zero-junk filtering to eBay's API servers, performs deterministic algorithmic price gating against `static_reference_layer.json`, and alerts the buyer instantaneously via macOS iMessage.

### 1.2 Architectural Separation of Concerns
| Dimension | `src/laptopfinder/runners/ebay_hunter.py` (Existing) | `scripts/ebay_sniper.py` (Proposed) |
| :--- | :--- | :--- |
| **Primary Goal** | Comprehensive market intelligence & verification | Zero-latency sniper acquisition of underpriced hits |
| **Execution Frequency** | On-demand / scheduled daily batch | Continuous 5-minute polling loop (`sleep(300)`) |
| **LLM & Token Usage** | Gemini 3.1 Pro reasoning + vision ground-truth | **Zero LLM tokens** (pure deterministic Python + REST) |
| **Filtering Layer** | Local Stage 1/Stage 2 grounding firewall | eBay Browse API server-side filters + local SRL regex |
| **Alerting Mechanism** | Formatted HTML/Text Email (`smtplib` via SMTP) | Instant macOS iMessage (`osascript` AppleScript push) |
| **Target Audience** | Analyst / Strategic Matrix building | Local Buyer (+61412202666, Northcote VIC 3070) |

---

## 2. Operational Lifecycle, State Management & Resilience

### 2.1 Process Daemonization & Execution
The sniper is designed to run locally on the buyer's macOS machine with zero external cloud infrastructure:
- **Foreground Development / Test:** Invoked via `.venv/bin/python -m scripts.ebay_sniper --dry-run` or `--once`.
- **Background Execution:** Managed via `Makefile` targets:
  - `make start-sniper`: Launches detached process via `nohup` or `launchctl`, writing logs to `data/logs/sniper.log`.
  - `make stop-sniper`: Terminate process cleanly via PID file (`data/sniper.pid`).
  - `make status-sniper`: Reports process uptime, last check timestamp, and hit counts.
- **Boot Persistence (Optional):** A macOS `launchd` property list (`com.laptopfinder.ebaysniper.plist`) in `~/Library/LaunchAgents/` ensures automatic background restart upon system reboot or crash.

### 2.2 State Persistence & Deduplication Schema
To prevent spam while ensuring price-drop responsiveness, state is maintained in `data/seen_sniper_items.json`.
**JSON Schema Structure:**
```json
{
  "last_sweep_utc": "2026-07-05T07:50:00Z",
  "total_alerts_sent": 14,
  "seen_items": {
    "v1|123456789012|0": {
      "item_id": "v1|123456789012|0",
      "title": "ASUS ROG Strix RTX 4090 24GB Laptop - Imperfect Box",
      "first_seen_utc": "2026-07-05T06:00:00Z",
      "last_price_aud": 3400.00,
      "strategy_triggered": "STRATEGY_A_FLAGSHIP",
      "alert_count": 1,
      "last_alerted_utc": "2026-07-05T06:00:00Z"
    }
  }
}
```
**Deduplication & Price-Drop Re-Alert Logic:**
1. When an item is fetched, check if `item_id` exists in `seen_items`.
2. **New Item:** If absent, evaluate against strategy rules. If matched -> send iMessage, record item, set `alert_count = 1`.
3. **Price-Drop Trigger:** If `item_id` exists, check if `new_price < last_price_aud` by at least $50 AUD AND `new_price <= observed_au_price_min_aud`. If true -> send a "🔻 PRICE DROP ALERT" iMessage, update `last_price_aud` and `last_alerted_utc`, increment `alert_count`.
4. **Atomic Writes:** State updates write to a temporary file (`seen_sniper_items.json.tmp`) before renaming, preventing file corruption if interrupted during write.

### 2.3 Authentication & Network Resilience
- **Token Renewal:** Reuses `get_ebay_token()` from `ebay_api.py`. Before each polling cycle, checks token validity or calls `scripts/authenticate_ebay.sh` automatically if a `401 Unauthorized` response is encountered.
- **Rate Limit Handling (HTTP 429):** Implements exponential backoff (`sleep(60 * (2 ** attempt))`) up to 3 retries if eBay API throttling occurs.
- **Network Fault Tolerance:** Catch `urllib.error.URLError` and socket timeouts, log warnings to stderr/log file, and sleep until the next scheduled 300-second epoch without crashing the background daemon.

---

## 3. Deep Specification of Sniper Strategies

### 3.1 Strategy A: The "Unicorn" Flagship Sweep (National)
Designed to catch ultra-rare, high-value discrete GPUs and high-capacity Apple Silicon UMA systems anywhere in Australia before market discovery. Bypasses standard price ceilings.
* **REST Endpoint:** `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
* **Query Parameters (`params`):**
  * `q`: `"RTX 5090" OR "RTX 4090" OR "RTX 3080 Ti" OR "RTX 5000 Ada" OR "M3 Max" OR "M3 Ultra" OR "Strix Halo"`
  * `category_ids`: `175672` (PC Laptops & Netbooks)
  * `filter`: `itemLocationCountry:AU,price:[1500..8000],priceCurrency:AUD`
  * `sort`: `newlyListed` (First-Mover advantage: captures mispriced private listings within minutes of posting)
  * `limit`: `20`
  * `fieldgroups`: `EXTENDED` (Enables `shortDescription` and `itemLocation.city` in summaries for context-rich iMessages)
* **Trigger Condition:** Any newly listed item matching these keywords where `item_id` is unseen triggers an immediate budget-bypass iMessage alert.

### 3.2 Strategy B: The Local Algorithmic Sniper (Melbourne / Northcote 3070)
Designed for standard target GPUs (e.g., RTX 3080, RTX 4080, RX 7900M) listed within a drivable radius, enabling same-day local pickup and cash/credit-on-collection negotiation.
* **REST Endpoint:** `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
* **Context Headers:**
  * `X-EBAY-C-MARKETPLACE-ID`: `EBAY_AU`
  * `X-EBAY-C-ENDUSERCTX`: `contextualLocation=country=AU,zip=3070`
* **Query Parameters (`params`):**
  * `q`: `"RTX 4080" OR "RTX 3080" OR "RTX 4070 Ti" OR "RX 7900"`
  * `category_ids`: `175672`
  * `filter`: `pickupCountry:AU,pickupPostalCode:3070,pickupRadius:100,pickupRadiusUnit:km,buyingOptions:{FIXED_PRICE|BEST_OFFER},sellerAccountTypes:{INDIVIDUAL}`
  * `sort`: `newlyListed`
  * `fieldgroups`: `EXTENDED`
* **Algorithmic Price Gating via SRL:**
  1. Parse the discovered GPU model from title/aspects.
  2. Load `config/static_reference_layer.json` -> `target_gpus[model].observed_au_price_min_aud` (or `observed_au_price_max_aud` depending on aggressiveness threshold).
  3. **Trigger Condition:** If `listing_price <= observed_au_price_min_aud` (or within 10% of the minimum observed floor), trigger the local alert.
* **Why Individual Sellers:** Private sellers (`sellerAccountTypes:{INDIVIDUAL}`) are significantly more likely to underprice heavy gaming/workstation laptops to avoid shipping risks.

### 3.3 Strategy C: The Precision Inclusion Layer (Zero-Junk API & Firewall)
Eliminates LLM token waste by pushing negative filtering to eBay's server infrastructure and backing it up with our deterministic local firewall.
* **Server-Side API Filters:**
  * `conditionIds`: `1000,2000,3000` (New, Certified Refurbished, Used Excellent/Good). Completely drops condition ID `7000` ("For Parts or Not Working") before the packet leaves eBay's edge.
  * `aspect_filter`: `categoryId:175672,GPU Memory Size:{16 GB|24 GB|32 GB|64 GB|128 GB}`. Forces eBay to strip out "16GB RAM / Integrated Graphics" office laptops that clutter standard keyword searches.
* **Local Deterministic Grounding Firewall:**
  * Before triggering any alert, check `title` and `shortDescription` against `data_integrity.exclusion_regex` loaded from `static_reference_layer.json`:
    `(?i)(bare shell|missing motherboard|screen only|no mobile-gpu|no core|chassis only|parts only|read description|junk|as-is|bare board)`
  * Any match results in silent discard and logging to debug trace, guaranteeing zero spam reaching the buyer's phone.

---

## 4. Native macOS iMessage Alerting Engine

### 4.1 AppleScript (`osascript`) Execution Design
To achieve zero-gateway latency and lock-screen visibility, alerts bypass SMTP and SMS gateways entirely by invoking macOS Messages directly.
* **Target Recipient:** `+61412202666` (or configured via `.env` variable `SNIPER_IMESSAGE_TARGET`).
* **Execution Subprocess:** Uses Python `subprocess.run(["osascript", "-e", script], check=True, timeout=10)`.
* **AppleScript Payload Template:**
```applescript
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "+61412202666" of targetService
    send "🎯 EBAY SNIPER ALERT [STRATEGY_A_FLAGSHIP]
📦 ASUS ROG Strix SCAR 18 (RTX 4090 24GB)
💰 Price: $3,350.00 AUD (Floor: $3,500 AUD)
📍 Location: Melbourne, VIC (12 km away)
🏷️ Condition: USED_EXCELLENT (Private Seller)
🔗 https://www.ebay.com.au/itm/123456789012" to targetBuddy
end tell
```

### 4.2 Security & String Sanitization
* **Injection Prevention:** Listing titles and descriptions from external API payloads can contain quotes, backslashes, or special characters. All text inserted into AppleScript must be strictly escaped by replacing `\` with `\\` and `"` with `\"`, or passed via secure stdin piping to prevent AppleScript execution injection.
* **Fallback Notification:** If `osascript` fails (e.g., Messages app closed or iCloud disconnected), the script logs an error to `data/logs/sniper.log` and triggers a macOS system notification via `osascript -e 'display notification "eBay hit found but iMessage failed!" with title "LaptopFinder Sniper"'`.

---

## 5. Software 2.0 & Karpathy Invariants Compliance
1. **No Logic in Prompts:** Zero prompts are used in this tool. All filtering is handled by REST aspect filters and Python regex.
2. **SRL as Governance Layer:** All price thresholds, exclusion regexes, and target GPU names are dynamically read from `config/static_reference_layer.json`. Zero hardcoded thresholds in Python source.
3. **Flat, Functional Python:** Structure remains Karpathy-style clean: standard library JSON/urllib/subprocess, explicit dictionary mapping, no complex class hierarchies or abstraction layers.

---

## 6. Proposed Component & File Modifications

### 6.1 Summary of Changes
```
scripts/
  └── [NEW] ebay_sniper.py          # Active token-free local sniper loop
Makefile                              # [MODIFY] Add start-sniper, stop-sniper, status-sniper, test-alert
config/
  └── [MODIFY] static_reference_layer.json # Ensure all required target_gpus have observed_au_price_min_aud
data/
  └── [NEW] seen_sniper_items.json  # Initial state persistence tracker
```

### 6.2 Detailed File Breakdowns

#### [NEW] [scripts/ebay_sniper.py](file:///Users/okgoogle13/Projects/laptopfinder/scripts/ebay_sniper.py)
* **Core Functions:**
  * `load_seen_state() -> dict` / `save_seen_state(state: dict) -> None`: Handles atomic JSON file read/write with `.tmp` swapping.
  * `execute_browse_query(token: str, params: dict, context_headers: dict = None) -> list[dict]`: Wrapper around `urllib.request` with 429 exponential backoff and error logging.
  * `run_strategy_a_flagship(token: str, seen: dict, srl: dict) -> list[dict]`: Executes National Flagship Unicorn sweep.
  * `run_strategy_b_local(token: str, seen: dict, srl: dict) -> list[dict]`: Executes Northcote VIC 3070 Local Algorithmic Sniper sweep with SRL price gating.
  * `apply_firewall(item: dict, srl: dict) -> bool`: Checks condition IDs and regex exclusion patterns.
  * `send_imessage(target_phone: str, text: str) -> bool`: Sanitizes text and invokes `osascript` via subprocess.
  * `main_loop(interval_sec: int = 300)`: Continuous orchestration loop with graceful SIGINT/SIGTERM handlers.

#### [MODIFY] [Makefile](file:///Users/okgoogle13/Projects/laptopfinder/Makefile)
* Add `.PHONY` entries: `start-sniper`, `stop-sniper`, `status-sniper`, `test-sniper-alert`.
* Add targets:
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

---

## 7. Verification & Quality Assurance Plan

### 7.1 Automated Unit & Integration Testing
* **Schema Verification:** Create a test fixture `tests/test_ebay_sniper.py` to verify that `seen_sniper_items.json` conforms to required schema keys and deduplication logic works as expected.
* **Firewall Unit Tests:** Assert that sample titles matching `exclusion_regex` ("ASUS RTX 4090 Laptop - Bare Shell No Motherboard") return `False` from `apply_firewall()`, while valid listings return `True`.
* **SRL Gating Tests:** Assert that Strategy B rejects items where `price > observed_au_price_min_aud` and accepts items below floor.

### 7.2 Manual & Live Verification Steps
1. **iMessage Connectivity Test:**
   Run `make test-sniper-alert` and verify that +61412202666 receives a cleanly formatted test iMessage via macOS Messages within 2 seconds.
2. **Dry-Run Sandbox Sweep:**
   Run `.venv/bin/python scripts/ebay_sniper.py --dry-run --once` against live eBay sandbox/production APIs. Verify console output correctly logs searched queries, filtered items, and mock alerts without modifying `data/seen_sniper_items.json`.
3. **Daemon Lifecycle Verification:**
   Execute `make start-sniper`, verify background process uptime via `make status-sniper`, inspect `data/logs/sniper.log`, and terminate cleanly using `make stop-sniper`.

---

## 8. Future Scope & Valuations (Gated)

### 8.1 Real Sold-Price Baselines via Marketplace Insights (D1)
* **Endpoint:** `GET /buy/marketplace_insights/v1_beta/item_sales/search` (90-day realized prices).
* **Objective:** Replace static `observed_au_price_min_aud` medians in `static_reference_layer.json` with dynamic realized sold-price percentiles.
* **Access Constraint:** Requires the separate `buy.marketplace.insights` OAuth scope, which mandates specific eBay Developer Program business vetting and approval. This module is scoped for Phase 2 implementation once API permissions are granted.