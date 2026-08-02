import os
import glob
import json
import sys

def check_regression():
    watchlist_dir = "output/watchlist/normalized"
    if not os.path.exists(watchlist_dir):
        print(f"Directory {watchlist_dir} not found. No regression check possible.")
        return

    files = glob.glob(f"{watchlist_dir}/watchlist-normalized-*.json")
    files.sort(key=os.path.getmtime, reverse=True)

    if len(files) < 2:
        print("Not enough normalized watchlist files to perform a regression check.")
        return

    recent_files = files[:3]
    recent_files.reverse() # Oldest to newest among the recent ones

    print(f"Comparing {len(recent_files)} recent watchlist files:")
    for f in recent_files:
        print(f" - {f}")

    history = {} # url -> list of (file_index, data)

    for idx, filepath in enumerate(recent_files):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for item in data:
                    url = item.get("url") or item.get("id")
                    if not url: continue
                    if url not in history:
                        history[url] = []
                    history[url].append((idx, item))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    print("\n--- Regression Report ---")
    flips_found = False

    for url, records in history.items():
        if len(records) < 2:
            continue
        
        # Compare consecutive records
        for i in range(len(records) - 1):
            idx1, item1 = records[i]
            idx2, item2 = records[i+1]

            decision1 = item1.get("decision", item1.get("recommended_action", "UNKNOWN"))
            decision2 = item2.get("decision", item2.get("recommended_action", "UNKNOWN"))

            score1 = item1.get("score_0_100", item1.get("score", 0))
            score2 = item2.get("score_0_100", item2.get("score", 0))

            if decision1 != decision2:
                print(f"[FLIP] {url}")
                print(f"  Decision changed: {decision1} -> {decision2}")
                flips_found = True
            
            if isinstance(score1, (int, float)) and isinstance(score2, (int, float)):
                if abs(score1 - score2) > 10:
                    print(f"[SWING] {url}")
                    print(f"  Score changed: {score1} -> {score2}")
                    flips_found = True

    if not flips_found:
        print("No decision flips or large score swings detected.")

if __name__ == "__main__":
    check_regression()
