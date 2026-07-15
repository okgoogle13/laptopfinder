"""Batch CSV Ingestion Workflow for the laptopfinder pipeline.

Reads cleaned eBay CSV, extracts hardware specs using Gemini API,
validates output against a strict schema, runs the decision engine,
and appends/writes results for the downstream rendering matrix.
"""
import sys
import os
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
import jsonschema

# Ensure src/ directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from laptopfinder.decide import decide

load_dotenv()

def clean_price(price_raw: str | None) -> float | None:
    """Clean price string like '(AU $7,324.68)' or 'AU $1,900.00*' into float."""
    if not price_raw or not isinstance(price_raw, str):
        return None
    # Strip whitespace
    price_raw = price_raw.strip()
    if price_raw.lower() in ("item not available", "not available", ""):
        return None
    # Match digits, commas, and decimal points after a dollar sign
    m = re.search(r'\$\s*([0-9,]+(?:\.[0-9]+)?)', price_raw)
    if m:
        val_str = m.group(1).replace(",", "")
        try:
            val = float(val_str)
            return val if val >= 200 else None
        except ValueError:
            return None
    return None

def parse_vram_gb(vram_str: str | int | None) -> int | None:
    """Helper to extract an integer value of VRAM from a string or number."""
    if vram_str is None:
        return None
    if isinstance(vram_str, int):
        return vram_str
    if isinstance(vram_str, float):
        return int(vram_str)
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", str(vram_str), re.IGNORECASE)
    return int(float(m.group(1))) if m else None

def parse_ram_gb(ram_str: str | int | None) -> int | None:
    """Helper to extract an integer value of RAM from a string or number."""
    if ram_str is None:
        return None
    if isinstance(ram_str, int):
        return ram_str
    if isinstance(ram_str, float):
        return int(ram_str)
    m = re.search(r"(\d+(?:\.\d+)?)\s*GB", str(ram_str), re.IGNORECASE)
    return int(float(m.group(1))) if m else None

