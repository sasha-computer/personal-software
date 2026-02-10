"""Domain Search CLI - find available domain names across all TLDs."""

import argparse
import asyncio
import sys

from domain_search.tld_list import fetch_tld_list
from domain_search.dns_checker import DomainStatus, DomainResult, check_domains


def generate_domains(term: str, tlds: list[str]) -> list[str]:
    """Generate {term}.{tld} for every TLD in the list."""
    return [f"{term}.{tld}" for tld in tlds]


def sort_results(results: list[DomainResult]) -> list[DomainResult]:
    """Sort results by availability status (available first, then unknown, then registered), then alphabetically."""
    status_order = {
        DomainStatus.AVAILABLE: 0,
        DomainStatus.UNKNOWN: 1,
        DomainStatus.REGISTERED: 2,
    }
    return sorted(results, key=lambda r: (status_order[r.status], r.domain))


def display_results(results: list[DomainResult]) -> None:
    """Display results to the terminal."""
    sorted_results = sort_results(results)

    available = sum(1 for r in results if r.status == DomainStatus.AVAILABLE)
    registered = sum(1 for r in results if r.status == DomainStatus.REGISTERED)
    unknown = sum(1 for r in results if r.status == DomainStatus.UNKNOWN)

    print(f"\n{'Domain':<40} {'Status'}")
    print("-" * 60)
    for r in sorted_results:
        print(f"{r.domain:<40} {r.status.value}")

    print("-" * 60)
    print(f"Total: {len(results)} | Available: {available} | Registered: {registered} | Unknown: {unknown}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search for available domain names across all TLDs."
    )
    parser.add_argument("term", help="Search term (e.g., sasha)")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Max concurrent DNS lookups (default: 50)",
    )
    args = parser.parse_args()

    tlds = fetch_tld_list()
    domains = generate_domains(args.term, tlds)

    total = len(domains)
    checked = 0

    def on_result(result: DomainResult) -> None:
        nonlocal checked
        checked += 1
        sys.stdout.write(f"\rChecking {total:,} domains... [{checked:,}/{total:,}]")
        sys.stdout.flush()

    print(f"Loaded {len(tlds):,} TLDs")
    print(f"Checking {total:,} domains for '{args.term}'...")

    results = asyncio.run(
        check_domains(domains, concurrency=args.concurrency, on_result=on_result)
    )

    # Clear the progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    display_results(results)


if __name__ == "__main__":
    main()
