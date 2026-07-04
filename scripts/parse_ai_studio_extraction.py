"""Parse the AI Studio JSON extraction response and run the full pipeline.

Reads:
  data/ai_studio_responses/ebay_csv_extraction.json  (the AI Studio output)
  data/fixtures/ebay_cleaned.csv                      (the original CSV for baseline fields)

Writes:
  data/processed_candidates/csv_import_<listing_id>.json  (one file per listing)
  data/shortlist_candidates.jsonl                          (matrix input)
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from laptopfinder.decide import decide

RESPONSE_PATH = Path("data/ai_studio_responses/ebay_csv_extraction.json")
CSV_PATH      = Path("data/fixtures/ebay_cleaned.csv")
SCHEMA_PATH   = Path("src/laptopfinder/schemas/ebay_hardware_listing.schema.json")
OUT_DIR       = Path("data/processed_candidates")
SHORTLIST_OUT = Path("data/shortlist_candidates.jsonl")

# Reject explicit desktop / tower / mini-PC form factors.
# Laptop workstations (ZBook, Precision, ThinkPad P-series) are intentionally
# NOT matched here — their titles contain "Laptop" or lack "Gaming PC" / "Tower".
DESKTOP_EXCLUSION_RE = re.compile(
    r"(?i)(\bGaming PC\b|\bDesktop PC\b|\bDesktop\b|\bTower\b|\bSFF\b"
    r"|\bMini PC\b|\bAll-in-One\b|\bAIO\b|\bAurora R\d|\bZ[0-9]+ G[0-9]+ (?:Workstation|Tower)\b)"
)


def clean_price(price_raw: str | None) -> float | None:
    if not price_raw or not isinstance(price_raw, str):
        return None
    price_raw = price_raw.strip()
    if price_raw.lower() in ("item not available", "not available", ""):
        return None
    m = re.search(r'\$\s*([0-9,]+(?:\.[0-9]+)?)', price_raw)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def parse_gb(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, int) and val != 0:
        return val
    if isinstance(val, float) and val != 0.0:
        return int(val)
    if isinstance(val, str):
        m = re.search(r"(\d+(?:\.\d+)?)\s*GB", val, re.IGNORECASE)
        return int(float(m.group(1))) if m else None
    return None


def main() -> int:
    if not RESPONSE_PATH.exists():
        print(f"ERROR: AI Studio response not found at {RESPONSE_PATH}", file=sys.stderr)
        print("Run scripts/generate_ai_studio_prompt.py first, paste into AI Studio, then save the result.", file=sys.stderr)
        return 1
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}", file=sys.stderr)
        return 1
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found at {SCHEMA_PATH}", file=sys.stderr)
        return 1

    with open(RESPONSE_PATH, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        # Strip markdown fences if AI Studio wrapped it
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        extractions = json.loads(raw)

    if not isinstance(extractions, list):
        print("ERROR: AI Studio response must be a JSON array.", file=sys.stderr)
        return 1

    # Index extractions by listing_id
    extraction_map = {e["listing_id"]: e for e in extractions if "listing_id" in e}
    print(f"Loaded {len(extraction_map)} extraction records from AI Studio response.")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Load CSV rows indexed by listing_id
    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        csv_rows = {row["listing_id"]: row for row in csv.DictReader(f)}

    # Build GPU->VRAM lookup from SRL target_gpus (the governance layer).
    # Used as fallback when the listing title did not state VRAM explicitly.
    srl_path = Path("config/static_reference_layer.json")
    gpu_vram_lookup: dict[str, int] = {}
    if srl_path.exists():
        srl = json.load(open(srl_path, encoding="utf-8"))
        for gpu_key, gpu_data in srl.get("target_gpus", {}).items():
            if isinstance(gpu_data, dict) and "vram_gb" in gpu_data:
                gpu_vram_lookup[gpu_key.lower()] = gpu_data["vram_gb"]
        # Also add from gpu_generation_by_name keys that appear in target_gpus
        # This covers aliases like "GeForce RTX 4090" -> "RTX 4090"
        print(f"SRL VRAM lookup built: {len(gpu_vram_lookup)} known GPUs")


    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHORTLIST_OUT.parent.mkdir(parents=True, exist_ok=True)

    shortlist_candidates = []
    ok = skipped = 0

    for listing_id, csv_row in csv_rows.items():
        ext = extraction_map.get(listing_id, {})

        platform    = csv_row.get("platform", "EBAY_AU")
        title       = csv_row.get("title", "")
        price_raw   = csv_row.get("price_raw")
        condition   = csv_row.get("condition") or None
        seller_name = csv_row.get("seller_name") or None
        url         = csv_row.get("url", "")

        # Form-factor gate: reject desktops/towers before any further processing.
        if DESKTOP_EXCLUSION_RE.search(title):
            print(f"SKIP [desktop]: {title[:70]}")
            skipped += 1
            continue

        price_cleaned   = clean_price(price_raw)
        raw_gpu         = ext.get("gpu_name", "")
        raw_vram        = ext.get("vram_capacity", 0)
        raw_cpu         = ext.get("cpu_name", "")
        raw_ram         = ext.get("total_system_ram", 0)
        raw_storage     = ext.get("storage", "")
        raw_egpu        = ext.get("egpu_model", "")
        raw_touch       = ext.get("touchscreen_digitizer", False)
        raw_model       = ext.get("exact_model_name", "")

        gpu_name        = raw_gpu   if raw_gpu   != "" else None
        vram_val        = parse_gb(raw_vram)
        cpu_name        = raw_cpu   if raw_cpu   != "" else None
        ram_val         = parse_gb(raw_ram)
        storage         = raw_storage if raw_storage != "" else None
        egpu_model      = raw_egpu  if raw_egpu  != "" else None
        touchscreen     = raw_touch if raw_touch else None
        exact_model     = raw_model if raw_model != "" else None

        # SRL VRAM fallback: if the title didn't state VRAM, look it up from the
        # governance layer by matching the extracted GPU name.
        if vram_val is None and gpu_name:
            # Try progressively shorter suffix matches (e.g. "GeForce RTX 4090" -> "RTX 4090")
            gpu_lower = gpu_name.lower().strip()
            vram_from_srl = gpu_vram_lookup.get(gpu_lower)
            if vram_from_srl is None:
                # Try stripping common prefixes
                for prefix in ("geforce ", "nvidia ", "quadro ", "mobile "):
                    stripped = gpu_lower.removeprefix(prefix)
                    vram_from_srl = gpu_vram_lookup.get(stripped)
                    if vram_from_srl:
                        break
            if vram_from_srl is None:
                # Normalise spacing (e.g. "rtx5080" -> "rtx 5080") — case-insensitive
                normalised = re.sub(r"(rtx a|quadro rtx|rtx|gtx)", r"\1 ", gpu_lower, flags=re.IGNORECASE)
                normalised = re.sub(r"\s+", " ", normalised).strip()
                vram_from_srl = gpu_vram_lookup.get(normalised)
            if vram_from_srl:
                print(f"  SRL VRAM fallback: {gpu_name!r} -> {vram_from_srl}GB (title had no VRAM spec)")
                vram_val = vram_from_srl

        candidate = {
            "platform":              platform,
            "listing_id":            listing_id,
            "url":                   url,
            "title":                 title,
            "price_aud":             price_cleaned,
            "seller_name":           seller_name,
            "seller_rating":         None,
            "condition_code":        None,
            "condition_label":       condition,
            "shipping_type":         None,
            "pickup_location_text":  None,
            "category_path":         "Computers/Tablets & Networking > Laptops & Netbooks",
            "full_listing_text":     title,
            "scraped_at":            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "gpu_name":              gpu_name,
            "vram_capacity":         vram_val,
            "cpu_name":              cpu_name,
            "total_system_ram":      ram_val,
            "storage":               storage,
            "egpu_model":            egpu_model,
            "touchscreen_digitizer": touchscreen,
            "exact_model_name":      exact_model,
        }

        try:
            jsonschema.validate(candidate, schema)
        except jsonschema.ValidationError as e:
            print(f"WARN: Validation failed for {listing_id}: {e.message}", file=sys.stderr)
            skipped += 1
            continue

        safe_id = listing_id.replace(":", "_")
        out_file = OUT_DIR / f"csv_import_{safe_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(candidate, f, indent=2)

        # Build Stage 2 analysis payload for decision engine
        vram_parsed = (
            {"semantic_value": float(vram_val), "verbatim_quote": f"{vram_val}GB"}
            if vram_val else None
        )
        analysis_payload = {
            "metadata": {
                "source_platform":               platform,
                "listing_url_or_identifier":      url,
                "listing_title":                  title,
                "listing_price_aud":              price_cleaned,
                "seller_name_or_identifier":      seller_name,
                "seller_rating_or_profile_signal": None,
            },
            "extracted_data": {
                "exact_model_name":      exact_model,
                "component_category":    "SYSTEM",
                "cpu":                   cpu_name,
                "gpu":                   gpu_name,
                "ram":                   f"{ram_val}GB" if ram_val else None,
                "storage":               storage,
                "vram_capacity":         vram_parsed,
                "stated_condition":      condition,
                "shipping_or_pickup_signal": "UNKNOWN",
                "missing_information": {
                    "gpu":       gpu_name is None,
                    "vram":      vram_val is None,
                    "cpu":       cpu_name is None,
                    "ram":       ram_val is None,
                    "storage":   storage is None,
                    # condition is structurally unavailable in CSV-only ingestion
                    # (title-only, no full listing page scraped); exclude from risk gate.
                    "condition": False,
                },
                "total_system_ram":      f"{ram_val}GB" if ram_val else None,
                "egpu_model":            egpu_model,
                "touchscreen_digitizer": "touchscreen" if touchscreen else None,
            },
            "analysis": {
                "risk_score":             1.0,
                "risk_flags":             [],
                "stated_pickup_location": None,
                "confidence":             0.8,
                "seller_classification":  "PRIVATE_ESTABLISHED",
            },
        }

        try:
            decision = decide(analysis_payload)
            action = decision["recommended_action"]
            notes = "; ".join(decision["reasons"])

            # Reclassify data-poor SKIPs as MANUAL_REVIEW with recovery hints
            # so they appear in the matrix rather than being silently excluded.
            recovery_hint = None
            if action == "SKIP":
                reasons_text = notes.lower()
                if "missing fields" in reasons_text:
                    mi = analysis_payload["extracted_data"]["missing_information"]
                    missing_names = [k for k, v in mi.items() if v]
                    recovery_hint = f"Missing: {', '.join(missing_names)} — check listing page or photos"
                    action = "MANUAL_REVIEW"
                elif "vram too low or unknown" in reasons_text and gpu_name:
                    recovery_hint = f"VRAM unknown for '{gpu_name}' — verify on listing page spec table"
                    action = "MANUAL_REVIEW"
                elif "touchscreen exception" in reasons_text:
                    recovery_hint = f"VRAM {vram_val}GB needs touchscreen exception — check if listing has touch display"
                    action = "MANUAL_REVIEW"

            if recovery_hint:
                notes = f"{notes}; 🔍 {recovery_hint}"

            shortlist_candidates.append({
                "recommended_action": action,
                "llm_index_score":    decision["llm_index_score"],
                "listing_title":      title,
                "gpu":                gpu_name or "—",
                "price":              f"AU ${price_cleaned:.2f}" if price_cleaned else "—",
                "notes":              notes,
            })
            ok += 1
        except Exception as e:
            print(f"WARN: Decision engine failed for {listing_id}: {e}", file=sys.stderr)
            skipped += 1

    with open(SHORTLIST_OUT, "w", encoding="utf-8") as f:
        for c in shortlist_candidates:
            f.write(json.dumps(c) + "\n")

    print(f"Done. {ok} records processed, {skipped} skipped.")
    print(f"  → {OUT_DIR}/ ({ok} JSON files)")
    print(f"  → {SHORTLIST_OUT} ({ok} lines)")
    print()
    print("Now run:  make render-matrix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
