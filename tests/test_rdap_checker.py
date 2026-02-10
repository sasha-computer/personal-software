"""Tests for US-005: RDAP availability verification."""

import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest

from domain_search.dns_checker import DomainResult, DomainStatus
from domain_search.rdap_checker import (
    RdapStatus,
    RdapResult,
    _parse_bootstrap,
    _get_tld,
    _classify_rdap_response,
    _rdap_to_domain_status,
    _RateLimiter,
    fetch_rdap_bootstrap,
    verify_available_domains,
)


# --- Bootstrap parsing ---

def test_parse_bootstrap_basic():
    """Should map TLDs to RDAP URLs from bootstrap JSON."""
    data = {
        "services": [
            [["com", "net"], ["https://rdap.verisign.com/com/v1/"]],
            [["io"], ["https://rdap.nic.io/"]],
        ]
    }
    result = _parse_bootstrap(data)
    assert result["com"] == "https://rdap.verisign.com/com/v1/"
    assert result["net"] == "https://rdap.verisign.com/com/v1/"
    assert result["io"] == "https://rdap.nic.io/"


def test_parse_bootstrap_prefers_https():
    """Should prefer HTTPS URLs over HTTP."""
    data = {
        "services": [
            [["kg"], ["http://rdap.cctld.kg/", "https://rdap.cctld.kg/"]],
        ]
    }
    result = _parse_bootstrap(data)
    assert result["kg"] == "https://rdap.cctld.kg/"


def test_parse_bootstrap_adds_trailing_slash():
    """Should ensure trailing slash on URLs."""
    data = {
        "services": [
            [["com"], ["https://rdap.verisign.com/com/v1"]],
        ]
    }
    result = _parse_bootstrap(data)
    assert result["com"].endswith("/")


def test_parse_bootstrap_lowercases_tlds():
    """Should lowercase TLDs for consistent lookup."""
    data = {
        "services": [
            [["COM", "Net"], ["https://rdap.example.com/"]],
        ]
    }
    result = _parse_bootstrap(data)
    assert "com" in result
    assert "net" in result


def test_parse_bootstrap_empty_services():
    """Should return empty dict when no services."""
    assert _parse_bootstrap({"services": []}) == {}
    assert _parse_bootstrap({}) == {}


# --- Helper functions ---

def test_get_tld():
    assert _get_tld("example.com") == "com"
    assert _get_tld("sasha.co.uk") == "uk"
    assert _get_tld("kosti.ck") == "ck"


def test_classify_rdap_response_active():
    """Response with 'active' status should be classified as registered."""
    data = {"status": ["active"]}
    assert _classify_rdap_response(data) == RdapStatus.REGISTERED


def test_classify_rdap_response_locked():
    """Response with lock statuses should be classified as registered."""
    data = {"status": ["client delete prohibited", "client transfer prohibited"]}
    assert _classify_rdap_response(data) == RdapStatus.REGISTERED


def test_classify_rdap_response_reserved():
    """Response with 'reserved' in status should be classified as reserved."""
    data = {"status": ["reserved"]}
    assert _classify_rdap_response(data) == RdapStatus.RESERVED


def test_classify_rdap_response_server_reserved():
    """Response with 'server reserved' should be classified as reserved."""
    data = {"status": ["server reserved"]}
    assert _classify_rdap_response(data) == RdapStatus.RESERVED


def test_classify_rdap_response_empty_status():
    """Response with empty or no status array should be classified as registered."""
    # A 200 response with no status still means the domain exists in registry
    assert _classify_rdap_response({"status": []}) == RdapStatus.REGISTERED
    assert _classify_rdap_response({}) == RdapStatus.REGISTERED


