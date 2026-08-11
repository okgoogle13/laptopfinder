"""Generates personal shopper reports from Stage 2 analysis JSONL.

Produces specific rankings for UK/AU purchase scenarios:
- shortlist_top15.json
- uk_opportunities.json
- manual_review_queue.json
- source_coverage_report.json
- shortlist_report.md
"""

import json
from pathlib import Path
from typing import Any
import sys

from laptopfinder.decide import decide, load_ref

OUTPUT_DIR = Path("output")


def load_candidates(path: Path) -> list[dict[str, Any]]:
    candidates = []
    if not path.exists():
        return candidates
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            candidates.append(json.loads(line))
    return candidates


def safe_get_landed_cost(candidate: dict, scenario_name: str) -> float:
    scenarios = candidate.get("decision", {}).get("landed_cost_scenarios", [])
    for s in scenarios:
        if s["scenario_name"] == scenario_name:
            return s.get("total_landed_cost_aud", float("inf"))
    return float("inf")


def generate_reports(input_path: Path):
    ref = load_ref()
    candidates = load_candidates(input_path)
    
    processed = []
    manual_review_queue = []
    
    # Process decisions
    for c in candidates:
        if "analysis" not in c or "extracted_data" not in c:
            continue
            
        decision = decide(c, ref)
        c["decision"] = decision
        
        # Check for manual review condition (missing fields)
        mi = c.get("extracted_data", {}).get("missing_information", {})
        n_missing = sum(mi.values()) if isinstance(mi, dict) else len(mi)
        
        if n_missing > 0:
            manual_review_queue.append(c)
        else:
            processed.append(c)
            
    # Filter only shortlisted items (or UMA platform / target overrides)
    shortlisted = [c for c in processed if c["decision"].get("recommended_action") == "SHORTLIST"]
    
    # Ranking 1: Top 15 overall (by llm_index_score, then lowest hand-carry cost or local cost)
    shortlisted.sort(
        key=lambda x: (
            -x["decision"].get("llm_index_score", 0), 
            min(
                safe_get_landed_cost(x, "UK purchase hand-carried to Australia"),
                safe_get_landed_cost(x, "Australian purchase")
            )
        )
    )
    top_15 = shortlisted[:15]
    
    # Ranking 2: UK Opportunities
    # Listings where hand-carry is cheaper than AU local, or item is UK only
    uk_opps = []
    for c in shortlisted:
        country = c.get("metadata", {}).get("item_location_country", "AU")
        if country == "UK":
            uk_opps.append(c)
            
    uk_opps.sort(key=lambda x: safe_get_landed_cost(x, "UK purchase hand-carried to Australia"))
    
    # Report coverage
    platforms = {}
    for c in candidates:
        plat = c.get("metadata", {}).get("source_platform", "UNKNOWN")
        platforms[plat] = platforms.get(plat, 0) + 1
        
    coverage = {
        "total_analyzed": len(candidates),
        "total_shortlisted": len(shortlisted),
        "platforms": platforms
    }
    
    # Write JSONs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "shortlist_top15.json").open("w", encoding="utf-8") as f:
        json.dump(top_15, f, indent=2)
        
    with (OUTPUT_DIR / "uk_opportunities.json").open("w", encoding="utf-8") as f:
        json.dump(uk_opps, f, indent=2)
        
    with (OUTPUT_DIR / "manual_review_queue.json").open("w", encoding="utf-8") as f:
        json.dump(manual_review_queue, f, indent=2)
        
    with (OUTPUT_DIR / "source_coverage_report.json").open("w", encoding="utf-8") as f:
        json.dump(coverage, f, indent=2)
        
    # Write Markdown Report
    with (OUTPUT_DIR / "shortlist_report.md").open("w", encoding="utf-8") as f:
        f.write("# Laptop Personal Shopper: UK/AU Report\n\n")
        
        f.write("## Top 15 Overall Value\n")
        for i, c in enumerate(top_15, 1):
            title = c.get("metadata", {}).get("listing_title", "Unknown")
            url = c.get("metadata", {}).get("listing_url_or_identifier", "#")
            score = c["decision"].get("score_0_100", 0)
            f.write(f"{i}. [{title}]({url}) - Score: **{score}**\n")
            
        f.write("\n## UK-Only Opportunities (Hand-Carry)\n")
        for c in uk_opps:
            title = c.get("metadata", {}).get("listing_title", "Unknown")
            cost = safe_get_landed_cost(c, "UK purchase hand-carried to Australia")
            f.write(f"- {title} (Estimated AUD {cost:.2f} Hand-Carried)\n")
            
    print(f"Generated reports in {OUTPUT_DIR}/")


if __name__ == "__main__":
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/shortlist_candidates.jsonl")
    generate_reports(input_file)
