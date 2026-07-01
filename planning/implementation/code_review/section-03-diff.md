diff --git a/data/urls.txt b/data/urls.txt
new file mode 100644
index 0000000..c768573
--- /dev/null
+++ b/data/urls.txt
@@ -0,0 +1,6 @@
+# URLs to scrape for the live pipeline.
+# One URL per line. Blank lines and lines starting with # are ignored.
+# Run: make scrape-and-live
+#
+# https://www.ebay.com.au/itm/example-listing-1
+# https://www.ebay.com.au/itm/example-listing-2
diff --git a/src/laptopfinder/scrape_live.py b/src/laptopfinder/scrape_live.py
new file mode 100644
index 0000000..f98966c
--- /dev/null
+++ b/src/laptopfinder/scrape_live.py
@@ -0,0 +1,68 @@
+"""Fetch listing URLs via Firecrawl and write per-listing text files."""
+import argparse
+import os
+import re
+import sys
+from urllib.parse import urlsplit
+
+from firecrawl import Firecrawl
+
+_NAV = re.compile(
+    r'^\s*(?:breadcrumb|watchlist|sign in|cookie notice).*$|^\s*cart\s*$',
+    re.IGNORECASE | re.MULTILINE,
+)
+_BOLD = re.compile(r'\*\*(.+?)\*\*')
+_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')
+
+
+def read_urls(path: str) -> list[str]:
+    with open(path) as fh:
+        return [ln.rstrip() for ln in fh if ln.strip() and not ln.startswith("#")]
+
+
+def strip_nav(md: str) -> str:
+    return _NAV.sub("", md)
+
+
+def normalise_md(md: str) -> str:
+    md = _BOLD.sub(r'\1', md)
+    return _LINK.sub(r'\1', md)
+
+
+def fetch_markdown(url: str, client) -> str | None:
+    try:
+        doc = client.scrape(url, formats=["markdown"], wait_for=3000)
+        cleaned = normalise_md(strip_nav(doc.markdown))
+        if len(cleaned) < 200:
+            print(f"WARN: thin content for {url} ({len(cleaned)} chars)", file=sys.stderr)
+            return None
+        return cleaned
+    except Exception as e:
+        print(f"WARN: failed {url}: {e}", file=sys.stderr)
+        return None
+
+
+def main(argv=None) -> None:
+    parser = argparse.ArgumentParser()
+    parser.add_argument("--urls-file", default="data/urls.txt")
+    parser.add_argument("--out-dir", default="data/feed_live/")
+    args = parser.parse_args(argv)
+
+    if "FIRECRAWL_API_KEY" not in os.environ:
+        print("ERROR: FIRECRAWL_API_KEY not set", file=sys.stderr)
+        sys.exit(1)
+
+    os.makedirs(args.out_dir, exist_ok=True)
+    client = Firecrawl()
+    for n, url in enumerate(read_urls(args.urls_file), 1):
+        md = fetch_markdown(url, client)
+        if md is None:
+            continue
+        clean_url = urlsplit(url)._replace(query="", fragment="").geturl()
+        out = os.path.join(args.out_dir, f"listing-{n:03d}.txt")
+        with open(out, "w") as fh:
+            fh.write(f"<!-- {clean_url} -->\n{md}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/tests/test_scrape_live.py b/tests/test_scrape_live.py
new file mode 100644
index 0000000..e1dfe5e
--- /dev/null
+++ b/tests/test_scrape_live.py
@@ -0,0 +1,166 @@
+"""Tests for scrape_live — zero live HTTP calls, all Firecrawl mocked."""
+import sys
+import textwrap
+import types
+from io import StringIO
+from pathlib import Path
+from unittest.mock import MagicMock, patch
+
+import pytest
+
+from laptopfinder.scrape_live import fetch_markdown, main, normalise_md, read_urls, strip_nav
+
+
+# ── read_urls ──────────────────────────────────────────────────────────────
+
+def test_read_urls_excludes_blanks(tmp_path):
+    f = tmp_path / "urls.txt"
+    f.write_text("\nhttps://example.com\n\n")
+    assert read_urls(str(f)) == ["https://example.com"]
+
+
+def test_read_urls_excludes_comments(tmp_path):
+    f = tmp_path / "urls.txt"
+    f.write_text("# comment\nhttps://example.com\n")
+    assert read_urls(str(f)) == ["https://example.com"]
+
+
+def test_read_urls_preserves_order(tmp_path):
+    f = tmp_path / "urls.txt"
+    f.write_text("https://a.com\nhttps://b.com\nhttps://c.com\n")
+    assert read_urls(str(f)) == ["https://a.com", "https://b.com", "https://c.com"]
+
+
+def test_read_urls_all_blanks_and_comments(tmp_path):
+    f = tmp_path / "urls.txt"
+    f.write_text("# only comments\n\n# another\n")
+    assert read_urls(str(f)) == []
+
+
+# ── strip_nav ──────────────────────────────────────────────────────────────
+
+def test_strip_nav_removes_breadcrumb():
+    result = strip_nav("breadcrumb: Home > Laptops\nActual content here")
+    assert "breadcrumb" not in result
+    assert "Actual content here" in result
+
+
+def test_strip_nav_no_false_positive_cartridge():
+    line = "cartridge case details"
+    result = strip_nav(line)
+    assert "cartridge case details" in result
+
+
+def test_strip_nav_preserves_provenance_comment():
+    line = "<!-- https://ebay.com.au/itm/123 -->"
+    assert strip_nav(line) == line
+
+
+def test_strip_nav_preserves_unrelated_content():
+    line = "ASUS ROG Zephyrus G14, RTX 4070, 32GB RAM"
+    assert strip_nav(line) == line
+
+
+# ── normalise_md ───────────────────────────────────────────────────────────
+
+def test_normalise_md_strips_bold():
+    assert normalise_md("**bold**") == "bold"
+
+
+def test_normalise_md_strips_link():
+    assert normalise_md("[link text](https://example.com)") == "link text"
+
+
+def test_normalise_md_plain_text_unchanged():
+    plain = "ASUS ROG laptop 32GB RAM RTX 4090"
+    assert normalise_md(plain) == plain
+
+
+# ── fetch_markdown ─────────────────────────────────────────────────────────
+
+def _make_doc(content: str):
+    doc = MagicMock()
+    doc.markdown = content
+    return doc
+
+
+def test_fetch_markdown_returns_cleaned_string():
+    client = MagicMock()
+    client.scrape.return_value = _make_doc("A" * 250)
+    result = fetch_markdown("https://example.com", client)
+    assert result is not None
+    assert len(result) >= 200
+
+
+def test_fetch_markdown_thin_content_returns_none(capsys):
+    client = MagicMock()
+    client.scrape.return_value = _make_doc("short")
+    result = fetch_markdown("https://example.com", client)
+    assert result is None
+    assert "WARN" in capsys.readouterr().err
+
+
+def test_fetch_markdown_exception_returns_none(capsys):
+    client = MagicMock()
+    client.scrape.side_effect = Exception("network error")
+    result = fetch_markdown("https://example.com", client)
+    assert result is None
+    assert "WARN" in capsys.readouterr().err
+
+
+# ── main ───────────────────────────────────────────────────────────────────
+
+def test_main_missing_api_key_exits(tmp_path, capsys):
+    urls_file = tmp_path / "urls.txt"
+    urls_file.write_text("https://example.com\n")
+    with patch.dict("os.environ", {}, clear=True):
+        # Remove key if present
+        import os
+        os.environ.pop("FIRECRAWL_API_KEY", None)
+        with pytest.raises(SystemExit) as exc:
+            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])
+        assert exc.value.code == 1
+    assert "FIRECRAWL_API_KEY" in capsys.readouterr().err
+
+
+def test_main_first_fails_second_succeeds(tmp_path, capsys):
+    urls_file = tmp_path / "urls.txt"
+    urls_file.write_text("https://fail.com\nhttps://ok.com\n")
+
+    good_doc = _make_doc("B" * 300)
+
+    def mock_scrape(url, **kwargs):
+        if "fail" in url:
+            raise Exception("timeout")
+        return good_doc
+
+    mock_client = MagicMock()
+    mock_client.scrape.side_effect = mock_scrape
+
+    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
+        with patch("laptopfinder.scrape_live.Firecrawl", return_value=mock_client):
+            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])
+
+    written = list(tmp_path.glob("listing-*.txt"))
+    assert len(written) == 1
+    assert "WARN" in capsys.readouterr().err
+
+
+def test_main_output_file_has_url_prefix_without_query(tmp_path):
+    urls_file = tmp_path / "urls.txt"
+    urls_file.write_text("https://ebay.com.au/itm/123?mkcid=1&mkrid=705\n")
+
+    doc = _make_doc("C" * 300)
+    mock_client = MagicMock()
+    mock_client.scrape.return_value = doc
+
+    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
+        with patch("laptopfinder.scrape_live.Firecrawl", return_value=mock_client):
+            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])
+
+    files = list(tmp_path.glob("listing-*.txt"))
+    assert len(files) == 1
+    content = files[0].read_text()
+    assert content.startswith("<!-- ")
+    assert "?" not in content.split("\n")[0]
+    assert "&" not in content.split("\n")[0]
