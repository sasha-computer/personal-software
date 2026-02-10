"""Async DNS availability checker for domain names."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import dns.asyncresolver
import dns.resolver


class DomainStatus(Enum):
    REGISTERED = "registered"
    AVAILABLE = "possibly available"
    UNKNOWN = "unknown"


@dataclass
class DomainResult:
    domain: str
    status: DomainStatus


DEFAULT_CONCURRENCY = 50
DNS_TIMEOUT = 5.0


async def check_domain(domain: str, resolver: dns.asyncresolver.Resolver) -> DomainResult:
    """Check a single domain's availability via NS and SOA DNS lookups.

    A domain is classified as:
    - "registered" if NS or SOA records exist
    - "possibly available" if NXDOMAIN is returned for both
    - "unknown" if a timeout or other error occurs
    """
    for rdtype in ("NS", "SOA"):
        try:
            await resolver.resolve(domain, rdtype)
            return DomainResult(domain=domain, status=DomainStatus.REGISTERED)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            continue
        except dns.resolver.NoAnswer:
            continue
        except (dns.exception.Timeout, dns.resolver.LifetimeTimeout):
            return DomainResult(domain=domain, status=DomainStatus.UNKNOWN)
        except Exception:
            return DomainResult(domain=domain, status=DomainStatus.UNKNOWN)

    return DomainResult(domain=domain, status=DomainStatus.AVAILABLE)


async def check_domains(
    domains: list[str],
    concurrency: int = DEFAULT_CONCURRENCY,
    on_result: Callable[[DomainResult], None] | None = None,
) -> list[DomainResult]:
    """Check multiple domains concurrently with a configurable concurrency limit.

    Args:
        domains: List of domain names to check (e.g. ["sasha.io", "sasha.dev"]).
        concurrency: Maximum number of concurrent DNS lookups.
        on_result: Optional callback invoked after each domain is checked.

    Returns:
        A list of DomainResult objects, one per input domain.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = DNS_TIMEOUT
    resolver.lifetime = DNS_TIMEOUT

    semaphore = asyncio.Semaphore(concurrency)

    async def _check_with_limit(domain: str) -> DomainResult:
        async with semaphore:
            result = await check_domain(domain, resolver)
            if on_result is not None:
                on_result(result)
            return result

    tasks = [asyncio.create_task(_check_with_limit(d)) for d in domains]
    results = await asyncio.gather(*tasks)
    return list(results)
