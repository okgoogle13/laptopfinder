"""Generate a single batch AI Studio prompt from ebay_cleaned.csv.

Reads the CSV and outputs a single prompt to:
  data/ai_studio_prompts/ebay_csv_extraction.txt

Paste that file's content into aistudio.google.com or gemini.google.com,
set the output to JSON, then save the JSON response to:
  data/ai_studio_responses/ebay_csv_extraction.json

After saving the response, run:
  .venv/bin/python scripts/parse_ai_studio_extraction.py
"""
import csv
import json
from pathlib import Path

csv_path = Path("data/fixtures/ebay_cleaned.csv")
srl_path = Path("config/static_reference_layer.json")
out_dir = Path("data/ai_studio_prompts")
out_dir.mkdir(parents=True, exist_ok=True)

with open(csv_path, mode="r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

with open(srl_path, encoding="utf-8") as f:
    srl = json.load(f)

# Build a compact input list: just the fields we need
inputs = []
for row in rows:
    inputs.append({
        "listing_id": row.get("listing_id"),
        "title": row.get("title"),
    })

# Build GPU reference tables from SRL
target_gpus = srl.get("target_gpus", {})
gpu_names = sorted(target_gpus.keys())
gpu_vram_lines = []
for name in gpu_names:
    vram = target_gpus[name].get("vram_gb", "?")
    gpu_vram_lines.append(f"  {name}: {vram}GB")
gpu_vram_table = "\n".join(gpu_vram_lines)
gpu_name_list = ", ".join(gpu_names)

# Also include watch_list GPUs and other known GPUs from gpu_generation_by_name
gen_map = srl.get("llm_index_score", {}).get("gpu_generation_by_name", {})
all_known_gpu_names = sorted(set(list(target_gpus.keys()) + list(gen_map.keys())))
all_gpu_list = ", ".join(all_known_gpu_names)

system_instructions = f"""You are a precise hardware information extraction tool.
Given a list of eBay laptop listing titles, extract hardware specifications from each title.

## Extraction Fields
For each listing, extract these fields from the title:
- `gpu_name` (string): The GPU model name, normalised per the rules below.
- `vram_capacity` (integer): VRAM in GB. If not stated in the title, use the Known VRAM Table below. Return 0 only if the GPU is unknown AND VRAM is not stated.
- `cpu_name` (string): CPU model, e.g. "Ultra 9 275HX", "i9-13980HX". Empty string if absent.
- `total_system_ram` (integer): System RAM in GB as a whole number. Return 0 if absent.
- `storage` (string): Storage spec, e.g. "1TB", "2TB SSD". Empty string if absent.
- `egpu_model` (string): eGPU enclosure name if mentioned, e.g. "Razer Core X". Empty string if absent.
- `touchscreen_digitizer` (boolean): true if title mentions "Touch", "Touchscreen", or "Digitizer". false otherwise.
- `exact_model_name` (string): Exact laptop chassis model, e.g. "Precision 7670", "ROG Strix Scar 18". Empty string if absent.

## GPU Name Normalisation Rules
When extracting `gpu_name`, apply these normalisation rules:
1. Strip prefixes: Remove "GeForce", "NVIDIA", "Mobile" from the GPU name.
2. Insert spaces: "RTX5080" → "RTX 5080", "RTX4090" → "RTX 4090", "RTX5070TI" → "RTX 5070 Ti"
3. Fix casing: "3080ti" → "RTX 3080 Ti", "rtx 4090" → "RTX 4090"
4. Bare numbers: If title says just "5090" in a GPU context, output "RTX 5090"
5. Keep dashes/hyphens as spaces: "RTX-3070Ti" → "RTX 3070 Ti"
6. Preserve workstation prefixes: "Quadro RTX 5000" stays as-is, "RTX A4500" stays as-is
7. Match against the canonical list below when possible.

## Canonical GPU Names (use these exact strings)
{gpu_name_list}

All known GPU names (including non-target): {all_gpu_list}

## Known VRAM by GPU
When VRAM is not explicitly stated in the title, use this lookup table:
{gpu_vram_table}

If the GPU name matches one of the above (after normalisation), return the known VRAM value.
If the GPU is NOT in this table and VRAM is not stated, return 0.

## Other Rules
- Do NOT conflate system RAM and VRAM. "32GB" without "VRAM"/"GDDR" context is system RAM.
- "Touch" or "4K Touch" in a title means `touchscreen_digitizer: true`.
- For `exact_model_name`, extract the laptop chassis name (e.g. "Predator Helios 18", "ROG Strix Scar 16"), not the GPU or CPU.
"""

task_prompt = f"""Extract hardware specs from these {len(inputs)} eBay laptop listings.

## Input Listings
{json.dumps(inputs, indent=2)}
"""

system_out_path = out_dir / "ebay_csv_extraction_system.txt"
task_out_path = out_dir / "ebay_csv_extraction_task.txt"

system_out_path.write_text(system_instructions, encoding="utf-8")
task_out_path.write_text(task_prompt, encoding="utf-8")


# Generate the JSON Schema for AI Studio's "Structured Output" feature
schema = {
    "type": "array",
    "description": "An array of extracted hardware specifications from laptop listings.",
    "items": {
        "type": "object",
        "properties": {
            "listing_id": {"type": "string", "description": "The listing_id provided in the input."},
            "gpu_name": {"type": "string", "description": "GPU model name. Empty string if absent."},
            "vram_capacity": {"type": "integer", "description": "VRAM in GB as a whole number. Return 0 if absent."},
            "cpu_name": {"type": "string", "description": "CPU model. Empty string if absent."},
            "total_system_ram": {"type": "integer", "description": "System RAM in GB as a whole number. Return 0 if absent."},
            "storage": {"type": "string", "description": "Storage spec. Empty string if absent."},
            "egpu_model": {"type": "string", "description": "eGPU enclosure name if mentioned. Empty string if absent."},
            "touchscreen_digitizer": {"type": "boolean", "description": "true if title explicitly mentions touchscreen or digitizer."},
            "exact_model_name": {"type": "string", "description": "Exact laptop chassis model. Empty string if absent."}
        },
        "required": [
            "listing_id",
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
}

schema_path = out_dir / "ebay_csv_extraction_schema.json"
with open(schema_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)


print(f"System instructions: {system_out_path}")
print(f"Task prompt: {task_out_path}")
print(f"Schema written to: {schema_path}")
print(f"Listings included: {len(inputs)}")
print()
print("Next steps:")
print("  1. Open https://aistudio.google.com/prompts/new_chat")
print("  2. Paste the contents of ebay_csv_extraction_system.txt into the 'System Instructions' box")
print("  3. Paste the contents of ebay_csv_extraction_task.txt into the main 'Type something' chat box")
print("  4. Set Output format → JSON (in the right panel)")
print("  5. Select 'Supply Schema' and paste the contents of ebay_csv_extraction_schema.json")
print("  6. Click 'Run'")
print("  7. Copy the JSON array response and save to:")
print("       data/ai_studio_responses/ebay_csv_extraction.json")
print("  8. Then run:")
print("       .venv/bin/python scripts/parse_ai_studio_extraction.py")