def test_rdap_to_domain_status_mapping():
    """RDAP statuses should map to the correct DomainStatus."""
    assert _rdap_to_domain_status(RdapStatus.AVAILABLE) == DomainStatus.AVAILABLE
    assert _rdap_to_domain_status(RdapStatus.REGISTERED) == DomainStatus.REGISTERED
    assert _rdap_to_domain_status(RdapStatus.RESERVED) == DomainStatus.REGISTERED
    assert _rdap_to_domain_status(RdapStatus.NO_RDAP) == DomainStatus.UNKNOWN
    assert _rdap_to_domain_status(RdapStatus.ERROR) == DomainStatus.UNKNOWN


# --- Rate limiter ---

@pytest.mark.asyncio
async def test_rate_limiter_allows_burst():
    """Rate limiter should allow a burst of requests up to the rate."""
    limiter = _RateLimiter(rate=10)
    # Should be able to acquire 10 tokens quickly
    for _ in range(10):
        await limiter.acquire()


# --- Fetch bootstrap ---

@pytest.mark.asyncio
async def test_fetch_rdap_bootstrap_uses_cache(tmp_path):
    """Should use cached bootstrap file when valid."""
    cache_file = tmp_path / "rdap_bootstrap.json"
    bootstrap_data = {
        "services": [[["com"], ["https://rdap.verisign.com/com/v1/"]]]
    }
    cache_file.write_text(json.dumps(bootstrap_data))

    with (
        patch("domain_search.rdap_checker.RDAP_CACHE_FILE", cache_file),
        patch("domain_search.rdap_checker._cache_is_valid", return_value=True),
    ):
        result = await fetch_rdap_bootstrap()
        assert "com" in result
        assert result["com"] == "https://rdap.verisign.com/com/v1/"


