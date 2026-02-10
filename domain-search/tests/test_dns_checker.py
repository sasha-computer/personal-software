"""Tests for async DNS availability checker."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import dns.asyncresolver
import dns.exception
import dns.resolver
import pytest

from domain_search.dns_checker import (
    DEFAULT_CONCURRENCY,
    DomainResult,
    DomainStatus,
    check_domain,
    check_domains,
)


@pytest.fixture
def resolver():
    """Create a mock async resolver."""
    r = MagicMock(spec=dns.asyncresolver.Resolver)
    r.resolve = AsyncMock()
    r.timeout = 5.0
    r.lifetime = 5.0
    return r


@pytest.mark.asyncio
async def test_registered_domain_ns_records(resolver):
    """Domain with NS records should be classified as registered."""
    resolver.resolve.return_value = MagicMock()  # Has answer
    result = await check_domain("example.com", resolver)
    assert result.status == DomainStatus.REGISTERED
    assert result.domain == "example.com"


@pytest.mark.asyncio
async def test_available_domain_nxdomain(resolver):
    """Domain returning NXDOMAIN for both NS and SOA should be possibly available."""
    resolver.resolve.side_effect = dns.resolver.NXDOMAIN()
    result = await check_domain("available-test.xyz", resolver)
    assert result.status == DomainStatus.AVAILABLE
    assert result.domain == "available-test.xyz"


@pytest.mark.asyncio
async def test_timeout_returns_unknown(resolver):
    """DNS timeout should result in 'unknown' status."""
    resolver.resolve.side_effect = dns.exception.Timeout()
    result = await check_domain("slow.example", resolver)
    assert result.status == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_lifetime_timeout_returns_unknown(resolver):
    """LifetimeTimeout should result in 'unknown' status."""
    resolver.resolve.side_effect = dns.resolver.LifetimeTimeout()
    result = await check_domain("slow.example", resolver)
    assert result.status == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_no_answer_continues_to_soa(resolver):
    """NoAnswer on NS should continue to SOA lookup."""
    # First call (NS) raises NoAnswer, second call (SOA) returns records
    resolver.resolve.side_effect = [
        dns.resolver.NoAnswer(),
        MagicMock(),  # SOA has answer
    ]
    result = await check_domain("partial.example", resolver)
    assert result.status == DomainStatus.REGISTERED
    assert resolver.resolve.call_count == 2


@pytest.mark.asyncio
async def test_no_nameservers_continues(resolver):
    """NoNameservers on NS should continue to SOA lookup."""
    resolver.resolve.side_effect = [
        dns.resolver.NoNameservers(),
        dns.resolver.NXDOMAIN(),
    ]
    result = await check_domain("noserver.example", resolver)
    assert result.status == DomainStatus.AVAILABLE


@pytest.mark.asyncio
async def test_unexpected_exception_returns_unknown(resolver):
    """Unexpected exceptions should result in 'unknown' status."""
    resolver.resolve.side_effect = RuntimeError("unexpected")
    result = await check_domain("error.example", resolver)
    assert result.status == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_check_domains_returns_all_results(resolver):
    """check_domains should return one result per input domain."""
    domains = ["a.com", "b.com", "c.com"]

    # a.com -> registered (NS returns answer)
    # b.com -> available (NXDOMAIN for both)
    # c.com -> unknown (timeout)
    call_count = 0

    async def mock_resolve(domain, rdtype):
        nonlocal call_count
        call_count += 1
        if domain == "a.com":
            return MagicMock()  # Has records
        elif domain == "b.com":
            raise dns.resolver.NXDOMAIN()
        else:
            raise dns.exception.Timeout()

    with patch("domain_search.dns_checker.dns.asyncresolver.Resolver") as MockResolver:
        mock_r = MagicMock()
        mock_r.resolve = AsyncMock(side_effect=mock_resolve)
        MockResolver.return_value = mock_r

        results = await check_domains(domains)
        assert len(results) == 3
        statuses = {r.domain: r.status for r in results}
        assert statuses["a.com"] == DomainStatus.REGISTERED
        assert statuses["b.com"] == DomainStatus.AVAILABLE
        assert statuses["c.com"] == DomainStatus.UNKNOWN


@pytest.mark.asyncio
async def test_check_domains_respects_concurrency():
    """check_domains should limit concurrent lookups via semaphore."""
    max_concurrent = 0
    current_concurrent = 0

    async def mock_check(domain, resolver):
        nonlocal max_concurrent, current_concurrent
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.01)
        current_concurrent -= 1
        return DomainResult(domain, DomainStatus.REGISTERED)

    domains = [f"test{i}.com" for i in range(20)]

    with patch("domain_search.dns_checker.check_domain", side_effect=mock_check):
        results = await check_domains(domains, concurrency=5)
        assert len(results) == 20
        assert max_concurrent <= 5


@pytest.mark.asyncio
async def test_check_domains_empty_list():
    """check_domains should handle an empty list."""
    results = await check_domains([])
    assert results == []


def test_default_concurrency():
    """Default concurrency should be 50."""
    assert DEFAULT_CONCURRENCY == 50


def test_domain_status_values():
    """DomainStatus enum should have the expected values."""
    assert DomainStatus.REGISTERED.value == "registered"
    assert DomainStatus.AVAILABLE.value == "possibly available"
    assert DomainStatus.UNKNOWN.value == "unknown"
