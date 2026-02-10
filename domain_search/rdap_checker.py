"""RDAP availability verification for domains flagged as 'possibly available' by DNS."""

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx

from domain_search.dns_checker import DomainResult, DomainStatus


RDAP_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
RDAP_CACHE_DIR = Path.home() / ".cache" / "domain-search"
RDAP_CACHE_FILE = RDAP_CACHE_DIR / "rdap_bootstrap.json"
RDAP_CACHE_MAX_AGE = 86400  # 1 day in seconds
RDAP_QUERY_TIMEOUT = 10.0
DEFAULT_RATE_LIMIT = 10  # max queries per second


class RdapStatus(Enum):
    REGISTERED = "registered"
    AVAILABLE = "available"
    RESERVED = "reserved"
    NO_RDAP = "no_rdap"
    ERROR = "error"


@dataclass
class RdapResult:
    domain: str
    rdap_status: RdapStatus
    final_status: DomainStatus


def _cache_is_valid() -> bool:
    """Check if the cached RDAP bootstrap file exists and is fresh."""
    if not RDAP_CACHE_FILE.exists():
        return False
    age = time.time() - RDAP_CACHE_FILE.stat().st_mtime
    return age < RDAP_CACHE_MAX_AGE


def _load_cached_bootstrap() -> dict[str, str]:
    """Load the TLD-to-RDAP-URL mapping from the cached bootstrap file."""
    data = json.loads(RDAP_CACHE_FILE.read_text())
    return _parse_bootstrap(data)


def _parse_bootstrap(data: dict) -> dict[str, str]:
    """Parse IANA RDAP bootstrap JSON into a TLD → RDAP base URL mapping.

    Each service entry is [tld_list, url_list]. We pick the first HTTPS URL
    if available, otherwise the first URL.
    """
    tld_map: dict[str, str] = {}
    for tld_list, url_list in data.get("services", []):
        # Prefer HTTPS URL
        url = url_list[0]
        for u in url_list:
            if u.startswith("https://"):
                url = u
                break
        # Ensure trailing slash
        if not url.endswith("/"):
            url += "/"
        for tld in tld_list:
            tld_map[tld.lower()] = url
    return tld_map


async def fetch_rdap_bootstrap() -> dict[str, str]:
    """Fetch the IANA RDAP bootstrap file and return a TLD → RDAP URL mapping.

    Uses a local cache with 1-day expiry.
    """
    if _cache_is_valid():
        return _load_cached_bootstrap()

    async with httpx.AsyncClient() as client:
        response = await client.get(RDAP_BOOTSTRAP_URL, timeout=30.0)
        response.raise_for_status()
        data = response.json()

    # Cache the raw bootstrap JSON
    RDAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RDAP_CACHE_FILE.write_text(json.dumps(data))

    return _parse_bootstrap(data)


def _get_tld(domain: str) -> str:
    """Extract the TLD from a domain name."""
    return domain.rsplit(".", 1)[-1].lower()


def _classify_rdap_response(data: dict) -> RdapStatus:
    """Classify a domain's registration status from RDAP response data.

    Looks at the 'status' array in the RDAP response. Common status values:
    - "active" → registered
    - "reserved" → reserved by registry
    - Various EPP status codes indicate registration
    """
    statuses = [s.lower() for s in data.get("status", [])]

    # Check for reserved status
    for s in statuses:
        if "reserved" in s:
            return RdapStatus.RESERVED

    # Any status at all typically means registered (active, locked, etc.)
    if statuses:
        return RdapStatus.REGISTERED

    # Response exists but no status array — treat as registered
    return RdapStatus.REGISTERED


def _rdap_to_domain_status(rdap_status: RdapStatus) -> DomainStatus:
    """Map an RDAP status to the unified DomainStatus."""
    if rdap_status == RdapStatus.AVAILABLE:
        return DomainStatus.AVAILABLE
    elif rdap_status in (RdapStatus.REGISTERED, RdapStatus.RESERVED):
        return DomainStatus.REGISTERED
    else:
        return DomainStatus.UNKNOWN


class _RateLimiter:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: int):
        self._rate = rate
        self._tokens = float(rate)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1


async def _query_rdap(
    domain: str,
    rdap_url: str,
    client: httpx.AsyncClient,
    rate_limiter: _RateLimiter,
) -> RdapResult:
    """Query a single domain via RDAP and return its status."""
    await rate_limiter.acquire()

    url = f"{rdap_url}domain/{domain}"
    try:
        response = await client.get(
            url,
            timeout=RDAP_QUERY_TIMEOUT,
            follow_redirects=True,
        )
        if response.status_code == 200:
            data = response.json()
            rdap_status = _classify_rdap_response(data)
        elif response.status_code == 404:
            rdap_status = RdapStatus.AVAILABLE
        else:
            rdap_status = RdapStatus.ERROR
    except (httpx.HTTPError, json.JSONDecodeError, Exception):
        rdap_status = RdapStatus.ERROR

    final_status = _rdap_to_domain_status(rdap_status)
    return RdapResult(domain=domain, rdap_status=rdap_status, final_status=final_status)


async def verify_available_domains(
    dns_results: list[DomainResult],
    rate_limit: int = DEFAULT_RATE_LIMIT,
    on_result: Callable[[RdapResult], None] | None = None,
) -> list[DomainResult]:
    """Verify domains flagged as 'possibly available' using RDAP.

    For each domain with DomainStatus.AVAILABLE, looks up the RDAP server
    for its TLD and queries for confirmation. Domains without RDAP servers
    keep their DNS-only result. Non-available domains are passed through unchanged.

    Args:
        dns_results: List of DomainResult objects from DNS checking.
        rate_limit: Maximum RDAP queries per second (default: 10).
        on_result: Optional callback invoked after each RDAP check completes.

    Returns:
        Updated list of DomainResult objects with RDAP-verified statuses.
    """
    # Separate available domains from the rest
    available = [r for r in dns_results if r.status == DomainStatus.AVAILABLE]
    other = [r for r in dns_results if r.status != DomainStatus.AVAILABLE]

    if not available:
        return dns_results

    # Fetch the RDAP bootstrap mapping
    tld_map = await fetch_rdap_bootstrap()

    # Partition available domains by whether they have an RDAP server
    has_rdap = []
    no_rdap = []
    for result in available:
        tld = _get_tld(result.domain)
        if tld in tld_map:
            has_rdap.append((result, tld_map[tld]))
        else:
            no_rdap.append(result)

    if not has_rdap:
        return dns_results

    # Query RDAP for domains that have a server
    rate_limiter = _RateLimiter(rate_limit)
    updated: list[DomainResult] = []

    async with httpx.AsyncClient() as client:
        tasks = []
        for dns_result, rdap_url in has_rdap:
            tasks.append(_query_rdap(dns_result.domain, rdap_url, client, rate_limiter))

        rdap_results = await asyncio.gather(*tasks)

    for rdap_result in rdap_results:
        updated.append(DomainResult(
            domain=rdap_result.domain,
            status=rdap_result.final_status,
        ))
        if on_result is not None:
            on_result(rdap_result)

    # Combine: other (registered/unknown) + no_rdap (keep available) + updated (RDAP-verified)
    return other + no_rdap + updated