@pytest.mark.asyncio
async def test_fetch_rdap_bootstrap_downloads_when_no_cache(tmp_path):
    """Should download bootstrap when cache is missing or stale."""
    cache_file = tmp_path / "rdap_bootstrap.json"
    cache_dir = tmp_path

    bootstrap_data = {
        "services": [[["io"], ["https://rdap.nic.io/"]]]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = bootstrap_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.RDAP_CACHE_FILE", cache_file),
        patch("domain_search.rdap_checker.RDAP_CACHE_DIR", cache_dir),
        patch("domain_search.rdap_checker._cache_is_valid", return_value=False),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await fetch_rdap_bootstrap()
        assert "io" in result
        # Should have cached the data
        assert cache_file.exists()


# --- verify_available_domains ---

@pytest.mark.asyncio
async def test_verify_no_available_domains():
    """If no domains are 'available', should return input unchanged."""
    dns_results = [
        DomainResult("a.com", DomainStatus.REGISTERED),
        DomainResult("b.com", DomainStatus.UNKNOWN),
    ]
    result = await verify_available_domains(dns_results)
    assert result == dns_results


@pytest.mark.asyncio
async def test_verify_domain_confirmed_available():
    """RDAP 404 should confirm domain as available."""
    dns_results = [
        DomainResult("available.com", DomainStatus.AVAILABLE),
        DomainResult("taken.com", DomainStatus.REGISTERED),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    statuses = {r.domain: r.status for r in results}
    assert statuses["available.com"] == DomainStatus.AVAILABLE
    assert statuses["taken.com"] == DomainStatus.REGISTERED


@pytest.mark.asyncio
async def test_verify_domain_actually_registered():
    """RDAP 200 with status should update domain to registered."""
    dns_results = [
        DomainResult("sneaky.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": ["active"]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    assert len(results) == 1
    assert results[0].domain == "sneaky.com"
    assert results[0].status == DomainStatus.REGISTERED


@pytest.mark.asyncio
async def test_verify_domain_reserved():
    """RDAP 200 with reserved status should update domain to registered."""
    dns_results = [
        DomainResult("reserved.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": ["reserved"]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    assert results[0].status == DomainStatus.REGISTERED


@pytest.mark.asyncio
async def test_verify_domain_no_rdap_server():
    """Domains with TLDs not in RDAP bootstrap should keep DNS-only result."""
    dns_results = [
        DomainResult("test.zz", DomainStatus.AVAILABLE),
    ]

    # Empty bootstrap — no RDAP servers
    mock_bootstrap: dict[str, str] = {}

    with patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap):
        results = await verify_available_domains(dns_results)

    assert len(results) == 1
    assert results[0].domain == "test.zz"
    assert results[0].status == DomainStatus.AVAILABLE


@pytest.mark.asyncio
async def test_verify_handles_http_error():
    """HTTP errors during RDAP query should result in unknown status."""
    dns_results = [
        DomainResult("error.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    assert results[0].status == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_verify_handles_unexpected_status_code():
    """Non-200/404 status codes should result in unknown status."""
    dns_results = [
        DomainResult("ratelimited.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 429  # Rate limited

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    assert results[0].status == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_verify_callback_invoked():
    """on_result callback should be invoked for each RDAP check."""
    dns_results = [
        DomainResult("a.com", DomainStatus.AVAILABLE),
        DomainResult("b.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    callback_calls = []

    def on_result(rdap_result):
        callback_calls.append(rdap_result)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        await verify_available_domains(dns_results, on_result=on_result)

    assert len(callback_calls) == 2


@pytest.mark.asyncio
async def test_verify_preserves_non_available_domains():
    """Registered and unknown domains should pass through unchanged."""
    dns_results = [
        DomainResult("reg.com", DomainStatus.REGISTERED),
        DomainResult("unk.com", DomainStatus.UNKNOWN),
        DomainResult("avail.com", DomainStatus.AVAILABLE),
    ]

    mock_bootstrap = {"com": "https://rdap.verisign.com/com/v1/"}

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("domain_search.rdap_checker.fetch_rdap_bootstrap", return_value=mock_bootstrap),
        patch("domain_search.rdap_checker.httpx.AsyncClient", return_value=mock_client),
    ):
        results = await verify_available_domains(dns_results)

    statuses = {r.domain: r.status for r in results}
    assert statuses["reg.com"] == DomainStatus.REGISTERED
    assert statuses["unk.com"] == DomainStatus.UNKNOWN
    assert statuses["avail.com"] == DomainStatus.AVAILABLE
    assert len(results) == 3


# --- CLI integration (--skip-rdap flag) ---

def test_main_skip_rdap_flag(capsys):
    """main() should skip RDAP when --skip-rdap is provided."""
    from main import main

    mock_results = [
        DomainResult("test.com", DomainStatus.AVAILABLE),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    with (
        patch("main.fetch_tld_list", return_value=["com"]),
        patch("main.check_domains", side_effect=mock_check_domains),
        patch("main.verify_available_domains") as mock_verify,
        patch("sys.argv", ["main.py", "test", "--skip-rdap"]),
    ):
        main()
        mock_verify.assert_not_called()

    output = capsys.readouterr().out
    assert "test.com" in output


def test_main_rdap_enabled_by_default(capsys):
    """main() should run RDAP verification by default."""
    from main import main

    mock_results = [
        DomainResult("test.com", DomainStatus.AVAILABLE),
    ]

    async def mock_check_domains(domains, concurrency=50, on_result=None):
        for r in mock_results:
            if on_result:
                on_result(r)
        return mock_results

    async def mock_verify(dns_results, rate_limit=10, on_result=None):
        # Simulate RDAP confirming the domain as registered
        return [DomainResult("test.com", DomainStatus.REGISTERED)]

    with (
        patch("main.fetch_tld_list", return_value=["com"]),
        patch("main.check_domains", side_effect=mock_check_domains),
        patch("main.verify_available_domains", side_effect=mock_verify),
        patch("sys.argv", ["main.py", "test"]),
    ):
        main()

    output = capsys.readouterr().out
    assert "test.com" in output
    assert "Registered: 1" in output
    assert "Available: 0" in output
