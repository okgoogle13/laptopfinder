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
* **Start Background Daemon:**
  ```bash
  make start-sniper
  ```
  Runs in background (5-minute loop), logging to `data/logs/sniper.log` and storing PID in `data/sniper.pid`.
* **Check Status:**
  ```bash
  make status-sniper
  ```
* **Stop Background Daemon:**
  ```bash
  make stop-sniper
  ```
* **Test iMessage Delivery:**
  ```bash
  make test-sniper-alert
  ```
* **Dry-Run / Single-Pass Test:**
  ```bash
  .venv/bin/python scripts/ebay_sniper.py --dry-run --once
  ```

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
