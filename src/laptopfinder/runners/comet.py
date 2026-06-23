"""Comet Discovery Agent Runner (Stage 1).

Executes the comet_discovery_agent prompt against raw unstructured text 
using the Gemini API, producing a Stage 1 Discovery JSON array.
"""
import os
import json
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def run_comet_discovery(raw_text: str, model: str = "gemini-2.5-pro") -> list[dict]:
    """Run the Comet discovery agent over raw text to extract candidates."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")
        
    client = genai.Client(api_key=api_key)
    
    # Load prompt
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "comet_discovery_agent.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
        
    # Load schema
    schema_path = Path(__file__).parent.parent / "schemas" / "stage1.discovery.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    # The new google-genai SDK takes dict schema, but doesn't like $schema and title in the strict validation sometimes, 
    # so we can pass it as a JSON payload request if we want, or rely on system instruction.
    # We will pass response_mime_type and rely on the robust prompt + system instruction.
    # Alternatively we can supply response_schema.
    
    # Clean up the schema dictionary for the API if needed
    schema.pop("$schema", None)
    schema.pop("title", None)

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(role="user", parts=[
                types.Part.from_text(f"{system_prompt}\n\nRAW TEXT TO PROCESS:\n{raw_text}")
            ])
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1
        )
    )
    
    content = response.text
    return json.loads(content)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m laptopfinder.runners.comet <path_to_raw_text>")
        sys.exit(1)
        
    text_path = sys.argv[1]
    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    print(f"Running Comet Discovery on {text_path}...")
    try:
        results = run_comet_discovery(text)
        print("\n--- OUTPUT ---\n")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")
