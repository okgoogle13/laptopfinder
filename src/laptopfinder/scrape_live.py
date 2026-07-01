"""Fetch listing URLs via Firecrawl and write per-listing text files."""
import argparse
import os
import re
import sys
from urllib.parse import urlsplit

from firecrawl import Firecrawl

_NAV = re.compile(
    r'^\s*(?:breadcrumb|watchlist|sign in|cookie notice).*$|^\s*cart\s*$',
    re.IGNORECASE | re.MULTILINE,
)
_BOLD = re.compile(r'\*\*(.+?)\*\*')
_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')


def read_urls(path: str) -> list[str]:
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def strip_nav(md: str) -> str:
    return _NAV.sub("", md)


def normalise_md(md: str) -> str:
    md = _BOLD.sub(r'\1', md)
    return _LINK.sub(r'\1', md)


def fetch_markdown(url: str, client) -> str | None:
    try:
        doc = client.scrape(url, formats=["markdown"], wait_for=3000)
        if doc.markdown is None:
            print(f"WARN: thin content for {url} (None)", file=sys.stderr)
            return None
        cleaned = normalise_md(strip_nav(doc.markdown))
        if len(cleaned) < 200:
            print(f"WARN: thin content for {url} ({len(cleaned)} chars)", file=sys.stderr)
            return None
        return cleaned
    except Exception as e:
        print(f"WARN: failed {url}: {e}", file=sys.stderr)
        return None


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls-file", default="data/urls.txt")
    parser.add_argument("--out-dir", default="data/feed_live/")
    args = parser.parse_args(argv)

    if "FIRECRAWL_API_KEY" not in os.environ:
        print("ERROR: FIRECRAWL_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    client = Firecrawl()
    for n, url in enumerate(read_urls(args.urls_file), 1):
        md = fetch_markdown(url, client)
        if md is None:
            continue
        clean_url = urlsplit(url)._replace(query="", fragment="").geturl()
        out = os.path.join(args.out_dir, f"listing-{n:03d}.txt")
        with open(out, "w") as fh:
            fh.write(f"<!-- {clean_url} -->\n{md}")


if __name__ == "__main__":
    main()
