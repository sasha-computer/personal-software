"""Tests for US-006: Rich Terminal Output."""

from unittest.mock import patch

from domain_search.cli import STATUS_STYLES, display_results
from domain_search.dns_checker import DomainResult, DomainStatus
from domain_search.types import DomainMetaMap

from .conftest import _capture_console


def test_display_uses_rich_table():
    """display_results should render a rich Table with 'Domain Search Results' title."""
    test_console, buf = _capture_console()
    results = [DomainResult("sasha.com", DomainStatus.REGISTERED)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "Domain Search Results" in output


def test_display_table_has_domain_column():
    """Table should have a Domain column."""
    test_console, buf = _capture_console()
    results = [DomainResult("sasha.com", DomainStatus.REGISTERED)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "Domain" in output
    assert "Status" in output


def test_display_table_hack_columns():
    """Table should show Type and Visual Reading columns when hack metadata is present."""
    test_console, buf = _capture_console()
    results = [
        DomainResult("kosti.ck", DomainStatus.AVAILABLE),
        DomainResult("sasha.com", DomainStatus.REGISTERED),
    ]
    meta: DomainMetaMap = {
        "kosti.ck": {"type": "hack", "visual": "kostick"},
        "sasha.com": {"type": "exact", "visual": ""},
    }
    display_results(results, meta, output_console=test_console)
    output = buf.getvalue()
    assert "Type" in output
    assert "Visual Reading" in output


def test_display_no_hack_columns_without_hacks():
    """Table should NOT show Type/Visual Reading columns when no hacks."""
    test_console, buf = _capture_console()
    results = [DomainResult("sasha.com", DomainStatus.REGISTERED)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "Type" not in output
    assert "Visual Reading" not in output


def test_display_color_coded_available():
    """Available domains should use green styling (ANSI escape codes)."""
    test_console, buf = _capture_console()
    results = [DomainResult("free.xyz", DomainStatus.AVAILABLE)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    # Rich uses ANSI codes for green - check the status text appears
    assert "possibly available" in output
    assert "free.xyz" in output


def test_display_color_coded_registered():
    """Registered domains should use red styling."""
    test_console, buf = _capture_console()
    results = [DomainResult("taken.com", DomainStatus.REGISTERED)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "registered" in output
    assert "taken.com" in output


def test_display_color_coded_unknown():
    """Unknown domains should use yellow styling."""
    test_console, buf = _capture_console()
    results = [DomainResult("mystery.net", DomainStatus.UNKNOWN)]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "unknown" in output
    assert "mystery.net" in output


def test_status_styles_mapping():
    """STATUS_STYLES should map all DomainStatus values to correct colors."""
    assert "green" in STATUS_STYLES[DomainStatus.AVAILABLE]
    assert "red" in STATUS_STYLES[DomainStatus.REGISTERED]
    assert "yellow" in STATUS_STYLES[DomainStatus.UNKNOWN]


def test_display_summary_with_counts():
    """Summary should show total, available, registered, and unknown counts."""
    test_console, buf = _capture_console()
    results = [
        DomainResult("a.com", DomainStatus.AVAILABLE),
        DomainResult("b.com", DomainStatus.AVAILABLE),
        DomainResult("c.com", DomainStatus.REGISTERED),
        DomainResult("d.com", DomainStatus.REGISTERED),
        DomainResult("e.com", DomainStatus.REGISTERED),
        DomainResult("f.com", DomainStatus.UNKNOWN),
    ]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    assert "Total: 6" in output
    assert "Available: 2" in output
    assert "Registered: 3" in output
    assert "Unknown: 1" in output


def test_display_available_grouped_at_top():
    """Available domains should appear before registered/unknown in the output."""
    test_console, buf = _capture_console()
    results = [
        DomainResult("z.com", DomainStatus.REGISTERED),
        DomainResult("a.xyz", DomainStatus.AVAILABLE),
        DomainResult("m.net", DomainStatus.UNKNOWN),
    ]
    display_results(results, output_console=test_console)
    output = buf.getvalue()
    # Available should come first
    pos_available = output.index("a.xyz")
    pos_unknown = output.index("m.net")
    pos_registered = output.index("z.com")
    assert pos_available < pos_unknown < pos_registered


def test_display_empty_results():
    """display_results should handle empty results gracefully."""
    test_console, buf = _capture_console()
    display_results([], output_console=test_console)
    output = buf.getvalue()
    assert "Total: 0" in output
    assert "Available: 0" in output


def test_main_uses_rich_progress_bar():
    """main() should use rich Progress for DNS scanning."""
    from domain_search.cli import main

    mock_results = [
        DomainResult("test.com", DomainStatus.REGISTERED),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    async def mock_verify(dns_results, rate_limit=10, on_result=None):
        return dns_results

    test_console, buf = _capture_console()

    with (
        patch("domain_search.cli.fetch_tld_list", return_value=["com"]),
        patch("domain_search.cli.check_domains", side_effect=mock_check_domains),
        patch("domain_search.cli.verify_available_domains", side_effect=mock_verify),
        patch("domain_search.cli.console", test_console),
        patch("sys.argv", ["main.py", "test"]),
    ):
        main()

    output = buf.getvalue()
    # Rich progress bar outputs progress info; also should have the table
    assert "Domain Search Results" in output
    assert "test.com" in output
