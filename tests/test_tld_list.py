"""Tests for TLD list fetching and caching."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from domain_search.tld_list import (
    _parse_tld_text,
    fetch_tld_list,
    CACHE_MAX_AGE,
)

SAMPLE_IANA_TEXT = """\
# Version 2024020400, Last Updated Mon Feb  5 07:07:01 2024 UTC
AAA
AARP
ABB
XN--11B4C3D
COM
NET
ORG
"""


def test_parse_tld_text_skips_comments_and_blanks():
    tlds = _parse_tld_text(SAMPLE_IANA_TEXT)
    assert "aaa" in tlds
    assert "com" in tlds
    # Comments should not appear
    assert not any(t.startswith("#") for t in tlds)


def test_parse_tld_text_lowercases():
    tlds = _parse_tld_text(SAMPLE_IANA_TEXT)
    assert all(t == t.lower() for t in tlds)


def test_parse_tld_text_handles_punycode():
    tlds = _parse_tld_text(SAMPLE_IANA_TEXT)
    assert "xn--11b4c3d" in tlds


def test_parse_tld_text_correct_count():
    tlds = _parse_tld_text(SAMPLE_IANA_TEXT)
    assert len(tlds) == 7


def test_fetch_tld_list_uses_cache(tmp_path: Path):
    cache_file = tmp_path / "tlds.txt"
    cache_file.write_text(SAMPLE_IANA_TEXT)

    with (
        patch("domain_search.tld_list.CACHE_FILE", cache_file),
        patch("domain_search.tld_list._cache_is_fresh", return_value=True),
    ):
        tlds = fetch_tld_list()
        assert len(tlds) == 7
        assert "com" in tlds


def test_fetch_tld_list_downloads_when_no_cache(tmp_path: Path):
    cache_file = tmp_path / "tlds.txt"
    cache_dir = tmp_path

    mock_response = MagicMock()
    mock_response.text = SAMPLE_IANA_TEXT
    mock_response.raise_for_status = MagicMock()

    with (
        patch("domain_search.tld_list.CACHE_FILE", cache_file),
        patch("domain_search.tld_list.CACHE_DIR", cache_dir),
        patch("domain_search.tld_list._cache_is_fresh", return_value=False),
        patch("domain_search.tld_list.httpx.get", return_value=mock_response) as mock_get,
    ):
        tlds = fetch_tld_list()
        mock_get.assert_called_once()
        assert len(tlds) == 7
        # Cache file should have been written
        assert cache_file.exists()


def test_fetch_tld_list_force_refresh(tmp_path: Path):
    cache_file = tmp_path / "tlds.txt"
    cache_file.write_text("# old data\nOLD")
    cache_dir = tmp_path

    mock_response = MagicMock()
    mock_response.text = SAMPLE_IANA_TEXT
    mock_response.raise_for_status = MagicMock()

    with (
        patch("domain_search.tld_list.CACHE_FILE", cache_file),
        patch("domain_search.tld_list.CACHE_DIR", cache_dir),
        patch("domain_search.tld_list._cache_is_fresh", return_value=True),
        patch("domain_search.tld_list.httpx.get", return_value=mock_response) as mock_get,
    ):
        tlds = fetch_tld_list(force_refresh=True)
        mock_get.assert_called_once()
        assert len(tlds) == 7
        assert "old" not in tlds
