"""Tests for US-007: Export Results to JSON and CSV."""

import csv
import io
import json
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console

from domain_search.dns_checker import DomainResult, DomainStatus
from domain_search.exporter import export_results


def _capture_console() -> tuple[Console, io.StringIO]:
    """Create a Console that writes to a StringIO for test capturing."""
    buf = io.StringIO()
    return Console(file=buf, force_terminal=True, width=120), buf


@pytest.fixture
def sample_results():
    return [
        DomainResult("sasha.com", DomainStatus.REGISTERED),
        DomainResult("sasha.xyz", DomainStatus.AVAILABLE),
        DomainResult("sasha.zzz", DomainStatus.UNKNOWN),
    ]


@pytest.fixture
def sample_meta():
    return {
        "sasha.com": {"type": "exact", "visual": ""},
        "sasha.xyz": {"type": "exact", "visual": "", "check_method": "RDAP"},
        "sasha.zzz": {"type": "hack", "visual": "sashazzz"},
    }


class TestExportJSON:
    def test_export_json_creates_file(self, tmp_path, sample_results):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out))
        assert out.exists()

    def test_export_json_valid_json(self, tmp_path, sample_results):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 3

    def test_export_json_contains_required_fields(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out), sample_meta)
        data = json.loads(out.read_text())
        required_fields = {"domain", "status", "check_method", "type", "timestamp"}
        for row in data:
            assert set(row.keys()) == required_fields

    def test_export_json_domain_values(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out), sample_meta)
        data = json.loads(out.read_text())
        domains = [row["domain"] for row in data]
        assert "sasha.com" in domains
        assert "sasha.xyz" in domains
        assert "sasha.zzz" in domains

    def test_export_json_status_values(self, tmp_path, sample_results):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        statuses = {row["domain"]: row["status"] for row in data}
        assert statuses["sasha.com"] == "registered"
        assert statuses["sasha.xyz"] == "possibly available"
        assert statuses["sasha.zzz"] == "unknown"

    def test_export_json_check_method(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out), sample_meta)
        data = json.loads(out.read_text())
        methods = {row["domain"]: row["check_method"] for row in data}
        assert methods["sasha.com"] == "DNS"
        assert methods["sasha.xyz"] == "RDAP"
        assert methods["sasha.zzz"] == "DNS"

    def test_export_json_type_field(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out), sample_meta)
        data = json.loads(out.read_text())
        types = {row["domain"]: row["type"] for row in data}
        assert types["sasha.com"] == "exact"
        assert types["sasha.zzz"] == "hack"

    def test_export_json_timestamp_is_iso(self, tmp_path, sample_results):
        out = tmp_path / "results.json"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        for row in data:
            # ISO 8601 format check - should contain 'T' and timezone info
            assert "T" in row["timestamp"]
            assert "+" in row["timestamp"] or row["timestamp"].endswith("Z") or "+00:00" in row["timestamp"]

    def test_export_json_default_check_method_is_dns(self, tmp_path, sample_results):
        """When no domain_meta provided, check_method defaults to DNS."""
        out = tmp_path / "results.json"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        for row in data:
            assert row["check_method"] == "DNS"


class TestExportJSONL:
    def test_export_jsonl_creates_file(self, tmp_path, sample_results):
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out))
        assert out.exists()

    def test_export_jsonl_valid_format(self, tmp_path, sample_results):
        """Each line should be a valid JSON object."""
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out))
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line)
            assert isinstance(data, dict)

    def test_export_jsonl_contains_required_fields(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out), sample_meta)
        lines = out.read_text().strip().split("\n")
        required_fields = {"domain", "status", "check_method", "type", "timestamp"}
        for line in lines:
            row = json.loads(line)
            assert set(row.keys()) == required_fields

    def test_export_jsonl_domain_values(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out), sample_meta)
        lines = out.read_text().strip().split("\n")
        domains = [json.loads(line)["domain"] for line in lines]
        assert "sasha.com" in domains
        assert "sasha.xyz" in domains
        assert "sasha.zzz" in domains

    def test_export_jsonl_status_values(self, tmp_path, sample_results):
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out))
        lines = out.read_text().strip().split("\n")
        statuses = {json.loads(line)["domain"]: json.loads(line)["status"] for line in lines}
        assert statuses["sasha.com"] == "registered"
        assert statuses["sasha.xyz"] == "possibly available"
        assert statuses["sasha.zzz"] == "unknown"

    def test_export_jsonl_check_method(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.jsonl"
        export_results(sample_results, str(out), sample_meta)
        lines = out.read_text().strip().split("\n")
        methods = {json.loads(line)["domain"]: json.loads(line)["check_method"] for line in lines}
        assert methods["sasha.com"] == "DNS"
        assert methods["sasha.xyz"] == "RDAP"
        assert methods["sasha.zzz"] == "DNS"


class TestExportCSV:
    def test_export_csv_creates_file(self, tmp_path, sample_results):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out))
        assert out.exists()

    def test_export_csv_has_header(self, tmp_path, sample_results):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out))
        reader = csv.DictReader(out.open())
        assert set(reader.fieldnames) == {"domain", "status", "check_method", "type", "timestamp"}

    def test_export_csv_row_count(self, tmp_path, sample_results):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out))
        reader = csv.DictReader(out.open())
        rows = list(reader)
        assert len(rows) == 3

    def test_export_csv_domain_values(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out), sample_meta)
        reader = csv.DictReader(out.open())
        rows = list(reader)
        domains = [row["domain"] for row in rows]
        assert "sasha.com" in domains
        assert "sasha.xyz" in domains

    def test_export_csv_status_values(self, tmp_path, sample_results):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out))
        reader = csv.DictReader(out.open())
        rows = list(reader)
        statuses = {row["domain"]: row["status"] for row in rows}
        assert statuses["sasha.com"] == "registered"
        assert statuses["sasha.xyz"] == "possibly available"

    def test_export_csv_check_method(self, tmp_path, sample_results, sample_meta):
        out = tmp_path / "results.csv"
        export_results(sample_results, str(out), sample_meta)
        reader = csv.DictReader(out.open())
        rows = list(reader)
        methods = {row["domain"]: row["check_method"] for row in rows}
        assert methods["sasha.xyz"] == "RDAP"
        assert methods["sasha.com"] == "DNS"


