"""Perplexity Deep Research Runner.

Executes the deep hardware research prompt using the Perplexity API (via openai SDK).
"""
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def run_deep_research(model: str = "sonar-pro") -> str:
    """Run the deep research prompt against the Perplexity API."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY is not set. Check your .env file.")
        
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "perplexity_deep_research.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # We send the instructions as the system prompt and a short trigger as user.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Execute the deep research pass and return the required output format exactly."}
        ]
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
