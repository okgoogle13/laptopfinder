"""Print current exclusion regex + 50 corpus titles for lf-exclusion-tune PWM workflow."""
import json

srl = json.load(open("config/static_reference_layer.json"))
print("CURRENT REGEX:", srl["data_integrity"]["exclusion_regex"])
print()
titles = [json.loads(l)["title"] for l in open("data/ebay/corpus.jsonl")][:50]
print("\n".join(titles))
