"""Validate seller_patches.json for lf-seller-intel PWM workflow."""
import json, sys

p = json.load(open("data/pwm/lf-seller-intel/seller_patches.json"))
r = p.get("rationale_by_seller", {})
missing = [k for k, v in r.items() if not v.get("verified_ebay_au_url")]
if missing:
    print("[FAIL] missing verified_ebay_au_url:", missing)
    sys.exit(1)
print(f"[OK] {len(r)} sellers with verified URLs")
