"""Claude Code Audit Runner.

Executes the claude_code_audit prompt against a Stage 2 Analysis JSON payload
and its corresponding Decision object using the Anthropic API (or Gemini API as fallback).
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def run_claude_audit(analysis_payload: dict, decision_payload: dict, model: str = "claude-3-5-sonnet-20241022") -> str:
    """Run the code audit against the analysis and decision payloads."""
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "claude_code_audit.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    input_text = (
        "Here is the Stage 2 Analysis Output (including full_listing_text):\n"
        f"{json.dumps(analysis_payload, indent=2)}\n\n"
        "Here is the Decision Output:\n"
        f"{json.dumps(decision_payload, indent=2)}\n\n"
        "Please provide the audit report."
    )

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        from anthropic import Anthropic
        client = Anthropic(api_key=anthropic_key)
        message = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": input_text}
            ]
        )
        return message.content[0].text
    else:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("Neither ANTHROPIC_API_KEY nor GEMINI_API_KEY is set. Check your .env file.")
            
        print("ANTHROPIC_API_KEY not found. Falling back to Gemini API (gemini-3.1-pro)...")
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-3.1-pro",
            contents=[
                types.Content(role="user", parts=[
                    types.Part.from_text(text=f"{system_prompt}\n\n{input_text}")
                ])
            ]
        )
        return response.text

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m laptopfinder.runners.claude_audit <path_to_analysis_json> <path_to_decision_json>")
        sys.exit(1)
        
    analysis_path = sys.argv[1]
    decision_path = sys.argv[2]
    
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)
        
    with open(decision_path, "r", encoding="utf-8") as f:
        decision = json.load(f)
        
    print("Running Claude Code Audit...")
    try:
        report = run_claude_audit(analysis, decision)
        print("\n--- OUTPUT ---\n")
        print(report)
    except Exception as e:
        print(f"Error: {e}")
