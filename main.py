"""Domain Search CLI - find available domain names across all TLDs."""

import argparse
import asyncio
import sys

from domain_search.tld_list import fetch_tld_list
from domain_search.dns_checker import DomainStatus, DomainResult, check_domains
from domain_search.hack_generator import generate_domain_hacks, DomainHack
from domain_search.rdap_checker import verify_available_domains


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


def display_results(
    results: list[DomainResult],
    domain_meta: dict[str, dict] | None = None,
) -> None:
    """Display results to the terminal.

    Args:
        results: List of DomainResult objects.
        domain_meta: Optional dict mapping domain -> {"type": "exact"|"hack", "visual": str}.
    """
    sorted_results = sort_results(results)
    meta = domain_meta or {}

    available = sum(1 for r in results if r.status == DomainStatus.AVAILABLE)
    registered = sum(1 for r in results if r.status == DomainStatus.REGISTERED)
    unknown = sum(1 for r in results if r.status == DomainStatus.UNKNOWN)

    has_hacks = any(m.get("type") == "hack" for m in meta.values())

    if has_hacks:
        print(f"\n{'Domain':<30} {'Status':<20} {'Type':<8} {'Visual Reading'}")
        print("-" * 80)
        for r in sorted_results:
            m = meta.get(r.domain, {})
            dtype = m.get("type", "exact")
            visual = m.get("visual", "")
            print(f"{r.domain:<30} {r.status.value:<20} {dtype:<8} {visual}")
    else:
        print(f"\n{'Domain':<40} {'Status'}")
        print("-" * 60)
        for r in sorted_results:
            print(f"{r.domain:<40} {r.status.value}")

    print("-" * (80 if has_hacks else 60))
    print(f"Total: {len(results)} | Available: {available} | Registered: {registered} | Unknown: {unknown}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search for available domain names across all TLDs."
    )
    parser.add_argument("term", nargs="?", help="Search term for exact match (e.g., sasha)")
    parser.add_argument(
        "--hack",
        metavar="WORD",
        help="Find domain hacks where the TLD forms part of the word (e.g., --hack kostick)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Max concurrent DNS lookups (default: 50)",
    )
    parser.add_argument(
        "--skip-rdap",
        action="store_true",
        help="Skip RDAP verification of available domains (faster but less accurate)",
    )
    args = parser.parse_args()

    if not args.term and not args.hack:
        parser.error("at least one of 'term' or '--hack WORD' is required")

    tlds = fetch_tld_list()

    # Build the list of domains to check and metadata for display
    all_domains: list[str] = []
    domain_meta: dict[str, dict] = {}

    # Exact search: term.{tld}
    if args.term:
        exact_domains = generate_domains(args.term, tlds)
        for d in exact_domains:
            if d not in domain_meta:
                all_domains.append(d)
                domain_meta[d] = {"type": "exact", "visual": ""}

    # Hack search: domain hacks from the word
    if args.hack:
        hacks = generate_domain_hacks(args.hack, tlds)
        for h in hacks:
            if h.domain not in domain_meta:
                all_domains.append(h.domain)
                domain_meta[h.domain] = {"type": "hack", "visual": h.visual}

    if not all_domains:
        print("No domains to check.")
        return

    total = len(all_domains)
    checked = 0

    def on_result(result: DomainResult) -> None:
        nonlocal checked
        checked += 1
        sys.stdout.write(f"\rChecking {total:,} domains... [{checked:,}/{total:,}]")
        sys.stdout.flush()

    print(f"Loaded {len(tlds):,} TLDs")
    print(f"Checking {total:,} domains...")

    results = asyncio.run(
        check_domains(all_domains, concurrency=args.concurrency, on_result=on_result)
    )

    # Clear the progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    # RDAP verification of "possibly available" domains
    if not args.skip_rdap:
        available_count = sum(1 for r in results if r.status == DomainStatus.AVAILABLE)
        if available_count > 0:
            rdap_checked = 0

            def on_rdap_result(rdap_result) -> None:
                nonlocal rdap_checked
                rdap_checked += 1
                sys.stdout.write(
                    f"\rVerifying {available_count:,} available domains via RDAP... "
                    f"[{rdap_checked:,}/{available_count:,}]"
                )
                sys.stdout.flush()

            print(f"Verifying {available_count:,} available domains via RDAP...")
            results = asyncio.run(
                verify_available_domains(results, on_result=on_rdap_result)
            )

            # Clear the RDAP progress line
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

    display_results(results, domain_meta)


if __name__ == "__main__":
    main()
