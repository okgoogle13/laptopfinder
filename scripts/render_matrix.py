"""Render a JSONL shortlist into a sorted Markdown purchase-decision table."""
import argparse
import datetime
import json
import os
import sys


def load_candidates(path: str) -> list[dict]:
    """Read JSONL file at path. Parse each line as JSON.
    Skip malformed lines with a WARN to stderr.
    Return list of successfully parsed dicts."""
    results = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARN: skipping malformed line {i}: {e}", file=sys.stderr)
    return results


def sort_candidates(candidates: list[dict]) -> list[dict]:
    """Sort by action priority group: SHORTLIST=0, MONITOR=1, SKIP=2, unknown=3.
    Within each group, sort descending by llm_index_score.
    Treat missing or null llm_index_score as -1 (sorts last in group).
    Does not mutate the input list."""
    priority = {"SHORTLIST": 0, "MONITOR": 1, "SKIP": 2}

    def sort_key(c):
        group = priority.get(c.get("recommended_action"), 3)
        v = c.get("llm_index_score")
        score = -(v if v is not None else -1)
        return (group, score)

    return sorted(candidates, key=sort_key)


def render_table(candidates: list[dict]) -> str:
    """Return a Markdown table string for the given candidates.
    Columns: Rank, Action, Score, Title, GPU, Price, Notes.
    All cell values have | escaped as \\| and newlines stripped.
    Missing keys render as — (em dash, not hyphen)."""

    def cell(v) -> str:
        if v is None:
            return "—"
        return str(v).replace("\n", " ").replace("|", r"\|")

    header = "| Rank | Action | Score | Title | GPU | Price | Notes |"
    separator = "|------|--------|-------|-------|-----|-------|-------|"
    rows = [header, separator]

    for rank, c in enumerate(candidates, 1):
        rows.append(
            f"| {rank}"
            f" | {cell(c.get('recommended_action'))}"
            f" | {cell(c.get('llm_index_score'))}"
            f" | {cell(c.get('listing_title'))}"
            f" | {cell(c.get('gpu'))}"
            f" | {cell(c.get('price'))}"
            f" | {cell(c.get('notes'))} |"
        )

    return "\n".join(rows)


def main() -> None:
    """CLI entry point.
    Flags: --in (default: data/shortlist_candidates.jsonl), --out (default: data/purchase_matrix.md).
    Loads candidates, sorts, renders table, prepends a heading with ISO timestamp, writes to --out.
    Prints confirmation line to stdout."""
    parser = argparse.ArgumentParser(description="Render JSONL shortlist to Markdown matrix")
    parser.add_argument("--in", dest="input", default="data/shortlist_candidates.jsonl")
    parser.add_argument("--out", default="data/purchase_matrix.md")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    candidates = load_candidates(args.input)
    candidates = sort_candidates(candidates)
    table = render_table(candidates)

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    content = f"# Purchase Decision Matrix\n\nGenerated: {timestamp}\n\n{table}\n"

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"Matrix written to {args.out} ({len(candidates)} entries)")


if __name__ == "__main__":
    main()
