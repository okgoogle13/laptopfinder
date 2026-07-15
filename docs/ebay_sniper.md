# eBay AU Sniper (`scripts/ebay_sniper.py`)

A lightweight, token-free background daemon designed to detect underpriced flagship and high-capacity UMA laptop hardware on eBay AU, pushing instant alerts to macOS iMessage.

## Overview
* **Strategy A: Flagship Sweep (National)**
  * Searches nationally for newly listed high-VRAM / UMA targets. Keyword list derived at runtime from `target_gpus` keys + `uma_platforms.chip_patterns` in `config/static_reference_layer.json`.
  * Bypasses budget ceilings to alert on first-mover flagship postings immediately.
* **Strategy B: Local Algorithmic Sniper (Melbourne VIC 3070)**
  * Filters to individual sellers within a 100km radius of Northcote VIC 3070 for local pickup / cash negotiation.
  * Dynamically gates asking prices against `observed_au_price_min_aud` loaded from `config/static_reference_layer.json`.
* **Zero-Junk Firewall**
  * Drops condition ID `7000` (For Parts / Not Working) at the eBay Browse API edge.
  * Rejects listings matching `exclusion_regex` (e.g., bare shells, missing motherboards, screen-only).

## How to Run
* **Run Live (Continuous Sweep):**
  ```bash
  make live
  # Equivalent to:
  # op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper
  ```
  Runs in the foreground, executing a sweep every 5 minutes (300 seconds).

* **Run a Dry-Run Single-Pass Test:**
  ```bash
  op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper --dry-run --once
  ```

* **Test iMessage Alerting Logic:**
  ```bash
  op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper --test-alert
  ```

* **Change Polling Interval:**
  ```bash
  op run --env-file=.env -- .venv/bin/python -m laptopfinder.runners.ebay_sniper --interval 600
  ```

## Running Unattended

`make live` runs in the foreground and dies when the terminal closes. For an unattended run that survives closing the terminal (but not reboot/logout), use `make live-daemon` — it wraps the same command in `nohup`, detaches it, logs to `data/logs/sniper.log`, and tracks the PID in `data/sniper.pid`:

```bash
make live-daemon    # start, detached
make live-tail       # follow the log (Ctrl-C just stops tailing, daemon keeps running)
make live-stop        # stop, cleans up data/sniper.pid
```

`live-daemon` refuses to start a second instance if `data/sniper.pid` already points at a live process — run `make live-stop` first. This is the standardized method (chosen over launchd/tmux for simplicity — no system-service setup, no extra terminal multiplexer dependency); revisit launchd only if the sniper needs to survive machine reboot/logout unattended.

## Configuration Requirements (`.env`)
* `EBAY_ACCESS_TOKEN` (or run `scripts/authenticate_ebay.sh` to generate `.ebay_access_token`)
* `SNIPER_APPLE_ID` (target phone number e.g. `+61412202666` or iCloud email for iMessage delivery)

## Alert Format
When a match is found, macOS Messages pushes an instant alert:
```
🎯 [Sniper] Local Match!
📦 ASUS ROG Strix Scar 18 RTX 4080 32GB RAM Laptop
💰 Price: $2800.0 AUD (Floor: $2800.0)
🔗 https://www.ebay.com.au/itm/123456789012
```

## Dry-Run Verification
* 2026-07-05: Unit test suite (`tests/test_ebay_sniper.py`) executed and passed clean.
* 2026-07-05: Single-pass dry run (`--dry-run --once`) verified syntax, firewall evaluation, and zero-state mutation.

## Live Daemon Log
* 2026-07-05 — Daemon launched. PID: 93807. Status: 🟢 running. Keywords and price floors derived from SRL at runtime (post peer-review fix). `make test` 174/174 green.