class TestFormatDetection:
    def test_json_extension_detected(self, tmp_path, sample_results):
        out = tmp_path / "output.json"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        assert isinstance(data, list)

    def test_jsonl_extension_detected(self, tmp_path, sample_results):
        out = tmp_path / "output.jsonl"
        export_results(sample_results, str(out))
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line)
            assert isinstance(data, dict)

    def test_csv_extension_detected(self, tmp_path, sample_results):
        out = tmp_path / "output.csv"
        export_results(sample_results, str(out))
        reader = csv.DictReader(out.open())
        rows = list(reader)
        assert len(rows) == 3

    def test_unsupported_extension_raises(self, tmp_path, sample_results):
        out = tmp_path / "output.txt"
        with pytest.raises(ValueError, match="Unsupported file format"):
            export_results(sample_results, str(out))

    def test_unsupported_extension_mentions_jsonl(self, tmp_path, sample_results):
        """Error message should mention .jsonl as a supported format."""
        out = tmp_path / "output.txt"
        with pytest.raises(ValueError, match=r"\.jsonl"):
            export_results(sample_results, str(out))

    def test_case_insensitive_extension(self, tmp_path, sample_results):
        out = tmp_path / "output.JSON"
        export_results(sample_results, str(out))
        data = json.loads(out.read_text())
        assert isinstance(data, list)


class TestCLIIntegration:
    def test_main_with_output_json(self, tmp_path):
        """main() with --output flag exports results to JSON."""
        from main import main

        out = tmp_path / "results.json"
        mock_results = [
            DomainResult("test.com", DomainStatus.REGISTERED),
            DomainResult("test.xyz", DomainStatus.AVAILABLE),
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
            patch("main.fetch_tld_list", return_value=["com", "xyz"]),
            patch("main.check_domains", side_effect=mock_check_domains),
            patch("main.verify_available_domains", side_effect=mock_verify),
            patch("main.console", test_console),
            patch("sys.argv", ["main.py", "test", "--output", str(out)]),
        ):
            main()

        assert out.exists()
        data = json.loads(out.read_text())
        assert len(data) == 2
        domains = [row["domain"] for row in data]
        assert "test.com" in domains
        assert "test.xyz" in domains
        output = buf.getvalue()
        assert "Results exported to" in output

    def test_main_with_output_csv(self, tmp_path):
        """main() with --output flag exports results to CSV."""
        from main import main

        out = tmp_path / "results.csv"
        mock_results = [
            DomainResult("test.com", DomainStatus.REGISTERED),
            DomainResult("test.xyz", DomainStatus.AVAILABLE),
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
            patch("main.fetch_tld_list", return_value=["com", "xyz"]),
            patch("main.check_domains", side_effect=mock_check_domains),
            patch("main.verify_available_domains", side_effect=mock_verify),
            patch("main.console", test_console),
            patch("sys.argv", ["main.py", "test", "--output", str(out)]),
        ):
            main()

        assert out.exists()
        reader = csv.DictReader(out.open())
        rows = list(reader)
        assert len(rows) == 2

    def test_main_without_output_flag_no_export(self, tmp_path):
        """main() without --output flag should not create any export file."""
        from main import main

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
            patch("main.fetch_tld_list", return_value=["com"]),
            patch("main.check_domains", side_effect=mock_check_domains),
            patch("main.verify_available_domains", side_effect=mock_verify),
            patch("main.console", test_console),
            patch("sys.argv", ["main.py", "test"]),
        ):
            main()

        output = buf.getvalue()
        assert "Results exported to" not in output
