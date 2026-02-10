"""Tests for US-003: Search term.{tld} across all TLDs."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import dns.asyncresolver
import dns.resolver
import pytest

from domain_search.dns_checker import DomainResult, DomainStatus
from main import generate_domains, sort_results, display_results


def test_generate_domains_creates_all_combinations():
    tlds = ["com", "net", "org"]
    domains = generate_domains("sasha", tlds)
    assert domains == ["sasha.com", "sasha.net", "sasha.org"]


def test_generate_domains_empty_tlds():
    assert generate_domains("sasha", []) == []


def test_generate_domains_preserves_term():
    domains = generate_domains("my-site", ["io"])
    assert domains == ["my-site.io"]


def test_sort_results_by_status_then_alphabetically():
    results = [
        DomainResult("b.com", DomainStatus.REGISTERED),
        DomainResult("a.net", DomainStatus.AVAILABLE),
        DomainResult("c.org", DomainStatus.UNKNOWN),
        DomainResult("a.com", DomainStatus.REGISTERED),
        DomainResult("z.io", DomainStatus.AVAILABLE),
    ]
    sorted_r = sort_results(results)
    # Available first (alphabetically), then unknown, then registered
    assert sorted_r[0].domain == "a.net"
    assert sorted_r[0].status == DomainStatus.AVAILABLE
    assert sorted_r[1].domain == "z.io"
    assert sorted_r[1].status == DomainStatus.AVAILABLE
    assert sorted_r[2].domain == "c.org"
    assert sorted_r[2].status == DomainStatus.UNKNOWN
    assert sorted_r[3].domain == "a.com"
    assert sorted_r[3].status == DomainStatus.REGISTERED
    assert sorted_r[4].domain == "b.com"
    assert sorted_r[4].status == DomainStatus.REGISTERED


def test_sort_results_empty():
    assert sort_results([]) == []


def test_display_results_outputs_summary(capsys):
    results = [
        DomainResult("sasha.com", DomainStatus.REGISTERED),
        DomainResult("sasha.xyz", DomainStatus.AVAILABLE),
        DomainResult("sasha.zzz", DomainStatus.UNKNOWN),
    ]
    display_results(results)
    output = capsys.readouterr().out
    assert "Total: 3" in output
    assert "Available: 1" in output
    assert "Registered: 1" in output
    assert "Unknown: 1" in output


def test_display_results_sorted_order(capsys):
    results = [
        DomainResult("b.com", DomainStatus.REGISTERED),
        DomainResult("a.xyz", DomainStatus.AVAILABLE),
    ]
    display_results(results)
    output = capsys.readouterr().out
    # Available should appear before registered in output
    available_pos = output.index("a.xyz")
    registered_pos = output.index("b.com")
    assert available_pos < registered_pos


@pytest.mark.asyncio
async def test_on_result_callback_invoked():
    """check_domains should invoke on_result callback for each domain."""
    callback_calls = []

    def on_result(result):
        callback_calls.append(result)

    async def mock_resolve(domain, rdtype):
        return MagicMock()

    with patch("domain_search.dns_checker.dns.asyncresolver.Resolver") as MockResolver:
        mock_r = MagicMock()
        mock_r.resolve = AsyncMock(side_effect=mock_resolve)
        MockResolver.return_value = mock_r

        from domain_search.dns_checker import check_domains
        results = await check_domains(["a.com", "b.com"], on_result=on_result)
        assert len(callback_calls) == 2
        assert len(results) == 2


def test_main_accepts_cli_argument(capsys):
    """main() should accept a search term as CLI argument."""
    from main import main

    # Mock both fetch_tld_list and check_domains to avoid real network calls
    mock_results = [
        DomainResult("test.com", DomainStatus.REGISTERED),
        DomainResult("test.xyz", DomainStatus.AVAILABLE),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    with (
        patch("main.fetch_tld_list", return_value=["com", "xyz"]),
        patch("main.check_domains", side_effect=mock_check_domains),
        patch("sys.argv", ["main.py", "test"]),
    ):
        main()

    output = capsys.readouterr().out
    assert "test.com" in output
    assert "test.xyz" in output
    assert "Available: 1" in output
    assert "Registered: 1" in output
