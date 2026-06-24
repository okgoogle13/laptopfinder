"""Perplexity Deep Research Runner.

Executes the deep hardware research prompt using the Perplexity API (via openai SDK).
"""
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def run_deep_research(model: str = None) -> str:
    """Run the deep research prompt against the Perplexity API or a local proxy."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    base_url = os.environ.get("PERPLEXITY_API_BASE", "https://api.perplexity.ai")
    
    is_local = "localhost" in base_url or "127.0.0.1" in base_url
    if not api_key:
        if is_local:
            api_key = "dummy-key-for-pwm"
        else:
            raise ValueError("PERPLEXITY_API_KEY is not set. Check your .env file.")
            
    # Resolve model: parameter overrides PERPLEXITY_MODEL env var, which overrides default "sonar-pro"
    if not model:
        model = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
        
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "perplexity_deep_research.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # If using local pwm, we combine system and user prompts to avoid prompt distillation/truncation in the proxy
    if is_local:
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\nExecute the deep research pass and return the required output format exactly."}
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Execute the deep research pass and return the required output format exactly."}
        ]

    # We send the instructions and trigger the runner.
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    
    content = response.choices[0].message.content
    return content

if __name__ == "__main__":
    print("Running Perplexity Deep Research...")
    try:
        output = run_deep_research()
        print("\n--- OUTPUT ---\n")
        print(output)
    except Exception as e:
        print(f"Error: {e}")
