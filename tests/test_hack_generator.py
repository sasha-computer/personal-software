"""Tests for US-004: Domain Hack Generator."""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from domain_search.hack_generator import (
    DomainHack,
    find_suffix_hacks,
    find_interior_hacks,
    generate_domain_hacks,
)
from domain_search.dns_checker import DomainResult, DomainStatus
from main import main, display_results


# --- find_suffix_hacks ---

def test_suffix_hack_finds_matching_tld():
    """kostick ends with ck -> kosti.ck"""
    hacks = find_suffix_hacks("kostick", ["ck"])
    assert len(hacks) == 1
    assert hacks[0].domain == "kosti.ck"
    assert hacks[0].visual == "kostick"


def test_suffix_hack_multiple_matches():
    """sasha ends with both 'a' and 'sha'."""
    hacks = find_suffix_hacks("sasha", ["a", "sha"])
    domains = [h.domain for h in hacks]
    assert "sash.a" in domains
    assert "sa.sha" in domains


def test_suffix_hack_no_match():
    hacks = find_suffix_hacks("hello", ["ck", "xyz"])
    assert hacks == []


def test_suffix_hack_tld_equals_word():
    """TLD that equals the entire word should not produce a hack (no prefix)."""
    hacks = find_suffix_hacks("com", ["com"])
    assert hacks == []


def test_suffix_hack_visual_reading():
    hacks = find_suffix_hacks("deutsch", ["ch"])
    assert hacks[0].visual == "deutsch"
    assert hacks[0].domain == "deuts.ch"


# --- find_interior_hacks ---

def test_interior_hack_finds_tld_within_word():
    """sasha contains 'sh' at position 2 -> sa.sh (reads as 'sash')."""
    hacks = find_interior_hacks("sasha", ["sh"])
    assert len(hacks) == 1
    assert hacks[0].domain == "sa.sh"
    assert hacks[0].visual == "sash"


def test_interior_hack_excludes_suffix_matches():
    """Suffix matches should be excluded from interior results."""
    hacks = find_interior_hacks("kostick", ["ck"])
    # "ck" appears at the end — that's a suffix match, excluded here
    assert hacks == []


def test_interior_hack_no_match():
    hacks = find_interior_hacks("hello", ["xyz"])
    assert hacks == []


def test_interior_hack_tld_at_start():
    """TLD at position 0 means no prefix — should be excluded."""
    hacks = find_interior_hacks("comedy", ["co"])
    # "co" at position 0 has no prefix, should be excluded
    assert hacks == []


def test_interior_hack_multiple_positions():
    """Word with TLD appearing in multiple non-suffix positions should only produce unique domains."""
    # "banana" with tld "an" -> b.an (pos 1), ban.an (pos 3); pos 5 is suffix
    hacks = find_interior_hacks("banana", ["an"])
    domains = [h.domain for h in hacks]
    assert "b.an" in domains
    assert "ban.an" in domains
    assert len(domains) == 2  # no suffix match (pos 4 ends at 6=len, excluded)


# --- generate_domain_hacks ---

def test_generate_domain_hacks_combines_suffix_and_interior():
    tlds = ["ck", "os", "st"]
    hacks = generate_domain_hacks("kostick", tlds)
    domains = [h.domain for h in hacks]
    # "kostick" ends with "ck" -> kosti.ck (suffix)
    assert "kosti.ck" in domains
    # "kostick" contains "os" at pos 1 -> k.os (interior, visual "kos")
    assert "k.os" in domains
    # "kostick" contains "st" at pos 2 -> ko.st (interior, visual "kost")
    assert "ko.st" in domains


def test_generate_domain_hacks_deduplicates():
    """If a domain is found by both suffix and interior logic, only include it once."""
    # Artificially craft a case where the same domain could appear twice
    hacks = generate_domain_hacks("abc", ["bc", "c"])
    domains = [h.domain for h in hacks]
    assert len(domains) == len(set(domains))


def test_generate_domain_hacks_sorted():
    hacks = generate_domain_hacks("kostick", ["ck", "os", "st"])
    domains = [h.domain for h in hacks]
    assert domains == sorted(domains)


def test_generate_domain_hacks_empty_tlds():
    assert generate_domain_hacks("word", []) == []


def test_generate_domain_hacks_no_matches():
    assert generate_domain_hacks("xyz", ["com", "net"]) == []


# --- CLI integration (--hack flag) ---

def test_main_hack_flag(capsys):
    """main() should accept --hack flag and find domain hacks."""
    mock_results = [
        DomainResult("kosti.ck", DomainStatus.AVAILABLE),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    async def mock_verify(dns_results, rate_limit=10, on_result=None):
        return dns_results

    with (
        patch("main.fetch_tld_list", return_value=["ck", "com"]),
        patch("main.check_domains", side_effect=mock_check_domains),
        patch("main.verify_available_domains", side_effect=mock_verify),
        patch("sys.argv", ["main.py", "--hack", "kostick"]),
    ):
        main()

    output = capsys.readouterr().out
    assert "kosti.ck" in output
    assert "kostick" in output  # visual reading
    assert "hack" in output  # type column


def test_main_combined_term_and_hack(capsys):
    """main() should support both positional term and --hack together."""
    mock_results = [
        DomainResult("sasha.com", DomainStatus.REGISTERED),
        DomainResult("sa.sh", DomainStatus.AVAILABLE),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    async def mock_verify(dns_results, rate_limit=10, on_result=None):
        return dns_results

    with (
        patch("main.fetch_tld_list", return_value=["com", "sh"]),
        patch("main.check_domains", side_effect=mock_check_domains),
        patch("main.verify_available_domains", side_effect=mock_verify),
        patch("sys.argv", ["main.py", "sasha", "--hack", "sasha"]),
    ):
        main()

    output = capsys.readouterr().out
    assert "sasha.com" in output
    assert "sa.sh" in output


def test_main_requires_term_or_hack(capsys):
    """main() should error if neither term nor --hack is provided."""
    with (
        patch("sys.argv", ["main.py"]),
        pytest.raises(SystemExit),
    ):
        main()


def test_display_results_with_hack_metadata(capsys):
    """display_results should show Type and Visual Reading columns when hacks are present."""
    results = [
        DomainResult("kosti.ck", DomainStatus.AVAILABLE),
        DomainResult("sasha.com", DomainStatus.REGISTERED),
    ]
    meta = {
        "kosti.ck": {"type": "hack", "visual": "kostick"},
        "sasha.com": {"type": "exact", "visual": ""},
    }
    display_results(results, meta)
    output = capsys.readouterr().out
    assert "Type" in output
    assert "Visual Reading" in output
    assert "hack" in output
    assert "exact" in output
    assert "kostick" in output


def test_display_results_without_hack_metadata(capsys):
    """display_results without hacks should show simple format (no Type/Visual columns)."""
    results = [
        DomainResult("sasha.com", DomainStatus.REGISTERED),
    ]
    display_results(results)
    output = capsys.readouterr().out
    assert "Type" not in output
    assert "Visual Reading" not in output
