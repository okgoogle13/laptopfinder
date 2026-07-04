"""Convert Chrome extension JSON/CSV exports (Instant Data Scraper, Web Scraper, etc.)
into clean pipeline-ready JSONL files and URL lists.

Supports both search results captures (e.g. ebay.csv) and shopping cart / multi-item
recommendation captures (e.g. cart.csv).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path


def _clean_url(url: str) -> str | None:
    """Extract canonical eBay AU item URL from a noisy capture link."""
    if not url or not isinstance(url, str):
        return None
    m = re.search(r'/itm/(\d+)', url)
    if m:
        return f"https://www.ebay.com.au/itm/{m.group(1)}"
    return None


def _extract_itm_id(url: str) -> str | None:
    """Extract numeric eBay item ID from URL string."""
    if not url or not isinstance(url, str):
        return None
    m = re.search(r'/itm/(\d+)', url)
    return m.group(1) if m else None


def _extract_seller_from_row(row: dict, suffix: str) -> str | None:
    """Attempt to extract seller username from row."""
    for sk in ["PSEUDOLINK" + suffix, "seller_name", "seller", "clipped"]:
        val = row.get(sk)
        if val and isinstance(val, str) and len(val.strip()) < 40 and "http" not in val:
            cleaned = val.strip()
            if not cleaned.startswith("Pay only") and not cleaned.startswith("Find similar"):
                return cleaned
    for vk in row.values():
        if vk and isinstance(vk, str) and "/usr/" in vk:
            sm = re.search(r'/usr/([^/?#&]+)', vk)
            if sm:
                return sm.group(1)
    return None


def parse_record_from_row(row: dict, default_platform: str = "EBAY_AU") -> list[dict]:
    """Parse one or more listing items from a single CSV/JSON export dict.

    Handles horizontal cart captures (where item-title and item-title 2 appear in one row)
    as well as standard search results rows.
    """
    results = []
    for k, v in row.items():
        if not k or not v or not isinstance(v, str):
            continue
        # Only look at columns that look like item titles
        if not any(t in k.lower() for t in ["title", "name"]):
            if k != "m-item-3-col__title--link":
                continue
        if any(x in k.lower() for x in ["href", "src", "url", "link", "seller", "rating", "price"]):
            if k != "m-item-3-col__title--link":
                continue
        if len(v.strip()) < 10 or "http" in v:
            continue

        # Suffix detection (e.g. 'item-title 2' -> ' 2')
        suffix = ""
        m = re.search(r'(\s+\d+)$', k)
        if m:
            suffix = m.group(1)

        # Look for corresponding URL column in the row
        url_candidates = [
            k + " href",
            "item-title href" + suffix if k.startswith("item-title") else None,
            "m-item-3-col__column--image href" + suffix,
            "default href" + suffix,
            "url" + suffix,
            "link" + suffix,
        ]
        raw_url = None
        for uc in url_candidates:
            if uc and row.get(uc) and "/itm/" in str(row.get(uc)):
                raw_url = row[uc]
                break
        if not raw_url:
            for rk, rv in row.items():
                if rv and isinstance(rv, str) and "/itm/" in rv:
                    raw_url = rv
                    break

        clean_url = _clean_url(raw_url) if raw_url else None
        if not clean_url:
            continue

        itm_id = _extract_itm_id(clean_url)
        if not itm_id:
            continue
        listing_id = f"{default_platform.lower()}:{itm_id}"

        # Price and condition detection
        price_raw = None
        cond = None

        # In horizontal cart captures, secondary items (e.g. item-title 2) are recommendations
        # without their own price/condition in that row. Do not inherit primary item spans.
        is_secondary_cart_item = k.startswith("item-title") and suffix != ""
        if not is_secondary_cart_item:
            for pk, pv in row.items():
                if pv and isinstance(pv, str) and "AU $" in pv and "http" not in pv:
                    price_raw = pv
                    break
            if not price_raw:
                for pk, pv in row.items():
                    if pv and isinstance(pv, str) and any(c in pv for c in ["US $", "GBP ", "EUR ", "$"]) and "http" not in pv and any(ch.isdigit() for ch in pv):
                        price_raw = pv
                        break
            if not price_raw and row.get("BOLD"):
                price_raw = str(row.get("BOLD"))

            cond_keywords = [
                "Used", "Refurbished", "Brand New", "Like New",
                "Opened", "Excellent -", "Good -", "Very Good -",
            ]
            for ck, cv in row.items():
                if cv and isinstance(cv, str) and len(cv.strip()) < 50 and any(w in cv for w in cond_keywords):
                    cond = cv.strip()
                    break

        seller_name = _extract_seller_from_row(row, suffix)

        # Construct full_listing_text stub
        stub_parts = [v.strip()]
        if price_raw:
            stub_parts.append(f"Price: {price_raw.strip()}")
        if cond:
            stub_parts.append(f"Condition: {cond}")
        full_text = "\n".join(stub_parts)

        results.append({
            "platform": default_platform,
            "listing_id": listing_id,
            "title": v.strip(),
            "price_raw": price_raw.strip() if price_raw else None,
            "url": clean_url,
            "seller_name": seller_name,
            "seller_rating": None,
            "full_listing_text": full_text,
            "_meta": {
                "condition": cond,
                "itm_id": itm_id,
            },
        })
    return results


def read_export_file(path: Path) -> list[dict]:
    """Read a JSON or CSV export file and extract clean raw records."""
    records = []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            # Maybe inside a key like 'items' or 'rows'
            for val in data.values():
                if isinstance(val, list):
                    data = val
                    break
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    records.extend(parse_record_from_row(item))
    else:
        with open(path, mode="r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                records.extend(parse_record_from_row(row))
    return records


def deduplicate_records(records: list[dict]) -> list[dict]:
    """Deduplicate records by listing_id, preferring records with more complete fields."""
    seen: dict[str, dict] = {}
    for r in records:
        lid = r["listing_id"]
        if lid not in seen:
            seen[lid] = r
        else:
            # Override if the existing one lacked price or condition
            old = seen[lid]
            if not old.get("price_raw") and r.get("price_raw"):
                seen[lid] = r
            elif not old.get("_meta", {}).get("condition") and r.get("_meta", {}).get("condition"):
                seen[lid] = r
    return list(seen.values())


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Convert Chrome extension exports to pipeline JSONL.")
    parser.add_argument("--in", "-i", dest="input_files", nargs="+", required=True, help="Input CSV or JSON files")
    parser.add_argument("--out", "-o", default="data/fixtures/ebay_export.jsonl", help="Output JSONL file path")
    parser.add_argument("--out-urls", "-u", help="Optional output text file for clean listing URLs (one per line)")
    parser.add_argument("--out-csv", "-c", help="Optional output CSV file for human review")
    args = parser.parse_args(argv)

    all_records = []
    for path_str in args.input_files:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: input file not found: {path}", file=sys.stderr)
            sys.exit(1)
        recs = read_export_file(path)
        print(f"[READ] {path.name}: extracted {len(recs)} raw records")
        all_records.extend(recs)

    cleaned = deduplicate_records(all_records)
    print(f"[CONVERT] {len(all_records)} records read ({len(cleaned)} unique after deduplication)")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, mode="w", encoding="utf-8") as fh:
        for r in cleaned:
            fh.write(json.dumps(r) + "\n")
    print(f"[CONVERT] {len(cleaned)} records written -> {out_path}")

    if args.out_urls:
        url_path = Path(args.out_urls)
        url_path.parent.mkdir(parents=True, exist_ok=True)
        urls = sorted(set(r["url"] for r in cleaned if r.get("url")))
        url_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
        print(f"[URLS] {len(urls)} canonical URLs written -> {url_path}")

    if args.out_csv:
        csv_path = Path(args.out_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["listing_id", "platform", "title", "price_raw", "condition", "seller_name", "url"]
        with open(csv_path, mode="w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in cleaned:
                writer.writerow({
                    "listing_id": r.get("listing_id"),
                    "platform": r.get("platform"),
                    "title": r.get("title"),
                    "price_raw": r.get("price_raw"),
                    "condition": r.get("_meta", {}).get("condition"),
                    "seller_name": r.get("seller_name"),
                    "url": r.get("url"),
                })
        print(f"[CSV] Cleaned spreadsheet written -> {csv_path}")


if __name__ == "__main__":
    main()
