"""Print SRL seller lists + corpus seller usernames for lf-seller-intel PWM workflow."""
import json

srl = json.load(open("config/static_reference_layer.json"))
print("clearance_sellers:", srl["clearance_sellers"])
print("watched_sellers:", srl["watched_sellers"])
seen = sorted(set(json.loads(l)["seller_username"] for l in open("data/ebay/corpus.jsonl")))
print("CORPUS SELLERS:", seen)
