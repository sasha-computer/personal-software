"""Fetch and cache the IANA TLD list."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

IANA_TLD_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
CACHE_DIR = Path.home() / ".cache" / "domain-search"
CACHE_FILE = CACHE_DIR / "tlds.txt"
CACHE_MAX_AGE = timedelta(days=1)


def _cache_is_fresh() -> bool:
    """Check if the cached TLD file exists and is less than CACHE_MAX_AGE old."""
    if not CACHE_FILE.exists():
        return False
    mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime, tz=UTC)
    return datetime.now(UTC) - mtime < CACHE_MAX_AGE


def _parse_tld_text(text: str) -> list[str]:
    """Parse the IANA TLD list text, skipping comments and blank lines.

    Returns lowercase TLD strings (including IDN/punycode like xn--...)
    """
    tlds: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tlds.append(line.lower())
    return tlds


def fetch_tld_list(*, force_refresh: bool = False) -> list[str]:
    """Fetch the complete TLD list from IANA, using a local cache.

    Args:
        force_refresh: If True, bypass the cache and re-download.

    Returns:
        A list of lowercase TLD strings.
    """
    if not force_refresh and _cache_is_fresh():
        text = CACHE_FILE.read_text()
    else:
        response = httpx.get(IANA_TLD_URL, follow_redirects=True, timeout=30)
        response.raise_for_status()
        text = response.text
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(text)

    tlds = _parse_tld_text(text)
    return tlds
