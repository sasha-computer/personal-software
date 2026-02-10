"""Domain Search CLI - find available domain names (exact + hack) across all TLDs."""

import argparse
import asyncio

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text

from domain_search.dns_checker import DomainResult, DomainStatus, check_domains
from domain_search.exporter import export_results
from domain_search.hack_generator import generate_domain_hacks
from domain_search.rdap_checker import RdapResult, verify_available_domains
from domain_search.tld_list import fetch_tld_list
from domain_search.types import DomainMetaMap

console = Console()


def generate_domains(term: str, tlds: list[str]) -> list[str]:
    """Generate {term}.{tld} for every TLD in the list."""
    return [f"{term}.{tld}" for tld in tlds]


def sort_results(results: list[DomainResult]) -> list[DomainResult]:
    """Sort results by status (available, unknown, registered), then alphabetically."""
    status_order = {
        DomainStatus.AVAILABLE: 0,
        DomainStatus.UNKNOWN: 1,
        DomainStatus.REGISTERED: 2,
    }
    return sorted(results, key=lambda r: (status_order[r.status], r.domain))


STATUS_STYLES = {
    DomainStatus.AVAILABLE: "bold green",
    DomainStatus.UNKNOWN: "yellow",
    DomainStatus.REGISTERED: "red",
}


def _create_progress(label: str, *, output_console: Console) -> Progress:
    """Create a standardized progress bar for long-running checks."""
    return Progress(
        TextColumn(f"[bold blue]{label}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=output_console,
    )


def display_results(
    results: list[DomainResult],
    domain_meta: DomainMetaMap | None = None,
    output_console: Console | None = None,
) -> None:
    """Display results to the terminal using rich.

    Args:
        results: List of DomainResult objects.
        domain_meta: Optional dict mapping domain -> {"type": "exact"|"hack", "visual": str}.
        output_console: Optional Console for output (used in testing).
    """
    out = output_console or console
    sorted_results = sort_results(results)
    meta = domain_meta or {}

    available = sum(1 for r in results if r.status == DomainStatus.AVAILABLE)
    registered = sum(1 for r in results if r.status == DomainStatus.REGISTERED)
    unknown = sum(1 for r in results if r.status == DomainStatus.UNKNOWN)

    has_hacks = any(m.get("type") == "hack" for m in meta.values())

    table = Table(title="Domain Search Results", show_lines=False)
    table.add_column("Domain", style="bold")
    table.add_column("Status")
    if has_hacks:
        table.add_column("Type")
        table.add_column("Visual Reading")

    for r in sorted_results:
        style = STATUS_STYLES.get(r.status, "")
        status_text = Text(r.status.value, style=style)
        domain_style = "bold green" if r.status == DomainStatus.AVAILABLE else ""
        domain_text = Text(r.domain, style=domain_style)

        m = meta.get(r.domain, {})
        if has_hacks:
            dtype = m.get("type", "exact")
            visual = m.get("visual", "")
            table.add_row(domain_text, status_text, dtype, visual)
        else:
            table.add_row(domain_text, status_text)

    out.print(table)

    summary = Text()
    summary.append(f"Total: {len(results)}", style="bold")
    summary.append(" | ")
    summary.append(f"Available: {available}", style="bold green")
    summary.append(" | ")
    summary.append(f"Registered: {registered}", style="red")
    summary.append(" | ")
    summary.append(f"Unknown: {unknown}", style="yellow")
    out.print(summary)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search for available domain names across all TLDs."
    )
    parser.add_argument("term", help="Word to search for (runs both exact and domain hack search)")
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
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Export results to a file (supports .json, .jsonl, and .csv)",
    )
    parser.add_argument(
        "--tld",
        nargs="+",
        metavar="TLD",
        help="Filter to specific TLDs (e.g., --tld com io or --tld ck)",
    )
    args = parser.parse_args()

    tlds = fetch_tld_list()

    # Filter TLDs if --tld flag is provided
    if args.tld:
        # Normalize user input to lowercase for comparison
        requested_tlds = [t.lower() for t in args.tld]
        tld_set = set(tlds)

        # Check for invalid TLDs and warn
        invalid_tlds = [t for t in requested_tlds if t not in tld_set]
        if invalid_tlds:
            invalid_tlds_text = ", ".join(invalid_tlds)
            console.print(
                "[yellow]Warning: The following TLDs are not in the IANA list and "
                f"will be skipped: {invalid_tlds_text}[/yellow]"
            )

        # Filter to only valid TLDs from the request
        valid_tlds = [t for t in requested_tlds if t in tld_set]

        if not valid_tlds:
            console.print("[red]Error: No valid TLDs specified.[/red]")
            return

        tlds = valid_tlds

    # Build the list of domains to check and metadata for display
    all_domains: list[str] = []
    domain_meta: DomainMetaMap = {}

    # Exact search: term.{tld}
    exact_domains = generate_domains(args.term, tlds)
    for d in exact_domains:
        if d not in domain_meta:
            all_domains.append(d)
            domain_meta[d] = {"type": "exact", "visual": ""}

    # Hack search: domain hacks from the same word
    hacks = generate_domain_hacks(args.term, tlds)
    for h in hacks:
        if h.domain not in domain_meta:
            all_domains.append(h.domain)
            domain_meta[h.domain] = {"type": "hack", "visual": h.visual}

    if not all_domains:
        console.print("No domains to check.")
        return

    total = len(all_domains)
    console.print(f"Loaded {len(tlds):,} TLDs")

    # DNS checking with rich progress bar
    with _create_progress("Checking domains", output_console=console) as progress:
        task = progress.add_task("dns", total=total)

        def on_result(result: DomainResult) -> None:
            progress.advance(task)

        results = asyncio.run(
            check_domains(all_domains, concurrency=args.concurrency, on_result=on_result)
        )

    # RDAP verification of "possibly available" domains
    rdap_checked: set[str] = set()
    if not args.skip_rdap:
        available_count = sum(1 for r in results if r.status == DomainStatus.AVAILABLE)
        if available_count > 0:
            rdap_checked = {r.domain for r in results if r.status == DomainStatus.AVAILABLE}
            with _create_progress("Verifying via RDAP", output_console=console) as progress:
                rdap_task = progress.add_task("rdap", total=available_count)

                def on_rdap_result(rdap_result: RdapResult) -> None:
                    progress.advance(rdap_task)

                results = asyncio.run(verify_available_domains(results, on_result=on_rdap_result))

    # Track check method in domain_meta for export
    for d in rdap_checked:
        if d in domain_meta:
            domain_meta[d]["check_method"] = "RDAP"

    display_results(results, domain_meta)

    # Export results if --output specified
    if args.output:
        export_results(results, args.output, domain_meta)
        console.print(f"Results exported to {args.output}")