def main(csv_path: Path | str | None = None) -> int:
    if csv_path is None:
        csv_path = Path("data/fixtures/ebay_cleaned.csv")
    else:
        csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"ERROR: Input CSV not found at {csv_path}", file=sys.stderr)
        return 1

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set. Check your .env file.", file=sys.stderr)
        return 1

    # Load full schema for validation
    schema_path = Path(__file__).resolve().parent / "schemas" / "ebay_hardware_listing.schema.json"
    if not schema_path.exists():
        print(f"ERROR: Schema not found at {schema_path}", file=sys.stderr)
        return 1
    with open(schema_path, "r", encoding="utf-8") as f:
        full_schema = json.load(f)

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Ensure output directories exist
    processed_dir = Path("data/processed_candidates")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Simple flat schema for LLM response, avoiding type lists
    llm_schema = {
        "type": "OBJECT",
        "properties": {
            "gpu_name": {"type": "STRING", "description": "The GPU model name. Return empty string if not found."},
            "vram_capacity": {"type": "INTEGER", "description": "VRAM capacity in gigabytes. Return 0 if not found."},
            "cpu_name": {"type": "STRING", "description": "The CPU model name. Return empty string if not found."},
            "total_system_ram": {"type": "INTEGER", "description": "Total system RAM in gigabytes. Return 0 if not found."},
            "storage": {"type": "STRING", "description": "Storage capacity (e.g., '1TB'). Return empty string if not found."},
            "egpu_model": {"type": "STRING", "description": "The eGPU model name. Return empty string if not found."},
            "touchscreen_digitizer": {"type": "BOOLEAN", "description": "Whether a touchscreen is mentioned. Return false if not found."},
            "exact_model_name": {"type": "STRING", "description": "The exact laptop model name. Return empty string if not found."}
        },
        "required": [
            "gpu_name",
            "vram_capacity",
            "cpu_name",
            "total_system_ram",
            "storage",
            "egpu_model",
            "touchscreen_digitizer",
            "exact_model_name"
        ]
    }

    shortlist_candidates = []

    REQUIRED_HEADERS = {"listing_id", "title", "price_raw", "condition", "seller_name", "url"}

    print(f"Reading CSV file: {csv_path}")
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if fieldnames is None:
        raise ValueError("CSV file is empty or has no header row.")

    actual_headers = set(fieldnames)
    missing_headers = REQUIRED_HEADERS - actual_headers
    if missing_headers:
        raise ValueError(f"CSV is missing required columns: {sorted(missing_headers)}")

    print(f"Total rows to process: {len(rows)}")

    for idx, row in enumerate(rows, 1):
        listing_id = row.get("listing_id")
        platform = row.get("platform", "EBAY_AU")
        title = row.get("title")
        price_raw = row.get("price_raw")
        condition = row.get("condition")
        seller_name = row.get("seller_name")
        url = row.get("url")

        if not listing_id or not title:
            print(f"[{idx}/{len(rows)}] Skipping row due to missing listing_id or title")
            continue

        print(f"[{idx}/{len(rows)}] Processing: {title[:50]}... ({listing_id})")

        price_cleaned = clean_price(price_raw)

        # AI Enrichment
        prompt = f"""
You are a precise hardware information extraction tool.
Given a laptop listing from eBay, you must extract hardware specifications strictly from the listing title.

Listing Details:
- Title: {title}
- Condition: {condition}
- Seller: {seller_name}

Your task:
Extract the following fields from the listing Title:
1. `gpu_name`: The GPU model name (e.g. "RTX 4090", "RTX A4500", "Quadro RTX 5000", "Apple M3 Max"). Return empty string if not found in the title.
2. `vram_capacity`: The VRAM capacity as an integer in gigabytes (e.g. 16, 8). Return 0 if not found in the title.
3. `cpu_name`: The CPU model name (e.g. "Ultra 9 275HX", "i9 11900K"). Return empty string if not found in the title.
4. `total_system_ram`: The system RAM capacity as an integer in gigabytes (e.g. 64, 32). Return 0 if not found in the title.
5. `storage`: The storage capacity (e.g. "4TB", "1TB"). Return empty string if not found in the title.
6. `egpu_model`: If there is an external GPU enclosure mentioned in the title, extract its name. Return empty string if not found.
7. `touchscreen_digitizer`: Boolean indicating if a touchscreen or digitizer is explicitly mentioned in the title. Return false if not found.
8. `exact_model_name`: The exact model name of the laptop chassis (e.g. "Titan 18 HX", "Precision 7670"). Return empty string if not found.

Strict Constraints:
- Extract ONLY from the Title. Do NOT use the Condition or Seller Name to assume or fabricate specifications.
- If a specification is not explicitly mentioned in the title, you must return the default fallback ("" for strings, 0 for integers, false for booleans). Never assume or default.
- Return a JSON object matching the schema.
"""

        max_retries = 5
        base_delay = 5.0
        extracted = None

        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=llm_schema,
                        temperature=0.1
                    )
                )
                extracted = json.loads(response.text)
                # Success: introduce a small delay between requests to avoid rate limits
                time.sleep(1.0)
                break
            except Exception as e:
                err_msg = str(e)
                if attempt == max_retries:
                    print(f"ERROR: Max retries exceeded calling Gemini API for row {idx}: {e}", file=sys.stderr)
                    extracted = {
                        "gpu_name": "",
                        "vram_capacity": 0,
                        "cpu_name": "",
                        "total_system_ram": 0,
                        "storage": "",
                        "egpu_model": "",
                        "touchscreen_digitizer": False,
                        "exact_model_name": ""
                    }
                    break

                if "429" in err_msg or "503" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "UNAVAILABLE" in err_msg:
                    delay = base_delay * (2 ** (attempt - 1))
                    # Parse suggested retryDelay if present
                    m_delay = re.search(r'retry\s+in\s+(\d+(?:\.\d+)?)s', err_msg, re.IGNORECASE)
                    if m_delay:
                        delay = float(m_delay.group(1)) + 1.0
                    print(f"Rate limited or unavailable (attempt {attempt}/{max_retries}). Sleeping for {delay:.1f}s before retry...")
                    time.sleep(delay)
                else:
                    print(f"ERROR calling Gemini API for row {idx} (attempt {attempt}/{max_retries}): {e}", file=sys.stderr)
                    time.sleep(2.0)

        # Convert fallback sentinels back to None for the schema
        raw_gpu = extracted.get("gpu_name")
        raw_vram = extracted.get("vram_capacity")
        raw_cpu = extracted.get("cpu_name")
        raw_ram = extracted.get("total_system_ram")
        raw_storage = extracted.get("storage")
        raw_egpu = extracted.get("egpu_model")
        raw_touch = extracted.get("touchscreen_digitizer")
        raw_model = extracted.get("exact_model_name")

        gpu_name = raw_gpu if raw_gpu != "" else None
        vram_capacity = raw_vram if raw_vram != 0 else None
        cpu_name = raw_cpu if raw_cpu != "" else None
        total_system_ram = raw_ram if raw_ram != 0 else None
        storage = raw_storage if raw_storage != "" else None
        egpu_model = raw_egpu if raw_egpu != "" else None
        touchscreen_digitizer = raw_touch if raw_touch is not None else None
        exact_model_name = raw_model if raw_model != "" else None

        # Double check parsing values
        vram_val = parse_vram_gb(vram_capacity)
        ram_val = parse_ram_gb(total_system_ram)

        # Merge baseline with LLM output matching target schema requirements
        candidate = {
            "platform": platform,
            "listing_id": listing_id,
            "url": url if url else "",
            "title": title,
            "price_aud": price_cleaned,
            "seller_name": seller_name if seller_name else None,
            "seller_rating": None,
            "condition_code": None,
            "condition_label": condition if condition else None,
            "shipping_type": None,
            "pickup_location_text": None,
            "category_path": "Computers/Tablets & Networking > Laptops & Netbooks",
            "full_listing_text": title,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "gpu_name": gpu_name,
            "vram_capacity": vram_val,
            "cpu_name": cpu_name,
            "total_system_ram": ram_val,
            "storage": storage,
            "egpu_model": egpu_model,
            "touchscreen_digitizer": touchscreen_digitizer,
            "exact_model_name": exact_model_name
        }

        # Validate against schema
        try:
            jsonschema.validate(candidate, full_schema)
        except jsonschema.ValidationError as e:
            print(f"Validation failed for candidate {listing_id}: {e.message}", file=sys.stderr)
            continue

        # Save individual candidate
        safe_listing_id = listing_id.replace(":", "_")
        candidate_file = processed_dir / f"csv_import_{safe_listing_id}.json"
        with open(candidate_file, "w", encoding="utf-8") as out_f:
            json.dump(candidate, out_f, indent=2)

        # Run decision engine
        vram_parsed = None
        if vram_val is not None:
            vram_parsed = {
                "semantic_value": float(vram_val),
                "verbatim_quote": f"{vram_val}GB"
            }

        # Construct Stage 2 Analysis schema payload
        analysis_payload = {
            "metadata": {
                "source_platform": platform,
                "listing_url_or_identifier": url,
                "listing_title": title,
                "listing_price_aud": price_cleaned,
                "seller_name_or_identifier": seller_name,
                "seller_rating_or_profile_signal": None
            },
            "extracted_data": {
                "exact_model_name": exact_model_name,
                "component_category": "SYSTEM",
                "cpu": cpu_name,
                "gpu": gpu_name,
                "ram": f"{ram_val}GB" if ram_val else None,
                "storage": storage,
                "vram_capacity": vram_parsed,
                "stated_condition": condition,
                "shipping_or_pickup_signal": "UNKNOWN",
                "missing_information": {
                    "gpu": gpu_name is None,
                    "vram": vram_val is None,
                    "cpu": cpu_name is None,
                    "ram": ram_val is None,
                    "storage": storage is None,
                    "condition": condition is None
                },
                "total_system_ram": f"{ram_val}GB" if ram_val else None,
                "egpu_model": egpu_model,
                "touchscreen_digitizer": "touchscreen" if touchscreen_digitizer else None
            },
            "analysis": {
                "risk_score": 1.0,
                "risk_flags": [],
                "stated_pickup_location": None,
                "confidence": 0.8,
                "seller_classification": "PRIVATE_ESTABLISHED"
            }
        }

        try:
            decision = decide(analysis_payload)
            # Map decision output to render_matrix input format
            shortlist_candidates.append({
                "recommended_action": decision["recommended_action"],
                "llm_index_score": decision["llm_index_score"],
                "listing_title": title,
                "gpu": gpu_name if gpu_name else "—",
                "price": f"AU ${price_cleaned:.2f}" if price_cleaned is not None else "—",
                "notes": "; ".join(decision["reasons"]),
                "price_aud": price_cleaned,
                "vram_gb": float(vram_val) if vram_val is not None else None,
                "system_ram_gb": float(ram_val) if ram_val else None,
                "has_touchscreen": bool(touchscreen_digitizer),
            })
        except Exception as e:
            print(f"ERROR executing decision engine for listing {listing_id}: {e}", file=sys.stderr)

    # Write all candidates to data/shortlist_candidates.jsonl
    shortlist_file = Path("data/shortlist_candidates.jsonl")
    shortlist_file.parent.mkdir(parents=True, exist_ok=True)
    with open(shortlist_file, "w", encoding="utf-8") as out_f:
        for c in shortlist_candidates:
            out_f.write(json.dumps(c) + "\n")

    print(f"Batch ingestion complete. Wrote {len(shortlist_candidates)} records to {shortlist_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
