"""AI Studio Runtime Runner (Stage 2).

Executes the ai_studio_runtime prompt against a handoff packet and full text 
using the Gemini API, producing a Stage 2 Analysis JSON object.
"""
import os
import json
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def run_stage2_analysis(handoff_packet: dict, full_listing_text: str, model: str = "gemini-3.1-pro") -> dict:
    """Run Stage 2 analysis on a single listing using AI Studio."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")
        
    client = genai.Client(api_key=api_key)
    
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "ai_studio_runtime.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
        
    schema_path = Path(__file__).parent.parent / "schemas" / "stage2.analysis.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    schema.pop("$schema", None)
    schema.pop("title", None)

    input_payload = {
        "handoff_packet": handoff_packet,
        "full_listing_text": full_listing_text
    }
    
    user_prompt = (
        "Execute MODE [STAGE 2: ANALYSIS] on the following input:\n\n"
        f"{json.dumps(input_payload, indent=2)}\n\n"
        "Return the strictly formatted Stage 2 JSON object."
    )

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_text(f"{system_prompt}\n\n{user_prompt}")
            ])
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1
        )
    )
    
    return json.loads(response.text)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m laptopfinder.runners.aistudio <path_to_handoff_json> <path_to_listing_text>")
        sys.exit(1)
        
    handoff_path = sys.argv[1]
    text_path = sys.argv[2]
    
    with open(handoff_path, "r", encoding="utf-8") as f:
        handoff = json.load(f)
        
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    print("Running AI Studio Stage 2 Analysis...")
    try:
        result = run_stage2_analysis(handoff, text)
        print("\n--- OUTPUT ---\n")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
