"""Tests for scrape_live — zero live HTTP calls, all Firecrawl mocked."""
from unittest.mock import MagicMock, patch

import pytest

from laptopfinder.scrape_live import fetch_markdown, main, normalise_md, read_urls, strip_nav


# ── read_urls ──────────────────────────────────────────────────────────────

def test_read_urls_excludes_blanks(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("\nhttps://example.com\n\n")
    assert read_urls(str(f)) == ["https://example.com"]


def test_read_urls_excludes_comments(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("# comment\nhttps://example.com\n")
    assert read_urls(str(f)) == ["https://example.com"]


def test_read_urls_preserves_order(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("https://a.com\nhttps://b.com\nhttps://c.com\n")
    assert read_urls(str(f)) == ["https://a.com", "https://b.com", "https://c.com"]


def test_read_urls_all_blanks_and_comments(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("# only comments\n\n# another\n")
    assert read_urls(str(f)) == []


# ── strip_nav ──────────────────────────────────────────────────────────────

def test_strip_nav_removes_breadcrumb():
    result = strip_nav("breadcrumb: Home > Laptops\nActual content here")
    assert "breadcrumb" not in result
    assert "Actual content here" in result


def test_strip_nav_no_false_positive_cartridge():
    line = "cartridge case details"
    result = strip_nav(line)
    assert "cartridge case details" in result


def test_strip_nav_preserves_provenance_comment():
    line = "<!-- https://ebay.com.au/itm/123 -->"
    assert strip_nav(line) == line


def test_strip_nav_preserves_unrelated_content():
    line = "ASUS ROG Zephyrus G14, RTX 4070, 32GB RAM"
    assert strip_nav(line) == line


# ── normalise_md ───────────────────────────────────────────────────────────

def test_normalise_md_strips_bold():
    assert normalise_md("**bold**") == "bold"


def test_normalise_md_strips_link():
    assert normalise_md("[link text](https://example.com)") == "link text"


def test_normalise_md_plain_text_unchanged():
    plain = "ASUS ROG laptop 32GB RAM RTX 4090"
    assert normalise_md(plain) == plain


# ── fetch_markdown ─────────────────────────────────────────────────────────

def _make_doc(content: str):
    doc = MagicMock()
    doc.markdown = content
    return doc


def test_fetch_markdown_returns_cleaned_string():
    client = MagicMock()
    client.scrape.return_value = _make_doc("A" * 250)
    result = fetch_markdown("https://example.com", client)
    assert result is not None
    assert len(result) >= 200


def test_fetch_markdown_thin_content_returns_none(capsys):
    client = MagicMock()
    client.scrape.return_value = _make_doc("short")
    result = fetch_markdown("https://example.com", client)
    assert result is None
    assert "WARN" in capsys.readouterr().err


def test_fetch_markdown_none_markdown_returns_none(capsys):
    client = MagicMock()
    client.scrape.return_value = _make_doc(None)
    result = fetch_markdown("https://example.com", client)
    assert result is None
    assert "WARN" in capsys.readouterr().err


def test_fetch_markdown_exception_returns_none(capsys):
    client = MagicMock()
    client.scrape.side_effect = Exception("network error")
    result = fetch_markdown("https://example.com", client)
    assert result is None
    assert "WARN" in capsys.readouterr().err


# ── main ───────────────────────────────────────────────────────────────────

def test_main_missing_api_key_exits(tmp_path, capsys):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://example.com\n")
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc:
            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])
        assert exc.value.code == 1
    assert "FIRECRAWL_API_KEY" in capsys.readouterr().err


def test_main_first_fails_second_succeeds(tmp_path, capsys):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://fail.com\nhttps://ok.com\n")

    good_doc = _make_doc("B" * 300)

    def mock_scrape(url, **kwargs):
        if "fail" in url:
            raise Exception("timeout")
        return good_doc

    mock_client = MagicMock()
    mock_client.scrape.side_effect = mock_scrape

    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
        with patch("laptopfinder.scrape_live.Firecrawl", return_value=mock_client):
            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])

    written = list(tmp_path.glob("listing-*.txt"))
    assert len(written) == 1
    # n=2 because fail.com was attempted first (counter tracks all URLs, not just successes)
    assert written[0].name == "listing-002.txt"
    assert "WARN" in capsys.readouterr().err


def test_main_output_file_has_url_prefix_without_query(tmp_path):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://ebay.com.au/itm/123?mkcid=1&mkrid=705\n")

    doc = _make_doc("C" * 300)
    mock_client = MagicMock()
    mock_client.scrape.return_value = doc

    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
        with patch("laptopfinder.scrape_live.Firecrawl", return_value=mock_client):
            main(["--urls-file", str(urls_file), "--out-dir", str(tmp_path)])

    files = list(tmp_path.glob("listing-*.txt"))
    assert len(files) == 1
    content = files[0].read_text()
    assert content.startswith("<!-- ")
    assert "?" not in content.split("\n")[0]
    assert "&" not in content.split("\n")[0]
