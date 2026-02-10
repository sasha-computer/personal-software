"""Export domain search results to JSON or CSV files."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from domain_search.dns_checker import DomainResult

FIELD_DOMAIN = "domain"
FIELD_STATUS = "status"
FIELD_CHECK_METHOD = "check_method"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
EXPORT_FIELDS = (
    FIELD_DOMAIN,
    FIELD_STATUS,
    FIELD_CHECK_METHOD,
    FIELD_TYPE,
    FIELD_TIMESTAMP,
)


def export_results(
    results: list[DomainResult],
    output_path: str,
    domain_meta: dict[str, dict] | None = None,
) -> None:
    """Export results to a file. Format is auto-detected from extension.

    Args:
        results: List of DomainResult objects.
        output_path: Path to output file (.json, .jsonl, or .csv).
        domain_meta: Optional dict mapping domain -> {"type": "exact"|"hack", "visual": str}.

    Raises:
        ValueError: If the file extension is not .json, .jsonl, or .csv.
    """
    path = Path(output_path)
    ext = path.suffix.lower()

    if ext == ".json":
        _export_json(results, path, domain_meta)
    elif ext == ".jsonl":
        _export_jsonl(results, path, domain_meta)
    elif ext == ".csv":
        _export_csv(results, path, domain_meta)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Use .json, .jsonl, or .csv.")


def _build_row(result: DomainResult, domain_meta: dict[str, dict] | None) -> dict:
    """Build a single export row from a DomainResult."""
    meta = (domain_meta or {}).get(result.domain, {})
    return {
        FIELD_DOMAIN: result.domain,
        FIELD_STATUS: result.status.value,
        FIELD_CHECK_METHOD: meta.get("check_method", "DNS"),
        FIELD_TYPE: meta.get("type", "exact"),
        FIELD_TIMESTAMP: datetime.now(UTC).isoformat(),
    }


def _export_json(
    results: list[DomainResult],
    path: Path,
    domain_meta: dict[str, dict] | None,
) -> None:
    """Export results as JSON."""
    rows = [_build_row(r, domain_meta) for r in results]
    path.write_text(json.dumps(rows, indent=2) + "\n")


def _export_jsonl(
    results: list[DomainResult],
    path: Path,
    domain_meta: dict[str, dict] | None,
) -> None:
    """Export results as JSONL (JSON Lines)."""
    lines = [json.dumps(_build_row(r, domain_meta)) for r in results]
    path.write_text("\n".join(lines) + "\n")


def _export_csv(
    results: list[DomainResult],
    path: Path,
    domain_meta: dict[str, dict] | None,
) -> None:
    """Export results as CSV."""
    fieldnames = list(EXPORT_FIELDS)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(_build_row(result, domain_meta))
